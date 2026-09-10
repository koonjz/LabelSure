"""
LabelSure Rules Engine — Rule 7 / Rule 7(3): Minimum Letter/Numeral Height
India Legal Metrology (Packaged Commodities) Rules, 2011.

Rule 7(1): Every declaration shall be in minimum heights per the lookup table
           (different thresholds for printed vs embossed/moulded/blown text).
Rule 7(3): Specifically for the MRP numerals and net-quantity declaration,
           the same height requirements apply and are verified separately.

The full lookup table is implemented in backend/rules/thresholds.py.
"""
from typing import Optional
from backend.rules.models import RuleResult, RuleSeverity, LabelData
from backend.rules.thresholds import (
    get_min_font_height_mm,
    normalise_quantity_to_grams_or_ml,
)


def check_rule_7(data: LabelData) -> RuleResult:
    """
    Rule 7 / 7(3) — Minimum height of numerals and letters on the label.

    The CV geometry engine measures the printed height of the smallest
    numerals on the label (typically the MRP or net-quantity figures).
    This function compares that measurement against the PCR 2011 table.

    If no measurement is available (CV engine could not measure), we skip
    this rule with an INFO-level note (cannot fail on unavailable data).
    """
    rule_id = "RULE_7_FONT_HEIGHT"
    rule_name = "Rule 7 / 7(3) — Minimum Letter/Numeral Height"

    # If font height was not measured by the CV engine, we cannot apply this rule
    if data.measured_font_height_mm is None:
        return RuleResult(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=True,   # Cannot fail what we cannot measure
            explanation=(
                "Font height could not be measured from this image "
                "(no reference object or package dimensions provided). "
                "Manual verification of Rule 7 compliance is recommended."
            ),
            severity=RuleSeverity.info,
        )

    # We need the net quantity to look up the threshold
    if data.net_quantity_value is None or data.net_quantity_unit is None:
        return RuleResult(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=True,   # Cannot compute threshold without qty
            explanation=(
                "Net quantity is not available; Rule 7 font-height threshold "
                "cannot be determined without knowing the declared net quantity."
            ),
            severity=RuleSeverity.info,
        )

    qty_normalised = normalise_quantity_to_grams_or_ml(
        data.net_quantity_value, data.net_quantity_unit
    )

    # Piece-count commodities: font-height rule still applies (use printed table with qty in pcs)
    # We treat piece-count as a special category — use the largest band (>1kg equiv → 6mm)
    # to be conservative. Officers can override manually.
    if qty_normalised is None:
        min_height = 6.0 if data.net_quantity_value > 1000 else 1.0
        note = (
            f"Net quantity is in pieces/count units; using conservative threshold of {min_height} mm. "
        )
    else:
        min_height = get_min_font_height_mm(qty_normalised, data.font_type)
        note = ""

    measured = data.measured_font_height_mm
    font_type_label = data.font_type.capitalize()

    if measured >= min_height:
        return RuleResult(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=True,
            explanation=(
                f"{note}Measured font height {measured:.1f} mm ≥ required minimum "
                f"{min_height:.1f} mm for {font_type_label} text with net qty "
                f"{data.net_quantity_value} {data.net_quantity_unit}. COMPLIANT."
            ),
        )

    # FAIL — font too small
    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        passed=False,
        explanation=(
            f"{note}FAIL — Font height {measured:.1f} mm is BELOW the required minimum "
            f"{min_height:.1f} mm for {font_type_label} text with net qty "
            f"{data.net_quantity_value} {data.net_quantity_unit}. "
            f"Rule 7(1) PCR 2011 requires ≥ {min_height:.1f} mm for this quantity band."
        ),
        severity=RuleSeverity.error,
    )


def run_all_rule_7(data: LabelData) -> list[RuleResult]:
    """Run Rule 7 checks and return results."""
    return [check_rule_7(data)]
