"""Content Brief model for storing keyword research and content briefs."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from blog_automation.models.base import BaseModel


class ContentBrief(BaseModel):
    """Content Brief model for keyword research and content planning.

    Stores all research data needed to generate an article including:
    - Keyword metrics from Ahrefs
    - Competitor analysis
    - Section recommendations
    - LSI keywords
    - External sources
    """

    __tablename__ = "content_briefs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Core fields
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    search_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Brief data (JSON structure)
    brief_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    """
    brief_data structure:
    {
        "sections": [
            {
                "h2": "Section Title",
                "purpose": "Why this section",
                "target_length": "200-300 words",
                "key_points": ["point1", "point2"]
            }
        ],
        "lsi_keywords": ["keyword1", "keyword2"],
        "sources": [
            {"url": "...", "title": "...", "snippet": "..."}
        ],
        "unique_angle": "...",
        "target_audience": "...",
        "pain_points": ["..."],
        "target_word_count": 2000,
        "competitor_analysis": {
            "avg_word_count": 1800,
            "common_h2s": ["..."],
            "top_pages": [...]
        }
    }
    """

    # SERP features
    serp_features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    """
    serp_features structure:
    {
        "featured_snippet": true,
        "people_also_ask": ["q1", "q2"],
        "tables": false,
        "videos": true
    }
    """

    # Competitor data
    competitor_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Validation status
    is_valid: Mapped[bool] = mapped_column(default=False)
    validation_errors: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Link to article (optional, set when article is created)
    article_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("articles.id"), nullable=True
    )

    def get_sections(self) -> list[dict]:
        """Get recommended H2 sections.

        Returns:
            List of section dictionaries
        """
        if not self.brief_data:
            return []
        return self.brief_data.get("sections", [])

    def get_lsi_keywords(self) -> list[str]:
        """Get LSI keywords.

        Returns:
            List of LSI keywords
        """
        if not self.brief_data:
            return []
        return self.brief_data.get("lsi_keywords", [])

    def get_sources(self) -> list[dict]:
        """Get external sources.

        Returns:
            List of source dictionaries
        """
        if not self.brief_data:
            return []
        return self.brief_data.get("sources", [])

    def get_target_word_count(self) -> int:
        """Get target word count.

        Returns:
            Target word count (default 2000)
        """
        if not self.brief_data:
            return 2000
        return self.brief_data.get("target_word_count", 2000)

    def get_unique_angle(self) -> str | None:
        """Get unique angle for the article.

        Returns:
            Unique angle string or None
        """
        if not self.brief_data:
            return None
        return self.brief_data.get("unique_angle")

    def validate(self) -> tuple[bool, list[str]]:
        """Validate brief completeness.

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []

        if not self.keyword:
            errors.append("Keyword is required")

        if not self.brief_data:
            errors.append("Brief data is required")
            self.is_valid = False
            self.validation_errors = errors
            return False, errors

        sections = self.get_sections()
        if len(sections) < 4:
            errors.append(f"Need at least 4 sections, got {len(sections)}")

        sources = self.get_sources()
        if len(sources) < 5:
            errors.append(f"Need at least 5 sources, got {len(sources)}")

        if not self.get_unique_angle():
            errors.append("Unique angle is required")

        lsi = self.get_lsi_keywords()
        if len(lsi) < 5:
            errors.append(f"Need at least 5 LSI keywords, got {len(lsi)}")

        self.is_valid = len(errors) == 0
        self.validation_errors = errors if errors else None
        return self.is_valid, errors
