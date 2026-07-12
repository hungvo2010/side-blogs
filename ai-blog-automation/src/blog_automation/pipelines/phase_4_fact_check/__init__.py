"""Phase 4 — Fact-Checking.

Extracts claims from articles and verifies them against web evidence.
"""

from blog_automation.pipelines.phase_4_fact_check.fact_checking import (
    extract_claims,
    fact_check_article,
    filter_checkworthy_claims,
    generate_fact_check_report,
    retrieve_evidence,
    verify_claim,
)

__all__ = [
    "extract_claims",
    "filter_checkworthy_claims",
    "retrieve_evidence",
    "verify_claim",
    "generate_fact_check_report",
    "fact_check_article",
]
