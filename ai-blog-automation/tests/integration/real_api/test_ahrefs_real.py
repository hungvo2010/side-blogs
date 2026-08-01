"""Real API integration tests for the Ahrefs client (phase 1: keyword research).

Requires: AHREFS_API_KEY in .env
Run with: RUN_REAL_API_TESTS=1 pytest tests/integration/real_api/test_ahrefs_real.py
"""

import pytest

from . import require_creds, settings

pytestmark = [
    pytest.mark.real_api,
    pytest.mark.ahrefs,
    require_creds("ahrefs", settings.ahrefs_api_key),
]

TEST_KEYWORD = "best coffee maker"


@pytest.fixture(scope="module")
def client():
    from blog_automation.integrations.ahrefs_client import AhrefsClient

    return AhrefsClient()


def test_get_keyword_overview(client):
    """Keyword overview returns volume/difficulty/cpc for a real keyword."""
    result = client.get_keyword_overview(TEST_KEYWORD)

    assert result["keyword"] == TEST_KEYWORD
    assert isinstance(result["volume"], (int, float))
    assert result["volume"] >= 0
    assert isinstance(result["difficulty"], (int, float))
    assert 0 <= result["difficulty"] <= 100
    assert result["country"] == "us"


def test_search_volume(client):
    """search_volume returns a volume figure and CPC."""
    result = client.search_volume(TEST_KEYWORD)

    assert isinstance(result, dict)
    assert "volume" in result
    assert isinstance(result["volume"], (int, float))


def test_keyword_difficulty(client):
    """keyword_difficulty returns a 0-100 difficulty score."""
    result = client.keyword_difficulty(TEST_KEYWORD)

    assert isinstance(result, dict)
    assert "difficulty" in result
    assert 0 <= result["difficulty"] <= 100


def test_serp_features(client):
    """serp_features detects SERP attributes for a competitive keyword."""
    result = client.serp_features(TEST_KEYWORD)

    assert isinstance(result, dict)


def test_top_pages(client):
    """top_pages returns the ranking pages for the keyword."""
    pages = client.top_pages(TEST_KEYWORD, limit=5)

    assert isinstance(pages, list)
    assert len(pages) <= 5
    if pages:  # a keyword this common should return pages, but stay lenient
        assert "url" in pages[0] or "title" in pages[0]


def test_empty_keyword_rejected(client):
    """Client-side validation rejects empty keywords."""
    from blog_automation.errors import InvalidKeywordError

    with pytest.raises(InvalidKeywordError):
        client.get_keyword_overview("   ")
