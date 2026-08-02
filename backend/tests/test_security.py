"""Test suite for backend security and CSP logic.

Author: Mike Borozdin (mikebz@)
"""

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from django.utils.csp import CSP

from djangovue import utils


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
        policy = utils.build_csp_policy(
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
        policy = utils.build_csp_policy(
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
        host = utils.format_url_host("::1")
        policy = utils.build_csp_policy(
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
        dev_policy = utils.build_csp_policy(
            dev_mode=True,
            dev_server_host="127.0.0.1",
            dev_server_port=3000,
        )
        built_policy = utils.build_csp_policy(
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
        self.assertEqual(utils.format_url_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(utils.format_url_host("frontend"), "frontend")

    def test_ipv6_host_is_bracketed(self) -> None:
        """Intent: a bare IPv6 literal is bracketed before a port is appended.

        Steps:
            1. Format the literal "::1".

        Verification:
            The result is "[::1]".
        """
        self.assertEqual(utils.format_url_host("::1"), "[::1]")

    def test_bracketed_host_is_not_double_wrapped(self) -> None:
        """Intent: an already-bracketed literal is left alone.

        Steps:
            1. Format the literal "[::1]".

        Verification:
            The result is still "[::1]".
        """
        self.assertEqual(utils.format_url_host("[::1]"), "[::1]")


class HstsPreloadValidationTest(SimpleTestCase):
    """Test the guard on preload-incompatible HSTS configurations."""

    def test_preload_off_accepts_any_settings(self) -> None:
        """Intent: the guard only applies when preload is actually requested.

        Steps:
            1. Validate with preload disabled and otherwise unusable values.

        Verification:
            No exception is raised.
        """
        utils.validate_hsts_preload(
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
            utils.validate_hsts_preload(
                preload=True,
                include_subdomains=False,
                max_age=utils.HSTS_PRELOAD_MIN_SECONDS,
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
            utils.validate_hsts_preload(
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
        utils.validate_hsts_preload(
            preload=True,
            include_subdomains=True,
            max_age=utils.HSTS_PRELOAD_MIN_SECONDS,
        )
