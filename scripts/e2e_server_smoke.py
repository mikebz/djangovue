#!/usr/bin/env python3
"""Start the Django development server on a spare port and verify it responds.

Launches `manage.py runserver --noreload` in its own process group so cleanup
stops the server without leaving orphaned children, checks that the target port
is free before starting, verifies the spawned process stays alive while polling
for HTTP 200, and captures logs in an unnamed temporary file.
"""

import argparse
import http.client
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from http.client import HTTPMessage
from pathlib import Path
from typing import IO

BASE_DIR: Path = Path(__file__).resolve().parent.parent
DEFAULT_HOST: str = "127.0.0.1"
# Spare port distinct from dev server (8000), docker smoke (8099), and Vite check (3999).
DEFAULT_PORT: int = 8098
STARTUP_TIMEOUT_SECONDS: float = 20.0
POLL_INTERVAL_SECONDS: float = 0.25
PORT_CHECK_TIMEOUT_SECONDS: float = 0.5
REQUEST_TIMEOUT_SECONDS: float = 5.0
SHUTDOWN_TIMEOUT_SECONDS: float = 10.0
EXPECTED_MARKER: str = '<div id="app">'


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Return 3xx responses as HTTPError instead of following redirects."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        """Decline every redirect so callers observe the raw 3xx status.

        Args:
            req: Original request.
            fp: Response stream (unused).
            code: HTTP redirect status code (unused).
            msg: HTTP reason phrase (unused).
            headers: Response headers (unused).
            newurl: Redirect target URL (unused).

        Returns:
            None, causing `HTTPRedirectHandler` to raise `HTTPError`.

        """
        return None


# Loopback requests must not go through an HTTP(S) proxy set in the environment,
# and redirects must not be followed silently (a 301 on / is not a 200 pass).
_OPENER: urllib.request.OpenerDirector = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    _NoRedirectHandler(),
)


def format_url_host(host: str) -> str:
    """Return a host formatted for URL authorities and Django runserver addrport.

    Bare IPv6 literals must be bracketed before appending `:port`, both for
    valid HTTP URLs and for Django's `runserver` address parser.

    Args:
        host: A hostname, IPv4 address, or IPv6 literal (bare or bracketed).

    Returns:
        The host, bracketed if it is an IPv6 literal.

    """
    stripped = host.strip("[]")
    if ":" in stripped:
        return f"[{stripped}]"
    return stripped


def connect_host_for(host: str) -> str:
    """Return the unbracketed host address to connect to for a bind host.

    Wildcard bind addresses (`0.0.0.0` and `::`) listen on loopback, so port
    probes and HTTP requests target `127.0.0.1` or `::1` instead of the
    wildcard literal.

    Args:
        host: Hostname, IPv4 address, or IPv6 literal (bare or bracketed).

    Returns:
        Unbracketed host suitable for `socket.create_connection` or
        `format_url_host`.

    """
    connect_host = host.strip("[]")
    if connect_host == "0.0.0.0":
        return "127.0.0.1"
    if connect_host == "::":
        return "::1"
    return connect_host


def build_server_url(host: str, port: int) -> str:
    """Build the root HTTP URL for the smoke-tested server.

    Maps wildcard bind hosts (`0.0.0.0` and `::`) to their loopback equivalents
    so the probe URL is connectable and matches default `ALLOWED_HOSTS`.

    Args:
        host: Hostname, IPv4 address, or IPv6 literal.
        port: TCP port number.

    Returns:
        The root URL string ending with `/`.

    """
    return f"http://{format_url_host(connect_host_for(host))}:{port}/"


def parse_host(value: str) -> str:
    """Validate a non-empty host value supplied on the command line.

    Args:
        value: Raw string supplied to `--host`.

    Returns:
        The trimmed host string.

    Raises:
        argparse.ArgumentTypeError: If the host is empty.

    """
    host = value.strip()
    if not host or not host.strip("[]"):
        raise argparse.ArgumentTypeError("host must not be empty")
    return host


def parse_port(value: str) -> int:
    """Parse and validate a TCP port number supplied on the command line.

    Args:
        value: Raw string supplied to `--port`.

    Returns:
        A TCP port number in the range 1..65535.

    Raises:
        argparse.ArgumentTypeError: If the value is not a valid port number.

    """
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid port: {value!r}") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(
            f"port must be between 1 and 65535, got {port}"
        )
    return port


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line options for the server smoke test.

    Args:
        argv: Optional argument list; defaults to `sys.argv[1:]`.

    Returns:
        Parsed CLI namespace with `host` and `port` attributes.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        type=parse_host,
        default=DEFAULT_HOST,
        help=f"host to bind and probe (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=parse_port,
        default=DEFAULT_PORT,
        help=f"port to bind and probe (default: {DEFAULT_PORT})",
    )
    return parser.parse_args(argv)


def is_port_in_use(
    host: str,
    port: int,
    timeout: float = PORT_CHECK_TIMEOUT_SECONDS,
) -> bool:
    """Return whether something is already accepting connections on host:port.

    Probing before starting `runserver` eliminates the race where a pre-existing
    server answers HTTP 200 before `runserver` finishes booting and crashes with
    `EADDRINUSE`.

    Args:
        host: Hostname, IPv4 address, or IPv6 literal (bare or bracketed).
        port: TCP port number to probe.
        timeout: Connection timeout in seconds.

    Returns:
        True if a TCP connection succeeds, False otherwise.

    """
    connect_host = connect_host_for(host)
    try:
        with socket.create_connection((connect_host, port), timeout=timeout):
            return True
    except OSError:
        return False


def fetch_page(
    url: str,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
) -> tuple[int, str]:
    """Return the HTTP status code and decoded body for a GET request.

    Args:
        url: The URL to request.
        timeout: Request timeout in seconds.

    Returns:
        A `(status_code, body)` tuple. For HTTP error responses, the status
        code is returned with an empty body.

    Raises:
        urllib.error.URLError: If no connection could be made.

    """
    try:
        with _OPENER.open(url, timeout=timeout) as response:
            status: int = response.status
            body: str = response.read().decode("utf-8", "replace")
            return status, body
    except urllib.error.HTTPError as exc:
        exc.close()
        return exc.code, ""


def wait_for_server(
    url: str,
    process: subprocess.Popen[bytes],
    *,
    timeout: float = STARTUP_TIMEOUT_SECONDS,
    poll_interval: float = POLL_INTERVAL_SECONDS,
) -> str | None:
    """Poll a URL until it serves the app shell while the server stays alive.

    Checks `process.poll()` on every iteration and again after receiving HTTP
    200 so a server that fails to boot never passes against another listener.
    Fails immediately once the server answers HTTP with a non-200 status or
    unexpected body, because `runserver` only binds its socket after Django has
    finished initializing.

    Args:
        url: Root URL to poll.
        process: The spawned Django server process.
        timeout: Maximum seconds to wait for readiness.
        poll_interval: Seconds to sleep between connection retries.

    Returns:
        None once the URL returns HTTP 200 containing the Vue mount marker and
        the spawned process is still running; otherwise a short reason string.

    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return "server process exited before becoming ready"
        try:
            status, body = fetch_page(url)
        except (urllib.error.URLError, OSError, http.client.HTTPException):
            if process.poll() is not None:
                return "server process exited before becoming ready"
            time.sleep(poll_interval)
            continue
        if status != 200:
            return f"returned HTTP {status}"
        if EXPECTED_MARKER not in body:
            return f"response missing {EXPECTED_MARKER}"
        if process.poll() is not None:
            return "server process exited during check"
        return None
    return f"timed out after {timeout:g}s"


def stop_process_group(
    process: subprocess.Popen[bytes],
    timeout: float = SHUTDOWN_TIMEOUT_SECONDS,
) -> None:
    """Stop a process started with `start_new_session=True`, and its children.

    Sends SIGTERM to the whole process group, escalating to SIGKILL if the
    group leader does not exit within `timeout` seconds.

    Args:
        process: The process group leader to stop.
        timeout: Seconds to wait after each signal before escalating.

    """
    if process.poll() is not None:
        # Already reaped: signaling process.pid now could hit a reused PID.
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            process.wait(timeout=timeout)
            return
        try:
            process.wait(timeout=timeout)
            return
        except subprocess.TimeoutExpired:
            continue
    print(
        f"Warning: server process {process.pid} did not exit after SIGKILL",
        file=sys.stderr,
    )


def print_server_log(log: IO[bytes]) -> None:
    """Print captured server output from a seekable binary log handle.

    Args:
        log: Seekable binary file object capturing server stdout and stderr.

    """
    log.seek(0)
    output = log.read().decode("utf-8", "replace").strip()
    if output:
        print(output)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Django development server smoke test.

    Args:
        argv: Optional CLI arguments; defaults to `sys.argv[1:]`.

    Returns:
        Exit code 0 when the server boots and serves the app, 1 otherwise.

    """
    args = parse_args(argv)
    url_host = format_url_host(args.host)
    url = build_server_url(args.host, args.port)

    if is_port_in_use(args.host, args.port):
        print(f"Server smoke test failed: {url_host}:{args.port} is already in use")
        return 1

    # Server output goes to an unnamed temporary file rather than a pipe: an
    # unread pipe can fill and block runserver, and nothing is left in /tmp.
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(
            [
                sys.executable,
                str(BASE_DIR / "manage.py"),
                "runserver",
                "--noreload",
                f"{url_host}:{args.port}",
            ],
            cwd=BASE_DIR,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            failure = wait_for_server(url, process)
        finally:
            stop_process_group(process)

        if failure is not None:
            print(f"Server smoke test failed: {url} ({failure})")
            print("Server output:")
            print_server_log(log)
            return 1

        print(f"Server smoke test passed: {url}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
