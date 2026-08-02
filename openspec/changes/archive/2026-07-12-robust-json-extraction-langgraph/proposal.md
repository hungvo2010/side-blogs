## Why

The `extract_json()` method in `openrouter_client.py` is the single point through which all structured LLM output flows (brief sections, LSI keywords, extracted claims, fact-check results). It uses greedy regex to find JSON in the model's response and parses it exactly once — if that parse fails, it raises `GenerationFailureError` and kills the pipeline step. This is fragile: LLMs routinely wrap JSON in markdown fences, emit trailing commas, truncate output, or surround the JSON with prose. A single malformed response breaks brief generation or fact-checking.

## What Changes

- Replace the regex-based `extract_json()` with **`ChatOpenAI.with_structured_output()`** from `langchain-openai`. Since OpenRouter is OpenAI-compatible, `ChatOpenAI` points at the same OpenRouter base URL — the API itself enforces valid JSON (JSON mode) or a Pydantic schema (function calling), eliminating client-side regex parsing entirely.
- No LangGraph, no JSON cleaner, no retry/repair loop — the structured-output API handles validation natively.
- Preserve the existing `extract_json()` signature so the 4 current call sites keep working unchanged; accept an optional Pydantic `schema` via `**kwargs` for opt-in schema-validated extraction.
- Keep the old regex approach as a **fallback** for models that don't support structured output (e.g. some OpenRouter-routed models).

## Capabilities

### New Capabilities
- `json-extraction`: Robust extraction of structured JSON from LLM responses using the OpenAI-compatible structured-output API (`with_structured_output`), with a regex fallback for unsupported models.

### Modified Capabilities
<!-- No existing specs require requirement-level changes. -->

## Impact

- **`src/blog_automation/integrations/openrouter_client.py`**: add a `ChatOpenAI` instance; rewrite `extract_json()` to use `with_structured_output()` with a regex fallback.
- **`pyproject.toml`**: add `langchain-openai` as a new dependency (provides `ChatOpenAI`; pulls `langchain-core` transitively).
- **4 call sites** (`brief_generation.py` ×2, `fact_checking.py` ×2): no signature change required.
- **Tests**: unit tests for `extract_json()` with mocked `ChatOpenAI` (structured output succeeds, fallback path, schema validation).
