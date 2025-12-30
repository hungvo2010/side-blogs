"""Anthropic Claude API client for fact-checking and analysis.

Provides Claude integration for claim extraction, verification,
and structured data extraction.
"""

import json
import re
from typing import Any

import anthropic
from anthropic import Anthropic

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
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}


class ClaudeClient:
    """Anthropic Claude API client.

    Provides methods for:
    - Message generation
    - JSON extraction from responses
    - Token counting
    - Cost estimation
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
    ):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key
            default_model: Default model to use
        """
        settings = get_settings()
        self.api_key = api_key or settings.anthropic_api_key
        self.default_model = default_model or settings.anthropic_default_model

        if not self.api_key:
            raise APIAuthenticationError(
                message="Anthropic API key not configured",
                service="anthropic",
            )

        self.client = Anthropic(api_key=self.api_key)
        self.total_cost = 0.0
        logger.info("Claude client initialized", model=self.default_model)

    def message(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate a message response.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Dict with content, tokens, and cost
        """
        model = model or self.default_model

        try:
            message_kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }

            if system_prompt:
                message_kwargs["system"] = system_prompt

            if temperature != 1.0:
                message_kwargs["temperature"] = temperature

            message_kwargs.update(kwargs)

            response = self.client.messages.create(**message_kwargs)

            content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            # Calculate cost
            cost = self.estimate_cost(model, input_tokens, output_tokens)
            self.total_cost += cost

            logger.info(
                "Claude message",
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
                "cost": cost,
            }

        except anthropic.RateLimitError as e:
            raise APIRateLimitError(
                message=str(e),
                service="anthropic",
            ) from e

        except anthropic.AuthenticationError as e:
            raise APIAuthenticationError(
                message=str(e),
                service="anthropic",
            ) from e

        except anthropic.APITimeoutError as e:
            raise APITimeoutError(
                message=str(e),
                service="anthropic",
            ) from e

        except anthropic.APIError as e:
            # Handle overload (529)
            if "overloaded" in str(e).lower():
                raise APIRateLimitError(
                    message="Claude API overloaded",
                    service="anthropic",
                    retry_after=60,
                ) from e
            raise APIServerError(
                message=str(e),
                service="anthropic",
            ) from e

        except Exception as e:
            raise GenerationFailureError(
                message=f"Claude generation failed: {str(e)}",
                context={"model": model},
            ) from e

    def extract_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs,
    ) -> dict | list:
        """Extract JSON from Claude response.

        Handles JSON in markdown code blocks or raw JSON.

        Args:
            prompt: User prompt (should request JSON output)
            system_prompt: Optional system prompt
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            Parsed JSON data

        Raises:
            GenerationFailureError: If JSON extraction fails
        """
        # Add JSON instruction to system prompt
        json_system = (
            system_prompt or ""
        ) + "\n\nRespond with valid JSON only. No additional text."

        response = self.message(
            prompt=prompt,
            system_prompt=json_system.strip(),
            model=model,
            **kwargs,
        )

        content = response["content"]

        # Try to extract JSON from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if json_match:
            content = json_match.group(1)

        # Try to parse JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON object or array
            obj_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", content)
            if obj_match:
                try:
                    return json.loads(obj_match.group(1))
                except json.JSONDecodeError:
                    pass

            raise GenerationFailureError(
                message="Failed to extract JSON from response",
                context={"response_preview": content[:500]},
            )

    def count_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: Text to count

        Returns:
            Estimated token count
        """
        # Claude uses a similar tokenization to GPT
        # Rough estimate: ~4 characters per token
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
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-3-sonnet-20240229"])
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost

    def get_total_cost(self) -> float:
        """Get total cost of all requests.

        Returns:
            Total cost in USD
        """
        return self.total_cost

    @staticmethod
    def select_model(task: str) -> str:
        """Select appropriate model for task.

        Args:
            task: Task type (extraction, verification, generation)

        Returns:
            Model name
        """
        model_map = {
            "extraction": "claude-3-sonnet-20240229",  # Good balance
            "verification": "claude-3-opus-20240229",  # Best accuracy
            "generation": "claude-3-sonnet-20240229",  # Good balance
            "quick": "claude-3-haiku-20240307",  # Fastest/cheapest
        }
        return model_map.get(task, "claude-3-sonnet-20240229")
