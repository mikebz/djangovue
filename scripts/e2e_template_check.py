#!/usr/bin/env python3
"""Validate that the index template renders expected frontend integration markers."""

import os
import sys

import django
from django.template.loader import render_to_string

EXPECTED_SNIPPETS = (
    "Vue.js App",
    '<div id="app">',
    ".js",
)


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangovue.settings")
    django.setup()

    rendered = render_to_string("index.html", {})
    missing = [snippet for snippet in EXPECTED_SNIPPETS if snippet not in rendered]
    if missing:
        print("Missing expected template snippets:")
        for snippet in missing:
            print(f"- {snippet}")
        return 1

    print(f"Template rendered successfully (length={len(rendered)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
