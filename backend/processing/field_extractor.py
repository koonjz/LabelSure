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

# MRP patterns:
# Priority 1: Labelled MRP ("MRP ₹150/-", "MRP : 150", "M.R.P. : ₹150.00", "MRP (incl. of all taxes) : 150")
_LABELLED_MRP_PATTERN = re.compile(
    r"(?:"
    r"M\.?\s*R\.?\s*P\.?"                      # MRP, M.R.P., M R P, M. R. P.
    r"|M\.?\s*B\.?\s*P\.?"                      # OCR typo MBP
    r"|M\.?\s*R\.?\s*F\.?"                      # OCR typo MRF
    r"|Max(?:imum|\.)?\s+Retail\s+Price"       # Maximum Retail Price, Max. Retail Price
    r"|Retail\s+Price"                         # Retail Price
    r"|Price"                                  # Price
    r")"
    r"(?:\s*\([^)]*(?:tax|all|incl)[^)]*\))?"  # Optional (Incl. of all taxes)
    r"[:\s\-._]*"                              # Separators
    r"(?:Rs\.?|INR|₹|Re\.?|[?*`'~^|\\/])?"     # Optional currency symbol or OCR symbol artifact
    r"[:\s\-._]*"                              # Secondary separators
    r"(\d{1,6}(?:[.,]\d{1,2})?)"               # Numerical amount
    r"(?:\s*/\s*-|\s*/-|\b)",                  # Optional /- suffix
    re.IGNORECASE,
)

# Priority 2: Standalone currency price fallback (e.g. "₹ 150/-", "Rs. 150/-", "₹150")
_STANDALONE_PRICE_PATTERN = re.compile(
    r"(?:Rs\.?|INR|₹)\s*(\d{1,6}(?:[.,]\d{1,2})?)\s*(?:/\s*-|/-|\b)",
    re.IGNORECASE,
)


# Net quantity patterns:
# Priority 1: Explicit labelled declaration (e.g. "Net Weight : 250 Gm", "Net Wt. 500g")
_LABELLED_NET_QTY_PATTERN = re.compile(
    r"(?:Net\s+(?:Wt\.?|Weight|Contents?|Quantity|Vol\.?|Volume|Qty\.?)"
    r"|NET\s+(?:WT\.?|WEIGHT|CONTENTS?|QUANTITY|VOL\.?|VOLUME|QTY\.?))[\s:]*"
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(g(?:m(?:s)?)?|kg(?:s)?|ml|millilitre|l(?:tr?(?:e)?)?|litre|liter|pcs?|nos?|pieces?|number)\b",
    re.IGNORECASE,
)

# Priority 2: Standalone declaration (fallback)
_STANDALONE_NET_QTY_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(g(?:m(?:s)?)?|kg(?:s)?|ml|millilitre|l(?:tr?(?:e)?)?|litre|liter|pcs?|nos?|pieces?|number)\b",
    re.IGNORECASE,
)

# Manufacture/Packing date patterns:
#   "Packed On : 09/05/2025", "Mfg. Date: 06/2023", "Date of Mfg: Jun 2023", "MFD: 2023-06"
#   "PKD./ USE BY DATE: 30.07.22/29.01.23", "Packed On: 01/22", "PKD: 07/2022"
_MFG_DATE_PATTERN = re.compile(
    r"(?:"
    r"Mfg\.?\s*(?:Date|Dt)?\.?"
    r"|Date\s+of\s+(?:Mfg|Manufacture|Mfgr|Manuf)\.?"
    r"|MFD\.?"
    r"|Packed?\s*(?:On|Date|Dt\.?)?\.?"
    r"|PKD\.?(?:/[^:]*)?"         # PKD./ or PKD / USE BY DATE etc.
    r"|Mfg\.?/Pkg\.?"
    r"|Manufacturing\s+Date"
    r"|Packing\s+Date"
    r")[:\s]*"
    r"(?:"
    r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})"   # group 1,2,3: DD/MM/YYYY or MM/DD/YYYY (4-digit year)
    r"|(\d{1,2})[/\-.](\d{4})"                 # group 4,5: MM/YYYY or DD/YYYY (4-digit year)
    r"|(\d{4})[/\-.](\d{1,2})"                 # group 6,7: YYYY/MM
    r"|([A-Za-z]{3,9})[\s,]+(\d{4})"           # group 8,9: Mon YYYY
    r"|(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2})"  # group 10,11,12: DD/MM/YY (2-digit year)
    r"|(\d{1,2})[/\-.](\d{2})"                 # group 13,14: MM/YY (2-digit year)
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
    r"(?:Manufactured\s+(?:and\s+Marketed\s+)?by|Mfg\.?\s*(?:&|and)?\s*(?:Pkd\.?)?\s*by|Packed\s+by|Pkd\.?\s+by|Marketed\s+by|Mkt\.?\s+by|Imported\s+by|Manufacturer|Producer|Packer)[:\s]*"
    r"([A-Za-z0-9\s&,.\-'()/]{3,80}?)"
    r"(?=\n\s*(?:MRP|Net|Batch|LOT|PKD|Packed|Best|Exp|Lic|FSSAI|Weight|Store|Customer|Consumer|Address|Email|Plot)|$|\n\n)",
    re.IGNORECASE,
)

# Address pattern: PIN code anchor OR address keywords
_ADDRESS_PIN_PATTERN = re.compile(
    r"([A-Za-z0-9\s,.\-/]{10,150})\s*[-,]?\s*(?:Pin|PIN)?\s*(\d{6})\b",
    re.IGNORECASE,
)

_ADDRESS_KEYWORD_PATTERN = re.compile(
    r"(?:Address|Regd\.?\s*Office|Factory|Unit|Works|Plot|Mfg\.?\s*at|Packed\s*at)[:\s\-._]*"
    r"([A-Za-z0-9\s,.\-/]{8,120}?)"
    r"(?=\n\s*(?:MRP|Net|Batch|LOT|PKD|Packed|Best|Exp|Lic|FSSAI|Weight|Store|Customer|Consumer)|$|\n\n)",
    re.IGNORECASE,
)

# Batch / Lot No.
_BATCH_PATTERN = re.compile(
    r"(?:Batch\s*(?:No\.?|Number)?|LOT\s*(?:No\.?|Number)?|B\.?\s*No\.?)[:\s\-._]*"
    r"([A-Za-z0-9/\-_]{3,30})",
    re.IGNORECASE,
)

# Best Before / Expiry
_EXPIRY_PATTERN = re.compile(
    r"(?:Best\s+Before|Use\s+By\s+Date|Use\s+By|Expiry\s+Date|Exp\.?\s*Date|Exp\.?)[:\s\-._]*"
    r"([A-Za-z0-9\s/\-.,]{3,50}?)"
    r"(?=\n\s*(?:MRP|Net|Batch|LOT|PKD|Packed|fssai|Lic|Store|Customer|Mfg)|$|\n\n)",
    re.IGNORECASE,
)

# FSSAI License Number
_FSSAI_PATTERN = re.compile(
    r"(?:fssai|FSSAI)[\s\w.]*(?:Lic\.?\s*(?:No\.?)?|License\s*(?:No\.?)?)?[:\s\-._]*"
    r"([A-Za-z0-9\s]{3,30}?)"
    r"(?=\n\s*(?:MRP|Net|Batch|LOT|PKD|Packed|Best|Store|Customer|Mfg)|$|\n\n)",
    re.IGNORECASE,
)

# Consumer Care / Helpline / Email
_CONSUMER_CARE_PATTERN = re.compile(
    r"(?:Consumer\s*Care|Customer\s*Care|Helpline|Toll\s*Free|Feedback|For\s*Feedback)[:\s\-._]*"
    r"([A-Za-z0-9@.\s\-_+()]{5,80}?)"
    r"(?=\n\s*(?:MRP|Net|Batch|LOT|PKD|Packed|Best|fssai|Mfg)|$|\n\n)",
    re.IGNORECASE,
)

_IGNORED_PRODUCT_KEYWORDS = {
    "nutrition", "nutritional", "ingredients", "net weight", "net wt", "mrp", "batch",
    "packed on", "mfg date", "best before", "fssai", "store in", "calories", "keep in",
    "customer care", "consumer care", "marketed by", "manufactured by", "packed by",
    "serving size", "approx", "coocking", "cooking", "lic no", "lot no", "pkd",
}


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
    batch_no = _extract_batch_number(text)
    expiry = _extract_expiry(text)
    fssai = _extract_fssai(text)
    consumer_care = _extract_consumer_care(text)

    return LabelData(
        manufacturer_name=mfr_name,
        manufacturer_address=mfr_addr,
        generic_name=generic_name,
        net_quantity_value=net_qty_value,
        net_quantity_unit=net_qty_unit,
        mrp=mrp,
        manufacture_month=mfg_month,
        manufacture_year=mfg_year,
        batch_number=batch_no,
        expiry_date=expiry,
        fssai_license=fssai,
        consumer_care=consumer_care,
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
    # 1. Look for explicit labelled MRP declaration
    match = _LABELLED_MRP_PATTERN.search(text)
    if match:
        raw = match.group(1).replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            pass
    # 2. Look for standalone currency declaration fallback
    match2 = _STANDALONE_PRICE_PATTERN.search(text)
    if match2:
        raw2 = match2.group(1).replace(",", ".")
        try:
            return float(raw2)
        except ValueError:
            pass
    return None


def _extract_net_qty(text: str) -> tuple[Optional[float], Optional[str]]:
    # 1. Prefer explicit labelled declaration ("Net Weight : 250 Gm")
    match = _LABELLED_NET_QTY_PATTERN.search(text)
    # 2. Fall back to standalone declaration if not found
    if not match:
        match = _STANDALONE_NET_QTY_PATTERN.search(text)
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
    g = match.groups()  # 14 groups total (indices 0-13)
    try:
        if g[0] and g[1] and g[2]:
            # DD/MM/YYYY or MM/DD/YYYY (e.g. 09/05/2025)
            first = int(g[0])
            second = int(g[1])
            year = int(g[2])
            month = second if 1 <= second <= 12 else first
            return month, year
        elif g[3] and g[4]:
            # MM/YYYY (4-digit year)
            month = int(g[3])
            year = int(g[4])
            month = month if 1 <= month <= 12 else None
            return month, year
        elif g[5] and g[6]:
            # YYYY/MM
            return int(g[6]), int(g[5])
        elif g[7] and g[8]:
            # Mon YYYY
            month_str = g[7][:3].lower()
            month = _MONTH_NAMES.get(month_str)
            return month, int(g[8])
        elif g[9] and g[10] and g[11]:
            # DD/MM/YY — 2-digit year (e.g. 30.07.22 → July 2022)
            month = int(g[10])
            year_2d = int(g[11])
            year = 2000 + year_2d
            return month if 1 <= month <= 12 else None, year
        elif g[12] and g[13]:
            # MM/YY or DD/YY — 2-digit year (e.g. 07/22)
            month = int(g[12])
            year_2d = int(g[13])
            year = 2000 + year_2d
            return month if 1 <= month <= 12 else None, year
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
    match = _ADDRESS_PIN_PATTERN.search(text)
    if match:
        addr = match.group(1).strip().rstrip(",.")
        pin = match.group(2)
        return f"{addr} - {pin}"
    match_kw = _ADDRESS_KEYWORD_PATTERN.search(text)
    if match_kw:
        addr_kw = match_kw.group(1).strip().rstrip(",.")
        if len(addr_kw) >= 5:
            return addr_kw
    return None


def _extract_generic_name(text: str, mfr_name: Optional[str]) -> Optional[str]:
    """
    Extract product / commodity name:
    Looks for the top non-noise line describing the product.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines:
        if len(line) < 3 or len(line) > 60:
            continue
        line_lower = line.lower()
        if mfr_name and line_lower in mfr_name.lower():
            continue
        if any(kw in line_lower for kw in _IGNORED_PRODUCT_KEYWORDS):
            continue
        if re.match(r"^[A-Za-z0-9\s\-&']+$", line):
            return line
    return None


def _extract_batch_number(text: str) -> Optional[str]:
    match = _BATCH_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return None


def _extract_expiry(text: str) -> Optional[str]:
    match = _EXPIRY_PATTERN.search(text)
    if match:
        return match.group(1).strip().rstrip(",.")
    return None


def _extract_fssai(text: str) -> Optional[str]:
    match = _FSSAI_PATTERN.search(text)
    if match:
        return match.group(1).strip().rstrip(",.")
    return None


def _extract_consumer_care(text: str) -> Optional[str]:
    match = _CONSUMER_CARE_PATTERN.search(text)
    if match:
        return match.group(1).strip().rstrip(",.")
    return None


