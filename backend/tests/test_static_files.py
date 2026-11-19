"""Test suite for how built static files are served in production.

Author: Mike Borozdin (mikebz@)
"""

import json

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase


def _built_entry_url() -> str:
    """Return the static URL of the built Vite entry script.

    Returns:
        The URL of the entry chunk named in the Vite manifest.

    """
    manifest_path = settings.DJANGO_VITE["default"]["manifest_path"]
    with open(manifest_path, encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)
    return f"{settings.STATIC_URL}{manifest['frontend/js/main.js']['file']}"


class BuiltAssetServingTest(SimpleTestCase):
    """Test the caching and compression of collected static files."""

    @classmethod
    def setUpClass(cls) -> None:
        """Collect static files so WhiteNoise has something to serve."""
        super().setUpClass()
        call_command("collectstatic", interactive=False, verbosity=0)

    def test_vite_assets_are_cached_forever(self) -> None:
        """Intent: content-hashed Vite output is cached by browsers for good.

        Steps:
            1. Look up the built entry script in the Vite manifest.
            2. GET it.

        Verification:
            Cache-Control marks the response immutable.
        """
        response = self.client.get(_built_entry_url())
        self.assertIn("immutable", response.headers["Cache-Control"])

    def test_unhashed_files_are_not_immutable(self) -> None:
        """Intent: files without a content hash can still change on deploy.

        Steps:
            1. GET a Django admin stylesheet, whose name carries no hash.

        Verification:
            Cache-Control does not mark the response immutable.
        """
        response = self.client.get(f"{settings.STATIC_URL}admin/css/base.css")
        self.assertNotIn("immutable", response.headers["Cache-Control"])

    def test_vite_assets_are_served_compressed(self) -> None:
        """Intent: clients that accept gzip get the smaller encoding.

        Steps:
            1. GET the built entry script with Accept-Encoding: gzip.

        Verification:
            The response is gzip-encoded.
        """
        response = self.client.get(
            _built_entry_url(), headers={"Accept-Encoding": "gzip"}
        )
        self.assertEqual(response.headers.get("Content-Encoding"), "gzip")
