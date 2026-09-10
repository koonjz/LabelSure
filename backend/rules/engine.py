"""
LabelSure Rules Engine — Main Orchestrator
Runs all PCR 2011 rules and returns a final Verdict.

Usage:
    from backend.rules.engine import evaluate_label
    verdict = evaluate_label(label_data, ocr_confidence=0.88)
"""
import os
from typing import List
from backend.rules.models import LabelData, RuleResult, RuleSeverity, Verdict
from backend.rules.rule_6_1 import run_all_rule_6_1
from backend.rules.rule_7 import run_all_rule_7
from backend.rules.rule_18_2 import run_all_rule_18_2
from backend.rules.thresholds import OCR_CONFIDENCE_THRESHOLD


def _load_version() -> str:
    version_file = os.path.join(os.path.dirname(__file__), "VERSION")
    try:
        with open(version_file) as f:
            return f.readline().strip()
    except FileNotFoundError:
        return "unknown"


RULES_VERSION = _load_version()


def evaluate_label(
    data: LabelData,
    ocr_confidence: float = 1.0,
) -> Verdict:
    """
    Run all compliance rules against the extracted label data.

    Args:
        data:           Structured label data extracted by the OCR/field extractor.
        ocr_confidence: Minimum OCR confidence score across all extracted fields.
                        Below OCR_CONFIDENCE_THRESHOLD → verdict is flagged as NEEDS_REVIEW
                        instead of committing to COMPLIANT/NON_COMPLIANT.

    Returns:
        A Verdict containing individual RuleResult objects and the overall verdict.
    """
    all_results: List[RuleResult] = []

    # --- Run all rule families ---
    all_results.extend(run_all_rule_6_1(data))
    all_results.extend(run_all_rule_7(data))
    all_results.extend(run_all_rule_18_2(data))

    # --- Determine overall pass/fail ---
    error_failures = [
        r for r in all_results
        if not r.passed and r.severity in (RuleSeverity.error, RuleSeverity.warning)
    ]
    is_compliant = len(error_failures) == 0

    # --- Check if OCR confidence is too low to trust the verdict ---
    needs_review = False
    review_reason = None
    if ocr_confidence < OCR_CONFIDENCE_THRESHOLD:
        needs_review = True
        review_reason = (
            f"OCR confidence {ocr_confidence:.0%} is below threshold "
            f"{OCR_CONFIDENCE_THRESHOLD:.0%}. The image may be blurry, glare-affected, "
            "or the text curved/occluded. Manual review is required before acting on this verdict."
        )

    return Verdict(
        is_compliant=is_compliant,
        needs_manual_review=needs_review,
        review_reason=review_reason,
        rule_results=all_results,
    )
