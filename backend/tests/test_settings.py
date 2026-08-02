"""Test suite for settings and environment parsing helpers.

Author: Mike Borozdin (mikebz@)
"""

import importlib
import os
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from djangovue import settings as project_settings
from djangovue import utils


class SettingsModuleTest(SimpleTestCase):
    """Test module-level settings evaluations."""

    def test_missing_secret_key_raises_error(self) -> None:
        """GIVEN: A missing SECRET_KEY in the environment.

        WHEN: The settings module is evaluated
        THEN: It should raise ImproperlyConfigured
        """
        # We use mock.patch.dict to clear the environment for testing
        with mock.patch.dict(os.environ, clear=True):
            with self.assertRaisesMessage(
                ImproperlyConfigured, "SECRET_KEY environment variable must be set"
            ):
                importlib.reload(project_settings)

        # Reload settings again with the original environment to restore state
        importlib.reload(project_settings)


class SettingsHelpersTest(SimpleTestCase):
    """Test environment parsing helpers used by project settings."""

    def test_get_env_bool_defaults_when_missing(self) -> None:
        """Use the default bool when an environment variable is missing."""
        self.assertFalse(utils.get_env_bool("DEBUG", environ={}))

    def test_get_env_bool_parses_truthy_values(self) -> None:
        """Parse accepted truthy strings to True."""
        environ = {"DEBUG": "true"}
        self.assertTrue(utils.get_env_bool("DEBUG", environ=environ))

    def test_get_env_list_splits_values(self) -> None:
        """Split comma-separated list values and trim whitespace."""
        environ = {"ALLOWED_HOSTS": "example.com, api.example.com"}
        self.assertEqual(
            utils.get_env_list("ALLOWED_HOSTS", environ=environ),
            ["example.com", "api.example.com"],
        )

    def test_get_env_list_returns_empty_when_missing(self) -> None:
        """Return an empty list when an environment variable is missing and no default is provided."""
        self.assertEqual(utils.get_env_list("MISSING", environ={}), [])

    def test_get_env_list_uses_default_when_missing(self) -> None:
        """Return the default sequence as a list when an environment variable is missing."""
        self.assertEqual(
            utils.get_env_list("MISSING", default=("a", "b"), environ={}),
            ["a", "b"],
        )

    def test_get_env_str_uses_default_when_missing(self) -> None:
        """Return the default string when an environment variable is missing."""
        self.assertEqual(
            utils.get_env_str("HOST", default="127.0.0.1", environ={}),
            "127.0.0.1",
        )

    def test_get_env_str_strips_whitespace(self) -> None:
        """Trim surrounding whitespace from string values."""
        environ = {"HOST": "  ::1  "}
        self.assertEqual(
            utils.get_env_str("HOST", default="x", environ=environ),
            "::1",
        )

    def test_get_env_str_falls_back_when_blank(self) -> None:
        """Treat a blank value as absent and use the default."""
        environ = {"HOST": "   "}
        self.assertEqual(
            utils.get_env_str("HOST", default="127.0.0.1", environ=environ),
            "127.0.0.1",
        )

    def test_get_env_int_uses_default(self) -> None:
        """Use the default integer when an environment variable is missing."""
        self.assertEqual(
            utils.get_env_int("DB_CONN_MAX_AGE", default=60, environ={}),
            60,
        )

    def test_get_env_int_parses_integer(self) -> None:
        """Parse integer values from environment variables."""
        environ = {"DB_CONN_MAX_AGE": "120"}
        self.assertEqual(
            utils.get_env_int("DB_CONN_MAX_AGE", default=0, environ=environ),
            120,
        )

    def test_get_env_int_raises_for_invalid_value(self) -> None:
        """Raise ImproperlyConfigured for non-integer environment values."""
        environ = {"DB_CONN_MAX_AGE": "not-a-number"}
        with self.assertRaises(ImproperlyConfigured):
            utils.get_env_int("DB_CONN_MAX_AGE", default=60, environ=environ)
