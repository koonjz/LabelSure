"""
Unit tests for field_extractor regex patterns.
Run with:  python3 -m pytest backend/tests/test_field_extractor.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from backend.processing.field_extractor import (
    _extract_mrp,
    _extract_net_qty,
    _extract_mfg_date,
    _extract_batch_number,
    _extract_expiry,
    _extract_fssai,
    _extract_consumer_care,
    _extract_manufacturer_name,
    _normalize_ocr_text,
)


# ── MRP ──────────────────────────────────────────────────────────────────────

class TestMRP:
    def test_mrp_simple(self):
        assert _extract_mrp("MRP ₹150") == 150.0

    def test_mrp_with_slash(self):
        assert _extract_mrp("MRP: ₹150/-") == 150.0

    def test_mrp_with_taxes(self):
        assert _extract_mrp("MRP (Incl. of all taxes) : Rs. 25/-") == 25.0

    def test_mrp_dotted(self):
        assert _extract_mrp("M.R.P. Rs 20.00") == 20.0

    def test_mrp_question_mark_artifact(self):
        """OCR often reads ₹ as ? — should still match after normalization"""
        text = _normalize_ocr_text("MRP ?150/-")
        assert _extract_mrp(text) == 150.0

    def test_mrp_star_artifact(self):
        text = _normalize_ocr_text("MRP *250")
        assert _extract_mrp(text) == 250.0

    def test_standalone_rupee(self):
        assert _extract_mrp("₹ 99") == 99.0

    def test_standalone_rs(self):
        assert _extract_mrp("Rs. 45/-") == 45.0

    def test_mrp_decimal(self):
        assert _extract_mrp("MRP Rs. 14.50") == 14.5

    def test_mrp_max_retail(self):
        assert _extract_mrp("Maximum Retail Price: 500") == 500.0

    def test_mrp_not_found(self):
        assert _extract_mrp("No price here") is None


# ── Net Quantity ──────────────────────────────────────────────────────────────

class TestNetQty:
    def test_net_weight_gm(self):
        val, unit = _extract_net_qty("Net Weight : 250 Gm")
        assert val == 250.0 and unit == "g"

    def test_net_wt_kg(self):
        val, unit = _extract_net_qty("NET WT. 1 kg")
        assert val == 1.0 and unit == "kg"

    def test_net_vol_ml(self):
        val, unit = _extract_net_qty("Net Volume: 500 ml")
        assert val == 500.0 and unit == "ml"

    def test_standalone_g(self):
        val, unit = _extract_net_qty("BISCUITS 100g")
        assert val == 100.0 and unit == "g"

    def test_nett_weight(self):
        val, unit = _extract_net_qty("Nett Wt. 200 g")
        assert val == 200.0 and unit == "g"

    def test_not_found(self):
        val, unit = _extract_net_qty("No quantity info")
        assert val is None and unit is None


# ── Manufacturing Date ────────────────────────────────────────────────────────

class TestMfgDate:
    def test_mfg_ddmmyyyy(self):
        m, y = _extract_mfg_date("Mfg. Date: 09/05/2025")
        assert y == 2025

    def test_mfg_mmyyyy(self):
        m, y = _extract_mfg_date("Packed On: 06/2024")
        assert m == 6 and y == 2024

    def test_mfg_mon_yyyy(self):
        m, y = _extract_mfg_date("MFD: Jun 2023")
        assert m == 6 and y == 2023

    def test_mfg_pkd(self):
        m, y = _extract_mfg_date("PKD: 07/2022")
        assert m == 7 and y == 2022

    def test_mfg_two_digit_year(self):
        m, y = _extract_mfg_date("Packed On: 03/24")
        assert m == 3 and y == 2024


# ── Batch Number ──────────────────────────────────────────────────────────────

class TestBatchNumber:
    def test_batch_no(self):
        assert _extract_batch_number("Batch No.: ABC123") == "ABC123"

    def test_lot_no(self):
        assert _extract_batch_number("LOT No. XYZ-456") == "XYZ-456"

    def test_b_no(self):
        assert _extract_batch_number("B. No.: B2024001") == "B2024001"

    def test_not_found(self):
        assert _extract_batch_number("No batch info here") is None


# ── Expiry ────────────────────────────────────────────────────────────────────

class TestExpiry:
    def test_best_before(self):
        result = _extract_expiry("Best Before: 12 Months from Mfg Date\nMRP ₹25")
        assert result is not None and "12" in result

    def test_use_by(self):
        result = _extract_expiry("Use By: 30/06/2025\nBatch No. A1")
        assert result is not None

    def test_exp_date(self):
        result = _extract_expiry("Exp. Date: 08/2025\nStore in cool")
        assert result is not None

    def test_bbd(self):
        result = _extract_expiry("BBD: 01/2026\nMfg Date: 01/2025")
        assert result is not None


# ── FSSAI ─────────────────────────────────────────────────────────────────────

class TestFSSAI:
    def test_fssai_with_keyword(self):
        result = _extract_fssai("FSSAI Lic. No.: 10013022002234\nBest Before")
        assert result is not None and "10013022002234" in result

    def test_fssai_14digit_standalone(self):
        result = _extract_fssai("Some text\n10013022002234\nMore text")
        assert result == "10013022002234"

    def test_fssai_not_found(self):
        assert _extract_fssai("No license number here") is None


# ── Consumer Care ─────────────────────────────────────────────────────────────

class TestConsumerCare:
    def test_consumer_care_phone(self):
        result = _extract_consumer_care("Consumer Care: 1800-102-3456\nMRP")
        assert result is not None

    def test_customer_care(self):
        result = _extract_consumer_care("Customer Care: info@company.com\nBatch")
        assert result is not None

    def test_toll_free(self):
        result = _extract_consumer_care("Toll Free: 1800-XXX-XXXX\nMRP ₹50")
        assert result is not None

    def test_phone_fallback(self):
        result = _extract_consumer_care("Ph: +91-9876543210")
        assert result is not None


# ── OCR Text Normalizer ───────────────────────────────────────────────────────

class TestNormalizer:
    def test_fix_broken_mrp_line(self):
        text = _normalize_ocr_text("MR\nP : 25")
        assert "MRP" in text

    def test_question_to_rupee(self):
        text = _normalize_ocr_text("MRP ?150")
        assert "₹150" in text or "?150" not in text  # ? before digit replaced

    def test_star_to_rupee(self):
        text = _normalize_ocr_text("Price *99/-")
        assert "₹99" in text


# ── Manufacturer Name ─────────────────────────────────────────────────────────

class TestManufacturerName:
    def test_manufactured_by(self):
        text = "Manufactured by Acme Foods Pvt Ltd\nNet Wt. 200g"
        result = _extract_manufacturer_name(text)
        assert result is not None and "Acme" in result

    def test_packed_by(self):
        text = "Packed by XYZ Industries\nMRP ₹50"
        result = _extract_manufacturer_name(text)
        assert result is not None and "XYZ" in result

    def test_marketed_by(self):
        text = "Marketed by ABC Corp.\nBatch No. 123"
        result = _extract_manufacturer_name(text)
        assert result is not None and "ABC" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
