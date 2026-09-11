"""
LabelSure Rules Engine — Data Models
Pure dataclasses; no ORM or FastAPI imports.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class RuleSeverity(str, Enum):
    error = "error"       # mandatory — causes NON_COMPLIANT
    warning = "warning"   # potential issue — causes NON_COMPLIANT
    info = "info"         # informational only


@dataclass
class RuleResult:
    """Result of evaluating a single compliance rule."""
    rule_id: str                           # e.g. "RULE_6_1_A"
    rule_name: str                         # Short display name
    passed: bool
    explanation: str                       # Plain-language description of pass/fail reason
    severity: RuleSeverity = RuleSeverity.error


@dataclass
class LabelData:
    """
    Structured representation of extracted label data passed to the rules engine.
    All fields are Optional — missing fields are what rules check for.
    """
    # Rule 6(1)(a)
    manufacturer_name: Optional[str] = None
    manufacturer_address: Optional[str] = None

    # Rule 6(1) — generic name and net quantity
    generic_name: Optional[str] = None
    net_quantity_value: Optional[float] = None    # numeric part of net qty
    net_quantity_unit: Optional[str] = None       # g | ml | kg | l | pcs

    # Rule 6(1) — MRP
    mrp: Optional[float] = None                  # INR, all-taxes-inclusive

    # Rule 6(1) — date of manufacture
    manufacture_month: Optional[int] = None       # 1–12
    manufacture_year: Optional[int] = None        # e.g. 2023

    # Additional standard food label declarations
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    fssai_license: Optional[str] = None
    consumer_care: Optional[str] = None

    # Rule 7 — font geometry (measured by CV engine)
    measured_font_height_mm: Optional[float] = None  # min measured height of MRP/qty numerals
    font_type: str = "printed"                   # "printed" | "embossed"

    # Rule 18(2) — sale price check
    entered_sale_price: Optional[float] = None   # price observed/entered by officer

    # Meta
    overall_ocr_confidence: float = 1.0
    detected_language: Optional[str] = None



@dataclass
class Verdict:
    """Final compliance verdict for a scanned label."""
    is_compliant: bool
    needs_manual_review: bool
    review_reason: Optional[str]
    rule_results: List[RuleResult] = field(default_factory=list)

    @property
    def verdict_str(self) -> str:
        if self.needs_manual_review:
            return "NEEDS_REVIEW"
        return "COMPLIANT" if self.is_compliant else "NON_COMPLIANT"

    @property
    def failed_rules(self) -> List[RuleResult]:
        return [r for r in self.rule_results if not r.passed]
