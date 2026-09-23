# PyInstaller spec for the Windows LIFEOS.exe — a single process bundling
# the Django backend AND the pywebview/WebView2 window together (unlike
# macOS, which has a separate thin Swift launcher + a separate bundled
# backend executable; see desktop/windows/lifeos_windows.py for why one
# process is simpler here).
#
# Must be built on Windows (no cross-compilation) — see
# packaging/windows/build_release.ps1, or the windows-latest job in
# .github/workflows/release.yml.
#
# Build from the repo root:
#   .venv\Scripts\pyinstaller.exe packaging\windows\lifeos.spec --noconfirm

import sys
from pathlib import Path

REPO_ROOT = Path(SPECPATH).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

DOMAIN_APPS = [
    "core", "devices", "people", "school", "projects", "tasks", "finance",
    "study", "calendar_app", "journal", "writing", "goals", "notes",
    "personal", "inbox", "dashboard", "sync", "security", "search",
]

# Same reasoning as packaging/macos/lifeos-backend.spec: Django's migration
# loader and MIDDLEWARE/REST_FRAMEWORK's dotted-path strings are resolved
# dynamically at runtime, invisible to PyInstaller's static analysis.
hidden_imports = [
    "waitress", "dotenv",
    "whitenoise.middleware", "whitenoise.storage",
    "django_filters.rest_framework",
    "rest_framework.authentication", "rest_framework.permissions",
    "rest_framework.pagination", "rest_framework.renderers",
    "webview.platforms.edgechromium",
]
for app in DOMAIN_APPS:
    hidden_imports.append(f"apps.{app}.migrations")

# Paths are bundle-root-relative with NO "backend/" prefix — matching
# packaging/macos/lifeos-backend.spec exactly, which this mirrors. A frozen
# module's __file__ (e.g. lifeos/settings.py) resolves relative to the
# bundle root itself, not to any custom prefix chosen here, so these must
# line up with settings.py's BASE_DIR (= that file's own directory).
datas = [
    (str(BACKEND_DIR / "templates"), "templates"),
    (str(BACKEND_DIR / "static"), "static"),
]
for app in DOMAIN_APPS:
    migrations_dir = BACKEND_DIR / "apps" / app / "migrations"
    if migrations_dir.is_dir():
        datas.append((str(migrations_dir), f"apps/{app}/migrations"))

a = Analysis(
    # backend/run_windows.py, NOT desktop/windows/lifeos_windows.py directly
    # — PyInstaller's Django hook locates the project relative to whichever
    # script is this Analysis entry point, so it must sit next to lifeos/
    # (see backend/run_windows.py's own docstring, and the already-working
    # packaging/macos/lifeos-backend.spec which uses backend/run_server.py
    # for the exact same reason).
    [str(BACKEND_DIR / "run_windows.py")],
    pathex=[str(BACKEND_DIR), str(REPO_ROOT / "desktop" / "windows")],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="LIFEOS",
    icon=str(REPO_ROOT / "packaging" / "windows" / "AppIcon.ico") if (REPO_ROOT / "packaging" / "windows" / "AppIcon.ico").exists() else None,
    debug=False,
    strip=False,
    upx=False,
    console=False,
    onefile=True,
)
