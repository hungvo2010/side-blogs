"""Article model for storing blog articles.

The core model for the content automation system, tracking articles
through all stages from draft to publication.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blog_automation.models.base import BaseModel

if TYPE_CHECKING:
    from blog_automation.models.metrics import ArticleMetrics
    from blog_automation.models.review import ArticleReview


class Article(BaseModel):
    """Article model representing a blog post.

    Tracks the article through all stages:
    - draft: Initial AI-generated content
    - fact_checking: Undergoing fact verification
    - fact_checking_issues: Issues found during fact-check
    - editing: Human review stage
    - seo_review: SEO optimization stage
    - approved: Ready for publishing
    - scheduled: Scheduled for future publication
    - published: Live on WordPress
    - rejected: Failed quality gates
    """

    __tablename__ = "articles"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Core fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Content
    content_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_final: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    outline: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI Metadata
    ai_model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_generation_cost: Mapped[float] = mapped_column(Float, default=0.0)
    ai_tokens_used: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        nullable=False,
        index=True,
    )

    # Fact-Checking
    fact_check_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fact_check_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fact_check_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fact_check_issues: Mapped[int] = mapped_column(Integer, default=0)

    # SEO
    seo_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seo_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    meta_title: Mapped[str | None] = mapped_column(String(70), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(170), nullable=True)
    keyword_density: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Quality
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    readability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    plagiarism_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_content_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # E-E-A-T Scores
    eeat_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eeat_expertise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eeat_authoritativeness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eeat_trustworthiness: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # WordPress
    wordpress_post_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    wordpress_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scheduled_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Links
    internal_links: Mapped[list | None] = mapped_column(JSON, nullable=True)
    external_links: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Categories and Tags
    categories: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Featured Image
    featured_image_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    featured_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Performance Tracking (aggregated)
    views_30_days: Mapped[int] = mapped_column(Integer, default=0)
    avg_time_on_page: Mapped[float | None] = mapped_column(Float, nullable=True)
    bounce_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Audit
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    reviews: Mapped[list["ArticleReview"]] = relationship(
        "ArticleReview",
        back_populates="article",
        cascade="all, delete-orphan",
    )
    metrics: Mapped[list["ArticleMetrics"]] = relationship(
        "ArticleMetrics",
        back_populates="article",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_articles_status_created", "status", "created_at"),
        Index("ix_articles_keyword_status", "keyword", "status"),
    )

    def mark_as_approved(self) -> None:
        """Mark article as approved for publishing."""
        self.status = "approved"

    def mark_as_published(
        self, wordpress_post_id: int, wordpress_url: str
    ) -> None:
        """Mark article as published.

        Args:
            wordpress_post_id: WordPress post ID
            wordpress_url: Published URL
        """
        self.status = "published"
        self.wordpress_post_id = wordpress_post_id
        self.wordpress_url = wordpress_url
        self.published_date = datetime.utcnow()

    def mark_as_scheduled(self, scheduled_date: datetime) -> None:
        """Mark article as scheduled for future publication.

        Args:
            scheduled_date: When to publish
        """
        self.status = "scheduled"
        self.scheduled_date = scheduled_date

    def update_word_count(self) -> int:
        """Calculate and update word count from content.

        Returns:
            Word count
        """
        content = self.content_final or self.content_draft or ""
        self.word_count = len(content.split())
        return self.word_count

    def calculate_keyword_density(self) -> float | None:
        """Calculate keyword density in content.

        Returns:
            Keyword density as percentage
        """
        content = self.content_final or self.content_draft or ""
        if not content or not self.keyword:
            return None

        word_count = len(content.split())
        if word_count == 0:
            return None

        keyword_count = content.lower().count(self.keyword.lower())
        self.keyword_density = (keyword_count / word_count) * 100
        return self.keyword_density

    def to_dict(self) -> dict[str, Any]:
        """Convert article to dictionary."""
        data = super().to_dict()
        # Add computed fields
        data["has_fact_check"] = self.fact_check_report is not None
        data["is_published"] = self.status == "published"
        return data
