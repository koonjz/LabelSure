"""
LabelSure — Database Engine Tests
Tests for Database URL normalization (SQLite, standard Postgres, and Neon Serverless Postgres).
"""
import pytest
from backend.database import _get_normalized_db_url


def test_sqlite_url_normalization():
    url = "sqlite+aiosqlite:///./test.db"
    norm_url, connect_args = _get_normalized_db_url(url)
    assert norm_url == url
    assert connect_args == {"check_same_thread": False}


def test_postgres_url_scheme_normalization():
    raw_url = "postgres://user:pass@localhost:5432/labelsure"
    norm_url, connect_args = _get_normalized_db_url(raw_url)
    assert norm_url.startswith("postgresql+asyncpg://")


def test_neon_postgres_url_normalization():
    neon_url = "postgres://alex:secret123@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require"
    norm_url, connect_args = _get_normalized_db_url(neon_url)
    assert norm_url.startswith("postgresql+asyncpg://")
    assert connect_args.get("ssl") == "require"


def test_neon_pooled_endpoint_normalization():
    neon_pooled_url = "postgresql://alex:secret123@ep-cool-darkness-123456-pooler.us-east-2.aws.neon.tech/neondb"
    norm_url, connect_args = _get_normalized_db_url(neon_pooled_url)
    assert norm_url.startswith("postgresql+asyncpg://")
    assert connect_args.get("ssl") == "require"
