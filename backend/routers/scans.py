"""
LabelSure — Scans Router
POST /scans/upload    — upload label image, run full pipeline, return verdict
GET  /scans           — list scans (officers see all; consumers see own)
GET  /scans/{scan_id} — get full scan detail including rule results
"""
from __future__ import annotations
import asyncio
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.auth import get_current_user, get_optional_user
from backend.config import get_settings
from backend.database import get_db
from backend.models import (
    AuditLog, ExtractedField, RuleViolation, Scan, User, UserRole, Verdict as VerdictEnum,
)
from backend.processing.ocr_engine import run_ocr
from backend.processing.cv_geometry import measure_min_font_height_mm, extract_image_dpi
from backend.processing.nlp_lang import detect_language
from backend.processing.field_extractor import extract_fields
from backend.rules import evaluate_label, LabelData
from backend.schemas import ScanDetail, ScanListItem, ScanListResponse, ScanUploadResponse

router = APIRouter(prefix="/scans", tags=["Scans"])
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# POST /scans/upload
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=ScanUploadResponse, status_code=201)
async def upload_scan(
    file: UploadFile = File(..., description="Label image (JPEG/PNG/WEBP)"),
    sale_price: Optional[float] = Form(None, description="Sale price in INR (for Rule 18(2) check)"),
    font_type: str = Form("printed", description="printed | embossed"),
    reference_width_mm: Optional[float] = Form(None),
    reference_width_px: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Upload a product label image. The pipeline:
    1. Save image to disk.
    2. Run OCR (PaddleOCR → Tesseract fallback).
    3. Detect language.
    4. Re-run OCR with language-appropriate model if needed.
    5. Measure font height via CV (if calibration data available).
    6. Extract structured fields.
    7. Run rules engine.
    8. Persist scan + results to DB.
    9. Return immediate verdict.
    """
    # --- Validate file ---
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/jpg"):
        raise HTTPException(400, detail="Only JPEG, PNG, or WEBP images are accepted.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(413, detail=f"Image exceeds {settings.max_upload_size_mb} MB limit.")

    # --- Save image ---
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_ext = Path(file.filename or "label.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4()}{file_ext}"
    image_path = upload_dir / filename
    with open(image_path, "wb") as f:
        f.write(content)

    # --- Step 1: Initial OCR with English model ---
    try:
        ocr_result = run_ocr(str(image_path), lang_code="en")
    except Exception as e:
        ocr_result_empty = type("OCRResult", (), {
            "full_text": "", "min_confidence": 0.0, "avg_confidence": 0.0,
            "boxes": [], "engine_used": "none"
        })()
        ocr_result = ocr_result_empty

    # --- Step 2: Detect language ---
    lang_code = detect_language(ocr_result.full_text)

    # --- Step 3: Re-run OCR with correct language model if non-English ---
    if lang_code != "en":
        try:
            ocr_result_lang = run_ocr(str(image_path), lang_code=lang_code)
            # Use whichever result has higher confidence
            if ocr_result_lang.min_confidence >= ocr_result.min_confidence:
                ocr_result = ocr_result_lang
        except Exception:
            pass  # Keep English result

    # --- Step 4: CV font height measurement ---
    dpi = extract_image_dpi(str(image_path))
    font_height_mm = measure_min_font_height_mm(
        str(image_path),
        ocr_result.boxes,
        dpi=dpi,
        reference_width_mm=reference_width_mm,
        reference_width_px=reference_width_px,
    )

    # --- Step 5: Extract structured fields ---
    label_data: LabelData = extract_fields(ocr_result, lang_code=lang_code)
    label_data.font_type = font_type
    label_data.measured_font_height_mm = font_height_mm
    label_data.entered_sale_price = sale_price

    # --- Step 6: Run rules engine ---
    verdict = evaluate_label(label_data, ocr_confidence=ocr_result.min_confidence)

    # --- Step 7: Persist to database ---
    verdict_enum = (
        VerdictEnum.needs_review if verdict.needs_manual_review else
        VerdictEnum.compliant if verdict.is_compliant else
        VerdictEnum.non_compliant
    )

    scan = Scan(
        user_id=current_user.id if current_user else None,
        image_path=str(image_path),
        image_filename=file.filename,
        verdict=verdict_enum,
        overall_confidence=ocr_result.min_confidence,
        needs_manual_review=verdict.needs_manual_review,
        review_reason=verdict.review_reason,
        detected_language=lang_code,
        processed_at=datetime.now(timezone.utc),
        entered_sale_price=sale_price,
    )
    db.add(scan)
    await db.flush()  # get scan.id

    # Persist extracted fields
    field_map = {
        "manufacturer_name": label_data.manufacturer_name,
        "manufacturer_address": label_data.manufacturer_address,
        "generic_name": label_data.generic_name,
        "net_quantity_value": str(label_data.net_quantity_value) if label_data.net_quantity_value else None,
        "net_quantity_unit": label_data.net_quantity_unit,
        "mrp": str(label_data.mrp) if label_data.mrp else None,
        "manufacture_month": str(label_data.manufacture_month) if label_data.manufacture_month else None,
        "manufacture_year": str(label_data.manufacture_year) if label_data.manufacture_year else None,
        "measured_font_height_mm": str(font_height_mm) if font_height_mm else None,
    }
    for fname, fval in field_map.items():
        ef = ExtractedField(
            scan_id=scan.id,
            field_name=fname,
            field_value=fval,
            confidence=ocr_result.avg_confidence,
        )
        db.add(ef)

    # Persist rule results
    for rr in verdict.rule_results:
        rv = RuleViolation(
            scan_id=scan.id,
            rule_id=rr.rule_id,
            rule_name=rr.rule_name,
            passed=rr.passed,
            explanation=rr.explanation,
            severity=rr.severity.value,
        )
        db.add(rv)

    # Audit log
    al = AuditLog(
        scan_id=scan.id,
        performed_by=current_user.id if current_user else None,
        action="SCAN_UPLOADED",
        detail=f"Verdict: {verdict_enum.value}",
    )
    db.add(al)

    await db.commit()
    await db.refresh(scan)

    # --- Build response ---
    from backend.schemas import ExtractedFieldOut, RuleViolationOut
    return ScanUploadResponse(
        scan_id=scan.id,
        verdict=verdict_enum,
        overall_confidence=ocr_result.min_confidence,
        needs_manual_review=verdict.needs_manual_review,
        review_reason=verdict.review_reason,
        detected_language=lang_code,
        extracted_fields=[
            ExtractedFieldOut(
                field_name=k,
                field_value=v,
                confidence=ocr_result.avg_confidence,
                bounding_box=None,
            )
            for k, v in field_map.items() if v is not None
        ],
        rule_results=[
            RuleViolationOut(
                rule_id=rr.rule_id,
                rule_name=rr.rule_name,
                passed=rr.passed,
                explanation=rr.explanation,
                severity=rr.severity.value,
            )
            for rr in verdict.rule_results
        ],
        created_at=scan.created_at,
        processed_at=scan.processed_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /scans
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=ScanListResponse)
async def list_scans(
    verdict_filter: Optional[str] = Query(None, alias="verdict"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List scans.
    - Officers/Admins see all scans (with optional filters).
    - Consumers/Sellers see only their own scans.
    """
    query = select(Scan)

    if current_user.role not in (UserRole.officer, UserRole.admin):
        query = query.where(Scan.user_id == current_user.id)

    if verdict_filter:
        try:
            vf = VerdictEnum(verdict_filter.upper())
            query = query.where(Scan.verdict == vf)
        except ValueError:
            pass

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginate
    query = query.order_by(Scan.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    scans = result.scalars().all()

    return ScanListResponse(
        items=[ScanListItem.model_validate(s) for s in scans],
        total=total,
        page=page,
        page_size=page_size,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /scans/{scan_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{scan_id}", response_model=ScanDetail)
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details for a single scan (extracted fields + rule results)."""
    try:
        sid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(400, detail="Invalid scan ID format.")

    result = await db.execute(
        select(Scan)
        .where(Scan.id == sid)
        .options(
            selectinload(Scan.extracted_fields),
            selectinload(Scan.rule_violations),
            selectinload(Scan.user),
        )
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(404, detail="Scan not found.")

    # Access control: consumers/sellers can only see their own scans
    if current_user.role not in (UserRole.officer, UserRole.admin):
        if scan.user_id != current_user.id:
            raise HTTPException(403, detail="Access denied.")

    from backend.schemas import ExtractedFieldOut, RuleViolationOut
    return ScanDetail(
        id=scan.id,
        verdict=scan.verdict,
        overall_confidence=scan.overall_confidence,
        needs_manual_review=scan.needs_manual_review,
        review_reason=scan.review_reason,
        detected_language=scan.detected_language,
        image_filename=scan.image_filename,
        image_path=scan.image_path,
        created_at=scan.created_at,
        processed_at=scan.processed_at,
        entered_sale_price=scan.entered_sale_price,
        extracted_fields=[ExtractedFieldOut.model_validate(ef) for ef in scan.extracted_fields],
        rule_results=[RuleViolationOut.model_validate(rv) for rv in scan.rule_violations],
        user=scan.user,
    )
