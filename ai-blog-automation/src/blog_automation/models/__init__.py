"""Database models package."""

from blog_automation.models.article import Article
from blog_automation.models.base import (
    Base,
    BaseModel,
    clear_all_tables,
    delete_article_cascade,
    get_engine,
    get_session,
    get_session_factory,
    init_db,
    reset_engine,
)
from blog_automation.models.brief import ContentBrief
from blog_automation.models.content_calendar import ContentCalendar
from blog_automation.models.metrics import ArticleMetrics
from blog_automation.models.review import ArticleReview
# Import AFTER the models above: task_queue.py imports from blog_automation.models,
# and importing it here registers ReviewTask on Base.metadata so init_db() creates
# the review_tasks table (previously missing — create_all silently skipped it).
from blog_automation.review.task_queue import ReviewTask  # noqa: E402

__all__ = [
    "Base",
    "BaseModel",
    "clear_all_tables",
    "delete_article_cascade",
    "get_engine",
    "get_session",
    "get_session_factory",
    "init_db",
    "reset_engine",
    "Article",
    "ContentBrief",
    "ContentCalendar",
    "ArticleMetrics",
    "ArticleReview",
    "ReviewTask",
]
