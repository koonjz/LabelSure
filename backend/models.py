"""
LabelSure — ORM Models
Uses String(36) UUIDs so the schema works with both SQLite (local dev) and PostgreSQL (prod).
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Float, Integer, DateTime,
    ForeignKey, Text,
)
from sqlalchemy.orm import relationship

from backend.database import Base


# ─────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default="consumer")  # officer|admin|consumer|seller
    region = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    audit_entries = relationship("AuditLog", back_populates="performed_by_user")


# ─────────────────────────────────────────────
# Scans
# ─────────────────────────────────────────────
class Scan(Base):
    __tablename__ = "scans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    image_path = Column(String(512), nullable=False)
    image_filename = Column(String(255), nullable=True)

    # Compliance result
    verdict = Column(String(20), nullable=True)  # COMPLIANT | NON_COMPLIANT | NEEDS_REVIEW
    overall_confidence = Column(Float, nullable=True)
    needs_manual_review = Column(Boolean, default=False)
    review_reason = Column(Text, nullable=True)

    # Detected language
    detected_language = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime, nullable=True)

    # Sale price entered by user (for Rule 18(2) check)
    entered_sale_price = Column(Float, nullable=True)

    # Relationships
    user = relationship("User", back_populates="scans")
    extracted_fields = relationship("ExtractedField", back_populates="scan", cascade="all, delete-orphan")
    rule_violations = relationship("RuleViolation", back_populates="scan", cascade="all, delete-orphan")
    audit_log = relationship("AuditLog", back_populates="scan", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Extracted Fields
# ─────────────────────────────────────────────
class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)   # e.g. "manufacturer_name", "mrp"
    field_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    bounding_box = Column(String(255), nullable=True)  # JSON: {"x":..,"y":..,"w":..,"h":..}

    scan = relationship("Scan", back_populates="extracted_fields")


# ─────────────────────────────────────────────
# Rule Violations
# ─────────────────────────────────────────────
class RuleViolation(Base):
    __tablename__ = "rule_violations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(50), nullable=False)       # e.g. "RULE_6_1_A"
    rule_name = Column(String(255), nullable=False)
    passed = Column(Boolean, nullable=False)
    explanation = Column(Text, nullable=True)
    severity = Column(String(20), nullable=True, default="error")  # error | warning | info

    scan = relationship("Scan", back_populates="rule_violations")


# ─────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=True, index=True)
    performed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    detail = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    scan = relationship("Scan", back_populates="audit_log")
    performed_by_user = relationship("User", back_populates="audit_entries")
