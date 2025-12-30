# AI Blog Automation - Article Creation Flow

## Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AI BLOG AUTOMATION - ARTICLE FLOW                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. KEYWORD  │────▶│  2. BRIEF    │────▶│  3. DRAFT    │────▶│ 4. FACT-CHECK│
│   RESEARCH   │     │  GENERATION  │     │  GENERATION  │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
      │                    │                    │                    │
      ▼                    ▼                    ▼                    ▼
   Ahrefs API          Claude API           GPT-4 API          Perplexity +
   • Volume            • H2 sections        • Full article      Claude API
   • Difficulty        • LSI keywords       • 1500+ words      • Extract claims
   • SERP features     • Sources            • Outline first    • Verify facts
   • Competitors       • Unique angle       • Quality check    • Report

      │                    │                    │                    │
      ▼                    ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ ContentBrief │     │ ContentBrief │     │   Article    │     │   Article    │
│   (basic)    │     │   (full)     │     │   (draft)    │     │ (fact-checked)│
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘

                              ▼

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   5. SEO     │────▶│ 6. QUALITY   │────▶│  7. HUMAN    │────▶│ 8. PUBLISH   │
│ OPTIMIZATION │     │    GATES     │     │   REVIEW     │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
      │                    │                    │                    │
      ▼                    ▼                    ▼                    ▼
   RankMath +          Copyscape +          CLI Interface      WordPress API
   GPT-4 API           Link checker         • View article     • Create post
   • Meta title        • Plagiarism <3%     • See reports      • Upload images
   • Meta desc         • Readability        • Approve/Reject   • Set metadata
   • Keyword density   • Link validation    • Request edits    • Schedule/Publish
   • Internal links    • Metadata check

      │                    │                    │                    │
      ▼                    ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Article    │     │   Article    │     │ArticleReview │     │   Article    │
│ (optimized)  │     │(gates passed)│     │  (approved)  │     │ (published)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

---

## Pipeline Steps Detail

### Step 1: Keyword Research
**Function:** `research_keyword(keyword)`  
**Input:** Keyword string  
**Output:** ContentBrief (basic)

**What it does:**
- Calls Ahrefs API for search volume, difficulty, SERP features
- Analyzes top competitor pages
- Creates initial ContentBrief with SEO data

```python
from blog_automation.pipelines import research_keyword

brief = research_keyword("python web scraping tutorial")
print(f"Volume: {brief.search_volume}, Difficulty: {brief.difficulty}")
```

---

### Step 2: Brief Generation
**Function:** `generate_content_brief(brief)`  
**Input:** ContentBrief (basic)  
**Output:** ContentBrief (full)

**What it does:**
- Uses Claude to generate H2 section structure
- Extracts LSI keywords for semantic coverage
- Collects external sources via Perplexity
- Creates unique angle for differentiation

```python
from blog_automation.pipelines import generate_content_brief

full_brief = generate_content_brief(brief)
print(f"Sections: {len(full_brief.get_sections())}")
print(f"LSI Keywords: {full_brief.get_lsi_keywords()}")
```

---

### Step 3: Draft Generation
**Function:** `content_brief_to_draft(brief)`  
**Input:** ContentBrief (full)  
**Output:** Article (draft)

**What it does:**
- Generates outline using Claude
- Creates full article using GPT-4 Turbo
- Validates word count (1500+ words)
- Checks keyword presence and density
- Tracks token usage and cost

```python
from blog_automation.pipelines import content_brief_to_draft

article = content_brief_to_draft(full_brief)
print(f"Title: {article.title}")
print(f"Words: {article.word_count}")
print(f"Cost: ${article.generation_cost:.2f}")
```

---

### Step 4: Fact-Checking
**Function:** `fact_check_article(article)`  
**Input:** Article (draft)  
**Output:** Fact-check report

**What it does:**
- Extracts factual claims using Claude
- Filters to checkworthy claims only
- Retrieves evidence via Perplexity search
- Verifies each claim against evidence
- Generates accuracy report

```python
from blog_automation.pipelines import fact_check_article

report = fact_check_article(article)
print(f"Claims checked: {report['total_claims']}")
print(f"Accuracy: {report['accuracy_rate']}%")
print(f"Pass: {report['passed']}")
```

---

### Step 5: SEO Optimization
**Function:** `seo_optimize_article(article)`  
**Input:** Article (fact-checked)  
**Output:** Article (optimized)

**What it does:**
- Analyzes content with RankMath
- Generates meta title (50-60 chars)
- Generates meta description (150-160 chars)
- Checks keyword placement
- Suggests internal links

```python
from blog_automation.pipelines import seo_optimize_article

optimized = seo_optimize_article(article)
print(f"Meta Title: {optimized.meta_title}")
print(f"SEO Score: {optimized.seo_score}")
```

---

### Step 6: Quality Gates
**Function:** `run_quality_gates(article)`  
**Input:** Article (optimized)  
**Output:** Gate results

**What it does:**
- Checks plagiarism via Copyscape (<3%)
- Verifies all links are working
- Calculates readability score
- Validates metadata completeness

```python
from blog_automation.pipelines import run_quality_gates

results = run_quality_gates(article)
print(f"Plagiarism: {results['plagiarism']['percentage']}%")
print(f"Readability: {results['readability']['score']}")
print(f"All gates passed: {results['passed']}")
```

---

### Step 7: Human Review
**Interface:** CLI commands  
**Input:** Article (gates passed)  
**Output:** ArticleReview (approved/rejected)

**Commands:**
```bash
# List pending reviews
poetry run python -m blog_automation.review list

# Review specific article
poetry run python -m blog_automation.review review <article_id>

# View stats
poetry run python -m blog_automation.review stats
```

---

### Step 8: Publish
**Function:** `publish_article(article)`  
**Input:** Article (approved)  
**Output:** Article (published)

**What it does:**
- Converts markdown to HTML
- Uploads images to WordPress
- Creates WordPress post
- Sets categories, tags, featured image
- Stores ACF metadata
- Initializes analytics tracking

```python
from blog_automation.pipelines import publish_article

published = publish_article(article)
print(f"URL: {published.wordpress_url}")
print(f"Post ID: {published.wordpress_post_id}")
```

---

## Quick Reference Table

| Step | Function | Input | Output | APIs Used |
|------|----------|-------|--------|-----------|
| 1 | `research_keyword()` | keyword | ContentBrief | Ahrefs |
| 2 | `generate_content_brief()` | ContentBrief | ContentBrief | Claude, Perplexity |
| 3 | `content_brief_to_draft()` | ContentBrief | Article | Claude, GPT-4 |
| 4 | `fact_check_article()` | Article | Report | Claude, Perplexity |
| 5 | `seo_optimize_article()` | Article | Article | RankMath, GPT-4 |
| 6 | `run_quality_gates()` | Article | Results | Copyscape |
| 7 | Human Review (CLI) | Article | Review | - |
| 8 | `publish_article()` | Article | Article | WordPress |

---

## Full Pipeline Example

```python
from blog_automation.pipelines import (
    research_keyword_full,
    content_brief_to_draft,
    fact_check_article,
    seo_optimize_article,
    run_quality_gates,
    publish_article,
)

# Steps 1-2: Research and Brief
brief = research_keyword_full("python web scraping tutorial")

# Step 3: Generate Draft
article = content_brief_to_draft(brief)

# Step 4: Fact-Check
fact_check_article(article)

# Step 5: SEO Optimize
seo_optimize_article(article)

# Step 6: Quality Gates
gates = run_quality_gates(article)

if gates['passed']:
    # Step 7: Human review happens via CLI
    # Step 8: Publish (after approval)
    publish_article(article)
```

---

## Airflow DAG (Automated)

The system can run automatically via Apache Airflow:

```
Daily at 8 AM:
  fetch_keyword → generate_brief → generate_draft → fact_check 
       → seo_optimize → quality_gates → create_review_task
       
After Human Approval:
  publish → setup_analytics → complete
```

See `airflow_dags/content_generation_dag.py` for full implementation.
