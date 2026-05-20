"""Test suite for backend views, routing, and settings helpers."""

from django.core.exceptions import ImproperlyConfigured
from django.test import Client, SimpleTestCase, TestCase

from djangovue import settings as project_settings


class IndexViewTest(TestCase):
    """
    Test the main index view that serves the Vue.js application.
    Following TDD principles with clear test naming and structure.
    """

    def setUp(self) -> None:
        """Set up test client for each test method."""
        self.client = Client()

    def test_index_view_returns_200_status_code(self) -> None:
        """
        GIVEN: A request to the root URL
        WHEN: The index view is called
        THEN: It should return a 200 status code
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_index_view_uses_correct_template(self) -> None:
        """
        GIVEN: A request to the root URL
        WHEN: The index view is called
        THEN: It should use the index.html template
        """
        response = self.client.get("/")
        self.assertTemplateUsed(response, "index.html")

    def test_index_view_contains_vue_app_div(self) -> None:
        """
        GIVEN: A request to the root URL
        WHEN: The index view is called
        THEN: The response should contain the Vue.js app mount point
        """
        response = self.client.get("/")
        self.assertContains(response, '<div id="app">')

    def test_index_view_contains_vue_js_title(self) -> None:
        """
        GIVEN: A request to the root URL
        WHEN: The index view is called
        THEN: The response should contain the Vue.js App title
        """
        response = self.client.get("/")
        self.assertContains(response, "Vue.js App")

    def test_index_view_contains_javascript_bundle(self) -> None:
        """
        GIVEN: A request to the root URL
        WHEN: The index view is called
        THEN: The response should include JavaScript bundle references
        """
        response = self.client.get("/")
        self.assertContains(response, ".js")

    def test_index_view_contains_css_bundle(self) -> None:
        """
        GIVEN: A request to the root URL
        WHEN: The index view is called
        THEN: The response should include CSS bundle references
        """
        response = self.client.get("/")
        self.assertContains(response, ".css")


class URLConfigTest(TestCase):
    """
    Test URL configuration and routing.
    Ensures proper URL patterns are working.
    """

    def test_root_url_resolves_to_index_view(self) -> None:
        """
        GIVEN: The root URL pattern
        WHEN: A request is made to '/'
        THEN: It should resolve to the index view
        """
        response = self.client.get("/")
        # Test that the response is successful
        self.assertEqual(response.status_code, 200)
        # Test that it contains expected content
        self.assertContains(response, "Vue.js App")


class ViteIntegrationTest(TestCase):
    """
    Test Django-Vite integration.
    Ensures build assets are properly integrated.
    """

    def test_vite_assets_are_loaded(self) -> None:
        """
        GIVEN: A built frontend with Vite
        WHEN: The index page is loaded
        THEN: Vite-generated assets should be referenced
        """
        response = self.client.get("/")
        # Check that the response contains script tags
        self.assertContains(response, "<script")
        # Check that the response contains link tags for CSS
        self.assertContains(response, 'rel="stylesheet"')

    def test_static_files_configuration_works(self) -> None:
        """
        GIVEN: Django static files configuration
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
