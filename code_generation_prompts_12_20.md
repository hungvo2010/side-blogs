# AI Blog Content Automation System
## Code Generation Prompts (12-20)

---

### PROMPT 12: Content Brief Generation Pipeline

```
CONTEXT:
Step 4.2: Content Brief Generation
Duration: 2 hours
Dependencies: Steps 1.1-4.1
Deliverable: Brief generation → storage, integrated with Step 4.1

TASK DESCRIPTION:
Create the content brief generation pipeline. Takes keyword research results
and generates detailed, actionable briefs for writers/AI systems to follow.

INPUT:
- keyword: str
- keyword_metrics: from Ahrefs (volume, difficulty, intent)
- competitor_analysis: analysis of top 10 results

OUTPUT:
- ContentBrief saved to database
- Integrated with Article workflow

KEY FEATURES:
1. Generate structured H2 sections based on competitor analysis
2. Identify LSI keywords automatically
3. Create unique angle recommendations
4. Collect reference sources
5. Validate all required fields present
6. Store in database with article link

REQUIREMENTS:

A. Main Function (src/blog_automation/pipelines/brief_generation.py):

   def generate_content_brief(keyword: str, brief_id: int = None) -> ContentBrief:
       """
       Generate detailed content brief from keyword data.
       
       1. Fetch or create keyword research
       2. Generate H2 sections (call Claude)
       3. Identify LSI keywords
       4. Collect external sources
       5. Generate unique angle
       6. Validate completeness
       7. Save to database
       8. Return brief
       """

B. Section Generation (Using Claude):
   
   Prompt to Claude:
   ```
   Based on this keyword research, suggest H2 sections for a blog post:
   
   Keyword: {keyword}
   Search Intent: {intent}
   Difficulty: {difficulty}
   
   Top competitor H2 patterns:
   {competitor_h2_patterns}
   
   Return JSON: {
     "sections": [
       {
         "h2": "Section Title",
         "purpose": "Why this section",
         "target_length": "200-300 words",
         "key_points": ["point1", "point2"]
       }
     ]
   }
   ```

C. LSI Keyword Generation:
   
   - Fetch from Ahrefs related keywords
   - Or use Claude to generate related terms
   - Target: 10-15 LSI keywords
   - Store for keyword density checking

D. Source Collection:
   
   ```python
   def collect_sources(keyword: str, source_count: int = 10) -> List[dict]:
       """Collect authoritative sources to cite"""
       # Use Perplexity search
       results = perplexity.search(keyword, source_count=source_count)
       return results["sources"]
   ```

E. Unique Angle Generation:
   
   ```python
   def generate_unique_angle(keyword: str, competitors: List[dict]) -> str:
       """Generate unique perspective"""
       # Claude analyzes competitors and suggests unique angle
       prompt = f"""
       Based on these competitor articles for '{keyword}':
       {json.dumps(competitors)}
       
       Suggest a unique angle or perspective that sets this post apart.
       """
       angle = claude.message(prompt)
       return angle
   ```

F. Validation:
   
   ```python
   def validate_brief(brief: ContentBrief) -> Tuple[bool, List[str]]:
       """Validate brief has all required fields"""
       errors = []
       
       if not brief.brief_data.get("sections"):
           errors.append("No sections defined")
       elif len(brief.brief_data["sections"]) < 4:
           errors.append(f"Only {len(sections)} sections, need 4+")
       
       if not brief.brief_data.get("sources"):
           errors.append("No external sources")
       elif len(brief.brief_data["sources"]) < 5:
           errors.append(f"Only {len(sources)} sources, need 5+")
       
       if not brief.brief_data.get("unique_angle"):
           errors.append("No unique angle defined")
       
       if not brief.brief_data.get("lsi_keywords"):
           errors.append("No LSI keywords")
       
       return len(errors) == 0, errors
   ```

G. Integration with Step 4.1:
   
   ```python
   # In keyword research pipeline, add:
   
   def research_keyword_full(keyword: str, article_id: int = None):
       """Keyword research + brief generation"""
       # Step 1: Research (from prompt 11)
       brief = research_keyword(keyword, article_id)
       if not brief:
           return None
       
       # Step 2: Generate content brief (this prompt)
       content_brief = generate_content_brief(
           keyword=keyword,
           brief_id=brief.id
       )
       
       return content_brief
   ```

TESTING:

1. Full pipeline integration test
2. Section generation with Claude mock
3. LSI keyword extraction
4. Source collection
5. Unique angle generation
6. Validation tests (pass and fail cases)
7. Database storage verification

DELIVERABLES:
1. src/blog_automation/pipelines/brief_generation.py
2. src/blog_automation/pipelines/prompts/brief_generation_prompts.py
3. tests/integration/test_brief_generation_pipeline.py
4. Integration with Step 4.1
```

---

### PROMPT 13: Article Outline & Drafting Pipeline

```
CONTEXT:
Step 4.3 & 4.4: Article Outline + Drafting
Duration: 2 hours (combined)
Dependencies: Steps 1.1-4.2
Deliverable: Content brief → Article outline → Full draft

TASK DESCRIPTION:
Generate article outlines and full drafts using GPT-4. Store drafts in database
with cost tracking.

INPUT:
- ContentBrief object
- Target keyword
- Competitor analysis

OUTPUT:
- Article object with draft content
- Cost tracking
- Stored in database

KEY STEPS:
1. Create outline using Claude/GPT-4
2. Validate outline structure
3. Generate full draft using GPT-4 Turbo
4. Track tokens and costs
5. Store in database
6. Validate quality (word count, keyword presence)
7. Return article with draft

REQUIREMENTS:

A. Outline Generation:
   
   def generate_outline(brief: ContentBrief) -> str:
       """Generate article outline from brief"""
       
       prompt = f"""
       Create a detailed article outline for: {brief.keyword}
       
       Sections to include:
       {json.dumps(brief.brief_data["sections"])}
       
       Requirements:
       - H1: Main title
       - H2 for each section
       - 2-3 H3 subsections per H2
       - FAQ section at end
       - Include internal link opportunities
       
       Return markdown outline only.
       """
       
       outline = openai.complete(prompt, temperature=0.7, max_tokens=1000)
       return outline

B. Draft Generation:
   
   def generate_article_draft(brief: ContentBrief, outline: str) -> Article:
       """Generate full article draft"""
       
       system_prompt = """
       You are a professional blog writer. Generate engaging, well-researched content.
       
       Guidelines:
       - Conversational tone, avoid robotic language
       - Short paragraphs (2-3 sentences max)
       - Include real-world examples and use cases
       - Natural keyword integration (3-5 times total)
       - No keyword stuffing
       - Cite sources where appropriate
       - Internal link anchors: [anchor text](article-slug)
       """
       
       user_prompt = f"""
       Write a complete blog post following this outline:
       {outline}
       
       Target keyword: {brief.keyword}
       Unique angle: {brief.brief_data["unique_angle"]}
       Target word count: {brief.brief_data.get("target_word_count", 2000)}
       
       Required word count: {brief.brief_data.get("target_word_count", 2000)} words minimum
       """
       
       draft = openai.chat_complete(
           messages=[
               {"role": "system", "content": system_prompt},
               {"role": "user", "content": user_prompt}
           ],
           temperature=0.7,
           max_tokens=3000
       )
       
       # Create article
       article = Article(
           title=brief.keyword,  # Will be edited later
           slug=generate_slug(brief.keyword),
           keyword=brief.keyword,
           content_draft=draft,
           status="draft",
           ai_model_used="gpt4-turbo",
           ai_generation_cost=calculate_cost(tokens)
       )
       
       return article

C. Cost Tracking:
   
   ```python
   def calculate_cost(tokens_used: dict, model: str) -> float:
       """Calculate cost of generation"""
       pricing = {
           "gpt-4-turbo": {"input": 0.01, "output": 0.03},
           "gpt-3.5": {"input": 0.0005, "output": 0.0015}
       }
       
       rate = pricing[model]
       input_cost = (tokens_used["input"] / 1000) * rate["input"]
       output_cost = (tokens_used["output"] / 1000) * rate["output"]
       
       return input_cost + output_cost
   ```

D. Quality Validation:
   
   ```python
   def validate_draft_quality(article: Article, brief: ContentBrief):
       """Validate draft meets quality standards"""
       errors = []
       
       # Check word count
       word_count = len(article.content_draft.split())
       min_words = brief.brief_data.get("target_word_count", 1500)
       if word_count < min_words:
           errors.append(f"Only {word_count} words, need {min_words}")
       
       # Check keyword presence
       keyword = brief.keyword.lower()
       keyword_count = article.content_draft.lower().count(keyword)
       if keyword_count < 3:
           errors.append(f"Keyword appears {keyword_count} times, need 3-5")
       if keyword_count > 10:
           errors.append(f"Keyword appears {keyword_count} times (keyword stuffing)")
       
       # Check for obvious AI patterns
       ai_phrases = ["as an ai", "i don't have", "please note that"]
       for phrase in ai_phrases:
           if phrase in article.content_draft.lower():
               errors.append(f"Found obvious AI phrase: '{phrase}'")
       
       return len(errors) == 0, errors
   ```

E. Pipeline Integration:
   
   ```python
   def content_brief_to_draft(brief: ContentBrief) -> Article:
       """Complete pipeline: brief → outline → draft"""
       
       # Step 1: Generate outline
       outline = generate_outline(brief)
       logger.info(f"Generated outline for {brief.keyword}")
       
       # Step 2: Generate draft
       article = generate_article_draft(brief, outline)
       logger.info(f"Generated draft {article.word_count} words")
       
       # Step 3: Validate quality
       is_valid, errors = validate_draft_quality(article, brief)
       if not is_valid:
           logger.warning(f"Draft validation failed: {errors}")
           article.status = "draft_validation_failed"
           # Could retry with adjusted prompt
       
       # Step 4: Save to database
       session.add(article)
       session.commit()
       
       return article
   ```

TESTING:

1. Outline generation and structure
2. Draft generation with mocked GPT-4
3. Cost calculation accuracy
4. Quality validation (pass and fail)
5. Word count detection
6. Keyword presence validation
7. AI pattern detection
8. Database storage

DELIVERABLES:
1. src/blog_automation/pipelines/drafting.py
2. src/blog_automation/pipelines/prompts/drafting_prompts.py
3. tests/integration/test_drafting_pipeline.py
```

---

### PROMPT 14: Claim Extraction & Fact-Checking Pipeline

```
CONTEXT:
Step 4.5, 4.6, 4.7: Claim extraction, verification, reporting
Duration: 2 hours
Dependencies: Steps 1.1-4.4
Deliverable: Draft → Claims extracted → Verified → Report generated

TASK DESCRIPTION:
Extract factual claims from article, verify against web evidence, generate
fact-check report with issues and suggestions.

INPUT:
- Article with draft content

OUTPUT:
- List of extracted claims
- Fact-check report with verdicts
- Issue list with suggestions
- Article updated with report

KEY STEPS:
1. Extract claims from article (Claude)
2. Filter to checkworthy claims
3. Retrieve evidence for each claim (Perplexity)
4. Compare claim vs evidence (Claude)
5. Generate verdict and suggestions
6. Create fact-check report
7. Store in Article object
8. Update article status

REQUIREMENTS:

A. Claim Extraction:
   
   def extract_claims(content: str) -> List[dict]:
       """Extract factual claims from article"""
       
       prompt = f"""
       Extract all factual, verifiable claims from this article.
       Filter out common knowledge, opinions, and subjective statements.
       
       Article:
       {content}
       
       Return JSON: {{
         "claims": [
           {{
             "claim": "Exact claim text",
             "type": "historical|statistic|technical|definition",
             "confidence": "high|medium|low",
             "line_number": 45
           }}
         ]
       }}
       """
       
       response = claude.extract_json(prompt)
       return response["claims"]

B. Claim Filtering:
   
   def filter_checkworthy_claims(claims: List[dict]) -> List[dict]:
       """Keep only checkworthy claims"""
       
       filtered = []
       common_knowledge = [
           "is a",  # "Python is a language"
           "was invented",
           "is used for"
       ]
       
       for claim in claims:
           # Remove very common knowledge
           if any(kw in claim["claim"].lower() for kw in common_knowledge):
               if claim["confidence"] == "high":
                   continue
           
           # Keep if medium/high confidence
           if claim["confidence"] != "low":
               filtered.append(claim)
       
       return filtered[:10]  # Max 10 claims per article

C. Evidence Retrieval:
   
   def retrieve_evidence(claim: str) -> List[dict]:
       """Search web for evidence"""
       
       results = perplexity.search(
           query=f"Evidence for: {claim}",
           source_count=3
       )
       
       return results["sources"]

D. Claim Verification:
   
   def verify_claim(claim: str, evidence: List[dict]) -> dict:
       """Compare claim against evidence"""
       
       evidence_text = "\n".join([
           f"Source: {s['url']}\n{s['snippet']}"
           for s in evidence
       ])
       
       prompt = f"""
       Verify this claim against the provided evidence.
       
       Claim: {claim}
       
       Evidence:
       {evidence_text}
       
       Return JSON: {{
         "verdict": "supported|contradicted|unclear",
         "confidence": 0-100,
         "explanation": "...",
         "suggested_revision": "..." or null
       }}
       """
       
       result = claude.extract_json(prompt)
       return result

E. Fact-Check Report Generation:
   
   def generate_fact_check_report(article: Article, claims: List[dict]) -> dict:
       """Create comprehensive report"""
       
       report = {
           "total_claims_checked": len(claims),
           "supported": 0,
           "contradicted": 0,
           "unclear": 0,
           "issues_found": [],
           "generated_at": datetime.utcnow().isoformat()
       }
       
       for claim in claims:
           evidence = retrieve_evidence(claim["claim"])
           verdict = verify_claim(claim["claim"], evidence)
           
           report[verdict["verdict"].lower()] += 1
           
           if verdict["verdict"] != "supported":
               report["issues_found"].append({
                   "claim": claim["claim"],
                   "verdict": verdict["verdict"],
                   "explanation": verdict["explanation"],
                   "suggested_revision": verdict.get("suggested_revision")
               })
       
       report["accuracy_rate"] = (report["supported"] / report["total_claims_checked"]) * 100
       report["pass"] = report["contradicted"] == 0 and report["accuracy_rate"] >= 95
       
       return report

F. Pipeline Integration:
   
   def fact_check_article(article: Article) -> dict:
       """Complete fact-checking pipeline"""
       
       article.status = "fact_checking"
       session.commit()
       
       # Extract claims
       claims = extract_claims(article.content_draft)
       logger.info(f"Extracted {len(claims)} claims")
       
       # Filter to checkworthy
       checkworthy = filter_checkworthy_claims(claims)
       logger.info(f"Filtered to {len(checkworthy)} checkworthy claims")
       
       # Generate report
       report = generate_fact_check_report(article, checkworthy)
       
       # Store report
       article.fact_check_report = report
       article.fact_check_passed = report["pass"]
       article.fact_check_date = datetime.utcnow()
       article.fact_check_issues = len(report["issues_found"])
       
       # Update status
       if report["pass"]:
           article.status = "editing"
       else:
           article.status = "fact_checking_issues"
       
       session.commit()
       
       return report

TESTING:

1. Claim extraction and structure
2. Claim filtering logic
3. Evidence retrieval with mocked Perplexity
4. Claim verification with mocked Claude
5. Report generation
6. Pass/fail determination
7. Database storage
8. Issue tracking

DELIVERABLES:
1. src/blog_automation/pipelines/fact_checking.py
2. tests/integration/test_fact_checking_pipeline.py
```

---

### PROMPT 15: SEO Optimization Pipeline

```
CONTEXT:
Step 5.2 & 5.3: SEO analysis and meta tag optimization
Duration: 2 hours
Dependencies: Steps 1.1-4.7
Deliverable: Article with SEO analysis, scores, meta tags

TASK DESCRIPTION:
Analyze article for SEO, generate optimization recommendations, create meta
tags, update database with SEO metrics.

INPUT:
- Article with draft content
- Keyword

OUTPUT:
- SEO analysis and score
- Optimization recommendations
- Meta title and description
- Updated article with metrics

KEY FEATURES:
1. Rank Math API integration for scoring
2. Content length recommendations
3. Keyword density analysis
4. Meta tag generation
5. LSI keyword integration check
6. Internal/external link recommendations

REQUIREMENTS:

[Similar structure to prompts 12-14, with focus on SEO-specific logic]

DELIVERABLES:
1. src/blog_automation/pipelines/seo_optimization.py
2. tests/integration/test_seo_pipeline.py
```

---

### PROMPT 16: Quality Gates & Plagiarism Check

```
CONTEXT:
Step 5.1 & 5.4 & 5.5: Plagiarism, link verification, final gates
Duration: 2 hours
Dependencies: Steps 1.1-5.3
Deliverable: Article validated through all quality gates

TASK DESCRIPTION:
Run final quality checks before human review: plagiarism detection, link
verification, readability scoring, metadata completeness.

DELIVERABLES:
1. src/blog_automation/pipelines/quality_gates.py
2. tests/integration/test_quality_gates.py
```

---

### PROMPT 17: WordPress Publishing Pipeline

```
CONTEXT:
Step 6.1-6.6: Content formatting, image handling, WordPress publishing, analytics
Duration: 2 hours
Dependencies: Steps 1.1-5.5
Deliverable: Article published to WordPress with tracking enabled

TASK DESCRIPTION:
Convert article to HTML, upload images, create WordPress post, set metadata,
initialize analytics tracking.

DELIVERABLES:
1. src/blog_automation/pipelines/publishing.py
2. tests/integration/test_publishing_pipeline.py
```

---

### PROMPT 18: Human Review Interface & Task Queue

```
CONTEXT:
Step 7.3: Human review task queue and interface
Duration: 2 hours
Dependencies: Steps 1.1-6.6, 7.1-7.2
Deliverable: Review task queue, notifications, feedback capture

TASK DESCRIPTION:
Create task queue for human editors, notification system, review interface
(CLI or web), feedback capture, revision workflow.

KEY FEATURES:
1. Task queue in database
2. Email/Slack notifications
3. CLI interface for reviewing articles
4. Feedback capture
5. Revision loop (return to drafting if needed)
6. Approval → publish workflow

DELIVERABLES:
1. src/blog_automation/review/task_queue.py
2. src/blog_automation/review/interface.py (CLI)
3. tests/unit/test_review_queue.py
```

---

### PROMPT 19: Apache Airflow DAG Setup & Orchestration

```
CONTEXT:
Step 7.1-7.4: Airflow DAGs for complete orchestration
Duration: 2 hours
Dependencies: All previous steps
Deliverable: Working Airflow setup with complete DAG

TASK DESCRIPTION:
Create Apache Airflow DAG that orchestrates the complete pipeline:
keyword research → brief → drafting → fact-checking → SEO → human review →
publishing → analytics

KEY FEATURES:
1. Complete workflow DAG
2. Task dependencies
3. Daily scheduling (8 AM)
4. Error handling and retries
5. Notifications (email/Slack)
6. Monitoring dashboard
7. Success/failure handling

DAG STRUCTURE:

fetch_keyword → generate_brief → generate_draft → fact_check → seo_optimize →
quality_gates → create_review_task → [HUMAN REVIEW] → publish_to_wordpress →
setup_analytics → complete

DELIVERABLES:
1. airflow_dags/content_generation_dag.py - Main DAG
2. airflow_dags/task_operators.py - Custom operators
3. tests/integration/test_airflow_dag.py
4. Airflow configuration documentation
```

---

### PROMPT 20: Complete Test Suite & CI/CD Pipeline

```
CONTEXT:
Step 7.5-7.8: Testing, code quality, CI/CD, security
Duration: 3-4 hours
Dependencies: All previous steps
Deliverable: 80%+ test coverage, GitHub Actions CI/CD, security scanning

TASK DESCRIPTION:
Create comprehensive test suite covering all components, set up GitHub Actions
for automated testing, code quality checks, security scanning, and deployment.

KEY COMPONENTS:
1. Unit test suite (50-60% of tests)
2. Integration test suite (30-40% of tests)
3. E2E test suite (10-15% of tests)
4. Performance tests
5. Security tests (SQL injection, XSS, auth)
6. GitHub Actions workflows
7. Code coverage reporting
8. Security scanning (OWASP, dependency checks)

DELIVERABLES:
1. tests/ - Complete test suite
2. .github/workflows/tests.yml - CI workflow
3. pytest.ini - Test configuration
4. .pre-commit-config.yaml - Pre-commit hooks
5. Security scan configuration
6. Coverage reports
7. Deployment automation
```

---

## SUMMARY: Integration & Wiring Guide

### How All Pieces Connect

```
LAYER 1-3 (Foundation)
      ↓
LAYER 4 (Pipelines)
├─ Step 4.1: Keyword Research
│   ↓
├─ Step 4.2: Brief Generation (uses 4.1 output)
│   ↓
├─ Step 4.3-4.4: Drafting (uses 4.2 output)
│   ↓
├─ Step 4.5-4.7: Fact-Checking (uses 4.4 output)
│   ↓
├─ Step 5: Quality Gates (uses 4.7 output)
│   ↓
├─ Step 6: Publishing (uses 5 output)
│   ↓
      ↓
LAYER 5 (Orchestration)
├─ Step 7.1-7.4: Airflow DAGs orchestrate all pipelines
│   ├─ Calls keyword_research()
│   ├─ Calls brief_generation()
│   ├─ Calls fact_checking()
│   ├─ etc...
│   ↓
LAYER 6 (Human Review)
├─ Step 7.3: Creates review task
│   ├─ Sends email/Slack notification
│   ├─ Editor reviews via CLI
│   ├─ Approves or requests revision
│   ├─ If approved → publish
│   ├─ If revise → return to drafting
│   ├─ If reject → manual rewrite needed
│   ↓
LAYER 7 (Testing & QA)
└─ Step 7.5-7.8: All tests verify everything
    └─ CI/CD runs on every push
```

### No Orphaned Code

**Every piece is used:**
- Base HTTP client → Used by all API clients
- API clients → Used by all pipelines
- Pipelines → Orchestrated by Airflow
- Airflow → Triggers human review
- Human review → Triggers publishing
- Publishing → Triggers analytics
- Testing → Validates all above

**Each prompt builds on previous:**
1. Project structure (1)
2. Logging (2)
3. Config (3)
4. Database (4)
5. Migrations (5)
6. HTTP client (6) ← Used by 7-10
7. Ahrefs (7) ← Used by pipeline 12
8. OpenAI (8) ← Used by pipelines 13-14
9. Claude (9) ← Used by pipelines 12, 14
10. Perplexity (10) ← Used by pipeline 14
11. Keyword research (11) ← Input to 12
12. Brief generation (12) ← Input to 13
13. Drafting (13) ← Input to 14
14. Fact-checking (14) ← Input to 15
15. SEO (15) ← Input to 16
16. Quality gates (16) ← Input to 17
17. Publishing (17) ← Input to 18
18. Human review (18) ← Input to 19
19. Airflow (19) ← Orchestrates all 11-18
20. Testing (20) ← Tests all 1-19

---

## Testing Strategy Across All Prompts

### Per-Prompt Testing Pattern

**For each code generation prompt:**

1. **Unit tests** (specific to that step)
   - Isolation: Mock all dependencies
   - Speed: <1 second per test
   - Coverage: 85%+ of code

2. **Integration tests** (multiple components)
   - Real databases (test DB)
   - Mocked external APIs
   - Full flow within step

3. **E2E tests** (when appropriate)
   - Multiple steps together
   - Real-like data
   - Verify database state

### Cross-Prompt Testing

**After each new prompt is complete:**
- Verify it integrates with previous steps
- Run all previous tests (nothing broke)
- Test the combined flow
- Update Airflow DAG tests

---

## Implementation Tips

1. **Start each prompt** by running previous tests (nothing broke)
2. **Build incrementally** - don't jump to complex features
3. **Test early and often** - write tests as you code
4. **Mock external APIs** - don't burn real API quotas
5. **Database migrations** - run them first, verify schema
6. **Logging everywhere** - debug pipeline issues
7. **Error handling** - explicitly handle each failure mode
8. **Documentation** - update as you go
9. **Code review** - have prompts reviewed before shipping
10. **Staging test** - run full pipeline in test environment

---

## Success Metrics

**After all 20 prompts:**
- ✅ 80%+ test coverage
- ✅ All pipelines working end-to-end
- ✅ Airflow DAG executes successfully
- ✅ Human review interface functional
- ✅ Articles publishing to WordPress
- ✅ No hanging code
- ✅ No orphaned functions
- ✅ All tests passing
- ✅ CI/CD pipeline green
- ✅ Ready for production MVP

---

## FAQ & Troubleshooting

**Q: Can I do multiple prompts in parallel?**
A: Only if they don't depend on each other. Prompts 1-5 can be parallel. Prompts 7-10 can be parallel. Everything else should be sequential.

**Q: What if an API changes?**
A: Update just that API client (prompts 7-10). Other code doesn't change because of abstraction layer.

**Q: How do I test without real API keys?**
A: All prompts use mocking. Mock external APIs in tests. Only integration tests use real keys (and only in CI/CD secrets).

**Q: What's the minimum viable product?**
A: Steps 1-5 + 11-14 + 19 = Basic working system that generates articles (no human review). Add 15-18 + 20 for full production system.

**Q: How long does each prompt really take?**
A: Estimates are for experienced Python developers. First-timers might take 1.5-2x longer. Use estimates as guide, not gospel.

**Q: Do I need all these tests?**
A: For production MVP, yes. For learning/experimentation, you can skip some but keep critical paths (pipelines, publishing, error handling).
```
