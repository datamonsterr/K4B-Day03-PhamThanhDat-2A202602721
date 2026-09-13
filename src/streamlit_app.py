"""
🚀 STREAMLIT REACT AGENT CHAT APPLICATION
Giao diện Web Chat UI ChatGPT-style với ReAct Event Streaming (Thought, Tool Call, Observation),
Human-in-the-Loop (Duyệt/Từ chối bài viết, nhập liệu, trắc nghiệm),
và thanh trạng thái Backend Online hiển thị trên đỉnh trung tâm.
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Generator

from dotenv import load_dotenv
import requests
import streamlit as st

# Ensure src and repo root are in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
for p in (CURRENT_DIR, PARENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from agent_stream import AgentEvent, stream_react_agent
    from app import load_test_cases, save_waterfall_trace
    from mcp_server import MCPThreadsServer
    from providers import get_llm_provider
except ImportError:
    from src.agent_stream import AgentEvent, stream_react_agent
    from src.app import load_test_cases, save_waterfall_trace
    from src.mcp_server import MCPThreadsServer
    from src.providers import get_llm_provider

load_dotenv()


def get_backend_url() -> str:
    """Xác định URL backend server từ cấu hình môi trường .env."""
    backend_url = os.getenv("BACKEND_URL")
    if backend_url:
        return backend_url.rstrip("/")

    host = (
        os.getenv("BACKEND_HOST")
        or os.getenv("MCP_SERVER_HOST")
        or "localhost"
    )
    if host in ("0.0.0.0", ""):
        host = "localhost"

    port = os.getenv("BACKEND_PORT") or os.getenv("MCP_SERVER_PORT") or "8000"
    return f"http://{host}:{port}"


def check_backend_health(url: str, timeout: float = 0.8) -> bool:
    """Kiểm tra máy chủ backend có đang hoạt động hay không."""
    try:
        resp = requests.get(f"{url}/health", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def stream_backend_events(
    backend_url: str,
    query: str,
    provider_name: str,
    resumed_action: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Kết nối tới backend qua giao thức SSE stream để nhận sự kiện ReAct theo thời gian thực."""
    endpoint = f"{backend_url}/api/chat/stream"
    payload: dict[str, Any] = {
        "query": query,
        "provider": provider_name,
    }
    if resumed_action is not None:
        payload["resumed_action"] = resumed_action

    resp = requests.post(endpoint, json=payload, stream=True, timeout=90)
    try:
        resp.raise_for_status()
        for raw_line in resp.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            if isinstance(raw_line, bytes):
                raw_line = raw_line.decode("utf-8")
            line = raw_line.strip()
            if line.startswith("data:"):
                json_str = line[5:].strip()
                if not json_str:
                    continue
                try:
                    event = json.loads(json_str)
                    if event.get("type") == "done":
                        break
                    yield event
                except Exception:
                    continue
    finally:
        resp.close()


def stream_local_events(
    query: str,
    provider_name: str,
    resumed_action: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Chạy trực tiếp logic tác tử trong cùng tiến trình Streamlit (Local Embedded Engine)."""
    provider = get_llm_provider(provider_name)
    mcp_server = MCPThreadsServer()

    for agent_event in stream_react_agent(
        user_query=query,
        provider=provider,
        mcp_server=mcp_server,
        resumed_action=resumed_action,
    ):
        yield {
            "type": agent_event.type,
            "content": agent_event.content,
            "tool_name": agent_event.tool_name,
            "arguments": agent_event.arguments,
            "observation": agent_event.observation,
            "options": agent_event.options,
            "latency_ms": agent_event.latency_ms,
            "step": agent_event.step,
        }


def stream_events(
    query: str,
    provider_name: str,
    resumed_action: dict[str, Any] | None = None,
    use_backend: bool = True,
    backend_url: str = "http://localhost:8000",
) -> Generator[dict[str, Any], None, None]:
    """Bộ điều phối stream sự kiện: ưu tiên Backend SSE, tự động fallback về Local Engine."""
    if use_backend:
        try:
            yield from stream_backend_events(
                backend_url=backend_url,
                query=query,
                provider_name=provider_name,
                resumed_action=resumed_action,
            )
            return
        except Exception as e:
            yield {
                "type": "thought",
                "content": f"⚠️ Kết nối backend thất bại ({e!s}). Tự động chuyển sang Local Embedded Engine.",
                "step": 1,
            }

    yield from stream_local_events(
        query=query,
        provider_name=provider_name,
        resumed_action=resumed_action,
    )


def render_event_item(ev: dict[str, Any]) -> None:
    """Kết xuất chi tiết một sự kiện trong chuỗi vết suy luận ReAct."""
    etype = ev.get("type")
    if etype == "thought":
        st.markdown(f"**🧠 Suy luận (Thought):** *{ev.get('content', '')}*")
    elif etype == "tool_call":
        st.markdown(f"**🛠️ Gọi công cụ:** `{ev.get('tool_name', '')}`")
        st.caption("Tham số đầu vào (Arguments):")
        st.json(ev.get("arguments", {}))
    elif etype == "observation":
        st.markdown(f"**👁️ Kết quả quan sát từ:** `{ev.get('tool_name', '')}`")
        st.json(ev.get("observation", {}))
    elif etype == "ask_permission":
        st.warning(f"⚠️ Yêu cầu phê duyệt công cụ: `{ev.get('tool_name', '')}`")
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
        page_title="Threads ReAct Agent",
        page_icon="🤖",
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    # CSS to hide Streamlit sidebar completely and style ChatGPT-like suggestion boxes
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarNav"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }
        .suggestion-card {
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 14px 16px;
            background-color: #fafafa;
            height: 100%;
            transition: all 0.2s ease-in-out;
        }
        .suggestion-card:hover {
            border-color: #000;
            background-color: #ffffff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        .suggestion-title {
            font-weight: 600;
            font-size: 0.95rem;
            color: #111827;
            margin-bottom: 4px;
        }
        .suggestion-desc {
            font-size: 0.82rem;
            color: #6b7280;
            line-height: 1.35;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    init_session_state()

    backend_url = get_backend_url()
    is_backend_healthy = check_backend_health(backend_url)

    # ==========================================
    # 1. STATUS BADGE ABOVE CENTER (GREEN / RED)
    # ==========================================
    status_bg = "#e8f5e9" if is_backend_healthy else "#ffebee"
    status_border = "#a5d6a7" if is_backend_healthy else "#ef9a9a"
    status_color = "#2e7d32" if is_backend_healthy else "#c62828"
    status_icon = "🟢" if is_backend_healthy else "🔴"
    status_text = (
        f"Backend Online ({backend_url})"
        if is_backend_healthy
        else f"Backend Offline ({backend_url} - Chạy Local Engine)"
    )

    st.markdown(
        f"""
        <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 12px;">
            <div style="
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 4px 16px;
                border-radius: 9999px;
                background-color: {status_bg};
                border: 1px solid {status_border};
                color: {status_color};
                font-size: 0.82rem;
                font-weight: 500;
                letter-spacing: 0.2px;
            ">
                <span>{status_icon}</span>
                <span>{status_text}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Header Title
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="font-size: 2.1rem; font-weight: 700; margin-bottom: 6px; letter-spacing: -0.5px;">
                🤖 Threads ReAct Agent
            </h1>
            <p style="color: #6b7280; font-size: 0.95rem; margin: 0;">
                Tác tử thông minh quản lý kênh Threads với ReAct Streaming & Human-in-the-Loop
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Setup provider list & default matching .env
    provider_labels = {
        "OpenAI": "openai",
        "Google Gemini": "gemini",
        "Mock Offline (Free)": "mock",
    }
    env_provider = os.getenv("LLM_PROVIDER", "openai").lower()
    label_keys = list(provider_labels.keys())
    default_idx = 0
    for idx, (lbl, code) in enumerate(provider_labels.items()):
        if code == env_provider:
            default_idx = idx
            break

    # ==========================================
    # 2. CHATGPT-STYLE SUGGESTION CARDS (IN CENTER)
    # ==========================================
    if len(st.session_state.messages) == 0 and st.session_state.pending_interaction is None:
        st.markdown(
            """
            <div style="text-align: center; margin-top: 10px; margin-bottom: 18px;">
                <span style="font-size: 0.9rem; font-weight: 500; color: #4b5563;">
                    ✨ Gợi ý câu hỏi bắt đầu:
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sugg_col1, sugg_col2 = st.columns(2)

        with sugg_col1:
            if st.button(
                "💡 **Tư vấn viết Hook Threads**\n\nLàm sao để viết hook 3 dòng đầu giữ chân người đọc?",
                use_container_width=True,
                key="btn_sugg_1",
            ):
                st.session_state.submitted_query = "Làm sao để viết hook 3 dòng đầu giữ chân người đọc trên Threads?"
                st.rerun()

            if st.button(
                "✍️ **Xuất bản bài viết mới (HITL)**\n\nĐăng bài mới chia sẻ về ReAct Agent và MCP Protocol",
                use_container_width=True,
                key="btn_sugg_3",
            ):
                st.session_state.submitted_query = "Xuất bản bài viết: ReAct Agent và MCP Protocol là bước ngoặt đưa AI từ Chatbot phản hồi tĩnh sang Hệ thống Tác tử tự chủ hành động. Cùng thảo luận nhé! #VinUniAI #ReActAgent"
                st.rerun()

        with sugg_col2:
            if st.button(
                "📊 **Tra cứu chỉ số tương tác**\n\nXem lượt views, likes của bài viết th_post_001",
                use_container_width=True,
                key="btn_sugg_2",
            ):
                st.session_state.submitted_query = "Tra cứu chỉ số tương tác bài viết th_post_001"
                st.rerun()

            if st.button(
                "🔍 **Tìm bài viết hot nhất**\n\nTìm các bài viết về AI có nhiều lượt xem nhất trên kênh",
                use_container_width=True,
                key="btn_sugg_4",
            ):
                st.session_state.submitted_query = "Tìm các bài viết về AI có nhiều lượt xem nhất"
                st.rerun()

        st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

    # ==========================================
    # 3. CHAT HISTORY RENDERING
    # ==========================================
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        events = msg.get("events", [])

        with st.chat_message(role):
            if role == "assistant" and events:
                with st.expander(
                    "🔍 Chi tiết chuỗi suy luận (ReAct Trace)", expanded=False
                ):
                    for ev in events:
                        render_event_item(ev)
            st.markdown(content)

    # ==========================================
    # 4. PENDING HITL INTERACTION CARDS
    # ==========================================
    if st.session_state.pending_interaction is not None:
        pending = st.session_state.pending_interaction
        itype = pending.get("type")

        with st.chat_message("assistant"):
            if itype in ("permission", "ask_permission"):
                tool_name = pending.get("tool_name", "")
                args = pending.get("arguments", {})
                current_text = args.get("text", "")

                st.warning("⚠️ **Yêu cầu phê duyệt thao tác ghi dữ liệu / xuất bản**")
                st.markdown(
                    f"Tác tử đề xuất gọi công cụ **`{tool_name}`** với tham số dưới đây."
                )

                st.json(args)

                edited_text = st.text_area(
                    "✏️ Kiểm tra hoặc chỉnh sửa nội dung bài viết trước khi xuất bản:",
                    value=current_text,
                    key="hitl_edit_post_text",
                    height=90,
                )

                col_app, col_rej = st.columns(2)
                with col_app:
                    if st.button(
                        "✅ Phê duyệt & Thực thi",
                        type="primary",
                        use_container_width=True,
                        key="btn_hitl_approve_action",
                    ):
                        updated_args = dict(args)
                        if "text" in updated_args:
                            updated_args["text"] = edited_text
                        st.session_state.trigger_resumption = {
                            "action": "approve",
                            "tool_name": tool_name,
                            "arguments": updated_args,
                            "query": pending.get("query", ""),
                            "step": pending.get("step", 1),
                        }
                        st.rerun()

                with col_rej:
                    if st.button(
                        "❌ Từ chối",
                        type="secondary",
                        use_container_width=True,
                        key="btn_hitl_reject_action",
                    ):
                        st.session_state.trigger_resumption = {
                            "action": "reject",
                            "tool_name": tool_name,
                            "arguments": args,
                            "reason": "Người dùng đã từ chối thao tác xuất bản này.",
                            "query": pending.get("query", ""),
                            "step": pending.get("step", 1),
                        }
                        st.rerun()

            elif itype in ("text_input", "ask_input"):
                prompt_text = pending.get("content") or pending.get("prompt", "")
                st.info(
                    f"✏️ **Tác tử yêu cầu thêm thông tin:** {prompt_text}"
                )
                user_val = st.text_input("Nội dung phản hồi:", key="hitl_user_text_input")
                if st.button("Gửi phản hồi", type="primary", key="btn_hitl_send_text"):
                    st.session_state.trigger_resumption = {
                        "action": "submit_input",
                        "tool_name": pending.get("tool_name", ""),
                        "response": user_val,
                        "query": pending.get("query", ""),
                        "step": pending.get("step", 1),
                    }
                    st.rerun()

            elif itype in ("choice", "ask_choice"):
                prompt_text = pending.get("content") or pending.get("prompt", "")
                st.info(
                    f"🔘 **Tác tử yêu cầu chọn:** {prompt_text}"
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
    # 5. RESUMPTION PROCESSING (AFTER HITL DUYỆT / TỪ CHỐI)
    # ==========================================
    # Bottom configs are read first so provider_code is accessible
    bottom_prov_idx = default_idx
    if "bottom_provider_idx" in st.session_state:
        bottom_prov_idx = st.session_state.bottom_provider_idx
    provider_code = provider_labels[label_keys[bottom_prov_idx]]
    use_backend = is_backend_healthy

    if st.session_state.get("trigger_resumption") is not None:
        resumed_action = st.session_state.pop("trigger_resumption")
        pending = st.session_state.pop("pending_interaction", None) or {}
        prior_events = pending.get("events", [])
        active_query = resumed_action.get("query", "")

        resumed_events = []
        final_answer_event = None

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

                for event in event_iter:
                    if event.get("type") not in ("token", "done"):
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
                    if ev.get("type") not in ("token", "done"):
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
    # 6. MAIN CHAT INPUT
    # ==========================================
    hitl_active = st.session_state.pending_interaction is not None
    placeholder = (
        "⚠️ Đang chờ phản hồi trên thẻ tương tác ở trên..."
        if hitl_active
        else "Nhập câu hỏi hoặc yêu cầu cho Threads ReAct Agent..."
    )

    incoming_query = None
    if st.session_state.submitted_query:
        incoming_query = st.session_state.pop("submitted_query")
    else:
        incoming_query = st.chat_input(placeholder, disabled=hitl_active)

    # ==========================================
    # 7. LLM PROVIDER & CONTROLS BELOW PROMPT BOX
    # ==========================================
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([4, 3, 3])

    with ctrl_col1:
        sel_label = st.selectbox(
            "Mô hình LLM:",
            label_keys,
            index=default_idx,
            key="bottom_provider_select",
            help="Chọn mô hình LLM để tác tử suy luận và tự sinh từ khóa tìm kiếm",
        )
        st.session_state.bottom_provider_idx = label_keys.index(sel_label)
        provider_code = provider_labels[sel_label]

    with ctrl_col2:
        st.write("")
        st.write("")
        if st.button("🗑️ Xóa hội thoại", use_container_width=True, key="btn_clear_chat"):
            st.session_state.messages = []
            st.session_state.pending_interaction = None
            st.session_state.waterfall_traces = []
            st.rerun()

    with ctrl_col3:
        st.write("")
        st.write("")
        st.download_button(
            label="📥 Tải Trace (JSON)",
            data=json.dumps(
                st.session_state.waterfall_traces, ensure_ascii=False, indent=2
            ),
            file_name="trace_waterfall.json",
            mime="application/json",
            use_container_width=True,
            key="btn_download_traces",
        )

    # ==========================================
    # 8. EXECUTE INCOMING QUERY
    # ==========================================
    if incoming_query:
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
                    if event.get("type") not in ("token", "done"):
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
                        st.session_state.pending_interaction = {
                            "type": "permission",
                            "tool_name": event.get("tool_name", ""),
                            "arguments": event.get("arguments", {}),
                            "query": incoming_query,
                            "step": event.get("step", 1),
                            "events": current_events,
                        }
                        status.update(
                            label="⚠️ Chờ phê duyệt của người dùng",
                            state="running",
                            expanded=True,
                        )
                        is_paused = True
                        break

                    elif etype == "ask_input":
                        current_events.append(event)
                        st.session_state.pending_interaction = {
                            "type": "text_input",
                            "tool_name": event.get("tool_name", ""),
                            "content": event.get("content", ""),
                            "query": incoming_query,
                            "step": event.get("step", 1),
                            "events": current_events,
                        }
                        status.update(
                            label="✏️ Chờ nhập liệu",
                            state="running",
                            expanded=True,
                        )
                        is_paused = True
                        break

                    elif etype == "ask_choice":
                        current_events.append(event)
                        st.session_state.pending_interaction = {
                            "type": "choice",
                            "tool_name": event.get("tool_name", ""),
                            "content": event.get("content", ""),
                            "options": event.get("options", []),
                            "query": incoming_query,
                            "step": event.get("step", 1),
                            "events": current_events,
                        }
                        status.update(
                            label="🔘 Chờ lựa chọn",
                            state="running",
                            expanded=True,
                        )
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

            fallback_text = (
                final_answer_event.get("content", "")
                if final_answer_event
                else ""
            )

            def stream_tokens_iter():
                tokens_found = False
                for ev in event_iter:
                    if ev.get("type") not in ("token", "done"):
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
