"""
Unit tests for prompts module (System instructions, Streamlit UI approval block syntax, and helper utilities).
"""

from src.prompts import (
    APPROVAL_BLOCK_END,
    APPROVAL_BLOCK_START,
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    format_action_approval_request,
    is_approval_response,
    is_rejection_response,
    parse_action_approval_request,
)


def test_react_agent_system_prompt_contains_approval_policy():
    """REACT_AGENT_SYSTEM_PROMPT must mandate user approval for write actions with Approve/Reject syntax."""
    prompt = REACT_AGENT_SYSTEM_PROMPT
    assert "threads_create_thread" in prompt
    assert "threads_reply_to_thread" in prompt
    assert "[ACTION_APPROVAL_REQUEST]" in prompt
    assert "[APPROVE]" in prompt
    assert "[REJECT]" in prompt
    assert "Streamlit" in prompt or "UI" in prompt


def test_react_agent_system_prompt_allows_read_and_search_freely():
    """REACT_AGENT_SYSTEM_PROMPT must explicitly allow read and search tools freely."""
    prompt = REACT_AGENT_SYSTEM_PROMPT
    assert "threads_search" in prompt
    assert "threads_get_profile" in prompt
    assert "threads_get_threads" in prompt
    assert "threads_get_insights" in prompt
    assert "tự do" in prompt.lower() or "freely" in prompt.lower()


def test_react_agent_system_prompt_instructs_use_cases():
    """Prompt must cover content research, trend research, celebrities/KOLs, trend analysis, and topic suggestion."""
    prompt = REACT_AGENT_SYSTEM_PROMPT.lower()
    # Content research & trends
    assert "nghiên cứu nội dung" in prompt or "content research" in prompt
    assert "nghiên cứu xu hướng" in prompt or "trend research" in prompt
    assert "top_views" in prompt
    assert "recent" in prompt
    # Celebrities / Key voices
    assert "nhân vật" in prompt or "celebrities" in prompt or "kol" in prompt
    # Trend analysis & topic suggestion
    assert "chủ đề" in prompt or "topic" in prompt


def test_react_agent_system_prompt_clarification_requirements():
    """Prompt must require clarifying topic, format (long/short), vibe/tone, and language (VN or en)."""
    prompt = REACT_AGENT_SYSTEM_PROMPT.lower()
    assert "chủ đề" in prompt or "topic" in prompt
    assert "định dạng" in prompt or "format" in prompt or "ngắn" in prompt or "dài" in prompt
    assert "vibe" in prompt or "tone" in prompt or "phong cách" in prompt
    assert "tiếng việt" in prompt or "tiếng anh" in prompt or "vn" in prompt or "en" in prompt


def test_format_action_approval_request():
    """format_action_approval_request builds a valid Streamlit-parsable markdown block."""
    block = format_action_approval_request(
        action="threads_create_thread",
        content="Hello Threads from ReAct Agent!",
        reply_control="everyone",
    )
    assert block.startswith(APPROVAL_BLOCK_START)
    assert block.endswith(APPROVAL_BLOCK_END)
    assert "Action: threads_create_thread" in block
    assert "Hello Threads from ReAct Agent!" in block
    assert "[APPROVE] [REJECT]" in block


def test_parse_action_approval_request():
    """parse_action_approval_request extracts structured approval parameters from text."""
    sample_text = """
    Tôi đã soạn xong nội dung bài viết theo yêu cầu của bạn:

    [ACTION_APPROVAL_REQUEST]
    Action: threads_create_thread
    Target_ID: None
    Reply_Control: everyone
    Content: \"\"\"
    ReAct Agent kết hợp MCP Protocol sẽ thay đổi hoàn toàn cách chúng ta tương tác với mạng xã hội! #VinUniAI
    \"\"\"
    Status: PENDING_APPROVAL
    [APPROVE] [REJECT]
    [/ACTION_APPROVAL_REQUEST]

    Vui lòng kiểm tra và bấm [Approve] hoặc [Reject].
    """
    parsed = parse_action_approval_request(sample_text)
    assert parsed is not None
    assert parsed["action"] == "threads_create_thread"
    assert parsed["target_id"] is None or parsed["target_id"] == "None"
    assert parsed["reply_control"] == "everyone"
    assert "ReAct Agent kết hợp MCP Protocol" in parsed["content"]
    assert parsed["status"] == "PENDING_APPROVAL"


def test_parse_action_approval_request_reply():
    """parse_action_approval_request extracts reply action with Target_ID."""
    sample_text = """
    [ACTION_APPROVAL_REQUEST]
    Action: threads_reply_to_thread
    Target_ID: 18069523004746345
    Reply_Control: everyone
    Content: \"\"\"
    Cảm ơn bạn đã quan tâm đến dự án VinUni AI!
    \"\"\"
    Status: PENDING_APPROVAL
    [APPROVE] [REJECT]
    [/ACTION_APPROVAL_REQUEST]
    """
    parsed = parse_action_approval_request(sample_text)
    assert parsed is not None
    assert parsed["action"] == "threads_reply_to_thread"
    assert parsed["target_id"] == "18069523004746345"
    assert "Cảm ơn bạn đã quan tâm" in parsed["content"]


def test_is_approval_and_rejection_response():
    """is_approval_response and is_rejection_response correctly classify user intent."""
    assert is_approval_response("[APPROVE]")
    assert is_approval_response("Approve")
    assert is_approval_response("approve this post")
    assert is_approval_response("Đồng ý đăng bài")
    assert is_approval_response("Duyệt")
    assert not is_approval_response("Không, hãy sửa lại nội dung")

    assert is_rejection_response("[REJECT]")
    assert is_rejection_response("Reject")
    assert is_rejection_response("Từ chối")
    assert is_rejection_response("Hủy bỏ")
    assert not is_rejection_response("Tuyệt vời, duyệt nhé")
