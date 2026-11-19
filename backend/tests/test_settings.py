"""Test suite for settings and environment parsing helpers.

Author: Mike Borozdin (mikebz@)
"""

import importlib
import os
import tempfile
from pathlib import Path
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from djangovue import settings as project_settings
from djangovue import utils


class SettingsModuleTest(SimpleTestCase):
    """Test module-level settings evaluations."""

    def test_missing_secret_key_raises_error(self) -> None:
        """Intent: a missing SECRET_KEY raises ImproperlyConfigured.

        Steps:
            1. Clear the environment.
            2. Evaluate the settings module.

        Verification:
            It raises ImproperlyConfigured.
        """
        # The settings module loads .env before reading SECRET_KEY, so the
        # loader is stubbed out too - otherwise a developer's .env would
        # repopulate the environment this test just cleared.
        with mock.patch.object(utils, "load_env_file", return_value={}):
            with mock.patch.dict(os.environ, clear=True):
                with self.assertRaisesMessage(
                    ImproperlyConfigured, "SECRET_KEY environment variable must be set"
                ):
                    importlib.reload(project_settings)

        # Reload settings again with the original environment to restore state
        importlib.reload(project_settings)


class EnvFileLoadingTest(SimpleTestCase):
    """Test how a .env file is applied to the process environment."""

    def _write_env(self, contents: str) -> Path:
        """Write a .env file into a temporary directory for one test.

        Args:
            contents: The file contents to write.

        Returns:
            The path to the written file.

        """
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / ".env"
        path.write_text(contents, encoding="utf-8")
        return path

    def test_load_sets_undefined_variables(self) -> None:
        """Intent: .env supplies configuration the environment lacks.

        Steps:
            1. Write a .env file defining DEBUG.
            2. Load it into an environment that does not define DEBUG.

        Verification:
            The value from the file is applied and reported as applied.
        """
        environ: dict[str, str] = {}
        applied = utils.load_env_file(self._write_env("DEBUG=1\n"), environ=environ)
        self.assertEqual(environ, {"DEBUG": "1"})
        self.assertEqual(applied, {"DEBUG": "1"})

    def test_environment_wins_over_env_file(self) -> None:
        """Intent: a real environment variable overrides the .env file.

        Steps:
            1. Write a .env file defining DEBUG and ALLOWED_HOSTS.
            2. Load it into an environment that already defines DEBUG.

        Verification:
            DEBUG keeps the value it was given, ALLOWED_HOSTS comes from the
            file, and only the latter is reported as applied.
        """
        environ = {"DEBUG": "0"}
        applied = utils.load_env_file(
            self._write_env("DEBUG=1\nALLOWED_HOSTS=example.com\n"),
            environ=environ,
        )
        self.assertEqual(environ["DEBUG"], "0")
        self.assertEqual(environ["ALLOWED_HOSTS"], "example.com")
        self.assertEqual(applied, {"ALLOWED_HOSTS": "example.com"})

    def test_missing_env_file_is_not_an_error(self) -> None:
        """Intent: deployments configured purely by environment need no file.

        Steps:
            1. Load a path that does not exist.

        Verification:
            Nothing is applied and no exception is raised.
        """
        environ = {"DEBUG": "0"}
        applied = utils.load_env_file(Path("no-such-directory/.env"), environ=environ)
        self.assertEqual(applied, {})
        self.assertEqual(environ, {"DEBUG": "0"})

    def test_load_ignores_directory_as_file(self) -> None:
        """Intent: An OSError (e.g., path is a directory) is safely ignored.

        Steps:
            1. Pass a directory path instead of a file.

        Verification:
            The function catches IsADirectoryError (an OSError) and returns an empty dict.
        """
        environ: dict[str, str] = {}
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        applied = utils.load_env_file(directory.name, environ=environ)
        self.assertEqual(applied, {})

    def test_load_ignores_invalid_unicode(self) -> None:
        """Intent: A UnicodeDecodeError is safely ignored.

        Steps:
            1. Write a file with invalid UTF-8 bytes.
            2. Attempt to load it.

        Verification:
            The function catches UnicodeDecodeError and returns an empty dict.
        """
        environ: dict[str, str] = {}
        path = self._write_env("")
        path.write_bytes(b"\x80abc")
        applied = utils.load_env_file(path, environ=environ)
        self.assertEqual(applied, {})

    def test_load_handles_utf8_bom(self) -> None:
        """Intent: a .env file with a Byte Order Mark (BOM) is parsed correctly.

        Steps:
            1. Write a .env file defining SECRET_KEY, starting with a BOM.
            2. Load it into a clean environment.

        Verification:
            The BOM is stripped and the key is loaded properly.
        """
        environ: dict[str, str] = {}
        applied = utils.load_env_file(
            self._write_env("\ufeffSECRET_KEY=123\n"), environ=environ
        )
        self.assertEqual(environ, {"SECRET_KEY": "123"})
        self.assertEqual(applied, {"SECRET_KEY": "123"})


class SettingsHelpersTest(SimpleTestCase):
    """Test environment parsing helpers used by project settings."""

    def test_get_env_bool_defaults_when_missing(self) -> None:
        """Intent: an unset boolean variable falls back to its default.

        Steps:
            1. Read DEBUG from an empty environment without passing a default.

        Verification:
            The result is False.
        """
        self.assertFalse(utils.get_env_bool("DEBUG", environ={}))

    def test_get_env_bool_parses_truthy_values(self) -> None:
        """Intent: a documented true spelling reads as True.

        Steps:
            1. Read DEBUG set to "true".

        Verification:
            The result is True.
        """
        environ = {"DEBUG": "true"}
        self.assertTrue(utils.get_env_bool("DEBUG", environ=environ))

    def test_get_env_bool_parses_falsy_values(self) -> None:
        """Intent: the documented false spellings all read as False.

        Steps:
            1. Read DEBUG set to each accepted false spelling, in mixed case.

        Verification:
            Every one returns False.
        """
        for value in ["0", "false", "f", "no", "n", "off", "OFF", "False"]:
            with self.subTest(value=value):
                environ = {"DEBUG": value}
                self.assertFalse(utils.get_env_bool("DEBUG", environ=environ))

    def test_get_env_bool_rejects_unknown_values(self) -> None:
        """Intent: a typo in a boolean setting stops startup, not reads False.

        Steps:
            1. Read SECURE_SSL_REDIRECT set to "ture" and to "enabled".

        Verification:
            Each raises ImproperlyConfigured naming the variable, instead of
            quietly switching the redirect off.
        """
        for value in ["ture", "enabled"]:
            with self.subTest(value=value):
                environ = {"SECURE_SSL_REDIRECT": value}
                with self.assertRaisesMessage(
                    ImproperlyConfigured, "SECURE_SSL_REDIRECT"
                ):
                    utils.get_env_bool("SECURE_SSL_REDIRECT", environ=environ)

    def test_get_env_bool_blank_uses_default(self) -> None:
        """Intent: an empty assignment such as `DEBUG=` means "not set".

        Steps:
            1. Read DEBUG set to whitespace with a default of True.

        Verification:
            The default is returned, matching how get_env_str treats blanks.
        """
        environ = {"DEBUG": "  "}
        self.assertTrue(utils.get_env_bool("DEBUG", default=True, environ=environ))

    def test_get_env_list_splits_values(self) -> None:
        """Intent: a comma-separated variable becomes a list of clean items.

        Steps:
            1. Read ALLOWED_HOSTS set to "example.com, api.example.com".

        Verification:
            The result is both hosts, with surrounding whitespace trimmed.
        """
        environ = {"ALLOWED_HOSTS": "example.com, api.example.com"}
        self.assertEqual(
            utils.get_env_list("ALLOWED_HOSTS", environ=environ),
            ["example.com", "api.example.com"],
        )

    def test_get_env_list_returns_empty_when_missing(self) -> None:
        """Intent: an unset list variable with no default reads as empty.

        Steps:
            1. Read a missing variable with no default.

        Verification:
            The result is an empty list.
        """
        self.assertEqual(utils.get_env_list("MISSING", environ={}), [])

    def test_get_env_list_uses_default_when_missing(self) -> None:
        """Intent: an unset list variable falls back to its default as a list.

        Steps:
            1. Read a missing variable with the tuple default ("a", "b").

        Verification:
            The result is the list ["a", "b"].
        """
        self.assertEqual(
            utils.get_env_list("MISSING", default=("a", "b"), environ={}),
            ["a", "b"],
        )

    def test_get_env_str_uses_default_when_missing(self) -> None:
        """Intent: an unset string variable falls back to its default.

        Steps:
            1. Read HOST from an empty environment with default "127.0.0.1".

        Verification:
            The result is "127.0.0.1".
        """
        self.assertEqual(
            utils.get_env_str("HOST", default="127.0.0.1", environ={}),
            "127.0.0.1",
        )

    def test_get_env_str_strips_whitespace(self) -> None:
        """Intent: stray whitespace around a string value is ignored.

        Steps:
            1. Read HOST set to "  ::1  ".

        Verification:
            The result is "::1".
        """
        environ = {"HOST": "  ::1  "}
        self.assertEqual(
            utils.get_env_str("HOST", default="x", environ=environ),
            "::1",
        )

    def test_get_env_str_falls_back_when_blank(self) -> None:
        """Intent: a blank string value means "not set".

        Steps:
            1. Read HOST set to whitespace only, with default "127.0.0.1".

        Verification:
            The result is the default, "127.0.0.1".
        """
        environ = {"HOST": "   "}
        self.assertEqual(
            utils.get_env_str("HOST", default="127.0.0.1", environ=environ),
            "127.0.0.1",
        )

    def test_get_env_int_uses_default(self) -> None:
        """Intent: an unset integer variable falls back to its default.

        Steps:
            1. Read DB_CONN_MAX_AGE from an empty environment with default 60.

        Verification:
            The result is 60.
        """
        self.assertEqual(
            utils.get_env_int("DB_CONN_MAX_AGE", default=60, environ={}),
            60,
        )

    def test_get_env_int_parses_integer(self) -> None:
        """Intent: an integer variable is read as an int.

        Steps:
            1. Read DB_CONN_MAX_AGE set to "120".

        Verification:
            The result is the integer 120.
        """
        environ = {"DB_CONN_MAX_AGE": "120"}
        self.assertEqual(
            utils.get_env_int("DB_CONN_MAX_AGE", default=0, environ=environ),
            120,
        )

    def test_get_env_int_raises_for_invalid_value(self) -> None:
        """Intent: a non-numeric integer setting stops startup.

        Steps:
            1. Read DB_CONN_MAX_AGE set to "not-a-number".

        Verification:
            ImproperlyConfigured is raised.
        """
        environ = {"DB_CONN_MAX_AGE": "not-a-number"}
        with self.assertRaises(ImproperlyConfigured):
            utils.get_env_int("DB_CONN_MAX_AGE", default=60, environ=environ)
