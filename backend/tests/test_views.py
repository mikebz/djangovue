"""Test suite for backend views and health check middleware."""

from django.test import SimpleTestCase, override_settings


class IndexViewTest(SimpleTestCase):
    """Test the main index view that serves the Vue.js application."""

    def test_index_renders_vue_shell_and_built_assets(self) -> None:
        """Intent: the root URL serves the Vue shell with built Vite JS and CSS bundles.

        Steps:
            1. GET "/".

        Verification:
            The response is 200 using index.html, includes the Vue mount point
            and title, and links built module JS and stylesheet CSS bundles.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")
        self.assertContains(response, '<div id="app">')
        self.assertContains(response, "Vue.js App")
        html = response.content.decode()
        # Require actual asset tags rather than bare ".js"/".css" substrings:
        # the "Vue.js App" title itself contains ".js".
        self.assertRegex(html, r'<script type="module"[^>]*\ssrc="/static/[^"]+\.js"')
        self.assertRegex(
            html,
            r'<link(?=[^>]*\srel="stylesheet")[^>]*\shref="/static/[^"]+\.css"',
        )

    def test_index_includes_document_metadata(self) -> None:
        """Intent: the root page sets language, mobile viewport, and static favicon link.

        Steps:
            1. GET "/".

        Verification:
            The HTML declares lang="en" (WCAG 3.1.1), sets the responsive
            viewport meta tag, and links the favicon under STATIC_URL.
        """
        response = self.client.get("/")
        self.assertContains(response, '<html lang="en">')
        self.assertContains(
            response,
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
        )
        self.assertContains(response, '<link rel="icon" href="/static/favicon.ico">')


class HealthEndpointTest(SimpleTestCase):
    """Test health endpoint behavior used by container checks."""

    def test_healthz_returns_non_cacheable_ok_json(self) -> None:
        """Intent: container probes get a non-cacheable JSON response with safety headers.

        Steps:
            1. GET "/healthz".

        Verification:
            The status is 200, JSON is {"status": "ok"}, Cache-Control is
            "no-store", X-Content-Type-Options is "nosniff", and Content-Length
            matches the response body.
        """
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(
            response.headers.get("Content-Length"),
            str(len(response.content)),
        )

    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["example.com"],
        SECURE_SSL_REDIRECT=True,
    )
    def test_healthz_bypasses_host_and_ssl_checks(self) -> None:
        """Intent: plain-HTTP GET probes bypass ALLOWED_HOSTS and SECURE_SSL_REDIRECT.

        Steps:
            1. Configure DEBUG=False, ALLOWED_HOSTS=["example.com"], and
               SECURE_SSL_REDIRECT=True.
            2. Send plain-HTTP GET "/healthz" with the public domain,
               localhost, and a pod IP as Host.

        Verification:
            Every request returns 200 with {"status": "ok"} instead of 301/400.
        """
        for host in ("example.com", "localhost:8000", "10.0.0.5:8000"):
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
        """Intent: plain-HTTP HEAD probes receive 200 with an empty response body.

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
            The request is rejected with 400 Bad Request and logged as a
            DisallowedHost security error.
        """
        with self.assertLogs("django.security.DisallowedHost", level="ERROR"):
            response = self.client.post("/healthz", headers={"Host": "localhost:8000"})
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
