# LIFEOS.app

A small native Swift/AppKit wrapper — no application logic of its own. It starts the backend, waits for it to report healthy, and shows it in a native window via `WKWebView`.

## Build

```bash
../scripts/build_mac_app.sh
open LIFEOS.app
```

No Xcode project is needed or used — `build_mac_app.sh` compiles `LIFEOSLauncher/*.swift` directly with `swiftc` and hand-assembles the `.app` bundle (`Info.plist`, compiled binary, generated icon, ad-hoc code signature). Requires Xcode Command Line Tools (`xcode-select --install`) for `swiftc`, `iconutil`, and `codesign`.

## What it actually does

1. `BackendManager.checkHealth()` — is something already answering `http://127.0.0.1:8420/api/health/`? If so, attach to it and skip straight to opening the window (never launches a second backend process — see spec's "prevent duplicate backend processes").
2. If not, launch `.venv/bin/python backend/run_server.py` as a child process, log its output to `data/logs/backend.log`, and poll the health endpoint (every 0.5s, up to 20s) until it responds.
3. Open an `NSWindow` with a `WKWebView` pointing at `http://127.0.0.1:8420/`.
4. On quit: if *this launch* started the backend, terminate it. If it attached to an already-running one (e.g. a `manage.py runserver` you started by hand for development), leave it running — LIFEOS.app never kills a process it didn't start.

`LSMultipleInstancesProhibited` in `Info.plist` means double-clicking the app again while it's already running just re-activates the existing window (`applicationShouldHandleReopen`) rather than launching a second instance — both of these (single-instance app, single backend process) were verified directly during this build by launching the app, attempting a second launch, and confirming no duplicate process appeared either time.

## Repo path resolution

`LIFEOS.app` is meant to be movable (Finder, `/Applications`, the Dock), so it can't infer where `backend/` and `.venv/` live from its own runtime location. `build_mac_app.sh` bakes the absolute repo path in at build time (generated into `build/BuildConfig.swift`, gitignored) — if you move the *source repo* itself after building, rebuild the app. `LIFEOS_REPO_ROOT` as an environment variable overrides this, for running the launcher against a different checkout without rebuilding.

## Icon

Generated at build time by `generate_icon.py` (a solid indigo rounded square with a concentric-ring mark, matching the Android launcher icon's design) via Pillow, then packaged into `.icns` with `iconutil`. Not committed as a binary — regenerated on every build.
