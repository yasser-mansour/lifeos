# LIFEOS Windows build

Unlike macOS (a native Swift/AppKit launcher shelling out to a separately
bundled Python backend — see `desktop/README.md`), the Windows build is one
process: `desktop/windows/lifeos_windows.py` runs the same Django backend
everywhere else uses in a background thread, and shows it in a native window
via [pywebview](https://pywebview.flowrl.com/) (WebView2 on Windows).

## Build

Must run on Windows — PyInstaller does not cross-compile:

```powershell
pwsh packaging/windows/build_release.ps1 -Version 0.1.0
```

Produces `packaging/windows/dist/LIFEOS-Setup-<version>.exe` — a normal
per-user installer (Inno Setup): Start Menu shortcut, optional desktop
shortcut, standard uninstall entry, and a WebView2 Runtime check/install so
a user is never asked to troubleshoot that themselves.

This is exercised for real by the `windows-latest` job in
`.github/workflows/release.yml` — the actual disclosed status (see the
project's distribution report) is that this has been verified via that CI
job, not by hand on a physical Windows machine, since none was available
during development. The equivalent Django/migrations/templates discovery
logic (the part most likely to silently break under PyInstaller) was
verified directly on macOS first, using the identical entry-point pattern
(`backend/run_windows.py`), before ever relying on CI to catch it.

## User data

Lives at `%LOCALAPPDATA%\LIFEOS\` (database, backups, logs) — never inside
the install directory, so an update or reinstall never touches it. See
`desktop/windows/lifeos_windows.py`'s `_app_data_dir()`.

## Signing

Unsigned — no Windows code-signing certificate is available. SmartScreen
will show an "unrecognized app" warning on first run; see the main
`README.md` for exactly what that looks like and why it's expected for this
beta, rather than something to work around by disabling Windows Defender.
