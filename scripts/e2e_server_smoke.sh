#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-127.0.0.1}"
PORT="${2:-8000}"
URL="http://${HOST}:${PORT}/"
LOG_FILE="${3:-/tmp/djangovue-e2e-server.log}"

command -v uv >/dev/null 2>&1 || {
  echo "uv is required to run the server smoke test." >&2
  echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
}

uv run python manage.py runserver "${HOST}:${PORT}" >"${LOG_FILE}" 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "${SERVER_PID}" 2>/dev/null || true
}

trap cleanup EXIT

for _ in $(seq 1 20); do
  if curl -fsS "${URL}" >/dev/null; then
    echo "Server smoke test passed: ${URL}"
    exit 0
  fi
  sleep 1
done

echo "Server smoke test failed: ${URL}"
echo "Last server log lines:"
tail -n 50 "${LOG_FILE}" || true
exit 1
