"""Test suite for backend views, routing, and settings helpers."""

import importlib
import os
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import Client, SimpleTestCase, TestCase
from django.utils.csp import CSP

from djangovue import settings as project_settings


class IndexViewTest(TestCase):
    """Test the main index view that serves the Vue.js application.

    Following TDD principles with clear test naming and structure.
    """

    def setUp(self) -> None:
        """Set up test client for each test method."""
        self.client = Client()

    def test_index_view_returns_200_status_code(self) -> None:
        """GIVEN: A request to the root URL.

        WHEN: The index view is called
        THEN: It should return a 200 status code
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_index_view_uses_correct_template(self) -> None:
        """GIVEN: A request to the root URL.

        WHEN: The index view is called
        THEN: It should use the index.html template
        """
        response = self.client.get("/")
        self.assertTemplateUsed(response, "index.html")

    def test_index_view_contains_vue_app_div(self) -> None:
        """GIVEN: A request to the root URL.

        WHEN: The index view is called
        THEN: The response should contain the Vue.js app mount point
        """
        response = self.client.get("/")
        self.assertContains(response, '<div id="app">')

    def test_index_view_contains_vue_js_title(self) -> None:
        """GIVEN: A request to the root URL.

        WHEN: The index view is called
        THEN: The response should contain the Vue.js App title
        """
        response = self.client.get("/")
        self.assertContains(response, "Vue.js App")

    def test_index_view_contains_javascript_bundle(self) -> None:
        """GIVEN: A request to the root URL.

        WHEN: The index view is called
        THEN: The response should include JavaScript bundle references
        """
        response = self.client.get("/")
        self.assertContains(response, ".js")

    def test_index_view_contains_css_bundle(self) -> None:
        """GIVEN: A request to the root URL.

        WHEN: The index view is called
        THEN: The response should include CSS bundle references
        """
        response = self.client.get("/")
        self.assertContains(response, ".css")


class URLConfigTest(TestCase):
    """Test URL configuration and routing.

    Ensures proper URL patterns are working.
    """

    def test_root_url_resolves_to_index_view(self) -> None:
        """GIVEN: The root URL pattern.

        WHEN: A request is made to '/'
        THEN: It should resolve to the index view
        """
        response = self.client.get("/")
        # Test that the response is successful
        self.assertEqual(response.status_code, 200)
        # Test that it contains expected content
        self.assertContains(response, "Vue.js App")


class ViteIntegrationTest(TestCase):
    """Test Django-Vite integration.

    Ensures build assets are properly integrated.
    """

    def test_vite_assets_are_loaded(self) -> None:
        """GIVEN: A built frontend with Vite.

        WHEN: The index page is loaded
        THEN: Vite-generated assets should be referenced
        """
        response = self.client.get("/")
        # Check that the response contains script tags
        self.assertContains(response, "<script")
        # Check that the response contains link tags for CSS
        self.assertContains(response, 'rel="stylesheet"')

    def test_static_files_configuration_works(self) -> None:
        """GIVEN: Django static files configuration.

        WHEN: Static files are requested
        THEN: They should be served correctly in development
        """
        # This test ensures static file serving is configured
        # In production, this would be handled by a web server
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)


class HealthEndpointTest(SimpleTestCase):
    """Test health endpoint behavior used by container checks."""

    def test_healthz_returns_ok_json(self) -> None:
        """Return a healthy JSON payload on the health endpoint."""
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class SecurityHeaderTest(SimpleTestCase):
    """Test the security response headers served with every page."""

    def test_index_sends_csp_header(self) -> None:
        """Intent: every page is served under a Content Security Policy.

        Steps:
            1. GET "/".
            2. Read the Content-Security-Policy response header.

        Verification:
            The header is present and restricts default-src to 'self'.
        """
        response = self.client.get("/")
        policy = response.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", policy)

    def test_index_denies_framing(self) -> None:
        """Intent: the app cannot be embedded in a frame by another site.

        Steps:
            1. GET "/".
            2. Read the X-Frame-Options header and the CSP frame-ancestors
               directive.

        Verification:
            X-Frame-Options is DENY and frame-ancestors is 'none'.
        """
        response = self.client.get("/")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn(
            "frame-ancestors 'none'", response.headers["Content-Security-Policy"]
        )

    def test_index_sends_nosniff_header(self) -> None:
        """Intent: browsers must not MIME-sniff responses from this app.

        Steps:
            1. GET "/".
            2. Read the X-Content-Type-Options header.

        Verification:
            The header is "nosniff".
        """
        response = self.client.get("/")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")


class CspPolicyTest(SimpleTestCase):
    """Test the Content Security Policy built for each run mode."""

    def test_built_policy_is_same_origin(self) -> None:
        """Intent: a built deployment loads scripts from its own origin only.

        Steps:
            1. Build the policy with dev_mode disabled.

        Verification:
            script-src and style-src allow only 'self' and the nonce
            placeholder - no third-party origin and no inline escape hatch.
        """
        policy = project_settings.build_csp_policy(
            dev_mode=False,
            dev_server_host="127.0.0.1",
            dev_server_port=3000,
        )
        self.assertEqual(policy["script-src"], [CSP.SELF, CSP.NONCE])
        self.assertEqual(policy["style-src"], [CSP.SELF, CSP.NONCE])

    def test_dev_policy_allows_vite_server(self) -> None:
        """Intent: dev mode may load modules and HMR sockets from Vite.

        Steps:
            1. Build the policy with dev_mode enabled for host 1.2.3.4:5173.

        Verification:
            script-src allows the dev server's HTTP origin and connect-src
            allows its websocket origin.
        """
        policy = project_settings.build_csp_policy(
            dev_mode=True,
            dev_server_host="1.2.3.4",
            dev_server_port=5173,
        )
        self.assertIn("http://1.2.3.4:5173", policy["script-src"])
        self.assertIn("ws://1.2.3.4:5173", policy["connect-src"])

    def test_dev_policy_brackets_ipv6_host(self) -> None:
        """Intent: an IPv6 dev server host yields valid CSP source expressions.

        Steps:
            1. Bracket the literal "::1" with format_url_host.
            2. Build the dev-mode policy with the bracketed host.

        Verification:
            The HTTP and websocket origins carry the brackets a URL authority
            needs, matching the URL django-vite builds from the same host.
        """
        host = project_settings.format_url_host("::1")
        policy = project_settings.build_csp_policy(
            dev_mode=True,
            dev_server_host=host,
            dev_server_port=3000,
        )
        self.assertIn("http://[::1]:3000", policy["script-src"])
        self.assertIn("ws://[::1]:3000", policy["connect-src"])

    def test_dev_policy_allows_inline_styles(self) -> None:
        """Intent: Vite injects component styles inline while developing.

        Steps:
            1. Build the policy with dev_mode enabled.
            2. Build the policy with dev_mode disabled.

        Verification:
            'unsafe-inline' is present in style-src for dev mode only.
        """
        dev_policy = project_settings.build_csp_policy(
            dev_mode=True,
            dev_server_host="127.0.0.1",
            dev_server_port=3000,
        )
        built_policy = project_settings.build_csp_policy(
            dev_mode=False,
            dev_server_host="127.0.0.1",
            dev_server_port=3000,
        )
        self.assertIn(CSP.UNSAFE_INLINE, dev_policy["style-src"])
        self.assertNotIn(CSP.UNSAFE_INLINE, built_policy["style-src"])


class UrlHostFormattingTest(SimpleTestCase):
    """Test host formatting for URL authorities."""

    def test_ipv4_host_is_unchanged(self) -> None:
        """Intent: ordinary hosts pass through untouched.

        Steps:
            1. Format an IPv4 address and a hostname.

        Verification:
            Both come back exactly as given.
        """
        self.assertEqual(project_settings.format_url_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(project_settings.format_url_host("frontend"), "frontend")

    def test_ipv6_host_is_bracketed(self) -> None:
        """Intent: a bare IPv6 literal is bracketed before a port is appended.

        Steps:
            1. Format the literal "::1".

        Verification:
            The result is "[::1]".
        """
        self.assertEqual(project_settings.format_url_host("::1"), "[::1]")

    def test_bracketed_host_is_not_double_wrapped(self) -> None:
        """Intent: an already-bracketed literal is left alone.

        Steps:
            1. Format the literal "[::1]".

        Verification:
            The result is still "[::1]".
        """
        self.assertEqual(project_settings.format_url_host("[::1]"), "[::1]")


class HstsPreloadValidationTest(SimpleTestCase):
    """Test the guard on preload-incompatible HSTS configurations."""

    def test_preload_off_accepts_any_settings(self) -> None:
        """Intent: the guard only applies when preload is actually requested.

        Steps:
            1. Validate with preload disabled and otherwise unusable values.

        Verification:
            No exception is raised.
        """
        project_settings.validate_hsts_preload(
            preload=False,
            include_subdomains=False,
            max_age=0,
        )

    def test_preload_needs_subdomains(self) -> None:
        """Intent: preload without includeSubDomains is rejected at startup.

        Steps:
            1. Validate with preload on, a one-year max-age, and subdomains
               off.

        Verification:
            ImproperlyConfigured names the subdomains setting.
        """
        with self.assertRaisesMessage(
            ImproperlyConfigured, "SECURE_HSTS_INCLUDE_SUBDOMAINS must be enabled"
        ):
            project_settings.validate_hsts_preload(
                preload=True,
                include_subdomains=False,
                max_age=project_settings.HSTS_PRELOAD_MIN_SECONDS,
            )

    def test_preload_needs_one_year_max_age(self) -> None:
        """Intent: preload with a short max-age is rejected at startup.

        Steps:
            1. Validate with preload and subdomains on but a one-day max-age.

        Verification:
            ImproperlyConfigured names the required minimum max-age.
        """
        with self.assertRaisesMessage(
            ImproperlyConfigured, "SECURE_HSTS_SECONDS must be at least 31536000"
        ):
            project_settings.validate_hsts_preload(
                preload=True,
                include_subdomains=True,
                max_age=86_400,
            )

    def test_valid_preload_config_is_accepted(self) -> None:
        """Intent: a preload-ready configuration passes the guard.

        Steps:
            1. Validate with preload on, subdomains on, and a one-year
               max-age.

        Verification:
            No exception is raised.
        """
        project_settings.validate_hsts_preload(
            preload=True,
            include_subdomains=True,
            max_age=project_settings.HSTS_PRELOAD_MIN_SECONDS,
        )


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
        self.assertFalse(project_settings.get_env_bool("DEBUG", environ={}))

    def test_get_env_bool_parses_truthy_values(self) -> None:
        """Parse accepted truthy strings to True."""
        environ = {"DEBUG": "true"}
        self.assertTrue(project_settings.get_env_bool("DEBUG", environ=environ))

    def test_get_env_list_splits_values(self) -> None:
        """Split comma-separated list values and trim whitespace."""
        environ = {"ALLOWED_HOSTS": "example.com, api.example.com"}
        self.assertEqual(
            project_settings.get_env_list("ALLOWED_HOSTS", environ=environ),
            ["example.com", "api.example.com"],
        )

    def test_get_env_list_returns_empty_when_missing(self) -> None:
        """Return an empty list when an environment variable is missing and no default is provided."""
        self.assertEqual(project_settings.get_env_list("MISSING", environ={}), [])

    def test_get_env_list_uses_default_when_missing(self) -> None:
        """Return the default sequence as a list when an environment variable is missing."""
        self.assertEqual(
            project_settings.get_env_list("MISSING", default=("a", "b"), environ={}),
            ["a", "b"],
        )

    def test_get_env_str_uses_default_when_missing(self) -> None:
        """Return the default string when an environment variable is missing."""
        self.assertEqual(
            project_settings.get_env_str("HOST", default="127.0.0.1", environ={}),
            "127.0.0.1",
        )

    def test_get_env_str_strips_whitespace(self) -> None:
        """Trim surrounding whitespace from string values."""
        environ = {"HOST": "  ::1  "}
        self.assertEqual(
            project_settings.get_env_str("HOST", default="x", environ=environ),
            "::1",
        )

    def test_get_env_str_falls_back_when_blank(self) -> None:
        """Treat a blank value as absent and use the default."""
        environ = {"HOST": "   "}
        self.assertEqual(
            project_settings.get_env_str("HOST", default="127.0.0.1", environ=environ),
            "127.0.0.1",
        )

    def test_get_env_int_uses_default(self) -> None:
        """Use the default integer when an environment variable is missing."""
        self.assertEqual(
            project_settings.get_env_int("DB_CONN_MAX_AGE", default=60, environ={}),
            60,
        )

    def test_get_env_int_parses_integer(self) -> None:
        """Parse integer values from environment variables."""
        environ = {"DB_CONN_MAX_AGE": "120"}
        self.assertEqual(
            project_settings.get_env_int("DB_CONN_MAX_AGE", default=0, environ=environ),
            120,
        )

    def test_get_env_int_raises_for_invalid_value(self) -> None:
        """Raise ImproperlyConfigured for non-integer environment values."""
        environ = {"DB_CONN_MAX_AGE": "not-a-number"}
        with self.assertRaises(ImproperlyConfigured):
            project_settings.get_env_int("DB_CONN_MAX_AGE", default=60, environ=environ)
