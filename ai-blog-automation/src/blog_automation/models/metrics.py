"""Article Metrics model for tracking daily performance."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from blog_automation.models.base import BaseModel

if TYPE_CHECKING:
    from blog_automation.models.article import Article


class ArticleMetrics(BaseModel):
    """Article Metrics model for daily performance tracking.

    Stores daily metrics from Google Analytics and Search Console:
    - Page views and engagement
    - Search impressions and clicks
    - Ranking positions
    """

    __tablename__ = "article_metrics"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to article
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id"), nullable=False, index=True
    )

    # Date for this metrics record
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Google Analytics metrics
    views: Mapped[int] = mapped_column(Integer, default=0)
    unique_visitors: Mapped[int] = mapped_column(Integer, default=0)
    avg_time_on_page: Mapped[float | None] = mapped_column(Float, nullable=True)
    bounce_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    scroll_depth: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Google Search Console metrics
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Top queries for this day
    top_queries: Mapped[list | None] = mapped_column(JSON, default=None)

    # Revenue (if applicable)
    ad_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    affiliate_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationship
    article: Mapped["Article"] = relationship("Article", back_populates="metrics")

    # Indexes
    __table_args__ = (
        Index("ix_metrics_article_date", "article_id", "date", unique=True),
    )

    def calculate_ctr(self) -> float | None:
        """Calculate click-through rate.

        Returns:
            CTR as percentage or None if no impressions
        """
        if self.impressions == 0:
            return None
        self.ctr = (self.clicks / self.impressions) * 100
        return self.ctr

    @classmethod
    def get_for_period(
        cls,
        session,
        article_id: int,
        start_date: date,
        end_date: date,
    ) -> list["ArticleMetrics"]:
        """Get metrics for an article over a date range.

        Args:
            session: Database session
            article_id: Article ID
            start_date: Start of period
            end_date: End of period

        Returns:
            List of ArticleMetrics records
        """
        return (
            session.query(cls)
            .filter(
                cls.article_id == article_id,
                cls.date >= start_date,
                cls.date <= end_date,
            )
            .order_by(cls.date.asc())
            .all()
        )

    @classmethod
    def get_totals_for_period(
        cls,
        session,
        article_id: int,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Get aggregated metrics for a period.

        Args:
            session: Database session
            article_id: Article ID
            start_date: Start of period
            end_date: End of period

        Returns:
            Dictionary with aggregated metrics
        """
        from sqlalchemy import func

        result = (
            session.query(
                func.sum(cls.views).label("total_views"),
                func.sum(cls.clicks).label("total_clicks"),
                func.sum(cls.impressions).label("total_impressions"),
                func.avg(cls.avg_position).label("avg_position"),
                func.avg(cls.bounce_rate).label("avg_bounce_rate"),
            )
            .filter(
                cls.article_id == article_id,
                cls.date >= start_date,
                cls.date <= end_date,
            )
            .first()
        )

        return {
            "total_views": result.total_views or 0,
            "total_clicks": result.total_clicks or 0,
            "total_impressions": result.total_impressions or 0,
            "avg_position": result.avg_position,
            "avg_bounce_rate": result.avg_bounce_rate,
        }

    @classmethod
    def upsert(
        cls,
        session,
        article_id: int,
        metrics_date: date,
        **metrics,
    ) -> "ArticleMetrics":
        """Insert or update metrics for a date.

        Args:
            session: Database session
            article_id: Article ID
            metrics_date: Date for metrics
            **metrics: Metric values to set

        Returns:
            ArticleMetrics instance
        """
        existing = (
            session.query(cls)
            .filter(cls.article_id == article_id, cls.date == metrics_date)
            .first()
        )

        if existing:
            for key, value in metrics.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            return existing

        new_metrics = cls(article_id=article_id, date=metrics_date, **metrics)
        session.add(new_metrics)
        return new_metrics
