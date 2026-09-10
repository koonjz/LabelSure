"""
LabelSure — Field Extractor Unit Tests
Tests that regex patterns correctly parse common label text formats.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from backend.processing.field_extractor import (
    _extract_mrp, _extract_net_qty, _extract_mfg_date,
    _extract_manufacturer_name, _extract_manufacturer_address,
)


class TestExtractMRP:
    def test_rupee_symbol(self):
        assert _extract_mrp("MRP ₹45.00") == 45.00

    def test_rs_prefix(self):
        assert _extract_mrp("M.R.P. Rs.120") == 120.0

    def test_no_currency_prefix(self):
        assert _extract_mrp("MRP: 89") == 89.0

    def test_maximum_retail_price(self):
        assert _extract_mrp("Maximum Retail Price Rs. 250.50") == 250.50

    def test_no_mrp(self):
        assert _extract_mrp("Product Name: Biscuits") is None


class TestExtractNetQty:
    def test_grams(self):
        val, unit = _extract_net_qty("Net Wt. 500g")
        assert val == 500.0
        assert unit == "g"

    def test_kg(self):
        val, unit = _extract_net_qty("Net Weight: 1.5 kg")
        assert val == 1.5
        assert unit == "kg"

    def test_ml(self):
        val, unit = _extract_net_qty("Contents: 200 ml")
        assert val == 200.0
        assert unit == "ml"

    def test_litre(self):
        val, unit = _extract_net_qty("1 Litre")
        assert val == 1.0
        assert unit == "l"

    def test_pcs(self):
        val, unit = _extract_net_qty("6 Pcs")
        assert val == 6.0
        assert unit == "pcs"

    def test_no_qty(self):
        val, unit = _extract_net_qty("Brand Name: XYZ")
        assert val is None
        assert unit is None


class TestExtractMfgDate:
    def test_mm_yyyy_slash(self):
        month, year = _extract_mfg_date("Mfg. Date: 06/2023")
        assert month == 6
        assert year == 2023

    def test_month_name_year(self):
        month, year = _extract_mfg_date("Date of Mfg: Mar 2024")
        assert month == 3
        assert year == 2024

    def test_no_date(self):
        month, year = _extract_mfg_date("No date here")
        assert month is None
        assert year is None

    def test_mfd_format(self):
        month, year = _extract_mfg_date("MFD: 12/2022")
        assert month == 12
        assert year == 2022


class TestExtractManufacturer:
    def test_manufactured_by(self):
        name = _extract_manufacturer_name("Manufactured by: Sunrise Foods Pvt. Ltd., Pune")
        assert name is not None
        assert "Sunrise Foods" in name

    def test_packed_by(self):
        name = _extract_manufacturer_name("Packed by ABC Enterprises, Mumbai")
        assert name is not None

    def test_no_manufacturer_keyword(self):
        name = _extract_manufacturer_name("Just some random text")
        assert name is None

    def test_address_with_pincode(self):
        addr = _extract_manufacturer_address("Plot 12, MIDC Area, Pune - 411026")
        assert addr is not None
        assert "411026" in addr
