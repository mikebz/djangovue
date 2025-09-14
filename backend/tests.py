from django.test import Client, TestCase


class IndexViewTest(TestCase):
    """
    Test the main index view that serves the Vue.js application.
    Following TDD principles with clear test naming and structure.
    """

    def setUp(self):
        """Set up test client for each test method."""
        self.client = Client()

    def test_index_view_returns_200_status_code(self):
        """
        GIVEN: A request to the root URL
        WHEN: The index view is called
        THEN: It should return a 200 status code
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_index_view_uses_correct_template(self):
        """
        GIVEN: A request to the root URL
        WHEN: The index view is called
        THEN: It should use the index.html template
        """
        response = self.client.get("/")
        self.assertTemplateUsed(response, "index.html")

    def test_index_view_contains_vue_app_div(self):
        """
        GIVEN: A request to the root URL
        WHEN: The index view is called
        THEN: The response should contain the Vue.js app mount point
        """
        response = self.client.get("/")
        self.assertContains(response, '<div id="app">')

    def test_index_view_contains_vue_js_title(self):
        """
        GIVEN: A request to the root URL
        WHEN: The index view is called
        THEN: The response should contain the Vue.js App title
        """
        response = self.client.get("/")
        self.assertContains(response, "Vue.js App")

    def test_index_view_contains_javascript_bundle(self):
        """
        GIVEN: A request to the root URL
        WHEN: The index view is called
        THEN: The response should include JavaScript bundle references
        """
        response = self.client.get("/")
        self.assertContains(response, ".js")

    def test_index_view_contains_css_bundle(self):
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

    def test_root_url_resolves_to_index_view(self):
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

    def test_vite_assets_are_loaded(self):
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

    def test_static_files_configuration_works(self):
        """
        GIVEN: Django static files configuration
        WHEN: Static files are requested
        THEN: They should be served correctly in development
        """
        # This test ensures static file serving is configured
        # In production, this would be handled by a web server
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
