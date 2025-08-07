# Multi-stage build for Railway deployment
FROM python:3.11-slim as builder

# Set build arguments and env vars in one layer
ARG DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies and cleanup in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Cache dependencies layer
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf ~/.cache/pip/*

# Production stage - Using slim for smaller image
FROM python:3.11-slim

# Set production env vars
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

# Install runtime deps and create user in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && useradd --create-home --shell /bin/bash --user-group python \
    && mkdir -p /app && chown python:python /app

# Copy virtual env and set workdir
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app

# Copy app code and set permissions
COPY --chown=python:python . .

# Switch to non-root user (security best practice)
USER python

# Health check with retry strategy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port (Railway will override this)
EXPOSE ${PORT}

# Use shell form for env var expansion
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers --forwarded-allow-ips='*'