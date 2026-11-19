"""Test suite for backend views and routing.

Author: Mike Borozdin (mikebz@)
"""

import tempfile

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings
from django.urls import resolve

from backend import views


class IndexViewTest(SimpleTestCase):
    """Test the main index view that serves the Vue.js application."""

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
        """Intent: the root URL loads the built JavaScript entry module.

        Steps:
            1. GET "/".

        Verification:
            The response has a module <script> whose src is a .js file. A bare
            ".js" substring is not enough: the "Vue.js App" title contains one.
        """
        response = self.client.get("/")
        self.assertRegex(
            response.content.decode(), r'<script type="module"[^>]*\ssrc="[^"]+\.js"'
        )

    def test_index_view_contains_css_bundle(self) -> None:
        """Intent: the root URL includes CSS bundle references.

        Steps:
            1. GET "/".

        Verification:
            The response includes CSS bundle references.
        """
        response = self.client.get("/")
        self.assertContains(response, ".css")

    def test_index_view_links_favicon(self) -> None:
        """Intent: browsers find the favicon, which lives under STATIC_URL.

        Steps:
            1. GET "/".

        Verification:
            The page links the favicon at its static URL. Without the link,
            browsers request /favicon.ico, which is a 404.
        """
        response = self.client.get("/")
        self.assertContains(response, '<link rel="icon" href="/static/favicon.ico">')


class URLConfigTest(SimpleTestCase):
    """Test URL configuration and routing.

    Ensures proper URL patterns are working.
    """

    def test_root_url_resolves_to_index_view(self) -> None:
        """Intent: the root URL is routed to the index view.

        Steps:
            1. Resolve "/" against the project URLconf.

        Verification:
            The resolved view function is backend.views.index.
        """
        self.assertIs(resolve("/").func, views.index)


class ViteIntegrationTest(SimpleTestCase):
    """Test Django-Vite integration.

    Ensures build assets are properly integrated.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Collect static files into a temporary STATIC_ROOT for these tests.

        Collecting into the real STATIC_ROOT would leave staticfiles/ in the
        working tree after every test run.
        """
        super().setUpClass()
        static_root = cls.enterClassContext(tempfile.TemporaryDirectory())
        cls.enterClassContext(override_settings(STATIC_ROOT=static_root))
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
