"""Django settings for djangovue project."""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent


def get_env_bool(name, *, default=False, environ=None):
    """Return an environment variable as a boolean."""
    env = os.environ if environ is None else environ
    raw_value = env.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def get_env_list(name, *, default=None, environ=None):
    """Return a comma-separated environment variable as a list of strings."""
    env = os.environ if environ is None else environ
    raw_value = env.get(name)
    if raw_value is None:
        return [] if default is None else default
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def get_env_int(name, *, default, environ=None):
    """Return an environment variable as an integer."""
    env = os.environ if environ is None else environ
    raw_value = env.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"{name} must be an integer, got {raw_value!r}"
        ) from exc


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable must be set")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env_bool("DEBUG", default=False)

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

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "backend",
    "django_vite",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "djangovue.urls"

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

WSGI_APPLICATION = "djangovue.wsgi.application"


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=get_env_int("DB_CONN_MAX_AGE", default=60),
    )
}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
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
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "frontend",
    BASE_DIR / "frontend" / "dist",
]

USE_X_FORWARDED_PROTO = get_env_bool("USE_X_FORWARDED_PROTO", default=False)
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if USE_X_FORWARDED_PROTO else None
)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = get_env_bool("SECURE_SSL_REDIRECT", default=False)

# Vite configuration
DJANGO_VITE = {
    "default": {
        "dev_mode": get_env_bool("DJANGO_VITE_DEV_MODE", default=False),
        "dev_server_host": os.environ.get("DJANGO_VITE_DEV_SERVER_HOST", "127.0.0.1"),
        "dev_server_port": get_env_int("DJANGO_VITE_DEV_SERVER_PORT", default=3000),
        "manifest_path": str(
            BASE_DIR / "frontend" / "dist" / ".vite" / "manifest.json"
        ),
        "static_url_prefix": "",
    }
}
