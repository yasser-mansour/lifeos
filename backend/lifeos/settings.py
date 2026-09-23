"""
Django settings for the LIFEOS backend.

LIFEOS is a local-first, single-user personal operating system. These settings
assume the server runs on the user's own Mac, reachable from other devices
(Android) only over the local network — there is no public deployment target.
"""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# App-data root
#
# Every path below (secret key, database, media, local data, backups) is
# repo-relative by default — exactly today's behavior, for the existing dev
# checkout and every installation that predates this setting. A packaged
# distributable (desktop/LIFEOSLauncher, a future Windows wrapper) sets
# LIFEOS_APP_DATA_DIR to a platform user-data directory (e.g. ~/Library/
# Application Support/LIFEOS on macOS) instead, so a fresh user's data lives
# outside the installed application bundle and survives an app update/
# reinstall. Sourced from a single env var rather than one per path so a
# launcher only has to set one thing; each individual path can still be
# overridden independently (LIFEOS_DB_PATH, etc.) exactly as before.
# ---------------------------------------------------------------------------
_app_data_dir_override = os.environ.get("LIFEOS_APP_DATA_DIR")
if _app_data_dir_override:
    APP_DATA_ROOT = Path(_app_data_dir_override)
    _secret_key_dir = APP_DATA_ROOT
    _default_db_path = APP_DATA_ROOT / "database" / "lifeos.sqlite3"
    _default_data_dir = APP_DATA_ROOT / "data"
    _default_backup_dir = APP_DATA_ROOT / "backups"
    _default_media_root = APP_DATA_ROOT / "media"
else:
    APP_DATA_ROOT = REPO_ROOT
    _secret_key_dir = BASE_DIR
    _default_db_path = BASE_DIR / "lifeos.sqlite3"
    _default_data_dir = REPO_ROOT / "data"
    _default_backup_dir = REPO_ROOT / "backups"
    _default_media_root = BASE_DIR / "media"

# Where any local secret file lives — the generated .secret_key above, and
# apps.security.crypto's non-macOS Keychain fallback. Same "repo-relative by
# default, app-data-relative when packaged" rule as everything else here.
LIFEOS_SECRETS_DIR = _secret_key_dir

# ---------------------------------------------------------------------------
# Secret key
#
# LIFEOS must work without the user ever hand-editing an .env file. If no key
# is supplied via environment/.env, one is generated once and cached locally
# (gitignored) so it stays stable across restarts.
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("LIFEOS_SECRET_KEY")
if not SECRET_KEY:
    _secret_key_dir.mkdir(parents=True, exist_ok=True)
    secret_key_file = _secret_key_dir / ".secret_key"
    if secret_key_file.exists():
        SECRET_KEY = secret_key_file.read_text().strip()
    else:
        SECRET_KEY = secrets.token_urlsafe(64)
        secret_key_file.write_text(SECRET_KEY)
        secret_key_file.chmod(0o600)

DEBUG = os.environ.get("LIFEOS_DEBUG", "true").lower() in ("1", "true", "yes")

# LIFEOS is never exposed to the public internet: no port forwarding, no
# public DNS. It is reached over localhost (desktop shell) or the trusted LAN
# (Android sync). Every request still has to pass application-level auth
# (session login for the desktop UI, a per-device token for the API), so a
# permissive host list here does not by itself grant access to anything.
ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8420",
    "http://127.0.0.1:8420",
]

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "django_filters",
    # LIFEOS domain apps, in dependency order (later apps may reference
    # earlier ones via ForeignKey).
    "apps.core",
    "apps.devices",
    "apps.people",
    "apps.school",
    "apps.projects",
    "apps.tasks",
    "apps.finance",
    "apps.study",
    "apps.calendar_app",
    "apps.journal",
    "apps.writing",
    "apps.goals",
    "apps.notes",
    "apps.personal",
    "apps.inbox",
    "apps.dashboard",
    "apps.sync",
    "apps.security",
    "apps.search",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.AutoLockMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "lifeos.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.lifeos_context",
            ],
        },
    },
]

WSGI_APPLICATION = "lifeos.wsgi.application"
ASGI_APPLICATION = "lifeos.asgi.application"

# ---------------------------------------------------------------------------
# Database
#
# SQLite is intentional: LIFEOS is a local single-user application. The file
# lives at backend/lifeos.sqlite3 (kept out of git; see .gitignore). Models
# use UUID primary keys throughout, so a future move to Postgres would not
# require touching any foreign keys.
# ---------------------------------------------------------------------------
_db_path = Path(os.environ.get("LIFEOS_DB_PATH", str(_default_db_path)))
_db_path.parent.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(_db_path),
        "OPTIONS": {
            "timeout": 20,
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("LIFEOS_TIME_ZONE", "Africa/Casablanca")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / media
#
# LIFEOS.app runs the backend through waitress (see run_server.py), not
# Django's dev server — so the auto-static-serving that runserver provides
# in DEBUG mode does not apply here. WhiteNoise serves static files instead,
# in every mode, so the shipped app isn't silently missing all its CSS/JS.
# WHITENOISE_USE_FINDERS serves straight from STATICFILES_DIRS, so there's
# no separate `collectstatic` build step for a single-user local app.
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_USE_FINDERS = True

MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.environ.get("LIFEOS_MEDIA_ROOT", str(_default_media_root)))
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth / sessions
#
# There is exactly one human owner account, created during first-run setup
# (apps.core). LIFEOS holds financial, journal and academic data, so the
# session model is bank-app-style rather than "trusted machine, stay logged
# in forever": SESSION_COOKIE_AGE is a ceiling, not a target — the real
# expiry is driven by apps.core.middleware.AutoLockMiddleware (inactivity)
# and SESSION_EXPIRE_AT_BROWSER_CLOSE (closing/quitting the app). Both must
# independently require the passcode again; neither is a user-facing toggle.
# ---------------------------------------------------------------------------
LOGIN_URL = "core:onboarding_welcome"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "core:login"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 365
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ---------------------------------------------------------------------------
# REST framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.devices.auth.DeviceTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DATETIME_FORMAT": "iso-8601",
}

# ---------------------------------------------------------------------------
# LIFEOS-specific settings
# ---------------------------------------------------------------------------
LIFEOS_DEFAULT_CURRENCY = os.environ.get("LIFEOS_DEFAULT_CURRENCY", "MAD")
LIFEOS_VERSION = "0.1.0-beta.1"
LIFEOS_DATA_DIR = Path(os.environ.get("LIFEOS_DATA_DIR", str(_default_data_dir)))
LIFEOS_BACKUP_DIR = Path(os.environ.get("LIFEOS_BACKUP_DIR", str(_default_backup_dir)))
LIFEOS_DATA_DIR.mkdir(parents=True, exist_ok=True)
LIFEOS_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Encryption key for genuinely sensitive fields (e.g. card last-4 metadata
# blobs). Backed by the macOS Keychain when available; see apps.security.crypto.
LIFEOS_KEYCHAIN_SERVICE = "com.lifeos.app"
LIFEOS_KEYCHAIN_ACCOUNT = "lifeos-field-encryption-key"

# ---------------------------------------------------------------------------
# Logging — never log request/response bodies (they can contain finance or
# journal content); keep it to level + path.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.server": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
