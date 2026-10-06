# syntax=docker/dockerfile:1
# MeetingOS API image. Runs database migrations, then serves the API.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app \
    HF_HOME=/app/models

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Install exactly the versions pinned in uv.lock. INSTALL_ASR=false builds a smaller image
# without speech-to-text (audio uploads then need ASR_PROVIDER=mock or a worker with ASR).
COPY pyproject.toml uv.lock ./
ARG INSTALL_ASR=true
RUN if [ "$INSTALL_ASR" = "true" ]; then \
        uv sync --frozen --no-dev --no-install-project --extra asr; \
    else \
        uv sync --frozen --no-dev --no-install-project; \
    fi

ENV PATH="/app/.venv/bin:$PATH"

COPY apps ./apps
COPY packages ./packages
COPY workers ./workers
COPY alembic ./alembic
COPY alembic.ini ./

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data/uploads /app/models \
    && chown -R appuser /app/data /app/models
USER appuser

EXPOSE 8000

# Migrations must succeed before the API starts serving requests
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers"]
