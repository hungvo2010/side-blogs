"""Test data factories using factory_boy."""

import factory
from datetime import datetime, timedelta
from factory.alchemy import SQLAlchemyModelFactory

from blog_automation.models import (
    Article,
    ArticleMetrics,
    ArticleReview,
    ContentBrief,
    ContentCalendar,
)


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with session configuration."""

    class Meta:
        abstract = True


class ArticleFactory(BaseFactory):
    """Factory for Article model."""

    class Meta:
        model = Article

    title = factory.Sequence(lambda n: f"Test Article {n}")
    slug = factory.Sequence(lambda n: f"test-article-{n}")
    keyword = factory.Sequence(lambda n: f"test keyword {n}")
    content_draft = factory.Faker("paragraph", nb_sentences=10)
    status = "draft"
    ai_model_used = "gpt-4-turbo"
    ai_generation_cost = factory.Faker("pyfloat", min_value=0.01, max_value=0.50)
    word_count = factory.Faker("pyint", min_value=1500, max_value=3000)


class ContentBriefFactory(BaseFactory):
    """Factory for ContentBrief model."""

    class Meta:
        model = ContentBrief

    keyword = factory.Sequence(lambda n: f"test keyword {n}")
    search_volume = factory.Faker("pyint", min_value=100, max_value=10000)
    difficulty = factory.Faker("pyint", min_value=1, max_value=100)
    intent = factory.Iterator(["informational", "commercial", "transactional"])
    brief_data = factory.LazyFunction(
        lambda: {
            "sections": [
                {"h2": "Introduction", "purpose": "Intro", "key_points": ["a", "b"]},
                {"h2": "Main Content", "purpose": "Main", "key_points": ["c", "d"]},
                {"h2": "Examples", "purpose": "Examples", "key_points": ["e", "f"]},
                {"h2": "Conclusion", "purpose": "Conclusion", "key_points": ["g", "h"]},
            ],
            "lsi_keywords": ["related1", "related2", "related3", "related4", "related5"],
            "sources": [
                {"url": f"https://example.com/{i}", "title": f"Source {i}"}
                for i in range(5)
            ],
            "unique_angle": "A unique perspective",
            "target_word_count": 2000,
        }
    )


class ArticleReviewFactory(BaseFactory):
    """Factory for ArticleReview model."""

    class Meta:
        model = ArticleReview

    article_id = factory.SelfAttribute("article.id")
    reviewer_id = factory.Sequence(lambda n: f"reviewer_{n}")
    status = "pending"
    content_quality = factory.Faker("pyint", min_value=1, max_value=10)
    originality = factory.Faker("pyint", min_value=1, max_value=10)
    overall_score = factory.Faker("pyint", min_value=1, max_value=10)

    class Params:
        article = factory.SubFactory(ArticleFactory)


class ContentCalendarFactory(BaseFactory):
    """Factory for ContentCalendar model."""

    class Meta:
        model = ContentCalendar

    keyword = factory.Sequence(lambda n: f"calendar keyword {n}")
    title = factory.Sequence(lambda n: f"Calendar Article {n}")
    status = "planned"
    pub_date = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(days=7))
    priority = factory.Faker("pyint", min_value=1, max_value=10)


class ArticleMetricsFactory(BaseFactory):
    """Factory for ArticleMetrics model."""

    class Meta:
        model = ArticleMetrics

    article_id = factory.SelfAttribute("article.id")
    date = factory.LazyFunction(lambda: datetime.utcnow().date())
    views = factory.Faker("pyint", min_value=0, max_value=1000)
    clicks = factory.Faker("pyint", min_value=0, max_value=100)
    impressions = factory.Faker("pyint", min_value=0, max_value=10000)
    avg_position = factory.Faker("pyfloat", min_value=1, max_value=100)

    class Params:
        article = factory.SubFactory(ArticleFactory)


def seed_test_database(session, count: int = 5):
    """Seed database with test data.

    Args:
        session: Database session
        count: Number of records to create

    Returns:
        Dict with created objects
    """
    # Configure factories to use session
    ArticleFactory._meta.sqlalchemy_session = session
    ContentBriefFactory._meta.sqlalchemy_session = session
    ArticleReviewFactory._meta.sqlalchemy_session = session
    ContentCalendarFactory._meta.sqlalchemy_session = session
    ArticleMetricsFactory._meta.sqlalchemy_session = session

    articles = []
    briefs = []
    reviews = []
    calendar_entries = []

    for i in range(count):
        # Create article
        article = ArticleFactory()
        articles.append(article)

        # Create brief linked to article
        brief = ContentBriefFactory(article_id=article.id)
        briefs.append(brief)

        # Create review for article
        review = ArticleReviewFactory(article_id=article.id)
        reviews.append(review)

        # Create calendar entry
        entry = ContentCalendarFactory(article_id=article.id)
        calendar_entries.append(entry)

    session.commit()

    return {
        "articles": articles,
        "briefs": briefs,
        "reviews": reviews,
        "calendar_entries": calendar_entries,
    }
