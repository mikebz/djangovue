#!/usr/bin/env python3
"""Run the production image and check that it serves the app.

The other e2e checks use `runserver` with the developer's settings. This one
starts the built image the way a deployment would (gunicorn, `DEBUG` off,
WhiteNoise serving static files) and checks the health endpoint, the page,
and every script and stylesheet the page links.

Pass `--url` to check an already-running server instead of starting the image.
"""

import argparse
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

IMAGE: str = "djangovue:latest"
CONTAINER_NAME: str = "djangovue-smoke"
HOST_PORT: int = 8099
STARTUP_TIMEOUT_SECONDS: float = 60.0
ASSET_REFERENCE: re.Pattern[str] = re.compile(
    r'<(?:script[^>]*\ssrc|link[^>]*\shref)="(/static/[^"]+)"'
)
# The built bundle itself: other /static/ links (the favicon) do not prove
# that {% vite_asset %} rendered anything.
SCRIPT_BUNDLE: re.Pattern[str] = re.compile(r'<script[^>]*\ssrc="/static/[^"]+\.js"')
STYLESHEET_BUNDLE: re.Pattern[str] = re.compile(
    r'<link(?=[^>]*\srel="stylesheet")[^>]*\shref="/static/[^"]+\.css"'
)

# Loopback requests must not go through an HTTP(S) proxy set in the environment.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def fetch(url: str) -> tuple[int, str]:
    """Return the status code and body of a GET request.

    Args:
        url: The URL to request.

    Returns:
        The status code and the body decoded as UTF-8.

    Raises:
        urllib.error.URLError: If no connection could be made.

    """
    try:
        with _OPENER.open(url, timeout=5) as response:
            status: int = response.status
            return status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""


def wait_until_healthy(base_url: str, is_alive: Callable[[], bool]) -> bool:
    """Poll the health endpoint until it answers 200.

    Args:
        base_url: The server's base URL, without a trailing slash.
        is_alive: Reports whether the server process is still running, so a
            server that crashes at startup fails at once instead of after
            the full timeout.

    Returns:
        True once /healthz answers 200, False if the server stops or never
        answers 200 in time.

    """
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if not is_alive():
            return False
        try:
            if fetch(f"{base_url}/healthz")[0] == 200:
                return True
        except (urllib.error.URLError, ConnectionError):
            pass
        time.sleep(1)
    return False


def check_site(base_url: str) -> list[str]:
    """Check the page and the static assets it references.

    Args:
        base_url: The server's base URL, without a trailing slash.

    Returns:
        A description of each problem found; empty when the site is healthy.

    """
    status, page = fetch(f"{base_url}/")
    if status != 200:
        return [f"/ -> {status}"]
    problems = [] if '<div id="app">' in page else ['/ has no <div id="app">']
    if not SCRIPT_BUNDLE.search(page):
        problems.append("/ has no <script> loading a /static/ .js bundle")
    if not STYLESHEET_BUNDLE.search(page):
        problems.append("/ has no stylesheet <link> to a /static/ .css bundle")

    assets = ASSET_REFERENCE.findall(page)
    for path in assets:
        asset_status = fetch(urllib.parse.urljoin(base_url, path))[0]
        if asset_status != 200:
            problems.append(f"{path} -> {asset_status}")
    return problems


def container_running() -> bool:
    """Report whether the smoke-test container is still running.

    Returns:
        True while Docker reports the container as running.

    """
    state = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", CONTAINER_NAME],
        capture_output=True,
        text=True,
    )
    return state.stdout.strip() == "true"


def run_container() -> str:
    """Start the image in the background with minimal production settings.

    Returns:
        The base URL the container answers on.

    """
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
    subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            CONTAINER_NAME,
            "--env",
            "SECRET_KEY=smoke-test-only-not-a-secret",
            "--env",
            "ALLOWED_HOSTS=127.0.0.1,localhost",
            "--publish",
            f"127.0.0.1:{HOST_PORT}:8000",
            IMAGE,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return f"http://127.0.0.1:{HOST_PORT}"


def main() -> int:
    """Run the smoke test.

    Returns:
        The integer exit code (0 for success, 1 for failure).

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="check this running server instead")
    args = parser.parse_args()

    base_url: str = args.url.rstrip("/") if args.url else run_container()
    is_alive: Callable[[], bool] = (lambda: True) if args.url else container_running
    try:
        if not wait_until_healthy(base_url, is_alive):
            print(f"{base_url}/healthz never answered 200")
            return 1
        problems = check_site(base_url)
        if problems:
            print("Smoke test failed:")
            print("- " + "\n- ".join(problems))
            return 1
        print(f"Smoke test passed: {base_url}")
        return 0
    finally:
        if not args.url:
            logs = subprocess.run(
                ["docker", "logs", "--tail", "30", CONTAINER_NAME],
                capture_output=True,
                text=True,
            )
            print("Last container log lines:")
            print(logs.stdout + logs.stderr)
            subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)


if __name__ == "__main__":
    sys.exit(main())
