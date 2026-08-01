"""Django settings for djangovue project.

See https://docs.djangoproject.com/en/6.0/topics/settings/ for the full list of
settings and https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/
for the production deployment checklist this module follows.
"""

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import dj_database_url
from dj_database_url import DBConfig
from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR: Path = Path(__file__).resolve().parent.parent


def get_env_bool(
    name: str,
    *,
    default: bool = False,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return an environment variable as a boolean.

    Args:
        name: The name of the environment variable.
        default: The default value to return if the variable is missing.
        environ: Optional mapping to use instead of `os.environ`.

    Returns:
        The evaluated boolean value of the environment variable.

    Examples:
        >>> get_env_bool("DEBUG", environ={"DEBUG": "1"})
        True
        >>> get_env_bool("DEBUG", environ={"DEBUG": "false"})
        False
        >>> get_env_bool("MISSING", default=True, environ={})
        True

    """
    env = os.environ if environ is None else environ
    raw_value = env.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def get_env_list(
    name: str,
    *,
    default: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    """Return a comma-separated environment variable as a list of strings.

    Args:
        name: The name of the environment variable.
        default: The default sequence to use if the variable is missing.
        environ: Optional mapping to use instead of `os.environ`.

    Returns:
        A list of strings split by commas.

    Examples:
        >>> get_env_list("HOSTS", environ={"HOSTS": "a,b, c "})
        ['a', 'b', 'c']
        >>> get_env_list("MISSING", environ={})
        []
        >>> get_env_list("MISSING", default=["local"], environ={})
        ['local']

    """
    env = os.environ if environ is None else environ
    raw_value = env.get(name)
    if raw_value is None:
        return [] if default is None else list(default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def get_env_int(
    name: str,
    *,
    default: int,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Return an environment variable as an integer.

    Args:
        name: The name of the environment variable.
        default: The default value to return if the variable is missing.
        environ: Optional mapping to use instead of `os.environ`.

    Returns:
        The integer value of the environment variable.

    Raises:
        ImproperlyConfigured: If the value cannot be parsed as an integer.

    Examples:
        >>> get_env_int("PORT", default=8000, environ={"PORT": "8080"})
        8080
        >>> get_env_int("PORT", default=8000, environ={})
        8000

    """
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


def build_csp_policy(
    *,
    dev_mode: bool,
    dev_server_host: str,
    dev_server_port: int,
) -> dict[str, list[str]]:
    """Return the Content-Security-Policy directives for the current run mode.

    The served page loads every asset from the same origin once the frontend is
    built, so the policy is `'self'` throughout. Running against the Vite dev
    server is the exception: modules are fetched from its origin, single-file
    component styles arrive as injected inline `<style>` elements, and hot
    module replacement opens a websocket back to it. Those three relaxations
    apply to dev mode only and never reach a built deployment.

    Args:
        dev_mode: Whether assets are served by the Vite dev server.
        dev_server_host: Host the Vite dev server listens on.
        dev_server_port: Port the Vite dev server listens on.

    Returns:
        A mapping of CSP directive name to its list of source expressions,
        shaped for the `SECURE_CSP` setting.

    Examples:
        >>> policy = build_csp_policy(
        ...     dev_mode=False, dev_server_host="127.0.0.1", dev_server_port=3000
        ... )
        >>> policy["script-src"] == [CSP.SELF, CSP.NONCE]
        True

    """
    # CSP.NONCE only becomes a real source when a template actually reads
    # {{ csp_nonce }}; unused, the middleware drops the placeholder. Listing it
    # is what lets a page add an inline script without loosening the policy.
    script_src: list[str] = [CSP.SELF, CSP.NONCE]
    style_src: list[str] = [CSP.SELF, CSP.NONCE]
    connect_src: list[str] = [CSP.SELF]

    if dev_mode:
        http_origin = f"http://{dev_server_host}:{dev_server_port}"
        websocket_origin = f"ws://{dev_server_host}:{dev_server_port}"
        script_src.append(http_origin)
        style_src += [http_origin, CSP.UNSAFE_INLINE]
        connect_src += [http_origin, websocket_origin]

    return {
        "default-src": [CSP.SELF],
        "script-src": script_src,
        "style-src": style_src,
        "connect-src": connect_src,
        # Vite inlines small assets as data: URIs during the production build.
        "img-src": [CSP.SELF, "data:"],
        "font-src": [CSP.SELF, "data:"],
        "base-uri": [CSP.SELF],
        "form-action": [CSP.SELF],
        "frame-ancestors": [CSP.NONE],
        "object-src": [CSP.NONE],
    }


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
VITE_DEV_SERVER_HOST: str = os.environ.get("DJANGO_VITE_DEV_SERVER_HOST", "127.0.0.1")
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

# Content Security Policy (new in Django 6.0).
SECURE_CSP: dict[str, list[str]] = build_csp_policy(
    dev_mode=VITE_DEV_MODE,
    dev_server_host=VITE_DEV_SERVER_HOST,
    dev_server_port=VITE_DEV_SERVER_PORT,
)
SECURE_CSP_REPORT_ONLY: dict[str, list[str]] = {}
