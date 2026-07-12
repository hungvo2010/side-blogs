## Why

When a pipeline step fails because of a 3rd-party API problem (e.g. Ahrefs returning `401 Unauthorized`), the user only sees a generic `Failed to start pipeline` in the dashboard and a raw traceback in the console — no hint about *which* API failed or what to fix. The `full` pipeline runs six steps (research → brief → draft → fact-check → SEO → quality gates), but the `Article` row is only created at the **draft** step, so a step-1 (keyword research) failure leaves nothing in the DB to show, and the UI has no progress or failure indicator.

## What Changes

- Add two columns to the existing `Article` table (**no new table**): `pipeline_progress` (JSON — per-step `done`/`failed`/`pending`) and `pipeline_error` (Text — the failure note).
- Create a stub `Article` row at the **start** of the `full` pipeline (before research) so a step-1 failure is captured on the article; update per-step progress as each step completes or fails.
- On failure, store a plain, human-readable error string produced by grouping the exception into common types (API auth, rate limit, timeout, connection, database, configuration, generic).
- Surface failed articles as Streamlit **toast** notifications, and show a **progress bar** plus a per-step done/failed list in the UI.
- Keep existing inline `st.error`/`st.warning`/`st.info` behavior; toasts and the progress view are additive.
- No new table, no files on disk, no error-code/severity mapping tables, no session-state de-duplication — the `Article` columns are the single source of truth.

## Capabilities

### New Capabilities
- `error-notification`: Tracks pipeline progress and failure on the `Article` row and surfaces it to the dashboard user via toast notifications, a per-step status list, and a progress bar.

### Modified Capabilities
<!-- No existing specs in openspec/specs/ — all behavior here is new. -->

## Impact

- **`Article` model** (`src/blog_automation/models/article.py`): add `pipeline_progress` (JSON) and `pipeline_error` (Text) columns; extend `status` usage with `researching`/`briefing`/`drafting`/`failed`. Alembic migration required.
- **New helper `describe_error(exc) -> str`** in `src/blog_automation/errors.py`: groups exceptions into common readable types.
- **`scripts/run_pipeline.py` (`cmd_full`)**: create a stub `Article` at the start; wrap each step to update `pipeline_progress`/`status` and set `pipeline_error` + `status="failed"` on failure.
- **`streamlit_app/app.py`**: query failed articles → `st.toast`; render `st.progress` + per-step list for in-progress/recent articles.
- **Dependencies**: none new (`st.toast` and `st.progress` ship with Streamlit).
