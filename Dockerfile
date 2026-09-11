# ─────────────────────────────────────────────────────────────────────────────
# LabelSure — Production Dockerfile (Repository Root)
# Render / Railway / Cloud Deployment Entry Point
# ─────────────────────────────────────────────────────────────────────────────

# Stage 1: Python dependency builder
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Runtime image
FROM python:3.11-slim AS runtime

LABEL maintainer="LabelSure <hello@labelsure.app>"
LABEL org.opencontainers.image.title="LabelSure Full Stack Repository"

WORKDIR /app

# System dependencies for Tesseract OCR, OpenCV, and PostgreSQL
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

COPY --from=builder /install /usr/local

COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd --no-create-home --shell /bin/false appuser \
    && mkdir -p uploads \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", \
     "gunicorn backend.main:app \
       --workers ${WORKERS:-2} \
       --worker-class uvicorn.workers.UvicornWorker \
       --bind 0.0.0.0:${PORT:-8000} \
       --timeout 120 \
       --keep-alive 5 \
       --access-logfile - \
       --error-logfile - \
       --log-level info"]
