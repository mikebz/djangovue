"""Django settings for djangovue project.

See https://docs.djangoproject.com/en/6.0/topics/settings/ for the full list of
settings and https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/
for the production deployment checklist this module follows.

Author: Mike Borozdin (mikebz@)
"""

import os
from pathlib import Path
from typing import Any

import dj_database_url
from dj_database_url import DBConfig
from django.core.exceptions import ImproperlyConfigured

from djangovue.utils import (
    build_csp_policy,
    format_url_host,
    get_env_bool,
    get_env_int,
    get_env_list,
    get_env_str,
    load_env_file,
    validate_hsts_preload,
)

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Local configuration comes from .env, copied from .env.example by `make setup`
# and never committed. Loading it here rather than in a task runner is what
# makes `uv run manage ...`, gunicorn, and the e2e scripts all see the same
# configuration. Real environment variables are left untouched, so a container
# or a CI job overrides individual keys without a file at all.
load_env_file(BASE_DIR / ".env")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY: str | None = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable must be set")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG: bool = get_env_bool("DEBUG", default=False)

ALLOWED_HOSTS: list[str]
if DEBUG:
    ALLOWED_HOSTS = get_env_list(
        "ALLOWED_HOSTS",
        default=["localhost", "127.0.0.1", "0.0.0.0"],
    )
else:
    ALLOWED_HOSTS = get_env_list("ALLOWED_HOSTS")
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured("ALLOWED_HOSTS must be set when DEBUG is disabled")


# Application definition

INSTALLED_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "backend",
    "django_vite",
]

MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    # Django 6.0 ships Content-Security-Policy support; the middleware reads
    # SECURE_CSP below and makes a per-request nonce available to templates.
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF: str = "djangovue.urls"

TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Exposes {{ csp_nonce }} for any inline script or style.
                "django.template.context_processors.csp",
            ],
        },
    },
]

WSGI_APPLICATION: str = "djangovue.wsgi.application"
ASGI_APPLICATION: str = "djangovue.asgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES: dict[str, DBConfig] = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=get_env_int("DB_CONN_MAX_AGE", default=60),
    )
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE: str = "en-us"

TIME_ZONE: str = "UTC"

USE_I18N: bool = True

USE_TZ: bool = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL: str = "/static/"
STATIC_ROOT: Path = BASE_DIR / "staticfiles"

STATICFILES_DIRS: list[Path] = [
    BASE_DIR / "frontend",
    BASE_DIR / "frontend" / "dist",
]


# Vite configuration
# The dev-mode flag and dev server address are read first because the CSP below
# has to allow that origin whenever assets are served from it.

VITE_DEV_MODE: bool = get_env_bool("DJANGO_VITE_DEV_MODE", default=False)
# Bracketed here rather than at each use site, so django-vite's asset URL and
# the CSP source that has to match it are built from the same string.
VITE_DEV_SERVER_HOST: str = format_url_host(
    get_env_str("DJANGO_VITE_DEV_SERVER_HOST", default="127.0.0.1")
)
VITE_DEV_SERVER_PORT: int = get_env_int("DJANGO_VITE_DEV_SERVER_PORT", default=3000)

DJANGO_VITE: dict[str, dict[str, Any]] = {
    "default": {
        "dev_mode": VITE_DEV_MODE,
        "dev_server_host": VITE_DEV_SERVER_HOST,
        "dev_server_port": VITE_DEV_SERVER_PORT,
        "manifest_path": str(
            BASE_DIR / "frontend" / "dist" / ".vite" / "manifest.json"
        ),
        "static_url_prefix": "",
    }
}


# Security
# https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

USE_X_FORWARDED_PROTO: bool = get_env_bool("USE_X_FORWARDED_PROTO", default=False)
SECURE_PROXY_SSL_HEADER: tuple[str, str] | None = (
    ("HTTP_X_FORWARDED_PROTO", "https") if USE_X_FORWARDED_PROTO else None
)
SESSION_COOKIE_SECURE: bool = not DEBUG
CSRF_COOKIE_SECURE: bool = not DEBUG
SECURE_SSL_REDIRECT: bool = get_env_bool("SECURE_SSL_REDIRECT", default=False)

# X_FRAME_OPTIONS, SECURE_CONTENT_TYPE_NOSNIFF, SECURE_REFERRER_POLICY and
# SECURE_CROSS_ORIGIN_OPENER_POLICY are left at Django's defaults, which already
# deny framing, disable MIME sniffing, and keep referrers and window handles
# same-origin. `SecurityHeaderTest` pins that behavior on the served response.

# HSTS is opt-in: switching it on tells browsers to refuse plain HTTP for this
# host for the whole max-age, which is not something to inflict on a developer
# machine or on a deployment that is not fully on HTTPS yet.
SECURE_HSTS_SECONDS: int = get_env_int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = get_env_bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False
)
SECURE_HSTS_PRELOAD: bool = get_env_bool("SECURE_HSTS_PRELOAD", default=False)

validate_hsts_preload(
    preload=SECURE_HSTS_PRELOAD,
    include_subdomains=SECURE_HSTS_INCLUDE_SUBDOMAINS,
    max_age=SECURE_HSTS_SECONDS,
)

# Content Security Policy (new in Django 6.0).
SECURE_CSP: dict[str, list[str]] = build_csp_policy(
    dev_mode=VITE_DEV_MODE,
    dev_server_host=VITE_DEV_SERVER_HOST,
    dev_server_port=VITE_DEV_SERVER_PORT,
)
SECURE_CSP_REPORT_ONLY: dict[str, list[str]] = {}
