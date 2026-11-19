#!/usr/bin/env python3
"""Check that dev-mode pages load their scripts from a running Vite dev server.

Starts Vite on a spare port, renders the index template with
`DJANGO_VITE_DEV_MODE=1`, and fetches every `<script src>` the page names.
A 404 here means the URL django-vite builds and the path Vite serves have
drifted apart, which leaves the page blank in development.

Author: Mike Borozdin (mikebz@)
"""

import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent
# Not 3000, so the check does not collide with a dev server already running.
DEV_SERVER_PORT: int = 3999
STARTUP_TIMEOUT_SECONDS: float = 30.0
SCRIPT_SRC: re.Pattern[str] = re.compile(r'<script[^>]*\ssrc="([^"]+)"')

# Loopback requests must not go through an HTTP(S) proxy set in the environment.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def fetch_status(url: str) -> int:
    """Return the HTTP status code for a GET request.

    Args:
        url: The URL to request.

    Returns:
        The response status code, including error codes such as 404.

    Raises:
        urllib.error.URLError: If no connection could be made.

    """
    try:
        with _OPENER.open(url, timeout=5) as response:
            status: int = response.status
            return status
    except urllib.error.HTTPError as exc:
        return exc.code


def wait_for_server(url: str) -> bool:
    """Poll a URL until the server behind it accepts connections.

    Args:
        url: Any URL on the server.

    Returns:
        True once the server answers, False if it never does in time.

    """
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            fetch_status(url)
            return True
        except urllib.error.URLError:
            time.sleep(0.25)
    return False


def render_dev_index() -> str:
    """Render the index template against the Vite dev server.

    Returns:
        The rendered HTML.

    """
    os.environ["DJANGO_VITE_DEV_MODE"] = "1"
    os.environ["DJANGO_VITE_DEV_SERVER_HOST"] = "127.0.0.1"
    os.environ["DJANGO_VITE_DEV_SERVER_PORT"] = str(DEV_SERVER_PORT)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangovue.settings")

    import django
    from django.template.loader import render_to_string

    django.setup()
    return render_to_string("index.html", {})


def main() -> int:
    """Run the dev-mode asset check.

    Returns:
        The integer exit code (0 for success, 1 for failure).

    """
    vite = subprocess.Popen(
        ["npx", "--no-install", "vite", "--port", str(DEV_SERVER_PORT), "--strictPort"],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        if not wait_for_server(f"http://127.0.0.1:{DEV_SERVER_PORT}/"):
            print("Vite dev server did not start")
            return 1

        sources = SCRIPT_SRC.findall(render_dev_index())
        if not sources:
            print("Dev-mode page references no scripts")
            return 1

        failures = [
            (src, status) for src in sources if (status := fetch_status(src)) != 200
        ]
        if failures:
            print("Dev-mode scripts the Vite dev server does not serve:")
            for src, status in failures:
                print(f"- {src} -> {status}")
            return 1

        print(f"Vite dev mode serves all {len(sources)} page scripts")
        return 0
    finally:
        vite.terminate()
        vite.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main())
