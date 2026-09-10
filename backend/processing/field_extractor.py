"""
LabelSure — Field Extractor
Parses raw OCR text into structured LabelData fields using regex patterns and
heuristics. Supports English and major Indic languages.

This module runs AFTER OCR and language detection.
Input:  OCRResult (list of text boxes with confidence scores)
Output: LabelData (structured fields for the rules engine)
"""
from __future__ import annotations
import re
import logging
from typing import Optional

from backend.processing.ocr_engine import OCRResult
from backend.rules.models import LabelData

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Pattern catalogue (English + common Indic transliterations)
# ─────────────────────────────────────────────────────────────────────────────

# MRP patterns: "MRP Rs.45.00", "MRP ₹45", "M.R.P. ₹45.00", "MRP: 45"
_MRP_PATTERN = re.compile(
    r"(?:M\.?R\.?P\.?|Maximum\s+Retail\s+Price)[:\s]*"
    r"(?:Rs\.?|INR|₹)?\s*(\d{1,6}(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)

# Net quantity patterns: "Net Wt. 500g", "Net Contents 1 kg", "500 ml", "1.5L"
_NET_QTY_PATTERN = re.compile(
    r"(?:Net\s+(?:Wt\.?|Weight|Contents?|Quantity|Vol\.?|Volume)[\s:]*)??"
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(g(?:m(?:s)?)?|kg(?:s)?|ml|millilitre|l(?:tr?(?:e)?)?|litre|liter|pcs?|nos?|pieces?|number)",
    re.IGNORECASE,
)

# Manufacture date: "Mfg. Date: 06/2023", "Date of Mfg: Jun 2023", "MFD: 2023-06"
_MFG_DATE_PATTERN = re.compile(
    r"(?:Mfg\.?\s*(?:Date|Dt)?\.?|Date\s+of\s+(?:Mfg|Manufacture|Mfgr|Manuf)\.?|MFD\.?|Packed\s+On)[:\s]*"
    r"(?:"
    r"(\d{1,2})[/\-.](\d{4})"               # DD/YYYY or MM/YYYY
    r"|(\d{4})[/\-.](\d{1,2})"               # YYYY/MM
    r"|([A-Za-z]{3,9})[\s,]+(\d{4})"         # Mon YYYY
    r")",
    re.IGNORECASE,
)

# Month name → number
_MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Manufacturer/Packer/Importer name: look for keywords
_MFR_NAME_PATTERN = re.compile(
    r"(?:Manufactured\s+by|Mfg\.?\s+by|Packed\s+by|Marketed\s+by|Imported\s+by|Manufacturer)[:\s]*"
    r"([A-Za-z0-9\s&,.\-'()/]{5,80})",
    re.IGNORECASE,
)

# Address pattern: look for pin code as anchor
_ADDRESS_PATTERN = re.compile(
    r"([A-Za-z0-9\s,.\-/]{10,150})\s*[-,]?\s*(?:Pin|PIN)?\s*(\d{6})",
    re.IGNORECASE,
)

# Generic / common name — typically the largest text on the label (product name)
# We approximate by taking the longest all-caps sequence or sentence before other fields
_GENERIC_NAME_PATTERN = re.compile(
    r"^([A-Z][A-Z\s\-&']{4,60})$",
    re.MULTILINE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Extractor
# ─────────────────────────────────────────────────────────────────────────────

def extract_fields(ocr_result: OCRResult, lang_code: str = "en") -> LabelData:
    """
    Extract structured label fields from OCR output.

    Args:
        ocr_result: Raw OCR result (boxes + full text).
        lang_code:  Detected language code.

    Returns:
        LabelData with populated fields and overall_ocr_confidence.
    """
    text = ocr_result.full_text
    confidence = ocr_result.min_confidence

    mrp = _extract_mrp(text)
    net_qty_value, net_qty_unit = _extract_net_qty(text)
    mfg_month, mfg_year = _extract_mfg_date(text)
    mfr_name = _extract_manufacturer_name(text)
    mfr_addr = _extract_manufacturer_address(text)
    generic_name = _extract_generic_name(text, mfr_name)

    return LabelData(
        manufacturer_name=mfr_name,
        manufacturer_address=mfr_addr,
        generic_name=generic_name,
        net_quantity_value=net_qty_value,
        net_quantity_unit=net_qty_unit,
        mrp=mrp,
        manufacture_month=mfg_month,
        manufacture_year=mfg_year,
        overall_ocr_confidence=confidence,
        detected_language=lang_code,
        # CV geometry values are injected later by the processing pipeline
        measured_font_height_mm=None,
        font_type="printed",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Individual field extractors
# ─────────────────────────────────────────────────────────────────────────────

def _extract_mrp(text: str) -> Optional[float]:
    match = _MRP_PATTERN.search(text)
    if match:
        raw = match.group(1).replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            pass
    return None


def _extract_net_qty(text: str) -> tuple[Optional[float], Optional[str]]:
    match = _NET_QTY_PATTERN.search(text)
    if match:
        raw_val = match.group(1).replace(",", ".")
        unit = match.group(2).strip().lower()
        # Normalise unit abbreviations
        unit_map = {
            "gm": "g", "gms": "g", "gram": "g", "grams": "g",
            "kgs": "kg",
            "millilitre": "ml",
            "ltr": "l", "litre": "l", "liter": "l", "lt": "l",
            "pcs": "pcs", "pc": "pcs",
            "nos": "pcs", "no": "pcs", "pieces": "pcs", "number": "pcs",
        }
        unit = unit_map.get(unit, unit)
        try:
            return float(raw_val), unit
        except ValueError:
            pass
    return None, None


def _extract_mfg_date(text: str) -> tuple[Optional[int], Optional[int]]:
    match = _MFG_DATE_PATTERN.search(text)
    if not match:
        return None, None
    g = match.groups()
    try:
        if g[0] and g[1]:
            # DD/YYYY or MM/YYYY
            month_or_day = int(g[0])
            year = int(g[1])
            month = month_or_day if 1 <= month_or_day <= 12 else None
            return month, year
        elif g[2] and g[3]:
            # YYYY/MM
            return int(g[3]), int(g[2])
        elif g[4] and g[5]:
            # Mon YYYY
            month_str = g[4][:3].lower()
            month = _MONTH_NAMES.get(month_str)
            return month, int(g[5])
    except (ValueError, IndexError):
        pass
    return None, None


def _extract_manufacturer_name(text: str) -> Optional[str]:
    match = _MFR_NAME_PATTERN.search(text)
    if match:
        name = match.group(1).strip().rstrip(",.")
        if len(name) >= 3:
            return name
    return None


def _extract_manufacturer_address(text: str) -> Optional[str]:
    match = _ADDRESS_PATTERN.search(text)
    if match:
        addr = match.group(1).strip().rstrip(",.")
        pin = match.group(2)
        return f"{addr} - {pin}"
    return None


def _extract_generic_name(text: str, mfr_name: Optional[str]) -> Optional[str]:
    """
    Heuristic: the generic/product name is often the first prominent ALL-CAPS
    line that is not the manufacturer's name.
    """
    candidates = _GENERIC_NAME_PATTERN.findall(text)
    for candidate in candidates:
        candidate = candidate.strip()
        # Skip if it looks like the manufacturer name
        if mfr_name and candidate.lower() in mfr_name.lower():
            continue
        # Skip very short candidates (likely OCR noise)
        if len(candidate) < 5:
            continue
        return candidate
    return None
