"""
LabelSure — Pydantic Schemas (API request/response models)
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator
from backend.models import UserRole, Verdict


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.consumer
    region: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    role: UserRole
    region: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─────────────────────────────────────────────
# Extracted Fields
# ─────────────────────────────────────────────
class ExtractedFieldOut(BaseModel):
    field_name: str
    field_value: Optional[str]
    confidence: Optional[float]
    bounding_box: Optional[str]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Rule Violations
# ─────────────────────────────────────────────
class RuleViolationOut(BaseModel):
    rule_id: str
    rule_name: str
    passed: bool
    explanation: Optional[str]
    severity: Optional[str]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Scans
# ─────────────────────────────────────────────
class ScanUploadResponse(BaseModel):
    scan_id: UUID
    verdict: Optional[Verdict]
    overall_confidence: Optional[float]
    needs_manual_review: bool
    review_reason: Optional[str]
    detected_language: Optional[str]
    extracted_fields: List[ExtractedFieldOut]
    rule_results: List[RuleViolationOut]
    created_at: datetime
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ScanListItem(BaseModel):
    id: UUID
    verdict: Optional[Verdict]
    needs_manual_review: bool
    detected_language: Optional[str]
    overall_confidence: Optional[float]
    image_filename: Optional[str]
    created_at: datetime
    user_id: Optional[UUID]

    model_config = {"from_attributes": True}


class ScanDetail(BaseModel):
    id: UUID
    verdict: Optional[Verdict]
    overall_confidence: Optional[float]
    needs_manual_review: bool
    review_reason: Optional[str]
    detected_language: Optional[str]
    image_filename: Optional[str]
    image_path: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    entered_sale_price: Optional[float]
    extracted_fields: List[ExtractedFieldOut]
    rule_results: List[RuleViolationOut]
    user: Optional[UserOut]

    model_config = {"from_attributes": True}


class ScanListResponse(BaseModel):
    items: List[ScanListItem]
    total: int
    page: int
    page_size: int


# ─────────────────────────────────────────────
# Reports
# ─────────────────────────────────────────────
class ReportFilters(BaseModel):
    verdict: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    region: Optional[str] = None
