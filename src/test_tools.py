"""
Unit tests for tools module (Threads MCP Tools implementation).
"""

import json
import pytest

from src.tools import TOOLS_SCHEMA, dispatch_tool_call


def test_tools_schema_contains_threads_tools():
    """TOOLS_SCHEMA must declare official quinnjr/threads-mcp tools."""
    tool_names = [tool["name"] for tool in TOOLS_SCHEMA]
    expected_tools = [
        "threads_get_profile",
        "threads_get_threads",
        "threads_get_thread",
        "threads_create_thread",
        "threads_reply_to_thread",
        "threads_get_insights",
        "threads_get_replies",
        "threads_get_conversation",
        "threads_search",
    ]
    for expected in expected_tools:
        assert expected in tool_names, f"Tool '{expected}' is missing from TOOLS_SCHEMA"

    for tool in TOOLS_SCHEMA:
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool
        assert tool["parameters"].get("type") == "object"


def test_threads_get_profile_success():
    """threads_get_profile returns account profile."""
    raw = dispatch_tool_call("threads_get_profile", {})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert "data" in result
    profile = result["data"]
    assert "username" in profile
    assert "followers_count" in profile


def test_threads_get_threads_success():
    """threads_get_threads returns list of threads."""
    raw = dispatch_tool_call("threads_get_threads", {})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert "data" in result
    assert isinstance(result["data"], list)
    assert len(result["data"]) > 0


def test_threads_get_thread_success():
    """threads_get_thread returns details of an existing thread."""
    raw = dispatch_tool_call("threads_get_thread", {"thread_id": "th_post_001"})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert result["thread_id"] == "th_post_001"
    assert "text" in result["data"]


def test_threads_get_thread_not_found():
    """threads_get_thread returns NOT_FOUND when thread does not exist."""
    raw = dispatch_tool_call("threads_get_thread", {"thread_id": "th_nonexistent_999"})
    result = json.loads(raw)
    assert result["status"] == "NOT_FOUND"
    assert "not found" in result["message"].lower()


def test_threads_create_thread_success():
    """threads_create_thread adds a new thread post."""
    text = "Exploring AI agents with Model Context Protocol! 🚀"
    raw = dispatch_tool_call("threads_create_thread", {"text": text})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert "id" in result
    assert result["text"] == text
    assert "permalink" in result


def test_threads_reply_to_thread_success():
    """threads_reply_to_thread adds a reply to an existing thread."""
    raw = dispatch_tool_call(
        "threads_reply_to_thread",
        {"thread_id": "th_post_001", "text": "Great insights on AI Agents!"},
    )
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert result["thread_id"] == "th_post_001"
    assert "id" in result


def test_threads_reply_to_thread_not_found():
    """threads_reply_to_thread returns NOT_FOUND when target thread does not exist."""
    raw = dispatch_tool_call(
        "threads_reply_to_thread",
        {"thread_id": "th_nonexistent_999", "text": "Invalid reply"},
    )
    result = json.loads(raw)
    assert result["status"] == "NOT_FOUND"


def test_threads_get_insights_success():
    """threads_get_insights returns performance metrics for a thread."""
    raw = dispatch_tool_call("threads_get_insights", {"thread_id": "th_post_001"})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert result["thread_id"] == "th_post_001"
    assert "metrics" in result
    metrics = result["metrics"]
    for metric_name in ["views", "likes", "replies", "reposts"]:
        assert metric_name in metrics


def test_threads_get_insights_not_found():
    """threads_get_insights returns NOT_FOUND for an unknown thread_id."""
    raw = dispatch_tool_call("threads_get_insights", {"thread_id": "th_nonexistent_999"})
    result = json.loads(raw)
    assert result["status"] == "NOT_FOUND"


def test_threads_get_replies_success():
    """threads_get_replies returns replies for a thread."""
    raw = dispatch_tool_call("threads_get_replies", {"thread_id": "th_post_001"})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert result["thread_id"] == "th_post_001"
    assert isinstance(result["data"], list)


def test_threads_get_conversation_success():
    """threads_get_conversation returns thread and its replies."""
    raw = dispatch_tool_call("threads_get_conversation", {"thread_id": "th_post_001"})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert "thread" in result
    assert "replies" in result


def test_dispatch_tool_call_unknown_tool():
    """Unknown tool name returns UNKNOWN_TOOL error."""
    raw = dispatch_tool_call("non_existent_tool", {})
    result = json.loads(raw)
    assert result["status"] == "UNKNOWN_TOOL"


def test_threads_search_top_views():
    """threads_search finds matching posts and sorts by top views."""
    raw = dispatch_tool_call(
        "threads_search", {"query": "AI", "sort_by": "top_views", "limit": 5}
    )
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert result["query"] == "AI"
    assert len(result["data"]) > 0
    top_post = result["data"][0]
    assert "AI" in top_post["text"]
    assert "views" in top_post
    assert top_post["id"] == "th_post_001"


def test_threads_search_recent():
    """threads_search sorts by recent timestamp when requested."""
    raw = dispatch_tool_call(
        "threads_search", {"query": "Threads", "sort_by": "recent", "limit": 5}
    )
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert len(result["data"]) > 0


def test_threads_search_not_found():
    """threads_search returns NOT_FOUND when no posts match query."""
    raw = dispatch_tool_call(
        "threads_search", {"query": "non_existent_keyword_xyz", "limit": 5}
    )
    result = json.loads(raw)
    assert result["status"] == "NOT_FOUND"

