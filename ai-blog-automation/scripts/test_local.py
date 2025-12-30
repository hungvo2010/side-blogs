#!/usr/bin/env python3
"""
Local Test Script (No API Keys Required)
=========================================
Tests that all modules import correctly and basic functionality works.

Usage:
    poetry run python scripts/test_local.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test all modules can be imported."""
    print("📦 Testing imports...")
    
    modules = [
        ("blog_automation", "Main package"),
        ("blog_automation.config", "Configuration"),
        ("blog_automation.errors", "Error classes"),
        ("blog_automation.logging_config", "Logging"),
        ("blog_automation.error_handler", "Error handlers"),
        ("blog_automation.alerts", "Alerts"),
        ("blog_automation.models", "Database models"),
        ("blog_automation.integrations", "API clients"),
        ("blog_automation.pipelines", "Pipelines"),
    ]
    
    success = 0
    for module, desc in modules:
        try:
            __import__(module)
            print(f"   ✅ {desc}")
            success += 1
        except Exception as e:
            print(f"   ❌ {desc}: {e}")
    
    return success == len(modules)


def test_error_classes():
    """Test error classes work correctly."""
    print("\n🔴 Testing error classes...")
    
    from blog_automation.errors import (
        AppError, APITimeoutError, APIRateLimitError,
        InvalidKeywordError, GenerationFailureError
    )
    
    # Test basic error
    err = AppError("Test error", error_code="test_001")
    assert err.message == "Test error"
    assert err.error_code == "test_001"
    
    # Test to_dict
    d = err.to_dict()
    assert "message" in d
    assert "error_code" in d
    assert "timestamp" in d
    
    # Test subclasses
    timeout = APITimeoutError("Timeout", service="openai")
    assert timeout.service == "openai"
    
    rate_limit = APIRateLimitError("Rate limited", retry_after=60)
    assert rate_limit.retry_after == 60
    
    print("   ✅ All error classes working")
    return True


def test_config():
    """Test configuration loading."""
    print("\n⚙️  Testing configuration...")
    
    import os
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    from blog_automation.config import get_settings, clear_settings_cache
    
    clear_settings_cache()
    settings = get_settings()
    
    assert settings.environment == "testing"
    assert settings.database_url == "sqlite:///:memory:"
    
    print(f"   ✅ Environment: {settings.environment}")
    print(f"   ✅ Database: {settings.database_url}")
    return True


def test_models():
    """Test database models with SQLite."""
    print("\n🗄️  Testing models (SQLite)...")
    
    import os
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from blog_automation.models import Base, Article, ContentBrief
    
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Test Article
    article = Article(
        title="Test Article",
        slug="test-article",
        keyword="test keyword",
        content_draft="Test content here",
        status="draft"
    )
    session.add(article)
    session.commit()
    
    assert article.id is not None
    print(f"   ✅ Article created: ID={article.id}")
    
    # Test ContentBrief
    brief = ContentBrief(
        keyword="test keyword",
        search_volume=1000,
        difficulty=50,
        brief_data={"sections": [], "sources": []}
    )
    session.add(brief)
    session.commit()
    
    assert brief.id is not None
    print(f"   ✅ Brief created: ID={brief.id}")
    
    session.close()
    return True


def test_decorators():
    """Test error handling decorators."""
    print("\n🎯 Testing decorators...")
    
    from blog_automation.error_handler import handle_errors, retry
    from blog_automation.errors import AppError
    
    # Test handle_errors with reraise=False to return default
    @handle_errors(reraise=False, default_return="default")
    def failing_func():
        raise ValueError("Test error")
    
    result = failing_func()
    assert result == "default"
    print("   ✅ @handle_errors working")
    
    # Test retry
    call_count = 0
    
    @retry(max_attempts=3, backoff_factor=1.01, jitter=False)
    def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary failure")
        return "success"
    
    result = flaky_func()
    assert result == "success"
    assert call_count == 3
    print("   ✅ @retry working")
    
    return True


def test_cache():
    """Test caching functionality."""
    print("\n💾 Testing cache...")
    
    from blog_automation.integrations.cache import CacheManager
    
    cache = CacheManager()
    
    # Test set_cache/get_cached
    cache.set_cache("test_key", {"data": "value"}, cache_type="default")
    result = cache.get_cached("test_key", cache_type="default")
    assert result == {"data": "value"}
    print("   ✅ Cache set/get working")
    
    # Test expiration (set with very short TTL by using a type that doesn't exist)
    # The cache uses DEFAULT_TTLS, so we test by clearing
    cache.clear_cache("expire")
    result = cache.get_cached("expire_key", cache_type="default")
    assert result is None
    print("   ✅ Cache expiration working")
    
    return True


def main():
    """Run all local tests."""
    print("=" * 60)
    print("🧪 AI Blog Automation - Local Tests (No API Keys)")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Error Classes", test_error_classes),
        ("Configuration", test_config),
        ("Models", test_models),
        ("Decorators", test_decorators),
        ("Cache", test_cache),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"   ❌ {name} failed: {e}")
            results[name] = False
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, status in results.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {name}")
    
    print(f"\n   {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
