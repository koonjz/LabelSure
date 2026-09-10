"""
LabelSure Rules Engine — Thresholds & Constants
India Legal Metrology (Packaged Commodities) Rules, 2011.

ALL numeric thresholds live here so rule updates require only this file to change.
Version-controlled independently via backend/rules/VERSION.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Rule 7 — Minimum Height of Letters/Numerals on Labels
# Source: Rule 7(1) of PCR 2011, as amended
# ─────────────────────────────────────────────────────────────────────────────

# Each entry: (upper_bound_grams_or_ml, min_height_mm)
# Upper bound is EXCLUSIVE upper limit; None = "above the previous band"
#
# For PRINTED declarations (Rule 7(1) table):
FONT_HEIGHT_PRINTED = [
    # (max_qty_g_or_ml_inclusive, min_height_mm)
    (50.0,    1.0),   # ≤ 50 g/ml
    (200.0,   2.0),   # > 50 and ≤ 200 g/ml
    (1000.0,  4.0),   # > 200 and ≤ 1000 g/ml  (i.e. ≤ 1 kg/L)
    (None,    6.0),   # > 1 kg/L
]

# For EMBOSSED / MOULDED / BLOWN declarations (Rule 7(1) proviso):
FONT_HEIGHT_EMBOSSED = [
    (200.0,   1.0),   # ≤ 200 g/ml
    (1000.0,  2.0),   # > 200 and ≤ 1000 g/ml
    (10000.0, 4.0),   # > 1 kg and ≤ 10 kg / > 1 L and ≤ 10 L
    (None,    6.0),   # > 10 kg/L
]

# ─────────────────────────────────────────────────────────────────────────────
# OCR confidence threshold below which we flag "NEEDS_REVIEW"
# ─────────────────────────────────────────────────────────────────────────────
OCR_CONFIDENCE_THRESHOLD = 0.70   # 70%

# ─────────────────────────────────────────────────────────────────────────────
# Unit normalisation: convert everything to grams/ml for comparison
# ─────────────────────────────────────────────────────────────────────────────
UNIT_TO_GRAMS_OR_ML = {
    "g":    1.0,
    "gm":   1.0,
    "gram": 1.0,
    "grams":1.0,
    "kg":   1000.0,
    "kgs":  1000.0,
    "ml":   1.0,
    "millilitre": 1.0,
    "milliliter": 1.0,
    "l":    1000.0,
    "lt":   1000.0,
    "ltr":  1000.0,
    "litre":1000.0,
    "liter":1000.0,
    "pcs":  None,   # piece-count — font height rule may not apply
    "nos":  None,
    "no":   None,
    "number": None,
    "pieces": None,
}


def normalise_quantity_to_grams_or_ml(value: float, unit: str) -> float | None:
    """
    Convert the declared net quantity to grams or millilitres for threshold comparison.
    Returns None if unit is non-weight/volume (e.g. pieces).
    """
    unit_lower = unit.strip().lower()
    factor = UNIT_TO_GRAMS_OR_ML.get(unit_lower)
    if factor is None:
        return None
    return value * factor


def get_min_font_height_mm(quantity_g_or_ml: float, font_type: str = "printed") -> float:
    """
    Return the minimum required font height (mm) for the given net quantity and font type.

    Args:
        quantity_g_or_ml: Net quantity in grams or millilitres.
        font_type:        "printed" or "embossed".

    Returns:
        Minimum font height in mm per Rule 7(1) PCR 2011.
    """
    table = FONT_HEIGHT_EMBOSSED if font_type.lower() == "embossed" else FONT_HEIGHT_PRINTED
    for (upper, min_height) in table:
        if upper is None or quantity_g_or_ml <= upper:
            return min_height
    return table[-1][1]  # fallback to highest tier
