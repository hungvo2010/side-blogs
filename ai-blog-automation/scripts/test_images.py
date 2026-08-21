#!/usr/bin/env python3
"""Test image providers — try all 3, show results."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blog_automation.integrations.image_provider import (
    PexelsProvider,
    PixabayProvider,
    UnsplashProvider,
)

KW = "coffee"

for p in [UnsplashProvider(), PexelsProvider(), PixabayProvider()]:
    status = "✅ configured" if p.is_configured() else "❌ no key"
    print(f"{p.name}: {status}")
    if p.is_configured():
        try:
            results = p.search(KW, count=3)
            for r in results:
                print(f"  {r.url[:80]}...")
        except Exception as e:
            print(f"  Error: {e}")
    print()
