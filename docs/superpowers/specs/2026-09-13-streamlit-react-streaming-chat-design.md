# Design Spec: Streamlit ReAct Agent Chat UI with Event Streaming & Human-in-the-Loop (HITL)

- **Date:** 2026-09-13
- **Status:** Approved
- **Topic:** Streamlit Chat UI for ReAct Agent with Explicit Streaming (Thought, Tool Calling, Observation) and Interactive Human-in-the-Loop (Approve/Reject for Write Tools, User Text Input, and Multiple Choices)

---

## 1. Overview & Objectives

This specification defines an interactive Streamlit Chat application exposing the ReAct Agent (`Thought -> Action -> Observation -> Final Answer`) with:
1. **Explicit Real-Time Streaming**:
   - **Thinking (`Thought`)**: Clearly exposed in real-time as the agent deliberates.
   - **Tool Calling (`Action`)**: Displays tool names and input parameters in formatted JSON.
   - **Observation (`Observation`)**: Renders tool execution outputs and metrics received from the MCP Server.
   - **Token-Level Streaming (`Final Answer`)**: Emits the final conversational response token-by-token using Streamlit's `st.write_stream`.
2. **Human-in-the-Loop (HITL) Interactivity**:
   - **Read vs. Write Tool Permission Control**:
     - *Read Tools* (`threads_get_insights`, `threads_get_thread`, `threads_get_threads`, `threads_get_profile`, `threads_search`, `threads_get_replies`, `threads_get_conversation`): Executed automatically without blocking.
     - *Write Tools* (`threads_create_thread`, `threads_reply_to_thread`): Pause agent execution and display an interactive permission card with `[ Approve & Execute ]` and `[ Reject ]` buttons (with optional argument tweaks/syntax check).
   - **Interactive User Text Input**: Agent can request clarification, custom formatting verification, or missing parameters from the user.
   - **Interactive Multiple Choices**: Agent can present selectable options (radio buttons / pills) for the user to choose from.

The application integrates with the existing project codebase:
- `src/mcp_server.py`: Model Context Protocol server exposing Threads tools.
- `src/providers.py`: Multi-provider LLM support (`MockOfflineProvider`, `GeminiProvider`, `OpenAIProvider`, `OpenRouterProvider`).
- `config/test_cases.json`: Test prompts for rapid verification and demo scenarios.

---

## 2. Architecture & Components

```
+---------------------------------------------------------------------------------+
|                               Streamlit Chat UI                                 |
|                             (src/streamlit_app.py)                              |
|                                                                                 |
|  +--------------------+   +--------------------------------------------------+  |
|  |      Sidebar       |   |               Chat Message Area                  |  |
|  |  - Provider pick   |   |  - User bubble                                   |  |
|  |  - API Key status  |   |  - Assistant bubble:                             |  |
|  |  - HITL Toggle     |   |    * st.status (Live ReAct Trace)                |  |
|  |  - Quick prompts   |   |      - 🧠 Thought                                |  |
|  |  - Clear & Export  |   |      - 🛠️ Action (Tool + Args)                   |  |
|  +--------------------+   |      - 👁️ Observation (MCP Result)               |  |
|                           |    * HITL Interactive Cards (if pending):        |  |
|                           |      - ⚠️ Approve/Reject Write Tools             |  |
|                           |      - ✏️ User Text Input Prompt                 |  |
|                           |      - 🔘 Multiple Choice Selector               |  |
|                           |    * st.write_stream (Token-by-token text)       |  |
|                           +--------------------------------------------------+  |
+----------------------------------------|----------------------------------------+
                                         | Events (yield / resume)
                                         v
+---------------------------------------------------------------------------------+
|                   Event Streaming Engine (src/agent_stream.py)                  |
|                                                                                 |
|  stream_react_agent(query, provider, mcp_server, interaction_response=None)     |
|    - step 1..MAX_ITERATIONS                                                     |
|    - yield AgentEvent("thought", ...)                                           |
|    - If tool in WRITE_TOOLS and not yet approved:                               |
|        yield AgentEvent("ask_permission", tool_name, args) -> PAUSE             |
|    - If tool is interactive user query (ask_input / ask_choice):                |
|        yield AgentEvent("ask_input" | "ask_choice", ...) -> PAUSE               |
|    - MCP execution -> yield AgentEvent("observation", ...)                      |
|    - yield AgentEvent("final_answer", ...)                                      |
|    - yield AgentEvent("token", ...)                                             |
+-------------------|--------------------------------------|----------------------+
                    |                                      |
                    v                                      v
+--------------------------------------+   +--------------------------------------+
|           MCPThreadsServer           |   |           BaseLLMProvider            |
|         (src/mcp_server.py)          |   |          (src/providers.py)          |
|  - list_tools()                      |   |  - MockOfflineProvider               |
|  - call_tool(name, args)             |   |  - Gemini / OpenAI Providers         |
+--------------------------------------+   +--------------------------------------+
```

---

## 3. Data Structures & Event Model

### 3.1. `AgentEvent`
```python
from dataclasses import dataclass
from typing import Any, Literal

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
    arguments: dict[str, Any] | None = None
    observation: dict[str, Any] | None = None
    options: list[str] | None = None
    latency_ms: float = 0.0
    step: int = 1
```

### 3.2. Session State Schema (`st.session_state`)
- `messages`: List of completed messages `[{"role": "user"|"assistant", "content": str, "events": list[dict], "timestamp": float}]`.
- `pending_interaction`: Dict containing active HITL state if paused:
  ```python
  {
      "type": "permission" | "text_input" | "choice",
      "tool_name": str,
      "arguments": dict,
      "prompt": str,
      "options": list[str],
      "step": int,
  }
  ```
- `provider_name`: Selected LLM provider (`"Mock Offline"`, `"Google Gemini"`, `"OpenAI"`).
- `waterfall_traces`: Cumulative list of all trace events for export to `docs/trace_waterfall.json`.

---

## 4. UI Specification & Human-in-the-Loop Flows

### 4.1. Automatic Read Tools vs. Write Tool Approvals
- **Read Tools**: `threads_get_insights`, `threads_get_thread`, `threads_get_threads`, `threads_get_profile`, `threads_search`, `threads_get_replies`, `threads_get_conversation`.
  - Executed immediately, emitting `tool_call` and `observation` inside the live `st.status`.
- **Write Tools**: `threads_create_thread`, `threads_reply_to_thread`.
  - Emits `ask_permission`.
  - The UI renders an alert container:
    - ⚠️ **Action Confirmation Required**: Explaining that the agent wants to perform an external write action.
    - JSON viewer and editor for arguments (`text`, `reply_control`).
    - Two action buttons:
      - `[ ✅ Approve & Execute ]`: Invokes tool with the (optionally edited) arguments and resumes agent.
      - `[ ❌ Reject ]`: Sends `{"status": "REJECTED_BY_USER", "reason": "User rejected write action"}` as observation to the agent, allowing LLM to adapt and acknowledge.

### 4.2. Interactive User Input & Choices
- **User Text Input (`ask_input`)**: Renders an `st.text_input` or `st.text_area` with a `Submit` button. When submitted, the input is passed back into the agent loop.
- **Multiple Choices (`ask_choice`)**: Renders `st.radio` or button pills for selectable options. When selected, the choice is forwarded as the response.

### 4.3. Streaming Display (`st.status` + `st.write_stream`)
- Live thinking, tool calling, and observation steps are rendered into `st.status("🧠 Agent Reasoning...", expanded=True)`.
- When reasoning concludes, `st.status` completes and collapses (`state="complete", expanded=False`).
- Final response is streamed token-by-token using `st.write_stream`.
- Historical messages persist in `st.session_state.messages` and render reasoning traces inside collapsible `st.expander` elements.

### 4.4. Sidebar Capabilities
- **Provider Switching**: Toggle between `Mock Offline Provider`, `Google Gemini`, and `OpenAI`.
- **API Key Configuration**: Visual status indicator and custom key input override.
- **Pre-set Test Cases**: Quick launch buttons for TC01-TC05 from `config/test_cases.json`.
- **Session Reset**: `Clear Chat` button.
- **Export Trace**: Button to download `docs/trace_waterfall.json`.

---

## 5. Testing & Verification Plan

1. **Unit Tests (`src/test_agent_stream.py`)**:
   - `test_stream_read_tool_auto_executes`: Confirms read tools execute without pausing.
   - `test_stream_write_tool_requires_permission`: Confirms write tools yield `ask_permission` and pause.
   - `test_stream_resume_after_approval`: Confirms agent resumes and calls tool when approved.
   - `test_stream_resume_after_rejection`: Confirms agent handles rejection gracefully.
   - `test_stream_ask_input_and_choice`: Confirms `ask_input` and `ask_choice` yield interaction events and handle responses.
2. **Regression Testing**:
   - `pytest` across all existing suites (`test_app.py`, `test_tools.py`, `test_providers.py`).
3. **Application Compilation & Smoke Test**:
   - Verify `src/streamlit_app.py` compiles without syntax or import errors.
