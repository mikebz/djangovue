"""Test suite for the server smoke test script."""

import argparse
import io
import signal
import socket
import subprocess
import urllib.error
import urllib.request
from collections.abc import Mapping
from contextlib import redirect_stderr, redirect_stdout
from http.client import HTTPMessage
from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from scripts import e2e_server_smoke


class UrlHostFormattingTest(SimpleTestCase):
    """Test host bracketing and URL construction for the smoke script."""

    def test_ipv4_and_hostname_are_unchanged(self) -> None:
        """Intent: IPv4 addresses and hostnames pass through without brackets.

        Steps:
            1. Format an IPv4 address and a hostname.

        Verification:
            Both values are returned unchanged.
        """
        self.assertEqual(e2e_server_smoke.format_url_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(e2e_server_smoke.format_url_host("localhost"), "localhost")

    def test_bare_ipv6_host_is_bracketed(self) -> None:
        """Intent: bare IPv6 literals are bracketed for URLs and runserver.

        Steps:
            1. Format the bare IPv6 loopback literal "::1".

        Verification:
            The result is "[::1]".
        """
        self.assertEqual(e2e_server_smoke.format_url_host("::1"), "[::1]")

    def test_bracketed_ipv6_is_not_double_wrapped(self) -> None:
        """Intent: an already-bracketed IPv6 literal is not wrapped twice.

        Steps:
            1. Format the bracketed IPv6 literal "[::1]".

        Verification:
            The result remains "[::1]".
        """
        self.assertEqual(e2e_server_smoke.format_url_host("[::1]"), "[::1]")

    def test_build_server_url_formats_ipv6_host(self) -> None:
        """Intent: server URLs built from bare IPv6 hosts are valid HTTP URLs.

        Steps:
            1. Build the server URL for host "::1" and port 8098.

        Verification:
            The resulting URL is "http://[::1]:8098/".
        """
        self.assertEqual(
            e2e_server_smoke.build_server_url("::1", 8098),
            "http://[::1]:8098/",
        )

    def test_build_server_url_maps_wildcard_hosts(self) -> None:
        """Intent: wildcard bind hosts map to loopback addresses for HTTP URLs.

        Steps:
            1. Build URLs for "0.0.0.0", "::", and "[::]" on port 8098.

        Verification:
            IPv4 wildcard maps to 127.0.0.1 and IPv6 wildcards map to [::1].
        """
        self.assertEqual(
            e2e_server_smoke.build_server_url("0.0.0.0", 8098),
            "http://127.0.0.1:8098/",
        )
        self.assertEqual(
            e2e_server_smoke.build_server_url("::", 8098),
            "http://[::1]:8098/",
        )
        self.assertEqual(
            e2e_server_smoke.build_server_url("[::]", 8098),
            "http://[::1]:8098/",
        )


class PortParsingTest(SimpleTestCase):
    """Test CLI port validation for the smoke script."""

    def test_valid_port_is_parsed(self) -> None:
        """Intent: valid TCP port numbers are accepted as integers.

        Steps:
            1. Parse the port string "8098".

        Verification:
            The integer 8098 is returned.
        """
        self.assertEqual(e2e_server_smoke.parse_port("8098"), 8098)

    def test_out_of_range_port_is_rejected(self) -> None:
        """Intent: TCP ports outside 1..65535 fail CLI argument validation.

        Steps:
            1. Parse "0" and "65536".

        Verification:
            Both raise argparse.ArgumentTypeError.
        """
        with self.assertRaises(argparse.ArgumentTypeError):
            e2e_server_smoke.parse_port("0")
        with self.assertRaises(argparse.ArgumentTypeError):
            e2e_server_smoke.parse_port("65536")

    def test_non_numeric_port_is_rejected(self) -> None:
        """Intent: non-numeric port values fail CLI argument validation.

        Steps:
            1. Parse the string "http".

        Verification:
            argparse.ArgumentTypeError is raised.
        """
        with self.assertRaises(argparse.ArgumentTypeError):
            e2e_server_smoke.parse_port("http")

    def test_blank_host_is_rejected(self) -> None:
        """Intent: blank or empty-bracket host values fail CLI validation.

        Steps:
            1. Parse "", "   ", and "[]" with parse_host.

        Verification:
            Each call raises argparse.ArgumentTypeError.
        """
        for value in ("", "   ", "[]"):
            with self.assertRaises(argparse.ArgumentTypeError):
                e2e_server_smoke.parse_host(value)


class PortInUseDetectionTest(SimpleTestCase):
    """Test pre-start detection of an existing listener on the target port."""

    def test_open_listener_reports_port_in_use(self) -> None:
        """Intent: an active TCP listener on the target port is detected.

        Steps:
            1. Bind and listen on an ephemeral loopback socket.
            2. Call is_port_in_use on that host and port.

        Verification:
            is_port_in_use returns True.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            self.assertTrue(e2e_server_smoke.is_port_in_use("127.0.0.1", port))

    def test_unused_port_reports_not_in_use(self) -> None:
        """Intent: a refused connection reports that the port is free.

        Steps:
            1. Patch socket.create_connection to raise ConnectionRefusedError.
            2. Call is_port_in_use on 127.0.0.1:8098.

        Verification:
            is_port_in_use returns False.
        """
        with patch(
            "scripts.e2e_server_smoke.socket.create_connection",
            side_effect=ConnectionRefusedError,
        ):
            self.assertFalse(e2e_server_smoke.is_port_in_use("127.0.0.1", 8098))

    def test_ipv6_brackets_are_stripped_when_probing(self) -> None:
        """Intent: bracketed IPv6 hosts are unbracketed before socket probing.

        Steps:
            1. Patch socket.create_connection to raise ConnectionRefusedError.
            2. Call is_port_in_use with "[::1]" and port 8098.

        Verification:
            socket.create_connection receives ("::1", 8098).
        """
        with patch(
            "scripts.e2e_server_smoke.socket.create_connection",
            side_effect=ConnectionRefusedError,
        ) as mock_connect:
            e2e_server_smoke.is_port_in_use("[::1]", 8098, timeout=0.5)
        mock_connect.assert_called_once_with(("::1", 8098), timeout=0.5)

    def test_wildcard_host_probes_loopback(self) -> None:
        """Intent: wildcard bind hosts probe their matching loopback address.

        Steps:
            1. Patch socket.create_connection to raise ConnectionRefusedError.
            2. Call is_port_in_use with "0.0.0.0" and "::".

        Verification:
            socket.create_connection probes "127.0.0.1" and "::1" respectively.
        """
        with patch(
            "scripts.e2e_server_smoke.socket.create_connection",
            side_effect=ConnectionRefusedError,
        ) as mock_connect:
            e2e_server_smoke.is_port_in_use("0.0.0.0", 8098, timeout=0.5)
            e2e_server_smoke.is_port_in_use("::", 8098, timeout=0.5)
        self.assertEqual(
            mock_connect.call_args_list,
            [
                ((("127.0.0.1", 8098),), {"timeout": 0.5}),
                ((("::1", 8098),), {"timeout": 0.5}),
            ],
        )


class FetchPageTest(SimpleTestCase):
    """Test HTTP fetching and redirect suppression."""

    def test_fetch_page_returns_status_and_body(self) -> None:
        """Intent: successful HTTP responses return their status and UTF-8 body.

        Steps:
            1. Build a mock HTTP response context manager with status 200.
            2. Patch the opener to return it and call fetch_page.

        Verification:
            fetch_page returns (200, '<div id="app"></div>').
        """
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'<div id="app"></div>'
        response.__enter__.return_value = response
        response.__exit__.return_value = None
        with patch.object(e2e_server_smoke._OPENER, "open", return_value=response):
            status, body = e2e_server_smoke.fetch_page("http://127.0.0.1:8098/")
        self.assertEqual((status, body), (200, '<div id="app"></div>'))

    def test_fetch_page_returns_http_error_status(self) -> None:
        """Intent: HTTP error responses return their status and close the error.

        Steps:
            1. Build an HTTPError for status 500 with a fake response stream.
            2. Patch the opener to raise that HTTPError and call fetch_page.

        Verification:
            fetch_page returns (500, "") and closes the HTTPError stream.
        """
        stream = io.BytesIO(b"error")
        exc = urllib.error.HTTPError(
            "http://127.0.0.1:8098/",
            500,
            "Internal Server Error",
            HTTPMessage(),
            stream,
        )
        with patch.object(e2e_server_smoke._OPENER, "open", side_effect=exc):
            status, body = e2e_server_smoke.fetch_page("http://127.0.0.1:8098/")
        self.assertEqual((status, body), (500, ""))
        self.assertTrue(stream.closed)

    def test_no_redirect_handler_declines_redirects(self) -> None:
        """Intent: 3xx responses are not silently followed as a 200 pass.

        Steps:
            1. Instantiate _NoRedirectHandler.
            2. Call redirect_request for a 301 response.

        Verification:
            redirect_request returns None so urllib surfaces HTTPError(301).
        """
        handler = e2e_server_smoke._NoRedirectHandler()
        result = handler.redirect_request(
            urllib.request.Request("http://127.0.0.1:8098/"),
            io.BytesIO(),
            301,
            "Moved Permanently",
            HTTPMessage(),
            "https://127.0.0.1:8098/",
        )
        self.assertIsNone(result)


class WaitForServerTest(SimpleTestCase):
    """Test polling for server readiness and process liveness."""

    def test_returns_none_when_page_and_process_healthy(self) -> None:
        """Intent: polling succeeds once HTTP 200 serves the app mount marker.

        Steps:
            1. Create a mock process whose poll() returns None.
            2. Patch fetch_page to return 200 with the expected mount marker.
            3. Call wait_for_server.

        Verification:
            wait_for_server returns None (no error).
        """
        process = MagicMock(spec=subprocess.Popen)
        process.poll.return_value = None
        with patch(
            "scripts.e2e_server_smoke.fetch_page",
            return_value=(200, '<html><body><div id="app"></div></body></html>'),
        ):
            error = e2e_server_smoke.wait_for_server(
                "http://127.0.0.1:8098/",
                process,
                timeout=1.0,
                poll_interval=0.0,
            )
        self.assertIsNone(error)

    def test_fails_fast_when_process_exits_early(self) -> None:
        """Intent: a server that crashes on startup fails before fetching HTTP.

        Steps:
            1. Create a mock process whose poll() returns exit code 1.
            2. Patch fetch_page and call wait_for_server.

        Verification:
            wait_for_server returns an error message and never calls fetch_page.
        """
        process = MagicMock(spec=subprocess.Popen)
        process.poll.return_value = 1
        with patch("scripts.e2e_server_smoke.fetch_page") as mock_fetch:
            error = e2e_server_smoke.wait_for_server(
                "http://127.0.0.1:8098/",
                process,
                timeout=5.0,
                poll_interval=0.0,
            )
        self.assertIsNotNone(error)
        self.assertIn("exited", error or "")
        mock_fetch.assert_not_called()

    def test_fails_when_process_exits_after_200(self) -> None:
        """Intent: an HTTP 200 from another listener cannot pass a dead server.

        Steps:
            1. Configure process.poll() to return None before fetch and 1 after.
            2. Patch fetch_page to return 200 with the mount marker.
            3. Call wait_for_server.

        Verification:
            wait_for_server returns an error because the spawned process exited.
        """
        process = MagicMock(spec=subprocess.Popen)
        process.poll.side_effect = [None, 1]
        with patch(
            "scripts.e2e_server_smoke.fetch_page",
            return_value=(200, '<div id="app"></div>'),
        ):
            error = e2e_server_smoke.wait_for_server(
                "http://127.0.0.1:8098/",
                process,
                timeout=1.0,
                poll_interval=0.0,
            )
        self.assertIsNotNone(error)
        self.assertIn("exited", error or "")

    def test_retries_connection_error_until_ready(self) -> None:
        """Intent: transient connection errors during boot are retried.

        Steps:
            1. Patch fetch_page to raise URLError once, then return 200.
            2. Call wait_for_server with a live mock process.

        Verification:
            wait_for_server returns None after retrying.
        """
        process = MagicMock(spec=subprocess.Popen)
        process.poll.return_value = None
        with patch(
            "scripts.e2e_server_smoke.fetch_page",
            side_effect=[
                urllib.error.URLError("connection refused"),
                (200, '<div id="app"></div>'),
            ],
        ) as mock_fetch:
            error = e2e_server_smoke.wait_for_server(
                "http://127.0.0.1:8098/",
                process,
                timeout=2.0,
                poll_interval=0.0,
            )
        self.assertIsNone(error)
        self.assertEqual(mock_fetch.call_count, 2)

    def test_fails_fast_on_non_200_http_response(self) -> None:
        """Intent: an HTTP error from a booted server fails without retrying.

        Steps:
            1. Patch fetch_page to return (400, "").
            2. Call wait_for_server with a live mock process.

        Verification:
            wait_for_server calls fetch_page once and reports HTTP 400.
        """
        process = MagicMock(spec=subprocess.Popen)
        process.poll.return_value = None
        with patch(
            "scripts.e2e_server_smoke.fetch_page",
            return_value=(400, ""),
        ) as mock_fetch:
            error = e2e_server_smoke.wait_for_server(
                "http://127.0.0.1:8098/",
                process,
                timeout=5.0,
                poll_interval=0.0,
            )
        self.assertEqual(mock_fetch.call_count, 1)
        self.assertIn("HTTP 400", error or "")

    def test_rejects_200_without_expected_marker(self) -> None:
        """Intent: an HTTP 200 lacking the Vue mount marker fails immediately.

        Steps:
            1. Patch fetch_page to return 200 with unrelated HTML.
            2. Call wait_for_server with a live mock process.

        Verification:
            wait_for_server calls fetch_page once and reports the missing marker.
        """
        process = MagicMock(spec=subprocess.Popen)
        process.poll.return_value = None
        with patch(
            "scripts.e2e_server_smoke.fetch_page",
            return_value=(200, "<html>other server</html>"),
        ) as mock_fetch:
            error = e2e_server_smoke.wait_for_server(
                "http://127.0.0.1:8098/",
                process,
                timeout=5.0,
                poll_interval=0.0,
            )
        self.assertEqual(mock_fetch.call_count, 1)
        self.assertIn(e2e_server_smoke.EXPECTED_MARKER, error or "")

    def test_returns_timeout_error_after_deadline(self) -> None:
        """Intent: persistent connection failures report a timeout once expired.

        Steps:
            1. Patch fetch_page to raise URLError.
            2. Patch time.monotonic so the deadline expires after one attempt.
            3. Call wait_for_server with a live mock process.

        Verification:
            wait_for_server returns a timeout message naming the timeout.
        """
        process = MagicMock(spec=subprocess.Popen)
        process.poll.return_value = None
        with (
            patch(
                "scripts.e2e_server_smoke.fetch_page",
                side_effect=urllib.error.URLError("connection refused"),
            ),
            patch(
                "scripts.e2e_server_smoke.time.monotonic",
                side_effect=[0.0, 0.1, 2.0],
            ),
        ):
            error = e2e_server_smoke.wait_for_server(
                "http://127.0.0.1:8098/",
                process,
                timeout=1.0,
                poll_interval=0.0,
            )
        self.assertEqual(error, "timed out after 1s")


class StopProcessGroupTest(SimpleTestCase):
    """Test process group teardown and SIGKILL escalation."""

    def test_sends_sigterm_to_process_group(self) -> None:
        """Intent: running server process groups receive SIGTERM and are reaped.

        Steps:
            1. Create a live mock process with pid 4321.
            2. Patch os.killpg and call stop_process_group.

        Verification:
            os.killpg is called once with SIGTERM and process.wait is called.
        """
        process = MagicMock(spec=subprocess.Popen)
        process.pid = 4321
        process.poll.return_value = None
        process.wait.return_value = 0
        with patch("scripts.e2e_server_smoke.os.killpg") as mock_killpg:
            e2e_server_smoke.stop_process_group(process, timeout=1.0)
        mock_killpg.assert_called_once_with(4321, signal.SIGTERM)
        process.wait.assert_called_once_with(timeout=1.0)

    def test_escalates_to_sigkill_after_timeout(self) -> None:
        """Intent: a process group ignoring SIGTERM is escalated to SIGKILL.

        Steps:
            1. Configure process.wait to time out once, then succeed.
            2. Patch os.killpg and call stop_process_group.

        Verification:
            os.killpg sends SIGTERM followed by SIGKILL.
        """
        process = MagicMock(spec=subprocess.Popen)
        process.pid = 4321
        process.poll.return_value = None
        process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="runserver", timeout=1.0),
            -9,
        ]
        with patch("scripts.e2e_server_smoke.os.killpg") as mock_killpg:
            e2e_server_smoke.stop_process_group(process, timeout=1.0)
        self.assertEqual(
            mock_killpg.call_args_list,
            [((4321, signal.SIGTERM),), ((4321, signal.SIGKILL),)],
        )

    def test_skips_signaling_already_reaped_process(self) -> None:
        """Intent: an already-reaped process is never signaled again.

        Steps:
            1. Create a mock process whose poll() returns 0.
            2. Patch os.killpg and call stop_process_group.

        Verification:
            os.killpg is not called.
        """
        process = MagicMock(spec=subprocess.Popen)
        process.pid = 4321
        process.poll.return_value = 0
        with patch("scripts.e2e_server_smoke.os.killpg") as mock_killpg:
            e2e_server_smoke.stop_process_group(process, timeout=1.0)
        mock_killpg.assert_not_called()

    def test_handles_process_lookup_error_cleanly(self) -> None:
        """Intent: a process exiting right before killpg is still reaped cleanly.

        Steps:
            1. Patch os.killpg to raise ProcessLookupError.
            2. Call stop_process_group on a mock process.

        Verification:
            No exception escapes and process.wait is called to reap it.
        """
        process = MagicMock(spec=subprocess.Popen)
        process.pid = 4321
        process.poll.return_value = None
        process.wait.return_value = 0
        with patch(
            "scripts.e2e_server_smoke.os.killpg",
            side_effect=ProcessLookupError,
        ):
            e2e_server_smoke.stop_process_group(process, timeout=1.0)
        process.wait.assert_called_once_with(timeout=1.0)

    def test_warns_when_process_survives_sigkill(self) -> None:
        """Intent: an unkillable process logs a diagnostic warning on stderr.

        Steps:
            1. Configure process.wait to raise TimeoutExpired on both signals.
            2. Patch os.killpg and capture stderr during stop_process_group.

        Verification:
            stderr includes a warning naming the PID and SIGKILL.
        """
        process = MagicMock(spec=subprocess.Popen)
        process.pid = 4321
        process.poll.return_value = None
        process.wait.side_effect = subprocess.TimeoutExpired(
            cmd="runserver",
            timeout=1.0,
        )
        stderr = io.StringIO()
        with (
            patch("scripts.e2e_server_smoke.os.killpg"),
            redirect_stderr(stderr),
        ):
            e2e_server_smoke.stop_process_group(process, timeout=1.0)
        self.assertIn("4321", stderr.getvalue())
        self.assertIn("SIGKILL", stderr.getvalue())


class MainFlowTest(SimpleTestCase):
    """Test the end-to-end control flow of main()."""

    def test_main_fails_fast_when_port_already_in_use(self) -> None:
        """Intent: an occupied port aborts before runserver is spawned.

        Steps:
            1. Patch is_port_in_use to return True and patch subprocess.Popen.
            2. Call main() with default arguments.

        Verification:
            main() returns 1, prints an error, and never calls Popen.
        """
        output = io.StringIO()
        with (
            patch("scripts.e2e_server_smoke.is_port_in_use", return_value=True),
            patch("scripts.e2e_server_smoke.subprocess.Popen") as mock_popen,
            redirect_stdout(output),
        ):
            exit_code = e2e_server_smoke.main([])
        self.assertEqual(exit_code, 1)
        mock_popen.assert_not_called()
        self.assertIn("already in use", output.getvalue())

    def test_main_launches_noreload_in_new_session(self) -> None:
        """Intent: runserver runs with --noreload in its own process group.

        Steps:
            1. Patch is_port_in_use, Popen, wait_for_server, and stop_process_group.
            2. Call main() with default arguments.

        Verification:
            Popen receives runserver --noreload 127.0.0.1:8098 with
            start_new_session=True, stop_process_group runs, and main() returns 0.
        """
        mock_process = MagicMock(spec=subprocess.Popen)
        output = io.StringIO()
        with (
            patch("scripts.e2e_server_smoke.is_port_in_use", return_value=False),
            patch(
                "scripts.e2e_server_smoke.subprocess.Popen",
                return_value=mock_process,
            ) as mock_popen,
            patch("scripts.e2e_server_smoke.wait_for_server", return_value=None),
            patch("scripts.e2e_server_smoke.stop_process_group") as mock_stop,
            redirect_stdout(output),
        ):
            exit_code = e2e_server_smoke.main([])

        self.assertEqual(exit_code, 0)
        cmd: list[str] = mock_popen.call_args.args[0]
        kwargs: Mapping[str, Any] = mock_popen.call_args.kwargs
        self.assertIn("runserver", cmd)
        self.assertIn("--noreload", cmd)
        self.assertEqual(cmd[-1], "127.0.0.1:8098")
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(kwargs["stderr"], subprocess.STDOUT)
        mock_stop.assert_called_once_with(mock_process)

    def test_main_passes_custom_ipv6_host_and_port(self) -> None:
        """Intent: CLI --host and --port bracket IPv6 for runserver and HTTP.

        Steps:
            1. Patch is_port_in_use, Popen, wait_for_server, and stop_process_group.
            2. Call main() with ["--host", "::1", "--port", "9090"].

        Verification:
            Popen receives "[::1]:9090" and wait_for_server receives
            "http://[::1]:9090/".
        """
        mock_process = MagicMock(spec=subprocess.Popen)
        output = io.StringIO()
        with (
            patch("scripts.e2e_server_smoke.is_port_in_use", return_value=False),
            patch(
                "scripts.e2e_server_smoke.subprocess.Popen",
                return_value=mock_process,
            ) as mock_popen,
            patch(
                "scripts.e2e_server_smoke.wait_for_server",
                return_value=None,
            ) as mock_wait,
            patch("scripts.e2e_server_smoke.stop_process_group"),
            redirect_stdout(output),
        ):
            exit_code = e2e_server_smoke.main(["--host", "::1", "--port", "9090"])

        self.assertEqual(exit_code, 0)
        cmd: list[str] = mock_popen.call_args.args[0]
        self.assertEqual(cmd[-1], "[::1]:9090")
        mock_wait.assert_called_once_with("http://[::1]:9090/", mock_process)

    def test_main_stops_process_and_prints_log_on_fail(self) -> None:
        """Intent: startup failure cleans up the process and prints server logs.

        Steps:
            1. Patch Popen so it writes a diagnostic line to the log file handle.
            2. Patch wait_for_server to return an error string.
            3. Call main() and capture stdout.

        Verification:
            main() returns 1, stops the process group, and prints the reason and log.
        """
        mock_process = MagicMock(spec=subprocess.Popen)

        def fake_popen(
            *_args: Any,
            **kwargs: Any,
        ) -> MagicMock:
            kwargs["stdout"].write(b"Error: That port is already in use.\n")
            kwargs["stdout"].flush()
            return mock_process

        output = io.StringIO()
        with (
            patch("scripts.e2e_server_smoke.is_port_in_use", return_value=False),
            patch(
                "scripts.e2e_server_smoke.subprocess.Popen",
                side_effect=fake_popen,
            ),
            patch(
                "scripts.e2e_server_smoke.wait_for_server",
                return_value="server process exited before becoming ready",
            ),
            patch("scripts.e2e_server_smoke.stop_process_group") as mock_stop,
            redirect_stdout(output),
        ):
            exit_code = e2e_server_smoke.main([])

        self.assertEqual(exit_code, 1)
        mock_stop.assert_called_once_with(mock_process)
        self.assertIn("exited before becoming ready", output.getvalue())
        self.assertIn("That port is already in use.", output.getvalue())
