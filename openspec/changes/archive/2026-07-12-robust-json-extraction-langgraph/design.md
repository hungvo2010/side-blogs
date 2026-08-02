## Context

`OpenRouterClient.extract_json()` is the single chokepoint for all structured LLM output in the platform. Four critical pipeline steps call it:

| Caller | File | Expected key |
|---|---|---|
| Section generation | `phase_2_brief/brief_generation.py:241` | `sections` |
| LSI keywords | `phase_2_brief/brief_generation.py:296` | `lsi_keywords` |
| Claim extraction | `phase_4_fact_check/fact_checking.py:83` | `claims` |
| Fact verification | `phase_4_fact_check/fact_checking.py:179` | (varies) |

The current implementation (lines 303–341) appends "Respond with valid JSON only" to the system prompt, calls `complete()`, then regex-extracts JSON from the response and `json.loads()` it once or twice. If both attempts fail, it raises `GenerationFailureError` and kills the pipeline step. The greedy regex (`(\{[\s\S]*\})`) matches from the first `{` to the last `}`, swallowing prose and nested objects.

OpenRouter is an **OpenAI-compatible** API. `langchain-openai` provides `ChatOpenAI`, which can point at any OpenAI-compatible endpoint by setting `base_url`. Its `.with_structured_output()` method makes the **API itself** enforce valid JSON (via `response_format: json_mode`) or a Pydantic schema (via function calling) — eliminating client-side regex parsing entirely. Neither `langchain-openai` nor `langgraph` is currently a dependency.

## Goals / Non-Goals

**Goals:**
- Replace the fragile regex-based `extract_json()` with `ChatOpenAI.with_structured_output()`, so the API enforces valid JSON/schema natively — no client-side parsing.
- Keep a regex fallback for models that don't support structured output.
- Preserve the existing `extract_json()` signature so the 4 call sites need no changes.
- Accept an optional Pydantic `schema` via `**kwargs` for callers that want full schema validation.

**Non-Goals:**
- No LangGraph, no retry/repair loop, no JSON cleaner — the structured-output API handles validation.
- No changing the 4 call sites' signatures.
- No replacing `chat_complete()` / `complete()` / the OpenAI SDK for non-structured calls.
- No defining Pydantic schemas for all 4 call sites in this change (optional `schema` param is additive; callers can opt in later).

## Decisions

### Decision 1: Use `ChatOpenAI.with_structured_output()` (not LangGraph, not raw regex)
**Choice:** Add `langchain-openai` as a dependency. Create a `ChatOpenAI` instance in `OpenRouterClient` pointing at the same OpenRouter base URL / API key. Rewrite `extract_json()` to call `.with_structured_output()` — the API enforces valid JSON natively. No LangGraph, no JSON cleaner, no retry loop.

**Why over alternatives:**
- *Alternative A — LangGraph state graph.* Rejected per feedback: too complex for this use case. The structured-output API already handles validation; no retry/repair loop is needed.
- *Alternative B — raw `response_format={"type": "json_object"}` on the existing `openai.OpenAI` client.* This works but only enforces JSON mode (valid JSON, no schema). `with_structured_output` additionally supports Pydantic schema validation via function calling, which is more robust for callers that declare their expected shape.
- *Alternative C — keep the regex, just make it less greedy.* Cosmetic; doesn't solve the fundamental problem (LLM output isn't guaranteed to be parseable JSON).

### Decision 2: JSON mode by default, Pydantic schema opt-in
**Choice:** `extract_json()` uses `with_structured_output(method="json_mode")` by default (returns a `dict`, works with any model that supports JSON mode). When a caller passes `schema=SomePydanticModel` via `**kwargs`, it uses `with_structured_output(schema)` (function-calling mode, returns a validated Pydantic instance → `.model_dump()`).

**Why:** JSON mode is the most widely supported (OpenAI, many OpenRouter-routed models). Function-calling/schema mode is stricter but not all models support it. Defaulting to JSON mode maximizes compatibility; the schema opt-in is for callers that need structural guarantees.

### Decision 3: Regex fallback for unsupported models
**Choice:** If `with_structured_output()` raises (model doesn't support JSON mode or function calling), fall back to the existing regex-based extraction (markdown fence → `json.loads` → raw object regex → `json.loads`). This preserves behavior for edge-case models without penalizing the common case.

**Why over alternatives:**
- *Alternative — no fallback, require structured-output support.* Would break for models like Perplexity that may not support JSON mode via OpenRouter. The fallback costs nothing on the happy path (only runs on exception).

### Decision 4: Preserve the `extract_json()` signature
**Choice:** The public signature stays `extract_json(self, prompt, system_prompt=None, model=None, **kwargs) -> dict | list`. The optional `schema` is popped from `**kwargs` (not forwarded to the LLM). Return type stays `dict | list`. No caller changes required.

**Why:** The 4 call sites are in production pipeline code; changing the signature is a **BREAKING** change we want to avoid.

## Risks / Trade-offs

- **[Risk] Not all OpenRouter models support structured output** → Mitigation: regex fallback (Decision 3) preserves the old behavior for unsupported models.
- **[Risk] New dependency (`langchain-openai` + `langchain-core`)** → Mitigation: pin versions; `langchain-openai` is lightweight and pure-Python. The `ChatOpenAI` instance reuses the same OpenRouter base URL / API key — no new auth or config.
- **[Risk] `with_structured_output(method="json_mode")` requires "json" in the prompt** → Mitigation: `extract_json()` already appends "Respond with valid JSON only" to the system prompt, which satisfies this requirement.
- **[Trade-off] JSON mode enforces valid JSON but not a specific schema** → Accepted for the default path; callers that need schema validation opt in via the `schema` parameter.