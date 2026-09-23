# PyInstaller spec for the self-contained LIFEOS backend used by the
# distributable desktop build (never the dev workflow — scripts/build_mac_app.sh
# and BackendManager.swift's dev-checkout path are untouched by this).
#
# Build from the repo root:
#   .venv/bin/pyinstaller packaging/macos/lifeos-backend.spec --noconfirm
#
# Produces dist/lifeos-backend/ — a self-contained onedir bundle (Python +
# Django + every dependency + templates/static/migrations) with no
# dependency on a system Python or this repo's own .venv. Onedir rather than
# onefile: a Django app's templates/migrations/static are plain files Django
# reads directly at runtime, which is far more robust under onedir (files
# extracted once, in place) than onefile (re-extracted to a temp dir on
# every single launch).

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

# Django's migration loader finds migrations by listing the filesystem, not
# by static import — PyInstaller's analysis can't see that, so every
# migrations package needs an explicit hidden-import.
hidden_imports = [
    "waitress", "dotenv",
    # These are only ever referenced as dotted-path strings in settings.py
    # (MIDDLEWARE, REST_FRAMEWORK) — Django/DRF resolve them dynamically via
    # import_string() at runtime, which PyInstaller's static analysis can't
    # see, so each one needs to be listed explicitly.
    "whitenoise.middleware", "whitenoise.storage",
    "django_filters.rest_framework",
    "rest_framework.authentication", "rest_framework.permissions",
    "rest_framework.pagination", "rest_framework.renderers",
]
for app in DOMAIN_APPS:
    hidden_imports.append(f"apps.{app}.migrations")

datas = [
    (str(BACKEND_DIR / "templates"), "templates"),
    (str(BACKEND_DIR / "static"), "static"),
]
for app in DOMAIN_APPS:
    migrations_dir = BACKEND_DIR / "apps" / app / "migrations"
    if migrations_dir.is_dir():
        datas.append((str(migrations_dir), f"apps/{app}/migrations"))

a = Analysis(
    [str(BACKEND_DIR / "run_server.py")],
    pathex=[str(BACKEND_DIR)],
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
    [],
    exclude_binaries=True,
    name="lifeos-backend",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="lifeos-backend",
)
