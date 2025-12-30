"""OpenAI API client for content generation.

Provides GPT-4 integration for article drafting, outline generation,
and meta tag optimization.
"""

from typing import Any, Generator

import openai
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


# Token pricing per 1K tokens (as of Dec 2024)
MODEL_PRICING = {
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-32k": {"input": 0.06, "output": 0.12},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
}


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
        """Log an API request.

        Args:
            model: Model used
            input_tokens: Input token count
            output_tokens: Output token count
            cost: Calculated cost in USD
        """
        from datetime import datetime

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
        """Get cost for a specific day.

        Args:
            date_str: Date string (YYYY-MM-DD), defaults to today
        """
        from datetime import datetime

        if date_str is None:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")

        return sum(
            r["cost"] for r in self.requests if r["timestamp"].startswith(date_str)
        )

    def get_cost_by_model(self) -> dict[str, float]:
        """Get costs grouped by model."""
        costs: dict[str, float] = {}
        for r in self.requests:
            model = r["model"]
            costs[model] = costs.get(model, 0) + r["cost"]
        return costs


class OpenAIClient:
    """OpenAI API client for content generation.

    Provides methods for:
    - Chat completions (GPT-4)
    - Token counting
    - Cost estimation
    - Streaming responses
    """

    def __init__(
        self,
        api_key: str | None = None,
        organization_id: str | None = None,
        default_model: str | None = None,
    ):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            organization_id: Optional organization ID
            default_model: Default model to use
        """
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.organization_id = organization_id or settings.openai_organization_id
        self.default_model = default_model or settings.openai_default_model

        if not self.api_key:
            raise APIAuthenticationError(
                message="OpenAI API key not configured",
                service="openai",
            )

        self.client = OpenAI(
            api_key=self.api_key,
            organization=self.organization_id,
        )

        self.cost_tracker = CostTracker()
        logger.info("OpenAI client initialized", model=self.default_model)

    def chat_complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 3000,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate a chat completion.

        Args:
            messages: List of message dicts with role and content
            model: Model to use (defaults to default_model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Dict with content, tokens, and cost

        Raises:
            GenerationFailureError: If generation fails
        """
        model = model or self.default_model

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            content = response.choices[0].message.content
            usage = response.usage

            # Calculate cost
            cost = self.estimate_cost(
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
            )

            # Track cost
            self.cost_tracker.log_request(
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cost=cost,
            )

            logger.info(
                "OpenAI completion",
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cost=f"${cost:.4f}",
            )

            return {
                "content": content,
                "model": model,
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "cost": cost,
            }

        except openai.RateLimitError as e:
            raise APIRateLimitError(
                message=str(e),
                service="openai",
            ) from e

        except openai.AuthenticationError as e:
            raise APIAuthenticationError(
                message=str(e),
                service="openai",
            ) from e

        except openai.APITimeoutError as e:
            raise APITimeoutError(
                message=str(e),
                service="openai",
            ) from e

        except openai.APIError as e:
            raise APIServerError(
                message=str(e),
                service="openai",
            ) from e

        except Exception as e:
            raise GenerationFailureError(
                message=f"OpenAI generation failed: {str(e)}",
                context={"model": model},
            ) from e

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Simple completion with optional system prompt.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            Completion result dict
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.chat_complete(messages, **kwargs)

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
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise GenerationFailureError(
                message=f"Streaming failed: {str(e)}",
                context={"model": model},
            ) from e

    def count_tokens(self, text: str, model: str | None = None) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for
            model: Model for tokenization

        Returns:
            Token count
        """
        try:
            import tiktoken

            model = model or self.default_model
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            # Fallback: rough estimate
            return len(text) // 4

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for a request.

        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Estimated cost in USD
        """
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4-turbo-preview"])
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost

    def validate_token_limit(
        self,
        text: str,
        max_tokens: int,
        model: str | None = None,
    ) -> tuple[bool, int]:
        """Validate text is within token limit.

        Args:
            text: Text to validate
            max_tokens: Maximum allowed tokens
            model: Model for tokenization

        Returns:
            Tuple of (is_valid, token_count)
        """
        token_count = self.count_tokens(text, model)
        return token_count <= max_tokens, token_count

    def get_cost_summary(self) -> dict[str, Any]:
        """Get cost tracking summary.

        Returns:
            Cost summary dict
        """
        return {
            "total_cost": self.cost_tracker.get_total_cost(),
            "total_requests": len(self.cost_tracker.requests),
            "by_model": self.cost_tracker.get_cost_by_model(),
        }
