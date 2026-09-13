"""
Unit tests for agent_stream module (Event Streaming ReAct engine).
"""
from unittest.mock import MagicMock

from src.agent_stream import AgentEvent, stream_react_agent
from src.mcp_server import MCPThreadsServer


def test_stream_direct_text_response():
    """Generator yields thought, final_answer, and token events when LLM responds with direct text."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "text",
        "thought": "Đây là câu hỏi lý thuyết, không cần gọi tool.",
        "content": "Threads khuyên dùng bài viết ngắn dưới 500 ký tự.",
    }
    server = MCPThreadsServer()

    events = list(stream_react_agent("Nên viết bài dài bao nhiêu?", mock_provider, server))

    event_types = [e.type for e in events]
    assert "thought" in event_types
    assert "final_answer" in event_types
    assert "token" in event_types

    thought_event = next(e for e in events if e.type == "thought")
    assert "lý thuyết" in thought_event.content

    final_event = next(e for e in events if e.type == "final_answer")
    assert "500 ký tự" in final_event.content
    assert "".join(e.content for e in events if e.type == "token") == "Threads khuyên dùng bài viết ngắn dưới 500 ký tự."


def test_stream_basic_tool_call():
    """Generator yields thought, tool_call, observation, final_answer, and tokens when LLM requests tool execution."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "tool_call",
        "thought": "Cần tìm kiếm bài viết về AI trên kênh Threads.",
        "tool_name": "threads_search",
        "arguments": {"query": "AI", "limit": 2},
    }
    server = MCPThreadsServer()

    events = list(stream_react_agent("Tìm bài viết về AI", mock_provider, server))

    event_types = [e.type for e in events]
    assert "thought" in event_types
    assert "tool_call" in event_types
    assert "observation" in event_types
    assert "final_answer" in event_types
    assert "token" in event_types

    tool_event = next(e for e in events if e.type == "tool_call")
    assert tool_event.tool_name == "threads_search"
    assert tool_event.arguments == {"query": "AI", "limit": 2}

    obs_event = next(e for e in events if e.type == "observation")
    assert obs_event.tool_name == "threads_search"
    assert "data" in obs_event.observation or "status" in obs_event.observation
    assert obs_event.latency_ms >= 0

    final_event = next(e for e in events if e.type == "final_answer")
    assert len(final_event.content) > 0
    assert "".join(e.content for e in events if e.type == "token") == final_event.content


def test_stream_unrecognized_response_type():
    """Generator yields error event when LLM response type is unrecognized."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "unknown_type",
        "thought": "Phân tích không xác định.",
    }
    server = MCPThreadsServer()

    events = list(stream_react_agent("Câu hỏi không xác định", mock_provider, server))

    error_event = next((e for e in events if e.type == "error"), None)
    assert error_event is not None
    assert error_event.content == "Unrecognized response type: unknown_type"

