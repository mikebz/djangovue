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
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy Python dependency files
COPY pyproject.toml uv.lock ./

# Copy project files required to build/install the local package
COPY . .

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist/ ./frontend/dist/

# Collect static files
RUN SECRET_KEY=docker-build-only-secret DEBUG=1 ALLOWED_HOSTS=localhost uv run python manage.py collectstatic --noinput

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
CMD ["uv", "run", "gunicorn", "djangovue.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
