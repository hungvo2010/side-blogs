"""Real API integration tests for the WordPress client (phase 8: publishing).

Requires: WORDPRESS_URL + WORDPRESS_USERNAME + WORDPRESS_APP_PASSWORD in .env
Run with: RUN_REAL_API_TESTS=1 pytest tests/integration/real_api/test_wordpress_real.py

Note: the post CRUD test creates a real DRAFT post on the site and deletes
it afterwards. No content is ever published.
"""

import pytest

from . import require_creds, settings

pytestmark = [
    pytest.mark.real_api,
    pytest.mark.wordpress,
    require_creds(
        "wordpress",
        settings.wordpress_url,
        settings.wordpress_username,
        settings.wordpress_app_password,
    ),
]


@pytest.fixture(scope="module")
def client():
    from blog_automation.integrations.wordpress_client import WordPressClient

    return WordPressClient()


def test_connection(client):
    """Auth against /wp-json/wp/v2/users/me succeeds."""
    assert client.test_connection() is True


def test_get_categories(client):
    """Category listing works (used when assigning posts)."""
    categories = client.get_categories()

    assert isinstance(categories, list)


def test_post_lifecycle_create_update_delete(client):
    """Create draft -> read -> update -> delete round-trip."""
    created = client.create_post(
        title="Real API Integration Test — delete me",
        content="<p>Automated integration test content. Safe to delete.</p>",
        status="draft",
    )
    post_id = created["id"]
    assert post_id

    try:
        # Read back
        fetched = client.get_post(post_id)
        assert fetched["id"] == post_id
        assert fetched["status"] == "draft"
        assert "Real API Integration Test" in fetched["title"]["rendered"]

        # Update
        updated = client.update_post(post_id, excerpt="updated excerpt")
        assert updated["id"] == post_id
    finally:
        # Cleanup — permanent delete so we don't litter the trash either
        assert client.delete_post(post_id, force=True) is True
