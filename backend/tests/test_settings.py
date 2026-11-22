"""Test suite for settings wiring and environment parsing helpers."""

import tempfile
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from backend.tests.helpers import reload_prod_settings, reload_settings
from djangovue import env
from djangovue import settings as project_settings


class SettingsModuleTest(SimpleTestCase):
    """Test module-level settings evaluations."""

    def test_missing_secret_key_raises_error(self) -> None:
        """Intent: a missing SECRET_KEY raises ImproperlyConfigured.

        Steps:
            1. Reload settings under an empty environment.

        Verification:
            ImproperlyConfigured is raised naming SECRET_KEY.
        """
        with self.assertRaisesMessage(
            ImproperlyConfigured, "SECRET_KEY environment variable must be set"
        ):
            reload_settings(self, {})

    def test_env_example_sqlite_path_is_absolute(self) -> None:
        """Intent: the shipped .env.example keeps SQLite in the project root.

        Steps:
            1. Read .env.example into an empty environment.
            2. Reload the settings module under that environment alone.

        Verification:
            The default database file is BASE_DIR/db.sqlite3 rather than a
            working-directory-relative path.
        """
        environ: dict[str, str] = {}
        env.load_env_file(project_settings.BASE_DIR / ".env.example", environ=environ)
        reload_settings(self, environ)
        self.assertEqual(
            project_settings.DATABASES["default"]["NAME"],
            str(project_settings.BASE_DIR / "db.sqlite3"),
        )

    def test_blank_allowed_hosts_uses_debug_defaults(self) -> None:
        """Intent: a blank ALLOWED_HOSTS under DEBUG=1 uses the dev defaults.

        Steps:
            1. Reload settings with SECRET_KEY, DEBUG="1", and ALLOWED_HOSTS="".

        Verification:
            ALLOWED_HOSTS equals ["localhost", "127.0.0.1", "0.0.0.0"].
        """
        reload_settings(
            self,
            {
                "SECRET_KEY": "test-secret-key",
                "DEBUG": "1",
                "ALLOWED_HOSTS": "",
            },
        )
        self.assertEqual(
            project_settings.ALLOWED_HOSTS,
            ["localhost", "127.0.0.1", "0.0.0.0"],
        )

    def test_blank_allowed_hosts_raises_when_debug_off(self) -> None:
        """Intent: a blank ALLOWED_HOSTS under DEBUG=0 stops startup.

        Steps:
            1. Reload settings with SECRET_KEY, DEBUG="0", and ALLOWED_HOSTS="".

        Verification:
            ImproperlyConfigured is raised naming ALLOWED_HOSTS.
        """
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "ALLOWED_HOSTS must be set when DEBUG is disabled",
        ):
            reload_settings(
                self,
                {
                    "SECRET_KEY": "test-secret-key",
                    "DEBUG": "0",
                    "ALLOWED_HOSTS": "",
                },
            )

    def test_database_url_and_conn_max_age_wiring(self) -> None:
        """Intent: DATABASE_URL and DB_CONN_MAX_AGE configure the default database.

        Steps:
            1. Reload production settings with DATABASE_URL="sqlite:///:memory:"
               and DB_CONN_MAX_AGE="120".

        Verification:
            The default database uses ":memory:" with CONN_MAX_AGE set to 120.
        """
        reload_prod_settings(
            self,
            {
                "DATABASE_URL": "sqlite:///:memory:",
                "DB_CONN_MAX_AGE": "120",
            },
        )
        self.assertEqual(project_settings.DATABASES["default"]["NAME"], ":memory:")
        self.assertEqual(project_settings.DATABASES["default"]["CONN_MAX_AGE"], 120)

    def test_production_security_settings_wiring(self) -> None:
        """Intent: environment flags wire proxy SSL, secure cookies, redirects, and CSRF origins.

        Steps:
            1. Reload production settings with defaults only.
            2. Reload with USE_X_FORWARDED_PROTO, SECURE_SSL_REDIRECT, and
               CSRF_TRUSTED_ORIGINS enabled.
            3. Reload with DEBUG="1".

        Verification:
            Secure cookies track `not DEBUG`, proxy SSL header toggles with
            USE_X_FORWARDED_PROTO, and SSL redirect and CSRF origins match env.
        """
        reload_prod_settings(self)
        self.assertFalse(project_settings.DEBUG)
        self.assertTrue(project_settings.SESSION_COOKIE_SECURE)
        self.assertTrue(project_settings.CSRF_COOKIE_SECURE)
        self.assertIsNone(project_settings.SECURE_PROXY_SSL_HEADER)
        self.assertFalse(project_settings.SECURE_SSL_REDIRECT)
        self.assertEqual(project_settings.CSRF_TRUSTED_ORIGINS, [])

        reload_prod_settings(
            self,
            {
                "USE_X_FORWARDED_PROTO": "1",
                "SECURE_SSL_REDIRECT": "1",
                "CSRF_TRUSTED_ORIGINS": (
                    "https://app.example.com, https://admin.example.com"
                ),
            },
        )
        self.assertEqual(
            project_settings.SECURE_PROXY_SSL_HEADER,
            ("HTTP_X_FORWARDED_PROTO", "https"),
        )
        self.assertTrue(project_settings.SECURE_SSL_REDIRECT)
        self.assertEqual(
            project_settings.CSRF_TRUSTED_ORIGINS,
            ["https://app.example.com", "https://admin.example.com"],
        )

        reload_prod_settings(self, {"DEBUG": "1"})
        self.assertFalse(project_settings.SESSION_COOKIE_SECURE)
        self.assertFalse(project_settings.CSRF_COOKIE_SECURE)

    def test_hsts_preload_validation_runs_on_import(self) -> None:
        """Intent: enabling SECURE_HSTS_PRELOAD without required HSTS settings fails startup.

        Steps:
            1. Reload production settings with SECURE_HSTS_PRELOAD="1" and
               default zeroed HSTS max-age/subdomains.

        Verification:
            ImproperlyConfigured is raised naming SECURE_HSTS_PRELOAD.
        """
        with self.assertRaisesMessage(ImproperlyConfigured, "SECURE_HSTS_PRELOAD"):
            reload_prod_settings(self, {"SECURE_HSTS_PRELOAD": "1"})

    def test_vite_dev_ipv6_wires_into_vite_and_csp(self) -> None:
        """Intent: an IPv6 Vite dev host is bracketed identically in DJANGO_VITE and SECURE_CSP.

        Steps:
            1. Reload settings with DJANGO_VITE_DEV_MODE="1",
               DJANGO_VITE_DEV_SERVER_HOST="::1", and port 5173.

        Verification:
            DJANGO_VITE uses "[::1]" on port 5173, and SECURE_CSP allows
            http://[::1]:5173 and ws://[::1]:5173.
        """
        reload_prod_settings(
            self,
            {
                "DJANGO_VITE_DEV_MODE": "1",
                "DJANGO_VITE_DEV_SERVER_HOST": "::1",
                "DJANGO_VITE_DEV_SERVER_PORT": "5173",
            },
        )
        vite_cfg = project_settings.DJANGO_VITE["default"]
        self.assertTrue(vite_cfg["dev_mode"])
        self.assertEqual(vite_cfg["dev_server_host"], "[::1]")
        self.assertEqual(vite_cfg["dev_server_port"], 5173)
        self.assertIn(
            "http://[::1]:5173",
            project_settings.SECURE_CSP["script-src"],
        )
        self.assertIn(
            "ws://[::1]:5173",
            project_settings.SECURE_CSP["connect-src"],
        )


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

    def test_load_applies_only_undefined_valued_keys(self) -> None:
        """Intent: .env fills missing keys without overwriting existing env or valueless entries.

        Steps:
            1. Write a .env defining DEBUG, ALLOWED_HOSTS, and a bare key
               without an `=` value.
            2. Load it into an environment that already defines DEBUG.

        Verification:
            DEBUG keeps its existing value, ALLOWED_HOSTS is applied, the
            valueless key is skipped, and only ALLOWED_HOSTS is returned.
        """
        environ = {"DEBUG": "0"}
        applied = env.load_env_file(
            self._write_env("DEBUG=1\nALLOWED_HOSTS=example.com\nNO_VALUE\n"),
            environ=environ,
        )
        self.assertEqual(environ, {"DEBUG": "0", "ALLOWED_HOSTS": "example.com"})
        self.assertEqual(applied, {"ALLOWED_HOSTS": "example.com"})

    def test_load_handles_utf8_bom(self) -> None:
        """Intent: a .env file with a UTF-8 Byte Order Mark (BOM) is parsed cleanly.

        Steps:
            1. Write a BOM-prefixed .env file defining SECRET_KEY.
            2. Load it into a clean environment.

        Verification:
            The BOM is stripped and SECRET_KEY is loaded properly.
        """
        environ: dict[str, str] = {}
        applied = env.load_env_file(
            self._write_env("\ufeffSECRET_KEY=123\n"), environ=environ
        )
        self.assertEqual(environ, {"SECRET_KEY": "123"})
        self.assertEqual(applied, {"SECRET_KEY": "123"})

    def test_load_ignores_missing_or_unreadable_paths(self) -> None:
        """Intent: missing, empty, directory, or invalid-UTF-8 paths are safely ignored.

        Steps:
            1. Call load_env_file on a missing path, an empty file, a
               directory, and a file containing invalid UTF-8 bytes.

        Verification:
            Each returns an empty dict without raising or mutating environ.
        """
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        empty_file = self._write_env("")
        bad_utf8 = self._write_env("")
        bad_utf8.write_bytes(b"\x80abc")

        cases: tuple[tuple[str, Path | str], ...] = (
            ("missing", Path("no-such-directory/.env")),
            ("empty", empty_file),
            ("directory", directory.name),
            ("invalid_utf8", bad_utf8),
        )
        for label, path in cases:
            with self.subTest(case=label):
                environ = {"DEBUG": "0"}
                applied = env.load_env_file(path, environ=environ)
                self.assertEqual(applied, {})
                self.assertEqual(environ, {"DEBUG": "0"})


class SettingsHelpersTest(SimpleTestCase):
    """Test environment parsing helpers used by project settings."""

    def test_get_env_bool_parses_values_and_defaults(self) -> None:
        """Intent: get_env_bool parses accepted spellings and falls back when unset or blank.

        Steps:
            1. Read every accepted truthy and falsy spelling (including mixed
               case and surrounding whitespace).
            2. Read missing and whitespace-only values with default False/True.

        Verification:
            Accepted spellings return their booleans and unset/blank values
            return the default.
        """
        for value in ("1", "true", "t", "yes", "y", "on", " TRUE ", "Yes"):
            with self.subTest(truthy=value):
                self.assertTrue(env.get_env_bool("FLAG", environ={"FLAG": value}))

        for value in ("0", "false", "f", "no", "n", "off", " OFF ", "False"):
            with self.subTest(falsy=value):
                self.assertFalse(env.get_env_bool("FLAG", environ={"FLAG": value}))

        self.assertFalse(env.get_env_bool("FLAG", environ={}))
        self.assertTrue(env.get_env_bool("FLAG", default=True, environ={}))
        self.assertTrue(env.get_env_bool("FLAG", default=True, environ={"FLAG": "  "}))

    def test_get_env_bool_rejects_unknown_values(self) -> None:
        """Intent: a typo in a boolean setting stops startup rather than reading False.

        Steps:
            1. Read SECURE_SSL_REDIRECT set to unrecognised strings.

        Verification:
            Each raises ImproperlyConfigured naming the variable.
        """
        for value in ("ture", "enabled", "2"):
            with self.subTest(value=value):
                with self.assertRaisesMessage(
                    ImproperlyConfigured, "SECURE_SSL_REDIRECT"
                ):
                    env.get_env_bool(
                        "SECURE_SSL_REDIRECT",
                        environ={"SECURE_SSL_REDIRECT": value},
                    )

    def test_get_env_list_splits_and_uses_defaults(self) -> None:
        """Intent: get_env_list splits clean items and returns a fresh default when unset or blank.

        Steps:
            1. Parse comma-separated values with whitespace and empty entries.
            2. Read missing and blank values both with and without defaults.

        Verification:
            Items are trimmed with empty segments dropped, missing/blank
            values return an empty list or a fresh list copy of default.
        """
        self.assertEqual(
            env.get_env_list(
                "ALLOWED_HOSTS",
                environ={"ALLOWED_HOSTS": "example.com, , api.example.com,"},
            ),
            ["example.com", "api.example.com"],
        )
        self.assertEqual(env.get_env_list("MISSING", environ={}), [])
        self.assertEqual(
            env.get_env_list("MISSING", default=("a", "b"), environ={}),
            ["a", "b"],
        )

        default = ["localhost", "127.0.0.1"]
        for value in ("", "   "):
            with self.subTest(blank=value):
                self.assertEqual(
                    env.get_env_list("ITEMS", environ={"ITEMS": value}),
                    [],
                )
                result = env.get_env_list(
                    "ITEMS", default=default, environ={"ITEMS": value}
                )
                self.assertEqual(result, default)
                self.assertIsNot(result, default)

    def test_get_env_str_strips_and_falls_back(self) -> None:
        """Intent: get_env_str trims surrounding whitespace and falls back when unset or blank.

        Steps:
            1. Read a padded string, a missing variable, and blank values.

        Verification:
            The padded string is stripped and missing/blank inputs return the
            default.
        """
        cases: tuple[tuple[dict[str, str], str], ...] = (
            ({"HOST": "  ::1  "}, "::1"),
            ({}, "127.0.0.1"),
            ({"HOST": ""}, "127.0.0.1"),
            ({"HOST": "   "}, "127.0.0.1"),
        )
        for environ, expected in cases:
            with self.subTest(environ=environ):
                self.assertEqual(
                    env.get_env_str("HOST", default="127.0.0.1", environ=environ),
                    expected,
                )

    def test_get_env_int_parses_and_falls_back(self) -> None:
        """Intent: get_env_int parses trimmed integers including zero and falls back on blanks.

        Steps:
            1. Read positive, padded, zero, negative, missing, and blank
               values.

        Verification:
            Numeric values parse to ints and missing/blank inputs return the
            default.
        """
        cases: tuple[tuple[dict[str, str], int], ...] = (
            ({"PORT": "120"}, 120),
            ({"PORT": " 120 "}, 120),
            ({"PORT": "0"}, 0),
            ({"PORT": "-5"}, -5),
            ({}, 60),
            ({"PORT": ""}, 60),
            ({"PORT": "   "}, 60),
        )
        for environ, expected in cases:
            with self.subTest(environ=environ):
                self.assertEqual(
                    env.get_env_int("PORT", default=60, environ=environ),
                    expected,
                )

    def test_get_env_int_raises_for_invalid_value(self) -> None:
        """Intent: a non-numeric integer setting stops startup with ImproperlyConfigured.

        Steps:
            1. Read DB_CONN_MAX_AGE set to non-integer strings.

        Verification:
            Each raises ImproperlyConfigured naming the variable.
        """
        for value in ("not-a-number", "3.14"):
            with self.subTest(value=value):
                with self.assertRaisesMessage(ImproperlyConfigured, "DB_CONN_MAX_AGE"):
                    env.get_env_int(
                        "DB_CONN_MAX_AGE",
                        default=60,
                        environ={"DB_CONN_MAX_AGE": value},
                    )
