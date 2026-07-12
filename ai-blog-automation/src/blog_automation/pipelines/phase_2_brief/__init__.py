"""Phase 2 — Content Brief Generation.

Generates detailed content briefs (sections, LSI keywords, sources, angle).
"""

from blog_automation.pipelines.phase_2_brief.brief_generation import (
    generate_content_brief,
    research_keyword_full,
)

__all__ = ["generate_content_brief", "research_keyword_full"]
