"""
LabelSure — FastAPI Application Entry Point
Run with: uvicorn backend.main:app --reload
"""
from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.database import create_tables
from backend.routers import auth, scans, reports

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Application lifecycle
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    # Auto-create tables on startup (use Alembic for production migrations)
    await create_tables()
    # Ensure upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)
    logger.info("Database tables ready.")
    yield
    logger.info(f"{settings.app_name} shutting down.")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="LabelSure API",
    description=(
        "AI-powered compliance scanner for India Legal Metrology "
        "(Packaged Commodities) Rules, 2011."
    ),
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow Flutter app and web dashboard origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploaded images
uploads_path = os.path.abspath(settings.upload_dir)
os.makedirs(uploads_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

# ─────────────────────────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(scans.router)
app.include_router(reports.router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.version}
