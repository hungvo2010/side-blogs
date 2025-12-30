"""Article Review model for tracking human editorial reviews."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blog_automation.models.base import BaseModel

if TYPE_CHECKING:
    from blog_automation.models.article import Article


class ArticleReview(BaseModel):
    """Article Review model for human editorial reviews.

    Tracks the review process including:
    - Reviewer assignment
    - Quality scores
    - Feedback and issues
    - Review timing (for Mediavine compliance)
    """

    __tablename__ = "article_reviews"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to article
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id"), nullable=False, index=True
    )

    # Reviewer
    reviewer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Quality Scores (1-10)
    content_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    originality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eeat_compliance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seo_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Verdict
    verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """
    Verdict values:
    - approve: Article passes review
    - revise: Needs changes, return to writer
    - reject: Needs complete rewrite
    """

    # Feedback
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    issues_found: Mapped[list | None] = mapped_column(JSON, nullable=True)
    """
    issues_found structure:
    [
        {
            "type": "factual|grammar|style|seo",
            "description": "...",
            "location": "section/paragraph",
            "severity": "high|medium|low"
        }
    ]
    """

    # Revision requests
    revision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sections_to_revise: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Timing (for Mediavine compliance - 1+ hour minimum)
    review_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending")
    """
    Status values:
    - pending: Awaiting review
    - in_review: Currently being reviewed
    - completed: Review finished
    """

    # Relationship
    article: Mapped["Article"] = relationship("Article", back_populates="reviews")

    def start_review(self) -> None:
        """Mark review as started."""
        self.status = "in_review"
        self.review_start = datetime.utcnow()

    def complete_review(
        self,
        verdict: str,
        feedback: str | None = None,
        scores: dict | None = None,
    ) -> None:
        """Complete the review.

        Args:
            verdict: Review verdict (approve/revise/reject)
            feedback: Optional feedback text
            scores: Optional quality scores dict
        """
        self.status = "completed"
        self.verdict = verdict
        self.feedback = feedback
        self.review_end = datetime.utcnow()

        if scores:
            self.content_quality = scores.get("content_quality")
            self.originality = scores.get("originality")
            self.eeat_compliance = scores.get("eeat_compliance")
            self.seo_quality = scores.get("seo_quality")
            self.overall_score = scores.get("overall_score")

        # Calculate review hours
        if self.review_start and self.review_end:
            delta = self.review_end - self.review_start
            self.review_hours = delta.total_seconds() / 3600

    def meets_mediavine_requirement(self) -> bool:
        """Check if review meets Mediavine's 1+ hour requirement.

        Returns:
            True if review was at least 1 hour
        """
        if self.review_hours is None:
            return False
        return self.review_hours >= 1.0

    def add_issue(
        self,
        issue_type: str,
        description: str,
        location: str | None = None,
        severity: str = "medium",
    ) -> None:
        """Add an issue to the review.

        Args:
            issue_type: Type of issue (factual/grammar/style/seo)
            description: Issue description
            location: Where in the article
            severity: Issue severity (high/medium/low)
        """
        if self.issues_found is None:
            self.issues_found = []

        self.issues_found.append(
            {
                "type": issue_type,
                "description": description,
                "location": location,
                "severity": severity,
            }
        )

    def get_issues_by_severity(self, severity: str) -> list[dict]:
        """Get issues filtered by severity.

        Args:
            severity: Severity level to filter by

        Returns:
            List of issues with matching severity
        """
        if not self.issues_found:
            return []
        return [i for i in self.issues_found if i.get("severity") == severity]
