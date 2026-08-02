"""Real API integration tests for the OpenRouter LLM gateway.

Covers the single gateway used by every AI pipeline phase:
drafting (phase 3), fact-checking (phase 4), briefs (phase 2),
SEO meta (phase 5), and web-search/evidence retrieval.

Requires: OPENROUTER_API_KEY in .env
Run with: RUN_REAL_API_TESTS=1 pytest tests/integration/real_api/test_openrouter_real.py
"""

import pytest

from . import require_creds, settings

pytestmark = [
    pytest.mark.real_api,
    pytest.mark.openrouter,
    require_creds("openrouter", settings.openrouter_api_key),
]


@pytest.fixture(scope="module")
def client():
    from blog_automation.integrations.openrouter_client import OpenRouterClient

    return OpenRouterClient()


def test_complete_returns_content_and_usage(client):
    """Basic completion returns content plus token/cost accounting."""
    result = client.complete(
        "Reply with exactly the word: pong",
        system_prompt="You are a minimal test bot. Answer tersely.",
        max_tokens=50,
        temperature=0.0,
    )

    assert result["content"].strip(), "expected non-empty completion"
    assert result["model"], "model slug should be recorded"
    assert result["input_tokens"] > 0
    assert result["output_tokens"] > 0
    assert result["total_tokens"] == result["input_tokens"] + result["output_tokens"]
    assert result["cost"] >= 0.0


def test_chat_complete_tracks_cost(client):
    """CostTracker accumulates one entry per request."""
    before = len(client.cost_tracker.requests)

    client.chat_complete(
        [{"role": "user", "content": "Say OK"}],
        max_tokens=10,
        temperature=0.0,
    )

    assert len(client.cost_tracker.requests) == before + 1
    assert client.get_total_cost() > 0


def test_extract_json_parses_structured_output(client):
    """extract_json (used by brief/claim extraction) returns parsed JSON."""
    data = client.extract_json(
        'Return a JSON object: {"claims": ["the sky is blue"], "count": 1}. '
        "Respond with JSON only.",
        max_tokens=100,
        temperature=0.0,
    )

    assert isinstance(data, dict)
    assert "claims" in data
    assert isinstance(data["claims"], list)


def test_search_returns_answer_and_sources(client):
    """Web-search model returns an answer (evidence retrieval for fact-checks)."""
    result = client.search("What is the capital of France?", source_count=3)

    assert result["query"] == "What is the capital of France?"
    assert result["answer"].strip()
    assert "sources" in result
    assert result["source_count"] == len(result["sources"])


def test_verify_fact_assesses_claim(client):
    """verify_fact returns a verdict structure for a well-known fact."""
    result = client.verify_fact("The Earth orbits the Sun.")

    assert isinstance(result, dict)
    # The client returns some verdict-ish structure; assert it carries content
    assert any(k in result for k in ("verdict", "answer", "content", "assessment"))
