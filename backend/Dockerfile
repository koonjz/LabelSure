# ─────────────────────────────────────────────────────────────────────────────
# LabelSure Backend — Production Dockerfile
# Multi-stage build: keeps final image lean by not including build tools.
# ─────────────────────────────────────────────────────────────────────────────

# Stage 1: Python dependency builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools needed for some Python packages (e.g. psycopg2, numpy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
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

# ─── OS-level dependencies (OCR + CV) ────────────────────────────────────────
# These CANNOT be pip-installed; they are system packages.
# Tesseract with Indic language packs + OpenCV runtime libs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Tesseract OCR engine
    tesseract-ocr \
    # Indic language packs
    tesseract-ocr-hin \
    tesseract-ocr-tam \
    tesseract-ocr-tel \
    tesseract-ocr-kan \
    tesseract-ocr-ben \
    # OpenCV runtime shared libraries
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    # PostgreSQL client libs (for asyncpg / psycopg2)
    libpq5 \
    # curl for health-check in docker-compose
    curl \
    && rm -rf /var/lib/apt/lists/*

# ─── Python packages from builder ────────────────────────────────────────────
COPY --from=builder /install /usr/local

# ─── Application source ───────────────────────────────────────────────────────
COPY . .

# ─── Non-root user (security hardening) ──────────────────────────────────────
RUN useradd --no-create-home --shell /bin/false appuser \
    && mkdir -p uploads \
    && chown -R appuser:appuser /app

USER appuser

# ─── Expose ───────────────────────────────────────────────────────────────────
EXPOSE 8000

# ─── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ─── Entrypoint ───────────────────────────────────────────────────────────────
# Uses gunicorn with UvicornWorker for production-grade ASGI serving.
# Workers: 2 per CPU core is a typical starting point. Override via WORKERS env var.
CMD ["sh", "-c", \
     "gunicorn backend.main:app \
       --workers ${WORKERS:-2} \
       --worker-class uvicorn.workers.UvicornWorker \
       --bind 0.0.0.0:8000 \
       --timeout 120 \
       --keep-alive 5 \
       --access-logfile - \
       --error-logfile - \
       --log-level info"]
