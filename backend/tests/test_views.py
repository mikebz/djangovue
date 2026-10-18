"""Test suite for backend views and routing.

Author: Mike Borozdin (mikebz@)
"""

from django.conf import settings
from django.core.management import call_command
from django.test import Client, SimpleTestCase, TestCase


class IndexViewTest(TestCase):
    """Test the main index view that serves the Vue.js application.

    Following TDD principles with clear test naming and structure.
    """

    def setUp(self) -> None:
        """Set up test client for each test method."""
        self.client = Client()

    def test_index_view_returns_200_status_code(self) -> None:
        """Intent: the root URL serves a successful response.

        Steps:
            1. GET "/".

        Verification:
            The response status is 200.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_index_view_uses_correct_template(self) -> None:
        """Intent: the root URL uses the correct template.

        Steps:
            1. GET "/".

        Verification:
            The index.html template is used.
        """
        response = self.client.get("/")
        self.assertTemplateUsed(response, "index.html")

    def test_index_view_contains_vue_app_div(self) -> None:
        """Intent: the root URL serves the Vue shell.

        Steps:
            1. GET "/".

        Verification:
            The response contains the Vue.js app mount point.
        """
        response = self.client.get("/")
        self.assertContains(response, '<div id="app">')

    def test_index_view_contains_vue_js_title(self) -> None:
        """Intent: the root URL serves the Vue app title.

        Steps:
            1. GET "/".

        Verification:
            The response contains the Vue.js App title.
        """
        response = self.client.get("/")
        self.assertContains(response, "Vue.js App")

    def test_index_view_contains_javascript_bundle(self) -> None:
        """Intent: the root URL includes JavaScript bundle references.

        Steps:
            1. GET "/".

        Verification:
            The response includes JavaScript bundle references.
        """
        response = self.client.get("/")
        self.assertContains(response, ".js")

    def test_index_view_contains_css_bundle(self) -> None:
        """Intent: the root URL includes CSS bundle references.

        Steps:
            1. GET "/".

        Verification:
            The response includes CSS bundle references.
        """
        response = self.client.get("/")
        self.assertContains(response, ".css")


class URLConfigTest(TestCase):
    """Test URL configuration and routing.

    Ensures proper URL patterns are working.
    """

    def test_root_url_resolves_to_index_view(self) -> None:
        """Intent: the root URL resolves to the index view.

        Steps:
            1. GET "/".

        Verification:
            It resolves to the index view and contains expected content.
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

    @classmethod
    def setUpClass(cls) -> None:
        """Collect static files before running Vite integration tests."""
        super().setUpClass()
        call_command("collectstatic", interactive=False, verbosity=0)

    def test_vite_assets_are_loaded(self) -> None:
        """Intent: Vite-generated assets are referenced in the built frontend.

        Steps:
            1. GET "/".

        Verification:
            Vite-generated assets (script and link tags) are referenced.
        """
        response = self.client.get("/")
        # Check that the response contains script tags
        self.assertContains(response, "<script")
        # Check that the response contains link tags for CSS
        self.assertContains(response, 'rel="stylesheet"')

    def test_static_files_configuration_works(self) -> None:
        """Intent: static files are served correctly in development.

        Steps:
            1. GET a static file URL.

        Verification:
            The static file is served successfully with a 200 status code.
        """
        # This test ensures static file serving is configured
        # In production, this would be handled by a web server
        response = self.client.get(f"{settings.STATIC_URL}admin/css/base.css")
        self.assertEqual(response.status_code, 200)


class HealthEndpointTest(SimpleTestCase):
    """Test health endpoint behavior used by container checks."""

    def test_healthz_returns_ok_json(self) -> None:
        """Return a healthy JSON payload on the health endpoint."""
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
