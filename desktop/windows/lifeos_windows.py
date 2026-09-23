"""Windows desktop wrapper for LIFEOS — the Windows equivalent of
desktop/LIFEOSLauncher (Swift/AppKit on macOS). There is no separate native
project here on purpose: Windows has no Xcode-style "compile a thin native
shell" story as convenient as swiftc, so this wrapper runs the same Django
backend everywhere else uses, in a background thread inside one process,
and shows it in a native window via pywebview (WebView2 on Windows — see
docs/ARCHITECTURE.md and packaging/windows/README.md). Built into a single
LIFEOS.exe by packaging/windows/build_release.ps1 (PyInstaller), which is
what packaging/windows/installer.iss wraps into the installer normal users
download.

Never launched by, and never touches, the macOS desktop/LIFEOSLauncher code
path or a dev checkout's own backend/lifeos.sqlite3 — this always runs
against %LOCALAPPDATA%\\LIFEOS, exactly like the macOS distributable build
always runs against ~/Library/Application Support/LIFEOS (see BackendManager.
swift). A developer working on Windows can still run `python manage.py
runserver` directly for day-to-day backend work; this file is only ever the
entry point PyInstaller freezes for the shipped app.
"""

import os
import socket
import sys
import threading
import time
from pathlib import Path

PORT = int(os.environ.get("LIFEOS_PORT", "8420"))
HOST = "127.0.0.1"


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / "LIFEOS"


def _run_backend():
    """Runs forever (waitress.serve blocks) — call on a background thread,
    never the main thread, since pywebview's event loop must own that."""
    if not getattr(sys, "frozen", False):
        # Only needed for `python desktop/windows/lifeos_windows.py` during
        # local iteration on this wrapper itself. A frozen (PyInstaller)
        # build already has apps.*/lifeos.* bundled as if they were
        # top-level packages (packaging/windows/lifeos.spec's `pathex`,
        # exactly like packaging/macos/lifeos-backend.spec does for the
        # already-verified macOS build) — no sys.path change needed there.
        backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
        sys.path.insert(0, str(backend_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lifeos.settings")
    os.environ["LIFEOS_APP_DATA_DIR"] = str(_app_data_dir())
    os.environ["LIFEOS_DEBUG"] = "false"
    os.environ["LIFEOS_PORT"] = str(PORT)
    os.environ["LIFEOS_HOST"] = HOST

    import django

    django.setup()
    from django.core.management import call_command
    from waitress import serve

    from lifeos.wsgi import application

    call_command("migrate", verbosity=0, interactive=False)
    serve(application, host=HOST, port=PORT, threads=8)


def _redirect_output_to_log_file():
    """A windowed (non-console) PyInstaller build has no terminal for print()
    to go to — everything would simply vanish. Mirrors BackendManager.swift
    logging to <app-data>/logs/backend.log."""
    logs_dir = _app_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(logs_dir / "backend.log", "a", buffering=1, encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file


def main():
    _redirect_output_to_log_file()

    # Same "never spawn a duplicate backend" rule as BackendManager.swift:
    # if something is already answering on this port (another LIFEOS
    # instance, or a developer's own manage.py runserver), attach to it
    # instead of racing it for the port.
    if not _is_port_open(HOST, PORT):
        threading.Thread(target=_run_backend, daemon=True).start()
        for _ in range(40):
            if _is_port_open(HOST, PORT):
                break
            time.sleep(0.5)
        else:
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                "LIFEOS couldn't start correctly.\n\nYour data has not been deleted.\n\n"
                f"Check the log at {_app_data_dir() / 'logs' / 'backend.log'} for details.",
                "LIFEOS",
                0x10,
            )
            return

    import webview

    webview.create_window("LIFEOS", f"http://{HOST}:{PORT}/", width=1280, height=860, min_size=(900, 600))
    webview.start()


if __name__ == "__main__":
    main()
