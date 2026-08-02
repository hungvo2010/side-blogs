## ADDED Requirements

### Requirement: Structured output via `with_structured_output`
The `extract_json()` method SHALL use `ChatOpenAI.with_structured_output()` from `langchain-openai` to obtain structured JSON from the LLM, so that the API itself enforces valid JSON rather than relying on client-side regex parsing. The `ChatOpenAI` instance SHALL point at the same OpenRouter base URL and API key as the existing OpenAI client.

#### Scenario: JSON mode returns a dict
- **WHEN** `extract_json(prompt)` is called without a `schema` argument
- **THEN** the method SHALL use `with_structured_output(method="json_mode")` and return a `dict` (or `list`) parsed from the API's JSON-mode response

#### Scenario: Pydantic schema returns a validated dict
- **WHEN** `extract_json(prompt, schema=SomePydanticModel)` is called with a Pydantic schema
- **THEN** the method SHALL use `with_structured_output(schema)` (function-calling mode), receive a validated Pydantic instance, and return its `.model_dump()` as a `dict`

### Requirement: Regex fallback for unsupported models
If `with_structured_output()` raises an exception (indicating the model does not support structured output), the method SHALL fall back to the existing regex-based extraction (markdown fence extraction → `json.loads` → raw-object regex → `json.loads`). If the fallback also fails, the method SHALL raise `GenerationFailureError`.

#### Scenario: Structured output fails, regex fallback succeeds
- **WHEN** `with_structured_output()` raises an exception
- **AND** the raw response contains JSON extractable by the regex fallback
- **THEN** the method SHALL return the regex-extracted parsed JSON without raising

#### Scenario: Both structured output and fallback fail
- **WHEN** `with_structured_output()` raises an exception
- **AND** the regex fallback also fails to parse valid JSON
- **THEN** the method SHALL raise `GenerationFailureError` with a preview of the response

### Requirement: Existing extract_json signature preserved
The public `extract_json()` method SHALL preserve its existing signature and return type (`dict | list`), absorbing the new optional `schema` parameter via `**kwargs` so that existing call sites require no changes.

#### Scenario: Existing caller works unchanged
- **WHEN** an existing caller invokes `extract_json(prompt)` without `schema`
- **THEN** the method SHALL return a parsed `dict` or `list` as before, using structured output internally with the regex fallback if needed