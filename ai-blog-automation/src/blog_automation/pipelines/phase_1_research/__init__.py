"""Phase 1 — Keyword Research.

Fetches keyword data from Ahrefs and creates the initial content brief.
"""

from blog_automation.pipelines.phase_1_research.keyword_research import (
    get_next_keyword_from_calendar,
    research_keyword,
)

__all__ = ["research_keyword", "get_next_keyword_from_calendar"]
