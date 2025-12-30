# Quick Start Guide - AI Blog Automation

## 1. Install Dependencies

```bash
cd ai-blog-automation
poetry install
```

## 2. Configure Environment

Copy the example env file and fill in your API keys:

```bash
cp .env.example .env
```

### Minimum Required Keys

| Service | Variable | Get it from |
|---------|----------|-------------|
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| Anthropic | `ANTHROPIC_API_KEY` | https://console.anthropic.com/ |
| Database | `DATABASE_URL` | Local PostgreSQL or cloud |

### Optional Keys (for full functionality)

| Service | Variable | Purpose |
|---------|----------|---------|
| Ahrefs | `AHREFS_API_KEY` | Keyword research |
| Perplexity | `PERPLEXITY_API_KEY` | Fact-checking sources |
| Copyscape | `COPYSCAPE_API_KEY` | Plagiarism detection |
| WordPress | `WORDPRESS_URL`, `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD` | Publishing |
| Google Analytics | `GOOGLE_ANALYTICS_PROPERTY_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON` | Metrics |

## 3. Test Integrations

```bash
poetry run python scripts/setup_integrations.py
```

This will test each integration and show which ones are working.

## 4. Setup Database

```bash
# Start PostgreSQL (if using Docker)
docker run -d --name blog-postgres \
  -e POSTGRES_USER=blog \
  -e POSTGRES_PASSWORD=blog \
  -e POSTGRES_DB=blog_db \
  -p 5432:5432 \
  postgres:15

# Run migrations
poetry run alembic upgrade head
```

## 5. Run Tests

```bash
poetry run pytest tests/unit/ -v
```

## 6. Quick Usage Examples

### Generate a Content Brief

```python
from blog_automation.pipelines import research_keyword_full

brief = research_keyword_full("python web scraping tutorial")
print(brief.brief_data)
```

### Generate an Article Draft

```python
from blog_automation.pipelines import content_brief_to_draft

article = content_brief_to_draft(brief)
print(article.content_draft[:500])
```

### Publish to WordPress

```python
from blog_automation.pipelines import publish_article

result = publish_article(article)
print(f"Published: {result['url']}")
```

## API Key Setup Guides

### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy and add to `.env` as `OPENAI_API_KEY`

### Anthropic (Claude)
1. Go to https://console.anthropic.com/
2. Navigate to API Keys
3. Create a new key
4. Copy and add to `.env` as `ANTHROPIC_API_KEY`

### WordPress App Password
1. Go to your WordPress admin → Users → Profile
2. Scroll to "Application Passwords"
3. Enter a name (e.g., "Blog Automation")
4. Click "Add New Application Password"
5. Copy the password (spaces are OK)
6. Add to `.env` as `WORDPRESS_APP_PASSWORD`

### Ahrefs
1. Go to https://ahrefs.com/api
2. Get your API key from account settings
3. Add to `.env` as `AHREFS_API_KEY`

### Perplexity
1. Go to https://www.perplexity.ai/settings/api
2. Generate an API key
3. Add to `.env` as `PERPLEXITY_API_KEY`

### Google Analytics
1. Create a service account in Google Cloud Console
2. Enable Analytics Data API
3. Download the JSON key file
4. Add property ID to `.env` as `GOOGLE_ANALYTICS_PROPERTY_ID`
5. Add path to JSON as `GOOGLE_SERVICE_ACCOUNT_JSON`

## Troubleshooting

### "Module not found" errors
```bash
poetry install
```

### Database connection errors
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Or start it
docker start blog-postgres
```

### API rate limits
The system has built-in retry logic with exponential backoff. If you hit rate limits frequently, consider:
- Reducing concurrent requests
- Adding delays between operations
- Upgrading your API plan

## Next Steps

1. Run the full pipeline test: `poetry run pytest tests/integration/ -v`
2. Set up Airflow for automation (see `airflow_dags/`)
3. Configure the human review interface

## 7. Web UI (Streamlit Dashboard)

Launch the web interface for reviewing articles:

```bash
poetry run streamlit run streamlit_app/app.py
```

This opens a browser at `http://localhost:8501` with:
- 🏠 **Dashboard** - Overview and quick stats
- 📋 **Review Queue** - Approve/reject articles with full reports
- 📄 **All Articles** - Browse and filter all content
- 📅 **Content Calendar** - Plan upcoming articles
- ⚙️ **Settings** - Configuration and commands

### Features
- View article content, fact-check reports, and SEO analysis
- Approve, request revisions, or reject articles
- Filter by status and search by keyword
- Track pipeline progress
