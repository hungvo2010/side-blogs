"""Unit tests for extract_json with structured output + regex fallback."""

import pytest

from blog_automation.errors import GenerationFailureError
from blog_automation.integrations.openrouter_client import OpenRouterClient


@pytest.fixture
def client():
    """Create an OpenRouterClient with a fake API key (no real calls)."""
    return OpenRouterClient(api_key="test-key")


class TestExtractJsonStructuredOutput:
    """Tests for the primary structured-output path."""

    def test_json_mode_returns_dict(self, client, mocker):
        """JSON mode (no schema) returns a dict from the API."""
        mock_chat = mocker.MagicMock()
        mock_structured = mocker.MagicMock()
        mock_structured.invoke.return_value = {"sections": [{"h2": "Test"}]}
        mock_chat.with_structured_output.return_value = mock_structured
        mocker.patch.object(client, "_get_chat_model", return_value=mock_chat)

        result = client.extract_json("Generate sections")
        assert result == {"sections": [{"h2": "Test"}]}
        mock_chat.with_structured_output.assert_called_with(method="json_mode")

    def test_schema_returns_model_dump(self, client, mocker):
        """Schema mode returns the Pydantic instance's .model_dump()."""
        from pydantic import BaseModel

        class MySchema(BaseModel):
            sections: list

        mock_chat = mocker.MagicMock()
        mock_structured = mocker.MagicMock()
        mock_structured.invoke.return_value = MySchema(sections=[{"h2": "X"}])
        mock_chat.with_structured_output.return_value = mock_structured
        mocker.patch.object(client, "_get_chat_model", return_value=mock_chat)

        result = client.extract_json("Generate sections", schema=MySchema)
        assert result == {"sections": [{"h2": "X"}]}
        mock_chat.with_structured_output.assert_called_with(MySchema)

    def test_system_prompt_included_in_messages(self, client, mocker):
        """The JSON instruction + system prompt are sent as a system message."""
        mock_chat = mocker.MagicMock()
        mock_structured = mocker.MagicMock()
        mock_structured.invoke.return_value = {"ok": True}
        mock_chat.with_structured_output.return_value = mock_structured
        mocker.patch.object(client, "_get_chat_model", return_value=mock_chat)

        client.extract_json("prompt", system_prompt="You are helpful")
        sent_messages = mock_structured.invoke.call_args[0][0]
        assert any("system" in m and "JSON" in m[1] for m in sent_messages)


class TestExtractJsonRegexFallback:
    """Tests for the regex fallback when structured output fails."""

    def test_fallback_succeeds_on_fenced_json(self, client, mocker):
        """Structured output fails → regex extracts JSON from a fence."""
        mock_chat = mocker.MagicMock()
        mock_chat.with_structured_output.side_effect = Exception("unsupported")
        mocker.patch.object(client, "_get_chat_model", return_value=mock_chat)
        mocker.patch.object(
            client,
            "complete",
            return_value={"content": '```json\n{"sections": [{"h2": "FB"}]}\n```'},
        )

        result = client.extract_json("Generate sections")
        assert result == {"sections": [{"h2": "FB"}]}

    def test_fallback_succeeds_on_raw_json(self, client, mocker):
        """Structured output fails → regex extracts raw JSON object."""
        mock_chat = mocker.MagicMock()
        mock_chat.with_structured_output.side_effect = Exception("unsupported")
        mocker.patch.object(client, "_get_chat_model", return_value=mock_chat)
        mocker.patch.object(
            client,
            "complete",
            return_value={"content": 'Here you go: {"lsi_keywords": ["a", "b"]}'},
        )

        result = client.extract_json("Generate LSI")
        assert result == {"lsi_keywords": ["a", "b"]}

    def test_both_fail_raises_generation_error(self, client, mocker):
        """Both structured output and regex fallback fail → raises."""
        mock_chat = mocker.MagicMock()
        mock_chat.with_structured_output.side_effect = Exception("unsupported")
        mocker.patch.object(client, "_get_chat_model", return_value=mock_chat)
        mocker.patch.object(
            client,
            "complete",
            return_value={"content": "This is not JSON at all."},
        )

        with pytest.raises(GenerationFailureError):
            client.extract_json("Generate sections")
