"""Pytest configuration and fixtures."""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LOG_LEVEL"] = "WARNING"


@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    from blog_automation.models.base import Base

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def session(engine):
    """Create test database session."""
    from blog_automation.models.base import Base
    
    # Create fresh tables for each test
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def db_session(session):
    """Alias for session fixture."""
    return session


@pytest.fixture
def sample_article(session):
    """Create a sample article for testing."""
    from blog_automation.models import Article

    article = Article(
        title="Test Article",
        slug="test-article-20240101",
        keyword="test keyword",
        content_draft="This is test content for the article.",
        status="draft",
    )
    session.add(article)
    session.commit()
    return article


@pytest.fixture
def sample_brief(session):
    """Create a sample content brief for testing."""
    from blog_automation.models import ContentBrief

    brief = ContentBrief(
        keyword="test keyword",
        search_volume=1000,
        difficulty=50,
        intent="informational",
        brief_data={
            "sections": [
                {"h2": "Section 1", "purpose": "Introduction", "key_points": ["a", "b"]},
                {"h2": "Section 2", "purpose": "Main content", "key_points": ["c", "d"]},
                {"h2": "Section 3", "purpose": "Examples", "key_points": ["e", "f"]},
                {"h2": "Section 4", "purpose": "Conclusion", "key_points": ["g", "h"]},
            ],
            "lsi_keywords": ["related1", "related2", "related3", "related4", "related5"],
            "sources": [
                {"url": "https://example.com/1", "title": "Source 1"},
                {"url": "https://example.com/2", "title": "Source 2"},
                {"url": "https://example.com/3", "title": "Source 3"},
                {"url": "https://example.com/4", "title": "Source 4"},
                {"url": "https://example.com/5", "title": "Source 5"},
            ],
            "unique_angle": "A fresh perspective on the topic",
            "target_word_count": 2000,
        },
    )
    session.add(brief)
    session.commit()
    return brief


@pytest.fixture
def mock_openai(mocker):
    """Mock OpenAI API responses."""
    mock_response = {
        "content": "Generated content from OpenAI",
        "model": "gpt-4-turbo-preview",
        "input_tokens": 100,
        "output_tokens": 500,
        "total_tokens": 600,
        "cost": 0.02,
    }

    mocker.patch(
        "blog_automation.integrations.openai_client.OpenAIClient.chat_complete",
        return_value=mock_response,
    )
    mocker.patch(
        "blog_automation.integrations.openai_client.OpenAIClient.complete",
        return_value=mock_response,
    )

    return mock_response


@pytest.fixture
def mock_claude(mocker):
    """Mock Claude API responses."""
    mock_response = {
        "content": "Generated content from Claude",
        "model": "claude-3-sonnet-20240229",
        "input_tokens": 100,
        "output_tokens": 500,
        "cost": 0.01,
    }

    mocker.patch(
        "blog_automation.integrations.claude_client.ClaudeClient.message",
        return_value=mock_response,
    )
    mocker.patch(
        "blog_automation.integrations.claude_client.ClaudeClient.extract_json",
        return_value={"claims": [], "sections": []},
    )

    return mock_response


@pytest.fixture
def mock_ahrefs(mocker):
    """Mock Ahrefs API responses."""
    mocker.patch(
        "blog_automation.integrations.ahrefs_client.AhrefsClient.search_volume",
        return_value={"keyword": "test", "volume": 1000, "cpc": 1.5},
    )
    mocker.patch(
        "blog_automation.integrations.ahrefs_client.AhrefsClient.keyword_difficulty",
        return_value={"keyword": "test", "difficulty": 50},
    )
    mocker.patch(
        "blog_automation.integrations.ahrefs_client.AhrefsClient.serp_features",
        return_value={"featured_snippet": False, "people_also_ask": []},
    )
    mocker.patch(
        "blog_automation.integrations.ahrefs_client.AhrefsClient.top_pages",
        return_value=[],
    )


@pytest.fixture
def mock_perplexity(mocker):
    """Mock Perplexity API responses."""
    mocker.patch(
        "blog_automation.integrations.perplexity_client.PerplexityClient.search",
        return_value={
            "query": "test",
            "answer": "Test answer",
            "sources": [{"url": "https://example.com", "title": "Example"}],
        },
    )


@pytest.fixture
def mock_wordpress(mocker):
    """Mock WordPress API responses."""
    mocker.patch(
        "blog_automation.integrations.wordpress_client.WordPressClient.create_post",
        return_value={"id": 123, "link": "https://example.com/post", "status": "draft"},
    )
    mocker.patch(
        "blog_automation.integrations.wordpress_client.WordPressClient.update_post",
        return_value={"id": 123, "status": "publish"},
    )
    mocker.patch(
        "blog_automation.integrations.wordpress_client.WordPressClient.upload_media",
        return_value={"id": 456, "url": "https://example.com/image.jpg"},
    )
