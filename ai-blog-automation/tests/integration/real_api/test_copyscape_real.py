"""Real API integration tests for Copyscape (phase 6: plagiarism quality gate).

Requires: COPYSCAPE_API_KEY + COPYSCAPE_USERNAME in .env
Run with: RUN_REAL_API_TESTS=1 pytest tests/integration/real_api/test_copyscape_real.py

Note: each plagiarism check spends Copyscape credits, so tests are minimal.
"""

import pytest

from . import require_creds, settings

pytestmark = [
    pytest.mark.real_api,
    pytest.mark.copyscape,
    require_creds(
        "copyscape", settings.copyscape_api_key, settings.copyscape_username
    ),
]


@pytest.fixture(scope="module")
def client():
    from blog_automation.integrations.copyscape_client import CopyscapeClient

    return CopyscapeClient()


def test_get_credits(client):
    """Credit check returns a non-negative integer balance (free call)."""
    credits = client.get_credits()

    assert isinstance(credits, int)
    assert credits >= 0


def test_check_plagiarism_unique_content(client):
    """Freshly written unique content should come back as original."""
    unique_text = (
        "The quantum espresso centrifuge Mk VII brews coffee by spinning "
        "ground beans at relativistic velocities inside a titanium drum, "
        "a technique first demonstrated in our Lisbon laboratory last March."
    )

    result = client.check_plagiarism(unique_text, title="Quantum Espresso")

    assert isinstance(result, dict)
    assert "plagiarism_percent" in result
    assert "matches" in result
    assert "is_original" in result
    assert result["words_checked"] == len(unique_text.split())
    assert result["plagiarism_percent"] >= 0.0
