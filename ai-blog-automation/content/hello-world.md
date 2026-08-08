---
title: Hello World from Cloudflare Pages
description: My first blog post published via GitHub + Cloudflare Pages, zero database required.
tags: cloudflare, static-site, tutorial
image: https://images.unsplash.com/photo-1498050108023-c5249f4df085?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3MTEwNzF8MHwxfHNlYXJjaHwxfHxsYXB0b3AlMjBjb2RpbmcsJTIwaGVybyUyMHdvcmxkfGVufDB8fHx8MTc4NTc4NTkyNXww&ixlib=rb-4.1.0&q=80&w=200
---

## Welcome to my blog

This is a **static blog** powered by Cloudflare Pages. Every time I write
a markdown file and run `publish.py`, it:

1. Converts markdown to clean HTML with full SEO metadata
2. Generates Open Graph tags for social sharing
3. Adds Schema.org `Article` JSON-LD for Google rich results
4. Builds `sitemap.xml` and `rss.xml`
5. Regenerates the index page
6. Pushes everything to GitHub
7. Cloudflare Pages auto-deploys in ~30 seconds

### Why Cloudflare Pages?

| Feature | WordPress | Cloudflare Pages |
|---|---|---|
| Speed | Depends on hosting + cache | Edge network, instant |
| Cost | $5-30/mo hosting | Free |
| Security | Plugin vulnerabilities | Static = no attack surface |
| SEO | Plugin-dependent | Built into the template |
| Maintenance | Updates, backups, DB | None |

### Code Example

```python
def publish(markdown_file: str) -> str:
    """One command to publish a post."""
    return "https://myblog.pages.dev/" + slugify(markdown_file)
```

That's it! No database, no WordPress, no 8-phase pipeline.
Just write markdown and ship.

---

*Want to try? Run `python scripts/publish.py content/hello-world.md`*
