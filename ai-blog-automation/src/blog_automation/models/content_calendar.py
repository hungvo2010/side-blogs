"""Content Calendar model for scheduling and tracking content production."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from blog_automation.models.base import BaseModel


class ContentCalendar(BaseModel):
    """Content Calendar model for planning and tracking articles.

    Tracks the content production schedule including:
    - Planned publication dates
    - Assigned writers and reviewers
    - Production status
    """

    __tablename__ = "content_calendar"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Scheduling
    week_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pub_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Content
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="planned",
        nullable=False,
        index=True,
    )
    """
    Status values:
    - planned: Scheduled for future
    - in_progress: Currently being worked on
    - submitted: Submitted for review
    - published: Live on site
    - cancelled: Cancelled/removed from schedule
    """

    # Assignment
    assigned_writer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assigned_reviewer: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Priority
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10, 1 is highest

    # Link to article
    article_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("articles.id"), nullable=True
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def mark_in_progress(self) -> None:
        """Mark calendar entry as in progress."""
        self.status = "in_progress"

    def mark_submitted(self) -> None:
        """Mark calendar entry as submitted for review."""
        self.status = "submitted"

    def mark_published(self, article_id: int) -> None:
        """Mark calendar entry as published.

        Args:
            article_id: ID of the published article
        """
        self.status = "published"
        self.article_id = article_id

    def is_overdue(self) -> bool:
        """Check if the entry is overdue.

        Returns:
            True if past publication date and not published
        """
        if not self.pub_date:
            return False
        if self.status == "published":
            return False
        return datetime.utcnow() > self.pub_date

    @classmethod
    def get_next_planned(cls, session) -> "ContentCalendar | None":
        """Get the next planned content item.

        Args:
            session: Database session

        Returns:
            Next planned ContentCalendar entry or None
        """
        return (
            session.query(cls)
            .filter(cls.status == "planned")
            .order_by(cls.priority.asc(), cls.pub_date.asc())
            .first()
        )
