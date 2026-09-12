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
# Priority 1: Labelled MRP (explicit declaration on the label)
# Handles: "MRP ₹150/-", "MRP : 150", "M.R.P. : ₹150.00", "MRP ₹: 5.00"
#          "MRP (incl. of all taxes) : 150", "MRP Rs. 20.00", "MRP ₹: 5.00 (Incl. of all taxes)"
#          "MRP. 250/-", "M R P : 18", "M.R.P Rs 25/-", "MRP: 5"
_LABELLED_MRP_PATTERN = re.compile(
    r"(?:"
    r"M\.?\s*R\.?\s*P\.?"                      # MRP, M.R.P., M R P, M. R. P.
    r"|M\.?\s*B\.?\s*P\.?"                      # OCR typo MBP
    r"|M\.?\s*R\.?\s*F\.?"                      # OCR typo MRF
    r"|Max(?:imum|\.)?\s+Retail\s+Price"       # Maximum Retail Price
    r"|Max\.?\s*Ret\.?\s*Price"                # Max. Ret. Price
    r"|Retail\s+Price"                         # Retail Price
    r"|(?<!\w)Price(?!\s*:\s*\w{10,})"        # Lone "Price" keyword
    r")"
    r"(?:\s*\([^)]*(?:tax|all|incl)[^)]*\))?"  # Optional (Incl. of all taxes) before amount
    r"[:\s\-._]*"                              # Separators
    r"(?:Rs\.?|INR|₹|Re\.?|[?*`'~^|\\/])?"    # Optional currency symbol or OCR artifact
    r"[:\s\-._]*"                              # Secondary separators
    r"(\d{1,6}(?:\s*[.,]\s*\d{1,2})?)"        # Numerical amount (GROUP 1)
    r"(?:\s*(?:/\s*-|/-|\([^)]*(?:tax|all|incl)[^)]*\)|\b))",  # Optional /- or (Incl. of all taxes) after
    re.IGNORECASE,
)

# Priority 2: Standalone currency price fallback (e.g. "₹ 150/-", "Rs. 150/-", "₹: 5.00", "₹5.00")
_STANDALONE_PRICE_PATTERN = re.compile(
    r"(?:Rs\.?|INR|₹|Re\.?)\s*[:\-._]?\s*(\d{1,6}(?:\s*[.,]\s*\d{1,2})?)\s*(?:/\s*-|/-|\b)",
    re.IGNORECASE,
)


# Net quantity patterns:
# Priority 1: Explicit labelled declaration
_LABELLED_NET_QTY_PATTERN = re.compile(
    r"(?:Net\s+(?:Wt\.?|Weight|Contents?|Quantity|Vol\.?|Volume|Qty\.?|Cont\.?)"
    r"|NET\s+(?:WT\.?|WEIGHT|CONTENTS?|QUANTITY|VOL\.?|VOLUME|QTY\.?|CONT\.?)"
    r"|Nett\s+(?:Wt\.?|Weight|Vol\.?|Qty\.?))[:\s]*"
    r"(\d+(?:\s*[.,]\s*\d+)?)\s*"
    r"(g(?:m(?:s)?)?|kg(?:s)?|ml|millilitre|l(?:tr?(?:e)?)?|litre|liter|pcs?|nos?|pieces?|number)\b",
    re.IGNORECASE,
)

# Priority 2: Standalone declaration (e.g. just "250 g" or "500ml" or "35g")
_STANDALONE_NET_QTY_PATTERN = re.compile(
    r"(?<!\d)(\d+(?:\s*[.,]\s*\d+)?)\s*"
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
    r"|PKD\.?(?:/[^:\n]*)?"        # PKD./ or PKD / USE BY DATE etc.
    r"|Mfg\.?/Pkg\.?"
    r"|Manufacturing\s+Date"
    r"|Packing\s+Date"
    r"|Manuf(?:actured)?\s+(?:On|Date)"
    r")[:\s]*"
    r"(?:"
    r"(\d{1,2})[/\-.](\d{1,2})[/\.\-](\d{4})"   # group 1,2,3: DD/MM/YYYY
    r"|(\d{1,2})[/\-.](\d{4})"                   # group 4,5: MM/YYYY
    r"|(\d{4})[/\-.](\d{1,2})"                   # group 6,7: YYYY/MM
    r"|([A-Za-z]{3,9})[\s,]+(\d{4})"             # group 8,9: Mon YYYY
    r"|(\d{1,2})[/\-.](\d{1,2})[/\.\-](\d{2})"  # group 10,11,12: DD/MM/YY
    r"|(\d{1,2})[/\-.](\d{2})"                   # group 13,14: MM/YY
    r")",
    re.IGNORECASE,
)

# Date pair pattern fallback: "30.07.22/29.01.23" (MFG/EXP pair common on Indian labels)
_DATE_PAIR_PATTERN = re.compile(
    r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\s*/\s*(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})"
)

# Standalone date fallback (DD/MM/YYYY or DD.MM.YY or MM/YYYY)
_STANDALONE_DATE_PATTERN = re.compile(
    r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b"
)

# Month name → number
_MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Manufacturer/Packer/Importer name
_MFR_NAME_PATTERN = re.compile(
    r"(?:Manufactured\s+(?:and\s+Marketed\s+)?by"
    r"|Mfg\.?\s*(?:&|and)?\s*(?:Pkd\.?)?\s*by"
    r"|Packed\s+(?:and\s+Marketed\s+)?by"
    r"|Pkd\.?\s+by"
    r"|Marketed\s+by"
    r"|Mkt\.?\s+by"
    r"|Imported\s+by"
    r"|Manufacturer"
    r"|Producer"
    r"|Packer)[:\s]*"
    r"([A-Za-z0-9\s&,.\-'()/]{3,100}?)"
    r"(?=\n\s*(?:MRP|Net|Batch|LOT|PKD|Packed|Best|Exp|Lic|FSSAI|Weight|Store|Customer|Consumer|Address|Email|Plot|Ph|Tel|www)|$|\n\n)",
    re.IGNORECASE,
)

# Address pattern: PIN code anchor OR address keywords
_ADDRESS_PIN_PATTERN = re.compile(
    r"([A-Za-z0-9\s,.\-/]{10,200})\s*[-,]?\s*(?:Pin|PIN|Pin\s*Code)?\s*[-:\s]?\s*(\d{6})\b",
    re.IGNORECASE,
)

_ADDRESS_KEYWORD_PATTERN = re.compile(
    r"(?:Address|Regd\.?\s*Office|Factory|Unit|Works|Plot|Mfg\.?\s*at|Packed\s*at)[:\s\-._]*"
    r"([A-Za-z0-9\s,.\-/]{8,200}?)"
    r"(?=\n\s*(?:MRP|Net|Batch|LOT|PKD|Packed|Best|Exp|Lic|FSSAI|Weight|Store|Customer|Consumer)|$|\n\n)",
    re.IGNORECASE,
)

# Batch / Lot No.
# Note: bare "Batch" must be followed by a qualifier (No./Number/Code/#).
# "LOT" alone is fine (less ambiguous). "B. No." is also fine.
_BATCH_PATTERN = re.compile(
    r"(?:Batch\s+(?:No\.?|Number|Code|#)"   # bare "Batch" MUST have qualifier
    r"|LOT\s*(?:No\.?|Number)?"             # LOT alone OK
    r"|B\.?\s*No\.?)[:\s\-._]*"             # B. No.
    r"([A-Za-z0-9][A-Za-z0-9/\-_]{2,39})",
    re.IGNORECASE,
)

# Best Before / Expiry — several label variants
_EXPIRY_PATTERN = re.compile(
    r"(?:Best\s+Before"
    r"|Use\s+By\s+Date"
    r"|Use\s+By"
    r"|Expiry\s+Date"
    r"|Exp(?:iry|\.?)?\s*(?:Date|Dt)?\.?"
    r"|Best\s+Before\s+(?:Date|End)"
    r"|BB\s+Date"
    r"|BBD)[:\s\-._]*"
    r"([A-Za-z0-9\s/\-.,]{2,60}?)"
    r"(?=\n\s*(?:MRP|Net|Batch|LOT|PKD|Packed|fssai|Lic|Store|Customer|Mfg|Consumer)|$|\n\n)",
    re.IGNORECASE,
)

# FSSAI License Number — 14-digit number OR licence text
_FSSAI_PATTERN = re.compile(
    r"(?:fssai|FSSAI)[\s\w.]*(?:Lic(?:ense|ence)?\.?\s*(?:No\.?)?|No\.?)?[:\s\-._]*"
    r"(\d{14}|\d[\d\s\-]{12,18}\d|[A-Za-z0-9\s]{3,30}?)"
    r"(?=\n\s*(?:MRP|Net|Batch|LOT|PKD|Packed|Best|Store|Customer|Mfg)|$|\n\n)",
    re.IGNORECASE,
)

# Stand-alone 14-digit FSSAI number (even without keyword, if it looks like one)
_FSSAI_14DIGIT_PATTERN = re.compile(
    r"\b(1[0-9]{13})\b"  # FSSAI numbers start with 1 and are 14 digits
)

# Consumer Care / Helpline / Email
_CONSUMER_CARE_PATTERN = re.compile(
    r"(?:Consumer\s*Care"
    r"|Customer\s*(?:Care|Service)"
    r"|Helpline"
    r"|Toll\s*Free"
    r"|Feedback"
    r"|For\s*(?:Feedback|Queries|Complaints)"
    r"|Contact\s*Us"
    r"|Call\s*Us)[:\s\-._]*"
    r"([A-Za-z0-9@.\s\-_+()/]{5,100}?)"
    r"(?=\n\s*(?:MRP|Net|Batch|LOT|PKD|Packed|Best|fssai|Mfg)|$|\n\n)",
    re.IGNORECASE,
)

# Phone number pattern (standalone, not preceded by a keyword above)
_PHONE_PATTERN = re.compile(
    r"(?:Ph\.?|Tel\.?|Phone|Mobile|Mob\.?|Call)[:\s]*([+\d\s\-()]{8,20})",
    re.IGNORECASE,
)

# Country of origin
_COUNTRY_ORIGIN_PATTERN = re.compile(
    r"(?:Country\s+of\s+(?:Origin|Mfg\.?)|Made\s+in|Product\s+of)[:\s\-._]*"
    r"([A-Za-z\s]{3,30}?)"
    r"(?=\n|\.|,|$)",
    re.IGNORECASE,
)

_IGNORED_PRODUCT_KEYWORDS = {
    "nutrition", "nutritional", "ingredients", "net weight", "net wt", "mrp", "batch",
    "packed on", "mfg date", "best before", "fssai", "store in", "calories", "keep in",
    "customer care", "consumer care", "marketed by", "manufactured by", "packed by",
    "serving size", "approx", "coocking", "cooking", "lic no", "lot no", "pkd",
    "energy", "protein", "carbohydrate", "fat", "sodium", "fibre", "fiber",
    "per 100", "per serving", "daily value", "allergen", "contains",
}


# ─────────────────────────────────────────────────────────────────────────────
# OCR text normalizer
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_ocr_text(text: str) -> str:
    """
    Fix common OCR transcription errors before regex extraction:
    - Reconnect broken lines (e.g. "MR\nP" → "MRP")
    - Normalize confusable characters (₹ ← ?, *, 2, ₹:)
    - Fix spacing around decimals (e.g. "5 . 00" -> "5.00")
    - Fix spacing around colons and digits
    """
    # Join lines broken in the middle of a keyword
    text = re.sub(r"\bMR\s*\n\s*P\b", "MRP", text, flags=re.IGNORECASE)
    text = re.sub(r"\bM\.?\s*\n\s*R\.?\s*\n\s*P\.?\b", "M.R.P.", text, flags=re.IGNORECASE)

    # OCR often reads ₹ as ?, *, ^, ', |, \, /
    # Replace lone symbol before a digit (price context) with ₹
    text = re.sub(r"(?<!\w)[?*`'~^|\\](?=\s*\d{1,6})", "₹", text)

    # Fix space inside decimal numbers (e.g. "5 . 00" or "5. 00" -> "5.00")
    text = re.sub(r"(\d+)\s*\.\s*(\d{2})\b", r"\1.\2", text)

    # Fix space inside dotted dates (e.g. "30 . 07 . 22" -> "30.07.22")
    text = re.sub(r"(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{2,4})", r"\1.\2.\3", text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text



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
    raw_text = ocr_result.full_text
    text = _normalize_ocr_text(raw_text)
    confidence = ocr_result.min_confidence

    logger.debug("Field extractor input text (%d chars):\n%s", len(text), text[:2000])

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

    logger.info(
        "Extracted — MRP:%.2f  NetQty:%s%s  Mfg:%s/%s  FSSAI:%s  Batch:%s  Expiry:%s",
        mrp or 0, net_qty_value, net_qty_unit or "", mfg_month, mfg_year,
        fssai, batch_no, expiry,
    )

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
            val = float(raw)
            if 1.0 <= val <= 99999.0:   # sanity check
                return val
        except ValueError:
            pass

    # 2. Look for standalone currency declaration fallback
    match2 = _STANDALONE_PRICE_PATTERN.search(text)
    if match2:
        raw2 = match2.group(1).replace(",", ".")
        try:
            val2 = float(raw2)
            if 1.0 <= val2 <= 99999.0:
                return val2
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
            "millilitre": "ml", "milliliter": "ml",
            "ltr": "l", "litre": "l", "liter": "l", "lt": "l",
            "pcs": "pcs", "pc": "pcs",
            "nos": "pcs", "no": "pcs", "pieces": "pcs", "number": "pcs",
        }
        unit = unit_map.get(unit, unit)
        try:
            val = float(raw_val)
            if val > 0:
                return val, unit
        except ValueError:
            pass
    return None, None


def _extract_mfg_date(text: str) -> tuple[Optional[int], Optional[int]]:
    # 1. Primary: Keyword-anchored Mfg/PKD date
    match = _MFG_DATE_PATTERN.search(text)
    if match:
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

    # 2. Date pair fallback: "30.07.22/29.01.23" (MFG/EXP pair common on Indian labels)
    match_pair = _DATE_PAIR_PATTERN.search(text)
    if match_pair:
        try:
            g = match_pair.groups()
            d1, m1, y1 = int(g[0]), int(g[1]), int(g[2])
            month = m1 if 1 <= m1 <= 12 else d1
            year = y1 if y1 >= 1000 else (2000 + y1 if y1 < 70 else 1900 + y1)
            if 1 <= month <= 12 and 2000 <= year <= 2040:
                return month, year
        except (ValueError, IndexError):
            pass

    # 3. Standalone date fallback near PKD/LOT/BATCH context
    match_std = _STANDALONE_DATE_PATTERN.search(text)
    if match_std:
        try:
            g = match_std.groups()
            d1, m1, y1 = int(g[0]), int(g[1]), int(g[2])
            month = m1 if 1 <= m1 <= 12 else d1
            year = y1 if y1 >= 1000 else (2000 + y1 if y1 < 70 else 1900 + y1)
            if 1 <= month <= 12 and 2018 <= year <= 2035:
                return month, year
        except (ValueError, IndexError):
            pass

    return None, None



def _extract_manufacturer_name(text: str) -> Optional[str]:
    match = _MFR_NAME_PATTERN.search(text)
    if match:
        name = match.group(1).strip().rstrip(",.")
        # Remove trailing address snippets that leaked past the lookahead
        name = re.split(r"\n", name)[0].strip()
        if len(name) >= 3:
            return name
    return None


def _extract_manufacturer_address(text: str) -> Optional[str]:
    # Try PIN code anchor first (most reliable)
    match = _ADDRESS_PIN_PATTERN.search(text)
    if match:
        addr_raw = match.group(1).strip().rstrip(",.")
        pin = match.group(2)
        # Clean up multi-line artefacts
        addr_clean = re.sub(r"\s*\n\s*", ", ", addr_raw).strip()
        return f"{addr_clean} - {pin}"

    # Fall back to keyword anchor
    match_kw = _ADDRESS_KEYWORD_PATTERN.search(text)
    if match_kw:
        addr_kw = match_kw.group(1).strip().rstrip(",.")
        addr_kw = re.sub(r"\s*\n\s*", ", ", addr_kw).strip()
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
        if len(line) < 3 or len(line) > 80:
            continue
        line_lower = line.lower()
        if mfr_name and line_lower in mfr_name.lower():
            continue
        if any(kw in line_lower for kw in _IGNORED_PRODUCT_KEYWORDS):
            continue
        # Must contain at least some alphabetical content
        if re.match(r"^[A-Za-z0-9\s\-&']+$", line) and re.search(r"[A-Za-z]{2,}", line):
            return line
    return None


def _extract_batch_number(text: str) -> Optional[str]:
    match = _BATCH_PATTERN.search(text)
    if match:
        val = match.group(1).strip()
        # Sanity check: batch numbers shouldn't be just digits that look like a year/price
        if len(val) >= 2:
            return val
    return None


def _extract_expiry(text: str) -> Optional[str]:
    match = _EXPIRY_PATTERN.search(text)
    if match:
        val = match.group(1).strip().rstrip(",.")
        if len(val) >= 2:
            return val
    return None


def _extract_fssai(text: str) -> Optional[str]:
    # First try keyword-anchored pattern
    match = _FSSAI_PATTERN.search(text)
    if match:
        val = match.group(1).strip().rstrip(",.")
        if len(val) >= 3:
            return val

    # Fallback: look for any 14-digit number starting with 1
    # (FSSAI license format is always 14 digits starting with 1x xxxx xxxx xxxxx)
    match14 = _FSSAI_14DIGIT_PATTERN.search(text)
    if match14:
        return match14.group(1)

    return None


def _extract_consumer_care(text: str) -> Optional[str]:
    match = _CONSUMER_CARE_PATTERN.search(text)
    if match:
        val = match.group(1).strip().rstrip(",.")
        if len(val) >= 5:
            return val

    # Fallback: look for phone number prefixed by common contact keywords
    phone_match = _PHONE_PATTERN.search(text)
    if phone_match:
        return phone_match.group(1).strip()

    return None
