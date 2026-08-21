#!/usr/bin/env python3
"""Backfill Unsplash images into content/*.md frontmatter for posts missing one.

Usage: python scripts/fetch_images.py
Env:   UNSPLASH_ACCESS_KEY (already in .env) or IMAGE_PROVIDER switch
"""

import re
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_SRC))

from blog_automation.integrations.image_provider import get_image_provider  # noqa: E402

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


def load_frontmatter(md_text: str) -> tuple[dict, str]:
    """Return (meta_dict, body) — preserves existing fields."""
    meta: dict[str, str] = {}
    body = md_text
    if md_text.startswith("---"):
        parts = re.split(r"^---\s*$", md_text, maxsplit=2, flags=re.M)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            body = parts[2].strip()
    return meta, body


def save_frontmatter(path: Path, meta: dict, body: str) -> None:
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    provider = get_image_provider()
    if not provider.is_configured():
        print(f"❌ {provider.name} not configured. Check .env")
        sys.exit(1)

    for md_file in sorted(CONTENT_DIR.glob("*.md")):
        meta, body = load_frontmatter(md_file.read_text(encoding="utf-8"))
        if meta.get("image"):
            print(f"⏭️  {md_file.name}: already has image")
            continue

        query = meta.get("title") or md_file.stem.replace("-", " ")
        try:
            results = provider.search(query, count=1)
        except Exception as e:
            print(f"⚠️  {md_file.name}: search failed: {e}")
            continue

        if not results:
            print(f"⚠️  {md_file.name}: no results for '{query}'")
            continue

        img = results[0]
        meta["image"] = img.thumbnail or img.url
        save_frontmatter(md_file, meta, body)
        print(f"✅ {md_file.name}: {query!r} → {meta['image'][:80]}...")


if __name__ == "__main__":
    main()
