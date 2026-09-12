"""
LabelSure — Reports Router
GET /reports/export  — Officer-only: export scan history as CSV or JSON
"""
import csv
import io
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_officer
from backend.database import get_db
from backend.models import RuleViolation, Scan, User

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_officer),
):
    """
    Officer-only: get aggregated Legal Metrology compliance metrics & rule violation distribution.
    """
    # 1. Total counts
    scans_result = await db.execute(select(Scan))
    scans = scans_result.scalars().all()
    total_scans = len(scans)
    compliant_count = sum(1 for s in scans if s.verdict == "COMPLIANT")
    non_compliant_count = sum(1 for s in scans if s.verdict == "NON_COMPLIANT")
    needs_review_count = sum(1 for s in scans if s.verdict == "NEEDS_REVIEW" or s.needs_manual_review)
    compliance_rate = round((compliant_count / total_scans) * 100, 1) if total_scans > 0 else 100.0

    # 2. Rule violations breakdown
    violations_query = select(RuleViolation).where(
        RuleViolation.passed == False,
        RuleViolation.severity != "info",
    )
    violations_result = await db.execute(violations_query)
    violations = violations_result.scalars().all()

    rule_counts = {
        "Rule 6(1)(a) Name & Address": 0,
        "Rule 6(1) Generic Name": 0,
        "Rule 6(1) Net Quantity & Font Height": 0,
        "Rule 6(1) MRP Inclusive of Taxes": 0,
        "Rule 6(1) Month & Year of Mfg/Pkg": 0,
        "Rule 18(2) Dual Pricing Check": 0,
    }

    for v in violations:
        rule_id = (v.rule_id or "").upper()
        rule_name = (v.rule_name or "").lower()

        if "6_1_A" in rule_id or "address" in rule_name or "manufacturer" in rule_name or "packer" in rule_name:
            rule_counts["Rule 6(1)(a) Name & Address"] += 1
        elif "6_1_B" in rule_id or "6_1_GENERIC" in rule_id or "generic" in rule_name or "commodity" in rule_name:
            rule_counts["Rule 6(1) Generic Name"] += 1
        elif "6_1_C" in rule_id or "6_1_NET" in rule_id or "font" in rule_name or "net quantity" in rule_name or "7" in rule_id:
            rule_counts["Rule 6(1) Net Quantity & Font Height"] += 1
        elif "6_1_D" in rule_id or "6_1_MRP" in rule_id or "mrp" in rule_name or "tax" in rule_name:
            rule_counts["Rule 6(1) MRP Inclusive of Taxes"] += 1
        elif "6_1_E" in rule_id or "6_1_DATE" in rule_id or "mfg" in rule_name or "month" in rule_name or "year" in rule_name or "pack" in rule_name:
            rule_counts["Rule 6(1) Month & Year of Mfg/Pkg"] += 1
        elif "18_2" in rule_id or "18(2)" in rule_id or "dual" in rule_name or "sale price" in rule_name:
            rule_counts["Rule 18(2) Dual Pricing Check"] += 1

    return {
        "total_scans": total_scans,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "needs_review_count": needs_review_count,
        "compliance_rate": compliance_rate,
        "rule_counts": rule_counts,
    }



@router.get("/export")
async def export_scans(
    fmt: str = Query("csv", description="Export format: csv | json"),
    verdict_filter: Optional[str] = Query(None, alias="verdict"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_officer),
):
    """
    Export scan records for reporting. Officer/Admin role required.
    Filterable by verdict, date range, and region.
    """
    query = select(Scan)

    if verdict_filter:
        query = query.where(Scan.verdict == verdict_filter.upper())

    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            query = query.where(Scan.created_at >= dt)
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.where(Scan.created_at <= dt)
        except ValueError:
            pass

    query = query.order_by(Scan.created_at.desc()).limit(10000)
    result = await db.execute(query)
    scans = result.scalars().all()

    if fmt.lower() == "json":
        import json
        data = [
            {
                "id": str(s.id),
                "verdict": s.verdict,
                "needs_manual_review": s.needs_manual_review,
                "detected_language": s.detected_language,
                "overall_confidence": s.overall_confidence,
                "image_filename": s.image_filename,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in scans
        ]
        return StreamingResponse(
            io.StringIO(json.dumps(data, indent=2)),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=labelsure_report.json"},
        )

    # Default: CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "Scan ID", "Verdict", "Needs Review", "Language", "Confidence",
        "Image Filename", "Timestamp"
    ])
    writer.writeheader()
    for s in scans:
        writer.writerow({
            "Scan ID": str(s.id),
            "Verdict": s.verdict or "UNKNOWN",
            "Needs Review": "Yes" if s.needs_manual_review else "No",
            "Language": s.detected_language or "en",
            "Confidence": f"{(s.overall_confidence or 0) * 100:.1f}%",
            "Image Filename": s.image_filename or "",
            "Timestamp": s.created_at.isoformat() if s.created_at else "",
        })
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=labelsure_report.csv"},
    )
