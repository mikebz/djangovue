"""Test suite for backend security headers, CSP, and HSTS helpers."""

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from django.utils.csp import CSP

from djangovue import security


class SecurityHeaderTest(SimpleTestCase):
    """Test the security response headers served with every page."""

    def test_index_sends_default_security_headers(self) -> None:
        """Intent: every page response includes CSP and Django's default security headers.

        Steps:
            1. GET "/".
            2. Inspect the security headers on the response.

        Verification:
            Content-Security-Policy enforces default-src 'self' and
            frame-ancestors 'none', X-Frame-Options is DENY,
            X-Content-Type-Options is nosniff, Referrer-Policy is same-origin,
            and Cross-Origin-Opener-Policy is same-origin.
        """
        response = self.client.get("/")
        policy = response.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
        self.assertEqual(response.headers["Cross-Origin-Opener-Policy"], "same-origin")


class CspPolicyTest(SimpleTestCase):
    """Test the Content Security Policy built for each run mode."""

    def test_built_policy_is_strict_same_origin(self) -> None:
        """Intent: a built deployment enforces strict same-origin CSP directives.

        Steps:
            1. Build the policy with dev_mode disabled.

        Verification:
            Every directive matches the strict same-origin policy, with no
            third-party origins and no 'unsafe-inline' escape hatch.
        """
        policy = security.build_csp_policy(
            dev_mode=False,
            dev_server_host="127.0.0.1",
            dev_server_port=3000,
        )
        self.assertEqual(
            policy,
            {
                "default-src": [CSP.SELF],
                "script-src": [CSP.SELF, CSP.NONCE],
                "style-src": [CSP.SELF, CSP.NONCE],
                "connect-src": [CSP.SELF],
                "img-src": [CSP.SELF, "data:"],
                "font-src": [CSP.SELF, "data:"],
                "base-uri": [CSP.SELF],
                "form-action": [CSP.SELF],
                "frame-ancestors": [CSP.NONE],
                "object-src": [CSP.NONE],
            },
        )

    def test_dev_policy_allows_vite_server_and_styles(self) -> None:
        """Intent: dev mode widens only script, style, and connect directives for Vite.

        Steps:
            1. Build the dev-mode policy for IPv4 host 1.2.3.4:5173.
            2. Build the dev-mode policy for a bare IPv6 literal formatted with
               format_url_host("::1") on port 3000.

        Verification:
            script-src, style-src, and connect-src admit the Vite HTTP/WS
            origins (including bracketed IPv6 authorities) and inline component
            styles, while framing and objects remain denied.
        """
        policy = security.build_csp_policy(
            dev_mode=True,
            dev_server_host="1.2.3.4",
            dev_server_port=5173,
        )
        self.assertEqual(
            policy["script-src"],
            [CSP.SELF, CSP.NONCE, "http://1.2.3.4:5173"],
        )
        self.assertEqual(
            policy["style-src"],
            [CSP.SELF, CSP.NONCE, "http://1.2.3.4:5173", CSP.UNSAFE_INLINE],
        )
        self.assertEqual(
            policy["connect-src"],
            [CSP.SELF, "http://1.2.3.4:5173", "ws://1.2.3.4:5173"],
        )
        self.assertEqual(policy["frame-ancestors"], [CSP.NONE])
        self.assertEqual(policy["object-src"], [CSP.NONE])

        ipv6_policy = security.build_csp_policy(
            dev_mode=True,
            dev_server_host=security.format_url_host("::1"),
            dev_server_port=3000,
        )
        self.assertIn("http://[::1]:3000", ipv6_policy["script-src"])
        self.assertIn("ws://[::1]:3000", ipv6_policy["connect-src"])


class UrlHostFormattingTest(SimpleTestCase):
    """Test host formatting for URL authorities."""

    def test_format_url_host_brackets_bare_ipv6_only(self) -> None:
        """Intent: bare IPv6 literals are bracketed while other hosts pass through unchanged.

        Steps:
            1. Format an IPv4 address, a hostname, bare IPv6 literals, and an
               already-bracketed IPv6 literal.

        Verification:
            Only bare IPv6 literals gain brackets; all other inputs are
            returned verbatim.
        """
        cases = (
            ("127.0.0.1", "127.0.0.1"),
            ("frontend", "frontend"),
            ("::1", "[::1]"),
            ("2001:db8::1", "[2001:db8::1]"),
            ("[::1]", "[::1]"),
        )
        for raw_host, expected in cases:
            with self.subTest(raw_host=raw_host):
                self.assertEqual(security.format_url_host(raw_host), expected)


class HstsPreloadValidationTest(SimpleTestCase):
    """Test the guard on preload-incompatible HSTS configurations."""

    def test_valid_hsts_preload_configs_are_accepted(self) -> None:
        """Intent: preload validation passes when preload is off or fully satisfied.

        Steps:
            1. Validate with preload disabled and zeroed HSTS settings.
            2. Validate with preload enabled, subdomains enabled, and a
               one-year max-age.

        Verification:
            Neither configuration raises an exception.
        """
        cases = (
            (False, False, 0),
            (True, True, security.HSTS_PRELOAD_MIN_SECONDS),
        )
        for preload, include_subdomains, max_age in cases:
            with self.subTest(
                preload=preload,
                include_subdomains=include_subdomains,
                max_age=max_age,
            ):
                security.validate_hsts_preload(
                    preload=preload,
                    include_subdomains=include_subdomains,
                    max_age=max_age,
                )

    def test_invalid_hsts_preload_configs_are_rejected(self) -> None:
        """Intent: incomplete HSTS preload settings fail startup naming every unmet rule.

        Steps:
            1. Validate preload with subdomains off, with a short max-age, and
               with both requirements unmet.

        Verification:
            Each raises ImproperlyConfigured listing every unmet preload
            requirement.
        """
        cases: tuple[tuple[bool, int, tuple[str, ...]], ...] = (
            (
                False,
                security.HSTS_PRELOAD_MIN_SECONDS,
                ("SECURE_HSTS_INCLUDE_SUBDOMAINS must be enabled",),
            ),
            (
                True,
                86_400,
                ("SECURE_HSTS_SECONDS must be at least 31536000",),
            ),
            (
                False,
                0,
                (
                    "SECURE_HSTS_INCLUDE_SUBDOMAINS must be enabled",
                    "SECURE_HSTS_SECONDS must be at least 31536000",
                ),
            ),
        )
        for include_subdomains, max_age, expected_messages in cases:
            with self.subTest(include_subdomains=include_subdomains, max_age=max_age):
                with self.assertRaises(ImproperlyConfigured) as raised:
                    security.validate_hsts_preload(
                        preload=True,
                        include_subdomains=include_subdomains,
                        max_age=max_age,
                    )
                for fragment in expected_messages:
                    self.assertIn(fragment, str(raised.exception))
