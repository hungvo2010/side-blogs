## 1. Dependency + ChatOpenAI setup

- [x] 1.1 Add `langchain-openai` to `pyproject.toml` dependencies; install in venv and confirm `from langchain_openai import ChatOpenAI` works
- [x] 1.2 Add a `ChatOpenAI` instance to `OpenRouterClient` (lazy-init, reusing `self.api_key` / `self.base_url` / `default_headers`); add a `_get_chat_model(model)` helper that returns a per-model `ChatOpenAI`
- [x] 1.3 Run `ruff check --fix` + `ruff format` + `ruff check` + `ruff format --check` on touched files

## 2. Rewrite extract_json with structured output

- [x] 2.1 Rewrite `extract_json()` in `openrouter_client.py`: pop `schema` from `**kwargs`; if schema provided, use `chat.with_structured_output(schema)` (function-calling) → `.model_dump()`; else use `chat.with_structured_output(method="json_mode")` → dict; invoke with the prompt + system_prompt messages
- [x] 2.2 Add a try/except around the structured-output call: on exception, fall back to the existing regex path (call `self.complete()`, regex-extract from fences / raw object, `json.loads`); if fallback also fails, raise `GenerationFailureError`
- [x] 2.3 Run ruff validation on touched files

## 3. Tests

- [x] 3.1 Add unit tests in `tests/unit/test_json_extraction.py`: mock `ChatOpenAI.with_structured_output` → returns dict (json_mode happy path); mock returns Pydantic instance (schema path); mock raises → regex fallback succeeds (fenced + raw); both fail → raises `GenerationFailureError`
- [x] 3.2 Verify the 4 existing call sites still work unchanged by running relevant unit tests (`test_errors.py`, `test_models.py`, pipeline tests if any)
- [x] 3.3 Run full `ruff check` + `ruff format --check` across all touched `src/` and `tests/` files; resolve any findings
- [x] 3.4 Run `pytest` for the new + existing test modules and confirm green