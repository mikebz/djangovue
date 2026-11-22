"""Test suite for static file discovery, caching, and compression."""

import json
import tempfile

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


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
    """Test the serving, caching, and compression of collected static files."""

    @classmethod
    def setUpClass(cls) -> None:
        """Collect static files into a temporary STATIC_ROOT for WhiteNoise.

        Collecting into the real STATIC_ROOT would leave staticfiles/ in the
        working tree, and could serve stale files from an earlier run.
        """
        super().setUpClass()
        static_root = cls.enterClassContext(tempfile.TemporaryDirectory())
        cls.enterClassContext(override_settings(STATIC_ROOT=static_root))
        call_command("collectstatic", interactive=False, verbosity=0)

    def test_vite_assets_are_cached_forever(self) -> None:
        """Intent: content-hashed Vite output is served and cached as immutable.

        Steps:
            1. Look up the built entry script in the Vite manifest.
            2. GET it.

        Verification:
            The response is 200 and Cache-Control marks it immutable.
        """
        response = self.client.get(_built_entry_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("immutable", response.headers["Cache-Control"])

    def test_unhashed_files_are_not_immutable(self) -> None:
        """Intent: unhashed static files are served without immutable caching.

        Steps:
            1. GET Django admin CSS and the app favicon, neither of which
               carries a content hash in its filename.

        Verification:
            Both return 200 and Cache-Control does not mark them immutable.
        """
        for path in ("admin/css/base.css", "favicon.ico"):
            with self.subTest(path=path):
                response = self.client.get(f"{settings.STATIC_URL}{path}")
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("immutable", response.headers["Cache-Control"])

    def test_vite_assets_are_served_compressed(self) -> None:
        """Intent: clients that accept gzip get the smaller encoding.

        Steps:
            1. GET the built entry script with Accept-Encoding: gzip.

        Verification:
            The response is 200 and gzip-encoded.
        """
        response = self.client.get(
            _built_entry_url(), headers={"Accept-Encoding": "gzip"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Encoding"), "gzip")


class StaticSourcesTest(SimpleTestCase):
    """Test what the staticfiles finders can see."""

    def test_frontend_source_is_not_published(self) -> None:
        """Intent: Vue source files are build input, not public static files.

        Steps:
            1. Ask the staticfiles finders for the App.vue source file.

        Verification:
            No finder returns it, so collectstatic never publishes it.
        """
        self.assertIsNone(finders.find("js/App.vue"))
