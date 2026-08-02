---
title: Side Blogs Dashboard
emoji: 📝
colorFrom: blue
colorTo: gray
sdk: streamlit
sdk_version: 1.40.0
app_file: streamlit_app/app.py
pinned: false
---

# Side Blogs — AI Blog Automation Dashboard

File-based Streamlit dashboard for the side-blogs static site.

**Features:**
- 📊 Content overview & stats
- 📄 Article management (published + drafts)
- 📅 Content calendar
- 🚀 Publish workflow overview
- ⚙️ Setup & deploy guide

## Requirements

- Python 3.11+
- PostgreSQL 15+
- Apache Airflow (for orchestration)

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ai-blog-automation
```

### 2. Install Dependencies

Using Poetry (recommended):
```bash
poetry install
```

Or using pip:
```bash
pip install -e ".[dev]"
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and database URL
```

### 4. Setup Database

```bash
# Create PostgreSQL database
createdb blog_db
```

### 5. Run Tests

```bash
pytest tests/ -v --cov=src/blog_automation
```

## Project Structure

```
ai-blog-automation/
├── src/blog_automation/       # Main application code
│   ├── config.py              # Configuration management
│   ├── errors.py              # Custom exceptions
│   ├── logging_config.py      # Logging setup
│   ├── models/                # SQLAlchemy models
│   ├── integrations/          # API clients
│   ├── pipelines/             # Business logic pipelines
│   └── review/                # Human review interface
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── fixtures/              # Test fixtures

├── airflow_dags/              # Airflow DAG definitions
└── logs/                      # Application logs
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for required variables.

### Required API Keys

- `OPENAI_API_KEY`: For GPT-4 content generation
- `ANTHROPIC_API_KEY`: For Claude fact-checking
- `AHREFS_API_KEY`: For keyword research
- `PERPLEXITY_API_KEY`: For evidence retrieval
- `COPYSCAPE_API_KEY`: For plagiarism detection

## Development

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src/blog_automation --cov-report=html

# Specific test file
pytest tests/unit/test_errors.py -v
```

## License

MIT License
=======
**No database required** — reads directly from `content/*.md` and `public/posts.json`.
