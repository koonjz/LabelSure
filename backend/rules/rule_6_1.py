"""
LabelSure Rules Engine — Rule 6(1) Mandatory Field Checks
India Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1) and 6(1)(a).

Checks:
  RULE_6_1_A  : Name & registered address of manufacturer/packer/importer
  RULE_6_1_B  : Generic/common name of the commodity
  RULE_6_1_C  : Net quantity (weight, volume, or count)
  RULE_6_1_D  : MRP inclusive of all taxes (rupees)
  RULE_6_1_E  : Month and year of manufacture/import/packing
"""
from backend.rules.models import RuleResult, RuleSeverity, LabelData
from datetime import datetime


def check_rule_6_1_a(data: LabelData) -> RuleResult:
    """
    Rule 6(1)(a): Every package shall bear the name and address of the
    manufacturer, packer or importer, as the case may be.
    """
    rule_id = "RULE_6_1_A"
    rule_name = "Rule 6(1)(a) — Manufacturer/Packer/Importer Name & Address"

    has_name = bool(data.manufacturer_name and data.manufacturer_name.strip())
    has_address = bool(data.manufacturer_address and data.manufacturer_address.strip())

    if has_name and has_address:
        return RuleResult(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=True,
            explanation=(
                f"Name '{data.manufacturer_name}' and address "
                f"'{data.manufacturer_address}' are present."
            ),
        )

    missing = []
    if not has_name:
        missing.append("manufacturer/packer/importer name")
    if not has_address:
        missing.append("registered address")

    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        passed=False,
        explanation=(
            f"FAIL — Missing: {', '.join(missing)}. "
            "Rule 6(1)(a) requires the name and full registered address of the "
            "manufacturer, packer, or importer to be declared on every package."
        ),
        severity=RuleSeverity.error,
    )


def check_rule_6_1_b(data: LabelData) -> RuleResult:
    """
    Rule 6(1): Every package shall carry the generic or common name of the commodity.
    """
    rule_id = "RULE_6_1_B"
    rule_name = "Rule 6(1) — Generic/Common Name of Commodity"

    if data.generic_name and data.generic_name.strip():
        return RuleResult(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=True,
            explanation=f"Generic name '{data.generic_name}' is declared.",
        )

    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        passed=False,
        explanation=(
            "FAIL — Generic or common name of the commodity is missing. "
            "Every package must state what the product actually is (e.g. 'Refined Sunflower Oil')."
        ),
        severity=RuleSeverity.error,
    )


def check_rule_6_1_c(data: LabelData) -> RuleResult:
    """
    Rule 6(1): Net quantity in terms of standard unit of weight or measure
    (or count, for certain commodities).
    """
    rule_id = "RULE_6_1_C"
    rule_name = "Rule 6(1) — Net Quantity"

    has_value = data.net_quantity_value is not None and data.net_quantity_value > 0
    has_unit = bool(data.net_quantity_unit and data.net_quantity_unit.strip())

    if has_value and has_unit:
        return RuleResult(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=True,
            explanation=(
                f"Net quantity '{data.net_quantity_value} {data.net_quantity_unit}' is declared."
            ),
        )

    missing = []
    if not has_value:
        missing.append("quantity value")
    if not has_unit:
        missing.append("unit of measurement")

    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        passed=False,
        explanation=(
            f"FAIL — Net quantity is incomplete: missing {', '.join(missing)}. "
            "The label must state the net quantity in standard units (e.g. '500 g', '1 L', '6 Pcs')."
        ),
        severity=RuleSeverity.error,
    )


def check_rule_6_1_d(data: LabelData) -> RuleResult:
    """
    Rule 6(1): Maximum Retail Price (MRP) inclusive of all taxes must be declared.
    Must be prefixed with 'MRP' and state 'inclusive of all taxes'.
    """
    rule_id = "RULE_6_1_D"
    rule_name = "Rule 6(1) — MRP (Inclusive of All Taxes)"

    if data.mrp is not None and data.mrp > 0:
        return RuleResult(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=True,
            explanation=f"MRP ₹{data.mrp:.2f} (inclusive of all taxes) is declared.",
        )

    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        passed=False,
        explanation=(
            "FAIL — MRP (Maximum Retail Price) inclusive of all taxes is missing. "
            "Every package must display the MRP in the format 'MRP ₹XX.XX (Incl. of all taxes)'."
        ),
        severity=RuleSeverity.error,
    )


def check_rule_6_1_e(data: LabelData) -> RuleResult:
    """
    Rule 6(1): Month and year of manufacture, packing, or import must be declared.
    """
    rule_id = "RULE_6_1_E"
    rule_name = "Rule 6(1) — Month & Year of Manufacture/Packing/Import"

    has_month = data.manufacture_month is not None and 1 <= data.manufacture_month <= 12
    has_year = data.manufacture_year is not None and data.manufacture_year >= 1900

    if has_month and has_year:
        current_year = datetime.now().year
        # Warn if the year is in the future (likely OCR error)
        if data.manufacture_year > current_year:
            return RuleResult(
                rule_id=rule_id,
                rule_name=rule_name,
                passed=False,
                explanation=(
                    f"FAIL — Manufacture year {data.manufacture_year} is in the future "
                    f"(current year: {current_year}). This likely indicates an OCR error or "
                    "an incorrectly printed label."
                ),
                severity=RuleSeverity.warning,
            )
        return RuleResult(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=True,
            explanation=(
                f"Month {data.manufacture_month:02d}/{data.manufacture_year} of manufacture is declared."
            ),
        )

    missing = []
    if not has_month:
        missing.append("month")
    if not has_year:
        missing.append("year")

    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        passed=False,
        explanation=(
            f"FAIL — {', '.join(missing).capitalize()} of manufacture/packing/import is missing. "
            "The label must state the month and year of manufacture, packing, or import."
        ),
        severity=RuleSeverity.error,
    )


def run_all_rule_6_1(data: LabelData) -> list[RuleResult]:
    """Run all Rule 6(1) checks and return results."""
    return [
        check_rule_6_1_a(data),
        check_rule_6_1_b(data),
        check_rule_6_1_c(data),
        check_rule_6_1_d(data),
        check_rule_6_1_e(data),
    ]
