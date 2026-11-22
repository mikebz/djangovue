# Multi-stage build for Django + Vue.js application

# uv's official image holds just the uv and uvx binaries. It is declared as a
# stage so it is pinned by version and digest like the base images below.
# https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
FROM ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d AS uv

FROM cgr.dev/chainguard/node:latest-dev@sha256:c50cc3b01363d48e078a253ae4d5cb7318bacc03d61506b77f2dd98f6543f8fe AS frontend-builder

USER root

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies needed for frontend build (including devDependencies like Vite)
RUN npm ci

# Copy frontend source
COPY frontend/ ./frontend/
COPY vite.config.js ./

# Build frontend
RUN npm run build

# Python application stage
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

# PATH puts the project virtualenv first, so `python` and `gunicorn` below are
# the installed ones and nothing has to resolve dependencies at container start.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# curl backs the HEALTHCHECK below. No compiler is installed: every Python
# dependency ships a pure-Python wheel.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /bin/

# Set work directory
WORKDIR /app

# Third-party dependencies resolve from the lock file alone, so this layer is
# reused across every source-only change. Pass --no-cache so /root/.cache/uv is
# never baked into image layers. The project itself is installed by the second
# sync once its source is in place.
# https://docs.astral.sh/uv/guides/integration/docker/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

# Copy only runtime Python files (plus README.md, which hatchling reads via
# pyproject.toml's `readme` field during the second sync) so frontend sources
# and dev files stay out of the runtime image and README edits do not bust the
# third-party dependencies layer above.
COPY manage.py README.md ./
COPY djangovue/ ./djangovue/
COPY backend/ ./backend/
RUN uv sync --frozen --no-dev --no-cache

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist/ ./frontend/dist/

# Collect static files. Settings are imported here, so the two required
# variables are supplied for this command only - .dockerignore keeps .env out of
# the image, and runtime configuration comes from the container environment.
ARG BUILD_DUMMY_KEY=dummy-secret-key-for-build
RUN SECRET_KEY=${BUILD_DUMMY_KEY} DEBUG=1 ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

# Create non-root runtime user. Leave /app, .venv, staticfiles, and
# frontend/dist owned by root (world-readable, non-writable by appuser) so
# chown -R does not duplicate those trees into a new layer and the runtime
# process cannot modify its own code or dependencies. Provision a separate
# /data directory owned by appuser so named volumes mounted for SQLite
# (DATABASE_URL=sqlite:////data/db.sqlite3) initialize writable.
RUN adduser --disabled-password --gecos '' appuser \
    && mkdir -p /data \
    && chown appuser:appuser /data
USER appuser

# Expose port
EXPOSE 8000

# Health check. Require HTTP 200 explicitly: `curl -f` exits 0 on 3xx
# redirects, which would mask an HTTPS redirect on /healthz.
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD test "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/healthz)" = "200"

# Run application
CMD ["gunicorn", "djangovue.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
