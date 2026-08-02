# pytrends — Free Keyword Research

Google Trends via pytrends. No API key, no credit card.

## Quick Start

```bash
PYTHONPATH=src .venv/bin/python scripts/poc_pytrends.py
```

## API

```python
from blog_automation.integrations.trends_client import TrendsClient

client = TrendsClient()

# Compare keywords across countries
df = client.compare_keywords(["air fryer", "coffee maker"], geo="US")
# → DataFrame: weekly interest for each keyword (0-100)

# Trending in a country
trending = client.trending_topics("VN", limit=10)
# → [{"title": "du lịch", "source": "trends"}, ...]

# Related queries (top + rising)
related = client.related_queries("air fryer", geo="US")
# → {"top": DataFrame, "rising": DataFrame}
```

## Examples

| Input | Output |
|---|---|
| `compare_keywords(["air fryer","coffee maker"], "US")` | US: air fryer=65, coffee maker=18 |
| `compare_keywords(["air fryer"], "VN")` | VN: air fryer=17 |
| `trending_topics("VN")` | du lịch, giải trí, bóng đá, công nghệ |
| `related_queries("air fryer", "US")` | rising: best air fryer 2026 (+13800%), ninja crispi pro (+10500%) |

## Supported Geos

`US` `VN` `AU` `GB` `CA` `DE` `FR` `JP` `SG` `IN`

## Rate Limits

Google Trends rate-limits aggressively. Scripts include 2s delay between calls + retry on 429. For batch jobs, space out requests.
