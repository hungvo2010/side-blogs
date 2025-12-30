"""Unit tests for database models."""

import pytest
from datetime import datetime

from blog_automation.models import (
    Article,
    ArticleMetrics,
    ArticleReview,
    ContentBrief,
    ContentCalendar,
)


class TestArticleModel:
    """Tests for Article model."""

    def test_create_article(self, session):
        """Test creating an article."""
        article = Article(
            title="Test Article",
            slug="test-article",
            keyword="test keyword",
            content_draft="Test content",
            status="draft",
        )
        session.add(article)
        session.commit()

        assert article.id is not None
        assert article.title == "Test Article"
        assert article.status == "draft"

    def test_article_timestamps(self, session):
        """Test article timestamps are set."""
        article = Article(
            title="Test",
            slug="test",
            keyword="test",
        )
        session.add(article)
        session.commit()

        assert article.created_at is not None
        assert article.updated_at is not None

    def test_mark_as_approved(self, sample_article):
        """Test marking article as approved."""
        sample_article.mark_as_approved()
        assert sample_article.status == "approved"

    def test_mark_as_published(self, sample_article):
        """Test marking article as published."""
        sample_article.mark_as_published(123, "https://example.com/post")

        assert sample_article.status == "published"
        assert sample_article.wordpress_post_id == 123
        assert sample_article.wordpress_url == "https://example.com/post"
        assert sample_article.published_date is not None

    def test_mark_as_scheduled(self, sample_article):
        """Test marking article as scheduled."""
        schedule_date = datetime(2024, 12, 31, 8, 0, 0)
        sample_article.mark_as_scheduled(schedule_date)

        assert sample_article.status == "scheduled"
        assert sample_article.scheduled_date == schedule_date

    def test_update_word_count(self, sample_article):
        """Test word count calculation."""
        sample_article.content_draft = "This is a test with exactly ten words here now"
        count = sample_article.update_word_count()

        assert count == 10
        assert sample_article.word_count == 10

    def test_calculate_keyword_density(self, sample_article):
        """Test keyword density calculation."""
        sample_article.keyword = "test"
        sample_article.content_draft = "This is a test. Another test here. Final test."

        density = sample_article.calculate_keyword_density()

        assert density is not None
        assert density > 0
        assert sample_article.keyword_density == density

    def test_article_to_dict(self, sample_article):
        """Test article serialization."""
        data = sample_article.to_dict()

        assert data["title"] == "Test Article"
        assert data["keyword"] == "test keyword"
        assert "has_fact_check" in data
        assert "is_published" in data


class TestContentBriefModel:
    """Tests for ContentBrief model."""

    def test_create_brief(self, session):
        """Test creating a content brief."""
        brief = ContentBrief(
            keyword="test keyword",
            search_volume=1000,
            difficulty=50,
            intent="informational",
        )
        session.add(brief)
        session.commit()

        assert brief.id is not None
        assert brief.keyword == "test keyword"

    def test_get_sections(self, sample_brief):
        """Test getting sections from brief."""
        sections = sample_brief.get_sections()
        assert len(sections) == 4
        assert sections[0]["h2"] == "Section 1"

    def test_get_lsi_keywords(self, sample_brief):
        """Test getting LSI keywords."""
        keywords = sample_brief.get_lsi_keywords()
        assert len(keywords) == 5
        assert "related1" in keywords

    def test_get_sources(self, sample_brief):
        """Test getting sources."""
        sources = sample_brief.get_sources()
        assert len(sources) == 5

    def test_get_target_word_count(self, sample_brief):
        """Test getting target word count."""
        count = sample_brief.get_target_word_count()
        assert count == 2000

    def test_get_unique_angle(self, sample_brief):
        """Test getting unique angle."""
        angle = sample_brief.get_unique_angle()
        assert angle == "A fresh perspective on the topic"

    def test_validate_valid_brief(self, sample_brief):
        """Test validating a valid brief."""
        is_valid, errors = sample_brief.validate()
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_brief(self, session):
        """Test validating an invalid brief."""
        brief = ContentBrief(
            keyword="test",
            brief_data={
                "sections": [{"h2": "Only one"}],
                "sources": [],
            },
        )

        is_valid, errors = brief.validate()
        assert is_valid is False
        assert len(errors) > 0


class TestArticleReviewModel:
    """Tests for ArticleReview model."""

    def test_create_review(self, session, sample_article):
        """Test creating a review."""
        review = ArticleReview(
            article_id=sample_article.id,
            reviewer_id="reviewer1",
            status="pending",
        )
        session.add(review)
        session.commit()

        assert review.id is not None

    def test_start_review(self, session, sample_article):
        """Test starting a review."""
        review = ArticleReview(
            article_id=sample_article.id,
            status="pending",
        )
        session.add(review)
        session.commit()

        review.start_review()

        assert review.status == "in_review"
        assert review.review_start is not None

    def test_complete_review(self, session, sample_article):
        """Test completing a review."""
        review = ArticleReview(
            article_id=sample_article.id,
            status="pending",
        )
        session.add(review)
        session.commit()

        review.start_review()
        review.complete_review(
            verdict="approve",
            feedback="Good article",
            scores={"content_quality": 8, "overall_score": 8},
        )

        assert review.status == "completed"
        assert review.verdict == "approve"
        assert review.feedback == "Good article"
        assert review.content_quality == 8

    def test_add_issue(self, session, sample_article):
        """Test adding an issue to review."""
        review = ArticleReview(
            article_id=sample_article.id,
            status="in_review",
        )
        session.add(review)
        session.commit()

        review.add_issue("factual", "Incorrect date", "paragraph 3", "high")

        assert len(review.issues_found) == 1
        assert review.issues_found[0]["type"] == "factual"

    def test_get_issues_by_severity(self, session, sample_article):
        """Test filtering issues by severity."""
        review = ArticleReview(
            article_id=sample_article.id,
            issues_found=[
                {"type": "factual", "severity": "high"},
                {"type": "grammar", "severity": "low"},
                {"type": "style", "severity": "high"},
            ],
        )

        high_issues = review.get_issues_by_severity("high")
        assert len(high_issues) == 2


class TestContentCalendarModel:
    """Tests for ContentCalendar model."""

    def test_create_calendar_entry(self, session):
        """Test creating a calendar entry."""
        entry = ContentCalendar(
            keyword="test keyword",
            title="Test Article",
            status="planned",
            pub_date=datetime(2024, 12, 31),
        )
        session.add(entry)
        session.commit()

        assert entry.id is not None

    def test_mark_in_progress(self, session):
        """Test marking entry as in progress."""
        entry = ContentCalendar(
            keyword="test",
            status="planned",
        )
        session.add(entry)
        session.commit()

        entry.mark_in_progress()
        assert entry.status == "in_progress"

    def test_is_overdue(self, session):
        """Test overdue detection."""
        past_entry = ContentCalendar(
            keyword="test",
            status="planned",
            pub_date=datetime(2020, 1, 1),
        )

        assert past_entry.is_overdue() is True

        future_entry = ContentCalendar(
            keyword="test",
            status="planned",
            pub_date=datetime(2030, 1, 1),
        )

        assert future_entry.is_overdue() is False


class TestArticleMetricsModel:
    """Tests for ArticleMetrics model."""

    def test_create_metrics(self, session, sample_article):
        """Test creating metrics."""
        from datetime import date

        metrics = ArticleMetrics(
            article_id=sample_article.id,
            date=date.today(),
            views=100,
            clicks=10,
            impressions=1000,
        )
        session.add(metrics)
        session.commit()

        assert metrics.id is not None

    def test_calculate_ctr(self, session, sample_article):
        """Test CTR calculation."""
        from datetime import date

        metrics = ArticleMetrics(
            article_id=sample_article.id,
            date=date.today(),
            clicks=10,
            impressions=100,
        )

        ctr = metrics.calculate_ctr()
        assert ctr == 10.0
        assert metrics.ctr == 10.0
