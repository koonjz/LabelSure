"""
LabelSure Rules Engine — Rule 18(2): Sale Price vs MRP
India Legal Metrology (Packaged Commodities) Rules, 2011.

Rule 18(2): No person shall sell or offer for sale any pre-packaged commodity
at a price exceeding the Maximum Retail Price declared on the package.
Violation is a cognizable offence under the Legal Metrology Act, 2009, s.36.
"""
from backend.rules.models import RuleResult, RuleSeverity, LabelData


def check_rule_18_2(data: LabelData) -> RuleResult:
    """
    Rule 18(2) — Sale price must not exceed declared MRP.

    Only evaluated when:
    - entered_sale_price is provided (officer/seller entered it during the scan)
    - mrp is available (extracted from the label)
    """
    rule_id = "RULE_18_2"
    rule_name = "Rule 18(2) — Sale Price Must Not Exceed MRP"

    # Can't check if sale price wasn't entered
    if data.entered_sale_price is None:
        return RuleResult(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=True,
            explanation=(
                "No sale price was entered for this scan. "
                "Rule 18(2) applies only when a sale price is compared against MRP."
            ),
            severity=RuleSeverity.info,
        )

    # Can't check if MRP is unknown
    if data.mrp is None:
        return RuleResult(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=False,
            explanation=(
                "FAIL — MRP could not be read from the label, but a sale price of "
                f"₹{data.entered_sale_price:.2f} was entered. "
                "Unable to verify Rule 18(2) compliance without a declared MRP."
            ),
            severity=RuleSeverity.warning,
        )

    sale_price = data.entered_sale_price
    mrp = data.mrp

    if sale_price <= mrp:
        return RuleResult(
            rule_id=rule_id,
            rule_name=rule_name,
            passed=True,
            explanation=(
                f"Sale price ₹{sale_price:.2f} ≤ declared MRP ₹{mrp:.2f}. COMPLIANT."
            ),
        )

    excess = sale_price - mrp
    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        passed=False,
        explanation=(
            f"FAIL — Sale price ₹{sale_price:.2f} EXCEEDS declared MRP ₹{mrp:.2f} "
            f"by ₹{excess:.2f}. Rule 18(2) PCR 2011 prohibits selling at a price "
            "above the MRP printed on the package. This constitutes a cognizable offence "
            "under Legal Metrology Act 2009, section 36."
        ),
        severity=RuleSeverity.error,
    )


def run_all_rule_18_2(data: LabelData) -> list[RuleResult]:
    return [check_rule_18_2(data)]
