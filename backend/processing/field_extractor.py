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

# Rate denominator pattern (e.g. / g, / kg, / ml, per g, per piece)
_RATE_DENOMINATOR_PATTERN = (
    r"(?:/|per)\s*(?:g(?:m(?:s)?)?|kg(?:s)?|ml|millilitre|l(?:tr?(?:e)?)?|litre|liter|pcs?|nos?|pieces?|number|pack|unit|item|serv(?:ing)?)\b"
)

# MRP patterns:
# Priority 1: Labelled MRP (explicit declaration on the label)
# Handles: "MRP ₹150/-", "MRP : 150", "M.R.P. : ₹150.00", "MRP ₹: 5.00"
#          "MRP (incl. of all taxes) : 150", "MRP Rs. 20.00", "MRP ₹: 5.00 (Incl. of all taxes)"
#          "MRP. 250/-", "M R P : 18", "M.R.P Rs 25/-", "MRP: 5", "Maximum Retail Price: Rs 500"
#          "MRP ₹ (Incl. of all taxes): RS: 75.00"
_LABELLED_MRP_PATTERN = re.compile(
    r"(?:"
    r"M\.?\s*R\.?\s*P\.?"                      # MRP, M.R.P., M R P, M. R. P.
    r"|M\.?\s*B\.?\s*P\.?"                      # OCR typo MBP
    r"|M\.?\s*R\.?\s*F\.?"                      # OCR typo MRF
    r"|Max(?:imum|\.)?\s+Retail\s+Price"       # Maximum Retail Price
    r"|Max\.?\s*Ret\.?\s*Price"                # Max. Ret. Price
    r"|Retail\s+Price"                         # Retail Price
    r")"
    r"(?:\s*(?:Rs\.?|INR|₹|Re\.?|[?*`'~^|\\/])?\s*\(?[^)\n]*(?:tax|all|incl)[^)\n]*\)?)?"  # Optional (Incl. of all taxes)
    r"[:\s\-._]*"                              # Separators
    r"(?:Rs\.?|INR|₹|Re\.?|[?*`'~^|\\/])?"    # Optional currency symbol or OCR artifact
    r"[:\s\-._]*"                              # Secondary separators
    r"(\d{1,6}(?:\s*[.,]\s*\d{1,2})?)"        # Numerical amount (GROUP 1)
    r"(?!\s*" + _RATE_DENOMINATOR_PATTERN + r")"  # Must NOT be followed by rate denominator (/ g, per g, etc.)
    r"(?:\s*(?:/\s*-|/-|\([^)]*(?:tax|all|incl)[^)]*\)|\b))",  # Optional /- or (Incl. of all taxes) after
    re.IGNORECASE,
)

# Priority 2: Generic total/package price fallback (e.g. "Total Price: Rs. 250", "Price: Rs. 500")
_GENERIC_PRICE_PATTERN = re.compile(
    r"\b(?:Total\s+Price|Net\s+Price|Package\s+Price|Price\s*[:\-])"
    r"(?:\s*\(?[^)\n]*(?:tax|all|incl)[^)\n]*\)?)?"
    r"[:\s\-._]*"
    r"(?:Rs\.?|INR|₹|Re\.?|[?*`'~^|\\/])?"
    r"[:\s\-._]*"
    r"(\d{1,6}(?:\s*[.,]\s*\d{1,2})?)"
    r"(?!\s*" + _RATE_DENOMINATOR_PATTERN + r")"
    r"(?:\s*(?:/\s*-|/-|\([^)]*(?:tax|all|incl)[^)]*\)|\b))",
    re.IGNORECASE,
)

# Priority 3: Standalone currency price fallback (e.g. "₹ 150/-", "Rs. 150/-", "₹: 5.00", "₹5.00")
_STANDALONE_PRICE_PATTERN = re.compile(
    r"(?:Rs\.?|INR|₹|Re\.?)\s*[:\-._]?\s*(\d{1,6}(?:\s*[.,]\s*\d{1,2})?)"
    r"(?!\s*" + _RATE_DENOMINATOR_PATTERN + r")"
    r"\s*(?:/\s*-|/-|\b)",
    re.IGNORECASE,
)

_USP_LINE_INDICATORS = ("unit sale price", "unit price", "usp", "u.s.p.", "price per", "rate/")



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

# Month name → number mapping (including full names and common OCR typos)
_MONTH_NAMES = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8, "ajg": 8, "au6": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "0ct": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_MONTH_REGEX_STR = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Ajg|Au6|Sep(?:t(?:ember)?)?|Oct(?:ober)?|0ct|Nov(?:ember)?|Dec(?:ember)?)"
)

# Manufacture/Packing date patterns:
#   "Packed On : 09/05/2025", "Mfg. Date: 06/2023", "Date of Mfg: Jun 2023", "MFD: 2023-06"
#   "PKD./ USE BY DATE: 30.07.22/29.01.23", "Packed On: 01/22", "PKD: 07/2022", "Pkg Dt: 05/24"
#   "Date of MFG.: 01AUG26", "25AUG2024", "01-AUG-26", "01/AUG/26", "01 AUG 2026", "AUG 2026"
#   "Packaging Date", "Date of Packing", "Imported On", "Date of Import"
_MFG_DATE_PATTERN = re.compile(
    r"(?:"
    r"Mfg\.?\s*(?:Date|Dt|On)?\.?"
    r"|Date\s+of\s+(?:Mfg|Manufacture|Mfgr|Manuf|Packaging|Packing|Import)\.?"
    r"|MFD\.?"
    r"|Packed?\s*(?:On|Date|Dt\.?|At)?\.?"
    r"|Pack(?:ing|age|aging)?\s*(?:Date|Dt|On)?\.?"
    r"|Pkg\.?\s*(?:Date|Dt|On)?\.?"
    r"|PKD\.?(?:/[^:\n]*)?"
    r"|Mfg\.?/Pkg\.?"
    r"|Manufacturing\s+(?:Date|Dt|On)?"
    r"|Manuf(?:actured)?\s+(?:On|Date|Dt)?"
    r"|Imported?\s+(?:On|Date|Dt)?"
    r")[:\s\-._]*"
    r"(?:"
    # DD-Mon-YYYY / DDMonYY / DD/Mon/YYYY (e.g. 01AUG26, 25AUG2024, 01-AUG-26, 01 AUG 2026)
    r"(\d{1,2})[\s/\-.]*(" + _MONTH_REGEX_STR + r")[\s/\-.]*(\d{2,4})"
    # Mon-YYYY / Mon-YY (e.g. AUG 2026, AUG-26, AUG26, AUG/26)
    r"|(" + _MONTH_REGEX_STR + r")[\s/\-.,]+(\d{2,4})"
    # DD/MM/YYYY or DD.MM.YYYY
    r"|(\d{1,2})[/\-.](\d{1,2})[/\.\-](\d{4})"
    # MM/YYYY
    r"|(\d{1,2})[/\-.](\d{4})"
    # YYYY/MM
    r"|(\d{4})[/\-.](\d{1,2})"
    # DD/MM/YY or DD.MM.YY
    r"|(\d{1,2})[/\-.](\d{1,2})[/\.\-](\d{2})"
    # MM/YY
    r"|(\d{1,2})[/\-.](\d{2})"
    r")",
    re.IGNORECASE,
)

# Date pair pattern fallback: "30.07.22/29.01.23" (MFG/EXP pair common on Indian labels)
_DATE_PAIR_PATTERN = re.compile(
    r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\s*/\s*(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})"
)

# Standalone Alpha-Numeric date fallback (e.g. 01AUG26, 25AUG2024, AUG 2026)
_STANDALONE_ALPHA_DATE_PATTERN = re.compile(
    r"\b(\d{1,2})[\s/\-.]*(" + _MONTH_REGEX_STR + r")[\s/\-.]*(\d{2,4})\b"
    r"|\b(" + _MONTH_REGEX_STR + r")[\s/\-.,]+(\d{2,4})\b",
    re.IGNORECASE,
)

# Standalone date fallback (DD/MM/YYYY or DD.MM.YY or MM/YYYY)
_STANDALONE_DATE_PATTERN = re.compile(
    r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b"
)

# Manufacturer/Packer/Marketed By prefix pattern
_MFR_PREFIX_PATTERN = re.compile(
    r"(?:"
    r"Manufactured\s+(?:(?:&|and)\s+)?(?:Marketed|Packed)\s+by"
    r"|Manufactured\s+by"
    r"|Mfg\.?\s*(?:&|and)?\s*(?:Pkd\.?|Mkt\.?)?\s*by"
    r"|Packed\s+(?:(?:&|and)\s+)?(?:Marketed|Mfg\.?)\s*by"
    r"|Packed\s+by"
    r"|Pkd\.?\s+by"
    r"|Marketed\s+(?:(?:&|and)\s+Distributed\s+)?by"
    r"|Mkt\.?\s+by"
    r"|Imported\s+by"
    r"|Manufacturer"
    r"|Producer"
    r"|Packer"
    r")[:\s\-._]*",
    re.IGNORECASE,
)

# Address pattern: PIN code anchor OR address keywords
_ADDRESS_PIN_PATTERN = re.compile(
    r"([A-Za-z0-9\s,.\-/]{10,200})\s*[-,]?\s*(?:Pin|PIN|Pin\s*Code)?\s*[-:\s]?\s*(\d{3}\s*\d{3})\b",
    re.IGNORECASE,
)

_ADDRESS_KEYWORD_PATTERN = re.compile(
    r"(?:Address|Regd\.?\s*Office|Factory|Unit|Works|Plot|Mfg\.?\s*at|Packed\s*at)[:\s\-._]*"
    r"([A-Za-z0-9\s,.\-/]{8,200}?)"
    r"(?=\n\s*(?:MRP|Net|Batch|LOT|PKD|Packed|Best|Exp|Lic|FSSAI|Weight|Store|Customer|Consumer)|$|\n\n)",
    re.IGNORECASE,
)

_INDIAN_LOCATIONS = (
    r"(?:Maharashtra|Mumbai|Pune|Nagpur|Thane|Nashik|Gujarat|Ahmedabad|Surat|Vadodara|Rajkot|"
    r"Delhi|New\s+Delhi|Noida|Gurgaon|Gurugram|Faridabad|Ghaziabad|Haryana|Punjab|Chandigarh|Ludhiana|"
    r"Karnataka|Bangalore|Bengaluru|Mysore|Tamil\s+Nadu|Chennai|Coimbatore|Madurai|"
    r"Telangana|Hyderabad|Secunderabad|Andhra\s+Pradesh|Visakhapatnam|Vijayawada|"
    r"West\s+Bengal|Kolkata|Howrah|Rajasthan|Jaipur|Jodhpur|Udaipur|Uttar\s+Pradesh|Lucknow|Kanpur|"
    r"Kerala|Kochi|Ernakulam|Trivandrum|Thiruvananthapuram|Madhya\s+Pradesh|Indore|Bhopal|"
    r"Goa|Panaji|Bihar|Patna|Jharkhand|Ranchi|Jamshedpur|Odisha|Bhubaneswar|Assam|Guwahati|"
    r"Nariman\s+Point|Andheri|Bandra|MIDC|GIDC|RIICO|Industrial\s+Area|Estate|Sector|Phase|Plot|Chambers|Building|Tower|Marg|Road|Street|Nagar)"
)

_ADDRESS_LOCATION_PATTERN = re.compile(
    r"([A-Za-z0-9\s,.\-/#()]{5,150}?\b" + _INDIAN_LOCATIONS + r"\b[A-Za-z0-9\s,.\-/#()]{0,100}?(?:\d{3}\s*\d{3})?)",
    re.IGNORECASE,
)

# Batch / Lot No.
# Supports "Batch : 20250509", "Batch No.: ABC", "LOT: 123", "B.No.: 456"
_BATCH_PATTERN = re.compile(
    r"(?:Batch\s+(?:No\.?|Number|Code|#)"
    r"|Batch\s*[:\-._]"
    r"|LOT\s*(?:No\.?|Number)?\b"
    r"|B\.?\s*No\.?)[:\s\-._]*"
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
    r"(?:fssai|FSSAI)[\sA-Za-z.]*(?:Lic(?:ense|ence)?\.?\s*(?:No\.?)?|No\.?)?[:\s\-._]*"
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

# Explicit Product / Commodity Name patterns
# Matches: "Name of Commodity: Roasted Almonds", "Generic Name: Roasted Salted Almonds",
#          "Commodity: Almonds", "Product Name: California Almonds", "Product: Roasted Almonds"
_COMMODITY_DECLARATION_PATTERN = re.compile(
    r"(?:Name\s+of\s+(?:the\s+)?Commodity"
    r"|Generic\s+Name"
    r"|Name\s+of\s+(?:the\s+)?Product"
    r"|Product\s+Name"
    r"|Commodity"
    r"|Product"
    r"|Item\s+Name"
    r"|Item"
    r"|Article)[:\s\-._]*"
    r"([A-Za-z0-9\s\-&',()]+?)"
    r"(?=\n|$|\.\s*(?:MRP|Net|Mfg|Date|Batch|LOT|PKD|Packed|fssai|Lic|Store|Customer|Consumer|Manufactured|Marketed))",
    re.IGNORECASE,
)

# Company entity recognition (for manufacturer fallback)
_COMPANY_LEGAL_SUFFIXES = [
    r"Pvt\.?\s*Ltd\.?",
    r"Private\s+Limited",
    r"Ltd\.?",
    r"Limited",
    r"LLP",
    r"L\.L\.P\.?",
    r"Industries",
    r"Enterprises",
    r"Beverages",
    r"Laboratories",
    r"Pharma",
    r"Packers",
    r"Naturals",
    r"Herbals",
    r"Foods",
    r"Agro",
    r"Organics",
    r"Products",
    r"Confectionery",
]

_COMPANY_CHECK_REGEX = re.compile(
    r"\b(?:" + "|".join(_COMPANY_LEGAL_SUFFIXES) + r")\b",
    re.IGNORECASE,
)

_IGNORED_COMPANY_LINE_KEYWORDS = {
    "nutrition", "ingredients", "mrp", "net wt", "net weight", "batch", "pkd",
    "mfg date", "best before", "expiry", "fssai", "customer care", "consumer care",
    "email", "phone", "website", "address:", "address :",
}

_IGNORED_PRODUCT_KEYWORDS = {
    "nutrition", "nutritional", "ingredients", "net weight", "net wt", "net quantity", "net qty",
    "mrp", "batch", "lot no", "b.no", "packed on", "mfg date", "date of mfg", "mfd",
    "best before", "expiry", "use by", "fssai", "store in", "calories", "keep in",
    "customer care", "consumer care", "marketed by", "manufactured by", "packed by", "mfg by", "pkd by",
    "serving size", "approx", "cooking", "lic no", "lot no", "pkd",
    "energy", "protein", "carbohydrate", "fat", "sodium", "fibre", "fiber",
    "per 100", "per serving", "daily value", "allergen", "contains",
    "unit sale price", "unit price", "usp", "address", "regd office", "factory",
    "scan qr", "feedback", "helpline", "email", "phone", "toll free",
    "country of origin", "made in", "product of", "veg", "non-veg", "100% veg",
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
    mfr_name, mfr_addr = _extract_manufacturer_info(text)
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

def _get_line_prefix(text: str, start_idx: int) -> str:
    """Get the text on the same line preceding start_idx."""
    line_start = text.rfind("\n", 0, start_idx)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1
    return text[line_start:start_idx].lower()


def _extract_mrp(text: str) -> Optional[float]:
    # 1. Look for explicit labelled MRP declaration (highest priority)
    for match in _LABELLED_MRP_PATTERN.finditer(text):
        prefix = _get_line_prefix(text, match.start())
        if any(usp_kw in prefix for usp_kw in _USP_LINE_INDICATORS):
            continue
        raw = match.group(1).replace(" ", "").replace(",", ".")
        try:
            val = float(raw)
            if 1.0 <= val <= 99999.0:   # sanity check
                return val
        except ValueError:
            pass

    # 2. Look for generic Price declaration (Total Price, Net Price, Price:)
    for match in _GENERIC_PRICE_PATTERN.finditer(text):
        prefix = _get_line_prefix(text, match.start())
        if any(usp_kw in prefix for usp_kw in _USP_LINE_INDICATORS):
            continue
        raw = match.group(1).replace(" ", "").replace(",", ".")
        try:
            val = float(raw)
            if 1.0 <= val <= 99999.0:
                return val
        except ValueError:
            pass

    # 3. Look for standalone currency declaration fallback (e.g. "₹ 150/-")
    for match2 in _STANDALONE_PRICE_PATTERN.finditer(text):
        prefix = _get_line_prefix(text, match2.start())
        if any(usp_kw in prefix for usp_kw in _USP_LINE_INDICATORS):
            continue
        raw2 = match2.group(1).replace(" ", "").replace(",", ".")
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
        g = match.groups()
        try:
            # Group 0,1,2: DD-Mon-YYYY or DDMonYY (e.g. 01AUG26, 25AUG2024, 01-AUG-26, 01 AUG 2026)
            if g[0] and g[1] and g[2]:
                m_str = g[1].lower()
                month = _MONTH_NAMES.get(m_str)
                y = int(g[2])
                year = 2000 + y if y < 100 else y
                return month, year
            # Group 3,4: Mon-YYYY or Mon-YY (e.g. AUG 2026, AUG-26, AUG26)
            elif g[3] and g[4]:
                m_str = g[3].lower()
                month = _MONTH_NAMES.get(m_str)
                y = int(g[4])
                year = 2000 + y if y < 100 else y
                return month, year
            # Group 5,6,7: DD/MM/YYYY or DD.MM.YYYY
            elif g[5] and g[6] and g[7]:
                first = int(g[5])
                second = int(g[6])
                year = int(g[7])
                month = second if 1 <= second <= 12 else first
                return month, year
            # Group 8,9: MM/YYYY
            elif g[8] and g[9]:
                month = int(g[8])
                year = int(g[9])
                return (month if 1 <= month <= 12 else None), year
            # Group 10,11: YYYY/MM
            elif g[10] and g[11]:
                return int(g[11]), int(g[10])
            # Group 12,13,14: DD/MM/YY
            elif g[12] and g[13] and g[14]:
                first = int(g[12])
                second = int(g[13])
                y = int(g[14])
                year = 2000 + y if y < 100 else y
                month = second if 1 <= second <= 12 else first
                return month, year
            # Group 15,16: MM/YY
            elif g[15] and g[16]:
                month = int(g[15])
                y = int(g[16])
                year = 2000 + y if y < 100 else y
                return (month if 1 <= month <= 12 else None), year
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

    # 3. Standalone Alpha-Numeric date fallback (e.g. 01AUG26, 25AUG2024, AUG 2026)
    match_alpha = _STANDALONE_ALPHA_DATE_PATTERN.search(text)
    if match_alpha:
        try:
            g = match_alpha.groups()
            if g[0] and g[1] and g[2]:
                m_str = g[1].lower()
                month = _MONTH_NAMES.get(m_str)
                y = int(g[2])
                year = 2000 + y if y < 100 else y
                if 2018 <= year <= 2040:
                    return month, year
            elif g[3] and g[4]:
                m_str = g[3].lower()
                month = _MONTH_NAMES.get(m_str)
                y = int(g[4])
                year = 2000 + y if y < 100 else y
                if 2018 <= year <= 2040:
                    return month, year
        except (ValueError, IndexError):
            pass

    # 4. Standalone date fallback near PKD/LOT/BATCH context
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


def _extract_manufacturer_info(text: str) -> tuple[Optional[str], Optional[str]]:
    mfr_name = None
    mfr_addr = None

    # Find the manufacturer / packer / marketed by prefix
    prefix_match = _MFR_PREFIX_PATTERN.search(text)
    if prefix_match:
        start_idx = prefix_match.end()
        rest_of_text = text[start_idx:].strip()
        lines = [l.strip() for l in rest_of_text.split("\n") if l.strip()]
        
        if lines:
            first_line = lines[0]
            name_candidate = re.split(
                r",\s*(?:Plot|Sector|MIDC|GIDC|Road|Street|Building|Floor|Chambers|Regd|\d{6})",
                first_line,
                flags=re.IGNORECASE,
            )[0].strip().rstrip(",.")
            
            if len(name_candidate) >= 3:
                mfr_name = name_candidate

            addr_candidates = []
            if len(lines) > 1:
                for line in lines[1:]:
                    if re.match(r"^(?:fssai|Lic|MRP|Net|Batch|LOT|PKD|Packed|Best|Exp|Weight|Store|Customer|Consumer|Manufactured|Marketed)", line, re.IGNORECASE):
                        break
                    addr_candidates.append(line)
            
            if addr_candidates:
                mfr_addr = ", ".join(addr_candidates)
            elif "," in first_line:
                inline_addr = first_line[len(name_candidate):].strip().lstrip(",").strip()
                if len(inline_addr) >= 5:
                    mfr_addr = inline_addr

    # Fallback for manufacturer name by company legal entities (Pvt Ltd, Foods Ltd, etc.)
    if not mfr_name:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines:
            if any(kw in line.lower() for kw in _IGNORED_COMPANY_LINE_KEYWORDS):
                continue
            if _COMPANY_CHECK_REGEX.search(line):
                cand = re.split(
                    r",\s*(?:Plot|Sector|MIDC|GIDC|Road|Street|Building|Floor|Chambers|Regd|\d{6})",
                    line,
                    flags=re.IGNORECASE,
                )[0].strip().rstrip(",.")
                if 3 <= len(cand) <= 80:
                    mfr_name = cand
                    break

    # Fallback for address with PIN code anywhere in text
    if not mfr_addr:
        pin_match = _ADDRESS_PIN_PATTERN.search(text)
        if pin_match:
            addr_part = pin_match.group(1).strip().rstrip(",-")
            pin = pin_match.group(2).replace(" ", "")
            if mfr_name and addr_part.startswith(mfr_name):
                addr_part = addr_part[len(mfr_name):].strip().lstrip(",-").strip()
            addr_clean = re.sub(r"\s*\n\s*", ", ", addr_part).strip()
            if len(addr_clean) >= 5:
                mfr_addr = f"{addr_clean} - {pin}"

    # Fallback for address with explicit keywords (Address:, Regd Office:, etc.)
    if not mfr_addr:
        match_kw = _ADDRESS_KEYWORD_PATTERN.search(text)
        if match_kw:
            addr_kw = match_kw.group(1).strip().rstrip(",.")
            addr_kw = re.sub(r"\s*\n\s*", ", ", addr_kw).strip()
            if len(addr_kw) >= 5:
                mfr_addr = addr_kw

    # Fallback for address with Location / City / State keywords
    if not mfr_addr:
        loc_match = _ADDRESS_LOCATION_PATTERN.search(text)
        if loc_match:
            cand = loc_match.group(1).strip().rstrip(",-")
            if mfr_name and cand.startswith(mfr_name):
                cand = cand[len(mfr_name):].strip().lstrip(",-").strip()
            cand_clean = re.sub(r"\s*\n\s*", ", ", cand).strip()
            if len(cand_clean) >= 8:
                mfr_addr = cand_clean

    # Clean up formatting
    if mfr_addr:
        mfr_addr = re.sub(r",\s*,+", ", ", mfr_addr)
        mfr_addr = re.sub(r"\s*-\s*-+\s*", " - ", mfr_addr)
        mfr_addr = re.sub(r"\s+", " ", mfr_addr).strip().rstrip(",.")

    return mfr_name, mfr_addr


def _extract_manufacturer_name(text: str) -> Optional[str]:
    name, _ = _extract_manufacturer_info(text)
    return name


def _extract_manufacturer_address(text: str) -> Optional[str]:
    _, addr = _extract_manufacturer_info(text)
    return addr


def _extract_generic_name(text: str, mfr_name: Optional[str]) -> Optional[str]:
    """
    Extract product / commodity name:
    1. Looks for explicit statutory declarations (Name of Commodity, Generic Name, Product Name, etc.)
    2. Fallback: inspects top non-noise title lines and merges connected multi-line titles.
    """
    # 1. Primary: Explicit statutory commodity declaration
    for match in _COMMODITY_DECLARATION_PATTERN.finditer(text):
        cand = match.group(1).strip().rstrip(",.")
        if 2 <= len(cand) <= 80 and not any(kw in cand.lower() for kw in _IGNORED_PRODUCT_KEYWORDS):
            return cand

    # 2. Fallback: Look at top non-noise lines
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    candidate_lines = []

    for i, line in enumerate(lines):
        line_clean = line.strip()
        if len(line_clean) < 2 or len(line_clean) > 80:
            continue
        line_lower = line_clean.lower()
        if mfr_name and (line_lower in mfr_name.lower() or mfr_name.lower() in line_lower):
            continue
        if any(kw in line_lower for kw in _IGNORED_PRODUCT_KEYWORDS):
            continue
        # Skip lines that are just numbers, dates, or prices
        if re.match(r"^[\d\s.,/\-:]+$", line_clean):
            continue
        # Must contain alphabetical letters
        if not re.search(r"[A-Za-z]{2,}", line_clean):
            continue

        candidate_lines.append(line_clean)

        # If this is the first candidate title line, check if the subsequent line is connected (e.g. ROASTED + ALMONDS)
        if len(candidate_lines) == 1:
            words = line_clean.split()
            if len(words) <= 3 and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                next_lower = next_line.lower()
                if (
                    2 <= len(next_line) <= 40
                    and not any(kw in next_lower for kw in _IGNORED_PRODUCT_KEYWORDS)
                    and not re.match(r"^[\d\s.,/\-:]+$", next_line)
                    and re.search(r"[A-Za-z]{2,}", next_line)
                    and not (mfr_name and next_lower in mfr_name.lower())
                ):
                    return f"{line_clean} {next_line}"
            return line_clean

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
