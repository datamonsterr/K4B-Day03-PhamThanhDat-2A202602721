"""
Unit tests for providers module (Google Gemini, OpenAI, OpenRouter, and Mock).
"""

import os
from unittest.mock import MagicMock, patch

from dotenv import load_dotenv

from src.prompts import CHATBOT_BASELINE_PROMPT
from src.providers import (
    GeminiProvider,
    MockOfflineProvider,
    OpenAIProvider,
    OpenRouterProvider,
    get_llm_provider,
)


def test_openrouter_generate_without_api_key_returns_error_string():
    """When API key is empty or placeholder, generate() returns an [OpenRouter Error] string."""
    provider = OpenRouterProvider(api_key="")
    response = provider.generate("Xin chào!")
    assert response.startswith("[OpenRouter Error]:")

    provider_placeholder = OpenRouterProvider(api_key="your_openrouter_api_key_here")
    response_placeholder = provider_placeholder.generate("Xin chào!")
    assert response_placeholder.startswith("[OpenRouter Error]:")


def test_openrouter_generate_handles_api_exception_gracefully():
    """When OpenRouter API raises an exception, generate() returns an [OpenRouter Exception] string."""
    with patch("openrouter.OpenRouter") as mock_openrouter_cls:
        mock_client = MagicMock()
        mock_client.chat.send.side_effect = RuntimeError("Connection timed out")
        mock_openrouter_cls.return_value.__enter__.return_value = mock_client

        provider = OpenRouterProvider(api_key="valid-dummy-key")
        response = provider.generate("Xin chào!")
        assert response.startswith("[OpenRouter Exception]:")
        assert "Connection timed out" in response


def test_openrouter_generate_sends_baseline_prompt_and_returns_content():
    """generate() sends system and user messages to OpenRouter and returns content string."""
    with patch("openrouter.OpenRouter") as mock_openrouter_cls:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = (
            "Quy chế học vụ VinUni yêu cầu sinh viên tích lũy tối thiểu 120 tín chỉ."
        )
        mock_response.choices = [mock_choice]
        mock_client.chat.send.return_value = mock_response
        mock_openrouter_cls.return_value.__enter__.return_value = mock_client

        provider = OpenRouterProvider(
            api_key="valid-dummy-key",
            model="nvidia/nemotron-3.5-lightning:free",
        )
        prompt = "Kỹ thuật viết hook Threads nào hiệu quả nhất?"
        response = provider.generate(prompt, system_prompt=CHATBOT_BASELINE_PROMPT)

        assert (
            response
            == "Quy chế học vụ VinUni yêu cầu sinh viên tích lũy tối thiểu 120 tín chỉ."
        )
        mock_client.chat.send.assert_called_once()
        called_kwargs = mock_client.chat.send.call_args.kwargs
        assert called_kwargs["model"] == "nvidia/nemotron-3.5-lightning:free"
        assert called_kwargs["messages"] == [
            {"role": "system", "content": CHATBOT_BASELINE_PROMPT},
            {"role": "user", "content": prompt},
        ]


def test_openrouter_generate_with_tools_mock_fallback_without_key():
    """generate_with_tools() falls back to MockOfflineProvider when api_key is missing."""
    provider = OpenRouterProvider(api_key="")
    result = provider.generate_with_tools("Tra cứu chỉ số bài đăng th_post_001", [])
    assert result.get("type") in ["tool_call", "text"]


def test_openrouter_generate_with_tools_parses_tool_call():
    """generate_with_tools() correctly parses tool call response from OpenRouter."""
    with patch("openrouter.OpenRouter") as mock_openrouter_cls:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "threads_get_insights"
        mock_tool_call.function.arguments = '{"thread_id": "th_post_001"}'
        mock_choice.message.tool_calls = [mock_tool_call]
        mock_response.choices = [mock_choice]
        mock_client.chat.send.return_value = mock_response
        mock_openrouter_cls.return_value.__enter__.return_value = mock_client

        provider = OpenRouterProvider(api_key="valid-dummy-key")
        tools_schema = [
            {
                "name": "threads_get_insights",
                "description": "Tra cứu chỉ số tương tác",
                "parameters": {"type": "object", "properties": {}},
            }
        ]
        result = provider.generate_with_tools("Tra cứu chỉ số th_post_001", tools_schema)
        assert result.get("type") == "tool_call"
        assert result.get("tool_name") == "threads_get_insights"
        assert result.get("arguments") == {"thread_id": "th_post_001"}


def test_get_llm_provider_factory():
    """Factory get_llm_provider returns configured provider instance."""
    with patch.dict(
        os.environ,
        {"LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "valid-dummy-key"},
    ):
        provider = get_llm_provider()
        assert isinstance(provider, OpenRouterProvider)

    with patch.dict(
        os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "valid-dummy-key"}
    ):
        provider = get_llm_provider()
        assert isinstance(provider, GeminiProvider)

    with patch.dict(
        os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "valid-dummy-key"}
    ):
        provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)

    with patch.dict(os.environ, {"LLM_PROVIDER": "mock"}):
        provider = get_llm_provider()
        assert isinstance(provider, MockOfflineProvider)


def test_live_openrouter_baseline_response():
    """End-to-end live test: verify baseline chat response if OPENROUTER_API_KEY is configured."""
    import pytest

    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "your_openrouter_api_key_here":
        pytest.skip("No valid OPENROUTER_API_KEY found in environment.")

    provider = OpenRouterProvider()
    response = provider.generate(
        "Chào bạn, hãy phân tích độ dài lý tưởng của một bài đăng Threads và các kỹ thuật viết hook để giữ chân người đọc trong 3 dòng đầu tiên?",
        system_prompt=CHATBOT_BASELINE_PROMPT,
    )
    assert isinstance(response, str)
    assert len(response.strip()) > 0
    assert not response.startswith("[OpenRouter Error]")
    assert not response.startswith("[OpenRouter Exception]")
