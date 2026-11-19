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
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent
# Not 3000, so the check does not collide with a dev server already running.
DEV_SERVER_PORT: int = 3999
STARTUP_TIMEOUT_SECONDS: float = 30.0
SCRIPT_SRC: re.Pattern[str] = re.compile(r'<script[^>]*\ssrc="([^"]+)"')
# Each must appear in some script src: the HMR client from {% vite_hmr_client %}
# and the entry module from {% vite_asset %}.
REQUIRED_SCRIPTS: tuple[str, ...] = ("/@vite/client", "/frontend/js/main.js")

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


def wait_for_server(url: str, process: subprocess.Popen[bytes]) -> bool:
    """Poll a URL until it answers 200, or the server process exits.

    The URL should be one only the expected server serves, so another process
    already listening on the port is never mistaken for it. Exiting early
    makes a server that cannot start (port taken, config error) fail fast.

    Args:
        url: A URL only the expected server answers with 200.
        process: The server process being waited for.

    Returns:
        True once the URL answers 200, False if the process exits or the URL
        never answers 200 in time.

    """
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            if fetch_status(url) == 200:
                return True
        except urllib.error.URLError:
            pass
        time.sleep(0.25)
    return False


def stop_process_group(process: subprocess.Popen[bytes]) -> None:
    """Stop a process started with `start_new_session=True`, and its children.

    Sends SIGTERM to the whole group, and SIGKILL if it has not exited within
    10 seconds.

    Args:
        process: The group leader to stop.

    """
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=10)
            return
        except subprocess.TimeoutExpired:
            continue


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
    # Vite's output goes to a file rather than a pipe: an unread pipe can fill
    # and block the server, and the file is still there to print on failure.
    log = tempfile.TemporaryFile()
    # The vite binary is run directly in its own process group: stopping an
    # `npx` wrapper leaves vite itself running, still holding the port.
    vite = subprocess.Popen(
        [
            str(BASE_DIR / "node_modules" / ".bin" / "vite"),
            # Loopback only, overriding the config's 0.0.0.0 for this check.
            "--host",
            "127.0.0.1",
            "--port",
            str(DEV_SERVER_PORT),
            "--strictPort",
        ],
        cwd=BASE_DIR,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        vite_client = f"http://127.0.0.1:{DEV_SERVER_PORT}/static/@vite/client"
        if not wait_for_server(vite_client, vite):
            print("Vite dev server did not start. Its output:")
            log.seek(0)
            print(log.read().decode("utf-8", "replace"))
            return 1

        sources = SCRIPT_SRC.findall(render_dev_index())
        missing = [
            name for name in REQUIRED_SCRIPTS if not any(name in src for src in sources)
        ]
        if missing:
            print("Dev-mode page is missing required scripts:")
            print("- " + "\n- ".join(missing))
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
        stop_process_group(vite)
        log.close()


if __name__ == "__main__":
    sys.exit(main())
