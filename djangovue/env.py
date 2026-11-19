"""Environment configuration helpers for the settings module.

Loads .env without overriding the real environment, and reads variables as
typed values. Each reader takes an optional `environ` mapping so tests can
exercise it without touching `os.environ`.

Author: Mike Borozdin (mikebz@)
"""

import os
from collections.abc import Mapping, MutableMapping, Sequence
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import dotenv_values


def load_env_file(
    path: Path | str,
    *,
    environ: MutableMapping[str, str] | None = None,
) -> dict[str, str]:
    """Apply a .env file to the environment without overwriting it.

    A variable that is already set wins over the file, so a shell export, a
    `docker run -e` flag, or a compose `environment:` entry overrides a single
    key without anyone editing .env. A missing file is not an error: the file
    is a convenience for local development, and deployments that pass real
    environment variables never need one.

    Args:
        path: Path to the .env file.
        environ: Optional mapping to update instead of `os.environ`.

    Returns:
        The variables actually applied - those the environment did not
        already define.

    Examples:
        >>> load_env_file("does-not-exist.env", environ={})
        {}

    """
    env = os.environ if environ is None else environ
    try:
        parsed = dotenv_values(path, encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return {}

    if not parsed:
        return {}

    applied = {
        name: value
        for name, value in parsed.items()
        if name not in env and value is not None
    }
    env.update(applied)
    return applied


def _get_env_value(
    name: str,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Return the raw value of an environment variable.

    Args:
        name: The name of the environment variable.
        environ: Optional mapping to use instead of `os.environ`.

    Returns:
        The raw string value of the environment variable, or None if missing.

    """
    env = os.environ if environ is None else environ
    return env.get(name)


_TRUTHY_STRINGS: frozenset[str] = frozenset({"1", "true", "t", "yes", "y", "on"})
_FALSY_STRINGS: frozenset[str] = frozenset({"0", "false", "f", "no", "n", "off"})


def get_env_bool(
    name: str,
    *,
    default: bool = False,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return an environment variable as a boolean.

    Anything outside the accepted spellings is an error rather than False, so
    a typo such as `SECURE_SSL_REDIRECT=ture` stops startup instead of quietly
    turning a security setting off.

    Args:
        name: The name of the environment variable.
        default: The default value to return if the variable is missing or blank.
        environ: Optional mapping to use instead of `os.environ`.

    Returns:
        The evaluated boolean value of the environment variable.

    Raises:
        ImproperlyConfigured: If the value is not a recognised boolean.

    Examples:
        >>> get_env_bool("DEBUG", environ={"DEBUG": "1"})
        True
        >>> get_env_bool("DEBUG", environ={"DEBUG": "false"})
        False
        >>> get_env_bool("MISSING", default=True, environ={})
        True

    """
    raw_value = _get_env_value(name, environ)
    if raw_value is None or not raw_value.strip():
        return default
    value = raw_value.strip().lower()
    if value in _TRUTHY_STRINGS:
        return True
    if value in _FALSY_STRINGS:
        return False
    raise ImproperlyConfigured(
        f"{name} must be one of 1/0, true/false, t/f, yes/no, y/n, on/off, "
        f"got {raw_value!r}"
    )


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
    raw_value = _get_env_value(name, environ)
    if raw_value is None:
        return [] if default is None else list(default)
    return [s for s in map(str.strip, raw_value.split(",")) if s]


def get_env_str(
    name: str,
    *,
    default: str,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return an environment variable as a string.

    Args:
        name: The name of the environment variable.
        default: The default value to return if the variable is missing or blank.
        environ: Optional mapping to use instead of `os.environ`.

    Returns:
        The stripped value of the environment variable, or the default.

    Examples:
        >>> get_env_str("HOST", default="127.0.0.1", environ={"HOST": " ::1 "})
        '::1'
        >>> get_env_str("HOST", default="127.0.0.1", environ={})
        '127.0.0.1'
        >>> get_env_str("HOST", default="127.0.0.1", environ={"HOST": ""})
        '127.0.0.1'

    """
    raw_value = _get_env_value(name, environ)
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value.strip()


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
    raw_value = _get_env_value(name, environ)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"{name} must be an integer, got {raw_value!r}"
        ) from exc
