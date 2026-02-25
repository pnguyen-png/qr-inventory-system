"""
Django settings for qr_inventory_project project.
Secured: Feb 2026
"""

from pathlib import Path
from urllib.parse import urlparse, unquote
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Core security
# -----------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-key-change-me")
PRINT_API_SECRET = os.environ.get("PRINT_API_SECRET", "")

# DEBUG: default OFF; enable locally by setting DEBUG=1
DEBUG = os.environ.get("DEBUG", "").strip() in ("1", "true", "True", "yes", "YES")

# Railway hosts
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    ".railway.app",
    "fratrack.com",
    "www.fratrack.com",
]

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
    "inventory.middleware.LoginRequiredMiddleware",
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
# Parse manually to avoid dj_database_url version incompatibilities.
_db_url = os.environ.get("DATABASE_URL", "").strip()
if _db_url:
    # Fix missing scheme from Railway
    if _db_url.startswith("://"):
        _db_url = "postgresql" + _db_url
    elif "://" not in _db_url:
        _db_url = "postgresql://" + _db_url
    _parsed = urlparse(_db_url)
    _db_name = unquote(_parsed.path.lstrip("/")) or "railway"
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _db_name,
            "USER": unquote(_parsed.username or ""),
            "PASSWORD": unquote(_parsed.password or ""),
            "HOST": _parsed.hostname or "localhost",
            "PORT": str(_parsed.port or 5432),
            "CONN_MAX_AGE": 600,
        }
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
TIME_ZONE = "America/New_York"
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
# CORS / CSRF
# -----------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://fratrack.com",
    "https://www.fratrack.com",
    "https://web-production-57c20.up.railway.app",
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "https://*.railway.app",
    "https://web-production-57c20.up.railway.app",
    "https://fratrack.com",
    "https://www.fratrack.com",
]

if DEBUG:
    CORS_ALLOWED_ORIGINS += [
        "http://localhost:8091",
        "http://127.0.0.1:8091",
    ]

# -----------------------------------------------------------------------------
# Proxy / HTTPS hardening for Railway
# -----------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = False  # Railway + Cloudflare terminate TLS; avoids redirect loops
    SECURE_HSTS_SECONDS = 31536000  # 1 year — browsers remember to use HTTPS
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False  # Enable after confirming HSTS works

# Security headers (apply in all environments)
SECURE_CONTENT_TYPE_NOSNIFF = True  # X-Content-Type-Options: nosniff
X_FRAME_OPTIONS = "DENY"  # Prevent clickjacking
SESSION_COOKIE_HTTPONLY = True  # JS cannot read session cookie
SESSION_COOKIE_SAMESITE = "Lax"  # Prevent CSRF via cross-site requests
CSRF_COOKIE_SAMESITE = "Lax"

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

# -----------------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------------
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Session expires after 15 minutes of inactivity; timer resets on each request
SESSION_COOKIE_AGE = 60 * 15  # 15 minutes
SESSION_SAVE_EVERY_REQUEST = True
