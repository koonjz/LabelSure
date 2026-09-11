# ─────────────────────────────────────────────────────────────────────────────
# LabelSure Backend — Production Dockerfile
# Multi-stage build: keeps final image lean by not including build tools.
# Binds dynamically to $PORT assigned by Render, Railway, or Docker Compose.
# ─────────────────────────────────────────────────────────────────────────────

# Stage 1: Python dependency builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools needed for C extensions (e.g. psycopg2, numpy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="LabelSure <hello@labelsure.app>"
LABEL org.opencontainers.image.title="LabelSure Backend"
LABEL org.opencontainers.image.description="FastAPI compliance-scanner backend"

WORKDIR /app

# ─── OS-level dependencies (OCR + CV + Postgres) ────────────────────────────
# Tesseract OCR engine with Indic language packs + OpenCV runtime libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-tam \
    tesseract-ocr-tel \
    tesseract-ocr-kan \
    tesseract-ocr-ben \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ─── Python packages from builder ────────────────────────────────────────────
COPY --from=builder /install /usr/local

# ─── Application source ───────────────────────────────────────────────────────
COPY . .

# ─── Environment defaults ────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ─── Non-root user (security hardening) ──────────────────────────────────────
RUN useradd --no-create-home --shell /bin/false appuser \
    && mkdir -p uploads \
    && chown -R appuser:appuser /app

USER appuser

# ─── Expose ───────────────────────────────────────────────────────────────────
EXPOSE 8000 10000

# ─── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# ─── Entrypoint ───────────────────────────────────────────────────────────────
# Binds dynamically to $PORT provided by Render, Railway, or Docker Compose.
CMD ["sh", "-c", \
     "gunicorn backend.main:app \
       --workers ${WORKERS:-2} \
       --worker-class uvicorn.workers.UvicornWorker \
       --bind 0.0.0.0:${PORT:-8000} \
       --bind 0.0.0.0:8000 \
       --bind 0.0.0.0:10000 \
       --timeout 120 \
       --keep-alive 5 \
       --access-logfile - \
       --error-logfile - \
       --log-level info"]
