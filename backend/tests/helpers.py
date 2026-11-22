"""Shared test helpers for reloading Django settings safely."""

import importlib
import os
import unittest
from collections.abc import Mapping
from unittest import mock

from djangovue import env
from djangovue import settings as project_settings

PROD_BASE_ENV: dict[str, str] = {
    "SECRET_KEY": "test-secret-key",
    "DEBUG": "0",
    "ALLOWED_HOSTS": "example.com",
}


def reload_settings(
    test_case: unittest.TestCase,
    environ: Mapping[str, str],
) -> None:
    """Reload `djangovue.settings` under an isolated environment mapping.

    Stubs out `.env` loading so a developer's local `.env` cannot leak into the
    reloaded module, and registers a cleanup on `test_case` to restore settings
    under the real environment even if the reload raises.

    Args:
        test_case: Running test case used to register the restore cleanup.
        environ: Exact environment mapping to expose while reloading settings.

    """
    test_case.addCleanup(importlib.reload, project_settings)
    with mock.patch.object(env, "load_env_file", return_value={}):
        with mock.patch.dict(os.environ, dict(environ), clear=True):
            importlib.reload(project_settings)


def reload_prod_settings(
    test_case: unittest.TestCase,
    extra_env: Mapping[str, str] | None = None,
) -> None:
    """Reload `djangovue.settings` under a minimal production environment.

    Args:
        test_case: Running test case used to register the restore cleanup.
        extra_env: Optional variables merged on top of `PROD_BASE_ENV`.

    """
    reload_settings(test_case, {**PROD_BASE_ENV, **(extra_env or {})})
