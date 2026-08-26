"""OpenRouter API client - the single LLM gateway for the platform.

All AI/LLM work (drafting, fact-checking, brief generation, SEO meta
generation, and web-search/evidence retrieval) flows through this one
client. OpenRouter exposes an OpenAI-compatible Chat Completions endpoint
(https://openrouter.ai/api/v1), so we reuse the official ``openai`` SDK
pointed at OpenRouter's base URL and pick the upstream model via the
``model`` field (e.g. ``openai/gpt-4o``, ``anthropic/claude-3.5-sonnet``,
``perplexity/llama-3.1-sonar-large-128k-online``).

This replaces the previous per-provider split (OpenAIClient, ClaudeClient,
PerplexityClient) with a single entry point.
"""

import json
import re
from datetime import datetime
from typing import Any, Generator

import openai
from langchain_openai import ChatOpenAI
from openai import OpenAI

from blog_automation.config import get_settings
from blog_automation.errors import (
    APIAuthenticationError,
    APIRateLimitError,
    APIServerError,
    APITimeoutError,
    GenerationFailureError,
)
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


# Rough per-1K-token pricing used only for cost estimation when OpenRouter
# does not report a cost. Keys are OpenRouter model slugs (or prefixes).
# Unknown models fall back to a conservative default.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "openai/gpt-4o": {"input": 0.005, "output": 0.015},
    "openai/gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "openai/gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "anthropic/claude-3.5-sonnet": {"input": 0.003, "output": 0.015},
    "anthropic/claude-3-opus": {"input": 0.015, "output": 0.075},
    "anthropic/claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "perplexity/llama-3.1-sonar-large-128k-online": {"input": 0.001, "output": 0.001},
    "google/gemini-flash-1.5": {"input": 0.000075, "output": 0.0003},
}
_DEFAULT_PRICING = {"input": 0.005, "output": 0.015}


class CostTracker:
    """Tracks API usage costs."""

    def __init__(self):
        self.requests: list[dict] = []

    def log_request(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> None:
        """Log an API request."""
        self.requests.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
            }
        )

    def get_total_cost(self) -> float:
        """Get total cost of all requests."""
        return sum(r["cost"] for r in self.requests)

    def get_daily_cost(self, date_str: str | None = None) -> float:
        """Get cost for a specific day (YYYY-MM-DD)."""
        if date_str is None:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return sum(
            r["cost"] for r in self.requests if r["timestamp"].startswith(date_str)
        )

    def get_cost_by_model(self) -> dict[str, float]:
        """Get costs grouped by model."""
        costs: dict[str, float] = {}
        for r in self.requests:
            costs[r["model"]] = costs.get(r["model"], 0) + r["cost"]
        return costs


class OpenRouterClient:
    """Single LLM gateway backed by the OpenRouter API.

    Provides the unified methods used across the pipelines:
    - chat_complete / complete  -> general text generation (drafting, SEO meta)
    - message / extract_json     -> structured/JSON generation (briefs, claims)
    - search / get_evidence / verify_fact -> web-search-backed evidence retrieval
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        search_model: str | None = None,
        site_url: str | None = None,
    ):
        """Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key (falls back to settings)
            base_url: OpenRouter base URL (defaults to the public endpoint)
            default_model: Default model slug for generation tasks
            search_model: Model slug used for web-search/evidence tasks
            site_url: Optional site URL sent as HTTP-Referer for rankings
        """
        import os

        settings = get_settings()
        # Optional primary override → OpenCode/Zen (deepseek-v4-flash).
        # When OPENCODE_BASE_URL + OPENCODE_API_KEY are set, generation uses
        # that OpenAI-compatible endpoint as PRIMARY and OpenRouter becomes
        # the retry fallback on rate-limit. Otherwise OpenRouter is primary.
        oc_base = os.environ.get("OPENCODE_BASE_URL") or ""
        oc_key = os.environ.get("OPENCODE_API_KEY") or ""
        oc_model = os.environ.get("OPENCODE_MODEL") or "deepseek-v4-flash"

        self.site_url = site_url or settings.openrouter_site_url

        if oc_base and oc_key:
            self.api_key = oc_key
            self.base_url = oc_base
            self.default_model = default_model or oc_model
            # The opencode endpoint only serves OPENCODE_MODEL, so the online
            # search must use it too (an OpenRouter slug here would 401).
            self.search_model = oc_model
            self.primary_is_openrouter = False
        else:
            self.api_key = api_key or settings.openrouter_api_key
            self.base_url = base_url or settings.openrouter_base_url or self.BASE_URL
            self.default_model = default_model or settings.openrouter_default_model
            self.search_model = search_model or settings.openrouter_search_model
            self.primary_is_openrouter = True

        if not self.api_key:
            raise APIAuthenticationError(
                message=(
                    "LLM API key not configured "
                    "(set OPENCODE_API_KEY or OPENROUTER_API_KEY)"
                ),
                service="llm",
            )

        default_headers: dict[str, str] = {"X-Title": "AI Blog Automation"}
        if self.site_url:
            default_headers["HTTP-Referer"] = self.site_url

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers=default_headers,
        )

        # OpenRouter fallback client (used when primary is rate-limited/429).
        self._fallback: dict[str, Any] | None = None
        if not self.primary_is_openrouter:
            or_key = settings.openrouter_api_key
            if or_key:
                self._fallback = {
                    "client": OpenAI(
                        api_key=or_key,
                        base_url=self.BASE_URL,
                        default_headers=default_headers,
                    ),
                    "model": settings.openrouter_default_model,
                }

        self.cost_tracker = CostTracker()
        self.total_cost = 0.0
        self._chat_models: dict[str, ChatOpenAI] = {}
        logger.info(
            "OpenRouter client initialized",
            base_url=self.base_url,
            default_model=self.default_model,
            search_model=self.search_model,
        )

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------
    def chat_complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 8000,
        max_retries: int = 3,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate a chat completion with auto-retry on failure.

        Args:
            messages: List of message dicts with role and content
            model: Model slug to use (defaults to default_model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            max_retries: Max retries on transient failures (timeout, rate limit)
            **kwargs: Additional parameters forwarded to the API

        Returns:
            Dict with content, model, input_tokens, output_tokens, total_tokens,
            and cost
        """
        import time as _time

        model = model or self.default_model
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return self._chat_complete_once(
                    messages, model, temperature, max_tokens, **kwargs
                )
            except (APIRateLimitError, APITimeoutError) as e:
                last_error = e
                # Primary provider rate-limited → try fallback (OpenRouter) once
                if self._fallback:
                    try:
                        return self._chat_complete_once(
                            messages,
                            self._fallback["model"],
                            temperature,
                            max_tokens,
                            client=self._fallback["client"],
                            **kwargs,
                        )
                    except Exception as fe:
                        last_error = fe
                        logger.warning(
                            "Fallback provider also failed",
                            error=str(fe)[:100],
                        )
                if attempt < max_retries:
                    delay = 2**attempt
                    logger.warning(
                        f"OpenRouter retry {attempt + 1}/{max_retries} in {delay}s",
                        model=model,
                        error=str(e)[:100],
                    )
                    _time.sleep(delay)
                    continue
            except APIServerError as e:
                last_error = e
                if attempt < max_retries - 1:  # fewer retries for server errors
                    delay = 5 * (attempt + 1)
                    logger.warning(
                        "OpenRouter server error, "
                        f"retry {attempt + 1}/{max_retries - 1} in {delay}s",
                        model=model,
                        error=str(e)[:100],
                    )
                    _time.sleep(delay)
                    continue

        raise last_error or GenerationFailureError(
            message=f"OpenRouter failed after {max_retries} retries",
            context={"model": model},
        )

    def _chat_complete_once(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        client: Any = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Single attempt at chat completion (no retry). `client` overrides the
        primary client (used for the OpenRouter fallback on rate-limit)."""

        client = client or self.client
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            content = response.choices[0].message.content or ""
            input_tokens = 0
            output_tokens = 0

            if response.usage:
                input_tokens = response.usage.prompt_tokens or 0
                output_tokens = response.usage.completion_tokens or 0

            cost = self._extract_cost(response, model, input_tokens, output_tokens)
            self.total_cost += cost
            self.cost_tracker.log_request(model, input_tokens, output_tokens, cost)

            logger.info(
                "OpenRouter completion",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=f"${cost:.4f}",
            )

            return {
                "content": content,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": cost,
            }

        except openai.RateLimitError as e:
            raise APIRateLimitError(message=str(e), service="openrouter") from e

        except openai.AuthenticationError as e:
            raise APIAuthenticationError(message=str(e), service="openrouter") from e

        except openai.APITimeoutError as e:
            raise APITimeoutError(message=str(e), service="openrouter") from e

        except openai.APIError as e:
            if "overloaded" in str(e).lower() or "rate" in str(e).lower():
                raise APIRateLimitError(
                    message=f"OpenRouter rate limited/overloaded: {str(e)[:200]}",
                    service="openrouter",
                    retry_after=60,
                ) from e
            raise APIServerError(message=str(e), service="openrouter") from e

        except Exception as e:
            raise GenerationFailureError(
                message=f"OpenRouter generation failed: {str(e)}",
                context={"model": model},
            ) from e

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate a completion from a single prompt.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: Model to use
            **kwargs: Additional parameters (temperature, max_tokens, ...)

        Returns:
            Dict with content, model, tokens, and cost
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.chat_complete(messages, model=model, **kwargs)

    def message(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate a message response (Claude-style API preserved).

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Dict with content, model, tokens, and cost
        """
        return self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

    def extract_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs,
    ) -> dict | list:
        """Extract structured JSON from a model response.

        Uses ``ChatOpenAI.with_structured_output()`` so the API itself
        enforces valid JSON (JSON mode) or a Pydantic schema (function
        calling). Falls back to regex-based extraction for models that
        don't support structured output.

        Args:
            prompt: User prompt (should request JSON output)
            system_prompt: Optional system prompt
            model: Model to use
            **kwargs: Additional parameters; accepts optional ``schema``
                (a Pydantic BaseModel class) for schema-validated output

        Returns:
            Parsed JSON data (dict or list)

        Raises:
            GenerationFailureError: If both structured output and regex
                fallback fail
        """
        schema = kwargs.pop("schema", None)
        json_system = (system_prompt or "") + (
            "\n\nRespond with valid JSON only. No additional text."
        )

        # Primary path: structured output via the API (no regex needed)
        try:
            chat = self._get_chat_model(model)
            if schema is not None:
                structured = chat.with_structured_output(schema)
            else:
                structured = chat.with_structured_output(method="json_mode")

            messages: list[tuple[str, str]] = []
            if json_system.strip():
                messages.append(("system", json_system.strip()))
            messages.append(("user", prompt))

            result = structured.invoke(messages)
            if hasattr(result, "model_dump"):
                return result.model_dump()
            return result
        except Exception as e:
            logger.warning(
                "Structured output failed, falling back to regex",
                error=str(e)[:200],
            )

        # Fallback: regex-based extraction from a plain completion
        response = self.complete(
            prompt=prompt,
            system_prompt=json_system.strip(),
            model=model,
            **kwargs,
        )
        content = response["content"]

        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if json_match:
            content = json_match.group(1)

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            obj_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", content)
            if obj_match:
                try:
                    return json.loads(obj_match.group(1))
                except json.JSONDecodeError:
                    pass

            raise GenerationFailureError(
                message="Failed to extract JSON from OpenRouter response",
                context={"response_preview": content[:500]},
            )

    def _get_chat_model(self, model: str | None = None) -> ChatOpenAI:
        """Get or create a ``ChatOpenAI`` for the given model.

        Reuses the same OpenRouter base URL / API key as the OpenAI client.
        Instances are cached per model slug.
        """
        model = model or self.default_model
        if model not in self._chat_models:
            default_headers: dict[str, str] = {"X-Title": "AI Blog Automation"}
            if self.site_url:
                default_headers["HTTP-Referer"] = self.site_url
            self._chat_models[model] = ChatOpenAI(
                model=model,
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers=default_headers,
                temperature=0.7,
                max_tokens=8000,
            )
        return self._chat_models[model]

    def complete_streaming(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        **kwargs,
    ) -> Generator[str, None, None]:
        """Generate a streaming chat completion.

        Args:
            messages: List of message dicts
            model: Model to use
            **kwargs: Additional parameters

        Yields:
            Content chunks as they arrive
        """
        model = model or self.default_model

        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                **kwargs,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise GenerationFailureError(
                message=f"Streaming failed: {str(e)}",
                context={"model": model},
            ) from e

    # ------------------------------------------------------------------
    # Web search / evidence retrieval (replaces PerplexityClient)
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        source_count: int = 5,
        focus: str = "internet",
    ) -> dict[str, Any]:
        """Search the web for information using an online model.

        Args:
            query: Search query
            source_count: Maximum number of sources to return
            focus: Search focus (kept for API compatibility)

        Returns:
            Dict with query, answer, sources, and source_count
        """
        response = self.chat_complete(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant. Provide accurate, "
                        "well-sourced information and cite the URLs you use."
                    ),
                },
                {"role": "user", "content": query},
            ],
            model=self.search_model,
            temperature=0.2,
            max_tokens=1024,
        )

        answer = response.get("content", "")
        sources = self._extract_sources(response, answer, source_count)

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "source_count": len(sources),
        }

    def get_evidence(
        self,
        claim: str,
        source_count: int = 3,
    ) -> dict[str, Any]:
        """Get evidence for a factual claim.

        Args:
            claim: Claim to find evidence for
            source_count: Number of sources

        Returns:
            Dict with evidence and sources
        """
        query = f"What is the evidence for: {claim}"
        return self.search(query, source_count=source_count)

    def verify_fact(
        self,
        fact: str,
    ) -> dict[str, Any]:
        """Verify a factual statement.

        Args:
            fact: Fact to verify

        Returns:
            Dict with verification result
        """
        query = f"Is this statement accurate? Provide sources: {fact}"
        result = self.search(query, source_count=3)
        result["fact"] = fact
        result["verified"] = len(result.get("sources", [])) > 0
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _extract_sources(
        self,
        response: dict[str, Any],
        answer: str,
        source_count: int,
    ) -> list[dict[str, Any]]:
        """Pull cited sources out of an online-model response.

        OpenRouter surfaces web citations via ``annotations`` on the message
        when an online/search model is used. We fall back to extracting URLs
        from the answer text when annotations are unavailable.
        """
        sources: list[dict[str, Any]] = []
        raw = response.get("_raw") if isinstance(response, dict) else None

        annotations = []
        if raw is not None:
            choices = getattr(raw, "choices", None)
            if choices:
                msg = getattr(choices[0], "message", None)
                if msg is not None:
                    annotations = getattr(msg, "annotations", None) or []

        for ann in annotations:
            if not isinstance(ann, dict):
                continue
            if ann.get("type") == "url_citation":
                uc = ann.get("url_citation", {}) or {}
                sources.append(
                    {
                        "url": uc.get("url", ""),
                        "title": uc.get("title", ""),
                        "snippet": uc.get("content", ""),
                    }
                )

        # Fallback: scrape URLs out of the answer text
        if not sources:
            for i, url in enumerate(re.findall(r"https?://[^\s)>]+", answer)):
                sources.append(
                    {
                        "url": url,
                        "title": url,
                        "snippet": "",
                        "position": i + 1,
                    }
                )

        return sources[:source_count]

    def _extract_cost(
        self,
        response: Any,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for a request.

        Prefers an explicit cost reported by OpenRouter; otherwise estimates
        from the pricing table using reported token counts.
        """
        usage = getattr(response, "usage", None)
        if usage is not None:
            reported = getattr(usage, "cost", None)
            if reported is not None:
                try:
                    return float(reported)
                except (TypeError, ValueError):
                    pass

        pricing = self._pricing_for(model)
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost

    @staticmethod
    def _pricing_for(model: str) -> dict[str, float]:
        """Look up pricing for a model, matching on the full slug then prefix."""
        if model in MODEL_PRICING:
            return MODEL_PRICING[model]
        prefix = model.split("/")[0] if "/" in model else model
        for key, value in MODEL_PRICING.items():
            if key.startswith(prefix):
                return value
        return _DEFAULT_PRICING

    def count_tokens(self, text: str, model: str | None = None) -> int:
        """Count tokens in text (rough estimate)."""
        try:
            import tiktoken

            model = model or self.default_model
            # OpenRouter slugs like "openai/gpt-4o" aren't tiktoken keys;
            # strip the provider prefix for tokenizer selection.
            short = model.split("/")[-1] if "/" in model else model
            try:
                encoding = tiktoken.encoding_for_model(short)
            except Exception:
                encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return len(text) // 4

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for a request."""
        pricing = self._pricing_for(model)
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost

    def validate_token_limit(
        self,
        text: str,
        max_tokens: int,
        model: str | None = None,
    ) -> tuple[bool, int]:
        """Validate text is within a token limit.

        Returns:
            Tuple of (is_valid, token_count)
        """
        token_count = self.count_tokens(text, model)
        return token_count <= max_tokens, token_count

    def get_total_cost(self) -> float:
        """Get total cost of all requests."""
        return self.total_cost

    def get_cost_summary(self) -> dict[str, Any]:
        """Get cost tracking summary."""
        return {
            "total_cost": self.cost_tracker.get_total_cost(),
            "total_requests": len(self.cost_tracker.requests),
            "by_model": self.cost_tracker.get_cost_by_model(),
        }

    @staticmethod
    def select_model(task: str) -> str:
        """Select an appropriate OpenRouter model slug for a task.

        Args:
            task: Task type (generation, extraction, verification, search, quick)

        Returns:
            Model slug (callers may still override per-call)
        """
        settings = get_settings()
        default = settings.openrouter_default_model
        search = settings.openrouter_search_model
        model_map = {
            "generation": default,
            "extraction": default,
            "verification": default,
            "search": search,
            "quick": default,
        }
        return model_map.get(task, default)
