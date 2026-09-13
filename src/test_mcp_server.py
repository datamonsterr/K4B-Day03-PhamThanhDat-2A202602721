"""
Unit tests for mcp_server module (MCP Threads Server).
"""

import pytest

from src.mcp_server import MCPThreadsServer


def test_mcp_threads_server_initialization():
    """MCPThreadsServer initializes with default server name and version."""
    server = MCPThreadsServer()
    assert "threads" in server.server_name.lower()
    assert server.version == "2026.1.0"


def test_mcp_threads_server_list_tools():
    """list_tools returns all declared Threads MCP tools."""
    server = MCPThreadsServer()
    tools = server.list_tools()
    tool_names = [t["name"] for t in tools]
    assert "threads_get_profile" in tool_names
    assert "threads_get_threads" in tool_names
    assert "threads_get_thread" in tool_names
    assert "threads_create_thread" in tool_names
    assert "threads_reply_to_thread" in tool_names
    assert "threads_get_insights" in tool_names
    assert "threads_get_replies" in tool_names
    assert "threads_get_conversation" in tool_names
    assert "threads_search" in tool_names


def test_mcp_threads_server_call_tool_success():
    """call_tool executes tool and returns JSON-RPC 2.0 formatted response."""
    server = MCPThreadsServer()
    response = server.call_tool("threads_get_insights", {"thread_id": "th_post_001"})
    assert response["jsonrpc"] == "2.0"
    assert response["server"] == server.server_name
    assert response["tool"] == "threads_get_insights"
    assert response["result"]["status"] == "SUCCESS"
    assert response["result"]["thread_id"] == "th_post_001"
    assert "metrics" in response["result"]


def test_mcp_threads_server_call_tool_not_found():
    """call_tool returns NOT_FOUND inside result for non-existent thread."""
    server = MCPThreadsServer()
    response = server.call_tool("threads_get_insights", {"thread_id": "th_nonexistent_999"})
    assert response["jsonrpc"] == "2.0"
    assert response["result"]["status"] == "NOT_FOUND"


def test_mcp_threads_server_call_tool_create_thread():
    """call_tool executes threads_create_thread successfully."""
    server = MCPThreadsServer()
    response = server.call_tool(
        "threads_create_thread", {"text": "TDD for MCP Server works! 🚀"}
    )
    assert response["jsonrpc"] == "2.0"
    assert response["result"]["status"] == "SUCCESS"
    assert "id" in response["result"]


def test_mcp_threads_server_call_tool_search():
    """call_tool executes threads_search successfully."""
    server = MCPThreadsServer()
    response = server.call_tool("threads_search", {"query": "AI", "sort_by": "top_views"})
    assert response["jsonrpc"] == "2.0"
    assert response["result"]["status"] == "SUCCESS"
    assert len(response["result"]["data"]) > 0


def test_mcp_threads_server_call_unknown_tool():
    """call_tool handles unknown tool name gracefully."""
    server = MCPThreadsServer()
    response = server.call_tool("invalid_tool", {})
    assert response["jsonrpc"] == "2.0"
    assert response["result"]["status"] == "UNKNOWN_TOOL"
