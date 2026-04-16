# AI Blog Content Automation System
## Detailed Implementation Blueprint & Code Generation Prompts

---

## PHASE 0: FOUNDATIONAL PLANNING

### High-Level Architecture Blueprint

```
LAYER 1: Infrastructure & Setup
├─ Project initialization (Python, dependencies, env)
├─ Database setup (PostgreSQL, migrations)
├─ Configuration management (env variables, settings)
└─ Logging & error tracking

LAYER 2: Data Models & Database
├─ Core data models (Article, Review, Brief, etc.)
├─ Database migrations
├─ Query helpers & ORM configuration
└─ Testing fixtures & seeds

LAYER 3: External API Integrations
├─ Base HTTP client with retry logic
├─ Ahrefs API (keyword research)
├─ OpenAI API (content generation)
├─ Anthropic API (fact-checking)
├─ Perplexity API (evidence retrieval)
├─ WordPress REST API (publishing)
├─ Rank Math API (SEO analysis)
└─ Google APIs (Analytics, GSC)

LAYER 4: Core Business Logic (Pipelines)
├─ Keyword research pipeline
├─ Content brief generation
├─ AI content drafting
├─ Claim extraction & filtering
├─ Fact-checking pipeline
├─ SEO optimization
├─ Quality gates & validation
└─ WordPress publishing

LAYER 5: Orchestration & Automation
├─ Apache Airflow DAG definitions
├─ Task scheduling
├─ Error handling & retries
├─ Monitoring & notifications
└─ Audit logging

LAYER 6: Human Review Interface
├─ Review task queue
├─ Web/CLI interface for editors
├─ Feedback capture
├─ Revision management
└─ Reporting dashboard

LAYER 7: Testing & Quality Assurance
├─ Unit test suite
├─ Integration tests
├─ End-to-end tests
├─ Performance tests
├─ Security tests
└─ CI/CD pipeline
```

### Implementation Timeline (6-8 weeks for MVP)

| Week | Layer | Focus | Deliverable |
|------|-------|-------|-------------|
| 1 | Layers 1-2 | Setup, Database, Schemas | Working DB with migrations |
| 2 | Layer 3 | API Clients | All 7 API integrations working |
| 3 | Layer 4 (pt 1) | Research & Drafting | Keyword→Brief→Draft pipeline |
| 4 | Layer 4 (pt 2) | Fact-Checking & SEO | Complete quality gates |
| 5 | Layer 4 (pt 3) | Publishing & Gates | WordPress publishing working |
| 6 | Layer 5 | Orchestration | Airflow DAGs fully configured |
| 7 | Layers 6-7 | Testing & Review | Full test suite + CI/CD |
| 8 | Layer 7 | Hardening | Production-ready optimization |

---

## PHASE 1: CHUNKING & ITERATION

### First Round: Large Chunks (7 work areas)

```
CHUNK 1: Project Foundation
├─ Python project setup
├─ Poetry/pip dependency management
├─ Environment configuration
├─ Logging system
└─ Error handling framework

CHUNK 2: Database Infrastructure
├─ PostgreSQL schema design
├─ SQLAlchemy ORM models
├─ Database migrations (Alembic)
├─ Connection pooling
└─ Testing fixtures

CHUNK 3: API Client Layer
├─ Base HTTP client with retry logic
├─ Ahrefs API client
├─ OpenAI/Claude API clients
├─ Perplexity API client
├─ WordPress REST API client
└─ Error handling for APIs

CHUNK 4: Content Generation Pipeline
├─ Keyword research pipeline
├─ Content brief generation
├─ Article drafting (GPT-4)
├─ Claim extraction (Claude)
└─ Fact-checking pipeline

CHUNK 5: Quality & Optimization
├─ Plagiarism detection
├─ SEO analysis & optimization
├─ Link verification
├─ Readability scoring
└─ Quality gates

CHUNK 6: Publishing & Tracking
├─ WordPress publishing integration
├─ Analytics setup (GA4, GSC)
├─ Metadata storage
├─ Performance tracking
└─ Scheduled publishing

CHUNK 7: Orchestration & Testing
├─ Apache Airflow setup
├─ DAG definitions
├─ Human review interface
├─ Full test suite
└─ CI/CD pipeline
```

### Second Round: Medium-Sized Chunks (Breaking down Chunks)

**CHUNK 1: Project Foundation** → 3 sub-chunks
```
1.1: Python Environment Setup
  ├─ pyproject.toml configuration
  ├─ Virtual environment setup
  ├─ Dependency management (poetry)
  └─ Version pinning

1.2: Configuration & Logging
  ├─ Environment variables (.env)
  ├─ Settings class (dev/test/prod)
  ├─ Logger configuration
  └─ Error tracking setup

1.3: Error Handling Framework
  ├─ Custom exception classes
  ├─ Error codes & mappings
  ├─ Error handler decorators
  └─ Alert/notification system
```

**CHUNK 2: Database Infrastructure** → 4 sub-chunks
```
2.1: ORM Models Definition
  ├─ Article model
  ├─ ContentBrief model
  ├─ ArticleReview model
  ├─ ArticleMetrics model
  └─ ContentCalendar model

2.2: Database Initialization
  ├─ SQLAlchemy engine setup
  ├─ Session management
  ├─ Connection pooling
  └─ Database creation

2.3: Schema Migrations (Alembic)
  ├─ Migration setup
  ├─ Initial schema migration
  ├─ Migration utilities
  └─ Rollback capabilities

2.4: Testing Fixtures
  ├─ Test database setup
  ├─ Fixture factories
  ├─ Mock data generators
  └─ Cleanup utilities
```

**CHUNK 3: API Client Layer** → 5 sub-chunks
```
3.1: Base HTTP Client
  ├─ Retry logic (exponential backoff)
  ├─ Timeout handling
  ├─ Rate limiting
  ├─ Response parsing
  └─ Error handling

3.2: Ahrefs API Client
  ├─ Authentication setup
  ├─ Keyword research methods
  ├─ SERP analysis methods
  ├─ Competitor analysis methods
  └─ Caching layer

3.3: OpenAI/Claude API Clients
  ├─ Model selection logic
  ├─ Prompt engineering
  ├─ Token counting
  ├─ Cost tracking
  └─ Streaming response handling

3.4: Supporting API Clients
  ├─ Perplexity API client
  ├─ Copyscape API client
  ├─ Rank Math API client
  └─ Google APIs (Analytics, GSC)

3.5: WordPress REST API Client
  ├─ Authentication (app passwords)
  ├─ Post creation/update
  ├─ Media upload
  ├─ Custom fields (ACF)
  └─ Batch operations
```

**CHUNK 4: Content Generation Pipeline** → 4 sub-chunks
```
4.1: Keyword Research Pipeline
  ├─ Fetch keyword from calendar
  ├─ Ahrefs metrics retrieval
  ├─ SERP feature analysis
  ├─ Competitor content analysis
  └─ Data validation & storage

4.2: Content Brief Generation
  ├─ Brief structure generation
  ├─ Section recommendations
  ├─ LSI keyword identification
  ├─ Source collection
  └─ Validation & feedback

4.3: Article Drafting
  ├─ Outline generation
  ├─ Full article generation
  ├─ Quality enforcement in prompt
  ├─ Cost tracking
  └─ Storage in database

4.4: Fact-Checking Pipeline
  ├─ Claim extraction
  ├─ Claim filtering
  ├─ Evidence retrieval (Perplexity)
  ├─ Claim verification
  ├─ Issue reporting
  └─ Suggestion generation
```

**CHUNK 5: Quality & Optimization** → 3 sub-chunks
```
5.1: Plagiarism & Content Checks
  ├─ Copyscape integration
  ├─ Internal duplicate checking
  ├─ Threshold validation
  ├─ Alert generation
  └─ Auto-rejection logic

5.2: SEO Optimization
  ├─ Rank Math API analysis
  ├─ SurferSEO content matching
  ├─ Meta tag optimization
  ├─ Keyword density analysis
  └─ Recommendation generation

5.3: Final Quality Gates
  ├─ Link verification
  ├─ Metadata validation
  ├─ Readability scoring
  ├─ Image optimization
  └─ Pre-publishing checklist
```

**CHUNK 6: Publishing & Tracking** → 3 sub-chunks
```
6.1: WordPress Publishing
  ├─ Content formatting (MD→HTML)
  ├─ Image uploads
  ├─ Post creation via REST API
  ├─ Metadata storage (ACF)
  ├─ Schedule vs publish
  └─ Error handling & retries

6.2: Analytics Setup
  ├─ GA4 initialization
  ├─ Google Search Console integration
  ├─ Event tracking code
  ├─ Custom field setup
  └─ Data sync scheduling

6.3: Performance Tracking
  ├─ Daily metrics collection
  ├─ GSC data import
  ├─ Rank tracking
  ├─ Performance dashboard
  └─ Email reports
```

**CHUNK 7: Orchestration & Testing** → 3 sub-chunks
```
7.1: Apache Airflow Setup
  ├─ Airflow initialization
  ├─ DAG structure definition
  ├─ Task dependencies
  ├─ Scheduling configuration
  └─ Monitoring setup

7.2: Human Review Interface
  ├─ Task queue system
  ├─ Review dashboard (web or CLI)
  ├─ Feedback capture
  ├─ Revision workflow
  └─ Email notifications

7.3: Testing & CI/CD
  ├─ Unit test suite structure
  ├─ Integration tests
  ├─ Test fixtures & mocks
  ├─ Coverage reporting
  ├─ GitHub Actions CI/CD
  └─ Deployment automation
```

### Third Round: Small, Implementable Steps

Now breaking each medium chunk into small, testable steps (~1-4 hours each):

```
LAYER 1: FOUNDATION (Week 1)

STEP 1.1: Create Python Project Structure
  - pyproject.toml with dependencies
  - .env.example file
  - src/ directory structure
  - README.md
  - .gitignore
  Time: 1 hour | Test: Import main modules

STEP 1.2: Setup Logging & Error Classes
  - Custom exception hierarchy
  - Logger configuration
  - Error codes enumeration
  - Log output formatting
  Time: 1.5 hours | Test: Unit tests for exceptions

STEP 1.3: Configuration Management
  - Settings class (dev/test/prod)
  - Environment variable loading
  - Validation of required vars
  - Test configuration setup
  Time: 1 hour | Test: Config loading tests

STEP 1.4: Error Handling Framework
  - Error handler decorator
  - Retry logic helper
  - Alert/notification skeleton
  - Error tracking integration
  Time: 1.5 hours | Test: Decorator tests with mock failures

LAYER 2: DATABASE (Week 1-2)

STEP 2.1: SQLAlchemy Setup & Article Model
  - Database engine creation
  - Base model class
  - Article model (core fields only)
  - Session factory
  Time: 1.5 hours | Test: Model creation & basic queries

STEP 2.2: Add Supporting Models (Brief, Calendar, Review)
  - ContentBrief model
  - ContentCalendar model
  - ArticleReview model
  - Foreign key relationships
  Time: 1.5 hours | Test: Relationship tests

STEP 2.3: Add Metrics & Metadata Models
  - ArticleMetrics model
  - JSON metadata fields
  - Indexes for performance
  - Time-series fields
  Time: 1 hour | Test: Metrics storage & queries

STEP 2.4: Alembic Migration Setup
  - Alembic initialization
  - Initial migration (create all tables)
  - Migration utilities
  - Version management
  Time: 1 hour | Test: Migration up/down tests

STEP 2.5: Database Fixtures & Testing Setup
  - Test database URL
  - Fixture factories (factory_boy)
  - Cleanup fixtures
  - Mock data generators
  Time: 1.5 hours | Test: Fixture tests

LAYER 3: API CLIENTS (Week 2-3)

STEP 3.1: Base HTTP Client with Retry Logic
  - requests wrapper
  - Exponential backoff retry
  - Timeout handling
  - Rate limit detection
  Time: 2 hours | Test: Retry mechanism tests with mock server

STEP 3.2: Ahrefs API Client
  - Authentication (API key)
  - Keyword search method
  - SERP analysis method
  - Response parsing
  - Caching decorator
  Time: 2 hours | Test: Mock Ahrefs API tests

STEP 3.3: OpenAI API Client
  - Model selection logic
  - Chat completion wrapper
  - Token counting
  - Cost calculation
  - Streaming handler
  Time: 2 hours | Test: Mock OpenAI API tests

STEP 3.4: Claude (Anthropic) API Client
  - Message API wrapper
  - Model selection
  - Token limits
  - Cost tracking
  - Cache usage
  Time: 1.5 hours | Test: Mock Claude API tests

STEP 3.5: Perplexity API Client
  - Web search method
  - Response structure
  - Error handling
  - Result ranking
  Time: 1.5 hours | Test: Mock Perplexity tests

STEP 3.6: Supporting API Clients (WordPress, Copyscape, Rank Math, Google)
  - WordPress REST API client
  - Copyscape API client
  - Rank Math API client
  - Google Analytics client
  - Google Search Console client
  Time: 3 hours | Test: Mock API tests for each

LAYER 4: CORE PIPELINES (Week 3-5)

STEP 4.1: Keyword Research Pipeline
  - Fetch keyword from calendar
  - Call Ahrefs API
  - Parse & validate response
  - Store ContentBrief in DB
  Time: 2 hours | Test: Integration test with mocked Ahrefs

STEP 4.2: Content Brief Generation
  - Generate brief structure (sections, sources)
  - Call OpenAI for brief generation
  - Validate brief completeness
  - Store & return brief
  Time: 2 hours | Test: Integration test with mocked GPT-4

STEP 4.3: Article Outline Generation
  - Create outline prompt
  - Call Claude for outline
  - Parse outline structure
  - Validate hierarchy
  Time: 1.5 hours | Test: Outline validation tests

STEP 4.4: Full Article Drafting
  - Create drafting prompt
  - Call GPT-4 Turbo
  - Enforce quality constraints in response
  - Store draft in database
  - Track costs
  Time: 2 hours | Test: Draft validation tests

STEP 4.5: Claim Extraction Pipeline
  - Create extraction prompt
  - Call Claude for claim extraction
  - Parse claim JSON
  - Store claims for fact-checking
  Time: 1.5 hours | Test: Claim parsing tests

STEP 4.6: Claim Filtering & Verification
  - Filter out non-checkworthy claims
  - Call Perplexity for evidence
  - Compare claims to evidence
  - Generate verification report
  Time: 2 hours | Test: Verification logic tests

STEP 4.7: Fact-Check Report Generation
  - Aggregate verification results
  - Calculate accuracy metrics
  - Generate issue list
  - Store report in database
  - Pass/fail determination
  Time: 1.5 hours | Test: Report structure tests

LAYER 5: QUALITY & OPTIMIZATION (Week 5-6)

STEP 5.1: Plagiarism Detection Integration
  - Copyscape API calls
  - Internal duplicate detection
  - Threshold checking
  - Issue flagging
  Time: 1.5 hours | Test: Mock Copyscape tests

STEP 5.2: SEO Analysis Pipeline
  - Rank Math API integration
  - SurferSEO comparison
  - Score calculation
  - Recommendation generation
  Time: 2 hours | Test: SEO analysis tests

STEP 5.3: Meta Tags Optimization
  - Meta title generation
  - Meta description generation
  - Human review & selection
  - Validation (length, keyword placement)
  Time: 1.5 hours | Test: Meta tag tests

STEP 5.4: Link Verification & Image Optimization
  - Verify all links (internal & external)
  - Image alt text optimization
  - Featured image selection
  - Broken link detection
  Time: 1.5 hours | Test: Link verification tests

STEP 5.5: Final Quality Gates
  - Readability scoring
  - Word count validation
  - Keyword density checks
  - Metadata completeness
  - Pre-publishing checklist
  Time: 1.5 hours | Test: Gate validation tests

LAYER 6: PUBLISHING & TRACKING (Week 6)

STEP 6.1: Content Formatting (Markdown to HTML)
  - Markdown parser setup
  - HTML conversion
  - Link handling
  - Code block formatting
  Time: 1.5 hours | Test: Markdown conversion tests

STEP 6.2: Image Handling & Upload
  - Image download
  - Image compression
  - WordPress upload via REST API
  - Attachment ID tracking
  Time: 1.5 hours | Test: Mock WordPress upload tests

STEP 6.3: WordPress Post Creation
  - Create post via REST API
  - Set metadata & categories
  - Handle draft vs publish
  - Retry on failure
  Time: 1.5 hours | Test: Mock WordPress post tests

STEP 6.4: ACF Custom Fields Storage
  - AI metadata storage
  - Fact-check results storage
  - SEO scores storage
  - Human review tracking
  Time: 1 hour | Test: Custom field tests

STEP 6.5: GA4 & GSC Integration Setup
  - GA4 tracking code insertion
  - GSC API authentication
  - Event tracking configuration
  - Data sync scheduling
  Time: 1.5 hours | Test: Tracking setup tests

STEP 6.6: Performance Metrics Collection
  - Daily metrics pull from GA4
  - Daily rank data from GSC
  - Database storage
  - Email report generation
  Time: 1.5 hours | Test: Metrics collection tests

LAYER 7: ORCHESTRATION & TESTING (Week 7-8)

STEP 7.1: Apache Airflow Project Setup
  - Airflow initialization
  - DAG directory structure
  - Variables & connections setup
  - Local executor configuration
  Time: 1.5 hours | Test: DAG parsing tests

STEP 7.2: Main DAG Definition
  - Keyword fetch task
  - Brief generation task
  - Drafting task
  - Fact-checking task
  - Task dependencies
  Time: 2 hours | Test: DAG structure tests

STEP 7.3: Human Review Task & Notifications
  - Task queue creation
  - Email notifications
  - Slack notifications (optional)
  - Task status tracking
  Time: 1.5 hours | Test: Notification tests

STEP 7.4: SEO & Publishing DAG Tasks
  - SEO optimization task
  - Final gates task
  - WordPress publishing task
  - Analytics setup task
  Time: 2 hours | Test: Publishing flow tests

STEP 7.5: Unit Test Suite Structure
  - Test directory organization
  - pytest configuration
  - Fixture setup
  - Mock utilities
  Time: 1.5 hours | Test: Test structure tests

STEP 7.6: Integration & E2E Tests
  - Full pipeline integration tests
  - Mock all external APIs
  - End-to-end flow tests
  - Error scenario tests
  Time: 3 hours | Test: Integration tests running

STEP 7.7: CI/CD Pipeline (GitHub Actions)
  - GitHub Actions workflow
  - Test execution
  - Coverage reporting
  - Automated deployment
  Time: 1.5 hours | Test: CI/CD running on pushes

STEP 7.8: Code Quality & Security
  - Linting setup (Black, flake8)
  - Type checking (mypy)
  - Security scanning
  - Documentation
  Time: 2 hours | Test: All quality checks passing
```

---

## PHASE 2: FINAL STEP SIZING REVIEW

### Step Sizing Analysis

**Verification Checklist for Each Step:**

```
✓ Scoped to 1-4 hours (realistically implementable)
✓ Has clear inputs/outputs
✓ Can be tested independently
✓ Has explicit test criteria
✓ Builds on previous steps
✓ No orphaned code (integrated with prior steps)
✓ Demonstrates working feature
✓ Provides visible progress
✓ Error handling included
✓ Documentation included
```

### Integration Graph (Dependency Order)

```
Step 1.1 (Project)
    ↓
Step 1.2 (Logging)
    ├─→ Step 1.3 (Config)
    ├─→ Step 1.4 (Error Framework)
    ├─→ Step 2.1 (Database)
    │   ├─→ Step 2.2 (Models)
    │   ├─→ Step 2.3 (Metrics)
    │   ├─→ Step 2.4 (Migrations)
    │   └─→ Step 2.5 (Fixtures)
    │
    └─→ Step 3.1 (HTTP Client)
        ├─→ Step 3.2 (Ahrefs)
        ├─→ Step 3.3 (OpenAI)
        ├─→ Step 3.4 (Claude)
        ├─→ Step 3.5 (Perplexity)
        └─→ Step 3.6 (Other APIs)
            ├─→ Step 4.1 (Keyword Research)
            ├─→ Step 4.2 (Brief Generation)
            ├─→ Step 4.3 (Outline)
            ├─→ Step 4.4 (Drafting)
            ├─→ Step 4.5 (Claim Extraction)
            ├─→ Step 4.6 (Verification)
            └─→ Step 4.7 (Report)
                ├─→ Step 5.1 (Plagiarism)
                ├─→ Step 5.2 (SEO)
                ├─→ Step 5.3 (Meta Tags)
                ├─→ Step 5.4 (Links)
                └─→ Step 5.5 (Final Gates)
                    ├─→ Step 6.1 (Formatting)
                    ├─→ Step 6.2 (Images)
                    ├─→ Step 6.3 (Publishing)
                    ├─→ Step 6.4 (ACF)
                    ├─→ Step 6.5 (GA4)
                    └─→ Step 6.6 (Metrics)
                        ├─→ Step 7.1 (Airflow)
                        ├─→ Step 7.2 (DAGs)
                        ├─→ Step 7.3 (Review)
                        ├─→ Step 7.4 (Publishing DAG)
                        ├─→ Step 7.5 (Tests)
                        ├─→ Step 7.6 (Integration)
                        ├─→ Step 7.7 (CI/CD)
                        └─→ Step 7.8 (Quality)
```

**No hanging code.** Each step explicitly integrates with prior steps.

---

## PHASE 3: LLM CODE GENERATION PROMPTS

Now follows a complete series of prompts for a code-generation LLM. Each prompt:
- References specific steps from above
- Provides necessary context
- Specifies test requirements
- Builds on previous steps
- Provides wiring instructions for integration

---

### PROMPT 1: Project Setup & Dependencies

```
CONTEXT:
Step 1.1: Create Python Project Structure
Duration: 1 hour
Deliverable: Working Python project with all dependencies installed

TASK DESCRIPTION:
You are building the Python backend for an AI Blog Content Automation Platform. 
This is the foundation step - all subsequent work depends on getting this right.

Create a complete, production-ready Python project structure with:
1. pyproject.toml with all required dependencies
2. Modern Python package structure
3. Environment configuration
4. Testing infrastructure setup
5. CI/CD-ready layout

PROJECT DETAILS:
- Target Python version: 3.11+
- Database: PostgreSQL 15+
- Main frameworks: FastAPI, SQLAlchemy, Apache Airflow
- APIs: OpenAI, Anthropic (Claude), Ahrefs, Perplexity, WordPress
- Testing: pytest with coverage

REQUIREMENTS:

A. pyproject.toml Structure:
   - Project name: ai-blog-automation
   - Version: 0.1.0
   - Description: "Automated AI content generation, fact-checking, and publishing platform"
   - License: MIT
   - Python requires: ">=3.11,<4.0"
   
B. Core Dependencies (add specific versions):
   RUNTIME:
   - sqlalchemy[postgresql]: ORM with PostgreSQL support
   - alembic: Database migrations
   - pydantic: Data validation
   - python-dotenv: Environment variables
   - requests: HTTP client
   - openai: OpenAI API
   - anthropic: Claude API
   - airflow-core: Workflow orchestration
   - markdown2: Content conversion
   - pytest: Testing
   - black: Code formatting
   - mypy: Type checking
   - flake8: Linting
   - pytest-cov: Coverage reporting
   - pytest-mock: Mocking
   - factory-boy: Test data generation

C. Project Directory Structure:
   ```
   ai-blog-automation/
   ├── pyproject.toml
   ├── poetry.lock (or requirements.txt)
   ├── .env.example
   ├── .gitignore
   ├── README.md
   ├── src/
   │   └── blog_automation/
   │       ├── __init__.py
   │       ├── config.py
   │       ├── logging_config.py
   │       ├── errors.py
   │       ├── models/
   │       │   └── __init__.py
   │       ├── integrations/
   │       │   └── __init__.py
   │       ├── pipelines/
   │       │   └── __init__.py
   │       ├── utils/
   │       │   └── __init__.py
   │       └── airflow_dags/
   │           └── __init__.py
   ├── tests/
   │   ├── conftest.py
   │   ├── __init__.py
   │   ├── unit/
   │   │   └── __init__.py
   │   ├── integration/
   │   │   └── __init__.py
   │   └── fixtures/
   │       └── __init__.py
   ├── migrations/
   │   └── versions/
   └── .github/
       └── workflows/
   ```

D. .env.example (template for developers):
   - DATABASE_URL=postgresql://user:password@localhost:5432/blog_db
   - OPENAI_API_KEY=sk-...
   - ANTHROPIC_API_KEY=sk-ant-...
   - AHREFS_API_KEY=...
   - PERPLEXITY_API_KEY=...
   - WORDPRESS_URL=https://yourblog.com
   - WORDPRESS_USERNAME=...
   - WORDPRESS_APP_PASSWORD=...
   - LOG_LEVEL=INFO
   - ENVIRONMENT=development

E. .gitignore:
   - Standard Python ignores
   - .env and .env.local
   - __pycache__/, *.pyc
   - .pytest_cache/
   - .mypy_cache/
   - *.egg-info/
   - dist/, build/
   - .vscode/, .idea/
   - logs/

F. README.md (basic project documentation):
   - Project description
   - Quick start guide
   - Installation instructions
   - Environment setup
   - Running tests
   - Project structure overview

TESTING REQUIREMENTS:
1. Verify all imports work: "python -c 'import blog_automation'"
2. Verify pytest finds tests: "pytest --collect-only"
3. Verify Black formatting works: "black --check src/"
4. Verify mypy type checking: "mypy src/"
5. Verify project structure with: "tree -L 3 src/"

DELIVERABLES:
1. Complete pyproject.toml (ready to run "poetry install" or "pip install -e .[dev]")
2. .env.example file
3. .gitignore file
4. README.md with setup instructions
5. Directory structure created and validated
6. All imports working (no import errors)

SUCCESS CRITERIA:
✓ Python 3.11+ environment working
✓ All dependencies installable
✓ Project structure matches specification
✓ "pytest --collect-only" finds 0 tests (but structure ready)
✓ No import errors
✓ .env.example covers all needed variables
```

---

### PROMPT 2: Logging & Error Handling Framework

```
CONTEXT:
Step 1.2: Setup Logging & Error Classes
Duration: 1.5 hours
Dependency: Step 1.1 (Project Setup)
Deliverable: Error classes and logging system

TASK DESCRIPTION:
Create a robust error handling and logging framework for the entire application.
This will be used throughout all subsequent steps for consistent error handling,
logging, and monitoring.

REQUIREMENTS:

A. Custom Exception Hierarchy (src/blog_automation/errors.py):
   
   Base Exception:
   - AppError (extends Exception)
     Attributes: message, error_code, severity (critical|error|warning), context
     Methods: to_dict(), __str__()
   
   Categories:
   - APIError (extends AppError)
     - APITimeoutError
     - APIRateLimitError
     - APIAuthenticationError
     - APIInvalidResponseError
     - APIServerError (5xx)
   
   - ValidationError (extends AppError)
     - InvalidKeywordError
     - InvalidBriefError
     - InvalidArticleError
     - MissingFieldError
   
   - ProcessingError (extends AppError)
     - GenerationFailureError
     - VerificationFailureError
     - PublishingFailureError
   
   - DatabaseError (extends AppError)
     - ConnectionError
     - ConstraintViolationError
     - NotFoundError
   
   Error codes:
   - API_TIMEOUT: "api_001"
   - API_RATE_LIMIT: "api_002"
   - API_AUTH_FAILED: "api_003"
   - INVALID_INPUT: "val_001"
   - PROCESSING_FAILED: "proc_001"
   - DB_CONNECTION: "db_001"
   - DB_CONSTRAINT: "db_002"
   [Add 10+ more for complete coverage]

B. Logging Configuration (src/blog_automation/logging_config.py):
   
   Features:
   - Structured logging with JSON output
   - Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - Log rotation (files don't grow unbounded)
   - Timestamp, logger name, level in all logs
   - Different formats for console vs file
   - Request ID tracking (for correlating logs)
   
   Output:
   - Console output: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
   - File output: JSON format with all metadata
   - Log file: "logs/app.log"
   - Rotates daily or at 100MB
   
   Levels:
   - DEBUG: Detailed information for debugging
   - INFO: General informational messages
   - WARNING: Warning messages (recoverable issues)
   - ERROR: Error messages (failures)
   - CRITICAL: Critical failures (stop execution)

C. Logger Factory:
   - get_logger(name) function to create loggers
   - Automatically configured with correct handlers
   - Used throughout app: logger = get_logger(__name__)

D. Error Handler Decorators (src/blog_automation/error_handler.py):
   
   @handle_errors decorator:
   - Catches exceptions automatically
   - Logs with context
   - Converts to AppError if needed
   - Calls alert system
   - Returns error response
   - Example usage:
     ```python
     @handle_errors(error_type=ValidationError, alert=True)
     def parse_keyword(keyword: str):
         ...
     ```
   
   @retry decorator:
   - Exponential backoff retry logic
   - Configurable max retries (default 3)
   - Configurable backoff factor (default 2)
   - Logs retry attempts
   - Example usage:
     ```python
     @retry(max_attempts=3, backoff_factor=2, timeout=30)
     def call_api():
         ...
     ```

E. Alert System (src/blog_automation/alerts.py):
   
   send_alert(error_code, error_message, severity, context)
   - Logs to error tracking service (stub for now)
   - Could integrate with: Sentry, Datadog, etc.
   - Different handlers for different severities
   - CRITICAL alerts go to admin immediately
   - ERROR alerts logged and batched
   - WARMING alerts logged only

TESTING REQUIREMENTS:

1. Test error creation:
   ```python
   def test_api_timeout_error():
       error = APITimeoutError("Request timed out", context={"api": "openai"})
       assert error.error_code == "api_001"
       assert error.severity == "error"
       assert error.to_dict()["context"]["api"] == "openai"
   ```

2. Test logger creation:
   ```python
   def test_get_logger():
       logger = get_logger("test")
       assert logger is not None
       logger.info("Test message")  # Should not raise
   ```

3. Test @handle_errors decorator:
   ```python
   @handle_errors(error_type=ValidationError)
   def failing_function():
       raise ValueError("Test error")
   
   def test_handle_errors():
       result = failing_function()
       assert result["status"] == "error"
       assert "error_code" in result
   ```

4. Test @retry decorator:
   ```python
   call_count = 0
   
   @retry(max_attempts=3, backoff_factor=1)
   def sometimes_fails():
       global call_count
       call_count += 1
       if call_count < 3:
           raise ValueError("Retry me")
       return "success"
   
   def test_retry_succeeds():
       assert sometimes_fails() == "success"
       assert call_count == 3
   ```

5. Test alert system:
   ```python
   def test_send_alert(capsys):
       send_alert("api_001", "API timeout", "error", {})
       # Should log error, not raise exception
   ```

DELIVERABLES:
1. src/blog_automation/errors.py - Exception hierarchy
2. src/blog_automation/logging_config.py - Logging setup
3. src/blog_automation/error_handler.py - Decorators and handlers
4. src/blog_automation/alerts.py - Alert system
5. tests/unit/test_errors.py - Error class tests
6. tests/unit/test_logging.py - Logging tests
7. tests/unit/test_error_handler.py - Decorator tests

SUCCESS CRITERIA:
✓ All error classes instantiate correctly
✓ Error.to_dict() includes all necessary fields
✓ Logger creates files in logs/ directory
✓ @handle_errors catches and logs exceptions
✓ @retry attempts exponential backoff correctly
✓ All tests pass with >90% coverage
✓ No errors when decorators are stacked
```

---

### PROMPT 3: Configuration & Settings Management

```
CONTEXT:
Step 1.3: Configuration Management
Duration: 1 hour
Dependency: Step 1.2 (Logging/Errors)
Deliverable: Settings class for all environments

TASK DESCRIPTION:
Create a centralized configuration management system that handles:
- Environment variables (.env)
- Different settings for dev/test/production
- Validation of required settings
- Secret management
- Initialization on startup

REQUIREMENTS:

A. Settings Class (src/blog_automation/config.py):
   
   Using pydantic BaseSettings:
   - Type-safe configuration
   - Environment variable parsing
   - Validation on initialization
   - Separate classes for dev/test/prod
   
   Settings structure:
   
   class BaseSettings:
     # API Keys (required)
     openai_api_key: str
     anthropic_api_key: str
     ahrefs_api_key: str
     perplexity_api_key: str
     
     # Database
     database_url: str  # postgresql://...
     database_echo: bool = False  # SQL logging
     
     # WordPress
     wordpress_url: str
     wordpress_username: str
     wordpress_app_password: str
     
     # Google APIs
     google_analytics_key: str (optional)
     google_search_console_key: str (optional)
     
     # Application
     environment: str  # "dev" | "test" | "production"
     debug: bool = False
     log_level: str = "INFO"
     
     # API Limits & Timeouts
     api_timeout_seconds: int = 30
     api_max_retries: int = 3
     api_retry_backoff_factor: float = 2.0
     
     # Rate Limiting
     ahrefs_requests_per_day: int = 100
     openai_max_concurrent: int = 3
     
     # Feature Flags
     enable_plagiarism_check: bool = True
     enable_fact_checking: bool = True
     enable_seo_optimization: bool = True
     
     # Paths
     project_root: Path
     logs_directory: Path
     migrations_directory: Path
   
   Configuration from:
   - Environment variables (highest priority)
   - .env file
   - Defaults in class
   
   class DevelopmentSettings(BaseSettings):
     environment: str = "development"
     debug: bool = True
     database_echo: bool = True
     log_level: str = "DEBUG"
   
   class TestSettings(BaseSettings):
     environment: str = "test"
     database_url: str = "sqlite:///:memory:"
     log_level: str = "WARNING"
     enable_plagiarism_check: bool = False
     enable_fact_checking: bool = False
   
   class ProductionSettings(BaseSettings):
     environment: str = "production"
     debug: bool = False
     database_echo: bool = False
     log_level: str = "INFO"

B. Settings Factory:
   
   get_settings() -> BaseSettings:
   - Read ENVIRONMENT env var
   - Load appropriate settings class
   - Validate all required fields present
   - Initialize paths
   - Return configured instance
   
   Used as:
   ```python
   from blog_automation.config import get_settings
   settings = get_settings()
   print(settings.database_url)
   ```

C. Environment Variable Validation:
   
   On startup, verify:
   - All required API keys set
   - Database URL valid format
   - Log directory writable
   - Timeout values reasonable
   
   If missing:
   - Log specific missing variables
   - Raise ConfigurationError with helpful message
   - Suggest .env.example

D. Path Management:
   
   Automatically set:
   - project_root: Path to project root
   - logs_directory: {project_root}/logs (create if not exists)
   - migrations_directory: {project_root}/migrations
   - test_fixtures_directory: {project_root}/tests/fixtures

TESTING REQUIREMENTS:

1. Test settings loading:
   ```python
   def test_development_settings(monkeypatch):
       monkeypatch.setenv("ENVIRONMENT", "development")
       monkeypatch.setenv("OPENAI_API_KEY", "test-key")
       # ... other required vars
       
       settings = get_settings()
       assert settings.environment == "development"
       assert settings.debug is True
   ```

2. Test missing required field:
   ```python
   def test_missing_api_key(monkeypatch):
       monkeypatch.delenv("OPENAI_API_KEY", raising=False)
       monkeypatch.setenv("ENVIRONMENT", "production")
       
       with pytest.raises(ConfigurationError):
           get_settings()
   ```

3. Test .env file loading:
   ```python
   def test_env_file_loading(tmp_path, monkeypatch):
       env_file = tmp_path / ".env"
       env_file.write_text("OPENAI_API_KEY=test-key\n")
       env_file.write_text("ENVIRONMENT=test\n")
       
       monkeypatch.chdir(tmp_path)
       settings = get_settings()
       assert settings.openai_api_key == "test-key"
   ```

4. Test path creation:
   ```python
   def test_logs_directory_created():
       settings = get_settings()
       assert settings.logs_directory.exists()
       assert settings.logs_directory.is_dir()
   ```

5. Test test settings vs production:
   ```python
   def test_different_settings_per_environment():
       dev_settings = DevelopmentSettings()
       test_settings = TestSettings()
       
       assert dev_settings.debug is True
       assert test_settings.debug is False
       assert test_settings.database_url == "sqlite:///:memory:"
   ```

DELIVERABLES:
1. src/blog_automation/config.py - Settings classes
2. .env.example - Template for developers
3. tests/unit/test_config.py - Configuration tests
4. Documentation in README about configuration

SUCCESS CRITERIA:
✓ Settings load from environment variables
✓ Defaults work for missing optional fields
✓ Required fields raise clear errors if missing
✓ Different settings per environment
✓ Paths created automatically
✓ No hardcoded secrets in code
✓ All tests pass
✓ ConfigurationError with helpful messages
```

---

### PROMPT 4: Database Models & ORM Setup

```
CONTEXT:
Step 2.1: SQLAlchemy Setup & Article Model
Duration: 1.5 hours
Dependencies: Steps 1.1, 1.2, 1.3
Deliverable: Database models with working Article model

TASK DESCRIPTION:
Set up SQLAlchemy ORM with core data models. This step creates the database
layer that all other components depend on. Start with the Article model
and gradually add supporting models.

REQUIREMENTS:

A. Database Engine & Session Setup (src/blog_automation/models/__init__.py):
   
   - SQLAlchemy engine creation from DATABASE_URL
   - Session factory with connection pooling
   - Base declarative class for models
   - Query helpers (add(), commit(), rollback(), etc.)
   
   Configuration:
   - Pool size: 10
   - Max overflow: 20
   - Pool timeout: 30 seconds
   - Pool recycle: 3600 seconds (hourly)
   - Echo SQL in debug mode only
   
   Exports:
   ```python
   from blog_automation.models import Base, get_session, engine
   
   # Use in code:
   session = get_session()
   article = session.query(Article).get(1)
   session.commit()
   ```

B. Base Model Class (src/blog_automation/models/base.py):
   
   All models inherit from this:
   - Automatic created_at timestamp
   - Automatic updated_at timestamp
   - to_dict() method for serialization
   - String representation
   
   Fields:
   - created_at: DateTime = Column(DateTime, default=now, nullable=False)
   - updated_at: DateTime = Column(DateTime, default=now, onupdate=now, nullable=False)
   
   Methods:
   - to_dict(): Returns dict of all columns
   - __repr__(): Returns "<Article id=1 title='...'"
   - dict_key: Property for cache keys

C. Article Model (src/blog_automation/models/article.py):
   
   Table: articles
   Indexes: keyword, status, created_at, wordpress_post_id
   
   Core fields:
   - id: Integer (PK)
   - title: String(255) INDEXED
   - slug: String(255) UNIQUE
   - keyword: String(255) INDEXED
   - content_draft: Text
   - content_final: Text
   - content_html: Text
   
   AI Metadata:
   - ai_model_used: String (gpt4|claude3|sonnet|hybrid)
   - ai_generation_cost: Float (USD)
   
   Status & Timestamps:
   - status: String INDEXED (draft|fact_checking|editing|seo_review|approved|published)
   - created_at: DateTime INDEXED
   - updated_at: DateTime
   - published_date: DateTime (nullable)
   
   Fact-Checking:
   - fact_check_report: JSON (full report structure)
   - fact_check_passed: Boolean
   - fact_check_date: DateTime
   - fact_check_issues: Integer (count of issues)
   
   SEO:
   - seo_score: Integer (0-100)
   - seo_analysis: JSON (detailed analysis)
   - meta_title: String(60)
   - meta_description: String(160)
   - keyword_density: Float
   
   Quality:
   - word_count: Integer
   - readability_score: Float
   - plagiarism_percent: Float (0-100)
   - original_content_percent: Float (0-100)
   
   E-E-A-T Scores:
   - eeat_experience: Integer (0-10)
   - eeat_expertise: Integer (0-10)
   - eeat_authoritativeness: Integer (0-10)
   - eeat_trustworthiness: Integer (0-10)
   
   WordPress Integration:
   - wordpress_post_id: Integer (nullable, INDEXED)
   - wordpress_url: String(500) (nullable)
   
   Links:
   - internal_links: JSON (array of post IDs)
   - external_links: JSON (array of URLs)
   
   Tracking:
   - views_30_days: Integer (default 0)
   - avg_time_on_page: Float (default 0.0)
   - bounce_rate: Float (default 0.0)
   
   Audit:
   - created_by: String (nullable)
   - updated_by: String (nullable)
   
   Methods:
   - mark_as_approved()
   - mark_as_published()
   - add_seo_analysis(analysis: dict)
   - add_fact_check_report(report: dict)

D. Content Calendar Model (src/blog_automation/models/content_calendar.py):
   
   Table: content_calendar
   
   Fields:
   - id: Integer (PK)
   - week_number: Integer
   - pub_date: DateTime (target publication date)
   - keyword: String(255)
   - title: String(255) (planned title)
   - status: String (planned|in_progress|submitted|published)
   - assigned_writer: String(100) (nullable)
   - assigned_reviewer: String(100) (nullable)
   - article_id: Integer (FK to Article, nullable)
   - created_at: DateTime
   - updated_at: DateTime
   
   Relationships:
   - article: relationship to Article (one-to-one)

E. Content Brief Model (src/blog_automation/models/brief.py):
   
   Table: content_briefs
   
   Fields:
   - id: Integer (PK)
   - keyword: String(255)
   - search_volume: Integer
   - difficulty: Integer (0-100)
   - intent: String (informational|commercial|transactional)
   - brief_data: JSON (full brief structure with sections, sources, etc.)
   - article_id: Integer (FK to Article, nullable)
   - created_at: DateTime

TESTING REQUIREMENTS:

1. Test engine creation:
   ```python
   def test_engine_creation():
       from blog_automation.models import engine
       assert engine is not None
       # Verify we can connect
       with engine.connect() as conn:
           result = conn.execute(text("SELECT 1"))
           assert result.scalar() == 1
   ```

2. Test session creation:
   ```python
   def test_session_creation():
       from blog_automation.models import get_session
       session = get_session()
       assert session is not None
       session.close()
   ```

3. Test Article model creation:
   ```python
   def test_create_article(db_session):
       article = Article(
           title="Test Article",
           slug="test-article",
           keyword="test",
           status="draft"
       )
       db_session.add(article)
       db_session.commit()
       
       assert article.id is not None
       assert article.created_at is not None
       assert article.status == "draft"
   ```

4. Test Article fields & types:
   ```python
   def test_article_fields_types(db_session):
       article = Article(
           title="Test",
           slug="test",
           keyword="test",
           status="draft",
           seo_score=75,
           word_count=1500,
           plagiarism_percent=2.5
       )
       db_session.add(article)
       db_session.commit()
       
       retrieved = db_session.query(Article).get(article.id)
       assert retrieved.seo_score == 75
       assert isinstance(retrieved.word_count, int)
       assert retrieved.plagiarism_percent == 2.5
   ```

5. Test JSON fields:
   ```python
   def test_json_fields(db_session):
       seo_data = {"score": 75, "issues": ["keyword_placement"]}
       article = Article(
           title="Test",
           slug="test",
           keyword="test",
           status="draft",
           seo_analysis=seo_data
       )
       db_session.add(article)
       db_session.commit()
       
       retrieved = db_session.query(Article).get(article.id)
       assert retrieved.seo_analysis["score"] == 75
   ```

6. Test to_dict() method:
   ```python
   def test_article_to_dict(db_session):
       article = Article(
           title="Test",
           slug="test",
           keyword="test",
           status="draft"
       )
       db_session.add(article)
       db_session.commit()
       
       article_dict = article.to_dict()
       assert "id" in article_dict
       assert article_dict["title"] == "Test"
       assert "created_at" in article_dict
   ```

7. Test relationships:
   ```python
   def test_content_calendar_to_article(db_session):
       article = Article(title="Test", slug="test", keyword="test", status="draft")
       calendar = ContentCalendar(
           week_number=1,
           pub_date=datetime.utcnow(),
           keyword="test",
           title="Test Article",
           status="in_progress",
           article=article
       )
       db_session.add(calendar)
       db_session.commit()
       
       retrieved_cal = db_session.query(ContentCalendar).get(calendar.id)
       assert retrieved_cal.article.title == "Test"
   ```

8. Test unique constraint:
   ```python
   def test_unique_slug_constraint(db_session):
       article1 = Article(title="Test", slug="test", keyword="test", status="draft")
       article2 = Article(title="Test2", slug="test", keyword="test", status="draft")
       
       db_session.add(article1)
       db_session.commit()
       
       db_session.add(article2)
       with pytest.raises(IntegrityError):
           db_session.commit()
   ```

DELIVERABLES:
1. src/blog_automation/models/__init__.py - Engine and session setup
2. src/blog_automation/models/base.py - Base model class
3. src/blog_automation/models/article.py - Article model
4. src/blog_automation/models/content_calendar.py - ContentCalendar model
5. src/blog_automation/models/brief.py - ContentBrief model
6. tests/unit/test_models_article.py - Article model tests
7. tests/unit/test_models_db.py - Database connection tests

SUCCESS CRITERIA:
✓ Engine creates successfully
✓ Sessions are created and closed properly
✓ Article model instantiates with all fields
✓ JSON fields save and retrieve correctly
✓ Timestamps auto-populate
✓ Unique constraints enforced
✓ Relationships work correctly
✓ All tests pass
✓ No import errors
```

---

### PROMPT 5: Alembic Database Migrations

```
CONTEXT:
Step 2.4: Alembic Migration Setup
Duration: 1 hour
Dependencies: Steps 2.1, 2.2, 2.3
Deliverable: Working migration system with initial schema

TASK DESCRIPTION:
Set up Alembic for database schema version control. This allows us to track
schema changes over time and migrate databases between versions.

REQUIREMENTS:

A. Alembic Initialization:
   
   Run: alembic init migrations
   
   Then configure:
   - alembic.ini: Main configuration file
   - migrations/env.py: Migration environment setup
   - migrations/script.py.mako: Migration template
   - migrations/versions/: Directory for migrations

B. Configuration (alembic.ini):
   
   Set sqlalchemy.url dynamically:
   - Don't hardcode, read from settings
   - Support dev/test/production databases
   - Use environment variables
   
   target_metadata = Base.metadata (from models)
   
   Enable auto-detection:
   - compare_type = true
   - compare_server_default = true

C. env.py Configuration:
   
   - Import Base from blog_automation.models
   - Configure target_metadata = Base.metadata
   - Set sqlalchemy.url from settings
   - Auto-generate migrations on schema changes
   - Support both "online" and "offline" modes
   
   Online mode: Runs against live database
   Offline mode: Generates SQL without executing

D. Initial Migration:
   
   Command: alembic revision --autogenerate -m "Initial schema"
   
   Creates migration with:
   - Create articles table
   - Create content_calendar table
   - Create content_briefs table
   - All columns, types, indexes, constraints
   
   Generated in: migrations/versions/001_initial_schema.py
   
   Migration format:
   ```python
   def upgrade():
       # Create tables, add columns, etc.
       op.create_table(
           'articles',
           sa.Column('id', sa.Integer(), nullable=False),
           ...
       )
   
   def downgrade():
       # Reverse operations
       op.drop_table('articles')
   ```

E. Migration Utilities (src/blog_automation/migrations.py):
   
   Helper functions:
   - get_migration_status(): List pending migrations
   - apply_migrations(database_url): Run all pending
   - rollback_migration(version): Revert to specific version
   - create_revision(message): Generate new migration
   - validate_schema(database_url): Check schema matches models
   
   Usage:
   ```python
   from blog_automation.migrations import apply_migrations
   apply_migrations(settings.database_url)
   ```

F. Auto-Migration on Startup:
   
   In application startup:
   ```python
   from blog_automation.migrations import apply_migrations
   
   def startup():
       apply_migrations(settings.database_url)
       logger.info("Database migrations applied")
   ```

TESTING REQUIREMENTS:

1. Test migration file generation:
   ```python
   def test_initial_migration_exists():
       migrations_dir = Path("migrations/versions")
       migration_files = list(migrations_dir.glob("*_initial*.py"))
       assert len(migration_files) > 0
   ```

2. Test migration applies cleanly:
   ```python
   def test_apply_migrations_test_db():
       # Create fresh test database
       test_db_url = "postgresql://test:test@localhost/test_blog_new"
       
       # Apply migrations
       apply_migrations(test_db_url)
       
       # Verify tables exist
       from sqlalchemy import inspect, create_engine
       engine = create_engine(test_db_url)
       inspector = inspect(engine)
       tables = inspector.get_table_names()
       
       assert "articles" in tables
       assert "content_calendar" in tables
       assert "content_briefs" in tables
   ```

3. Test rollback:
   ```python
   def test_rollback_migration(test_db_url):
       # Apply migrations
       apply_migrations(test_db_url)
       
       # Get current version
       from alembic.config import Config
       config = Config("alembic.ini")
       
       # Rollback one version
       # (test only if you have multiple migrations)
       # rollback_migration(test_db_url, "1")
   ```

4. Test schema validation:
   ```python
   def test_schema_matches_models(test_db_url):
       # After migrations, schema should match ORM models
       from blog_automation.migrations import validate_schema
       
       is_valid = validate_schema(test_db_url)
       assert is_valid is True
   ```

5. Test migration message:
   ```python
   def test_migration_has_message():
       migration_file = Path("migrations/versions/001_initial_schema.py")
       content = migration_file.read_text()
       
       # Should have docstring describing change
       assert "Create articles table" in content or "initial" in content.lower()
   ```

DELIVERABLES:
1. alembic.ini - Alembic configuration
2. migrations/env.py - Migration environment
3. migrations/script.py.mako - Migration template
4. migrations/versions/001_initial_schema.py - Initial migration
5. src/blog_automation/migrations.py - Migration utilities
6. tests/integration/test_migrations.py - Migration tests
7. Documentation on creating new migrations

SUCCESS CRITERIA:
✓ alembic init creates migrations directory
✓ Initial migration generates from models
✓ Migration applies without errors
✓ All tables created with correct columns
✓ Indexes and constraints created
✓ Schema matches ORM models
✓ Migration can be applied and rolled back
✓ Utility functions work correctly
```

---

### PROMPT 6: Base HTTP Client with Retry Logic

```
CONTEXT:
Step 3.1: Base HTTP Client with Retry Logic
Duration: 2 hours
Dependencies: Steps 1.2, 1.3
Deliverable: Production-ready HTTP client used by all API integrations

TASK DESCRIPTION:
Create a robust HTTP client wrapper that handles all the common API
interaction patterns: retries, timeouts, rate limiting, error handling.
This client will be inherited by all specific API clients.

REQUIREMENTS:

A. Base HTTP Client Class (src/blog_automation/integrations/base_client.py):
   
   class HTTPClient:
   
   Constructor:
   - base_url: str
   - timeout: int = 30 (seconds)
   - max_retries: int = 3
   - backoff_factor: float = 2.0
   - headers: dict = {} (default headers)
   
   Configuration:
   - Session management (persistent connections)
   - Custom headers (User-Agent, etc.)
   - Timeout handling per request
   - Rate limit awareness
   
   Methods:
   
   1. get(url, params=None, **kwargs) -> dict:
      - Full URL or path (appended to base_url)
      - Optional query parameters
      - Returns JSON response
      - Handles retries, timeouts, errors
   
   2. post(url, data=None, json=None, **kwargs) -> dict:
      - POST request with form data or JSON
      - Returns JSON response
   
   3. put(url, data=None, json=None, **kwargs) -> dict:
      - PUT request
   
   4. delete(url, **kwargs) -> dict:
      - DELETE request
   
   5. request(method, url, **kwargs) -> dict:
      - Generic request handler
      - All methods use this
      - Error handling and retries
   
   Error Handling:
   - Timeout (> 30 seconds) → Retry with backoff
   - 429 Too Many Requests (rate limit) → Queue retry with Retry-After header
   - 401/403 Unauthorized → Don't retry, raise immediately
   - 5xx Server Error → Retry with backoff
   - Connection error → Retry with backoff
   - Valid response (2xx) → Return parsed JSON
   - Invalid response (4xx not 401/403) → Don't retry, raise

B. Retry Logic (src/blog_automation/integrations/retry.py):
   
   class RetryStrategy:
   
   Configuration:
   - max_attempts: int = 3
   - initial_delay: float = 1.0 (seconds)
   - backoff_factor: float = 2.0
   - max_delay: float = 300.0 (5 minutes max)
   - jitter: bool = True (randomize delay slightly)
   
   Behavior:
   - Attempt 1: Immediate
   - Attempt 2: 1s * 2^1 = 2s
   - Attempt 3: 1s * 2^2 = 4s
   - Attempt 4: 1s * 2^3 = 8s (if max_attempts > 3)
   - Max delay: Never exceeds 300s
   
   Jitter: Add ±10% random variation (prevent thundering herd)
   
   Methods:
   - should_retry(exception, attempt) -> bool
   - get_wait_time(attempt) -> float
   - execute(func, *args, **kwargs) -> result
   
   Retry predicates:
   - Timeout error → Yes
   - Connection error → Yes
   - 429 rate limit → Yes
   - 5xx server error → Yes
   - Other 4xx errors → No
   - 401/403 → No (auth issue, won't fix with retry)

C. Rate Limit Awareness (src/blog_automation/integrations/rate_limit.py):
   
   class RateLimitHandler:
   
   Tracks:
   - Requests per time window
   - Remaining quota
   - Reset times
   
   Methods:
   - check_limit(service: str) -> bool
   - wait_if_limited(service: str) -> None
   - update_limit(service: str, remaining: int, reset_at: datetime) -> None
   
   Integration with response:
   - Parse rate limit headers from response
   - Extract: X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After
   - Store state in memory (Redis optional for multi-process)
   - If limit approaching, insert delay

D. Request/Response Logging (src/blog_automation/integrations/logging.py):
   
   For each request:
   - Log: method, URL (without secrets), status code, duration
   - Log sensitive data: Never log API keys, auth tokens, passwords
   - Log response: Status code, error message if applicable
   
   Format:
   ```
   [INFO] HTTP GET https://api.example.com/search?q=test (200) 1.23s
   [WARNING] HTTP POST https://api.example.com/auth (401) 0.45s - Invalid credentials
   [ERROR] HTTP GET https://api.example.com/data (500) 0.89s - Server error
   ```

E. Response Parsing:
   
   Common patterns:
   - JSON response → parse to dict
   - Streaming response → handle chunks
   - Binary response → save to file
   - Empty response (204) → return None
   - Unexpected content type → raise error

TESTING REQUIREMENTS:

1. Test successful GET request:
   ```python
   def test_http_get(mock_requests):
       mock_requests.get.return_value = Mock(
           status_code=200,
           json=lambda: {"data": "test"}
       )
       
       client = HTTPClient(base_url="https://api.example.com")
       result = client.get("/test")
       
       assert result["data"] == "test"
       mock_requests.get.assert_called_once()
   ```

2. Test retry on timeout:
   ```python
   def test_retry_on_timeout(mock_requests):
       # First 2 attempts timeout, 3rd succeeds
       mock_requests.get.side_effect = [
           Timeout(),
           Timeout(),
           Mock(status_code=200, json=lambda: {"success": True})
       ]
       
       client = HTTPClient(base_url="https://api.example.com", max_retries=3)
       result = client.get("/test")
       
       assert result["success"] is True
       assert mock_requests.get.call_count == 3
   ```

3. Test rate limit handling (429):
   ```python
   def test_rate_limit_retry():
       response = Mock(
           status_code=429,
           headers={"Retry-After": "60"}
       )
       
       with patch('time.sleep') as mock_sleep:
           # Should detect 429 and wait
           with pytest.raises(RateLimitError):
               HTTPClient._handle_response(response)
   ```

4. Test no retry on auth error:
   ```python
   def test_no_retry_on_auth_error(mock_requests):
       mock_requests.get.return_value = Mock(
           status_code=401,
           json=lambda: {"error": "Unauthorized"}
       )
       
       client = HTTPClient(base_url="https://api.example.com")
       
       with pytest.raises(AuthenticationError):
           client.get("/test")
       
       # Should only try once
       assert mock_requests.get.call_count == 1
   ```

5. Test exponential backoff timing:
   ```python
   def test_exponential_backoff_timing():
       strategy = RetryStrategy(
           max_attempts=4,
           initial_delay=1.0,
           backoff_factor=2.0
       )
       
       assert strategy.get_wait_time(1) == pytest.approx(2.0)   # 1 * 2^1
       assert strategy.get_wait_time(2) == pytest.approx(4.0)   # 1 * 2^2
       assert strategy.get_wait_time(3) == pytest.approx(8.0)   # 1 * 2^3
   ```

6. Test request logging (no secrets):
   ```python
   def test_request_logging_no_secrets(caplog):
       client = HTTPClient(base_url="https://api.example.com")
       client.default_headers = {"Authorization": "Bearer secret-key"}
       
       with patch('requests.get') as mock:
           mock.return_value = Mock(status_code=200, json=lambda: {})
           client.get("/test")
       
       log_output = caplog.text
       assert "secret-key" not in log_output
       assert "/test" in log_output
       assert "200" in log_output
   ```

7. Test rate limit tracking:
   ```python
   def test_rate_limit_tracking():
       handler = RateLimitHandler()
       
       # Service has 100 requests left
       handler.update_limit("ahrefs", remaining=100, reset_at=datetime.utcnow() + timedelta(hours=1))
       assert handler.check_limit("ahrefs") is True
       
       # Service has 0 requests left
       handler.update_limit("ahrefs", remaining=0, reset_at=datetime.utcnow() + timedelta(minutes=30))
       assert handler.check_limit("ahrefs") is False
   ```

DELIVERABLES:
1. src/blog_automation/integrations/base_client.py - HTTPClient class
2. src/blog_automation/integrations/retry.py - RetryStrategy class
3. src/blog_automation/integrations/rate_limit.py - RateLimitHandler class
4. tests/unit/test_http_client.py - HTTP client tests
5. tests/unit/test_retry_logic.py - Retry strategy tests
6. Documentation on extending HTTPClient

SUCCESS CRITERIA:
✓ GET/POST/PUT/DELETE methods work
✓ Retries on timeout with exponential backoff
✓ No retries on 401/403
✓ Rate limits respected
✓ Response logging doesn't expose secrets
✓ Jitter prevents thundering herd
✓ All tests pass with high coverage
✓ Client is thread-safe
✓ No hanging connections
```

---

### PROMPT 7: Ahrefs API Client

```
CONTEXT:
Step 3.2: Ahrefs API Client
Duration: 2 hours
Dependencies: Steps 3.1
Deliverable: Complete Ahrefs integration for keyword research

TASK DESCRIPTION:
Create a complete Ahrefs API client for keyword research and competitor analysis.
This client will be used by the keyword research pipeline to gather initial data
about keywords.

REQUIREMENTS:

A. Ahrefs Client Class (src/blog_automation/integrations/ahrefs_client.py):
   
   class AhrefsClient(HTTPClient):
   
   Constructor:
   - api_key: str (from settings)
   - max_results_per_query: int = 10 (for competitor analysis)
   
   Inherits from HTTPClient:
   - Uses base retry logic
   - Uses base error handling
   - Uses base logging
   
   Authentication:
   - Include API key in Authorization header
   - Or as URL parameter (check Ahrefs docs)
   - Test authentication on initialization

B. Methods:
   
   1. search_volume(keyword: str) -> dict:
      Endpoint: /keywords/search-volume
      Input: keyword (string)
      Returns:
      {
        "keyword": "python asyncio",
        "search_volume": 2400,
        "clicks_per_search": 0.45,
        "global_volume": 2800,
        "cpc": 0.85  # Cost per click
      }
      
      Error handling:
      - Keyword too short → raise InvalidKeywordError
      - No data for keyword → return default structure with 0 values
      - API error → retry or raise
   
   2. keyword_difficulty(keyword: str) -> dict:
      Endpoint: /keywords/difficulty
      Input: keyword
      Returns:
      {
        "keyword": "python asyncio",
        "difficulty": 32,  # 0-100 scale
        "difficulty_label": "easy"
      }
      
      Difficulty scale:
      - 0-20: Very Easy
      - 21-40: Easy
      - 41-60: Medium
      - 61-80: Hard
      - 81-100: Very Hard
   
   3. serp_features(keyword: str) -> dict:
      Endpoint: /serp/features
      Input: keyword
      Returns:
      {
        "keyword": "python asyncio",
        "features": {
          "featured_snippet": True,
          "people_also_ask": True,
          "knowledge_panel": False,
          "image_pack": False,
          "video_pack": True
        },
        "snippet_text": "Python asyncio...",
        "top_10_urls": [
          {
            "position": 1,
            "url": "https://...",
            "title": "...",
            "snippet": "..."
          },
          ...
        ]
      }
   
   4. top_pages(keyword: str, limit: int = 10) -> List[dict]:
      Endpoint: /serp/top-results (or similar)
      Input: keyword, limit (default 10)
      Returns list of top SERP results:
      [
        {
          "position": 1,
          "url": "https://python.org/docs/asyncio",
          "title": "asyncio - asynchronous I/O",
          "snippet": "...",
          "domain": "python.org",
          "word_count": 3500,
          "backlinks": 12500,
          "referring_domains": 450
        },
        ...
      ]
   
   5. competitor_analysis(keyword: str, limit: int = 5) -> dict:
      Endpoint: Uses top_pages internally
      Input: keyword, limit (default 5)
      Returns aggregated analysis:
      {
        "keyword": "python asyncio",
        "average_word_count": 2500,
        "average_backlinks": 8500,
        "average_referring_domains": 300,
        "most_common_word_count": 2000,
        "min_word_count": 1500,
        "max_word_count": 4000,
        "h2_pattern": ["What is...", "How to...", "Best Practices"],
        "recommended_structure": "definition -> examples -> best practices -> faq"
      }
      
      This analyzes top competitors to inform content strategy
   
   6. keyword_difficulty_batch(keywords: List[str]) -> List[dict]:
      Input: list of keywords
      Returns: list of difficulty scores
      
      Optimization:
      - Batch API calls if supported
      - Or loop with rate limit awareness

C. Caching Layer:
   
   Implement caching for expensive/stable queries:
   - Cache search volume for 30 days (doesn't change often)
   - Cache difficulty for 30 days
   - Cache SERP features for 7 days (changes more often)
   - Cache top pages for 3 days
   
   Cache storage:
   - Simple: JSON files in cache/ directory
   - Better: Redis if available
   - Cache key: f"ahrefs_{method}_{keyword_hash}"
   
   Methods:
   - get_cached(key) -> dict or None
   - set_cache(key, value, ttl_hours) -> None
   - clear_cache(older_than_hours=None) -> None

D. Error Handling:
   
   Custom exceptions:
   - AhrefsAPIError (base)
   - AhrefsAuthError (401)
   - AhrefsQuotaError (quota exceeded)
   - AhrefsInvalidKeywordError (keyword rejected)
   
   Specific error codes:
   - 401: Invalid API key → raise AhrefsAuthError
   - 429: Rate limited → retry with backoff
   - Keyword validation errors → raise AhrefsInvalidKeywordError
   - 5xx: Server error → retry

E. Usage Example:
   
   ```python
   from blog_automation.integrations import AhrefsClient
   from blog_automation.config import get_settings
   
   settings = get_settings()
   ahrefs = AhrefsClient(api_key=settings.ahrefs_api_key)
   
   # Get keyword data
   volume = ahrefs.search_volume("python asyncio")
   difficulty = ahrefs.keyword_difficulty("python asyncio")
   features = ahrefs.serp_features("python asyncio")
   competitors = ahrefs.competitor_analysis("python asyncio", limit=5)
   
   # Batch operations
   keywords = ["python", "asyncio", "concurrency"]
   difficulties = ahrefs.keyword_difficulty_batch(keywords)
   ```

TESTING REQUIREMENTS:

1. Test successful keyword metrics:
   ```python
   def test_search_volume(ahrefs_client, mock_requests):
       mock_requests.get.return_value = Mock(
           status_code=200,
           json=lambda: {
               "keyword": "python asyncio",
               "search_volume": 2400
           }
       )
       
       result = ahrefs_client.search_volume("python asyncio")
       assert result["search_volume"] == 2400
   ```

2. Test difficulty scoring:
   ```python
   def test_keyword_difficulty(ahrefs_client, mock_requests):
       mock_requests.get.return_value = Mock(
           status_code=200,
           json=lambda: {
               "keyword": "python asyncio",
               "difficulty": 32
           }
       )
       
       result = ahrefs_client.keyword_difficulty("python asyncio")
       assert result["difficulty"] == 32
   ```

3. Test SERP features:
   ```python
   def test_serp_features(ahrefs_client, mock_requests):
       mock_requests.get.return_value = Mock(
           status_code=200,
           json=lambda: {
               "keyword": "python asyncio",
               "features": {"featured_snippet": True}
           }
       )
       
       result = ahrefs_client.serp_features("python asyncio")
       assert result["features"]["featured_snippet"] is True
   ```

4. Test caching:
   ```python
   def test_search_volume_caching(ahrefs_client, mock_requests):
       mock_requests.get.return_value = Mock(
           status_code=200,
           json=lambda: {"search_volume": 2400}
       )
       
       # First call hits API
       result1 = ahrefs_client.search_volume("python asyncio")
       assert mock_requests.get.call_count == 1
       
       # Second call uses cache
       result2 = ahrefs_client.search_volume("python asyncio")
       assert mock_requests.get.call_count == 1  # No additional call
       assert result1 == result2
   ```

5. Test invalid keyword error:
   ```python
   def test_invalid_keyword(ahrefs_client, mock_requests):
       mock_requests.get.return_value = Mock(
           status_code=400,
           json=lambda: {"error": "Invalid keyword"}
       )
       
       with pytest.raises(AhrefsInvalidKeywordError):
           ahrefs_client.search_volume("@#$%")
   ```

6. Test batch operations:
   ```python
   def test_difficulty_batch(ahrefs_client, mock_requests):
       keywords = ["python", "asyncio", "concurrency"]
       mock_requests.post.return_value = Mock(
           status_code=200,
           json=lambda: {
               "results": [
                   {"keyword": "python", "difficulty": 48},
                   {"keyword": "asyncio", "difficulty": 35},
                   {"keyword": "concurrency", "difficulty": 52}
               ]
           }
       )
       
       results = ahrefs_client.keyword_difficulty_batch(keywords)
       assert len(results) == 3
   ```

7. Test competitor analysis structure:
   ```python
   def test_competitor_analysis(ahrefs_client, mock_requests):
       # Mock top pages response
       mock_requests.get.return_value = Mock(
           status_code=200,
           json=lambda: {
               "results": [
                   {"url": "...", "word_count": 2500, "backlinks": 8000},
                   {"url": "...", "word_count": 2300, "backlinks": 9000}
               ]
           }
       )
       
       result = ahrefs_client.competitor_analysis("python asyncio", limit=2)
       assert result["average_word_count"] > 0
       assert "recommended_structure" in result
   ```

DELIVERABLES:
1. src/blog_automation/integrations/ahrefs_client.py - Ahrefs client
2. src/blog_automation/integrations/cache.py - Caching utilities
3. tests/unit/test_ahrefs_client.py - Ahrefs tests
4. Documentation on Ahrefs API methods

SUCCESS CRITERIA:
✓ All methods return correct structure
✓ Caching works correctly
✓ Rate limiting respected
✓ Error handling for invalid keywords
✓ Batch operations work
✓ All tests pass
✓ No API key exposed in logs
```

---

### PROMPT 8: OpenAI API Client

```
CONTEXT:
Step 3.3: OpenAI API Client
Duration: 2 hours
Dependencies: Steps 3.1
Deliverable: Complete OpenAI integration for content generation

TASK DESCRIPTION:
Create a wrapper around OpenAI's API for GPT-4 Turbo model. This will be
used for content drafting, meta tag generation, and other language tasks.

REQUIREMENTS:

A. OpenAI Client Class (src/blog_automation/integrations/openai_client.py):
   
   class OpenAIClient(HTTPClient):
   
   Constructor:
   - api_key: str (from settings)
   - organization_id: str (optional, from settings)
   - default_model: str = "gpt-4-turbo-preview"
   
   Authentication:
   - Use official OpenAI Python library: from openai import OpenAI
   - Or implement HTTP wrapper following OpenAI API spec
   - Include API key in Authorization header

B. Models & Pricing:
   
   Supported models:
   - gpt-4-turbo-preview (fast, $0.01 input / $0.03 output per 1K)
   - gpt-4 (slow, $0.03 input / $0.06 output per 1K)
   - gpt-3.5-turbo (cheapest, $0.0005 input / $0.0015 output per 1K)
   
   Selection logic:
   - Content generation → gpt-4-turbo-preview (best quality/cost balance)
   - Quick summaries → gpt-3.5-turbo (faster, cheaper)
   - Complex reasoning → gpt-4 (slower, better reasoning)

C. Methods:
   
   1. complete(prompt: str, model: str = None, **kwargs) -> str:
      Input:
      - prompt: Full prompt text
      - model: Override default model
      - temperature: 0.0-1.0 (default varies by use case)
      - max_tokens: Max output tokens (default 2000)
      - top_p: 0.0-1.0 nucleus sampling
      
      Returns:
      - response_text: str (the generated text)
      
      Handles:
      - Streaming responses
      - Token limits
      - Error handling
      - Cost tracking
      
      Example:
      ```python
      response = client.complete(
          prompt="Write a blog post about...",
          temperature=0.7,
          max_tokens=2000
      )
      ```
   
   2. chat_complete(messages: List[dict], model: str = None, **kwargs) -> str:
      Input:
      - messages: List of {"role": "user|assistant|system", "content": "..."}
      - model: Override default
      - temperature: 0.7 for balance
      - max_tokens: Default 2000
      
      Returns:
      - response_text: str
      
      Example:
      ```python
      messages = [
          {"role": "system", "content": "You are a professional writer..."},
          {"role": "user", "content": "Write a blog post about..."}
      ]
      response = client.chat_complete(messages)
      ```
   
   3. count_tokens(text: str, model: str = None) -> int:
      Input: Text to count
      Returns: Number of tokens
      
      Uses: tiktoken library for accurate counting
      
      Purpose: Estimate costs, validate input within limits
      
      Example:
      ```python
      tokens = client.count_tokens("This is a test")
      cost = (tokens / 1000) * 0.01  # Cost for gpt-4-turbo
      ```
   
   4. estimate_cost(input_tokens: int, output_tokens: int, model: str = None) -> float:
      Input: Input and output token counts
      Returns: Cost in USD
      
      Pricing per model:
      - gpt-4-turbo: $0.01/$0.03 per 1K
      - gpt-4: $0.03/$0.06 per 1K
      - gpt-3.5-turbo: $0.0005/$0.0015 per 1K

D. Streaming Support:
   
   For long generations, support streaming:
   
   ```python
   response = client.complete_streaming(
       prompt="...",
       model="gpt-4-turbo-preview"
   )
   
   # Returns iterator
   for chunk in response:
       print(chunk)  # Print as it arrives
   ```

E. Token Management:
   
   Utilities:
   - MAX_TOKENS: 8000 for gpt-4-turbo
   - SAFE_MAX: 7000 (leave 1000 for response)
   - Calculate remaining tokens: remaining = SAFE_MAX - prompt_tokens
   
   Validation:
   - If prompt_tokens > SAFE_MAX → raise error
   - If remaining < 500 → warn and suggest truncating prompt

F. Cost Tracking (src/blog_automation/integrations/cost_tracker.py):
   
   Track all API usage for cost management:
   
   ```python
   tracker = CostTracker()
   
   # Log each API call
   tracker.log_request(
       service="openai",
       model="gpt-4-turbo",
       input_tokens=1000,
       output_tokens=2000,
       cost=0.07
   )
   
   # Query costs
   daily_cost = tracker.get_daily_cost("2024-01-15")
   monthly_cost = tracker.get_monthly_cost("2024-01")
   model_cost = tracker.get_cost_by_model("gpt-4-turbo")
   ```
   
   Storage: SQLite or simple JSON file

G. Error Handling:
   
   Custom exceptions:
   - OpenAIError (base)
   - OpenAIAuthError (401)
   - OpenAIRateLimitError (429, with Retry-After)
   - OpenAITokenLimitError (exceeds max tokens)
   - OpenAIServerError (5xx)
   
   Specific handling:
   - Rate limit → retry after Retry-After header
   - Token limit → truncate prompt and retry
   - Server error → retry with backoff

H. System Prompts (src/blog_automation/integrations/prompts.py):
   
   Predefined system prompts for common tasks:
   
   ```python
   CONTENT_GENERATION_PROMPT = """
   You are a professional blog writer specializing in technical content.
   
   Guidelines:
   - Write in a conversational, accessible tone
   - Include real-world examples
   - Avoid keyword stuffing
   - Use short paragraphs (2-3 sentences max)
   - Include actionable advice
   
   Requirements:
   - Keyword appears 3-5 times naturally
   - No obvious AI patterns
   - Cite credible sources
   - Include internal links to related topics
   """
   
   OUTLINE_GENERATION_PROMPT = """
   Create a detailed outline for a blog post about {topic}.
   
   Requirements:
   - H1: Main title
   - 4-5 main H2 sections
   - 2-3 H3 subsections per H2
   - Include FAQ section
   - Estimated word count
   """
   ```

TESTING REQUIREMENTS:

1. Test completion:
   ```python
   def test_complete(openai_client, mock_openai):
       mock_openai.ChatCompletion.create.return_value = Mock(
           choices=[Mock(message=Mock(content="Generated text"))]
       )
       
       result = openai_client.complete(
           prompt="Write about...",
           temperature=0.7
       )
       
       assert "Generated" in result
   ```

2. Test token counting:
   ```python
   def test_count_tokens(openai_client):
       count = openai_client.count_tokens("This is a test prompt")
       assert isinstance(count, int)
       assert count > 0
       assert count < 20  # This short text should be <20 tokens
   ```

3. Test cost estimation:
   ```python
   def test_estimate_cost(openai_client):
       cost = openai_client.estimate_cost(
           input_tokens=1000,
           output_tokens=2000,
           model="gpt-4-turbo-preview"
       )
       
       # gpt-4-turbo: 1000*0.01 + 2000*0.03 = 70 cents = $0.70
       assert cost == pytest.approx(0.70)
   ```

4. Test token limit validation:
   ```python
   def test_token_limit_validation(openai_client):
       # Very long prompt
       long_prompt = "word " * 10000  # ~10k tokens
       
       with pytest.raises(OpenAITokenLimitError):
           openai_client.complete(long_prompt)
   ```

5. Test rate limit retry:
   ```python
   def test_rate_limit_retry(openai_client, mock_openai):
       mock_openai.ChatCompletion.create.side_effect = [
           Exception("429 Too Many Requests"),
           Mock(choices=[Mock(message=Mock(content="Success"))])
       ]
       
       # Should retry after handling 429
       result = openai_client.complete("test")
       assert "Success" in result
   ```

6. Test streaming:
   ```python
   def test_streaming_response(openai_client, mock_openai):
       # Mock streaming chunks
       chunks = [
           Mock(choices=[Mock(delta=Mock(content="chunk1"))]),
           Mock(choices=[Mock(delta=Mock(content="chunk2"))]),
       ]
       mock_openai.ChatCompletion.create.return_value = iter(chunks)
       
       result = openai_client.complete_streaming("test")
       text = "".join(result)
       assert "chunk1chunk2" in text
   ```

7. Test cost tracking:
   ```python
   def test_cost_tracker():
       tracker = CostTracker()
       
       tracker.log_request(
           service="openai",
           model="gpt-4-turbo",
           input_tokens=1000,
           output_tokens=2000,
           cost=0.07
       )
       
       daily_cost = tracker.get_daily_cost(datetime.now().date())
       assert daily_cost == pytest.approx(0.07)
   ```

DELIVERABLES:
1. src/blog_automation/integrations/openai_client.py - OpenAI client
2. src/blog_automation/integrations/prompts.py - System prompts
3. src/blog_automation/integrations/cost_tracker.py - Cost tracking
4. tests/unit/test_openai_client.py - OpenAI client tests
5. Documentation on available models and pricing

SUCCESS CRITERIA:
✓ Completion works with different models
✓ Token counting is accurate
✓ Cost estimation is correct
✓ Rate limiting is respected
✓ Streaming works correctly
✓ Token limits validated
✓ Cost tracking works
✓ All tests pass
✓ No API key exposed in logs
```

---

### PROMPT 9: Claude (Anthropic) API Client

```
CONTEXT:
Step 3.4: Claude (Anthropic) API Client
Duration: 1.5 hours
Dependencies: Steps 3.1
Deliverable: Complete Claude API integration for fact-checking

TASK DESCRIPTION:
Create a wrapper around Anthropic's Claude API. This will be used primarily
for claim extraction and verification tasks (better reasoning than GPT-4).

REQUIREMENTS:

A. Claude Client Class (src/blog_automation/integrations/claude_client.py):
   
   class ClaudeClient(HTTPClient):
   
   Constructor:
   - api_key: str (from settings)
   - default_model: str = "claude-3-sonnet-20240229"
   
   Supported models:
   - claude-3-opus: Best intelligence, slower, more expensive
   - claude-3-sonnet: Balance of speed and intelligence
   - claude-3-haiku: Fastest and cheapest
   
   Model selection strategy:
   - Fact checking (complex reasoning) → opus
   - Claim extraction (structured output) → sonnet
   - Quick summaries → haiku

B. Methods:
   
   1. message(prompt: str, model: str = None, **kwargs) -> str:
      Uses Claude messages API
      Input:
      - prompt: str
      - model: Override default
      - max_tokens: 2000 (default)
      - temperature: 0.5 (more deterministic than GPT)
      
      Returns: Response text
      
      Includes:
      - Prompt caching (Claude feature for cost savings)
      - Stop sequences
      - Token counting
   
   2. extract_json(prompt: str, model: str = None) -> dict:
      Special method for structured extraction
      Input:
      - prompt: Must end with "Return valid JSON only"
      - model: Default to sonnet
      
      Returns: Parsed JSON dict
      
      Handles:
      - Partial JSON responses
      - Extraction of JSON from markdown blocks
      - Validation of returned structure
      
      Example:
      ```python
      prompt = """Extract claims from this text as JSON:
      {article_text}
      
      Return valid JSON only: {
        "claims": [
          {"claim": "...", "confidence": "high"}
        ]
      }"""
      
      result = client.extract_json(prompt)
      ```
   
   3. count_tokens(text: str, model: str = None) -> int:
      Uses Claude's token counting API
      Returns: Number of tokens
   
   4. estimate_cost(input_tokens: int, output_tokens: int, model: str = None) -> float:
      Pricing:
      - opus: $15/$45 per 1M tokens
      - sonnet: $3/$15 per 1M tokens
      - haiku: $0.80/$4 per 1M tokens

C. Prompt Caching (Claude Feature):
   
   Claude supports caching prompts to save costs:
   
   ```python
   # Large system prompt or context gets cached
   system_prompt = """
   You are a fact-checking expert...
   [Long context that won't change]
   """
   
   response = client.message(
       prompt="Verify this claim: ...",
       system_prompt=system_prompt,
       use_cache=True  # Reuse cache if available
   )
   
   # Cost savings: cached tokens cost 90% less
   ```

D. Error Handling:
   
   Custom exceptions:
   - ClaudeError (base)
   - ClaudeAuthError (401)
   - ClaudeOverloadError (529 - model overloaded)
   - ClaudeInvalidRequestError (400)
   
   Specific handling:
   - 529 overloaded → retry with longer backoff
   - 400 invalid → don't retry, fix prompt
   - Other 5xx → retry with backoff

E. System Prompts for Fact-Checking (src/blog_automation/integrations/fact_check_prompts.py):
   
   ```python
   CLAIM_EXTRACTION_PROMPT = """
   You are a fact-checking expert. Extract atomic, verifiable claims from the following article.
   
   Return ONLY valid JSON with this structure:
   {
     "claims": [
       {
         "claim": "Exact claim from article",
         "type": "historical|statistic|technical|definition",
         "confidence": "high|medium|low",
         "line_number": 45
       }
     ]
   }
   
   Article:
   {article}
   """
   
   CLAIM_VERIFICATION_PROMPT = """
   You are a fact-checker. Verify if the following claim is supported by the evidence.
   
   Claim: {claim}
   
   Evidence:
   {evidence}
   
   Return ONLY valid JSON:
   {
     "verdict": "supported|contradicted|unclear",
     "confidence": 0-100,
     "explanation": "...",
     "suggested_revision": "..." (if needed)
   }
   """
   ```

TESTING REQUIREMENTS:

1. Test message generation:
   ```python
   def test_message(claude_client, mock_claude):
       mock_claude.messages.create.return_value = Mock(
           content=[Mock(text="Response text")]
       )
       
       result = claude_client.message("Test prompt")
       assert "Response" in result
   ```

2. Test JSON extraction:
   ```python
   def test_extract_json(claude_client, mock_claude):
       mock_claude.messages.create.return_value = Mock(
           content=[Mock(text='{"claims": [{"claim": "test", "confidence": "high"}]}')]
       )
       
       result = claude_client.extract_json("Extract claims: ...")
       assert "claims" in result
       assert len(result["claims"]) > 0
   ```

3. Test model selection:
   ```python
   def test_model_selection(claude_client):
       # Fact checking should use opus
       model = claude_client._select_model("fact_checking")
       assert "opus" in model
       
       # Quick summary should use haiku
       model = claude_client._select_model("summary")
       assert "haiku" in model
   ```

4. Test token counting:
   ```python
   def test_token_counting(claude_client):
       tokens = claude_client.count_tokens("Test text")
       assert isinstance(tokens, int)
       assert tokens > 0
   ```

5. Test cost estimation:
   ```python
   def test_cost_estimation(claude_client):
       # Sonnet: $3 per 1M input tokens
       cost = claude_client.estimate_cost(
           input_tokens=1_000_000,
           output_tokens=0,
           model="claude-3-sonnet-20240229"
       )
       assert cost == pytest.approx(3.0)
   ```

6. Test overload handling:
   ```python
   def test_overload_retry(claude_client, mock_claude):
       mock_claude.messages.create.side_effect = [
           Exception("529 Model overloaded"),
           Mock(content=[Mock(text="Success")])
       ]
       
       result = claude_client.message("test")
       assert "Success" in result
       assert mock_claude.messages.create.call_count >= 2
   ```

7. Test prompt caching:
   ```python
   def test_prompt_caching(claude_client, mock_claude):
       system_prompt = "Long system prompt..." * 100
       
       # First call caches
       claude_client.message(
           "Question 1",
           system_prompt=system_prompt,
           use_cache=True
       )
       
       # Second call uses cache
       claude_client.message(
           "Question 2",
           system_prompt=system_prompt,
           use_cache=True
       )
       
       # Should have cheaper tokens on second call due to caching
   ```

DELIVERABLES:
1. src/blog_automation/integrations/claude_client.py - Claude client
2. src/blog_automation/integrations/fact_check_prompts.py - Fact-checking prompts
3. tests/unit/test_claude_client.py - Claude client tests
4. Documentation on Claude models and prompt caching

SUCCESS CRITERIA:
✓ Message API works correctly
✓ JSON extraction parses responses correctly
✓ Token counting is accurate
✓ Cost estimation is correct
✓ Prompt caching works
✓ Model selection logic works
✓ Overload handling works
✓ All tests pass
✓ No API key exposed in logs
```

---

### PROMPT 10: Perplexity & Supporting API Clients

```
CONTEXT:
Step 3.5: Perplexity API Client + Step 3.6: Supporting API Clients
Duration: 1.5 hours each (3 hours total)
Dependencies: Steps 3.1
Deliverables: Web search, plagiarism detection, SEO analysis clients

TASK DESCRIPTION:
Create clients for remaining APIs: Perplexity (web search), Copyscape (plagiarism),
Rank Math (SEO), WordPress (publishing), and Google APIs (analytics/GSC).

REQUIREMENTS:

A. Perplexity API Client (src/blog_automation/integrations/perplexity_client.py):
   
   class PerplexityClient(HTTPClient):
   
   Purpose: Search the web for evidence to fact-check claims
   
   Method:
   
   search(query: str, source_count: int = 5) -> dict:
   Input:
   - query: Search query string
   - source_count: Number of sources to return
   
   Returns:
   {
     "query": "search query",
     "answer": "Perplexity's synthesized answer",
     "sources": [
       {
         "title": "Source title",
         "url": "https://...",
         "snippet": "Relevant excerpt"
       },
       ...
     ]
   }
   
   Error handling:
   - Rate limiting: Respect API limits
   - Invalid query: Return empty results
   - API error: Retry with backoff

B. Copyscape API Client (src/blog_automation/integrations/copyscape_client.py):
   
   class CopyscapeClient(HTTPClient):
   
   Purpose: Check article for plagiarism
   
   Method:
   
   check_plagiarism(content: str) -> dict:
   Input:
   - content: Article text to check
   
   Returns:
   {
     "plagiarism_percent": 2.5,  # 0-100
     "matches": [
       {
         "url": "https://...",
         "matched_text": "...",
         "percent_matched": 15.0
       }
     ]
   }
   
   Threshold: Accept <3% plagiarism

C. Rank Math API Client (src/blog_automation/integrations/rankmath_client.py):
   
   class RankMathClient(HTTPClient):
   
   Purpose: SEO analysis and scoring
   
   Method:
   
   analyze_content(content: str, keyword: str) -> dict:
   Input:
   - content: Article HTML or text
   - keyword: Target keyword
   
   Returns:
   {
     "score": 75,  # 0-100 SEO score
     "analysis": {
       "keyword_placement": "good",
       "content_length": "optimal",
       "readability": "good",
       "links": "good",
       "images": "good"
     },
     "issues": [
       "Keyword not in first 100 words",
       "No internal links"
     ],
     "suggestions": [
       "Add keyword to intro",
       "Link to 3-5 related posts"
     ]
   }

D. WordPress REST API Client (src/blog_automation/integrations/wordpress_client.py):
   
   class WordPressClient(HTTPClient):
   
   Authentication:
   - Use app-specific passwords (not main password)
   - Basic auth: Authorization: Basic base64(user:password)
   
   Methods:
   
   1. create_post(data: dict) -> dict:
      Input:
      {
        "title": "Post title",
        "content": "<p>HTML content</p>",
        "excerpt": "Post excerpt",
        "status": "draft" or "publish" or "future",
        "date": "2024-01-15T08:00:00Z",  # For scheduling
        "categories": [5, 10],  # Category IDs
        "tags": [15, 20],  # Tag IDs
        "featured_media": 1234  # Featured image attachment ID
      }
      
      Returns:
      {
        "id": 123,
        "link": "https://yourblog.com/post-title/",
        "date": "...",
        "status": "draft"
      }
   
   2. upload_media(file_path: str, title: str) -> dict:
      Input:
      - file_path: Path to image
      - title: Image title for media library
      
      Returns:
      {
        "id": 1234,  # Attachment ID
        "source_url": "https://yourblog.com/wp-content/uploads/..."
      }
   
   3. update_post_meta(post_id: int, meta_key: str, meta_value: any) -> bool:
      For ACF custom fields
   
   4. get_post(post_id: int) -> dict:
      Retrieve existing post data
   
   5. update_post(post_id: int, data: dict) -> dict:
      Update existing post

E. Google Analytics API Client (src/blog_automation/integrations/google_analytics_client.py):
   
   class GoogleAnalyticsClient(HTTPClient):
   
   Purpose: Track article performance
   
   Setup:
   - Create service account
   - Grant access to GA4 property
   - Store credentials in settings
   
   Method:
   
   get_metrics(article_url: str, days: int = 30) -> dict:
   Input:
   - article_url: Full URL of published article
   - days: Days of historical data
   
   Returns:
   {
     "page_views": 150,
     "avg_session_duration": 2.5,  # Minutes
     "bounce_rate": 45.0,  # Percentage
     "users": 100,
     "engagements": 75
   }

F. Google Search Console API Client (src/blog_automation/integrations/gsc_client.py):
   
   class SearchConsoleClient(HTTPClient):
   
   Purpose: Get keyword rankings and CTR
   
   Method:
   
   get_search_metrics(article_url: str, days: int = 90) -> dict:
   Input:
   - article_url: Full URL of article
   - days: Historical data (default 90)
   
   Returns:
   {
     "queries": [
       {
         "query": "python asyncio tutorial",
         "impressions": 500,
         "clicks": 50,
         "ctr": 10.0,  # Percentage
         "average_position": 3.5
       },
       ...
     ],
     "total_impressions": 1500,
     "total_clicks": 150,
     "avg_ctr": 10.0,
     "avg_position": 4.2
   }

TESTING REQUIREMENTS:

1. Perplexity search:
   ```python
   def test_perplexity_search(perplexity_client, mock_requests):
       mock_requests.post.return_value = Mock(
           status_code=200,
           json=lambda: {
               "answer": "Evidence text",
               "sources": [{"url": "https://...", "title": "Source"}]
           }
       )
       
       result = perplexity_client.search("test claim")
       assert "sources" in result
       assert len(result["sources"]) > 0
   ```

2. Copyscape plagiarism check:
   ```python
   def test_plagiarism_check(copyscape_client, mock_requests):
       mock_requests.post.return_value = Mock(
           status_code=200,
           json=lambda: {
               "plagiarism_percent": 2.1,
               "matches": []
           }
       )
       
       result = copyscape_client.check_plagiarism("Article content")
       assert result["plagiarism_percent"] < 3.0
   ```

3. Rank Math SEO analysis:
   ```python
   def test_seo_analysis(rankmath_client, mock_requests):
       mock_requests.post.return_value = Mock(
           status_code=200,
           json=lambda: {
               "score": 78,
               "issues": ["Keyword not in title"]
           }
       )
       
       result = rankmath_client.analyze_content("Article", "keyword")
       assert result["score"] > 50
   ```

4. WordPress post creation:
   ```python
   def test_create_wordpress_post(wordpress_client, mock_requests):
       mock_requests.post.return_value = Mock(
           status_code=201,
           json=lambda: {
               "id": 123,
               "link": "https://blog.com/post/"
           }
       )
       
       result = wordpress_client.create_post({
           "title": "Test Post",
           "content": "<p>Content</p>"
       })
       assert result["id"] == 123
   ```

5. Google Analytics metrics:
   ```python
   def test_ga_metrics(ga_client, mock_requests):
       mock_requests.post.return_value = Mock(
           status_code=200,
           json=lambda: {
               "rows": [[150, 2.5, 45.0]]
           }
       )
       
       result = ga_client.get_metrics("https://blog.com/post/")
       assert result["page_views"] > 0
   ```

DELIVERABLES:
1. src/blog_automation/integrations/perplexity_client.py
2. src/blog_automation/integrations/copyscape_client.py
3. src/blog_automation/integrations/rankmath_client.py
4. src/blog_automation/integrations/wordpress_client.py
5. src/blog_automation/integrations/google_analytics_client.py
6. src/blog_automation/integrations/gsc_client.py
7. tests/unit/test_supporting_clients.py

SUCCESS CRITERIA:
✓ All clients work with their respective APIs
✓ Error handling for each API
✓ Rate limiting respected
✓ All tests pass
```

---

### PROMPT 11: Keyword Research Pipeline (First Business Logic)

```
CONTEXT:
Step 4.1: Keyword Research Pipeline
Duration: 2 hours
Dependencies: Steps 1.1-3.6 (all foundation work)
Deliverable: Working end-to-end keyword research → ContentBrief storage

TASK DESCRIPTION:
This is the first complete business logic pipeline. It takes a keyword from
the content calendar and executes the full research flow, storing results.

REQUIREMENTS:

A. Pipeline Function (src/blog_automation/pipelines/keyword_research.py):
   
   ```python
   def research_keyword(keyword: str, article_id: int = None) -> ContentBrief:
       """
       Complete keyword research pipeline.
       
       Input: keyword (str)
       Output: ContentBrief object saved to database
       
       Steps:
       1. Validate keyword
       2. Fetch from Ahrefs (search volume, difficulty, intent)
       3. Analyze SERP features
       4. Analyze competitor content
       5. Create ContentBrief structure
       6. Validate brief completeness
       7. Save to database
       8. Return brief
       """
   ```

B. Detailed Steps:
   
   Step 1: Validate Input
   - Keyword not empty
   - Keyword length 2-100 characters
   - No special characters
   - Log validation
   
   Step 2: Fetch Ahrefs Data
   - Call ahrefs.search_volume(keyword)
   - Call ahrefs.keyword_difficulty(keyword)
   - Call ahrefs.serp_features(keyword)
   - Handle API errors with retry logic
   - Log results
   
   Step 3: Competitor Analysis
   - Call ahrefs.top_pages(keyword, limit=10)
   - Calculate average metrics:
     - word_count
     - readability_score
     - backlinks
     - referring_domains
   - Extract H2 patterns
   - Recommend article structure
   
   Step 4: Create Brief Structure
   ```python
   brief_data = {
       "keyword": keyword,
       "search_volume": metrics["volume"],
       "difficulty": metrics["difficulty"],
       "intent": metrics["intent"],
       "estimated_traffic_potential": volume * (100 - difficulty) / 100,
       "target_audience": generate_audience_description(keyword),
       "recommended_sections": [
           "Introduction (with keyword definition)",
           "Benefits & Use Cases",
           "How-to or Tutorial",
           "Best Practices",
           "Common Mistakes",
           "FAQ"
       ],
       "target_word_count": recommend_word_count(difficulty),
       "internal_links_to_create": 5,
       "external_sources_minimum": 10,
       "unique_angle": generate_unique_angle(keyword, competitors),
       "competitor_analysis": {
           "avg_word_count": 2500,
           "avg_backlinks": 8000,
           "h2_patterns": ["How to", "Best", "vs"],
           "recommended_structure": "..."
       },
       "seo_targets": {
           "keyword_density": "0.5-1.5%",
           "internal_links": "3-5",
           "external_links": "5-10",
           "meta_title_length": "50-60",
           "meta_description_length": "150-160"
       }
   }
   ```
   
   Step 5: Validate Brief
   - Has minimum 5 external sources identified
   - Has 4+ section recommendations
   - Has target audience defined
   - Has unique angle
   - If validation fails → log error → return None
   
   Step 6: Save to Database
   ```python
   brief = ContentBrief(
       keyword=keyword,
       search_volume=metrics["volume"],
       difficulty=metrics["difficulty"],
       intent=metrics["intent"],
       brief_data=brief_data,
       article_id=article_id  # Optional, link to article if provided
   )
   session.add(brief)
   session.commit()
   return brief
   ```
   
   Step 7: Error Handling
   - API timeout → retry 3 times with backoff
   - Invalid keyword → log and skip
   - Database error → log and raise
   - Partial failure → save what we have, log warning

C. Helper Functions:
   
   ```python
   def generate_audience_description(keyword: str) -> str:
       """Generate description of target audience for keyword"""
       # Could use Claude for this
       
   def recommend_word_count(difficulty: int) -> int:
       """Recommend article length based on difficulty"""
       # Higher difficulty = longer articles
       if difficulty < 20:
           return 1000
       elif difficulty < 40:
           return 1500
       elif difficulty < 60:
           return 2000
       else:
           return 2500
   
   def generate_unique_angle(keyword: str, competitors: List[dict]) -> str:
       """Suggest unique angle based on competitor analysis"""
       # Could use Claude for this
   ```

D. Logging & Monitoring:
   
   Log at each step:
   - "Starting keyword research: {keyword}"
   - "Found {volume} monthly searches"
   - "Analyzed {count} competitor articles"
   - "Created brief with {section_count} sections"
   - "Saved brief #{brief_id} to database"
   
   Log errors:
   - "Failed to fetch Ahrefs data: {error}"
   - "Brief validation failed: {missing_fields}"
   - "Database error: {error}"

TESTING REQUIREMENTS:

1. Integration test - full pipeline:
   ```python
   def test_full_keyword_research_pipeline(db_session):
       # Mock all external APIs
       with patch('integrations.ahrefs_client.AhrefsClient') as mock_ahrefs:
           # Setup mocks
           mock_ahrefs.search_volume.return_value = {"volume": 2400}
           mock_ahrefs.keyword_difficulty.return_value = {"difficulty": 32}
           mock_ahrefs.serp_features.return_value = {"features": {...}}
           mock_ahrefs.competitor_analysis.return_value = {"avg_word_count": 2500}
           
           # Run pipeline
           brief = research_keyword("python asyncio")
           
           # Assertions
           assert brief is not None
           assert brief.keyword == "python asyncio"
           assert brief.search_volume == 2400
           assert brief.difficulty == 32
           
           # Verify saved to database
           from_db = db_session.query(ContentBrief).filter_by(
               keyword="python asyncio"
           ).first()
           assert from_db is not None
   ```

2. Test validation:
   ```python
   def test_invalid_keyword():
       result = research_keyword("")
       assert result is None
       
       result = research_keyword("@#$%^&")
       assert result is None
   ```

3. Test error handling:
   ```python
   def test_ahrefs_timeout_retry():
       with patch('integrations.ahrefs_client.AhrefsClient') as mock:
           # First 2 fail, 3rd succeeds
           mock.search_volume.side_effect = [
               Timeout(),
               Timeout(),
               {"volume": 2400}
           ]
           
           brief = research_keyword("test")
           assert brief is not None
           # Should have retried 3 times
           assert mock.search_volume.call_count == 3
   ```

4. Test database storage:
   ```python
   def test_brief_saved_to_database(db_session):
       brief = research_keyword("test keyword")
       
       # Verify in database
       from_db = db_session.query(ContentBrief).get(brief.id)
       assert from_db.keyword == "test keyword"
       assert from_db.brief_data is not None
   ```

DELIVERABLES:
1. src/blog_automation/pipelines/keyword_research.py - Main pipeline
2. src/blog_automation/pipelines/__init__.py - Pipeline exports
3. tests/integration/test_keyword_research_pipeline.py - Integration tests
4. Documentation on running the pipeline

SUCCESS CRITERIA:
✓ Pipeline executes end-to-end
✓ All Ahrefs data fetched correctly
✓ Brief created with all required fields
✓ Database storage works
✓ Error handling and retries work
✓ All tests pass
✓ Logging captures all steps
✓ No hanging code
```

---

I'll continue with the remaining 9 prompts. Due to length constraints, here's the structure for the rest:
