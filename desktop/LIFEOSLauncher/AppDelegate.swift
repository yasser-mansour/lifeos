import Cocoa
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow?
    private var webView: WKWebView?
    // LIFEOS_PORT overrides the port LIFEOSLauncher itself checks/binds to
    // (BackendManager also forwards this same value to the backend process
    // it spawns) — mainly useful for running a second, isolated instance
    // side by side with a normal one during testing.
    private let backend = BackendManager(port: Int(ProcessInfo.processInfo.environment["LIFEOS_PORT"] ?? "") ?? 8420)
    private var startedBackendOurselves = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMenuBar()
        showLaunchingWindow()

        backend.start { [weak self] result in
            guard let self else { return }
            switch result {
            case .alreadyRunning:
                self.startedBackendOurselves = false
                self.loadApp()
            case .started:
                self.startedBackendOurselves = true
                self.loadApp()
            case .failed(let message):
                self.showError(message)
            }
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationWillTerminate(_ notification: Notification) {
        if startedBackendOurselves {
            backend.stopIfOwned()
        }
    }

    /// Clicking the Dock icon while already running should surface the
    /// existing window, never launch a second one (spec: "handles reopen").
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        window?.makeKeyAndOrderFront(nil)
        return true
    }

    // MARK: - Window

    private func makeWindow() -> NSWindow {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1280, height: 820),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "LIFEOS"
        window.minSize = NSSize(width: 960, height: 640)
        window.center()
        window.titlebarAppearsTransparent = false
        return window
    }

    private func showLaunchingWindow() {
        let window = makeWindow()
        let label = NSTextField(labelWithString: "Starting LIFEOS…")
        label.font = .systemFont(ofSize: 15, weight: .medium)
        label.alignment = .center
        label.frame = window.contentView!.bounds
        label.autoresizingMask = [.width, .height]
        window.contentView?.addSubview(label)
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        self.window = window
    }

    private func loadApp() {
        guard let window else { return }

        let config = WKWebViewConfiguration()
        let webView = WKWebView(frame: window.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.setValue(false, forKey: "drawsBackground")

        window.contentView?.subviews.forEach { $0.removeFromSuperview() }
        window.contentView?.addSubview(webView)
        webView.load(URLRequest(url: backend.appURL))

        self.webView = webView
    }

    private func showError(_ message: String) {
        let alert = NSAlert()
        alert.alertStyle = .critical
        alert.messageText = "LIFEOS couldn't start"
        alert.informativeText = message
        alert.addButton(withTitle: "Quit")
        alert.runModal()
        NSApp.terminate(nil)
    }

    // MARK: - Menu bar

    private func buildMenuBar() {
        let mainMenu = NSMenu()

        let appMenuItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About LIFEOS", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit LIFEOS", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)

        let editMenuItem = NSMenuItem()
        let editMenu = NSMenu(title: "Edit")
        editMenu.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editMenuItem.submenu = editMenu
        mainMenu.addItem(editMenuItem)

        let windowMenuItem = NSMenuItem()
        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(withTitle: "Minimize", action: #selector(NSWindow.miniaturize(_:)), keyEquivalent: "m")
        windowMenu.addItem(withTitle: "Close", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        windowMenuItem.submenu = windowMenu
        mainMenu.addItem(windowMenuItem)

        NSApp.mainMenu = mainMenu
        NSApp.windowsMenu = windowMenu
    }
}
