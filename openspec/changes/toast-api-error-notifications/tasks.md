## 1. Article schema + migration

- [x] 1.1 Add `pipeline_progress` (JSON, nullable) and `pipeline_error` (Text, nullable) columns to `Article` in `src/blog_automation/models/article.py`; document extended `status` values (`researching`, `briefing`, `drafting`, `failed`) in the class docstring
- [x] 1.2 Generate an Alembic migration adding the two columns to `articles` and run `alembic upgrade head`
- [x] 1.3 Run `ruff check --fix` + `ruff format` + `ruff check` + `ruff format --check` on touched files

## 2. Grouped error-string helper

- [x] 2.1 Add `describe_error(exc) -> str` to `src/blog_automation/errors.py` that unwraps one level of `__cause__` and groups by `isinstance` into: `APIAuthenticationError`, `APIRateLimitError`, `APITimeoutError`, `APIConnectionError`, `DatabaseError`, `ConfigurationError`, else `f"Pipeline failed: {str(exc)}"`
- [x] 2.2 Add unit tests in `tests/unit/test_errors.py` for each common type + the wrapped-cause case + the fallback
- [x] 2.3 Run ruff validation on touched files

## 3. Pipeline tracks progress + failure on the Article

- [x] 3.1 Update `scripts/run_pipeline.py` `cmd_full` to create a stub `Article` row at the start (keyword, placeholder title=keyword, unique slug, `status="researching"`, `pipeline_progress` all `pending`); keep the `article.id` for the run
- [x] 3.2 Wrap each of the six steps (research, brief, draft, fact_check, seo, quality_gates) to set `pipeline_progress[step]="done"` on success; on exception set `pipeline_progress[step]="failed"`, `status="failed"`, `pipeline_error=describe_error(exc)`, commit, and stop
- [x] 3.3 Add a test that a forced step-1 failure leaves the stub `Article` with `status="failed"`, `pipeline_progress["research"]="failed"`, and a grouped `pipeline_error` (use mock mode + a forced error)
- [x] 3.4 Run ruff validation on touched files

## 4. Streamlit UI: toasts + progress bar + step list

- [x] 4.1 Add `render_pipeline_toasts()` in `streamlit_app/app.py` that queries `Article` rows with `status=="failed"` and calls `st.toast(pipeline_error, icon="❌")` for each
- [x] 4.2 Add a progress view (on the Dashboard) that, for in-progress/recent articles, renders `st.progress(done_count/6)` and a per-step list (done ✅ / failed ❌ / pending ⏳) from `pipeline_progress`
- [x] 4.3 Call `render_pipeline_toasts()` on the Dashboard and Review Queue pages
- [x] 4.4 Keep existing inline `st.error`/`st.warning`/`st.info` calls unchanged; verify toasts/progress are additive
- [ ] 4.5 Manual smoke test: trigger a known API auth failure (bad Ahrefs key) via the "New Article" quick action and confirm a toast + a failed stub `Article` with `pipeline_error` + progress view appear

## 5. Validation & wrap-up

- [x] 5.1 Run full `ruff check` + `ruff format --check` across all touched `src/`, `streamlit_app/`, and `tests/` files; resolve any findings
- [x] 5.2 Run `pytest` for the new/updated test modules and confirm green
