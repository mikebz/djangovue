# Multi-stage build for Django + Vue.js application
FROM node:22-alpine AS frontend-builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

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

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy project
COPY . .

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist/ ./frontend/dist/

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
