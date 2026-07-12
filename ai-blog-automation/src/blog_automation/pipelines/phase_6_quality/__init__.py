"""Phase 6 — Quality Gates.

Final quality checks before publishing: plagiarism, links, readability,
metadata validation.
"""

from blog_automation.pipelines.phase_6_quality.quality_gates import (
    check_plagiarism,
    check_readability,
    run_quality_gates,
    validate_metadata,
    verify_links,
)

__all__ = [
    "check_plagiarism",
    "verify_links",
    "check_readability",
    "validate_metadata",
    "run_quality_gates",
]
