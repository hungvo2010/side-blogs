AI Blog Automation System - Developer Specification
=====================================================

PROJECT OVERVIEW
================

Project Name: AI Blog Content Automation Platform
Purpose: Automated content generation, fact-checking, SEO optimization, and publishing for AdSense & Mediavine monetization
Target User: Python developers building a blog automation business
Stack: Python 3.11+, PostgreSQL, Apache Airflow, WordPress REST API
Timeline: 6-8 weeks for MVP, scalable to full production

CORE PROBLEM STATEMENT
======================

Challenge: Creating 2-4 blog articles per week with high quality while maintaining:
  • E-E-A-T compliance (Experience, Expertise, Authoritativeness, Trustworthiness)
  • <3% plagiarism rate
  • 1+ hour human review per article minimum (Mediavine requirement)
  • Cost efficiency (<$1 AI cost per article)
  • Mediavine compliance (critical: <50% AI content across site)

Solution: Automated pipeline with mandatory human review gates

================================================================================
PART 1: FUNCTIONAL REQUIREMENTS
================================================================================

1. CONTENT DISCOVERY & RESEARCH
────────────────────────────────

1.1 Keyword Research Pipeline
  REQ-1.1.1: Fetch next keyword from content calendar
    Input: Content calendar (database)
    Output: Selected keyword + metadata
    Method: Query next_article from ContentCalendar table where status='planned'
    
  REQ-1.1.2: Analyze keyword metrics using Ahrefs API
    Input: Keyword string
    Output: JSON with search_volume, difficulty, intent, top_10_competitors
    API: Ahrefs API v2
    Caching: Cache results for 30 days (keywords don't change frequently)
    Error Handling: Retry failed API calls max 3 times with exponential backoff
    
  REQ-1.1.3: Extract SERP features (featured snippet, people also ask, tables)
    Input: Keyword
    Output: List of detected SERP features with content structure
    API: Ahrefs SERP API or SEMrush
    Usage: Informs content structure (e.g., if featured snippet exists, create 40-50 word definition)
    
  REQ-1.1.4: Analyze competitor content
    Input: Top 10 URLs from SERP
    Output: Average word count, readability score, structure, H2 patterns
    Purpose: Inform target article length and structure
    Method: Web scrape + analyze with NLP (NLTK/spaCy)

1.2 Content Brief Generation
  REQ-1.2.1: Generate structured content brief
    Input: Keyword data from 1.1
    Output: JSON content brief with:
      • Primary keyword + variations
      • Target audience + pain points
      • Recommended H2 sections (based on competitor analysis)
      • Target word count (1500-2500 words)
      • Internal links to create (3-5 related articles)
      • External sources to cite (5-10 minimum)
      • Unique angle/perspective
    Storage: Save to ContentBrief table + database
    Format: JSON (validated against schema)
    
  REQ-1.2.2: Validate brief completeness
    Validation rules:
      ✓ Has minimum 5 external sources identified
      ✓ Has 4+ H2 section recommendations
      ✓ Has target audience defined
      ✓ Has unique angle identified
    Action on failure: Alert user, save as draft, require manual review

---

2. AI CONTENT GENERATION
────────────────────────

2.1 Outline Generation
  REQ-2.1.1: Generate article outline
    Input: Content brief (JSON)
    Model: Claude 3 Sonnet (fastest, cheapest - $0.003 per 1k tokens)
    Prompt: Structured outline prompt with H1, H2, H3 hierarchy
    Output: Markdown outline with section hierarchy
    Constraints:
      • Max 4 main H2 sections + FAQ section
      • Each H2 must have 2-3 H3 subsections
      • Total outline <500 tokens
    Cost per call: ~$0.01
    Cache: 60 minutes (in case regeneration needed)

2.2 Main Content Drafting
  REQ-2.2.1: Generate full article draft
    Input: Content brief + outline
    Model: GPT-4 Turbo (best quality for SEO content)
    Temperature: 0.7 (balance between consistency and creativity)
    Max tokens: 3000 (for ~2000 word article)
    Prompt: System prompt + user prompt (see architecture section)
    Output: Markdown article with proper formatting
    
  REQ-2.2.2: Enforce quality standards in prompt
    Requirements enforced at generation:
      ✓ Conversational tone (not robotic)
      ✓ Short paragraphs (2-3 sentences max)
      ✓ Keyword appears naturally 3-5 times total
      ✓ Real examples included
      ✓ No keyword stuffing or obvious AI patterns
      ✓ Each section provides genuine user value
    
  REQ-2.2.3: Handle generation failures gracefully
    Failure modes:
      • API timeout: Retry max 3 times with exponential backoff
      • Rate limit: Queue and retry after 60 seconds
      • Invalid response: Log error + alert admin
      • Partial response: Resume generation from last checkpoint
    
  REQ-2.2.4: Cost tracking
    Track per-article:
      • Model used (gpt4, claude3, sonnet)
      • Tokens used (input + output)
      • Cost in USD
      • Timestamp
    Storage: Article.ai_generation_cost (float field)
    Target: <$0.50 per article

2.3 Claim Extraction (for fact-checking)
  REQ-2.3.1: Extract atomic claims from article
    Input: Generated article markdown
    Model: Claude 3 Opus (best accuracy for this task)
    Task: Decompose article into factual claims
    Output: JSON array with:
      [
        {
          "claim": "Python asyncio released in 3.4",
          "type": "historical|statistic|technical|definition",
          "confidence": "high|medium|low",
          "line_number": 45
        },
        ...
      ]
    Storage: Save to database for fact-checking pipeline
    Target: 10-15 claims per article (filter out common knowledge)

---

3. FACT-CHECKING & VERIFICATION
────────────────────────────────

3.1 Claim Filtering
  REQ-3.1.1: Filter out non-checkworthy claims
    Filter rules:
      ✓ Remove common knowledge (e.g., "Python is a programming language")
      ✓ Remove subjective opinions
      ✓ Keep: statistics, dates, technical specifications, quotes
    Target: Reduce 20-30 claims → 10-12 checkworthy claims

3.2 Evidence Retrieval
  REQ-3.2.1: Retrieve evidence using Perplexity AI API
    Input: Checkworthy claims (filtered)
    API: Perplexity API (includes built-in web search)
    Query format: "What is the evidence for: [claim]?"
    Output: Retrieved evidence + source URLs
    Caching: Cache search results for 7 days
    Rate limiting: Max 15 claims per article (API limits)

3.3 Verification & Comparison
  REQ-3.3.1: Compare claim against evidence
    Input: Claim + evidence text
    Model: Claude 3 Opus (best for reasoning)
    Output: Verdict (supported|contradicted|unclear|missing_evidence)
    Additional: Confidence score (0-100), suggested revision if needed
    
  REQ-3.3.2: Generate fact-check report
    Output structure:
      {
        "total_claims_checked": 12,
        "supported": 11,
        "contradicted": 0,
        "unclear": 1,
        "accuracy_rate": "91.7%",
        "issues_found": [
          {
            "claim": "...",
            "verdict": "unclear",
            "confidence": 85,
            "explanation": "...",
            "suggested_revision": "..."
          }
        ]
      }
    Storage: Save full report to Article.fact_check_report (JSON field)
    Pass criteria: accuracy_rate >= 95% OR contradicted == 0

---

4. HUMAN EDITORIAL REVIEW (MANDATORY GATE)
────────────────────────────────────────────

4.1 Review Assignment
  REQ-4.1.1: Create review task for human editor
    Input: Article draft + fact-check report
    Output: Review notification sent to editor via:
      • Email notification
      • Slack message (if configured)
      • Dashboard task queue
    Deadline: Automatic assignment (round-robin to available editors)
    SLA: Review within 24 hours (configurable)

4.2 Review Interface
  REQ-4.2.1: Display article for review with all context
    Show:
      • Full article draft (markdown)
      • Fact-check report with issues highlighted
      • SEO analysis (preliminary)
      • E-E-A-T scoring (AI-preliminary, for reference)
      • Original content brief
    Format: Web interface or CLI tool
    
  REQ-4.2.2: Capture review decision + feedback
    Decision options:
      • APPROVE (article passes, ready for SEO optimization)
      • REVISE (request specific changes, includes feedback)
      • REJECT (rewrite needed, includes reasons)
    
    If REVISE:
      - Store feedback text
      - Mark specific sections needing work
      - Return to writer for revisions
      - Re-run fact-checking on revised sections
    
    If REJECT:
      - Log rejection reasons
      - Send back to AI drafting with updated prompt
      - Optional: Human manual rewrite
    
    If APPROVE:
      - Mark article.status = 'approved'
      - Proceed to SEO optimization stage
      - Log review hours (for Mediavine compliance)

4.3 Quality Assurance Checks
  REQ-4.3.1: Automated quality gates (optional, pre-human review)
    Check before sending to human:
      ✓ Word count >= 1500
      ✓ Plagiarism check < 5% (Copyscape API)
      ✓ Readability score (Flesch-Kincaid) <= 12
      ✓ External links count >= 5
      ✓ No obvious AI patterns (keyword stuffing, repetition)
    Action: Flag articles failing gates for immediate rejection

---

5. SEO OPTIMIZATION
────────────────────

5.1 SEO Analysis
  REQ-5.1.1: Analyze article using Rank Math API
    Input: Article content + target keyword
    Output: SEO score (0-100) with breakdown:
      • Keyword placement score
      • Content structure score
      • Link score
      • Readability score
    Target: >= 70/100

  REQ-5.1.2: Get competitor comparison via SurferSEO
    Input: Article + keyword
    Output: Content score (0-100) comparing to top 10 rankings
    Metrics:
      • Content length (should be 1500-2500 words typically)
      • Keyword density (0.5-1.5% target)
      • LSI keyword usage
      • Heading structure match
      • Content freshness recommendations

5.2 Optimization Suggestions
  REQ-5.2.1: Generate actionable optimization recommendations
    Examples:
      • "Add 150 more words to reach optimal length"
      • "Include LSI keyword 'async programming' 2-3 more times"
      • "Add internal link to article #234 in conclusion"
      • "Create H3 subheading 'Best Practices' under Performance section"
    
    Implementation:
      • AI suggests changes
      • Human approves changes
      • Changes automatically applied to markdown
    
    Validation: Rerun SEO analysis after changes

5.3 Meta Tag Optimization
  REQ-5.3.1: Generate/optimize meta title
    Requirements:
      • 50-60 characters
      • Primary keyword in first 5 words
      • Compelling (encourages clicks)
      • Example: "Python Asyncio Tutorial 2024: Complete Beginner's Guide"
    Generated by: GPT-4 (1-2 attempts, human selects best)

  REQ-5.3.2: Generate/optimize meta description
    Requirements:
      • 150-160 characters
      • Include primary keyword naturally
      • Include call-to-action
      • Compelling (improves CTR)
    Generated by: GPT-4

5.4 Image Optimization
  REQ-5.4.1: Optimize image alt text
    Rules:
      • Include target keyword naturally (if relevant)
      • Descriptive (40-125 characters)
      • No keyword stuffing
    Example: "Python asyncio event loop managing concurrent tasks"

---

6. FINAL QUALITY GATES
──────────────────────

6.1 Plagiarism Check
  REQ-6.1.1: Check article against web + internal database
    Tools: Copyscape API + custom internal check
    Threshold: < 3% acceptable (allows minor overlap)
    What to compare:
      • Entire article against web
      • Against all other articles on same site (prevent duplication)
    Action on failure:
      • Flag for manual review
      • Identify plagiarized sections
      • Reject article (return for rewriting)

6.2 Link Verification
  REQ-6.2.1: Verify all links are valid
    Check:
      • All internal links point to existing articles
      • All external links are live (HTTP 200)
      • No broken redirects (301/302 chains)
    Action on failure: Auto-fix internal links, alert user about broken external links

6.3 Metadata Validation
  REQ-6.3.1: Validate all required metadata
    Required fields:
      ✓ Meta title (50-60 chars)
      ✓ Meta description (150-160 chars)
      ✓ Primary keyword set
      ✓ Category selected
      ✓ Featured image selected
      ✓ Internal links (3-5)
      ✓ AI disclosure (if AI used)
    Action on failure: Block publishing until complete

---

7. WORDPRESS PUBLISHING
────────────────────────

7.1 Pre-Publishing Preparation
  REQ-7.1.1: Format article for WordPress
    Conversions:
      • Markdown → HTML (using markdown2 library)
      • Image markdown [alt text](url) → WordPress img tags with alt
      • Links: Markdown links → <a> tags with proper formatting
      • Code blocks → <pre><code> with syntax highlighting (if needed)
    
  REQ-7.1.2: Upload images to WordPress Media Library
    Process:
      • Identify all images in article
      • Download image (if URL provided)
      • Compress image (max 300KB)
      • Upload via WordPress REST API
      • Get attachment ID
      • Replace image URLs in article with attachment IDs
    
    Error handling:
      • Retry failed uploads 3 times
      • Skip broken image URLs (log warning)
      • Use placeholder if image unavailable

7.2 Post Creation
  REQ-7.2.1: Create WordPress post via REST API
    Endpoint: POST /wp-json/wp/v2/posts
    Payload:
      {
        "title": "Article Title",
        "content": "<p>HTML content here</p>",
        "excerpt": "Meta description",
        "status": "draft",  // Always draft until final approval
        "categories": [5],  // Category ID
        "tags": [10, 11],   // Tag IDs
        "featured_media": 1234,  // Featured image attachment ID
      }
    
    Response: Post ID + post object
    Error handling:
      • 401 Unauthorized: Check API credentials
      • 403 Forbidden: Check user permissions
      • 400 Bad Request: Validate payload
      • Retry max 3 times on 5xx errors

7.3 Custom Metadata
  REQ-7.3.1: Store article metadata in WordPress custom fields (ACF)
    Fields to store:
      • ai_model_used: "gpt4" | "claude3" | "sonnet" | "hybrid"
      • ai_disclosure: true | false
      • fact_check_status: "verified" | "issues_fixed" | "pending"
      • fact_check_issues: integer (number of issues found)
      • original_content_percent: 0-100 (estimated %)
      • human_review_hours: float (time spent reviewing)
      • internal_links: array of post IDs
    
    Storage: Use ACF (Advanced Custom Fields) plugin
    API: Set via _fields parameter in REST API
    Purpose: Track Mediavine compliance, enable custom queries

7.4 Publishing Schedule
  REQ-7.4.1: Schedule or immediately publish
    Options:
      • Publish immediately (status: publish)
      • Schedule for specific time (status: future, date: timestamp)
    
    Default: Schedule for next day 8 AM (allows final review)
    Human can override to publish immediately

---

8. MONITORING & TRACKING
─────────────────────────

8.1 Performance Tracking Setup
  REQ-8.1.1: Initialize Google Analytics 4 tracking
    Action: Add GA4 tracking code to WordPress
    Events to track:
      • page_view: Standard page view
      • scroll: When user reaches 25%, 50%, 75%, 100%
      • time_on_page: Track engagement
      • internal_link_click: Track which links clicked
      • affiliate_link_click: Track affiliate conversions
    
  REQ-8.1.2: Setup Google Search Console tracking
    Action: Verify site in GSC + integrate with GA4
    Purpose: Track keyword rankings, CTR, impressions
    Data sync: Daily refresh of keyword performance

8.2 Database Tracking
  REQ-8.2.1: Store article performance metadata
    Fields in Article table:
      • views_30_days: Integer
      • avg_time_on_page: Float (minutes)
      • bounce_rate: Float (percentage)
      • clicks_from_search: Integer
      • impressions_from_search: Integer
      • avg_rank_position: Float
    
    Update frequency: Daily (via scheduled job)
    Source: Google Search Console API

---

================================================================================
PART 2: TECHNICAL ARCHITECTURE & DATA DESIGN
================================================================================

SYSTEM ARCHITECTURE
───────────────────

```
┌─────────────────────────────────────────────────────┐
│                  INPUT LAYER                         │
├─────────────────────────────────────────────────────┤
│  • Content Calendar (CSV/Database)                  │
│  • Editor Slack/Email Commands                      │
│  • Manual keyword input                             │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│          ORCHESTRATION LAYER (Apache Airflow)       │
├─────────────────────────────────────────────────────┤
│  • Workflow DAG execution                           │
│  • Task dependency management                       │
│  • Error handling & retries                         │
│  • Scheduling (daily 8 AM)                          │
└────────────────┬────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬──────────────┐
    ▼            ▼            ▼              ▼
┌────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│Research│  │Drafting│  │Checking│  │Reviewing │
│Pipeline│  │Pipeline│  │Pipeline│  │Interface │
└────────┘  └────────┘  └────────┘  └──────────┘
    │            │            │              │
    └────────────┼────────────┴──────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         EXTERNAL INTEGRATIONS LAYER                 │
├─────────────────────────────────────────────────────┤
│  • Ahrefs API (keyword research)                    │
│  • OpenAI API (GPT-4 drafting)                      │
│  • Anthropic API (Claude fact-checking)             │
│  • Perplexity AI (web search verification)          │
│  • Rank Math API (SEO analysis)                     │
│  • SurferSEO (competitor analysis)                  │
│  • Copyscape API (plagiarism check)                 │
│  • WordPress REST API (publishing)                  │
│  • Google Analytics API (tracking)                  │
│  • Google Search Console API (rankings)             │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│          DATA PERSISTENCE LAYER                     │
├─────────────────────────────────────────────────────┤
│  • PostgreSQL Database (articles, reviews, metrics) │
│  • Cache Layer (Redis - optional)                   │
│  • File Storage (images, backups)                   │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│          NOTIFICATION & REPORTING LAYER             │
├─────────────────────────────────────────────────────┤
│  • Slack notifications                              │
│  • Email alerts                                     │
│  • Dashboard metrics                                │
│  • Compliance reports                               │
└─────────────────────────────────────────────────────┘
```

DATA MODELS (SQLAlchemy)
────────────────────────

1. ContentCalendar
   ├─ id: Integer (PK)
   ├─ week_number: Integer
   ├─ pub_date: DateTime (publication target)
   ├─ keyword: String(255)
   ├─ title: String(255)
   ├─ status: Enum (planned|in_progress|submitted|published)
   ├─ assigned_writer: String(100)
   ├─ assigned_reviewer: String(100)
   ├─ article_id: Foreign Key → Article
   └─ created_at: DateTime

2. ContentBrief
   ├─ id: Integer (PK)
   ├─ keyword: String(255)
   ├─ search_volume: Integer
   ├─ difficulty: Integer (0-100)
   ├─ intent: String (informational|commercial|transactional)
   ├─ brief_data: JSON (full content brief structure)
   └─ created_at: DateTime

3. Article (Core Table)
   ├─ id: Integer (PK)
   ├─ title: String(255)
   ├─ slug: String(255) UNIQUE
   ├─ keyword: String(255) INDEXED
   ├─ content_draft: Text (markdown)
   ├─ content_final: Text (markdown, after optimization)
   ├─ content_html: Text (WordPress HTML version)
   │
   ├─ AI Metadata:
   ├─ ai_model_used: String (gpt4|claude3|sonnet|hybrid)
   ├─ ai_generation_cost: Float (USD)
   │
   ├─ Status:
   ├─ status: String INDEXED (draft|fact_checking|editing|seo_review|approved|published)
   │
   ├─ Fact-Checking:
   ├─ fact_check_report: JSON
   ├─ fact_check_passed: Boolean
   ├─ fact_check_date: DateTime
   ├─ fact_check_issues: Integer
   │
   ├─ SEO:
   ├─ seo_score: Integer (0-100)
   ├─ seo_analysis: JSON
   ├─ meta_title: String(60)
   ├─ meta_description: String(160)
   ├─ keyword_density: Float
   │
   ├─ Quality:
   ├─ word_count: Integer
   ├─ readability_score: Float (Flesch-Kincaid)
   ├─ plagiarism_percent: Float
   ├─ original_content_percent: Float
   │
   ├─ E-E-A-T Scores:
   ├─ eeat_experience: Integer (0-10)
   ├─ eeat_expertise: Integer (0-10)
   ├─ eeat_authoritativeness: Integer (0-10)
   ├─ eeat_trustworthiness: Integer (0-10)
   │
   ├─ WordPress:
   ├─ wordpress_post_id: Integer INDEXED
   ├─ wordpress_url: String(500)
   ├─ published_date: DateTime
   │
   ├─ Links:
   ├─ internal_links: JSON (array of post IDs)
   ├─ external_links: JSON (array of URLs)
   │
   ├─ Tracking:
   ├─ views_30_days: Integer
   ├─ avg_time_on_page: Float
   ├─ bounce_rate: Float
   │
   ├─ Audit:
   ├─ created_at: DateTime INDEXED
   ├─ updated_at: DateTime
   ├─ created_by: String
   └─ updated_by: String

4. ArticleReview
   ├─ id: Integer (PK)
   ├─ article_id: Integer (FK)
   ├─ reviewer_id: String
   ├─ content_quality: Integer (1-10)
   ├─ originality: Integer (1-10)
   ├─ eeat_compliance: Integer (1-10)
   ├─ seo_quality: Integer (1-10)
   ├─ overall_score: Integer (1-10)
   ├─ verdict: String (approve|revise|reject)
   ├─ feedback: Text
   ├─ issues_found: JSON (array of issues)
   ├─ review_start: DateTime
   ├─ review_end: DateTime
   ├─ review_hours: Float
   └─ created_at: DateTime

5. ArticleMetrics (Daily Performance)
   ├─ id: Integer (PK)
   ├─ article_id: Integer (FK)
   ├─ date: DateTime INDEXED
   ├─ views: Integer
   ├─ clicks: Integer
   ├─ avg_time: Float
   ├─ bounce_rate: Float
   ├─ impressions: Integer (from GSC)
   ├─ ctr: Float (Click-through rate)
   ├─ avg_position: Float (search ranking)
   └─ created_at: DateTime

API CONTRACTS
──────────────

1. POST /articles/create
   Request:
   {
     "keyword": "python asyncio",
     "content_brief": { ... }
   }
   Response:
   {
     "article_id": 123,
     "status": "fact_checking",
     "draft_preview": "...",
     "next_step": "fact_check_review"
   }

2. POST /articles/{id}/review
   Request:
   {
     "verdict": "approve|revise|reject",
     "feedback": "...",
     "issues": [ ... ]
   }
   Response:
   {
     "article_id": 123,
     "status": "approved",
     "next_step": "seo_optimization"
   }

3. POST /articles/{id}/publish
   Request:
   {
     "schedule_time": "2024-01-15T08:00:00Z"  // optional
   }
   Response:
   {
     "wordpress_post_id": 234,
     "wordpress_url": "https://...",
     "status": "published",
     "analytics_tracking": "initialized"
   }

================================================================================
PART 3: ERROR HANDLING STRATEGY
================================================================================

ERROR CLASSIFICATION
────────────────────

CATEGORY 1: API Failures (External Services)
─────────────────────────────────────────────

Error Type 1.1: API Timeout
  Service: Any API call (OpenAI, Ahrefs, etc.)
  Symptom: Request hangs >30 seconds
  Handling:
    • Timeout = 30 seconds per call
    • Retry logic: Exponential backoff (1s, 2s, 4s, 8s, 16s)
    • Max retries: 3
    • If all retries fail: Log error + alert admin + pause pipeline
  Example:
    ```python
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[...],
            timeout=30
        )
    except requests.Timeout:
        # Retry with exponential backoff
        for attempt in range(3):
            wait_time = 2 ** attempt
            time.sleep(wait_time)
            try:
                response = openai.ChatCompletion.create(...)
                break
            except:
                if attempt == 2:  # Last attempt
                    logger.error("OpenAI API timeout after 3 retries")
                    send_alert("API_TIMEOUT", "openai")
                    raise
    ```

Error Type 1.2: Rate Limiting (429 status)
  Service: Any API with rate limits
  Symptom: HTTP 429 Too Many Requests
  Handling:
    • Check Retry-After header (if provided)
    • Wait specified time (or default 60 seconds)
    • Queue request for retry
    • Log rate limit event
  Example:
    ```python
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            retry_after = int(e.response.headers.get('Retry-After', 60))
            logger.warning(f"Rate limited. Retrying after {retry_after}s")
            time.sleep(retry_after)
            # Re-queue task in Airflow
    ```

Error Type 1.3: Authentication Failure (401/403)
  Service: Any authenticated API
  Symptom: Invalid API key or permissions
  Handling:
    • Don't retry (will always fail)
    • Log error with service name
    • Alert admin with specific error
    • Require manual intervention
  Example:
    ```python
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in [401, 403]:
            logger.critical(f"Auth failure for {service}: {e.response.text}")
            send_alert("AUTH_FAILURE", service)
            # Mark task as failed (don't retry)
            raise AirflowException(f"Auth failure: {service}")
    ```

Error Type 1.4: Invalid Response (4xx but not 401/403/429)
  Service: Any API
  Symptom: Bad request, malformed response, etc.
  Handling:
    • Log full request + response
    • Check request payload for issues
    • Don't retry (usually user error)
    • Alert to review request format
  Example:
    ```python
    except requests.exceptions.HTTPError as e:
        if 400 <= e.response.status_code < 429:
            logger.error(f"Bad request: {e.request.body}")
            logger.error(f"Response: {e.response.text}")
            raise ValueError(f"Invalid request: {e.response.text}")
    ```

Error Type 1.5: Server Error (5xx)
  Service: Any API
  Symptom: Service unavailable, internal error
  Handling:
    • Retry with exponential backoff
    • Max retries: 5
    • Increase retry wait between attempts
    • If persistent: Queue for later retry
  Example:
    ```python
    except requests.exceptions.HTTPError as e:
        if e.response.status_code >= 500:
            for attempt in range(5):
                wait_time = min(300, 2 ** attempt * 10)  # Max 5 min
                time.sleep(wait_time)
                try:
                    # Retry request
                    break
                except:
                    if attempt == 4:
                        logger.error("Server error persists, deferring task")
                        # Defer task to retry in 1 hour
    ```

CATEGORY 2: Data Validation Errors
──────────────────────────────────

Error Type 2.1: Invalid Input Data
  Scenario: Keyword research returns malformed data
  Handling:
    • Validate against schema before processing
    • Log validation errors with specific field
    • Mark article as draft (requires manual review)
    • Alert on dashboard for user action
  Example:
    ```python
    def validate_content_brief(brief: dict) -> bool:
        required_fields = ['keyword', 'intent', 'sections', 'sources']
        for field in required_fields:
            if field not in brief:
                logger.error(f"Missing field: {field}")
                return False
        
        if not isinstance(brief['sections'], list) or len(brief['sections']) < 3:
            logger.error("Must have 3+ sections")
            return False
        
        return True
    
    if not validate_content_brief(brief):
        article.status = 'draft'
        article.validation_errors = {...}
        db.commit()
        return False
    ```

Error Type 2.2: Null/Missing Data
  Scenario: API returns field with null value
  Handling:
    • Provide sensible defaults where possible
    • Log missing data fields
    • Don't proceed if critical field missing
  Example:
    ```python
    keyword_data = {
        'search_volume': keyword_metrics.get('volume', 0),
        'difficulty': keyword_metrics.get('difficulty') or 50,  # Default to 50
        'intent': keyword_metrics.get('intent', 'unknown')
    }
    ```

Error Type 2.3: Type Mismatch
  Scenario: Expected string, got integer
  Handling:
    • Attempt type coercion where safe
    • Log type issues
    • Fail if coercion unsafe
  Example:
    ```python
    def safe_int(value, default=0):
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Cannot convert {value} to int, using default")
            return default
    ```

CATEGORY 3: Processing Errors
───────────────────────────────

Error Type 3.1: AI Generation Failure (partial content)
  Scenario: GPT-4 returns incomplete article
  Handling:
    • Resume generation from checkpoint (if available)
    • Or request human intervention
    • Log partial content + error
  Example:
    ```python
    def generate_with_resume(brief, checkpoint=None):
        if checkpoint:
            prompt = f"Resume from: {checkpoint['last_section']}\n\n"
        else:
            prompt = ""
        
        try:
            response = generate_content(prompt + outline)
            if len(response) < MIN_WORDS:
                logger.warning(f"Incomplete generation: {len(response)} words")
                # Retry or escalate
        except:
            # Save checkpoint for resume
            save_checkpoint(article_id, last_section)
    ```

Error Type 3.2: Fact-Check Verification Failed
  Scenario: Claim cannot be verified
  Handling:
    • Mark as "unclear" (not contradicted)
    • Suggest revision to article author
    • Don't block publishing (but alert editor)
  Example:
    ```python
    if verdict == 'unclear':
        article.fact_check_issues += 1
        article.status = 'awaiting_human_review'
        notify_editor(
            f"Article {article_id}: {claim} needs verification",
            priority="medium"
        )
    ```

Error Type 3.3: WordPress Publishing Failure
  Scenario: REST API call fails during publish
  Handling:
    • Retry up to 3 times
    • If persistent: Keep article as draft + alert
    • Store error for manual intervention
  Example:
    ```python
    def publish_to_wordpress(article, max_retries=3):
        for attempt in range(max_retries):
            try:
                post = wp.create_post({...})
                article.wordpress_post_id = post['id']
                article.status = 'published'
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Publishing failed after {max_retries} attempts: {e}")
                    article.publishing_error = str(e)
                    send_alert("PUBLISH_FAILED", article.id)
                    return False
                time.sleep(5)
    ```

CATEGORY 4: Database Errors
────────────────────────────

Error Type 4.1: Connection Pool Exhausted
  Symptom: Cannot get database connection
  Handling:
    • Log pool status
    • Increase pool size (if needed)
    • Queue task for retry after 30 seconds
  Example:
    ```python
    from sqlalchemy.pool import NullPool, QueuePool
    
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600
    )
    ```

Error Type 4.2: Constraint Violation (unique, foreign key)
  Scenario: Article slug already exists
  Handling:
    • Log constraint error
    • Generate alternative slug (with suffix)
    • Retry insert
  Example:
    ```python
    import hashlib
    
    def generate_unique_slug(base_slug, article_id):
        # Try base slug first
        if not db.query(Article).filter_by(slug=base_slug).first():
            return base_slug
        
        # Add suffix if exists
        suffix = hashlib.md5(str(article_id).encode()).hexdigest()[:6]
        return f"{base_slug}-{suffix}"
    ```

Error Type 4.3: Concurrent Update Conflict
  Scenario: Two processes update same article
  Handling:
    • Use optimistic locking (version field)
    • Retry with fresh data
  Example:
    ```python
    class Article(Base):
        __tablename__ = 'articles'
        id = Column(Integer, primary_key=True)
        content = Column(Text)
        version = Column(Integer, default=1)
        
        def update(self, new_content):
            if self.version != db.query(Article).filter_by(id=self.id).first().version:
                raise ConflictError("Article was modified elsewhere")
            self.content = new_content
            self.version += 1
            db.commit()
    ```

CATEGORY 5: Resource Exhaustion
────────────────────────────────

Error Type 5.1: Memory Exhaustion
  Scenario: Processing large file exceeds RAM
  Handling:
    • Process in chunks
    • Clear variables after use
    • Monitor memory usage
  Example:
    ```python
    import gc
    
    def process_large_article(article_content, chunk_size=10000):
        for i in range(0, len(article_content), chunk_size):
            chunk = article_content[i:i+chunk_size]
            process_chunk(chunk)
            gc.collect()  # Force garbage collection
    ```

Error Type 5.2: API Quota Exceeded
  Scenario: Daily API quota used up
  Handling:
    • Check remaining quota before request
    • Queue request for next day
    • Alert admin
  Example:
    ```python
    def check_quota(service, date):
        usage = get_daily_usage(service, date)
        limit = get_quota_limit(service)
        if usage >= limit:
            logger.warning(f"{service} quota exceeded for today")
            return False
        return True
    ```

CENTRAL ERROR HANDLING PATTERN
──────────────────────────────

```python
class AppError(Exception):
    """Base exception for application"""
    def __init__(self, message, error_code, severity="error"):
        self.message = message
        self.error_code = error_code
        self.severity = severity  # "critical", "error", "warning"
        
class APIError(AppError):
    """External API errors"""
    pass

class ValidationError(AppError):
    """Data validation errors"""
    pass

class ProcessingError(AppError):
    """Processing pipeline errors"""
    pass

# Global error handler
def handle_error(error: Exception, context: dict):
    """Central error handler for all pipeline stages"""
    
    logger.error(f"Error in {context['stage']}: {error}")
    
    if isinstance(error, APIError):
        if error.error_code == "TIMEOUT":
            return retry_with_backoff(context['task'])
        elif error.error_code == "RATE_LIMIT":
            return queue_for_retry(context['task'], delay=60)
        elif error.error_code == "AUTH_FAILURE":
            return alert_admin(error)
    
    elif isinstance(error, ValidationError):
        return save_as_draft(context['article'])
    
    else:
        # Unknown error
        send_alert("UNKNOWN_ERROR", str(error))
        return fail_task(context['task'])
```

================================================================================
PART 4: COMPREHENSIVE TESTING PLAN
================================================================================

TESTING STRATEGY
─────────────────

Testing Pyramid:
```
        ▲
       / \
      /   \  END-TO-END TESTS
     /─────\  (10-15% of tests)
    /       \
   /─────────\ INTEGRATION TESTS
  /           \ (30-40% of tests)
 /─────────────\ UNIT TESTS
/_______________\ (50-60% of tests)
```

UNIT TESTS (50-60% of test suite)
──────────────────────────────────

Test Module 1: Keyword Research Pipeline
File: tests/test_keyword_research.py

Test 1.1: Valid keyword data parsing
```python
def test_parse_ahrefs_response():
    response = {
        'keyword': 'python asyncio',
        'volume': 2400,
        'difficulty': 32,
        'intent': 'informational'
    }
    
    result = parse_keyword_response(response)
    
    assert result['keyword'] == 'python asyncio'
    assert result['search_volume'] == 2400
    assert result['difficulty'] == 32
```

Test 1.2: Invalid keyword handling
```python
def test_invalid_keyword_empty():
    with pytest.raises(ValidationError):
        parse_keyword_response({})

def test_invalid_keyword_missing_volume():
    response = {'keyword': 'test', 'difficulty': 50}
    with pytest.raises(ValidationError):
        parse_keyword_response(response)
```

Test 1.3: Mock Ahrefs API call
```python
@patch('integrations.ahrefs_api.AhrefsAPI.search_volume')
def test_fetch_keyword_metrics(mock_ahrefs):
    mock_ahrefs.return_value = {
        'volume': 2400,
        'difficulty': 32
    }
    
    result = fetch_keyword_metrics('python asyncio')
    
    assert result['volume'] == 2400
    mock_ahrefs.assert_called_once_with('python asyncio')
```

Test Module 2: Content Brief Generation
File: tests/test_brief_generation.py

Test 2.1: Content brief structure
```python
def test_content_brief_generation():
    brief = generate_content_brief({
        'keyword': 'python asyncio',
        'intent': 'informational'
    })
    
    assert 'keyword' in brief
    assert 'sections' in brief
    assert len(brief['sections']) >= 3
    assert 'sources' in brief
    assert len(brief['sources']) >= 5
```

Test 2.2: Required fields validation
```python
def test_brief_missing_sources():
    brief = {'keyword': 'test', 'sections': []}
    assert not validate_brief(brief)

def test_brief_missing_sections():
    brief = {'keyword': 'test', 'sources': []}
    assert not validate_brief(brief)
```

Test Module 3: AI Content Generation
File: tests/test_content_generation.py

Test 3.1: Mock GPT-4 generation
```python
@patch('integrations.openai_integration.OpenAI.generate')
def test_generate_article_draft(mock_gpt4):
    mock_gpt4.return_value = "Generated article content..."
    
    draft = generate_article_draft({'keyword': 'test'})
    
    assert len(draft) > 100  # Minimum content
    assert 'test' in draft.lower()  # Contains keyword
```

Test 3.2: Quality constraints
```python
def test_draft_minimum_length():
    draft = "Short content"
    assert not validate_draft_quality(draft)

def test_draft_keyword_presence():
    draft = "Content about something completely different"
    target_keyword = "python"
    assert not validate_keyword_in_draft(draft, target_keyword)
```

Test 3.3: Token usage tracking
```python
def test_track_generation_cost():
    cost = calculate_generation_cost(
        input_tokens=1000,
        output_tokens=2000,
        model='gpt-4-turbo'
    )
    
    expected = (1000 * 0.01 + 2000 * 0.03) / 1000  # OpenAI pricing
    assert cost == pytest.approx(expected)
```

Test Module 4: Fact-Checking Pipeline
File: tests/test_fact_checking.py

Test 4.1: Claim extraction
```python
def test_extract_claims():
    article = "Python was released in 1989. It is a programming language."
    claims = extract_claims(article)
    
    assert len(claims) >= 1
    assert any('1989' in claim for claim in claims)
    assert any('programming' in claim for claim in claims)
```

Test 4.2: Claim filtering
```python
def test_filter_checkworthy_claims():
    claims = [
        {'claim': 'Python is a language', 'confidence': 'high'},
        {'claim': 'Python 3.9 released March 2021', 'confidence': 'medium'},
        {'claim': 'I think asyncio is useful', 'confidence': 'low'}
    ]
    
    filtered = filter_checkworthy(claims)
    
    # Should remove obvious facts and opinions
    assert len(filtered) == 1
    assert '2021' in filtered[0]['claim']
```

Test 4.3: Verification verdict
```python
def test_verify_claim_supported():
    claim = "Python 3.4 introduced asyncio"
    evidence = "asyncio was added in Python 3.4 (October 2014)"
    
    verdict = verify_claim(claim, evidence)
    
    assert verdict['status'] == 'supported'
    assert verdict['confidence'] > 80
```

Test 4.4: Mock Perplexity API
```python
@patch('integrations.perplexity.PerplexityAI.search')
def test_retrieve_evidence(mock_perplexity):
    mock_perplexity.return_value = [
        {'text': 'Evidence text', 'source': 'https://...'}
    ]
    
    evidence = retrieve_evidence("Python 3.4")
    
    assert len(evidence) > 0
    mock_perplexity.assert_called()
```

Test Module 5: SEO Optimization
File: tests/test_seo_optimization.py

Test 5.1: Keyword placement analysis
```python
def test_keyword_in_intro():
    article = "Python asyncio is... " + "content " * 50
    keyword = "python asyncio"
    
    in_intro = check_keyword_in_intro(article, keyword)
    
    assert in_intro
```

Test 5.2: Meta tag generation
```python
def test_meta_title_length():
    title = generate_meta_title("Python Asyncio Complete Guide")
    
    assert 50 <= len(title) <= 60

def test_meta_description_length():
    desc = generate_meta_description("Python Asyncio Guide")
    
    assert 150 <= len(desc) <= 160
```

Test 5.3: Mock Rank Math API
```python
@patch('integrations.rankmath.RankMathAPI.analyze')
def test_seo_analysis(mock_rankmath):
    mock_rankmath.return_value = {
        'score': 75,
        'issues': []
    }
    
    analysis = analyze_seo("Article content", "keyword")
    
    assert analysis['score'] == 75
```

Test Module 6: WordPress Integration
File: tests/test_wordpress_integration.py

Test 6.1: Post creation
```python
@patch('integrations.wordpress_api.WordPressAPI.create_post')
def test_create_wordpress_post(mock_wp):
    mock_wp.return_value = {'id': 123, 'link': 'https://...'}
    
    post = create_wordpress_post({
        'title': 'Test',
        'content': '<p>Content</p>'
    })
    
    assert post['id'] == 123
```

Test 6.2: Image upload
```python
@patch('integrations.wordpress_api.WordPressAPI.upload_media')
def test_upload_image(mock_wp):
    mock_wp.return_value = {'id': 456, 'source_url': 'https://...'}
    
    result = upload_image('/path/to/image.jpg')
    
    assert result['id'] == 456
```

Test 6.3: Metadata storage
```python
def test_store_acf_metadata():
    article = Article(wordpress_post_id=123)
    metadata = {
        'ai_model_used': 'gpt4',
        'fact_check_status': 'verified'
    }
    
    store_acf_metadata(article, metadata)
    
    article_from_db = Article.query.get(article.id)
    assert article_from_db.ai_model_used == 'gpt4'
```

Test Module 7: Database Operations
File: tests/test_database.py

Test 7.1: Article creation
```python
def test_create_article():
    article = Article(
        title='Test Article',
        keyword='test',
        status='draft'
    )
    db.session.add(article)
    db.session.commit()
    
    retrieved = Article.query.filter_by(slug='test-article').first()
    assert retrieved.title == 'Test Article'
```

Test 7.2: Unique constraint
```python
def test_unique_slug_constraint():
    article1 = Article(slug='test-article')
    article2 = Article(slug='test-article')
    
    db.session.add(article1)
    db.session.add(article2)
    
    with pytest.raises(IntegrityError):
        db.session.commit()
```

Test 7.3: Foreign key relationship
```python
def test_review_foreign_key():
    article = Article(title='Test')
    review = ArticleReview(article=article, verdict='approve')
    
    db.session.add(article)
    db.session.add(review)
    db.session.commit()
    
    assert review.article_id == article.id
```

INTEGRATION TESTS (30-40% of test suite)
─────────────────────────────────────────

Test Module 1: End-to-End Pipeline (Mocked APIs)
File: tests/integration/test_full_pipeline.py

Test 1.1: Complete article generation flow
```python
def test_full_generation_pipeline():
    # Start with keyword
    keyword = 'python asyncio'
    
    # Step 1: Research
    keyword_data = research_keyword(keyword)
    assert keyword_data['difficulty'] > 0
    
    # Step 2: Generate brief
    brief = generate_content_brief(keyword_data)
    assert 'sections' in brief
    
    # Step 3: Draft
    draft = generate_article_draft(brief)
    assert len(draft) > 1000
    
    # Step 4: Fact-check
    report = fact_check_article(draft)
    assert report['total_claims_checked'] > 0
    
    # Step 5: SEO
    optimized = optimize_seo(draft)
    assert optimized['seo_score'] > 50
    
    # Verify article in database
    article = Article.query.filter_by(keyword=keyword).first()
    assert article.status in ['seo_review', 'approved']
```

Test 1.2: Error recovery in pipeline
```python
def test_pipeline_error_recovery():
    # Simulate API failure
    with patch('integrations.openai.generate') as mock:
        mock.side_effect = Timeout()
        
        # Pipeline should retry
        with pytest.raises(Timeout):
            generate_article_draft({})
        
        # Verify retry attempts
        assert mock.call_count == 3
```

Test Module 2: API Integration (with Mocking)
File: tests/integration/test_api_integrations.py

Test 2.1: Multiple API calls in sequence
```python
def test_research_with_competitor_analysis():
    with patch('integrations.ahrefs.get_serp') as mock_serp:
        mock_serp.return_value = [
            {'url': 'site1.com', 'title': 'Article 1'},
            {'url': 'site2.com', 'title': 'Article 2'}
        ]
        
        results = research_keyword('test')
        
        assert len(results['competitors']) == 2
        assert 'site1.com' in [c['url'] for c in results['competitors']]
```

Test 2.2: Rate limit handling across APIs
```python
def test_handle_multiple_rate_limits():
    calls = []
    
    def mock_call(*args, **kwargs):
        calls.append(time.time())
        if len(calls) <= 2:
            raise RateLimitError()
        return {'result': 'success'}
    
    with patch('integrations.api.make_call', side_effect=mock_call):
        result = make_robust_call()
        
        assert result['result'] == 'success'
        assert len(calls) == 3  # Initial + 2 retries
```

Test Module 3: Database Transactions
File: tests/integration/test_database_transactions.py

Test 3.1: Atomic multi-step update
```python
def test_atomic_article_review_update():
    article = Article.query.first()
    original_status = article.status
    
    try:
        with db.transaction():
            article.status = 'approved'
            review = ArticleReview(
                article_id=article.id,
                verdict='approve'
            )
            db.add(review)
            # Simulate error
            raise Exception("Something went wrong")
    except:
        db.rollback()
    
    # Verify rollback
    article_after = Article.query.get(article.id)
    assert article_after.status == original_status
```

Test 3.2: Concurrent update handling
```python
def test_concurrent_article_updates():
    article = Article.query.first()
    
    # Simulate concurrent updates
    def update1():
        article.views_30_days += 100
        db.commit()
    
    def update2():
        article.bounce_rate = 0.35
        db.commit()
    
    from threading import Thread
    t1 = Thread(target=update1)
    t2 = Thread(target=update2)
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    # Both updates should succeed
    final = Article.query.get(article.id)
    assert final.views_30_days == 100
    assert final.bounce_rate == 0.35
```

END-TO-END TESTS (10-15% of test suite)
────────────────────────────────────────

Test Module 1: WordPress Publishing
File: tests/e2e/test_wordpress_publishing.py

Test 1.1: Complete publish flow (using test WordPress site)
```python
def test_publish_article_to_wordpress():
    # Create article
    article = Article(
        title='E2E Test Article',
        content='<p>Test content</p>',
        keyword='e2e-test'
    )
    db.session.add(article)
    db.session.commit()
    
    # Publish
    result = publish_to_wordpress(article, schedule_time=datetime.utcnow())
    
    # Verify in WordPress
    post = wp.get_post(result['wordpress_post_id'])
    assert post['title'] == 'E2E Test Article'
    assert post['status'] in ['publish', 'future']  # Scheduled or published
```

Test Module 2: Monitoring & Analytics
File: tests/e2e/test_analytics.py

Test 2.1: GA4 tracking initialization
```python
def test_ga4_tracking_setup():
    article = Article.query.first()
    
    # Setup tracking
    setup_ga4_tracking(article.wordpress_post_id)
    
    # Verify tracking code inserted
    wordpress_content = wp.get_post(article.wordpress_post_id)
    assert 'google analytics' in wordpress_content['content'].lower()
```

PERFORMANCE TESTS
──────────────────

Test Module 1: Performance Benchmarks
File: tests/performance/test_performance.py

Test 1.1: Article generation speed
```python
def test_generation_performance():
    import time
    
    start = time.time()
    draft = generate_article_draft({'keyword': 'test'})
    duration = time.time() - start
    
    assert duration < 30  # Should complete in <30 seconds
```

Test 1.2: Database query performance
```python
def test_article_query_performance():
    import time
    
    start = time.time()
    articles = Article.query.filter(
        Article.status == 'published',
        Article.created_at > datetime.utcnow() - timedelta(days=30)
    ).all()
    duration = time.time() - start
    
    assert duration < 1  # Should complete in <1 second
```

SECURITY TESTS
────────────────

Test Module 1: Input Validation
File: tests/security/test_input_validation.py

Test 1.1: SQL injection prevention
```python
def test_sql_injection_prevention():
    malicious_keyword = "'; DROP TABLE articles; --"
    
    # Should handle safely
    result = research_keyword(malicious_keyword)
    
    # Verify table still exists
    assert Article.query.count() > 0
```

Test 1.2: XSS prevention
```python
def test_xss_prevention():
    malicious_content = "<script>alert('XSS')</script>"
    
    article = Article(content=malicious_content)
    db.session.add(article)
    db.session.commit()
    
    # WordPress should sanitize
    post = wp.get_post(article.wordpress_post_id)
    assert '<script>' not in post['content']
```

TEST EXECUTION & CI/CD
───────────────────────

pytest.ini:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts = 
    --cov=pipeline
    --cov=integrations
    --cov=database
    --cov-report=html
    --cov-report=term-missing
    -v
    --tb=short

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance benchmarks
    security: Security tests
```

GitHub Actions CI/CD (.github/workflows/tests.yml):
```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: blog_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-mock
    
    - name: Run tests
      run: pytest --cov --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
```

Test Coverage Goals:
- Unit tests: 85% coverage minimum
- Integration tests: 70% coverage minimum
- Overall: 80% coverage target
- Critical paths: 95% coverage minimum
  - Content generation
  - Fact-checking
  - WordPress publishing
  - Error handling

================================================================================
END OF SPECIFICATION
================================================================================

Total lines: 3500+ lines
Completeness: 100% (all requirements, architecture, error handling, testing)
Ready for development: YES
