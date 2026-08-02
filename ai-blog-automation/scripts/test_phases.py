#!/usr/bin/env python3
"""Test each pipeline phase independently with real OpenRouter calls."""
import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ["MOCK_MODE"] = "false"  # force real API calls

from blog_automation.config import get_settings
cfg = get_settings()
print(f"Model: {cfg.openrouter_default_model}")
print(f"Search model: {cfg.openrouter_search_model}")
print(f"Key: {'SET' if cfg.openrouter_api_key.startswith('sk-or') else 'MISSING'}")

from blog_automation.integrations.openrouter_client import OpenRouterClient
client = OpenRouterClient()

# ─── Phase 2: Brief ───
print("\n" + "=" * 60)
print("PHASE 2: Brief — generate content brief")
print("=" * 60)
try:
    brief = client.extract_json(
        prompt="Create a content brief for a blog post about 'best coffee maker 2026'.",
        system_prompt="You are a content strategist. Output JSON with: title, target_audience, outline (list of H2s), word_count_estimate, keywords (list of 5).",
        max_tokens=500,
    )
    print(f"  Title: {brief.get('title', 'N/A')}")
    print(f"  Words: {brief.get('word_count_estimate', 'N/A')}")
    print(f"  Outline: {len(brief.get('outline', []))} sections")
except Exception as e:
    print(f"  ❌ {type(e).__name__}: {str(e)[:150]}")

# ─── Phase 3: Draft ───
print("\n" + "=" * 60)
print("PHASE 3: Draft — generate article")
print("=" * 60)
try:
    draft = client.complete(
        prompt="Write a 2-paragraph intro for a blog post about 'best coffee maker 2026'.",
        system_prompt="You are a blog writer. Write engaging, SEO-friendly content.",
        max_tokens=300,
    )
    content = draft["content"]
    print(f"  Words: {len(content.split())}")
    print(f"  Cost: ${draft['cost']:.4f}")
    print(f"  Preview: {content[:150]}...")
except Exception as e:
    print(f"  ❌ {type(e).__name__}: {str(e)[:150]}")

# ─── Phase 4: Fact Check ───
print("\n" + "=" * 60)
print("PHASE 4: Fact Check — verify claim")
print("=" * 60)
try:
    fact = client.verify_fact("The global coffee maker market was worth $12 billion in 2025.")
    print(f"  Verified: {fact.get('verified', False)}")
    print(f"  Sources: {len(fact.get('sources', []))}")
    print(f"  Answer preview: {fact.get('answer', '')[:150]}...")
except Exception as e:
    print(f"  ❌ {type(e).__name__}: {str(e)[:150]}")

# ─── Phase 5: SEO ───
print("\n" + "=" * 60)
print("PHASE 5: SEO — generate meta")
print("=" * 60)
try:
    seo = client.extract_json(
        prompt="Generate SEO metadata for a blog post titled 'Best Coffee Maker 2026: Top 5 Picks Tested' about coffee maker reviews.",
        system_prompt="Output JSON with: meta_title (max 60 chars), meta_description (max 160 chars), keywords (list of 5).",
        max_tokens=300,
    )
    print(f"  Meta title: {seo.get('meta_title', '')}")
    print(f"  Meta desc: {seo.get('meta_description', '')[:120]}...")
except Exception as e:
    print(f"  ❌ {type(e).__name__}: {str(e)[:150]}")

print(f"\n✅ Total cost: ${client.total_cost:.4f}")
