"""Test suite for which files the project publishes as static files."""

import json

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


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

    def test_built_entry_is_published(self) -> None:
        """Intent: the built Vite entry is what the page actually loads.

        Steps:
            1. Read the built entry file name from the Vite manifest.
            2. Ask the staticfiles finders for it.

        Verification:
            A finder returns it.
        """
        manifest_path = settings.DJANGO_VITE["default"]["manifest_path"]
        with open(manifest_path, encoding="utf-8") as manifest_file:
            entry = json.load(manifest_file)["frontend/js/main.js"]["file"]
        self.assertIsNotNone(finders.find(entry))
