# Design Spec: Streamlit ReAct Agent Chat UI with Event Streaming

- **Date:** 2026-09-13
- **Status:** Approved
- **Topic:** Streamlit Chat UI for ReAct Agent with Explicit Streaming of Thought, Action (Tool Calling), and Observation

---

## 1. Overview & Objectives

This specification defines the architecture and implementation for an interactive web-based Chat UI using Streamlit. The application exposes the ReAct Agent (`Thought -> Action -> Observation -> Final Answer`) with explicit real-time streaming:
- **Explicit Thinking (`Thought`)**: Clearly exposed in real-time as the agent deliberates.
- **Explicit Tool Calling (`Action`)**: Displays tool names and input parameters in formatted JSON.
- **Explicit Observation (`Observation`)**: Renders tool execution outputs and metrics received from the MCP Server.
- **Token-Level Streaming (`Final Answer`)**: Emits the final conversational response token-by-token using Streamlit's `st.write_stream`.

The UI integrates seamlessly with the existing project codebase:
- `src/mcp_server.py`: Model Context Protocol server exposing Threads tools (`threads_get_insights`, `threads_create_thread`, `threads_search`, `threads_get_threads`, etc.).
- `src/providers.py`: Multi-provider LLM support (`MockOfflineProvider`, `GeminiProvider`, `OpenAIProvider`, `OpenRouterProvider`).
- `config/test_cases.json`: Test prompts used for quick testing and demonstrations.

---

## 2. Architecture & Components

```
+-------------------------------------------------------------+
|                      Streamlit Chat UI                      |
|                    (src/streamlit_app.py)                   |
|                                                             |
|  +-------------------+   +-------------------------------+  |
|  |      Sidebar      |   |        Chat Message Area      |  |
|  |  - Provider pick  |   |  - User bubble                |  |
|  |  - API Key status |   |  - Assistant bubble:          |  |
|  |  - Quick prompts  |   |    * st.status (Live ReAct)   |  |
|  |  - Clear & Export |   |      - Thought                |  |
|  +-------------------+   |      - Action (Tool + Args)   |  |
|                          |      - Observation (Result)   |  |
|                          |    * st.write_stream (Tokens) |  |
|                          +-------------------------------+  |
+------------------------------|------------------------------+
                               | Events (yield)
                               v
+-------------------------------------------------------------+
|            Event Streaming Engine (src/agent_stream.py)     |
|                                                             |
|  stream_react_agent(query, provider, mcp_server)            |
|    - step 1..MAX_ITERATIONS                                 |
|    - yield AgentEvent("thought", ...)                       |
|    - yield AgentEvent("tool_call", ...)                     |
|    - yield AgentEvent("observation", ...)                   |
|    - yield AgentEvent("final_answer", ...)                  |
|    - yield AgentEvent("token", ...)                         |
+-----------------|---------------------------|---------------+
                  |                           |
                  v                           v
+----------------------------------+  +-----------------------+
|          MCPThreadsServer        |  |    BaseLLMProvider    |
|       (src/mcp_server.py)        |  |   (src/providers.py)  |
|  - list_tools()                  |  |  - MockOffline        |
|  - call_tool(name, args)         |  |  - Gemini / OpenAI    |
+----------------------------------+  +-----------------------+
```

---

## 3. Data Structures

### `AgentEvent`
```python
from dataclasses import dataclass
from typing import Any, Literal

@dataclass
class AgentEvent:
    type: Literal["thought", "tool_call", "observation", "token", "final_answer", "error"]
    content: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] | None = None
    observation: dict[str, Any] | None = None
    latency_ms: float = 0.0
    step: int = 1
```

### Chat History in `st.session_state.messages`
```python
{
    "role": "user" | "assistant",
    "content": str,          # Final textual response
    "events": list[dict],    # Detailed reasoning events (thought, tool_call, observation)
    "timestamp": float,
}
```

---

## 4. UI Specification

### 4.1. Live Execution in Current Turn
When the user submits a message:
1. Display the user query immediately via `st.chat_message("user")`.
2. Inside `st.chat_message("assistant")`:
   - Open a dynamic `st.status("🧠 Agent Reasoning...", expanded=True) as status`.
   - Iterate over `stream_react_agent(prompt, provider, mcp_server)`:
     - On `type == "thought"`: Update status label to `"🧠 Thinking..."`; write thought in markdown.
     - On `type == "tool_call"`: Update status label to `f"🛠️ Executing {tool_name}..."`; display tool name and arguments with `st.json(arguments)`.
     - On `type == "observation"`: Update status label to `f"👁️ Observed output from {tool_name}"`; display observation results with `st.json(observation)`.
     - On `type == "final_answer"`: Complete status `status.update(label="✅ Reasoning complete", state="complete", expanded=False)`.
     - Collect tokens and stream with `st.write_stream()`.
3. Persist the turn into `st.session_state.messages`.

### 4.2. Historical Turn Re-rendering
- On Streamlit rerun, previous assistant messages render:
  - An `st.expander("🔍 Reasoning Trace (Thought & Tools)", expanded=False)` containing thoughts, actions, and observations.
  - The final answer text below the expander.

### 4.3. Sidebar Features
- **Provider Selector**: Select between `Mock Offline (Free)`, `Google Gemini`, and `OpenAI`.
- **API Key Configuration**: View whether the environment variable is loaded; provide an optional override input field.
- **Predefined Test Queries**: Dropdown or buttons populated from `config/test_cases.json` (or `test_cases.example.json`) to quickly trigger TC01-TC05.
- **Session Controls**:
  - `Clear Chat`: Resets `st.session_state.messages`.
  - `Export Trace Waterfall JSON`: Downloads the session's ReAct traces matching `docs/trace_waterfall.json` schema.

---

## 5. Testing & Verification

1. **Unit Tests (`src/test_agent_stream.py`)**:
   - `test_stream_direct_text_response`: Verifies generator yields thought, final_answer, and token events for direct text answers without calling tools.
   - `test_stream_tool_execution`: Verifies full sequence (`thought` -> `tool_call` -> `observation` -> `final_answer` -> `token`) for queries requiring tools.
   - `test_stream_tool_error_handling`: Verifies edge cases (e.g. non-existent IDs yielding `NOT_FOUND`) are handled gracefully and yielded as observations.
2. **Regression Tests**:
   - Run `pytest` to guarantee `src/test_app.py`, `src/test_providers.py`, and `src/test_tools.py` all continue passing.
3. **Smoke Test**:
   - Verify `src/streamlit_app.py` compiles without syntax errors and runs cleanly.
