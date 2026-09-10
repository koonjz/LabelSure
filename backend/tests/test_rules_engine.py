"""
LabelSure Rules Engine — Comprehensive Unit Tests
Run with: cd backend && python -m pytest tests/test_rules_engine.py -v

Tests cover:
- Rule 6(1)(a): Manufacturer name & address
- Rule 6(1)(b): Generic name
- Rule 6(1)(c): Net quantity
- Rule 6(1)(d): MRP
- Rule 6(1)(e): Manufacture date
- Rule 7: Font height across all quantity bands (printed + embossed)
- Rule 18(2): Sale price vs MRP
- Engine-level: NEEDS_REVIEW flag on low confidence
- Engine-level: Verdict aggregation
- Thresholds: get_min_font_height_mm lookup table
"""
import pytest
import sys
import os

# Allow running from the backend/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.rules.models import LabelData, RuleSeverity
from backend.rules.engine import evaluate_label
from backend.rules.rule_6_1 import (
    check_rule_6_1_a, check_rule_6_1_b, check_rule_6_1_c,
    check_rule_6_1_d, check_rule_6_1_e,
)
from backend.rules.rule_7 import check_rule_7
from backend.rules.rule_18_2 import check_rule_18_2
from backend.rules.thresholds import get_min_font_height_mm, normalise_quantity_to_grams_or_ml


# ─────────────────────────────────────────────────────────────────────────────
# Helper: fully compliant label
# ─────────────────────────────────────────────────────────────────────────────
def compliant_label() -> LabelData:
    return LabelData(
        manufacturer_name="Sunrise Foods Pvt. Ltd.",
        manufacturer_address="Plot 12, MIDC Industrial Area, Pune - 411026",
        generic_name="REFINED SUNFLOWER OIL",
        net_quantity_value=1000.0,
        net_quantity_unit="ml",
        mrp=120.00,
        manufacture_month=3,
        manufacture_year=2024,
        measured_font_height_mm=4.5,
        font_type="printed",
        entered_sale_price=None,
        overall_ocr_confidence=0.92,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 6(1)(a) Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestRule61A:
    def test_pass_with_name_and_address(self):
        data = compliant_label()
        result = check_rule_6_1_a(data)
        assert result.passed is True
        assert result.rule_id == "RULE_6_1_A"

    def test_fail_missing_name(self):
        data = compliant_label()
        data.manufacturer_name = None
        result = check_rule_6_1_a(data)
        assert result.passed is False
        assert "name" in result.explanation.lower()
        assert result.severity == RuleSeverity.error

    def test_fail_missing_address(self):
        data = compliant_label()
        data.manufacturer_address = None
        result = check_rule_6_1_a(data)
        assert result.passed is False
        assert "address" in result.explanation.lower()

    def test_fail_missing_both(self):
        data = compliant_label()
        data.manufacturer_name = None
        data.manufacturer_address = None
        result = check_rule_6_1_a(data)
        assert result.passed is False

    def test_fail_empty_string_name(self):
        data = compliant_label()
        data.manufacturer_name = "   "
        result = check_rule_6_1_a(data)
        assert result.passed is False

    def test_pass_with_minimal_valid_data(self):
        data = compliant_label()
        data.manufacturer_name = "XYZ Ltd"
        data.manufacturer_address = "Delhi - 110001"
        result = check_rule_6_1_a(data)
        assert result.passed is True


# ─────────────────────────────────────────────────────────────────────────────
# Rule 6(1)(b) Tests — Generic Name
# ─────────────────────────────────────────────────────────────────────────────
class TestRule61B:
    def test_pass_with_generic_name(self):
        data = compliant_label()
        result = check_rule_6_1_b(data)
        assert result.passed is True

    def test_fail_missing_generic_name(self):
        data = compliant_label()
        data.generic_name = None
        result = check_rule_6_1_b(data)
        assert result.passed is False

    def test_fail_empty_generic_name(self):
        data = compliant_label()
        data.generic_name = ""
        result = check_rule_6_1_b(data)
        assert result.passed is False


# ─────────────────────────────────────────────────────────────────────────────
# Rule 6(1)(c) Tests — Net Quantity
# ─────────────────────────────────────────────────────────────────────────────
class TestRule61C:
    def test_pass_with_value_and_unit(self):
        data = compliant_label()
        result = check_rule_6_1_c(data)
        assert result.passed is True

    def test_fail_missing_value(self):
        data = compliant_label()
        data.net_quantity_value = None
        result = check_rule_6_1_c(data)
        assert result.passed is False

    def test_fail_zero_value(self):
        data = compliant_label()
        data.net_quantity_value = 0
        result = check_rule_6_1_c(data)
        assert result.passed is False

    def test_fail_missing_unit(self):
        data = compliant_label()
        data.net_quantity_unit = None
        result = check_rule_6_1_c(data)
        assert result.passed is False

    def test_pass_various_units(self):
        for unit in ["g", "kg", "ml", "l", "pcs"]:
            data = compliant_label()
            data.net_quantity_unit = unit
            data.net_quantity_value = 500.0
            result = check_rule_6_1_c(data)
            assert result.passed is True, f"Failed for unit: {unit}"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 6(1)(d) Tests — MRP
# ─────────────────────────────────────────────────────────────────────────────
class TestRule61D:
    def test_pass_with_mrp(self):
        data = compliant_label()
        result = check_rule_6_1_d(data)
        assert result.passed is True

    def test_fail_missing_mrp(self):
        data = compliant_label()
        data.mrp = None
        result = check_rule_6_1_d(data)
        assert result.passed is False

    def test_fail_zero_mrp(self):
        data = compliant_label()
        data.mrp = 0.0
        result = check_rule_6_1_d(data)
        assert result.passed is False

    def test_pass_high_mrp(self):
        data = compliant_label()
        data.mrp = 9999.99
        result = check_rule_6_1_d(data)
        assert result.passed is True


# ─────────────────────────────────────────────────────────────────────────────
# Rule 6(1)(e) Tests — Manufacture Date
# ─────────────────────────────────────────────────────────────────────────────
class TestRule61E:
    def test_pass_with_valid_date(self):
        data = compliant_label()
        result = check_rule_6_1_e(data)
        assert result.passed is True

    def test_fail_missing_month(self):
        data = compliant_label()
        data.manufacture_month = None
        result = check_rule_6_1_e(data)
        assert result.passed is False

    def test_fail_missing_year(self):
        data = compliant_label()
        data.manufacture_year = None
        result = check_rule_6_1_e(data)
        assert result.passed is False

    def test_fail_future_year(self):
        data = compliant_label()
        data.manufacture_year = 2099
        result = check_rule_6_1_e(data)
        assert result.passed is False
        assert result.severity == RuleSeverity.warning

    def test_fail_invalid_month(self):
        data = compliant_label()
        data.manufacture_month = 13  # invalid
        result = check_rule_6_1_e(data)
        assert result.passed is False

    def test_pass_boundary_months(self):
        for m in [1, 12]:
            data = compliant_label()
            data.manufacture_month = m
            result = check_rule_6_1_e(data)
            assert result.passed is True, f"Failed for month {m}"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 7 Tests — Font Height
# ─────────────────────────────────────────────────────────────────────────────
class TestRule7:
    def test_pass_adequate_font_height(self):
        data = compliant_label()
        data.net_quantity_value = 1000.0
        data.net_quantity_unit = "ml"
        data.measured_font_height_mm = 4.5  # required: 4.0 mm
        result = check_rule_7(data)
        assert result.passed is True

    def test_fail_font_too_small(self):
        data = compliant_label()
        data.net_quantity_value = 1000.0
        data.net_quantity_unit = "ml"
        data.measured_font_height_mm = 2.0   # required: 4.0 mm
        result = check_rule_7(data)
        assert result.passed is False
        assert "2.0 mm" in result.explanation

    def test_skip_when_no_measurement(self):
        data = compliant_label()
        data.measured_font_height_mm = None
        result = check_rule_7(data)
        assert result.passed is True  # can't fail on unavailable data
        assert result.severity == RuleSeverity.info

    def test_skip_when_no_qty(self):
        data = compliant_label()
        data.net_quantity_value = None
        result = check_rule_7(data)
        assert result.passed is True
        assert result.severity == RuleSeverity.info

    def test_embossed_different_thresholds(self):
        # Embossed ≤200g/ml → 1mm threshold
        data = compliant_label()
        data.net_quantity_value = 100.0
        data.net_quantity_unit = "g"
        data.font_type = "embossed"
        data.measured_font_height_mm = 1.5   # required: 1.0 mm
        result = check_rule_7(data)
        assert result.passed is True

    def test_embossed_fail_too_small(self):
        # Embossed > 1kg → 4mm threshold
        data = compliant_label()
        data.net_quantity_value = 2000.0
        data.net_quantity_unit = "g"
        data.font_type = "embossed"
        data.measured_font_height_mm = 1.5   # required: 4.0 mm
        result = check_rule_7(data)
        assert result.passed is False


# ─────────────────────────────────────────────────────────────────────────────
# Thresholds lookup table tests
# ─────────────────────────────────────────────────────────────────────────────
class TestThresholds:
    """Test the complete font-height lookup table per PCR 2011 Rule 7."""

    # Printed text thresholds
    @pytest.mark.parametrize("qty_g_ml, expected_mm", [
        (10.0,   1.0),   # ≤50g
        (50.0,   1.0),   # boundary ≤50g
        (51.0,   2.0),   # >50 ≤200
        (200.0,  2.0),   # boundary ≤200
        (201.0,  4.0),   # >200 ≤1000
        (1000.0, 4.0),   # boundary ≤1000 (=1kg)
        (1001.0, 6.0),   # >1kg
        (5000.0, 6.0),   # >1kg
    ])
    def test_printed_thresholds(self, qty_g_ml, expected_mm):
        result = get_min_font_height_mm(qty_g_ml, "printed")
        assert result == expected_mm, (
            f"Printed {qty_g_ml}g/ml: expected {expected_mm}mm, got {result}mm"
        )

    # Embossed text thresholds
    @pytest.mark.parametrize("qty_g_ml, expected_mm", [
        (100.0,   1.0),   # ≤200g
        (200.0,   1.0),   # boundary ≤200
        (201.0,   2.0),   # >200 ≤1000
        (1000.0,  2.0),   # boundary ≤1000
        (1001.0,  4.0),   # >1kg ≤10kg
        (10000.0, 4.0),   # boundary 10kg
        (10001.0, 6.0),   # >10kg
    ])
    def test_embossed_thresholds(self, qty_g_ml, expected_mm):
        result = get_min_font_height_mm(qty_g_ml, "embossed")
        assert result == expected_mm, (
            f"Embossed {qty_g_ml}g/ml: expected {expected_mm}mm, got {result}mm"
        )

    def test_unit_normalisation_kg(self):
        result = normalise_quantity_to_grams_or_ml(1.5, "kg")
        assert result == 1500.0

    def test_unit_normalisation_litre(self):
        result = normalise_quantity_to_grams_or_ml(2.0, "l")
        assert result == 2000.0

    def test_unit_normalisation_pcs_returns_none(self):
        result = normalise_quantity_to_grams_or_ml(6, "pcs")
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Rule 18(2) Tests — Sale Price vs MRP
# ─────────────────────────────────────────────────────────────────────────────
class TestRule182:
    def test_no_sale_price_entered(self):
        data = compliant_label()
        data.entered_sale_price = None
        result = check_rule_18_2(data)
        assert result.passed is True
        assert result.severity == RuleSeverity.info

    def test_sale_price_equals_mrp(self):
        data = compliant_label()
        data.entered_sale_price = 120.00
        data.mrp = 120.00
        result = check_rule_18_2(data)
        assert result.passed is True

    def test_sale_price_below_mrp(self):
        data = compliant_label()
        data.entered_sale_price = 100.00
        data.mrp = 120.00
        result = check_rule_18_2(data)
        assert result.passed is True

    def test_sale_price_above_mrp(self):
        data = compliant_label()
        data.entered_sale_price = 150.00
        data.mrp = 120.00
        result = check_rule_18_2(data)
        assert result.passed is False
        assert "₹30.00" in result.explanation   # excess amount

    def test_sale_price_missing_mrp(self):
        data = compliant_label()
        data.entered_sale_price = 120.00
        data.mrp = None
        result = check_rule_18_2(data)
        assert result.passed is False
        assert result.severity == RuleSeverity.warning

    def test_large_price_violation(self):
        data = compliant_label()
        data.entered_sale_price = 999.99
        data.mrp = 100.00
        result = check_rule_18_2(data)
        assert result.passed is False
        assert "899.99" in result.explanation


# ─────────────────────────────────────────────────────────────────────────────
# Engine-level integration tests
# ─────────────────────────────────────────────────────────────────────────────
class TestEngine:
    def test_fully_compliant_label(self):
        data = compliant_label()
        verdict = evaluate_label(data, ocr_confidence=0.95)
        assert verdict.is_compliant is True
        assert verdict.needs_manual_review is False
        assert verdict.verdict_str == "COMPLIANT"

    def test_non_compliant_missing_mrp(self):
        data = compliant_label()
        data.mrp = None
        verdict = evaluate_label(data, ocr_confidence=0.95)
        assert verdict.is_compliant is False
        assert verdict.verdict_str == "NON_COMPLIANT"
        failed_ids = {r.rule_id for r in verdict.failed_rules}
        assert "RULE_6_1_D" in failed_ids

    def test_needs_review_low_confidence(self):
        data = compliant_label()
        verdict = evaluate_label(data, ocr_confidence=0.40)
        assert verdict.needs_manual_review is True
        assert verdict.verdict_str == "NEEDS_REVIEW"
        assert verdict.review_reason is not None

    def test_needs_review_threshold_boundary(self):
        data = compliant_label()
        # Exactly at threshold: should NOT trigger review
        verdict = evaluate_label(data, ocr_confidence=0.70)
        assert verdict.needs_manual_review is False

    def test_multiple_rule_failures(self):
        data = LabelData(
            # Everything missing
            manufacturer_name=None,
            manufacturer_address=None,
            generic_name=None,
            net_quantity_value=None,
            net_quantity_unit=None,
            mrp=None,
            manufacture_month=None,
            manufacture_year=None,
        )
        verdict = evaluate_label(data, ocr_confidence=0.90)
        assert verdict.is_compliant is False
        assert len(verdict.failed_rules) >= 4   # at least all 6(1) fields missing

    def test_rule_results_always_returned(self):
        data = compliant_label()
        verdict = evaluate_label(data, ocr_confidence=0.95)
        # All rules should have a result (even passing ones)
        rule_ids = {r.rule_id for r in verdict.rule_results}
        assert "RULE_6_1_A" in rule_ids
        assert "RULE_6_1_B" in rule_ids
        assert "RULE_6_1_C" in rule_ids
        assert "RULE_6_1_D" in rule_ids
        assert "RULE_6_1_E" in rule_ids
        assert "RULE_7_FONT_HEIGHT" in rule_ids
        assert "RULE_18_2" in rule_ids

    def test_sale_price_violation_makes_non_compliant(self):
        data = compliant_label()
        data.entered_sale_price = 999.00
        verdict = evaluate_label(data, ocr_confidence=0.90)
        assert verdict.is_compliant is False
        failed_ids = {r.rule_id for r in verdict.failed_rules}
        assert "RULE_18_2" in failed_ids
