## Context

The AI Blog Automation platform raises a custom `AppError` hierarchy (`src/blog_automation/errors.py`) with subclasses like `APIAuthenticationError`, `APIRateLimitError`, `APITimeoutError`, `DatabaseError`, `ConfigurationError`. The base HTTP client raises `APIAuthenticationError` on a 401/403 from a 3rd-party API (e.g. Ahrefs). Pipeline steps such as `research_keyword()` catch these and re-raise a `ProcessingError` via `raise ... from e`, so the original exception stays on `__cause__`.

Two gaps prevent the user from learning what went wrong:

1. **No status/progress on the article.** The `full` pipeline (`scripts/run_pipeline.py:cmd_full`) runs six steps — research → brief → draft → fact-check → SEO → quality gates — but the `Article` row is only created at the **draft** step (`content_brief_to_draft` → `session.add(article)`). So when keyword research (step 1) fails with a 3rd-party API error, there is no `Article` row to record the failure on, and the UI has nothing to show. The dashboard launches the pipeline via `subprocess.Popen`, so the parent UI never learns it failed either.

2. **Flat error string.** Even where errors are caught, the UI only has `str(e)` — a raw traceback like `[proc_006] Keyword research failed: [api_003] Authentication failed: ["Error","Unauthorized"]`. The user gets no grouped, human-readable hint (e.g. "API authentication failed — check your API keys in .env").

Streamlit provides `st.toast(message, icon=...)` for non-blocking notifications and `st.progress(value)` for a progress bar. The existing inline `st.error`/`st.info`/`st.warning` calls throughout `app.py` should remain.

## Goals / Non-Goals

**Goals:**
- Track pipeline progress and failure on the `Article` row itself (no new table), so the Streamlit UI can show which steps are done/failed and a progress bar.
- Create the `Article` row at the **start** of the `full` pipeline (before research) so a step-1 failure is captured on the article.
- On failure, store a plain, human-readable error note produced by grouping the exception into common types.
- Surface failed articles to the user as a Streamlit **toast**; show per-step status and a progress bar in the UI.
- No new third-party dependencies.

**Non-Goals:**
- No new DB table — columns are added to the existing `Article` table.
- No files on disk for run status.
- No per-error-code mapping table / title-hint-icon dictionaries — one grouped string per common type.
- No `error_code`/`severity`/`context` propagation machinery — just a readable string.
- No `session_state` de-duplication tracking — the `Article` columns are the single source of truth.
- No real-time push; the UI reads the DB on each render.
- No retry/auto-recovery — toasts inform the user; the user acts.

## Decisions

### Decision 1: Track progress + failure in new columns on `Article` (no new table)
**Choice:** Add two columns to the existing `Article` model:
- `pipeline_progress` (JSON, nullable): `{step: "done"|"failed"|"pending"}` for the six steps `research`, `brief`, `draft`, `fact_check`, `seo`, `quality_gates`. Drives the progress bar and the per-step done/failed list.
- `pipeline_error` (Text, nullable): the human-readable failure note (the grouped string from `describe_error`).

The existing `status` column is reused and extended with pipeline-progress values (`researching`, `briefing`, `drafting`, plus the existing `fact_checking`/`seo_review`) and `failed` on failure. `status` is `String(50)` (not a DB enum), so new values need no enum migration — only the two new columns do.

**Why over alternatives:**
- *Alternative A — new `pipeline_runs` table.* Rejected per feedback: no new table; track on the article.
- *Alternative B — a single `last_error` column on `Article` only.* Insufficient: it can't drive a per-step progress bar or "which steps done" view, and it can't record step-1 failures unless the Article is created earlier (see Decision 2).
- *Alternative C — file-based status.* Rejected per feedback: no files.

**Why JSON for progress:** the `Article` model already uses JSON columns (`ai_tokens_used`, `fact_check_report`, `seo_analysis`), so the pattern is established. A JSON object of six step keys maps directly to a progress bar (done count / 6) and a step list, and extends trivially if steps are added.

### Decision 2: Create a stub `Article` row at the start of the `full` pipeline
**Choice:** `cmd_full` creates an `Article` row **before** step 1 (research), with `keyword=keyword`, a placeholder `title=keyword`, a unique `slug` (slugified keyword + short timestamp suffix to satisfy the `unique`/`nullable=False` constraints), `status="researching"`, and `pipeline_progress` initialized with all six steps `"pending"`. Each step then updates `pipeline_progress[step]` to `"done"` (or `"failed"` on error) and advances `status`; the placeholder `title`/`slug` are replaced when the draft step produces the real title.

**Why:** This is required for the Article-column approach to actually capture the reported bug — keyword research (step 1) currently fails before any `Article` exists. Creating the row at the start makes every step's progress and any step's failure recordable on the article the UI already knows how to list.

**Trade-off (accepted):** a failed step-1 run leaves a stub `Article` with no content. The UI surfaces it as a failed/progress entry (status `failed`, `pipeline_error` set) rather than hiding it — which is the desired behavior (the user wants to see what failed).

### Decision 3: `describe_error(exc)` groups exceptions into a readable string
**Choice:** A small helper `describe_error(exc) -> str` that unwraps one level of `__cause__` (to get past `ProcessingError`) and classifies the exception by `isinstance` against the common `AppError` subclasses, returning a fixed human-readable string per group:
- `APIAuthenticationError` → "API authentication failed — check your API keys in .env"
- `APIRateLimitError` → "API rate limit reached — wait a moment and retry"
- `APITimeoutError` → "Request to the API timed out — check your connection and retry"
- `APIConnectionError` → "Could not connect to the API service"
- `DatabaseError` → "Database error — check the database is running"
- `ConfigurationError` → "Configuration missing — check your .env file"
- otherwise → f"Pipeline failed: {str(exc)}"

**Why over alternatives:**
- *Alternative A — per-`ErrorCode` mapping dict with title/hint/icon.* Rejected per feedback: too complex.
- *Alternative B — show `str(exc)` verbatim.* Rejected: not grouped or actionable.

`isinstance` grouping reuses the existing exception hierarchy with no error-code tables and no severity logic.

### Decision 4: UI shows toast + per-step status + progress bar; no session_state de-dup
**Choice:** On each render, the dashboard queries `Article` rows with `status == "failed"` and calls `st.toast(pipeline_error, icon="❌")` for each. For articles in progress or recently run, the UI renders `st.progress(done_count / 6)` and a step list (research/brief/draft/fact_check/seo/quality_gates) showing done (✅) / failed (❌) / pending (⏳) per `pipeline_progress`. No `session_state` tracking of shown toasts — the DB columns are the single source of truth.

**Trade-off (accepted):** Streamlit reruns on every interaction, so a toast may repeat while an article stays `failed`. Per feedback, de-dup machinery is not wanted.

## Risks / Trade-offs

- **[Trade-off] Toasts repeat on rerun while an article is `failed`** → Accepted per feedback (no de-dup).
- **[Risk] Stub Article left on step-1 failure** → By design: it is the record of the failure (status `failed`, `pipeline_error` set). The UI shows it in the failed/progress view. If desired later, a cleanup could delete stubs with no content older than N days — not included now.
- **[Risk] DB unavailable** → The pipeline cannot proceed without the DB anyway, and the UI's existing inline `st.error("Database not connected")` alert already covers this.
- **[Risk] Subprocess killed (SIGKILL/OOM) before updating columns** → The article stays in its last step state (e.g. `status="researching"`). The UI can treat in-progress articles unchanged for longer than N minutes as "stalled".
- **[Risk] Migration required** → A small Alembic migration adds the two columns to `articles`; rollback drops them.
- **[Trade-off] Polling on render vs push** → Toasts/progress appear on the next render. Acceptable for a human-review tool; not a real-time push system.