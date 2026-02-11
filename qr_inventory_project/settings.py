"""
Django settings for qr_inventory_project project.
"""

from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Core security
# -----------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-key-change-me")

# DEBUG: temporarily ON to diagnose 500 error — revert after fixing
DEBUG = True

# Railway hosts (temporarily wildcard for debugging)
ALLOWED_HOSTS = ["*"]

# If you are testing via ngrok locally
if os.environ.get("ALLOW_NGROK", "").strip() in ("1", "true", "True"):
    ALLOWED_HOSTS.append(".ngrok-free.dev")

# -----------------------------------------------------------------------------
# Apps
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "inventory",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "qr_inventory_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "qr_inventory_project.wsgi.application"

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------

# Railway injects DATABASE_URL when Postgres plugin is attached.
# Fix: Railway may provide a URL with missing scheme (e.g. "://user:pass@host/db")
_db_url = os.environ.get("DATABASE_URL", "").strip()
if _db_url:
    if _db_url.startswith("://"):
        _db_url = "postgresql" + _db_url
    elif "://" not in _db_url:
        _db_url = "postgresql://" + _db_url
    DATABASES = {
        "default": dj_database_url.parse(_db_url, conn_max_age=600)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# -----------------------------------------------------------------------------
# Auth / i18n
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Static files (WhiteNoise)
# -----------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Django 5.0+ requires STORAGES instead of the removed STATICFILES_STORAGE
# WhiteNoise middleware serves static files; use Django's built-in storage for collection
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Media files (photo uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------------------------------------------------------
# CORS / CSRF (Excel calls your API)
# -----------------------------------------------------------------------------
# For production you should restrict this; leaving permissive to unblock your integration.
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "https://*.railway.app",
    "https://web-production-57c20.up.railway.app",
]

# -----------------------------------------------------------------------------
# Proxy / HTTPS hardening for Railway
# -----------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = False  # Railway already terminates TLS; leaving False avoids redirect loops

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------------------------------------------
# Logging — send errors to stdout so Railway logs capture them
# -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
