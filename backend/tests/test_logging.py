"""Test suite for production logging configuration and LOG_LEVEL validation."""

import io
import logging
from typing import Any
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, SimpleTestCase, override_settings
from django.utils.log import AdminEmailHandler, ServerFormatter
from django.utils.log import configure_logging as django_configure_logging

from backend.tests.helpers import reload_prod_settings
from djangovue import settings as project_settings


class _LoggingCaptureMixin(SimpleTestCase):
    """Helper for applying a LOGGING dict with stderr redirected to a buffer."""

    def _restore_logging(self) -> None:
        """Restore the Django test runner's logging configuration."""
        django_configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)

    def _assert_no_admin_email_handler(self, *logger_names: str) -> None:
        """Assert that none of the named loggers attach `AdminEmailHandler`.

        Args:
            *logger_names: Logger names to inspect (use `""` for root).

        """
        for logger_name in logger_names:
            for handler in logging.getLogger(logger_name).handlers:
                self.assertNotIsInstance(handler, AdminEmailHandler)

    def _capture_logging_stderr(self, logging_config: dict[str, Any]) -> io.StringIO:
        """Apply a logging config with stderr redirected to an in-memory buffer.

        Applies `DEFAULT_LOGGING` first and then `logging_config`, mirroring
        Django startup, and registers cleanups to restore `sys.stderr` and the
        original logging configuration in the right order.

        Args:
            logging_config: DictConfig mapping to apply on top of
                `DEFAULT_LOGGING`.

        Returns:
            The `StringIO` buffer bound to the configured stream handlers.

        """
        stream = io.StringIO()
        # Registered before the stderr patch so teardown restores sys.stderr
        # first and only then re-binds handlers back to the real stderr.
        self.addCleanup(self._restore_logging)
        self.enterContext(mock.patch("sys.stderr", stream))
        django_configure_logging("logging.config.dictConfig", logging_config)
        return stream


class LogLevelConfigTest(SimpleTestCase):
    """Test parsing and validation of the LOG_LEVEL setting."""

    def test_log_level_normalises_and_defaults(self) -> None:
        """Intent: LOG_LEVEL defaults to INFO and applies case-insensitive valid levels.

        Steps:
            1. Parse every valid standard level in mixed case.
            2. Reload production settings with LOG_LEVEL unset and blank.
            3. Reload production settings with LOG_LEVEL="warning".

        Verification:
            Valid levels normalise to uppercase, unset/blank fall back to
            INFO, and LOG_LEVEL="warning" updates root and Django loggers.
        """
        cases = (
            ("debug", "DEBUG"),
            ("Info", "INFO"),
            (" warning ", "WARNING"),
            ("ERROR", "ERROR"),
            ("CrItIcAl", "CRITICAL"),
        )
        for raw_value, expected in cases:
            with self.subTest(raw_value=raw_value):
                self.assertEqual(project_settings.parse_log_level(raw_value), expected)

        for extra_env in (None, {"LOG_LEVEL": "   "}):
            with self.subTest(extra_env=extra_env):
                reload_prod_settings(self, extra_env)
                self.assertEqual(project_settings.LOG_LEVEL, "INFO")
                self.assertEqual(project_settings.LOGGING["root"]["level"], "INFO")

        reload_prod_settings(self, {"LOG_LEVEL": "warning"})
        self.assertEqual(project_settings.LOG_LEVEL, "WARNING")
        self.assertEqual(project_settings.LOGGING["root"]["level"], "WARNING")
        for logger_name in ("django", "django.request", "django.security"):
            self.assertEqual(
                project_settings.LOGGING["loggers"][logger_name]["level"],
                "WARNING",
            )

    def test_log_level_rejects_invalid_values(self) -> None:
        """Intent: invalid LOG_LEVEL values stop startup with ImproperlyConfigured.

        Steps:
            1. Pass invalid level strings to `parse_log_level`.
            2. Reload settings with LOG_LEVEL="VERBOSE".

        Verification:
            Each invalid value raises ImproperlyConfigured naming LOG_LEVEL.
        """
        for invalid in ("VERBOSE", "WARN", "NOTSET", "10", ""):
            with self.subTest(invalid=invalid):
                with self.assertRaisesMessage(ImproperlyConfigured, "LOG_LEVEL"):
                    project_settings.parse_log_level(invalid)

        with self.assertRaisesMessage(ImproperlyConfigured, "LOG_LEVEL"):
            reload_prod_settings(self, {"LOG_LEVEL": "VERBOSE"})


class ProductionLoggingConfigTest(_LoggingCaptureMixin):
    """Test that Django and application logs reach stderr when DEBUG is off."""

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["example.com"])
    def test_disallowed_host_logs_when_debug_is_false(self) -> None:
        """Intent: a DisallowedHost rejection logs once to stderr when DEBUG=False.

        Steps:
            1. Reload production settings and apply LOGGING with captured
               stderr while DEBUG=False and ALLOWED_HOSTS=["example.com"].
            2. GET "/" with a disallowed Host header.

        Verification:
            The response is 400, django.security has no AdminEmailHandler, and
            stderr records the DisallowedHost error once.
        """
        reload_prod_settings(self)
        stream = self._capture_logging_stderr(project_settings.LOGGING)
        self._assert_no_admin_email_handler("django.security")

        response = self.client.get("/", headers={"Host": "evil.example"})

        self.assertEqual(response.status_code, 400)
        output = stream.getvalue()
        self.assertEqual(output.count("ERROR django.security.DisallowedHost:"), 1)
        self.assertIn("Invalid HTTP_HOST header", output)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_unhandled_500_logs_when_debug_is_false(self) -> None:
        """Intent: an unhandled 500 view exception logs its traceback once when DEBUG=False.

        Steps:
            1. Reload production settings and apply LOGGING with captured
               stderr while DEBUG=False.
            2. Patch backend.views.render to raise RuntimeError and GET "/"
               with a client that returns 500 responses instead of re-raising.

        Verification:
            The response is 500, django.request has no AdminEmailHandler, and
            stderr contains the django.request error and traceback once.
        """
        reload_prod_settings(self)
        stream = self._capture_logging_stderr(project_settings.LOGGING)
        self._assert_no_admin_email_handler("django.request")
        client = Client(raise_request_exception=False)

        with mock.patch("backend.views.render", side_effect=RuntimeError("boom")):
            response = client.get("/")

        self.assertEqual(response.status_code, 500)
        output = stream.getvalue()
        self.assertEqual(
            output.count("ERROR django.request: Internal Server Error: /"), 1
        )
        self.assertIn("RuntimeError: boom", output)

    @override_settings(DEBUG=False)
    def test_app_logger_emits_when_debug_is_false(self) -> None:
        """Intent: application loggers reach stderr once via the root logger when DEBUG=False.

        Steps:
            1. Reload production settings and apply LOGGING with captured
               stderr.
            2. Log an INFO message on an application logger ("backend.views").

        Verification:
            Neither root nor django attaches AdminEmailHandler, and the
            message, severity, and logger name appear once in stderr.
        """
        reload_prod_settings(self)
        stream = self._capture_logging_stderr(project_settings.LOGGING)
        self._assert_no_admin_email_handler("", "django")

        logging.getLogger("backend.views").info("application startup event")

        output = stream.getvalue()
        self.assertEqual(output.count("application startup event"), 1)
        self.assertIn("INFO", output)
        self.assertIn("backend.views", output)

    @override_settings(DEBUG=False)
    def test_log_level_controls_stderr_threshold(self) -> None:
        """Intent: LOG_LEVEL filters lower-severity logs and allows DEBUG when lowered.

        Steps:
            1. Reload with LOG_LEVEL=WARNING and emit INFO and WARNING records
               on django.request and backend.views.
            2. Reload with LOG_LEVEL=DEBUG and emit a DEBUG record on
               backend.views.

        Verification:
            INFO records are suppressed at WARNING while WARNING emits once
            each, and DEBUG emits once at DEBUG.
        """
        reload_prod_settings(self, {"LOG_LEVEL": "WARNING"})
        warning_stream = self._capture_logging_stderr(project_settings.LOGGING)
        logging.getLogger("django.request").info("suppressed request info")
        logging.getLogger("django.request").warning("kept request warning")
        logging.getLogger("backend.views").info("suppressed app info")
        logging.getLogger("backend.views").warning("kept app warning")

        warning_output = warning_stream.getvalue()
        self.assertNotIn("suppressed request info", warning_output)
        self.assertNotIn("suppressed app info", warning_output)
        self.assertEqual(warning_output.count("kept request warning"), 1)
        self.assertEqual(warning_output.count("kept app warning"), 1)

        reload_prod_settings(self, {"LOG_LEVEL": "DEBUG"})
        debug_stream = self._capture_logging_stderr(project_settings.LOGGING)
        logging.getLogger("backend.views").debug("verbose diagnostic trace")

        debug_output = debug_stream.getvalue()
        self.assertEqual(debug_output.count("verbose diagnostic trace"), 1)
        self.assertIn("DEBUG", debug_output)

    def test_django_server_preserves_server_formatter(self) -> None:
        """Intent: runserver logging keeps ServerFormatter without duplication.

        Steps:
            1. Reload production settings and apply LOGGING over
               DEFAULT_LOGGING with captured stderr.
            2. Inspect django.server and emit an INFO record on it.

        Verification:
            django.server does not propagate, uses ServerFormatter, and emits
            the record once.
        """
        reload_prod_settings(self)
        stream = self._capture_logging_stderr(project_settings.LOGGING)

        server_logger = logging.getLogger("django.server")
        self.assertFalse(server_logger.propagate)
        self.assertEqual(len(server_logger.handlers), 1)
        self.assertIsInstance(server_logger.handlers[0].formatter, ServerFormatter)

        server_logger.info('"GET / HTTP/1.1" 200 42')
        output = stream.getvalue()
        self.assertEqual(output.count('"GET / HTTP/1.1" 200 42'), 1)
