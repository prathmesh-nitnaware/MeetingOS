# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install python dependencies into virtualenv
RUN uv venv .venv && \
    uv pip install --no-cache -r pyproject.toml

ENV PATH="/app/.venv/bin:$PATH"

# Copy source tree
COPY apps ./apps
COPY packages ./packages
COPY workers ./workers
COPY datasets ./datasets
COPY evaluation ./evaluation
COPY alembic ./alembic
COPY alembic.ini ./

# Expose port
EXPOSE 8000

# Default command: FastAPI production server
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
