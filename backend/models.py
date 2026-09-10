"""
LabelSure — ORM Models
SQLAlchemy models for: users, scans, extracted_fields, rule_violations, audit_log.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Float, Integer, DateTime,
    ForeignKey, Text, Enum as SAEnum, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class UserRole(str, enum.Enum):
    officer = "officer"
    consumer = "consumer"
    seller = "seller"
    admin = "admin"


class Verdict(str, enum.Enum):
    compliant = "COMPLIANT"
    non_compliant = "NON_COMPLIANT"
    needs_review = "NEEDS_REVIEW"


# ─────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.consumer)
    region = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    audit_entries = relationship("AuditLog", back_populates="performed_by_user")


# ─────────────────────────────────────────────
# Scans
# ─────────────────────────────────────────────
class Scan(Base):
    __tablename__ = "scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    image_path = Column(String(512), nullable=False)
    image_filename = Column(String(255), nullable=True)

    # Compliance result
    verdict = Column(SAEnum(Verdict), nullable=True)
    overall_confidence = Column(Float, nullable=True)  # 0.0–1.0 (min OCR confidence across fields)
    needs_manual_review = Column(Boolean, default=False)
    review_reason = Column(Text, nullable=True)

    # Detected language
    detected_language = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

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
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)   # e.g. "manufacturer_name", "mrp", "net_quantity"
    field_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)           # OCR confidence for this field
    bounding_box = Column(String(255), nullable=True)  # JSON string: {"x":..,"y":..,"w":..,"h":..}

    scan = relationship("Scan", back_populates="extracted_fields")


# ─────────────────────────────────────────────
# Rule Violations
# ─────────────────────────────────────────────
class RuleViolation(Base):
    __tablename__ = "rule_violations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(50), nullable=False)         # e.g. "RULE_6_1_A"
    rule_name = Column(String(255), nullable=False)
    passed = Column(Boolean, nullable=False)
    explanation = Column(Text, nullable=True)             # plain-language reason
    severity = Column(String(20), nullable=True, default="error")  # error | warning | info

    scan = relationship("Scan", back_populates="rule_violations")


# ─────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=True, index=True)
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)   # "SCAN_UPLOADED", "VERDICT_ISSUED", "REPORT_EXPORTED"
    detail = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    scan = relationship("Scan", back_populates="audit_log")
    performed_by_user = relationship("User", back_populates="audit_entries")
