# =============================================================================
# Backend Dockerfile — multi-stage (dev | prod)
# =============================================================================
ARG PYTHON_VERSION=3.11

# ---------- base ----------
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# uv — tezroq pip alternativasi
RUN pip install --no-cache-dir uv

WORKDIR /app

# ---------- dev ----------
FROM base AS dev

COPY pyproject.toml ./
RUN uv pip install --system --no-cache .[dev]

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------- prod ----------
FROM base AS prod

COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

COPY . .

# Non-root user
RUN useradd -m -u 1000 lms && chown -R lms:lms /app
USER lms

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
