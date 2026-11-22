"""Test suite for production logging configuration and LOG_LEVEL validation."""

import importlib
import io
import logging
import os
from collections.abc import Mapping
from typing import Any
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, SimpleTestCase, override_settings
from django.utils.log import AdminEmailHandler, RequireDebugTrue, ServerFormatter
from django.utils.log import configure_logging as django_configure_logging

from djangovue import env
from djangovue import settings as project_settings

_PROD_BASE_ENV: dict[str, str] = {
    "SECRET_KEY": "test-secret-key",
    "DEBUG": "0",
    "ALLOWED_HOSTS": "example.com",
}


class _LoggingReloadMixin(SimpleTestCase):
    """Helpers for reloading settings and capturing configured logging output."""

    def _reload_settings(self, extra_env: Mapping[str, str] | None = None) -> None:
        """Reload `djangovue.settings` under a controlled production environment.

        Registers a cleanup to reload the settings module under the real
        environment afterwards so no module-level state leaks between tests.

        Args:
            extra_env: Additional environment variables merged on top of the
                minimal production environment.

        """
        environ = {**_PROD_BASE_ENV, **(extra_env or {})}
        self.addCleanup(importlib.reload, project_settings)
        with mock.patch.object(env, "load_env_file", return_value={}):
            with mock.patch.dict(os.environ, environ, clear=True):
                importlib.reload(project_settings)

    def _restore_logging(self) -> None:
        """Restore the Django test runner's logging configuration."""
        django_configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)

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


class LogLevelConfigTest(_LoggingReloadMixin):
    """Test parsing and validation of the LOG_LEVEL setting."""

    def test_log_level_defaults_to_info(self) -> None:
        """Intent: LOG_LEVEL defaults to INFO when unset in the environment.

        Steps:
            1. Reload settings under a production environment without LOG_LEVEL.

        Verification:
            LOG_LEVEL is "INFO" and the root logger uses "INFO".
        """
        self._reload_settings()
        self.assertEqual(project_settings.LOG_LEVEL, "INFO")
        self.assertEqual(project_settings.LOGGING["root"]["level"], "INFO")

    def test_log_level_blank_defaults_to_info(self) -> None:
        """Intent: a blank LOG_LEVEL value falls back to INFO.

        Steps:
            1. Reload settings with LOG_LEVEL set to whitespace only.

        Verification:
            LOG_LEVEL evaluates to "INFO".
        """
        self._reload_settings({"LOG_LEVEL": "   "})
        self.assertEqual(project_settings.LOG_LEVEL, "INFO")

    def test_log_level_accepts_case_insensitive_levels(self) -> None:
        """Intent: LOG_LEVEL accepts all standard level names regardless of case.

        Steps:
            1. Parse each valid level name in mixed/lower case via
               `parse_log_level`.
            2. Reload settings with LOG_LEVEL="warning".

        Verification:
            Every valid level normalises to uppercase, and the reloaded
            LOGGING dict applies "WARNING" to root, django, django.request,
            and django.security.
        """
        cases = (
            ("debug", "DEBUG"),
            ("Info", "INFO"),
            ("warning", "WARNING"),
            ("ERROR", "ERROR"),
            ("CrItIcAl", "CRITICAL"),
        )
        for raw_value, expected in cases:
            with self.subTest(raw_value=raw_value):
                self.assertEqual(project_settings.parse_log_level(raw_value), expected)

        self._reload_settings({"LOG_LEVEL": "warning"})
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
            self._reload_settings({"LOG_LEVEL": "VERBOSE"})


class ProductionLoggingConfigTest(_LoggingReloadMixin):
    """Test that Django and application logs reach stderr when DEBUG is off."""

    def test_console_handler_has_no_debug_filter(self) -> None:
        """Intent: production loggers write to stderr without debug filters or email.

        Steps:
            1. Reload settings under DEBUG=0 and apply LOGGING over
               DEFAULT_LOGGING.
            2. Inspect the handlers attached to root, django, django.request,
               and django.security.

        Verification:
            Each logger uses a StreamHandler with no RequireDebugTrue filter
            and no AdminEmailHandler.
        """
        self._reload_settings()
        self._capture_logging_stderr(project_settings.LOGGING)

        for logger_name in ("", "django", "django.request", "django.security"):
            with self.subTest(logger_name=logger_name or "<root>"):
                logger = logging.getLogger(logger_name)
                self.assertTrue(logger.handlers)
                if logger_name:
                    self.assertFalse(logger.propagate)
                for handler in logger.handlers:
                    self.assertIsInstance(handler, logging.StreamHandler)
                    self.assertNotIsInstance(handler, AdminEmailHandler)
                    self.assertFalse(
                        any(
                            isinstance(flt, RequireDebugTrue) for flt in handler.filters
                        )
                    )

    @override_settings(DEBUG=False)
    def test_django_request_logs_when_debug_is_false(self) -> None:
        """Intent: django.request errors emit once to stderr when DEBUG=False.

        Steps:
            1. Reload settings under DEBUG=0 and apply LOGGING with captured
               stderr.
            2. Log an error on the django.request logger.

        Verification:
            The error message, severity, and logger name appear once in stderr.
        """
        self._reload_settings()
        stream = self._capture_logging_stderr(project_settings.LOGGING)

        logging.getLogger("django.request").error("unhandled request error")

        output = stream.getvalue()
        self.assertEqual(output.count("unhandled request error"), 1)
        self.assertIn("ERROR", output)
        self.assertIn("django.request", output)

    @override_settings(DEBUG=False)
    def test_django_security_logs_when_debug_is_false(self) -> None:
        """Intent: django.security events emit once to stderr when DEBUG=False.

        Steps:
            1. Reload settings under DEBUG=0 and apply LOGGING with captured
               stderr.
            2. Log an error on django.security.DisallowedHost.

        Verification:
            The message, severity, and logger name appear once in stderr.
        """
        self._reload_settings()
        stream = self._capture_logging_stderr(project_settings.LOGGING)

        logging.getLogger("django.security.DisallowedHost").error("blocked host")

        output = stream.getvalue()
        self.assertEqual(output.count("blocked host"), 1)
        self.assertIn("ERROR", output)
        self.assertIn("django.security.DisallowedHost", output)

    @override_settings(DEBUG=False)
    def test_app_logger_emits_when_debug_is_false(self) -> None:
        """Intent: application loggers reach stderr once via the root logger.

        Steps:
            1. Reload settings under DEBUG=0 and apply LOGGING with captured
               stderr.
            2. Log an INFO message on an application logger ("backend.views").

        Verification:
            The message, severity, and logger name appear once in stderr.
        """
        self._reload_settings()
        stream = self._capture_logging_stderr(project_settings.LOGGING)

        logging.getLogger("backend.views").info("application startup event")

        output = stream.getvalue()
        self.assertEqual(output.count("application startup event"), 1)
        self.assertIn("INFO", output)
        self.assertIn("backend.views", output)

    def test_django_server_preserves_server_formatter(self) -> None:
        """Intent: runserver logging keeps ServerFormatter without duplication.

        Steps:
            1. Apply project LOGGING over DEFAULT_LOGGING with captured stderr.
            2. Inspect django.server and emit an INFO record on it.

        Verification:
            django.server does not propagate, uses ServerFormatter, and emits
            the record once.
        """
        self._reload_settings()
        stream = self._capture_logging_stderr(project_settings.LOGGING)

        server_logger = logging.getLogger("django.server")
        self.assertFalse(server_logger.propagate)
        self.assertEqual(len(server_logger.handlers), 1)
        self.assertIsInstance(server_logger.handlers[0].formatter, ServerFormatter)

        server_logger.info('"GET / HTTP/1.1" 200 42')
        output = stream.getvalue()
        self.assertEqual(output.count('"GET / HTTP/1.1" 200 42'), 1)

    @override_settings(DEBUG=False)
    def test_log_level_filters_lower_severity_records(self) -> None:
        """Intent: raising LOG_LEVEL suppresses lower-severity log records.

        Steps:
            1. Reload settings with DEBUG=0 and LOG_LEVEL=WARNING.
            2. Apply LOGGING with captured stderr.
            3. Emit INFO and WARNING records on django.request and backend.views.

        Verification:
            INFO records are filtered out and WARNING records appear once each.
        """
        self._reload_settings({"LOG_LEVEL": "WARNING"})
        stream = self._capture_logging_stderr(project_settings.LOGGING)

        logging.getLogger("django.request").info("suppressed request info")
        logging.getLogger("django.request").warning("kept request warning")
        logging.getLogger("backend.views").info("suppressed app info")
        logging.getLogger("backend.views").warning("kept app warning")

        output = stream.getvalue()
        self.assertNotIn("suppressed request info", output)
        self.assertNotIn("suppressed app info", output)
        self.assertEqual(output.count("kept request warning"), 1)
        self.assertEqual(output.count("kept app warning"), 1)

    @override_settings(DEBUG=False)
    def test_debug_log_level_emits_debug_records(self) -> None:
        """Intent: setting LOG_LEVEL=DEBUG allows DEBUG records through console.

        Steps:
            1. Reload settings with DEBUG=0 and LOG_LEVEL=DEBUG.
            2. Apply LOGGING with captured stderr and emit a DEBUG record on
               backend.views.

        Verification:
            The DEBUG message appears once in stderr.
        """
        self._reload_settings({"LOG_LEVEL": "DEBUG"})
        stream = self._capture_logging_stderr(project_settings.LOGGING)

        logging.getLogger("backend.views").debug("verbose diagnostic trace")

        output = stream.getvalue()
        self.assertEqual(output.count("verbose diagnostic trace"), 1)
        self.assertIn("DEBUG", output)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["example.com"])
    def test_disallowed_host_request_logs_in_production(self) -> None:
        """Intent: a DisallowedHost rejection logs to stderr when DEBUG=False.

        Steps:
            1. Configure logging with captured stderr while DEBUG=False and
               ALLOWED_HOSTS=["example.com"].
            2. GET "/" with a disallowed Host header.

        Verification:
            The response is 400 and stderr records the DisallowedHost error
            from django.security.DisallowedHost once.
        """
        stream = self._capture_logging_stderr(project_settings.LOGGING)

        response = self.client.get("/", headers={"Host": "evil.example"})

        self.assertEqual(response.status_code, 400)
        output = stream.getvalue()
        self.assertEqual(output.count("ERROR django.security.DisallowedHost:"), 1)
        self.assertIn("Invalid HTTP_HOST header", output)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_unhandled_500_request_logs_in_production(self) -> None:
        """Intent: an unhandled 500 view exception logs its traceback when DEBUG=False.

        Steps:
            1. Configure logging with captured stderr while DEBUG=False.
            2. Patch backend.views.render to raise RuntimeError and GET "/"
               with a client that returns 500 responses instead of re-raising.

        Verification:
            The response is 500 and stderr contains the django.request error
            and exception traceback once.
        """
        stream = self._capture_logging_stderr(project_settings.LOGGING)
        client = Client(raise_request_exception=False)

        with mock.patch("backend.views.render", side_effect=RuntimeError("boom")):
            response = client.get("/")

        self.assertEqual(response.status_code, 500)
        output = stream.getvalue()
        self.assertEqual(
            output.count("ERROR django.request: Internal Server Error: /"), 1
        )
        self.assertIn("RuntimeError: boom", output)
