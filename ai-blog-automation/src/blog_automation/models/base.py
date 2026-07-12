"""Database base model and session management.

Provides SQLAlchemy engine creation, session factory, and base model
class with common fields and methods.
"""

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator

from sqlalchemy import DateTime, create_engine, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from blog_automation.config import get_settings
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)

# Global engine and session factory
_engine = None
_SessionFactory = None


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BaseModel(Base, TimestampMixin):
    """Abstract base model with common fields and methods.

    All models should inherit from this class to get:
    - Auto-incrementing primary key
    - created_at and updated_at timestamps
    - to_dict() serialization method
    - Useful __repr__ method
    """

    __abstract__ = True

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result

    def __repr__(self) -> str:
        """String representation of the model."""
        pk = getattr(self, "id", None)
        return f"<{self.__class__.__name__}(id={pk})>"


def get_engine(database_url: str | None = None):
    """Get or create the database engine.

    Args:
        database_url: Optional database URL override

    Returns:
        SQLAlchemy engine instance
    """
    global _engine

    if _engine is None:
        settings = get_settings()
        url = database_url or settings.database_url

        _engine = create_engine(
            url,
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
        )

    return _engine


def get_session_factory(engine=None) -> sessionmaker:
    """Get or create the session factory.

    Args:
        engine: Optional engine override

    Returns:
        SQLAlchemy sessionmaker instance
    """
    global _SessionFactory

    if _SessionFactory is None:
        eng = engine or get_engine()
        _SessionFactory = sessionmaker(bind=eng, expire_on_commit=False)
        logger.debug("Session factory created")

    return _SessionFactory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Yields:
        SQLAlchemy session

    Example:
        with get_session() as session:
            article = session.query(Article).first()
    """
    factory = get_session_factory()
    session = factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_session() -> Session:
    """Create a new database session.

    Returns:
        SQLAlchemy session (caller must manage lifecycle)
    """
    factory = get_session_factory()
    return factory()


def init_db(engine=None) -> None:
    """Initialize the database by creating all tables.

    Args:
        engine: Optional engine override
    """
    eng = engine or get_engine()
    Base.metadata.create_all(eng)
    logger.info("Database tables created")


def drop_db(engine=None) -> None:
    """Drop all database tables.

    Args:
        engine: Optional engine override
    """
    eng = engine or get_engine()
    Base.metadata.drop_all(eng)
    logger.warning("Database tables dropped")


def clear_all_tables(engine=None) -> dict[str, int]:
    """Delete all rows from every table, keeping table structure intact.

    Deletes child tables first to respect foreign-key constraints. Returns a
    mapping of table name to the number of rows deleted.

    Args:
        engine: Optional engine override

    Returns:
        Dict mapping table name -> deleted row count.
    """
    from sqlalchemy import delete, func, select

    eng = engine or get_engine()
    # Child tables first (depend on articles/briefs), parents last.
    deletion_order = [
        "review_tasks",
        "article_reviews",
        "article_metrics",
        "content_calendar",
        "content_briefs",
        "articles",
    ]
    counts: dict[str, int] = {}
    with eng.begin() as conn:
        for table_name in deletion_order:
            table = Base.metadata.tables.get(table_name)
            if table is None:
                continue
            count = conn.execute(select(func.count()).select_from(table)).scalar() or 0
            if count:
                conn.execute(delete(table))
            counts[table_name] = count
    logger.warning("All table rows cleared", counts=counts)
    return counts


def delete_article_cascade(article_id: int, engine=None) -> bool:
    """Delete a single article and all its dependent rows.

    Removes related review_tasks, article_reviews, article_metrics, and the
    linked content_brief, then the article itself.

    Args:
        article_id: ID of the article to delete
        engine: Optional engine override

    Returns:
        True if the article was found and deleted, False otherwise.
    """
    from sqlalchemy import delete, select

    eng = engine or get_engine()
    with eng.begin() as conn:
        row = conn.execute(
            select(Base.metadata.tables["articles"].c.id).where(
                Base.metadata.tables["articles"].c.id == article_id
            )
        ).first()
        if not row:
            return False

        articles = Base.metadata.tables["articles"]
        reviews = Base.metadata.tables.get("article_reviews")
        metrics = Base.metadata.tables.get("article_metrics")
        briefs = Base.metadata.tables.get("content_briefs")
        review_tasks = Base.metadata.tables.get("review_tasks")

        if review_tasks is not None:
            conn.execute(
                delete(review_tasks).where(review_tasks.c.article_id == article_id)
            )
        if reviews is not None:
            conn.execute(delete(reviews).where(reviews.c.article_id == article_id))
        if metrics is not None:
            conn.execute(delete(metrics).where(metrics.c.article_id == article_id))
        if briefs is not None:
            conn.execute(delete(briefs).where(briefs.c.article_id == article_id))
        conn.execute(delete(articles).where(articles.c.id == article_id))
    logger.info("Article deleted (cascade)", article_id=article_id)
    return True


def reset_engine() -> None:
    """Reset the global engine and session factory.

    Useful for testing or reconfiguration.
    """
    global _engine, _SessionFactory

    if _engine:
        _engine.dispose()
        _engine = None

    _SessionFactory = None
    logger.debug("Database engine reset")
