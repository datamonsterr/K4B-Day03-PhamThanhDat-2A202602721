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
