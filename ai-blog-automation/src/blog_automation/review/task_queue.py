"""Review task queue management.

Handles creation, assignment, and tracking of human review tasks.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from blog_automation.alerts import send_notification
from blog_automation.logging_config import get_logger
from blog_automation.models import Article, ArticleReview, get_session
from blog_automation.models.base import BaseModel

logger = get_logger(__name__)


class ReviewTask(BaseModel):
    """Review task model for tracking human review assignments."""

    __tablename__ = "review_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id"), nullable=False, index=True
    )
    assigned_reviewer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


def create_review_task(
    article: Article,
    reviewer: str | None = None,
    deadline_hours: int = 24,
) -> ReviewTask:
    """Create a review task for an article.

    Args:
        article: Article to review
        reviewer: Optional assigned reviewer
        deadline_hours: Hours until deadline

    Returns:
        Created ReviewTask
    """
    logger.info("Creating review task", article_id=article.id)

    with get_session() as session:
        # Check if task already exists
        existing = (
            session.query(ReviewTask)
            .filter(
                ReviewTask.article_id == article.id,
                ReviewTask.status.in_(["pending", "in_review"]),
            )
            .first()
        )

        if existing:
            logger.info("Review task already exists", task_id=existing.id)
            return existing

        # Create task
        task = ReviewTask(
            article_id=article.id,
            assigned_reviewer=reviewer,
            status="pending",
            deadline=datetime.utcnow() + timedelta(hours=deadline_hours),
        )

        if reviewer:
            task.assigned_at = datetime.utcnow()

        session.add(task)

        # Create ArticleReview record
        review = ArticleReview(
            article_id=article.id,
            reviewer_id=reviewer,
            status="pending",
        )
        session.add(review)

        # Update article status
        article_obj = session.query(Article).get(article.id)
        if article_obj:
            article_obj.status = "pending_review"

        session.commit()

        logger.info(
            "Review task created",
            task_id=task.id,
            article_id=article.id,
            reviewer=reviewer,
        )

        # Send notification
        _send_review_notification(task, article)

        return task


def get_pending_tasks() -> list[dict[str, Any]]:
    """Get all pending review tasks.

    Returns:
        List of pending task data
    """
    with get_session() as session:
        tasks = (
            session.query(ReviewTask)
            .filter(ReviewTask.status == "pending")
            .order_by(ReviewTask.deadline.asc())
            .all()
        )

        result = []
        for task in tasks:
            article = session.query(Article).get(task.article_id)
            result.append(
                {
                    "task_id": task.id,
                    "article_id": task.article_id,
                    "title": article.title if article else "Unknown",
                    "keyword": article.keyword if article else "Unknown",
                    "status": task.status,
                    "deadline": task.deadline.isoformat() if task.deadline else None,
                    "assigned_reviewer": task.assigned_reviewer,
                    "is_overdue": task.deadline and datetime.utcnow() > task.deadline,
                }
            )

        return result


def get_reviewer_tasks(reviewer_id: str) -> list[dict[str, Any]]:
    """Get tasks assigned to a specific reviewer.

    Args:
        reviewer_id: Reviewer identifier

    Returns:
        List of assigned task data
    """
    with get_session() as session:
        tasks = (
            session.query(ReviewTask)
            .filter(
                ReviewTask.assigned_reviewer == reviewer_id,
                ReviewTask.status.in_(["pending", "in_review"]),
            )
            .order_by(ReviewTask.deadline.asc())
            .all()
        )

        result = []
        for task in tasks:
            article = session.query(Article).get(task.article_id)
            result.append(
                {
                    "task_id": task.id,
                    "article_id": task.article_id,
                    "title": article.title if article else "Unknown",
                    "keyword": article.keyword if article else "Unknown",
                    "status": task.status,
                    "deadline": task.deadline.isoformat() if task.deadline else None,
                    "is_overdue": task.deadline and datetime.utcnow() > task.deadline,
                }
            )

        return result


def assign_task(task_id: int, reviewer_id: str) -> bool:
    """Assign a task to a reviewer.

    Args:
        task_id: Task ID
        reviewer_id: Reviewer to assign

    Returns:
        True if successful
    """
    with get_session() as session:
        task = session.query(ReviewTask).get(task_id)
        if not task:
            return False

        task.assigned_reviewer = reviewer_id
        task.assigned_at = datetime.utcnow()
        session.commit()

        logger.info(
            "Task assigned",
            task_id=task_id,
            reviewer=reviewer_id,
        )

        return True


def update_task_status(
    task_id: int,
    new_status: str,
    feedback: str | None = None,
) -> bool:
    """Update task status.

    Args:
        task_id: Task ID
        new_status: New status
        feedback: Optional feedback

    Returns:
        True if successful
    """
    with get_session() as session:
        task = session.query(ReviewTask).get(task_id)
        if not task:
            return False

        task.status = new_status

        if new_status == "completed":
            task.completed_at = datetime.utcnow()

        if feedback:
            task.notes = feedback

        # Update associated review
        review = (
            session.query(ArticleReview)
            .filter(ArticleReview.article_id == task.article_id)
            .order_by(ArticleReview.created_at.desc())
            .first()
        )

        if review:
            if new_status == "in_review":
                review.start_review()
            elif new_status == "completed":
                review.status = "completed"

        session.commit()

        logger.info(
            "Task status updated",
            task_id=task_id,
            status=new_status,
        )

        return True


def complete_review(
    task_id: int,
    verdict: str,
    feedback: str | None = None,
    scores: dict | None = None,
) -> dict[str, Any]:
    """Complete a review task.

    Args:
        task_id: Task ID
        verdict: Review verdict (approve/revise/reject)
        feedback: Optional feedback
        scores: Optional quality scores

    Returns:
        Result dict with next steps
    """
    with get_session() as session:
        task = session.query(ReviewTask).get(task_id)
        if not task:
            return {"success": False, "error": "Task not found"}

        # Update task
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.notes = feedback

        # Update review
        review = (
            session.query(ArticleReview)
            .filter(ArticleReview.article_id == task.article_id)
            .order_by(ArticleReview.created_at.desc())
            .first()
        )

        if review:
            review.complete_review(verdict, feedback, scores)

        # Update article status based on verdict
        article = session.query(Article).get(task.article_id)
        if article:
            if verdict == "approve":
                article.status = "approved"
                next_step = "publish"
            elif verdict == "revise":
                article.status = "revision_requested"
                next_step = "revise"
            else:  # reject
                article.status = "rejected"
                next_step = "rewrite"

        session.commit()

        logger.info(
            "Review completed",
            task_id=task_id,
            verdict=verdict,
            article_id=task.article_id,
        )

        return {
            "success": True,
            "verdict": verdict,
            "next_step": next_step,
            "article_id": task.article_id,
        }


def get_review_stats() -> dict[str, Any]:
    """Get review queue statistics.

    Returns:
        Statistics dict
    """
    with get_session() as session:
        pending = (
            session.query(ReviewTask).filter(ReviewTask.status == "pending").count()
        )
        in_review = (
            session.query(ReviewTask).filter(ReviewTask.status == "in_review").count()
        )
        completed_today = (
            session.query(ReviewTask)
            .filter(
                ReviewTask.status == "completed",
                ReviewTask.completed_at
                >= datetime.utcnow().replace(hour=0, minute=0, second=0),
            )
            .count()
        )

        overdue = (
            session.query(ReviewTask)
            .filter(
                ReviewTask.status.in_(["pending", "in_review"]),
                ReviewTask.deadline < datetime.utcnow(),
            )
            .count()
        )

        return {
            "pending": pending,
            "in_review": in_review,
            "completed_today": completed_today,
            "overdue": overdue,
        }


def _send_review_notification(task: ReviewTask, article: Article) -> None:
    """Send notification for new review task.

    Args:
        task: Review task
        article: Article to review
    """
    title = f"New Review Task: {article.title}"
    message = (
        f"Article '{article.title}' is ready for review.\n"
        f"Keyword: {article.keyword}\n"
        f"Deadline: {task.deadline.strftime('%Y-%m-%d %H:%M') if task.deadline else 'None'}"
    )

    send_notification(title, message)
