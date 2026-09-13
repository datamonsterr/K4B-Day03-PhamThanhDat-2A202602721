"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT - THREADS MCP)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối Threads MCP Server (Cấp 3).
"""

import contextlib
import io
import json
import os
import sys
import time

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding != "utf-8":
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")

from mcp_server import MCPThreadsServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    MAX_ITERATIONS,
    REACT_AGENT_SYSTEM_PROMPT,
)
from providers import get_llm_provider

load_dotenv()


def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print(
                "⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'."
            )
            print(
                "👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n"
            )
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(
        f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!"
    )


def run_baseline_chatbot(user_query: str, provider) -> str:
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")
    return response


def _format_threads_observation(tool_name: str, obs_data: dict) -> str:
    """Định dạng kết quả Observation từ Threads MCP Server thành câu trả lời cho người dùng."""
    status = obs_data.get("status")

    if status == "NOT_FOUND":
        return obs_data.get(
            "message", f"Không tìm thấy dữ liệu yêu cầu khi gọi công cụ '{tool_name}'."
        )

    if status == "EXECUTION_ERROR":
        return f"Lỗi thực thi công cụ '{tool_name}': {obs_data.get('error', 'Không rõ nguyên nhân')}."

    if status == "UNKNOWN_TOOL":
        return f"Công cụ '{tool_name}' không tồn tại trên hệ thống MCP Server."

    if tool_name == "threads_get_insights":
        m = obs_data.get("metrics", {})
        tid = obs_data.get("thread_id", "")
        return (
            f"Chỉ số tương tác bài viết '{tid}': "
            f"{m.get('views', 0):,} Views, {m.get('likes', 0):,} Likes, "
            f"{m.get('replies', 0):,} Replies, {m.get('reposts', 0):,} Reposts, {m.get('quotes', 0):,} Quotes."
        )

    if tool_name == "threads_create_thread":
        return (
            f"Xuất bản thành công bài viết mới lên Threads (ID: {obs_data.get('id', '')}). "
            f"Liên kết bài đăng: {obs_data.get('permalink', '')}. Nội dung: \"{obs_data.get('text', '')}\""
        )

    if tool_name == "threads_reply_to_thread":
        return (
            f"Phản hồi thành công vào bài viết '{obs_data.get('thread_id', '')}' (Reply ID: {obs_data.get('id', '')}). "
            f"Nội dung phản hồi: \"{obs_data.get('text', '')}\""
        )

    if tool_name == "threads_get_thread":
        d = obs_data.get("data", {})
        tid = obs_data.get("thread_id", "")
        return (
            f"Thông tin bài viết '{tid}': \"{d.get('text', '')}\" "
            f"(Thời gian: {d.get('timestamp', '')}, Loại: {d.get('media_type', '')}). Link: {d.get('permalink', '')}"
        )

    if tool_name == "threads_get_threads":
        threads = obs_data.get("data", [])
        summaries = [f"- [{t.get('id')}]: \"{t.get('text', '')[:60]}...\"" for t in threads]
        return f"Danh sách {len(threads)} bài viết gần đây trên kênh:\n" + "\n".join(summaries)

    if tool_name == "threads_get_profile":
        p = obs_data.get("data", {})
        return (
            f"Hồ sơ kênh @{p.get('username', '')} ({p.get('name', '')}): {p.get('threads_biography', '')} "
            f"(Người theo dõi: {p.get('followers_count', 0):,})."
        )

    if tool_name == "threads_search":
        items = obs_data.get("data", [])
        q = obs_data.get("query", "")
        sort = obs_data.get("sort_by", "top_views")
        if not items:
            return f"Không tìm thấy bài viết nào phù hợp với từ khóa '{q}'."
        sort_label = "Lượt xem cao nhất" if sort == "top_views" else ("Lượt thích nhiều nhất" if sort == "top_likes" else "Mới nhất")
        lines = [f"Kết quả tìm kiếm cho chủ đề '{q}' ({sort_label}):"]
        for i, post in enumerate(items, 1):
            views = post.get("views", 0)
            likes = post.get("likes", 0)
            lines.append(
                f"{i}. [{post.get('id')}]: \"{post.get('text', '')}\" "
                f"({views:,} Views, {likes:,} Likes) - Link: {post.get('permalink', '')}"
            )
        return "\n".join(lines)

    if tool_name == "threads_get_replies":
        replies = obs_data.get("data", [])
        return f"Bài viết '{obs_data.get('thread_id', '')}' có {len(replies)} phản hồi từ người dùng."

    if "message" in obs_data:
        return obs_data["message"]

    return f"Đã hoàn tất xử lý qua MCP Server: {json.dumps(obs_data, ensure_ascii=False)}"


def run_react_agent(user_query: str, provider, mcp_server: MCPThreadsServer) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")

    step = 0
    trace_logs = []
    tools_list = mcp_server.list_tools()

    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")

        # Gọi LLM với Native Tool Calling Specs
        llm_response = provider.generate_with_tools(
            user_query, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT
        )
        latency_ms = round((time.time() - step_start_time) * 1000, 2)

        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")

        # Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append(
                {
                    "step": step,
                    "query": user_query,
                    "action_type": "FINAL_ANSWER",
                    "thought": thought,
                    "output": final_content,
                    "latency_ms": latency_ms,
                }
            )
            break

        # Trường hợp 2: LLM đề xuất gọi Tool (Action)
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})

            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")

            # Thực thi Tool qua MCP Server
            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})

            if not obs_data:
                print("👁️ [Observation từ MCP Server]: {}")
                final_answer = f"Chưa thể trả lời chi tiết do công cụ '{tool_name}' không trả về kết quả."
            else:
                obs_str = json.dumps(obs_data, ensure_ascii=False)
                print(f"👁️ [Observation từ MCP Server]: {obs_str}")
                final_answer = _format_threads_observation(tool_name, obs_data)

            trace_logs.append(
                {
                    "step": step,
                    "query": user_query,
                    "action_type": "TOOL_EXECUTION",
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "observation": obs_data,
                    "latency_ms": latency_ms,
                }
            )

            # Xuất Final Answer sau khi nhận kết quả Observation
            print(
                "🧠 [Thought]: Đã nhận được dữ liệu từ MCP Server. Tổng hợp kết quả phản hồi."
            )
            print(f"🏁 [Final Answer]: {final_answer}")

            trace_logs.append(
                {
                    "step": step + 1,
                    "query": user_query,
                    "action_type": "FINAL_ANSWER",
                    "thought": "Tổng hợp kết quả từ MCP Server thành công.",
                    "output": final_answer,
                    "latency_ms": 10.0,
                }
            )
            break

    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("📱 THREADS AI AGENT - DAY 03 LAB: CHATBOT VS REACT AGENT")
    print("==========================================================")

    provider = get_llm_provider()
    mcp_server = MCPThreadsServer()

    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")

    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")

    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với Threads ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Kỹ thuật viết bài: 'Phân tích kỹ thuật viết hook 3 dòng đầu giữ chân người đọc'")
        print("   - Tra cứu chỉ số: 'Hãy tra cứu các chỉ số tương tác của bài viết th_post_001'")
        print("   - Đăng bài mới: 'Xuất bản bài viết mới lên kênh Threads với nội dung: Chào thế giới AI Agent!'")
        print("   - Trường hợp lỗi: 'Kiểm tra thông tin bài đăng th_post_999'")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
        while True:
            try:
                user_input = input("👤 Quản trị viên hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        todo_count = 0
        all_traces = []

        for tc in tests:
            print("\n==================================================")
            print(
                f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})"
            )
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")

            if tc["question"].strip().startswith("TODO"):
                print("⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(
                    "   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!"
                )
                todo_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1

        print("\n==================================================")
        print(
            f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)"
        )
        if all_traces:
            save_waterfall_trace(all_traces)
        print(
            "💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'"
        )
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")

        sample_query = tests[1]["question"]
        print("--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu chỉ số tương tác) ---")
        logs = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(logs)
        print(
            "\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!"
        )
