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


def test_stream_read_tool_auto_executes():
    """Read tools (e.g. threads_get_insights) execute immediately without asking permission."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "tool_call",
        "tool_name": "threads_get_insights",
        "arguments": {"thread_id": "th_post_001"},
        "thought": "Tra cứu chỉ số bài đăng th_post_001.",
    }
    server = MCPThreadsServer()

    events = list(stream_react_agent("Xem chỉ số th_post_001", mock_provider, server))
    event_types = [e.type for e in events]

    assert "ask_permission" not in event_types
    assert "tool_call" in event_types
    assert "observation" in event_types
    assert "final_answer" in event_types
    assert "token" in event_types


def test_stream_write_tool_requires_permission():
    """Write tools (e.g. threads_create_thread, threads_reply_to_thread) yield ask_permission event and pause without executing."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "tool_call",
        "tool_name": "threads_create_thread",
        "arguments": {"text": "Hello Threads!", "reply_control": "everyone"},
        "thought": "Cần xuất bản bài viết mới.",
    }
    server = MCPThreadsServer()

    events = list(stream_react_agent("Đăng bài viết mới", mock_provider, server))
    event_types = [e.type for e in events]

    assert "ask_permission" in event_types
    assert "observation" not in event_types

    perm_event = next(e for e in events if e.type == "ask_permission")
    assert perm_event.tool_name == "threads_create_thread"
    assert perm_event.arguments["text"] == "Hello Threads!"
    assert perm_event.step == 1
    assert perm_event.latency_ms >= 0

    # Also test threads_reply_to_thread
    mock_provider.generate_with_tools.return_value = {
        "type": "tool_call",
        "tool_name": "threads_reply_to_thread",
        "arguments": {"thread_id": "th_post_001", "text": "Nice post!"},
        "thought": "Cần phản hồi bài viết.",
    }
    events_reply = list(stream_react_agent("Trả lời bài viết", mock_provider, server))
    types_reply = [e.type for e in events_reply]
    assert "ask_permission" in types_reply
    assert "observation" not in types_reply


def test_stream_resume_after_approval():
    """When resumed with approval, executes tool and completes response."""
    server = MCPThreadsServer()
    mock_provider = MagicMock()

    resumed_action = {
        "action": "approve",
        "tool_name": "threads_create_thread",
        "arguments": {"text": "Hello Approved!", "reply_control": "everyone"},
        "query": "Đăng bài viết mới",
        "step": 1,
    }

    events = list(stream_react_agent("Đăng bài viết mới", mock_provider, server, resumed_action=resumed_action))
    event_types = [e.type for e in events]

    assert "tool_call" in event_types
    assert "observation" in event_types
    assert "final_answer" in event_types
    assert "token" in event_types

    tool_event = next(e for e in events if e.type == "tool_call")
    assert tool_event.tool_name == "threads_create_thread"

    obs_event = next(e for e in events if e.type == "observation")
    assert obs_event.observation.get("status") == "SUCCESS"

    final_event = next(e for e in events if e.type == "final_answer")
    assert len(final_event.content) > 0


def test_stream_resume_after_rejection():
    """When resumed with rejection, yields rejection observation and friendly final answer."""
    server = MCPThreadsServer()
    mock_provider = MagicMock()

    resumed_action = {
        "action": "reject",
        "tool_name": "threads_create_thread",
        "arguments": {"text": "Rejected draft"},
        "reason": "Nội dung chưa phù hợp văn phong",
        "query": "Đăng bài",
        "step": 1,
    }

    events = list(stream_react_agent("Đăng bài", mock_provider, server, resumed_action=resumed_action))
    event_types = [e.type for e in events]

    assert "observation" in event_types
    assert "final_answer" in event_types
    assert "token" in event_types

    obs_event = next(e for e in events if e.type == "observation")
    assert obs_event.observation["status"] == "REJECTED_BY_USER"
    assert obs_event.observation["reason"] == "Nội dung chưa phù hợp văn phong"

    final_event = next(e for e in events if e.type == "final_answer")
    assert "đã hủy" in final_event.content.lower() or "từ chối" in final_event.content.lower()


def test_stream_interactive_ask_input_and_choice():
    """Verify ask_user_input and ask_user_choice yield interaction events and handle resumption."""
    server = MCPThreadsServer()
    mock_provider = MagicMock()

    # 1. ask_user_input pause
    mock_provider.generate_with_tools.return_value = {
        "type": "tool_call",
        "tool_name": "ask_user_input",
        "arguments": {"prompt": "Vui lòng nhập chủ đề bạn quan tâm:"},
        "thought": "Cần hỏi thêm thông tin từ người dùng.",
    }
    events_input = list(stream_react_agent("Tạo bài viết", mock_provider, server))
    types_input = [e.type for e in events_input]
    assert "ask_input" in types_input
    assert "observation" not in types_input
    input_event = next(e for e in events_input if e.type == "ask_input")
    assert input_event.content == "Vui lòng nhập chủ đề bạn quan tâm:"

    # 2. Resumption for submit_input
    resume_input = {
        "action": "submit_input",
        "tool_name": "ask_user_input",
        "response": "Chủ đề AI và Agent",
        "step": 1,
    }
    events_resumed_input = list(stream_react_agent("Tạo bài viết", mock_provider, server, resumed_action=resume_input))
    types_resumed_input = [e.type for e in events_resumed_input]
    assert "observation" in types_resumed_input
    assert "final_answer" in types_resumed_input
    assert "token" in types_resumed_input
    obs_input = next(e for e in events_resumed_input if e.type == "observation")
    assert obs_input.observation == {"status": "USER_RESPONSE", "response": "Chủ đề AI và Agent"}
    final_input = next(e for e in events_resumed_input if e.type == "final_answer")
    assert "Chủ đề AI và Agent" in final_input.content

    # 3. ask_user_choice pause
    mock_provider.generate_with_tools.return_value = {
        "type": "tool_call",
        "tool_name": "ask_user_choice",
        "arguments": {
            "prompt": "Chọn phong cách bài viết:",
            "options": ["Chuyên nghiệp", "Hài hước", "Ngắn gọn"],
        },
        "thought": "Cần người dùng chọn phong cách.",
    }
    events_choice = list(stream_react_agent("Tạo bài viết", mock_provider, server))
    types_choice = [e.type for e in events_choice]
    assert "ask_choice" in types_choice
    assert "observation" not in types_choice
    choice_event = next(e for e in events_choice if e.type == "ask_choice")
    assert choice_event.content == "Chọn phong cách bài viết:"
    assert choice_event.options == ["Chuyên nghiệp", "Hài hước", "Ngắn gọn"]

    # 4. Resumption for submit_choice
    resume_choice = {
        "action": "submit_choice",
        "tool_name": "ask_user_choice",
        "response": "Hài hước",
        "step": 1,
    }
    events_resumed_choice = list(stream_react_agent("Tạo bài viết", mock_provider, server, resumed_action=resume_choice))
    types_resumed_choice = [e.type for e in events_resumed_choice]
    assert "observation" in types_resumed_choice
    assert "final_answer" in types_resumed_choice
    assert "token" in types_resumed_choice
    obs_choice = next(e for e in events_resumed_choice if e.type == "observation")
    assert obs_choice.observation == {"status": "USER_RESPONSE", "response": "Hài hước"}
    final_choice = next(e for e in events_resumed_choice if e.type == "final_answer")
    assert "Hài hước" in final_choice.content

