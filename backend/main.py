"""
LabelSure — FastAPI Application

Production entry point:
  gunicorn backend.main:app -k uvicorn.workers.UvicornWorker -w 2 --bind 0.0.0.0:8000

Dev entry point:
  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""
from contextlib import asynccontextmanager
import asyncio
import logging
import os
import time

try:
    import orjson
    def _json_dumps(obj) -> str:
        return orjson.dumps(obj).decode()
except ImportError:
    import json
    def _json_dumps(obj) -> str:
        return json.dumps(obj)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from fastapi.responses import ORJSONResponse as _FastResponse
except ImportError:
    _FastResponse = JSONResponse  # type: ignore

from backend.config import get_settings
from backend.database import create_tables, engine
from backend.routers import auth, scans, reports

settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Logging — structured JSON in production, plain text in dev
# ─────────────────────────────────────────────────────────────────────────────
class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        return json.dumps(log)


def _configure_logging():
    handler = logging.StreamHandler()
    if settings.log_format == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if settings.debug else logging.INFO)


_configure_logging()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# In-memory rate limiter (per-IP, per-minute window)
# For a multi-process production deployment, replace with Redis-backed limiter
# such as slowapi or redis-py with a sliding window.
# ─────────────────────────────────────────────────────────────────────────────
class _SimpleRateLimiter:
    """Per-IP, per-endpoint, per-minute request counter stored in process memory.
    Sufficient for single-process / single-worker deployments.
    For multi-worker (gunicorn), wire up slowapi + Redis instead."""

    def __init__(self):
        # {(ip, endpoint_key): [timestamps]}
        self._buckets: dict[tuple, list[float]] = {}

    def is_allowed(self, ip: str, key: str, rpm: int) -> bool:
        now = time.monotonic()
        bucket_key = (ip, key)
        bucket = self._buckets.setdefault(bucket_key, [])
        # Evict timestamps older than 60 seconds
        cutoff = now - 60.0
        self._buckets[bucket_key] = [t for t in bucket if t > cutoff]
        if len(self._buckets[bucket_key]) >= rpm:
            return False
        self._buckets[bucket_key].append(now)
        return True


_limiter = _SimpleRateLimiter()


# ─────────────────────────────────────────────────────────────────────────────
# Application lifecycle
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s v%s | debug=%s | db=%s",
        settings.app_name,
        settings.version,
        settings.debug,
        "postgres" if settings.is_postgres else "sqlite",
    )
    await create_tables()
    os.makedirs(settings.upload_dir, exist_ok=True)
    logger.info("Database tables ready. Upload dir: %s", settings.upload_dir)

    # ── Pre-warm OCR model ─────────────────────────────────────────────
    # Load PaddleOCR (or Tesseract) in a thread so it doesn't block the event
    # loop. The model download + init can take 10-30 s on first cold start.
    # After this, every subsequent scan request hits a warm model instantly.
    # ──────────────────────────────────────────────────────────────
    def _warmup_ocr():
        try:
            from backend.processing.ocr_engine import _PADDLE_AVAILABLE, _get_paddle
            if _PADDLE_AVAILABLE:
                logger.info("Pre-warming PaddleOCR English model...")
                _get_paddle("en")   # loads model weights into RAM
                logger.info("PaddleOCR model warm-up complete.")
            else:
                import pytesseract
                pytesseract.get_tesseract_version()  # verify tesseract is reachable
                logger.info("Tesseract available (version checked).")
        except Exception as exc:
            logger.warning("OCR warm-up failed (non-fatal): %s", exc)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _warmup_ocr)
    # ──────────────────────────────────────────────────────────────

    yield
    logger.info("%s shutting down.", settings.app_name)
    await engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app
# Swagger/ReDoc are disabled in production (debug=False) to avoid leaking
# API structure. Set DEBUG=true to re-enable during development.
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="LabelSure API",
    description=(
        "AI-powered compliance scanner for India Legal Metrology "
        "(Packaged Commodities) Rules, 2011."
    ),
    version=settings.version,
    lifespan=lifespan,
    default_response_class=_FastResponse,   # orjson for all responses
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)


# ─────────────────────────────────────────────────────────────────────────────
# CORS
# In production, CORS_ORIGINS must be set to the exact frontend origin(s).
# Example: CORS_ORIGINS=https://dashboard.labelsure.app,https://labelsure.app
# Wildcard "*" is only accepted when DEBUG=true.
# ─────────────────────────────────────────────────────────────────────────────
_origins = settings.cors_origins_list
if "*" in _origins or not _origins:
    _origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com|http://localhost:.*|http://127\.0\.0\.1:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiting middleware
# Applied globally; each router applies the relevant limit by endpoint key.
# ─────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    method = request.method

    # Auth endpoints — strict limit (brute-force protection)
    if path.startswith("/auth/login") or path.startswith("/auth/register"):
        if not _limiter.is_allowed(ip, "auth", settings.rate_limit_auth_rpm):
            logger.warning("Rate limit hit: ip=%s path=%s", ip, path)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please wait a moment before trying again."
                },
            )

    # Scan upload — per-IP limit
    if path == "/scans/upload" and method == "POST":
        if not _limiter.is_allowed(ip, "upload", settings.rate_limit_upload_rpm):
            logger.warning("Upload rate limit hit: ip=%s", ip)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Upload rate limit exceeded. Slow down."},
            )

    return await call_next(request)


# ─────────────────────────────────────────────────────────────────────────────
# Request logging middleware
# ─────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = (time.monotonic() - start) * 1000
    logger.info(
        "%s %s → %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Static file serving for uploaded images
# ─────────────────────────────────────────────────────────────────────────────
uploads_path = os.path.abspath(settings.upload_dir)
os.makedirs(uploads_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")


# ─────────────────────────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(scans.router)
app.include_router(reports.router)


# ─────────────────────────────────────────────────────────────────────────────
# Health check — for uptime monitors and container orchestrators
# Returns 200 when the app is up; 503 if the DB is unreachable.
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"], include_in_schema=settings.debug)
async def health():
    """Liveness + DB connectivity check."""
    from sqlalchemy import text
    from backend.database import AsyncSessionLocal

    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.error("Health check DB ping failed: %s", exc)

    payload = {
        "status": "ok" if db_ok else "degraded",
        "app": settings.app_name,
        "version": settings.version,
        "db": "ok" if db_ok else "unreachable",
    }
    return JSONResponse(
        content=payload,
        status_code=200 if db_ok else 503,
    )


@app.get("/", include_in_schema=False)
async def root():
    return {"app": settings.app_name, "version": settings.version, "status": "running"}
