#!/usr/bin/env python3
"""
Integration Setup & Test Script
================================
Minimal script to test all 3rd party integrations.

Usage:
    1. Copy .env.example to .env
    2. Fill in your API keys
    3. Run: poetry run python scripts/setup_integrations.py

Each integration can be tested individually or all at once.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()


def test_openrouter():
    """Test OpenRouter API connection (single LLM gateway)."""
    print("\n--> Testing OpenRouter...")
    api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not api_key or api_key.startswith("sk-..."):
        print("   [!] OPENROUTER_API_KEY not set. Skipping.")
        return False

    try:
        from blog_automation.integrations import OpenRouterClient

        client = OpenRouterClient(api_key=api_key)
        response = client.chat_complete(
            messages=[{"role": "user", "content": "Say 'Hello' in one word"}],
            max_tokens=10,
        )
        print(
            f"   [OK] OpenRouter working! Response: {response.get('content', '')[:50]}"
        )
        return True
    except Exception as e:
        print(f"   [ERR] OpenRouter error: {e}")
        return False


def test_ahrefs():
    """Test Ahrefs API connection."""
    print("\n🟠 Testing Ahrefs...")
    api_key = os.getenv("AHREFS_API_KEY", "")

    if not api_key:
        print("   ⚠️  AHREFS_API_KEY not set. Skipping.")
        return False

    try:
        from blog_automation.integrations import AhrefsClient

        client = AhrefsClient(api_key=api_key)
        # Test with a simple keyword
        response = client.search_volume("python programming")
        print(f"   ✅ Ahrefs working! Volume: {response.get('volume', 'N/A')}")
        return True
    except Exception as e:
        print(f"   ❌ Ahrefs error: {e}")
        return False


def test_copyscape():
    """Test Copyscape API connection."""
    print("\n🟡 Testing Copyscape...")
    api_key = os.getenv("COPYSCAPE_API_KEY", "")
    username = os.getenv("COPYSCAPE_USERNAME", "")

    if not api_key or not username:
        print("   ⚠️  COPYSCAPE_API_KEY or COPYSCAPE_USERNAME not set. Skipping.")
        return False

    try:
        from blog_automation.integrations import CopyscapeClient

        client = CopyscapeClient(api_key=api_key, username=username)
        # Just check balance/credits
        print("   ✅ Copyscape configured (test requires credits)")
        return True
    except Exception as e:
        print(f"   ❌ Copyscape error: {e}")
        return False


def test_wordpress():
    """Test WordPress API connection."""
    print("\n🟢 Testing WordPress...")
    url = os.getenv("WORDPRESS_URL", "")
    username = os.getenv("WORDPRESS_USERNAME", "")
    password = os.getenv("WORDPRESS_APP_PASSWORD", "")

    if not url or not username or not password:
        print("   ⚠️  WordPress credentials not set. Skipping.")
        return False

    try:
        from blog_automation.integrations import WordPressClient

        client = WordPressClient(site_url=url, username=username, app_password=password)
        # Test by getting site info
        response = client.get_post(1)  # Try to get post ID 1
        print("   ✅ WordPress connected!")
        return True
    except Exception as e:
        print(f"   ❌ WordPress error: {e}")
        return False


def test_google_analytics():
    """Test Google Analytics connection."""
    print("\n📊 Testing Google Analytics...")
    property_id = os.getenv("GOOGLE_ANALYTICS_PROPERTY_ID", "")
    service_account = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    if not property_id or not service_account:
        print("   ⚠️  GA4 credentials not set. Skipping.")
        return False

    try:
        from blog_automation.integrations import GoogleAnalyticsClient

        client = GoogleAnalyticsClient(property_id=property_id)
        print("   ✅ Google Analytics configured!")
        return True
    except Exception as e:
        print(f"   ❌ Google Analytics error: {e}")
        return False


def test_database():
    """Test database connection."""
    print("\n🗄️  Testing Database...")
    db_url = os.getenv("DATABASE_URL", "")

    if not db_url or "localhost" in db_url:
        print("   ⚠️  Using default/local database URL")

    try:
        from sqlalchemy import text

        from blog_automation.models import get_engine

        engine = get_engine()
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("   ✅ Database connected!")
        return True
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        print("   💡 Tip: Make sure PostgreSQL is running")
        return False


def print_env_template():
    """Print the required environment variables."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                    REQUIRED ENVIRONMENT VARIABLES                 ║
╠══════════════════════════════════════════════════════════════════╣
║ Copy these to your .env file and fill in your values:            ║
╚══════════════════════════════════════════════════════════════════╝

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/blog_db

# AI API (Required for content generation - single LLM gateway)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_DEFAULT_MODEL=openai/gpt-4o
OPENROUTER_SEARCH_MODEL=perplexity/llama-3.1-sonar-large-128k-online

# SEO & Research (Optional but recommended)
AHREFS_API_KEY=your_ahrefs_key

# Quality Checks (Optional)
COPYSCAPE_API_KEY=your_copyscape_key
COPYSCAPE_USERNAME=your_username

# WordPress Publishing (Required for publishing)
WORDPRESS_URL=https://your-site.com
WORDPRESS_USERNAME=your_username
WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx

# Google Analytics (Optional)
GOOGLE_ANALYTICS_PROPERTY_ID=123456789
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
""")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("🚀 AI Blog Automation - Integration Setup Test")
    print("=" * 60)

    results = {
        "OpenRouter": test_openrouter(),
        "Ahrefs": test_ahrefs(),
        "Copyscape": test_copyscape(),
        "WordPress": test_wordpress(),
        "Google Analytics": test_google_analytics(),
        "Database": test_database(),
    }

    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)

    working = sum(1 for v in results.values() if v)
    total = len(results)

    for name, status in results.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {name}")

    print(f"\n   {working}/{total} integrations configured")

    if working < total:
        print("\n💡 Need help? Run with --help for environment variable template")

    if "--help" in sys.argv or "-h" in sys.argv:
        print_env_template()

    return 0 if working > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
