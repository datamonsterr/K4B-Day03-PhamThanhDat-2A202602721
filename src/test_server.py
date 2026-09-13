"""
Unit tests for Backend Server and SSE streaming (Task 3A: Starlette + Uvicorn server mode).
"""
import json
from unittest.mock import MagicMock

from starlette.testclient import TestClient

from src.app import create_backend_app
from src.mcp_server import MCPThreadsServer
from src.providers import MockOfflineProvider


def _parse_sse_events(response_text: str) -> list[dict]:
    """Helper to parse SSE text stream into list of JSON event dictionaries."""
    events = []
    for line in response_text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            raw_json = line[len("data:") :].strip()
            if raw_json:
                events.append(json.loads(raw_json))
    return events


def test_health_endpoint_default():
    """GET /health returns 200 with status ok and server name."""
    app = create_backend_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "provider" in data
    assert data["server"] == "vinuni-threads-mcp-server"


def test_health_endpoint_custom_provider_and_server():
    """GET /health reflects custom provider model_name and server server_name."""
    mock_provider = MagicMock()
    mock_provider.model_name = "test-custom-llm"
    mock_server = MagicMock()
    mock_server.server_name = "custom-mcp-server"

    app = create_backend_app(provider=mock_provider, mcp_server=mock_server)
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["provider"] == "test-custom-llm"
    assert data["server"] == "custom-mcp-server"


def test_get_tools_endpoint():
    """GET /api/tools returns 200 and the MCP tools list schema."""
    server = MCPThreadsServer()
    app = create_backend_app(mcp_server=server)
    client = TestClient(app)

    response = client.get("/api/tools")
    assert response.status_code == 200
    tools = response.json()
    assert isinstance(tools, list)
    assert len(tools) > 0

    tool_names = [t.get("name") for t in tools]
    assert "threads_get_insights" in tool_names
    assert "threads_create_thread" in tool_names
    assert "threads_search" in tool_names


def test_get_test_cases_endpoint():
    """GET /api/test-cases returns 200 and the loaded test cases."""
    app = create_backend_app()
    client = TestClient(app)

    response = client.get("/api/test-cases")
    assert response.status_code == 200
    cases = response.json()
    assert isinstance(cases, list)
    assert len(cases) >= 1
    assert "id" in cases[0]
    assert "question" in cases[0]


def test_chat_stream_direct_text_response():
    """POST /api/chat/stream streams thought, final_answer, tokens, and done event for text response."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "text",
        "thought": "Đây là câu hỏi lý thuyết, không cần gọi tool.",
        "content": "Threads ưu tiên nội dung ngắn gọn và hình ảnh bắt mắt.",
    }
    server = MCPThreadsServer()
    app = create_backend_app(provider=mock_provider, mcp_server=server)
    client = TestClient(app)

    payload = {"query": "Chia sẻ kinh nghiệm làm nội dung Threads"}
    response = client.post("/api/chat/stream", json=payload)

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    events = _parse_sse_events(response.text)
    event_types = [e.get("type") for e in events]

    assert "thought" in event_types
    assert "final_answer" in event_types
    assert "token" in event_types
    assert "done" in event_types

    # Ensure last event is done
    assert events[-1]["type"] == "done"

    thought_event = next(e for e in events if e.get("type") == "thought")
    assert "lý thuyết" in thought_event.get("content", "")

    final_event = next(e for e in events if e.get("type") == "final_answer")
    assert "Threads ưu tiên" in final_event.get("content", "")


def test_chat_stream_tool_call_flow():
    """POST /api/chat/stream streams tool_call, observation, final_answer, and done for tool execution."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "tool_call",
        "thought": "Tra cứu chỉ số bài đăng th_post_001.",
        "tool_name": "threads_get_insights",
        "arguments": {"thread_id": "th_post_001"},
    }
    server = MCPThreadsServer()
    app = create_backend_app(provider=mock_provider, mcp_server=server)
    client = TestClient(app)

    payload = {"query": "Tra cứu số liệu th_post_001"}
    response = client.post("/api/chat/stream", json=payload)

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    events = _parse_sse_events(response.text)
    event_types = [e.get("type") for e in events]

    assert "thought" in event_types
    assert "tool_call" in event_types
    assert "observation" in event_types
    assert "final_answer" in event_types
    assert "done" in event_types

    tool_event = next(e for e in events if e.get("type") == "tool_call")
    assert tool_event.get("tool_name") == "threads_get_insights"
    assert tool_event.get("arguments") == {"thread_id": "th_post_001"}

    obs_event = next(e for e in events if e.get("type") == "observation")
    assert obs_event.get("tool_name") == "threads_get_insights"
    assert obs_event.get("observation", {}).get("status") == "SUCCESS"


def test_chat_stream_human_in_the_loop_ask_permission():
    """POST /api/chat/stream halts and yields ask_permission for write tools."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "tool_call",
        "thought": "Yêu cầu đăng bài mới.",
        "tool_name": "threads_create_thread",
        "arguments": {"text": "Nội dung bài viết mới"},
    }
    server = MCPThreadsServer()
    app = create_backend_app(provider=mock_provider, mcp_server=server)
    client = TestClient(app)

    payload = {"query": "Đăng bài viết mới"}
    response = client.post("/api/chat/stream", json=payload)

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_types = [e.get("type") for e in events]

    assert "ask_permission" in event_types
    assert "done" in event_types

    perm_event = next(e for e in events if e.get("type") == "ask_permission")
    assert perm_event.get("tool_name") == "threads_create_thread"
    assert perm_event.get("arguments") == {"text": "Nội dung bài viết mới"}


def test_chat_stream_resumed_action():
    """POST /api/chat/stream executes tool and finishes when resumed_action is provided."""
    server = MCPThreadsServer()
    app = create_backend_app(mcp_server=server)
    client = TestClient(app)

    payload = {
        "query": "Đăng bài viết mới",
        "resumed_action": {
            "action": "approve",
            "tool_name": "threads_create_thread",
            "arguments": {"text": "Bài viết đã được duyệt qua SSE API"},
            "step": 1,
        },
    }
    response = client.post("/api/chat/stream", json=payload)

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    event_types = [e.get("type") for e in events]

    assert "tool_call" in event_types
    assert "observation" in event_types
    assert "final_answer" in event_types
    assert "done" in event_types

    obs_event = next(e for e in events if e.get("type") == "observation")
    assert obs_event.get("observation", {}).get("status") == "SUCCESS"


def test_chat_stream_provider_selection_mock():
    """POST /api/chat/stream with provider='mock' selects MockOfflineProvider."""
    server = MCPThreadsServer()
    app = create_backend_app(mcp_server=server)
    client = TestClient(app)

    payload = {
        "query": "Phân tích kỹ thuật viết hook 3 dòng đầu",
        "provider": "mock",
    }
    response = client.post("/api/chat/stream", json=payload)

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert len(events) > 0
    assert events[-1]["type"] == "done"


def test_cors_middleware():
    """Server responds with appropriate CORS headers on preflight OPTIONS."""
    app = create_backend_app()
    client = TestClient(app)

    response = client.options(
        "/api/tools",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
