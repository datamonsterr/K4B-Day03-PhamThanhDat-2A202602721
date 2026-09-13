"""
📱 THREADS REACT AGENT - STREAMLIT WEB UI
Event Streaming ReAct UI with Live Status & Human-in-the-Loop (HITL) Interactivity.
"""
import dataclasses
import json
import os
import sys
from typing import Any, Generator

from dotenv import load_dotenv
import requests
import streamlit as st

# Add project root and src directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
for path in (BASE_DIR, SRC_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from src.agent_stream import stream_react_agent
from src.app import load_test_cases, save_waterfall_trace
from src.mcp_server import MCPThreadsServer
from src.providers import get_llm_provider

load_dotenv()


def get_backend_url() -> str:
    """Đọc cấu hình URL backend từ biến môi trường."""
    host = os.getenv("BACKEND_HOST") or os.getenv("MCP_SERVER_HOST") or "localhost"
    port = os.getenv("BACKEND_PORT") or os.getenv("MCP_SERVER_PORT") or "8000"
    return os.getenv("BACKEND_URL", f"http://{host}:{port}")


def check_backend_health(backend_url: str, timeout: float = 1.5) -> bool:
    """Kiểm tra xem backend server có đang hoạt động hay không."""
    try:
        resp = requests.get(f"{backend_url}/health", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def stream_backend_events(
    backend_url: str,
    query: str,
    provider: str,
    resumed_action: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Kết nối tới POST /api/chat/stream và parse SSE stream (Server-Sent Events)."""
    payload = {
        "query": query,
        "provider": provider,
        "resumed_action": resumed_action,
    }
    response = requests.post(
        f"{backend_url}/api/chat/stream",
        json=payload,
        stream=True,
        timeout=60,
    )
    response.raise_for_status()

    for line in response.iter_lines(decode_unicode=True):
        if line:
            line = line.strip()
            if line.startswith("data:"):
                raw_json = line[len("data:") :].strip()
                if raw_json:
                    event = json.loads(raw_json)
                    if event.get("type") == "done":
                        break
                    yield event


def stream_local_events(
    query: str,
    provider_name: str,
    resumed_action: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Chạy trực tiếp generator stream_react_agent trong tiến trình local."""
    provider = get_llm_provider(provider_name)
    mcp_server = MCPThreadsServer()

    for event in stream_react_agent(
        user_query=query,
        provider=provider,
        mcp_server=mcp_server,
        resumed_action=resumed_action,
    ):
        if dataclasses.is_dataclass(event):
            yield dataclasses.asdict(event)
        elif isinstance(event, dict):
            yield event
        else:
            yield vars(event)


def stream_events(
    query: str,
    provider_name: str,
    resumed_action: dict[str, Any] | None = None,
    use_backend: bool = True,
    backend_url: str | None = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Hàm phát sinh event thống nhất:
    Ưu tiên gọi Backend SSE stream nếu use_backend=True;
    nếu lỗi kết nối thì tự động fallback về Local Embedded Engine.
    """
    target_url = backend_url or get_backend_url()
    if use_backend:
        try:
            yield from stream_backend_events(
                target_url, query, provider_name, resumed_action
            )
            return
        except Exception as e:
            yield {
                "type": "thought",
                "content": f"⚠️ Kết nối Backend ({target_url}) thất bại ({e}). Đang tự động chuyển sang Local Embedded Engine.",
                "step": 1,
            }

    yield from stream_local_events(query, provider_name, resumed_action)


def render_trace_events(events: list[dict[str, Any]]) -> None:
    """Hiển thị chuỗi sự kiện ReAct trace trong expander hoặc container."""
    for ev in events:
        etype = ev.get("type")
        if etype == "thought":
            st.markdown(
                f"**🧠 Thought (Step {ev.get('step', 1)}):** *{ev.get('content', '')}*"
            )
        elif etype == "tool_call":
            tname = ev.get("tool_name", "")
            st.write(f"🛠️ Gọi công cụ **`{tname}`** với tham số:")
            st.json(ev.get("arguments", {}))
        elif etype == "observation":
            tname = ev.get("tool_name", "")
            st.write(f"👁️ Kết quả quan sát từ **`{tname}`**:")
            st.json(ev.get("observation", {}))
        elif etype == "ask_permission":
            st.warning(
                f"⚠️ Yêu cầu phê duyệt hành động ghi dữ liệu cho **`{ev.get('tool_name', '')}`**"
            )
            st.json(ev.get("arguments", {}))
        elif etype in ("ask_input", "ask_choice"):
            st.info(f"❓ Tương tác người dùng: {ev.get('content', '')}")


def init_session_state() -> None:
    """Khởi tạo trạng thái phiên làm việc trong st.session_state."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_interaction" not in st.session_state:
        st.session_state.pending_interaction = None
    if "waterfall_traces" not in st.session_state:
        st.session_state.waterfall_traces = []
    if "trigger_resumption" not in st.session_state:
        st.session_state.trigger_resumption = None
    if "submitted_query" not in st.session_state:
        st.session_state.submitted_query = None


def main() -> None:
    st.set_page_config(
        page_title="Threads ReAct Agent - Chat UI",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    backend_url = get_backend_url()
    is_backend_healthy = check_backend_health(backend_url)

    # ==========================================
    # SIDEBAR CONTROLS
    # ==========================================
    st.sidebar.title("🤖 Threads ReAct Agent")
    st.sidebar.caption(
        "Day 03: Event Streaming Chat UI with Human-in-the-Loop Control"
    )

    st.sidebar.markdown("### 🌐 Backend Server Status")
    force_local = st.sidebar.checkbox(
        "Chạy Local Embedded Engine",
        value=not is_backend_healthy,
        help="Bỏ qua backend server và thực thi logic tác tử trực tiếp trong tiến trình Streamlit.",
    )

    use_backend = is_backend_healthy and not force_local
    if use_backend:
        st.sidebar.success(f"🟢 Backend Online: {backend_url}")
    else:
        st.sidebar.warning(
            f"🟡 Mode: Local Engine {'(Offline)' if not is_backend_healthy else '(Manual)'}"
        )

    st.sidebar.markdown("### 🔌 LLM Provider")
    provider_labels = {
        "Mock Offline (Free)": "mock",
        "Google Gemini": "gemini",
        "OpenAI": "openai",
    }
    selected_provider_label = st.sidebar.selectbox(
        "Chọn mô hình ngôn ngữ:",
        list(provider_labels.keys()),
        index=0,
    )
    provider_code = provider_labels[selected_provider_label]

    # API Key status and optional override
    if provider_code == "gemini":
        gemini_env = os.getenv("GEMINI_API_KEY")
        if gemini_env and gemini_env != "your_gemini_api_key_here":
            st.sidebar.caption("🔑 Gemini Key: Đã nạp từ .env")
        else:
            st.sidebar.caption("⚠️ Gemini Key: Chưa cấu hình trong .env")
        override_gemini = st.sidebar.text_input(
            "Nhập Gemini API Key tùy chọn:",
            type="password",
            key="input_gemini_override",
        )
        if override_gemini:
            os.environ["GEMINI_API_KEY"] = override_gemini

    elif provider_code == "openai":
        openai_env = os.getenv("OPENAI_API_KEY")
        if openai_env and openai_env != "your_openai_api_key_here":
            st.sidebar.caption("🔑 OpenAI Key: Đã nạp từ .env")
        else:
            st.sidebar.caption("⚠️ OpenAI Key: Chưa cấu hình trong .env")
        override_openai = st.sidebar.text_input(
            "Nhập OpenAI API Key tùy chọn:",
            type="password",
            key="input_openai_override",
        )
        if override_openai:
            os.environ["OPENAI_API_KEY"] = override_openai
    else:
        st.sidebar.info(
            "💡 Mock Offline Provider: Không cần API Key, hoàn toàn miễn phí."
        )

    # Quick Sample Test Cases
    st.sidebar.markdown("### 🧪 Quick Sample Test Cases")
    test_cases = load_test_cases()
    test_case_descriptions = {
        "TC01": "TC01: Tư vấn viết hook bài đăng Threads (Không gọi tool)",
        "TC02": "TC02: Tra cứu chỉ số tương tác bài viết th_post_001 (Read tool - Auto)",
        "TC03": "TC03: Xuất bản bài viết mới lên Threads (Write tool - Kích hoạt HITL Phê duyệt)",
        "TC04": "TC04: Tìm bài viết có tương tác cao nhất (Multi-step Reasoning)",
        "TC05": "TC05: Kiểm tra bài viết không tồn tại th_post_999 (Tool Failure / Edge case)",
    }

    for tc in test_cases:
        t_id = tc.get("id", "")
        btn_label = test_case_descriptions.get(
            t_id, f"[{t_id}] {tc.get('type', '')}"
        )
        if st.sidebar.button(
            btn_label, key=f"btn_tc_{t_id}", use_container_width=True
        ):
            st.session_state.submitted_query = tc.get("question", "")
            st.rerun()

    # Session Actions
    st.sidebar.markdown("### ⚙️ Session Actions")
    if st.sidebar.button(
        "🗑️ Xóa lịch sử trò chuyện",
        use_container_width=True,
        type="secondary",
    ):
        st.session_state.messages = []
        st.session_state.pending_interaction = None
        st.session_state.waterfall_traces = []
        st.session_state.trigger_resumption = None
        st.session_state.submitted_query = None
        st.rerun()

    st.sidebar.download_button(
        label="📥 Tải file Trace Waterfall (JSON)",
        data=json.dumps(
            st.session_state.waterfall_traces, ensure_ascii=False, indent=2
        ),
        file_name="trace_waterfall.json",
        mime="application/json",
        use_container_width=True,
    )

    # ==========================================
    # MAIN CHAT AREA
    # ==========================================
    st.title("📱 Threads AI ReAct Agent - Interactive Chat UI")
    st.markdown(
        "Hệ thống Tác tử ReAct minh bạch hiển thị **Thought, Tool Calling, Observation** theo thời gian thực "
        "và bảo vệ an toàn qua cơ chế **Human-in-the-Loop (HITL)**."
    )

    # Render message history
    for msg in st.session_state.messages:
        role = msg.get("role")
        content = msg.get("content", "")
        events = msg.get("events", [])

        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        elif role == "assistant":
            with st.chat_message("assistant"):
                if events:
                    with st.expander(
                        "🔍 Chi tiết chuỗi suy luận (ReAct Trace)",
                        expanded=False,
                    ):
                        render_trace_events(events)
                st.markdown(content)

    # ==========================================
    # HUMAN-IN-THE-LOOP (HITL) INTERACTIVE CARDS
    # ==========================================
    if st.session_state.pending_interaction is not None:
        pending = st.session_state.pending_interaction
        ptype = pending.get("type")

        with st.container(border=True):
            if ptype == "permission":
                st.warning("⚠️ **Yêu cầu phê duyệt hành động ghi dữ liệu**")
                tool_name = pending.get("tool_name", "")
                raw_args = pending.get("arguments", {})
                st.write(f"Công cụ yêu cầu thực thi: **`{tool_name}`**")
                st.write("Tham số hiện tại:")
                st.json(raw_args)

                # Editable text area for post content (syntax / text tweak)
                current_text = raw_args.get("text", "")
                edited_text = st.text_area(
                    "Nội dung bài viết (có thể chỉnh sửa trước khi phê duyệt):",
                    value=current_text,
                    key="hitl_edit_text_area",
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✅ Phê duyệt & Thực thi",
                        type="primary",
                        use_container_width=True,
                        key="btn_hitl_approve",
                    ):
                        edited_arguments = dict(raw_args)
                        if "text" in edited_arguments:
                            edited_arguments["text"] = edited_text
                        st.session_state.trigger_resumption = {
                            "action": "approve",
                            "tool_name": tool_name,
                            "arguments": edited_arguments,
                            "query": pending.get("query", ""),
                            "step": pending.get("step", 1),
                        }
                        st.rerun()

                with col2:
                    if st.button(
                        "❌ Từ chối",
                        type="secondary",
                        use_container_width=True,
                        key="btn_hitl_reject",
                    ):
                        st.session_state.trigger_resumption = {
                            "action": "reject",
                            "tool_name": tool_name,
                            "arguments": raw_args,
                            "reason": "Người dùng đã từ chối thao tác",
                            "query": pending.get("query", ""),
                            "step": pending.get("step", 1),
                        }
                        st.rerun()

            elif ptype == "ask_input":
                st.info(
                    f"❓ **Yêu cầu phản hồi từ Agent:**\n\n{pending.get('prompt', '')}"
                )
                user_text = st.text_input(
                    "Câu trả lời của bạn:", key="hitl_user_text_val"
                )
                if st.button(
                    "Gửi phản hồi",
                    type="primary",
                    key="btn_hitl_send_input",
                ):
                    st.session_state.trigger_resumption = {
                        "action": "submit_input",
                        "tool_name": pending.get("tool_name", ""),
                        "response": user_text,
                        "query": pending.get("query", ""),
                        "step": pending.get("step", 1),
                    }
                    st.rerun()

            elif ptype == "ask_choice":
                st.info(
                    f"❓ **Lựa chọn từ Agent:**\n\n{pending.get('prompt', '')}"
                )
                options = pending.get("options", [])
                chosen_opt = st.radio(
                    "Tùy chọn:", options=options, key="hitl_user_radio_choice"
                )
                if st.button("Chọn", type="primary", key="btn_hitl_send_choice"):
                    st.session_state.trigger_resumption = {
                        "action": "submit_choice",
                        "tool_name": pending.get("tool_name", ""),
                        "response": chosen_opt,
                        "query": pending.get("query", ""),
                        "step": pending.get("step", 1),
                    }
                    st.rerun()

    # ==========================================
    # RESUMPTION PROCESSING (AFTER HITL INTERACTION)
    # ==========================================
    if st.session_state.get("trigger_resumption") is not None:
        resumed_action = st.session_state.pop("trigger_resumption")
        pending = st.session_state.pop("pending_interaction", None) or {}
        prior_events = pending.get("events", [])
        active_query = resumed_action.get("query", "")

        resumed_events = []
        is_paused = False

        with st.chat_message("assistant"):
            with st.status(
                "🧠 Agent Resuming Execution...", expanded=True
            ) as status:
                event_iter = stream_events(
                    query=active_query,
                    provider_name=provider_code,
                    resumed_action=resumed_action,
                    use_backend=use_backend,
                    backend_url=backend_url,
                )

                final_answer_event = None

                for event in event_iter:
                    st.session_state.waterfall_traces.append(event)
                    etype = event.get("type")

                    if etype == "thought":
                        resumed_events.append(event)
                        status.update(label="🧠 Thinking...", state="running")
                        st.markdown(f"**🧠 Thought:** *{event.get('content', '')}*")

                    elif etype == "tool_call":
                        resumed_events.append(event)
                        tname = event.get("tool_name", "")
                        status.update(
                            label=f"🛠️ Calling tool `{tname}`...",
                            state="running",
                        )
                        st.write(f"Calling **`{tname}`** with arguments:")
                        st.json(event.get("arguments", {}))

                    elif etype == "observation":
                        resumed_events.append(event)
                        tname = event.get("tool_name", "")
                        status.update(
                            label=f"👁️ Observed output from `{tname}`",
                            state="running",
                        )
                        st.write("Observation:")
                        st.json(event.get("observation", {}))

                    elif etype == "final_answer":
                        final_answer_event = event
                        status.update(
                            label="✅ Reasoning complete",
                            state="complete",
                            expanded=False,
                        )
                        break

            # Stream remaining token events outside status block
            fallback_text = (
                final_answer_event.get("content", "")
                if final_answer_event
                else ""
            )

            def stream_tokens_iter():
                tokens_found = False
                for ev in event_iter:
                    st.session_state.waterfall_traces.append(ev)
                    if ev.get("type") == "token":
                        tokens_found = True
                        yield ev.get("content", "")
                    elif ev.get("type") == "done":
                        break
                if not tokens_found and fallback_text:
                    yield fallback_text

            final_text = st.write_stream(stream_tokens_iter)

        all_events = prior_events + resumed_events
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": final_text,
                "events": all_events,
            }
        )
        save_waterfall_trace(st.session_state.waterfall_traces)
        st.rerun()

    # ==========================================
    # NEW QUERY SUBMISSION
    # ==========================================
    incoming_query = None
    if st.session_state.get("submitted_query"):
        incoming_query = st.session_state.pop("submitted_query")
    else:
        # Disable input if an interaction is waiting for approval
        hitl_active = st.session_state.pending_interaction is not None
        placeholder = (
            "⚠️ Đang chờ phản hồi trên thẻ tương tác..."
            if hitl_active
            else "Nhập câu hỏi hoặc yêu cầu cho Threads ReAct Agent..."
        )
        incoming_query = st.chat_input(placeholder, disabled=hitl_active)

    if incoming_query:
        # Add and display user message
        st.session_state.messages.append(
            {"role": "user", "content": incoming_query, "events": []}
        )
        with st.chat_message("user"):
            st.markdown(incoming_query)

        current_events = []
        is_paused = False
        final_answer_event = None

        with st.chat_message("assistant"):
            with st.status("🧠 Agent Reasoning...", expanded=True) as status:
                event_iter = stream_events(
                    query=incoming_query,
                    provider_name=provider_code,
                    resumed_action=None,
                    use_backend=use_backend,
                    backend_url=backend_url,
                )

                for event in event_iter:
                    st.session_state.waterfall_traces.append(event)
                    etype = event.get("type")

                    if etype == "thought":
                        current_events.append(event)
                        status.update(label="🧠 Thinking...", state="running")
                        st.markdown(f"**🧠 Thought:** *{event.get('content', '')}*")

                    elif etype == "tool_call":
                        current_events.append(event)
                        tname = event.get("tool_name", "")
                        status.update(
                            label=f"🛠️ Calling tool `{tname}`...",
                            state="running",
                        )
                        st.write(f"Calling **`{tname}`** with arguments:")
                        st.json(event.get("arguments", {}))

                    elif etype == "observation":
                        current_events.append(event)
                        tname = event.get("tool_name", "")
                        status.update(
                            label=f"👁️ Observed output from `{tname}`",
                            state="running",
                        )
                        st.write("Observation:")
                        st.json(event.get("observation", {}))

                    elif etype == "ask_permission":
                        current_events.append(event)
                        status.update(
                            label="⚠️ Chờ phê duyệt của người dùng",
                            state="running",
                        )
                        st.session_state.pending_interaction = {
                            "type": "permission",
                            "tool_name": event.get("tool_name", ""),
                            "arguments": event.get("arguments", {}),
                            "query": incoming_query,
                            "step": event.get("step", 1),
                            "events": current_events,
                        }
                        is_paused = True
                        break

                    elif etype == "ask_input":
                        current_events.append(event)
                        status.update(
                            label="❓ Yêu cầu phản hồi từ người dùng",
                            state="running",
                        )
                        st.session_state.pending_interaction = {
                            "type": "ask_input",
                            "prompt": event.get("content", ""),
                            "tool_name": event.get("tool_name", ""),
                            "arguments": event.get("arguments", {}),
                            "query": incoming_query,
                            "step": event.get("step", 1),
                            "events": current_events,
                        }
                        is_paused = True
                        break

                    elif etype == "ask_choice":
                        current_events.append(event)
                        status.update(
                            label="🔘 Yêu cầu lựa chọn từ người dùng",
                            state="running",
                        )
                        st.session_state.pending_interaction = {
                            "type": "ask_choice",
                            "prompt": event.get("content", ""),
                            "options": event.get("options", []),
                            "tool_name": event.get("tool_name", ""),
                            "arguments": event.get("arguments", {}),
                            "query": incoming_query,
                            "step": event.get("step", 1),
                            "events": current_events,
                        }
                        is_paused = True
                        break

                    elif etype == "final_answer":
                        final_answer_event = event
                        status.update(
                            label="✅ Reasoning complete",
                            state="complete",
                            expanded=False,
                        )
                        break

            if is_paused:
                save_waterfall_trace(st.session_state.waterfall_traces)
                st.rerun()

            # Stream tokens
            fallback_text = (
                final_answer_event.get("content", "")
                if final_answer_event
                else ""
            )

            def stream_tokens_iter():
                tokens_found = False
                for ev in event_iter:
                    st.session_state.waterfall_traces.append(ev)
                    if ev.get("type") == "token":
                        tokens_found = True
                        yield ev.get("content", "")
                    elif ev.get("type") == "done":
                        break
                if not tokens_found and fallback_text:
                    yield fallback_text

            final_text = st.write_stream(stream_tokens_iter)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": final_text,
                "events": current_events,
            }
        )
        save_waterfall_trace(st.session_state.waterfall_traces)
        st.rerun()


if __name__ == "__main__":
    main()
