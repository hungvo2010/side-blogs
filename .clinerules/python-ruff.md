# Python validation with Ruff

**Rule:** After *every* Python code change, validate it with `ruff` before considering the task done. This is mandatory, not optional.

Ruff is installed **globally** (`ruff` is on PATH via pipx; `ruff 0.15.21`+). Project configuration lives in `ai-blog-automation/pyproject.toml` under `[tool.ruff]` (line-length 88, black-compatible, target py311).

## Required steps after editing any `.py` file

Run these from the `ai-blog-automation/` directory, on the file(s) you touched (or on `src`/`tests` if a change spans many files):

1. **Lint + auto-fix**
   ```bash
   ruff check --fix src/blog_automation/path/to/file.py
   ```
2. **Format**
   ```bash
   ruff format src/blog_automation/path/to/file.py
   ```
3. **Verify clean — must exit 0 with no findings:**
   ```bash
   ruff check src/blog_automation/path/to/file.py
   ruff format --check src/blog_automation/path/to/file.py
   ```

## Requirements
- Do **not** mark a Python task complete while `ruff check` reports any error on the files you edited. Re-run until clean.
- If `ruff check --fix` cannot auto-fix an issue (e.g. `E501` line-too-long, `F841` unused-variable), fix it manually.
- Never add inline `# noqa` suppressions without a one-line comment explaining why.
- `ruff` **replaces** flake8, isort, and black for validation/formatting of new fixes. Do not invoke those legacy tools for new changes.
- `migrations/` (auto-generated Alembic) and `dist/` are excluded via `extend-exclude` — do not lint them.

## Scope
This rule applies to files you **edit or create** during a task. It does **not** require fixing pre-existing lint debt in untouched files (that is tracked separately — as of this commit there are ~237 findings under `E,W,F,I` and 19 files not ruff-formatted, mostly unused imports and whitespace).
