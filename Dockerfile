# Multi-stage build for Django + Vue.js application

# uv's official image holds just the uv and uvx binaries. It is declared as a
# stage so it is pinned by version and digest like the base images below.
# https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
FROM ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c AS uv

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
FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f

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
# reused across every source-only change. The project itself is installed by the
# second sync, once its source is in place.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist/ ./frontend/dist/

# Collect static files. Settings are imported here, so the two required
# variables are supplied for this command only - .dockerignore keeps .env out of
# the image, and runtime configuration comes from the container environment.
ARG BUILD_DUMMY_KEY=dummy-secret-key-for-build
RUN SECRET_KEY=${BUILD_DUMMY_KEY} DEBUG=1 ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run application
CMD ["gunicorn", "djangovue.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
