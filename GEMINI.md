# GEMINI.md - AI Blog Content Automation Platform

## Project Overview
This project is an **AI-driven blog automation platform** designed to streamline the entire content lifecycle—from keyword research to publishing—while maintaining high quality, fact-checking standards, and SEO optimization. It is built to comply with E-E-A-T guidelines and Mediavine/AdSense requirements.

### Core Technologies
- **Language:** Python 3.11+
- **Database:** PostgreSQL with SQLAlchemy 2.0 & Alembic
- **Validation:** Pydantic v2
- **UI:** Streamlit (Human Review Interface)
- **AI Models:** GPT-4 (Drafting), Claude 3 (Fact-checking/Outlining)
- **APIs:** Ahrefs (Keywords), Perplexity (Evidence), Copyscape (Plagiarism), Rank Math (SEO), WordPress REST API

### Key Architectural Layers
1.  **Integrations Layer:** Robust API clients for external services with built-in retry logic and rate limiting.
2.  **Models Layer:** SQLAlchemy 2.0 models for Articles, Briefs, Metrics, and Reviews.
3.  **Pipelines Layer:** Business logic for research, drafting, fact-checking, and publishing.
4.  **Review Layer:** Streamlit-based interface for mandatory human-in-the-loop validation.

---

## Building and Running

### 1. Prerequisites
- Python 3.11 or higher.
- Poetry (dependency management).
- PostgreSQL 15 or higher.

### 2. Setup
```bash
# Install dependencies
poetry install

# Configure environment (copy .env.example to .env and fill in API keys)
cp .env.example .env

# Initialize database and run migrations
alembic upgrade head
```

### 3. Running the Application
- **Human Review Dashboard:** `streamlit run streamlit_app/app.py`
- **Airflow Scheduler:** `airflow scheduler`
- **Airflow Webserver:** `airflow webserver`

### 4. Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/blog_automation
```

### 5. Mock Mode (Fast Testing)
You can run the entire pipeline without real API keys by enabling Mock Mode. This uses pre-defined dummy data for all AI and SEO steps.
1.  Add `MOCK_MODE=True` to your `.env` file.
2.  Run the pipeline as usual via Dashboard or CLI.
3.  Great for testing UI changes or database migrations quickly.

---

## Development Conventions

### Coding Standards
- **Formatting:** Use `black` for code formatting (line length 88).
- **Linting:** Use `flake8` for linting.
- **Type Safety:** Use `mypy` for static type checking; all new code must have type hints.
- **Imports:** Use `isort` to maintain consistent import order.

### Project Structure
- `src/blog_automation/integrations/`: Dedicated clients for each external API.
- `src/blog_automation/models/`: Domain models using SQLAlchemy's modern `Mapped` types.
- `src/blog_automation/pipelines/`: Isolated processing steps (Research -> Draft -> Fact-check -> SEO -> Publish).
- `tests/`: Organized into `unit/`, `integration/`, and `fixtures/`.

### Key Workflows
- **Research -> Brief -> Draft:** Automation starts from a keyword in the content calendar.
- **Fact-Checking Gate:** Every article must undergo automated claim extraction and verification via Claude 3 and Perplexity.
- **Human Review:** No article is published without a manual `APPROVE` verdict in the review interface.
- **Cost Tracking:** AI token usage and USD cost are tracked per-article to maintain efficiency (<$1/article target).

### Error Handling
- Use the custom exceptions defined in `src/blog_automation/errors.py`.
- Apply the `@retry` decorator for transient API failures.
- Logs are structured JSON stored in the `logs/` directory.
