"""
LabelSure — Scans Router
POST /scans/upload    — upload label image, run full pipeline, return verdict
GET  /scans           — list scans (officers see all; consumers see own)
GET  /scans/{scan_id} — get full scan detail including rule results
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.auth import get_current_user, get_optional_user
from backend.config import get_settings
from backend.database import get_db
from backend.models import AuditLog, ExtractedField, RuleViolation, Scan, User
from backend.processing.ocr_engine import run_ocr
from backend.processing.cv_geometry import measure_min_font_height_mm, extract_image_dpi
from backend.processing.nlp_lang import detect_language
from backend.processing.field_extractor import extract_fields
from backend.rules import evaluate_label, LabelData
from backend.schemas import (
    ScanDetail, ScanListItem, ScanListResponse, ScanUploadResponse, TextScanRequest,
    ExtractedFieldOut, RuleViolationOut,
)

router = APIRouter(prefix="/scans", tags=["Scans"])
settings = get_settings()
OFFICER_ROLES = ("officer", "admin")


def _verdict_str(verdict) -> str:
    """Convert a rules-engine Verdict to a plain string."""
    if hasattr(verdict, "value"):
        return verdict.value
    return str(verdict)


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
    Upload a product label image. Pipeline:
    1. Validate & save image.
    2. Run OCR (PaddleOCR → Tesseract fallback).
    3. Detect language; re-run OCR with Indic model if needed.
    4. Measure font height via CV.
    5. Extract structured fields.
    6. Run rules engine.
    7. Persist results to DB.
    8. Return verdict.
    """
    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/jpg"):
        raise HTTPException(400, detail="Only JPEG, PNG, or WEBP images are accepted.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(413, detail=f"Image exceeds {settings.max_upload_size_mb} MB limit.")

    # Save image
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_ext = Path(file.filename or "label.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4()}{file_ext}"
    image_path = upload_dir / filename
    with open(image_path, "wb") as fh:
        fh.write(content)

    # Step 1: OCR with primary English/bilingual model
    try:
        ocr_result = run_ocr(str(image_path), lang_code="en")
        logger.info(
            "OCR result for '%s' (engine=%s, chars=%d, min_conf=%.2f):\n%s",
            image_path,
            ocr_result.engine_used,
            len(ocr_result.full_text),
            ocr_result.min_confidence,
            ocr_result.full_text,
        )
    except Exception as exc:
        logger.error(
            "OCR failed for image '%s': %s",
            image_path,
            exc,
            exc_info=True,
        )
        ocr_result = OCRResult(boxes=[], full_text="", min_confidence=0.0, avg_confidence=0.0, engine_used="none")

    # Step 2: Language detection (detects Indic Unicode script only if present)
    lang_code = detect_language(ocr_result.full_text)

    # Step 3: Re-run with Indic model only if Indic script was explicitly detected
    if lang_code != "en":
        try:
            ocr_lang = run_ocr(str(image_path), lang_code=lang_code)
            # Only use Indic OCR if it extracted more content
            if len(ocr_lang.full_text.strip()) > len(ocr_result.full_text.strip()):
                ocr_result = ocr_lang
        except Exception as exc:
            logger.warning("Indic OCR pass failed (%s), keeping primary result.", exc)


    # Step 4: CV font height
    dpi = extract_image_dpi(str(image_path))
    font_height_mm = measure_min_font_height_mm(
        str(image_path),
        ocr_result.boxes,
        dpi=dpi,
        reference_width_mm=reference_width_mm,
        reference_width_px=reference_width_px,
    )

    # Step 5: Field extraction
    label_data: LabelData = extract_fields(ocr_result, lang_code=lang_code)
    label_data.font_type = font_type
    label_data.measured_font_height_mm = font_height_mm
    label_data.entered_sale_price = sale_price

    # Step 6: Rules engine
    verdict = evaluate_label(label_data, ocr_confidence=ocr_result.min_confidence)
    verdict_str = (
        "NEEDS_REVIEW" if verdict.needs_manual_review
        else "COMPLIANT" if verdict.is_compliant
        else "NON_COMPLIANT"
    )

    now_dt = datetime.utcnow()

    try:
        # Step 7: Persist
        scan = Scan(
            user_id=current_user.id if current_user else None,
            image_path=str(image_path),
            image_filename=file.filename,
            verdict=verdict_str,
            overall_confidence=ocr_result.min_confidence,
            needs_manual_review=verdict.needs_manual_review,
            review_reason=verdict.review_reason,
            detected_language=lang_code,
            created_at=now_dt,
            processed_at=now_dt,
            entered_sale_price=sale_price,
        )
        db.add(scan)
        await db.flush()  # get scan.id

        field_map = {
            "generic_name": label_data.generic_name,
            "manufacturer_name": label_data.manufacturer_name,
            "manufacturer_address": label_data.manufacturer_address,
            "net_quantity_value": str(label_data.net_quantity_value) if label_data.net_quantity_value else None,
            "net_quantity_unit": label_data.net_quantity_unit,
            "mrp": str(label_data.mrp) if label_data.mrp else None,
            "manufacture_month": str(label_data.manufacture_month) if label_data.manufacture_month else None,
            "manufacture_year": str(label_data.manufacture_year) if label_data.manufacture_year else None,
            "batch_number": label_data.batch_number,
            "expiry_date": label_data.expiry_date,
            "fssai_license": label_data.fssai_license,
            "consumer_care": label_data.consumer_care,
            "measured_font_height_mm": str(font_height_mm) if font_height_mm else None,
        }
        for fname, fval in field_map.items():
            db.add(ExtractedField(
                scan_id=scan.id,
                field_name=fname,
                field_value=fval,
                confidence=ocr_result.avg_confidence,
            ))

        rule_results_out = []
        for rr in verdict.rule_results:
            sev = rr.severity.value if hasattr(rr.severity, "value") else str(rr.severity)
            db.add(RuleViolation(
                scan_id=scan.id,
                rule_id=rr.rule_id,
                rule_name=rr.rule_name,
                passed=rr.passed,
                explanation=rr.explanation,
                severity=sev,
            ))
            rule_results_out.append(RuleViolationOut(
                rule_id=rr.rule_id,
                rule_name=rr.rule_name,
                passed=rr.passed,
                explanation=rr.explanation,
                severity=sev,
            ))

        db.add(AuditLog(
            scan_id=scan.id,
            performed_by=current_user.id if current_user else None,
            action="SCAN_UPLOADED",
            detail=f"Verdict: {verdict_str}",
            timestamp=now_dt,
        ))

        await db.commit()
        await db.refresh(scan)

        return ScanUploadResponse(
            scan_id=scan.id,
            verdict=verdict_str,
            overall_confidence=ocr_result.min_confidence,
            needs_manual_review=verdict.needs_manual_review,
            review_reason=verdict.review_reason,
            detected_language=lang_code,
            raw_ocr_text=ocr_result.full_text[:4000] if ocr_result.full_text else None,
            ocr_engine=ocr_result.engine_used,
            extracted_fields=[
                ExtractedFieldOut(field_name=k, field_value=v, confidence=ocr_result.avg_confidence, bounding_box=None)
                for k, v in field_map.items() if v is not None
            ],
            rule_results=rule_results_out,
            created_at=scan.created_at or now_dt,
            processed_at=scan.processed_at or now_dt,
        )
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to persist scan '%s': %s", image_path, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process and save scan: {exc}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# POST /scans/analyze-text  (on-device OCR fast path)
# Flutter app sends pre-extracted text from Google ML Kit — no image upload needed.
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/analyze-text", response_model=ScanUploadResponse, status_code=201)
async def analyze_text_scan(
    body: TextScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Fast-path endpoint for on-device OCR.

    The Flutter app runs Google ML Kit OCR locally, then sends only the extracted
    text here. We skip image upload/storage and go straight to:
      field extraction → compliance rules → return verdict.

    This is ~10x faster than /scans/upload because:
      - No multipart file transfer
      - No server-side OCR (Tesseract/PaddleOCR)
      - Only field extraction + rules evaluation (~100ms)
    """
    logger.info(
        "analyze-text: lang=%s, chars=%d, user=%s",
        body.lang_code, len(body.ocr_text),
        current_user.id if current_user else "anonymous",
    )

    if not body.ocr_text.strip():
        raise HTTPException(status_code=422, detail="ocr_text must not be empty.")

    # Build a minimal OCRResult from the provided text
    from backend.processing.ocr_engine import OCRResult
    ocr_result = OCRResult(
        full_text=body.ocr_text,
        boxes=[],
        avg_confidence=0.9,    # ML Kit is generally high confidence
        min_confidence=0.85,
        engine_used="mlkit",
    )

    # Language detection & sanitization
    detected_lang = detect_language(body.ocr_text)
    effective_lang = detected_lang if (detected_lang == "en" and body.lang_code != "en") else (body.lang_code or detected_lang)

    # Field extraction
    label_data = extract_fields(ocr_result, lang_code=effective_lang)
    if body.sale_price is not None:
        label_data.entered_sale_price = body.sale_price
    if body.font_type:
        label_data.font_type = body.font_type

    # Rules evaluation
    verdict = evaluate_label(label_data, ocr_confidence=ocr_result.min_confidence)
    verdict_str = (
        "NEEDS_REVIEW" if verdict.needs_manual_review
        else "COMPLIANT" if verdict.is_compliant
        else "NON_COMPLIANT"
    )

    now_dt = datetime.utcnow()

    try:
        scan = Scan(
            user_id=current_user.id if current_user else None,
            image_path="on_device_ocr",
            image_filename="on_device_ocr.txt",
            verdict=verdict_str,
            overall_confidence=ocr_result.min_confidence,
            needs_manual_review=verdict.needs_manual_review,
            review_reason=verdict.review_reason,
            detected_language=effective_lang,
            created_at=now_dt,
            processed_at=now_dt,
            entered_sale_price=body.sale_price,
        )
        db.add(scan)
        await db.flush()

        field_map = {
            "generic_name":         label_data.generic_name,
            "manufacturer_name":    label_data.manufacturer_name,
            "manufacturer_address": label_data.manufacturer_address,
            "net_quantity_value":   str(label_data.net_quantity_value) if label_data.net_quantity_value else None,
            "net_quantity_unit":    label_data.net_quantity_unit,
            "mrp":                  str(label_data.mrp) if label_data.mrp else None,
            "manufacture_month":    str(label_data.manufacture_month) if label_data.manufacture_month else None,
            "manufacture_year":     str(label_data.manufacture_year) if label_data.manufacture_year else None,
            "batch_number":         label_data.batch_number,
            "expiry_date":          label_data.expiry_date,
            "fssai_license":        label_data.fssai_license,
            "consumer_care":        label_data.consumer_care,
            "ocr_source":           "mlkit_on_device",
        }
        for fname, fval in field_map.items():
            db.add(ExtractedField(
                scan_id=scan.id,
                field_name=fname,
                field_value=fval,
                confidence=ocr_result.avg_confidence,
            ))

        rule_results_out = []
        for rr in verdict.rule_results:
            sev = rr.severity.value if hasattr(rr.severity, "value") else str(rr.severity)
            db.add(RuleViolation(
                scan_id=scan.id,
                rule_id=rr.rule_id,
                rule_name=rr.rule_name,
                passed=rr.passed,
                explanation=rr.explanation,
                severity=sev,
            ))
            rule_results_out.append(RuleViolationOut(
                rule_id=rr.rule_id,
                rule_name=rr.rule_name,
                passed=rr.passed,
                explanation=rr.explanation,
                severity=sev,
            ))

        db.add(AuditLog(
            scan_id=scan.id,
            performed_by=current_user.id if current_user else None,
            action="TEXT_SCAN",
            detail=f"Verdict: {verdict_str} | Engine: mlkit | Chars: {len(body.ocr_text)}",
            timestamp=now_dt,
        ))

        await db.commit()
        await db.refresh(scan)

        return ScanUploadResponse(
            scan_id=scan.id,
            verdict=verdict_str,
            overall_confidence=ocr_result.min_confidence,
            needs_manual_review=verdict.needs_manual_review,
            review_reason=verdict.review_reason,
            detected_language=effective_lang,
            raw_ocr_text=body.ocr_text[:4000],
            ocr_engine="mlkit",
            extracted_fields=[
                ExtractedFieldOut(
                    field_name=k, field_value=v,
                    confidence=ocr_result.avg_confidence, bounding_box=None,
                )
                for k, v in field_map.items() if v is not None
            ],
            rule_results=rule_results_out,
            created_at=scan.created_at or now_dt,
            processed_at=scan.processed_at or now_dt,
        )
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to persist text scan: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process scan: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# GET /scans
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=ScanListResponse)
async def list_scans(
    verdict_filter: Optional[str] = Query(None, alias="verdict"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Officers/Admins see all scans; consumers/sellers see only their own."""
    query = select(Scan)

    if current_user.role not in OFFICER_ROLES:
        query = query.where(Scan.user_id == current_user.id)

    if verdict_filter:
        query = query.where(Scan.verdict == verdict_filter.upper())

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

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
    result = await db.execute(
        select(Scan)
        .where(Scan.id == scan_id)
        .options(
            selectinload(Scan.extracted_fields),
            selectinload(Scan.rule_violations),
            selectinload(Scan.user),
        )
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(404, detail="Scan not found.")

    if current_user.role not in OFFICER_ROLES:
        if scan.user_id != current_user.id:
            raise HTTPException(403, detail="Access denied.")

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
