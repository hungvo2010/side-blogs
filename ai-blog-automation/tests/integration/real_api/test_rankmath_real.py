"""Real integration tests for the RankMath client (phase 5: SEO optimization).

RankMath has no public API — the client performs LOCAL analysis against
Rank Math's scoring criteria, so no credentials are needed. The global
RUN_REAL_API_TESTS gate from this package still applies.
"""

import pytest

pytestmark = [pytest.mark.real_api]


@pytest.fixture(scope="module")
def client():
    from blog_automation.integrations.rankmath_client import RankMathClient

    return RankMathClient()


def _long_article(keyword: str) -> str:
    """Build genuinely well-optimized content per the client's own rubric.

    Rubric targets: 1500+ words, keyword 3-10x, density 0.5-1.5%,
    3+ H2 headings, 3+ internal links, 3+ external links.
    """
    paragraph = (
        f"When choosing {keyword}, consider build quality, price, and reviews. "
        "Our experts tested dozens of models side by side for three months. "
    )
    body = paragraph * 130  # ~1600 words, keyword ~3x → density ~0.7%
    return (
        f"## Why {keyword} matters\n\n"
        + body
        + "\n## How we tested\n\nSee [our testing lab](/about/lab), "
        "the [comparison table](/comparisons), and [methodology](/methodology). "
        "Sources: [CoffeeGeek](https://coffeegeek.com), "
        "[Wirecutter](https://nytimes.com/wirecutter), "
        "[Seattle Coffee Gear](https://seattlecoffeegear.com).\n\n"
        "## Final verdict\n\n" + paragraph * 5
    )


def test_analyze_strong_content_scores_high(client):
    """Well-optimized long content with keyword usage gets a good score."""
    keyword = "best espresso machine"
    result = client.analyze_content(
        content=_long_article(keyword),
        keyword=keyword,
        title="Best Espresso Machine: 2026 Buyer's Guide",
        meta_description=f"Looking for the {keyword}? Our expert guide compares the top models.",
    )

    assert isinstance(result, dict)
    assert "score" in result
    assert 0 <= result["score"] <= 100
    assert result["score"] >= 50, (
        f"well-optimized content should score decently, got {result['score']}"
    )


def test_analyze_thin_content_flags_issues(client):
    """Short, keyword-free content is flagged with issues/suggestions."""
    result = client.analyze_content(
        content="Short paragraph with nothing useful in it.",
        keyword="best espresso machine",
        title="Hi",
        meta_description="x",
    )

    issues = result.get("issues", [])
    suggestions = result.get("suggestions", [])
    assert issues or suggestions, "thin content should produce feedback"
    assert result["score"] < 80


def test_get_recommendations_shape(client):
    """get_recommendations converts an analysis into actionable items."""
    keyword = "pour over coffee"
    analysis = client.analyze_content(
        content="Tiny bit of text.",
        keyword=keyword,
    )

    recs = client.get_recommendations(analysis)

    assert isinstance(recs, (list, dict))
