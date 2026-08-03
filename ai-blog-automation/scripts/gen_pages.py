#!/usr/bin/env python3
"""Generate static pages: about, privacy, terms"""
import sys
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[2] / "public"
SITE = "Tien's Blog"
SITE_URL = "https://side-blogs.pages.dev"

ABOUT = f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>About — {SITE}</title>
<link rel="canonical" href="{SITE_URL}/about">
<style>:root{{--primary:#1a73e8;--text:#1f2937;--bg:#fff}}*{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.7;color:var(--text);background:#f8fafc;margin:0}}
.container{{max-width:800px;margin:40px auto;padding:40px;background:var(--bg);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
h1{{font-size:2rem}}a{{color:var(--primary)}}footer{{text-align:center;padding:32px;color:#6b7280;font-size:.85rem}}
</style></head><body>
<nav style="background:#fff;border-bottom:1px solid #e5e7eb;padding:12px 0">
<div style="max-width:800px;margin:0 auto;padding:0 20px"><a href="/">{SITE}</a></div></nav>
<main class="container">
<h1>About</h1>
<p>Expert reviews, guides, and in-depth articles on coffee, kitchen appliances, and home brewing.</p>
<p>Every article is written based on real testing and research. No AI-generated fluff — just honest, helpful content.</p>
<p>Questions? Reach out via our contact page.</p>
</main>
<footer><p>&copy; 2026 {SITE}. <a href="/">Home</a> · <a href="/about">About</a> · <a href="/privacy">Privacy</a></p></footer>
</body></html>"""

PRIVACY = f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Privacy Policy — {SITE}</title>
<link rel="canonical" href="{SITE_URL}/privacy">
<style>:root{{--primary:#1a73e8;--text:#1f2937;--bg:#fff}}*{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.7;color:var(--text);background:#f8fafc;margin:0}}
.container{{max-width:800px;margin:40px auto;padding:40px;background:var(--bg);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
h1{{font-size:2rem}}a{{color:var(--primary)}}footer{{text-align:center;padding:32px;color:#6b7280;font-size:.85rem}}
</style></head><body>
<nav style="background:#fff;border-bottom:1px solid #e5e7eb;padding:12px 0">
<div style="max-width:800px;margin:0 auto;padding:0 20px"><a href="/">{SITE}</a></div></nav>
<main class="container">
<h1>Privacy Policy</h1>
<p>This site does not collect, store, or share personal data.</p>
<p>We use no cookies, no tracking scripts, and no analytics.</p>
<p>Cloudflare Pages may collect anonymized access logs for security purposes.</p>
</main>
<footer><p>&copy; 2026 {SITE}. <a href="/">Home</a> · <a href="/about">About</a> · <a href="/privacy">Privacy</a></p></footer>
</body></html>"""

PUBLIC.mkdir(parents=True, exist_ok=True)
(PUBLIC / "about").mkdir(exist_ok=True)
(PUBLIC / "privacy").mkdir(exist_ok=True)
(PUBLIC / "about" / "index.html").write_text(ABOUT)
(PUBLIC / "privacy" / "index.html").write_text(PRIVACY)
print("✅ About + Privacy pages generated")
