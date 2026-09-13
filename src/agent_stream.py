"""
⚡ EVENT STREAMING REACT ENGINE
Provides generator-based ReAct loop yielding real-time events for Streamlit UI.
"""
from dataclasses import dataclass, field
import os
import sys
import time
from typing import Any, Generator, Literal

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from src.prompts import REACT_AGENT_SYSTEM_PROMPT
    from src.app import _format_threads_observation
except ModuleNotFoundError:
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

    tool_start = time.time()
    mcp_result = mcp_server.call_tool(tool_name, arguments)
    obs_data = mcp_result.get("result", {})
    obs_latency = round((time.time() - tool_start) * 1000, 2)

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


def stream_react_agent(
    user_query: str,
    provider: Any,
    mcp_server: Any,
    max_iterations: int = 5,
    resumed_action: dict[str, Any] | None = None,
) -> Generator[AgentEvent, None, None]:
    """
    Yields real-time events for Thought -> Action -> Observation -> Final Answer.
    Supports Human-in-the-Loop permission gating and resumption.
    """
    if resumed_action:
        action = resumed_action.get("action")
        tool_name = resumed_action.get("tool_name", "")
        arguments = resumed_action.get("arguments", {})
        step = resumed_action.get("step", 1)

        if action == "approve":
            yield from execute_tool_and_yield_events(tool_name, arguments, mcp_server, step)
            return

        elif action == "reject":
            reason = resumed_action.get("reason", "Thao tác đã bị người dùng từ chối.")
            yield AgentEvent(
                type="observation",
                tool_name=tool_name,
                arguments=arguments,
                observation={"status": "REJECTED_BY_USER", "reason": reason},
                step=step,
            )
            final_content = f"Người dùng đã từ chối thao tác '{tool_name}'. Đã hủy thực thi. Lý do: {reason}"
            yield AgentEvent(
                type="final_answer",
                content=final_content,
                step=step + 1,
            )
            for token_event in stream_tokens(final_content, delay=0.0):
                yield token_event
            return

        elif action in ("submit_input", "submit_choice"):
            user_response = (
                resumed_action.get("response")
                if resumed_action.get("response") is not None
                else (
                    resumed_action.get("value")
                    if resumed_action.get("value") is not None
                    else (
                        resumed_action.get("input")
                        if resumed_action.get("input") is not None
                        else resumed_action.get("choice", "")
                    )
                )
            )
            obs_data = {"status": "USER_RESPONSE", "response": user_response}
            yield AgentEvent(
                type="observation",
                tool_name=tool_name,
                arguments=arguments,
                observation=obs_data,
                step=step,
            )
            final_content = f"Đã ghi nhận phản hồi từ người dùng: {user_response}"
            yield AgentEvent(
                type="final_answer",
                content=final_content,
                step=step + 1,
            )
            for token_event in stream_tokens(final_content, delay=0.0):
                yield token_event
            return

        else:
            yield AgentEvent(
                type="error",
                content=f"Unrecognized resumed action: {action}",
                step=step,
            )
            return

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

            if tool_name in WRITE_TOOLS:
                yield AgentEvent(
                    type="ask_permission",
                    tool_name=tool_name,
                    arguments=arguments,
                    step=step,
                    latency_ms=latency_ms,
                )
                return

            elif tool_name in INTERACTIVE_TOOLS:
                if tool_name == "ask_user_input":
                    yield AgentEvent(
                        type="ask_input",
                        content=arguments.get("prompt", ""),
                        tool_name=tool_name,
                        arguments=arguments,
                        step=step,
                    )
                elif tool_name == "ask_user_choice":
                    yield AgentEvent(
                        type="ask_choice",
                        content=arguments.get("prompt", ""),
                        options=arguments.get("options", []),
                        tool_name=tool_name,
                        arguments=arguments,
                        step=step,
                    )
                return

            else:
                yield from execute_tool_and_yield_events(tool_name, arguments, mcp_server, step)
                break

        else:
            yield AgentEvent(
                type="error",
                content=f"Unrecognized response type: {resp_type}",
                step=step,
            )
            break

