"""
Unit tests for app module (Chatbot baseline and ReAct agent loop for Threads MCP).
"""

import json
from unittest.mock import MagicMock

from src.app import load_test_cases, run_baseline_chatbot, run_react_agent, save_waterfall_trace
from src.mcp_server import MCPThreadsServer
from src.prompts import CHATBOT_BASELINE_PROMPT


def test_run_baseline_chatbot_delegates_with_baseline_prompt():
    """run_baseline_chatbot delegates query to provider with CHATBOT_BASELINE_PROMPT and returns response."""
    mock_provider = MagicMock()
    mock_provider.generate.return_value = "Phản hồi tư vấn hook Threads"

    query = "Làm sao để viết hook 3 dòng đầu giữ chân người đọc?"
    result = run_baseline_chatbot(query, mock_provider)
    mock_provider.generate.assert_called_once_with(
        query,
        system_prompt=CHATBOT_BASELINE_PROMPT,
    )
    assert result == "Phản hồi tư vấn hook Threads"


def test_run_react_agent_direct_text_response():
    """run_react_agent returns FINAL_ANSWER trace when provider responds with text."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "text",
        "content": "Bài đăng Threads lý tưởng từ 150-300 ký tự.",
        "thought": "Câu hỏi tư vấn chung, trả lời trực tiếp.",
    }
    server = MCPThreadsServer()

    query = "Độ dài lý tưởng bài đăng Threads là bao nhiêu?"
    traces = run_react_agent(query, mock_provider, server)

    assert len(traces) == 1
    assert traces[0]["action_type"] == "FINAL_ANSWER"
    assert traces[0]["query"] == query
    assert "150-300" in traces[0]["output"]
    assert "thought" in traces[0]
    assert "latency_ms" in traces[0]


def test_run_react_agent_tool_execution_insights():
    """run_react_agent executes tool and generates formatted final answer from observations."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "tool_call",
        "tool_name": "threads_get_insights",
        "arguments": {"thread_id": "th_post_001"},
        "thought": "Cần tra cứu số liệu bài đăng th_post_001.",
    }
    server = MCPThreadsServer()

    query = "Tra cứu chỉ số bài đăng th_post_001"
    traces = run_react_agent(query, mock_provider, server)

    assert len(traces) == 2
    # Step 1: TOOL_EXECUTION
    assert traces[0]["action_type"] == "TOOL_EXECUTION"
    assert traces[0]["tool_name"] == "threads_get_insights"
    assert traces[0]["observation"]["status"] == "SUCCESS"
    assert "views" in traces[0]["observation"]["metrics"]
    # Step 2: FINAL_ANSWER
    assert traces[1]["action_type"] == "FINAL_ANSWER"
    assert "th_post_001" in traces[1]["output"] or "views" in traces[1]["output"].lower()


def test_run_react_agent_tool_failure_not_found():
    """run_react_agent handles tool NOT_FOUND observation gracefully in final answer."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "tool_call",
        "tool_name": "threads_get_thread",
        "arguments": {"thread_id": "th_post_999"},
        "thought": "Tra cứu bài đăng th_post_999.",
    }
    server = MCPThreadsServer()

    query = "Kiểm tra bài đăng th_post_999"
    traces = run_react_agent(query, mock_provider, server)

    assert len(traces) == 2
    assert traces[0]["observation"]["status"] == "NOT_FOUND"
    assert traces[1]["action_type"] == "FINAL_ANSWER"
    assert "not found" in traces[1]["output"].lower() or "không tồn tại" in traces[1]["output"].lower() or "th_post_999" in traces[1]["output"]


def test_run_react_agent_create_thread():
    """run_react_agent executes threads_create_thread and reports success."""
    mock_provider = MagicMock()
    mock_provider.generate_with_tools.return_value = {
        "type": "tool_call",
        "tool_name": "threads_create_thread",
        "arguments": {"text": "TDD for ReAct Agent is great!"},
        "thought": "Đăng bài mới.",
    }
    server = MCPThreadsServer()

    query = "Xuất bản bài viết: TDD for ReAct Agent is great!"
    traces = run_react_agent(query, mock_provider, server)

    assert len(traces) == 2
    assert traces[0]["action_type"] == "TOOL_EXECUTION"
    assert traces[0]["observation"]["status"] == "SUCCESS"
    assert "id" in traces[0]["observation"]
    assert traces[1]["action_type"] == "FINAL_ANSWER"
