# AI Blog Content Automation Platform

Automated AI content generation, fact-checking, SEO optimization, and publishing platform for blog monetization.

## Features

- **Keyword Research**: Automated keyword analysis using Ahrefs API
- **Content Brief Generation**: AI-powered content briefs with competitor analysis
- **Article Drafting**: GPT-4 powered article generation with quality controls
- **Fact-Checking**: Automated claim extraction and verification using Claude
- **SEO Optimization**: Rank Math integration and meta tag optimization
- **Quality Gates**: Plagiarism detection, link verification, readability scoring
- **WordPress Publishing**: Automated publishing with ACF metadata
- **Human Review**: Mandatory editorial review workflow
- **Analytics Tracking**: GA4 and Google Search Console integration

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

# Run migrations
alembic upgrade head
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
├── migrations/                # Alembic migrations
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
