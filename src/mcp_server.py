"""
🔌 THREADS MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa cho kênh Threads.
"""

import contextlib
import io
import json
import sys
from typing import Any

try:
    from src.tools import TOOLS_SCHEMA, dispatch_tool_call
except ModuleNotFoundError:
    from tools import TOOLS_SCHEMA, dispatch_tool_call

if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding != "utf-8":
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")


class MCPThreadsServer:
    """
    MCP Server tuân thủ chuẩn giao thức Model Context Protocol cho kênh Threads.
    """

    def __init__(self, server_name: str = "vinuni-threads-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"

    def list_tools(self) -> list[dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC 2.0
        """
        raw_result = dispatch_tool_call(tool_name, arguments)
        try:
            content = json.loads(raw_result)
        except Exception:
            content = {"status": "PARSE_ERROR", "raw": raw_result}

        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content,
        }


# Backward compatibility alias
MCPAcademicServer = MCPThreadsServer


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (vinuni-threads-mcp-server)")
    print("==========================================================")

    server = MCPThreadsServer()
    tools = server.list_tools()
    print(
        f"✅ Khởi tạo thành công MCP Server: {server.server_name} (Version: {server.version})"
    )
    print(f"📦 Số lượng Tools công bố: {len(tools)}")

    # Test tool call
    test_result = server.call_tool("threads_get_insights", {"thread_id": "th_post_001"})
    print("✅ Test dispatch tool 'threads_get_insights':")
    print(f"   Phản hồi JSON-RPC: {json.dumps(test_result, ensure_ascii=False)}")
