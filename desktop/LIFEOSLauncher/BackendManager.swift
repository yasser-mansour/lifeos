import Foundation

/// Starts, health-checks, and stops the Django/waitress backend. Never
/// spawns a second copy if one is already answering on the health endpoint
/// — that's the "prevent duplicate backend processes" requirement, and it
/// also means launching LIFEOS.app while `manage.py runserver` is already
/// running in a terminal (e.g. during development) just attaches to it
/// instead of fighting over the port.
final class BackendManager {
    enum StartResult {
        case alreadyRunning
        case started
        case failed(String)
    }

    private var process: Process?
    private let host = "127.0.0.1"
    private let port: Int
    private let repoRoot: URL?
    private let logFileURL: URL

    init(port: Int = 8420) {
        self.port = port

        if Self.bundledBackendPath != nil {
            // Distributable mode: no sibling repo checkout exists at all on
            // an end user's machine, so there's nothing to bake a path to —
            // logs live under the same per-user app-data directory the
            // backend itself writes its database into.
            self.repoRoot = nil
            let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("LIFEOS")
            let logsDir = appSupport.appendingPathComponent("logs")
            try? FileManager.default.createDirectory(at: logsDir, withIntermediateDirectories: true)
            self.logFileURL = logsDir.appendingPathComponent("backend.log")
        } else {
            // LIFEOS.app/Contents/MacOS/LIFEOSLauncher -> walk up to the repo root.
            // In a from-source dev run, LIFEOS_REPO_ROOT overrides this (see build_mac_app.sh).
            // LIFEOS.app is meant to be movable (Finder, /Applications, Dock — see
            // spec §2), so its own path at runtime can't tell us where the repo
            // (backend/, .venv/) lives. build_mac_app.sh bakes that absolute path
            // in at build time via BuildConfig.swift; LIFEOS_REPO_ROOT remains a
            // manual override for running the launcher straight from source.
            let root: URL
            if let override = ProcessInfo.processInfo.environment["LIFEOS_REPO_ROOT"] {
                root = URL(fileURLWithPath: override)
            } else {
                root = URL(fileURLWithPath: BuildConfig.repoRootPath)
            }
            self.repoRoot = root

            let logsDir = root.appendingPathComponent("data/logs")
            try? FileManager.default.createDirectory(at: logsDir, withIntermediateDirectories: true)
            self.logFileURL = logsDir.appendingPathComponent("backend.log")
        }
    }

    var healthURL: URL { URL(string: "http://\(host):\(port)/api/health/")! }
    var appURL: URL { URL(string: "http://\(host):\(port)/")! }

    func start(completion: @escaping (StartResult) -> Void) {
        checkHealth { [weak self] isHealthy in
            guard let self else { return }
            if isHealthy {
                completion(.alreadyRunning)
                return
            }
            self.launchProcess(completion: completion)
        }
    }

    /// A distributable build (packaging/macos/build_release.sh) embeds the
    /// PyInstaller-bundled backend at Contents/Resources/lifeos-backend/ —
    /// a real standalone executable, no system Python or .venv involved. A
    /// dev build (scripts/build_mac_app.sh) never has this, so it falls
    /// through to the existing sibling-checkout behavior below, completely
    /// unchanged — this is what keeps the current dev workflow working.
    private static var bundledBackendPath: URL? {
        guard let resourcePath = Bundle.main.resourcePath else { return nil }
        let candidate = URL(fileURLWithPath: resourcePath)
            .appendingPathComponent("lifeos-backend/lifeos-backend")
        return FileManager.default.fileExists(atPath: candidate.path) ? candidate : nil
    }

    private func launchProcess(completion: @escaping (StartResult) -> Void) {
        let task = Process()
        task.environment = ProcessInfo.processInfo.environment
        task.environment?["LIFEOS_PORT"] = String(port)

        if let backendExe = Self.bundledBackendPath {
            // Distributable mode: a fresh user's data must live outside the
            // (replaceable-on-update) app bundle — see docs on app-data
            // paths. DEBUG is explicitly off for anything actually shipped.
            let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("LIFEOS")
            task.executableURL = backendExe
            task.arguments = []
            task.environment?["LIFEOS_APP_DATA_DIR"] = appSupport.path
            task.environment?["LIFEOS_DEBUG"] = "false"
        } else if let repoRoot {
            let pythonPath = repoRoot.appendingPathComponent(".venv/bin/python")
            let scriptPath = repoRoot.appendingPathComponent("backend/run_server.py")

            guard FileManager.default.fileExists(atPath: pythonPath.path) else {
                completion(.failed("No Python virtual environment found at \(pythonPath.path). Run scripts/setup_mac.sh first."))
                return
            }
            task.executableURL = pythonPath
            task.arguments = [scriptPath.path]
        } else {
            completion(.failed("No bundled backend and no dev repo checkout found — this build is misconfigured."))
            return
        }

        FileManager.default.createFile(atPath: logFileURL.path, contents: nil)
        if let handle = FileHandle(forWritingAtPath: logFileURL.path) {
            task.standardOutput = handle
            task.standardError = handle
        }

        do {
            try task.run()
            self.process = task
        } catch {
            completion(.failed("Couldn't start the backend process: \(error.localizedDescription)"))
            return
        }

        waitForHealthy(attemptsRemaining: 40) { healthy in
            if healthy {
                completion(.started)
            } else {
                completion(.failed("The backend started but never became healthy. Check \(self.logFileURL.path)."))
            }
        }
    }

    private func waitForHealthy(attemptsRemaining: Int, completion: @escaping (Bool) -> Void) {
        guard attemptsRemaining > 0 else {
            completion(false)
            return
        }
        checkHealth { [weak self] healthy in
            if healthy {
                completion(true)
            } else {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                    self?.waitForHealthy(attemptsRemaining: attemptsRemaining - 1, completion: completion)
                }
            }
        }
    }

    func checkHealth(completion: @escaping (Bool) -> Void) {
        var request = URLRequest(url: healthURL)
        request.timeoutInterval = 2
        URLSession.shared.dataTask(with: request) { data, response, error in
            guard error == nil, let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                DispatchQueue.main.async { completion(false) }
                return
            }
            DispatchQueue.main.async { completion(true) }
        }.resume()
    }

    /// Only stops the backend if *this* launch started it — attaching to an
    /// already-running dev server should never kill someone else's process.
    func stopIfOwned() {
        guard let process, process.isRunning else { return }
        process.terminate()
    }
}
