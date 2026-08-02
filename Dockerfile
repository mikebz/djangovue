# Multi-stage build for Django + Vue.js application
FROM cgr.dev/chainguard/node:latest-dev@sha256:f9949d26d61c5fc46cf247f082d0e2b0ec352ba75b102524efadcf0db454520b AS frontend-builder

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
FROM python:3.14-slim

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

# Install UV
RUN pip install --no-cache-dir uv

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
