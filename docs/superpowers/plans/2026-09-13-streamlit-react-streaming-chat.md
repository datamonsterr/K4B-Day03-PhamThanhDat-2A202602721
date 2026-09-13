# Streamlit ReAct Agent Chat UI with Event Streaming & Human-in-the-Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive Streamlit Chat UI for the Threads ReAct Agent featuring real-time event streaming of Thought, Tool Calling, and Observation, along with Human-in-the-Loop (HITL) controls for approving/rejecting write tools, answering agent text prompts, and selecting multiple choices.

**Architecture:** A decoupled generator-based event engine (`src/agent_stream.py`) yields typed events (`thought`, `tool_call`, `observation`, `ask_permission`, `ask_input`, `ask_choice`, `token`, `final_answer`) consumed in real-time by a Streamlit application (`src/streamlit_app.py`) via `st.status`, interactive widgets, and `st.write_stream`.

**Tech Stack:** Python 3.10+, Streamlit, Pytest, Python-dotenv, MCP (Model Context Protocol).

---

### Task 1: Data Structures & Core Event Streaming Generator

**Files:**
- Create: `src/agent_stream.py`
- Test: `src/test_agent_stream.py`

- [ ] **Step 1: Write failing unit test for `AgentEvent` and direct text response generator**

Create `src/test_agent_stream.py`:
```python
"""
Unit tests for agent_stream module (Event Streaming ReAct engine).
"""
import pytest
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest src/test_agent_stream.py::test_stream_direct_text_response -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.agent_stream'`

- [ ] **Step 3: Implement `AgentEvent` and basic `stream_react_agent` in `src/agent_stream.py`**

Create `src/agent_stream.py`:
```python
"""
⚡ EVENT STREAMING REACT ENGINE
Provides generator-based ReAct loop yielding real-time events for Streamlit UI.
"""
from dataclasses import dataclass, field
import json
import time
from typing import Any, Generator, Literal

from prompts import REACT_AGENT_SYSTEM_PROMPT
from app import _format_threads_observation

WRITE_TOOLS = {"threads_create_thread", "threads_reply_to_thread"}
INTERACTIVE_TOOLS = {"ask_user_input", "ask_user_choice"}

@dataclass
class AgentEvent:
    type: Literal[
        "thought",
        "tool_call",
        "ask_permission",
        "ask_input",
        "ask_choice",
        "observation",
        "token",
        "final_answer",
        "error",
    ]
    content: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    observation: dict[str, Any] = field(default_factory=dict)
    options: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    step: int = 1


def stream_tokens(text: str, delay: float = 0.015) -> Generator[AgentEvent, None, None]:
    """Split text into words/tokens and yield token events."""
    words = text.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == len(words) - 1 else word + " "
        yield AgentEvent(type="token", content=chunk)
        if delay > 0:
            time.sleep(delay)


def stream_react_agent(
    user_query: str,
    provider: Any,
    mcp_server: Any,
    max_iterations: int = 5,
    resumed_action: dict[str, Any] | None = None,
) -> Generator[AgentEvent, None, None]:
    """
    Yields real-time events for Thought -> Action -> Observation -> Final Answer.
    """
    tools_list = mcp_server.list_tools()
    step = 0

    while step < max_iterations:
        step += 1
        step_start_time = time.time()

        llm_response = provider.generate_with_tools(
            user_query, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT
        )
        latency_ms = round((time.time() - step_start_time) * 1000, 2)
        thought = llm_response.get("thought", "Đang phân tích...")

        yield AgentEvent(
            type="thought",
            content=thought,
            step=step,
            latency_ms=latency_ms,
        )

        resp_type = llm_response.get("type")

        if resp_type == "text":
            final_content = llm_response.get("content", "")
            yield AgentEvent(
                type="final_answer",
                content=final_content,
                step=step,
                latency_ms=latency_ms,
            )
            for token_event in stream_tokens(final_content, delay=0.0):
                yield token_event
            break

        elif resp_type == "tool_call":
            tool_name = llm_response.get("tool_name", "")
            arguments = llm_response.get("arguments", {})

            # Read tools auto-execute
            yield AgentEvent(
                type="tool_call",
                tool_name=tool_name,
                arguments=arguments,
                step=step,
                latency_ms=latency_ms,
            )

            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})
            obs_latency = round((time.time() - step_start_time) * 1000, 2)

            yield AgentEvent(
                type="observation",
                tool_name=tool_name,
                arguments=arguments,
                observation=obs_data,
                step=step,
                latency_ms=obs_latency,
            )

            final_answer = _format_threads_observation(tool_name, obs_data)
            yield AgentEvent(
                type="final_answer",
                content=final_answer,
                step=step + 1,
            )
            for token_event in stream_tokens(final_answer, delay=0.0):
                yield token_event
            break
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest src/test_agent_stream.py::test_stream_direct_text_response -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agent_stream.py src/test_agent_stream.py
git commit -m "feat: add AgentEvent and basic stream_react_agent generator"
```

---

### Task 2: Read vs Write Tool Permission & Human-in-the-Loop Resumption

**Files:**
- Modify: `src/agent_stream.py`
- Modify: `src/test_agent_stream.py`

- [x] **Step 1: Write failing tests for read tool auto-execution and write tool permission gating**

Add to `src/test_agent_stream.py`:
```python
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


def test_stream_write_tool_requires_permission():
    """Write tools (e.g. threads_create_thread) yield ask_permission event and pause without executing."""
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

    obs_event = next(e for e in events if e.type == "observation")
    assert obs_event.observation["status"] == "SUCCESS"


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
    obs_event = next(e for e in events if e.type == "observation")
    assert obs_event.observation["status"] == "REJECTED_BY_USER"

    final_event = next(e for e in events if e.type == "final_answer")
    assert "đã hủy" in final_event.content.lower() or "từ chối" in final_event.content.lower()
```

- [x] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest src/test_agent_stream.py -k "permission or resume" -v`
Expected: FAIL (write tool permission logic not yet implemented).

- [x] **Step 3: Implement write tool permission check and resumption handling in `src/agent_stream.py`**

Update `src/agent_stream.py` to check `WRITE_TOOLS` and handle `resumed_action`:
```python
def execute_tool_and_yield_events(
    tool_name: str,
    arguments: dict[str, Any],
    mcp_server: Any,
    step: int,
) -> Generator[AgentEvent, None, None]:
    """Helper to dispatch tool, yield observation, and yield formatted final answer."""
    yield AgentEvent(
        type="tool_call",
        tool_name=tool_name,
        arguments=arguments,
        step=step,
    )
    start_time = time.time()
    mcp_result = mcp_server.call_tool(tool_name, arguments)
    obs_data = mcp_result.get("result", {})
    latency = round((time.time() - start_time) * 1000, 2)

    yield AgentEvent(
        type="observation",
        tool_name=tool_name,
        arguments=arguments,
        observation=obs_data,
        step=step,
        latency_ms=latency,
    )

    final_answer = _format_threads_observation(tool_name, obs_data)
    yield AgentEvent(
        type="final_answer",
        content=final_answer,
        step=step + 1,
    )
    for token_event in stream_tokens(final_answer, delay=0.0):
        yield token_event
```
And in `stream_react_agent`:
- If `resumed_action`:
  - If `action == "approve"`: call `execute_tool_and_yield_events(tool_name, arguments, mcp_server, step)`.
  - If `action == "reject"`: yield rejection observation `{"status": "REJECTED_BY_USER", "reason": reason}` and final answer explaining the cancellation.
- If in standard loop and `tool_name in WRITE_TOOLS`:
  - Yield `AgentEvent(type="ask_permission", tool_name=tool_name, arguments=arguments, step=step)`.
  - Return early (pause).
- Also support custom agent prompt tools `ask_user_input` and `ask_user_choice`:
  - If `tool_name == "ask_user_input"`: yield `AgentEvent(type="ask_input", content=arguments.get("prompt", ""), step=step)`.
  - If `tool_name == "ask_user_choice"`: yield `AgentEvent(type="ask_choice", content=arguments.get("prompt", ""), options=arguments.get("options", []), step=step)`.

- [x] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest src/test_agent_stream.py -v`
Expected: ALL PASS

- [x] **Step 5: Commit**

```bash
git add src/agent_stream.py src/test_agent_stream.py
git commit -m "feat: implement HITL permission gating and resumption in agent_stream"
```

---

### Task 3: Streamlit Web UI Core (`src/streamlit_app.py`)

**Files:**
- Create: `src/streamlit_app.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Ensure requirements.txt lists `streamlit`**

Verify `requirements.txt` contains `streamlit`.

- [ ] **Step 2: Implement `src/streamlit_app.py`**

Features:
1. `st.set_page_config(page_title="Threads ReAct Agent", page_icon="🤖", layout="wide")`.
2. Initialize `st.session_state`:
   - `messages`: List of message objects.
   - `pending_interaction`: None or dict for paused HITL action.
   - `provider_choice`: "Mock Offline (Free)".
3. Re-render past message history:
   - For user: `st.chat_message("user").markdown(msg["content"])`.
   - For assistant:
     - If `msg.get("events")`: render `st.expander("🔍 ReAct Reasoning Trace (Thought & Tools)")` with thought, tool calls (JSON), and observations (JSON).
     - Render `msg["content"]`.
4. Render pending HITL interactions (if any):
   - **Permission Card (`ask_permission`)**:
     - Alert banner: "⚠️ Phê duyệt thao tác ghi dữ liệu / xuất bản bài viết".
     - Tool name & Arguments JSON.
     - Form or text area to allow user editing the post text / arguments before approval.
     - Two buttons: `[ ✅ Phê duyệt & Thực thi ]` and `[ ❌ Từ chối ]`.
   - **Text Input Card (`ask_input`)**:
     - Prompt text with `st.text_input` and `[ Gửi phản hồi ]` button.
   - **Multiple Choice Card (`ask_choice`)**:
     - Prompt text with `st.radio` options and `[ Chọn ]` button.
5. Handle new user input via `st.chat_input`:
   - Append to messages and render user bubble.
   - Assistant container:
     - Open `with st.status("🧠 Đang suy luận...", expanded=True) as status:`
     - Iterate through `stream_react_agent(query, provider, mcp_server)`:
       - On `thought`: update status label, print thought.
       - On `tool_call`: update status label `🛠️ Đang gọi công cụ {tool_name}...`, show JSON.
       - On `observation`: update status label `👁️ Nhận kết quả từ {tool_name}`, show JSON.
       - On `ask_permission` / `ask_input` / `ask_choice`: store in `st.session_state.pending_interaction` and trigger rerun to display interactive card.
       - On `final_answer`: update status to complete.
       - Accumulate tokens and stream to user using `st.write_stream()`.
     - Save assistant message with events to history.

- [ ] **Step 3: Syntax and import verification**

Run: `.venv/bin/python -m py_compile src/streamlit_app.py`
Expected: Clean compilation with exit code 0.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt src/streamlit_app.py
git commit -m "feat: implement Streamlit chat UI with live status streaming and HITL cards"
```

---

### Task 4: Sidebar Controls, Provider Switching & Waterfall Trace Export

**Files:**
- Modify: `src/streamlit_app.py`

- [ ] **Step 1: Implement full sidebar in `src/streamlit_app.py`**
- Provider Selection: Radio button `["Mock Offline (Free)", "Google Gemini", "OpenAI"]`.
- API Key Status / Input:
  - If Gemini: Check `os.getenv("GEMINI_API_KEY")`; show status badge (Configured / Missing) and provide optional text input to enter key.
  - If OpenAI: Check `os.getenv("OPENAI_API_KEY")`; show status badge and provide optional text input.
- Quick Test Cases:
  - Load test cases from `config/test_cases.json` or `config/test_cases.example.json`.
  - Display buttons / selectbox for TC01 (Tư vấn hook), TC02 (Chỉ số insights), TC03 (Xuất bản bài đăng - triggers HITL), TC04 (Bài tương tác cao nhất), TC05 (Kiểm tra bài không tồn tại - edge case).
  - Clicking a case automatically submits it as a query.
- Action Buttons:
  - `🗑️ Xóa lịch sử hội thoại`: Clears `st.session_state.messages` and `st.session_state.pending_interaction`.
  - `📥 Tải file Trace Waterfall (JSON)`: Download button for `st.session_state.waterfall_traces`.

- [ ] **Step 2: Verify Python compilation**

Run: `.venv/bin/python -m py_compile src/streamlit_app.py`
Expected: Exit code 0.

- [ ] **Step 3: Commit**

```bash
git add src/streamlit_app.py
git commit -m "feat: add sidebar controls, provider switching, and trace export to streamlit app"
```

---

### Task 5: End-to-End Verification & Documentation

**Files:**
- Test: All tests via `pytest`
- Update: `README.md` (Add quickstart section for running Streamlit UI)

- [ ] **Step 1: Run full test suite**

Run: `.venv/bin/pytest -v`
Expected: All tests pass (including existing `test_app.py`, `test_tools.py`, `test_providers.py`, and new `test_agent_stream.py`).

- [ ] **Step 2: Update `README.md` with Streamlit running instructions**

Add a clear section in `README.md`:
```bash
# Chạy giao diện Web Chat UI Streamlit (Hỗ trợ Live Streaming & Human-in-the-Loop):
streamlit run src/streamlit_app.py
```

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -m "docs: add Streamlit Chat UI instructions to README"
```
