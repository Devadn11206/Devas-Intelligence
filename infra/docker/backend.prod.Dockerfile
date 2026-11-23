# ==============================================================================
# Production Dockerfile for DEVA Intelligence Backend (FastAPI + Celery)
# Multi-stage build with security hardening (non-root deva user)
# ==============================================================================

FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /install

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

# ------------------------------------------------------------------------------
# Final Runtime Image
# ------------------------------------------------------------------------------
FROM python:3.10-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python dependencies from builder
COPY --from=builder /install/deps /usr/local

# Create non-root application user
RUN groupadd -g 10001 deva && \
    useradd -u 10001 -g deva -m -s /bin/bash deva && \
    mkdir -p /app/mlruns /app/data && \
    chown -R deva:deva /app

COPY --chown=deva:deva . /app

USER deva

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ready || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
