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
from backend.models import Scan, User, UserRole, Verdict as VerdictEnum

router = APIRouter(prefix="/reports", tags=["Reports"])


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
        try:
            query = query.where(Scan.verdict == VerdictEnum(verdict_filter.upper()))
        except ValueError:
            pass

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
                "verdict": s.verdict.value if s.verdict else None,
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
            "Verdict": s.verdict.value if s.verdict else "UNKNOWN",
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
