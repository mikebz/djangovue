"""Test suite for backend views and routing."""

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

    def test_index_view_declares_language(self) -> None:
        """Intent: assistive technology knows which language the page is in.

        Steps:
            1. GET "/".

        Verification:
            The <html> element carries lang="en" (WCAG 2.1 success criterion
            3.1.1, Language of Page).
        """
        response = self.client.get("/")
        self.assertContains(response, '<html lang="en">')

    def test_index_view_sets_mobile_viewport(self) -> None:
        """Intent: phones lay the page out at device width, not desktop width.

        Steps:
            1. GET "/".

        Verification:
            The page has a viewport meta tag with width=device-width.
        """
        response = self.client.get("/")
        self.assertContains(
            response,
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
        )

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
        """Intent: container probes see the app as healthy when it is up.

        Steps:
            1. GET "/healthz".

        Verification:
            The status is 200 and the JSON body is {"status": "ok"}.
        """
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_healthz_sets_no_store_cache_control(self) -> None:
        """Intent: caches never serve a stale health check response.

        Steps:
            1. GET "/healthz".

        Verification:
            The Cache-Control header includes "no-store".
        """
        response = self.client.get("/healthz")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["example.com"])
    def test_healthz_bypasses_allowed_hosts(self) -> None:
        """Intent: container probes using localhost or a pod IP succeed.

        Steps:
            1. Configure DEBUG=False and ALLOWED_HOSTS=["example.com"].
            2. GET "/healthz" with Host "localhost:8000" and "10.0.0.5:8000".

        Verification:
            Both requests return 200 with {"status": "ok"}.
        """
        for host in ("localhost:8000", "10.0.0.5:8000"):
            with self.subTest(host=host):
                response = self.client.get("/healthz", headers={"Host": host})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"status": "ok"})

    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["example.com"],
        SECURE_SSL_REDIRECT=True,
    )
    def test_healthz_bypasses_ssl_redirect(self) -> None:
        """Intent: plain-HTTP probes get 200 when HTTPS redirect is enabled.

        Steps:
            1. Enable SECURE_SSL_REDIRECT with DEBUG=False and
               ALLOWED_HOSTS=["example.com"].
            2. Send plain-HTTP GET "/healthz" with both the configured domain
               and localhost.

        Verification:
            Both requests return 200 with {"status": "ok"} instead of 301/400.
        """
        for host in ("example.com", "localhost:8000"):
            with self.subTest(host=host):
                response = self.client.get("/healthz", headers={"Host": host})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"status": "ok"})

    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["example.com"],
        SECURE_SSL_REDIRECT=True,
    )
    def test_healthz_supports_head_requests(self) -> None:
        """Intent: probes using HEAD receive 200 with no response body.

        Steps:
            1. Enable SECURE_SSL_REDIRECT with DEBUG=False and
               ALLOWED_HOSTS=["example.com"].
            2. Send plain-HTTP HEAD "/healthz" with Host "localhost:8000".

        Verification:
            The status is 200 and the response body is empty.
        """
        response = self.client.head("/healthz", headers={"Host": "localhost:8000"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["example.com"])
    def test_healthz_post_does_not_bypass_host_check(self) -> None:
        """Intent: only GET and HEAD probes bypass host validation on /healthz.

        Steps:
            1. Configure DEBUG=False and ALLOWED_HOSTS=["example.com"].
            2. POST "/healthz" with Host "localhost:8000".

        Verification:
            The request is rejected with 400 Bad Request.
        """
        response = self.client.post("/healthz", headers={"Host": "localhost:8000"})
        self.assertEqual(response.status_code, 400)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["example.com"])
    def test_index_still_rejects_disallowed_host(self) -> None:
        """Intent: host validation remains enforced on application routes.

        Steps:
            1. Configure DEBUG=False and ALLOWED_HOSTS=["example.com"].
            2. GET "/" with Host "localhost:8000".

        Verification:
            The response status is 400.
        """
        response = self.client.get("/", headers={"Host": "localhost:8000"})
        self.assertEqual(response.status_code, 400)

    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["example.com"],
        SECURE_SSL_REDIRECT=True,
    )
    def test_index_still_redirects_to_https(self) -> None:
        """Intent: HTTPS redirect remains enforced on application routes.

        Steps:
            1. Enable SECURE_SSL_REDIRECT with DEBUG=False and
               ALLOWED_HOSTS=["example.com"].
            2. Send plain-HTTP GET "/" with Host "example.com".

        Verification:
            The response is a 301 redirect to https://example.com/.
        """
        response = self.client.get("/", headers={"Host": "example.com"})
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.headers["Location"], "https://example.com/")
