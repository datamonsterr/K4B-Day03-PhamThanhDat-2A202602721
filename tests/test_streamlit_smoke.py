"""
Smoke tests for Streamlit Web UI, configuration, launcher, and event streaming.
"""
import os
import py_compile
import subprocess
import sys
import tomllib
from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest

from src.streamlit_app import (
    check_backend_health,
    get_backend_url,
    stream_backend_events,
    stream_events,
    stream_local_events,
)


def test_streamlit_compilation():
    """Verify that src/streamlit_app.py compiles without syntax errors."""
    app_path = os.path.abspath("src/streamlit_app.py")
    compiled = py_compile.compile(app_path)
    assert compiled is not None


def test_streamlit_config_toml():
    """Verify .streamlit/config.toml exists and contains required server configurations."""
    config_path = os.path.abspath(".streamlit/config.toml")
    assert os.path.exists(config_path), ".streamlit/config.toml must exist"

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    assert "server" in config
    server_cfg = config["server"]
    assert server_cfg.get("headless") is True
    assert server_cfg.get("port") == 8501
    assert server_cfg.get("enableCORS") is False
    assert server_cfg.get("enableXsrfProtection") is False


def test_run_ui_launcher_help():
    """Verify that run_ui.py --help executes cleanly with code 0."""
    result = subprocess.run(
        [sys.executable, "run_ui.py", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Usage: python run_ui.py" in result.stdout
    assert "STREAMLIT_PORT" in result.stdout


def test_get_backend_url_defaults_and_env():
    """Verify get_backend_url resolves correctly from env variables."""
    with patch.dict(os.environ, {"BACKEND_URL": "http://mycustomhost:9999"}, clear=False):
        assert get_backend_url() == "http://mycustomhost:9999"

    with patch.dict(os.environ, {"BACKEND_HOST": "api.test", "BACKEND_PORT": "8888"}, clear=False):
        if "BACKEND_URL" in os.environ:
            del os.environ["BACKEND_URL"]
        assert get_backend_url() == "http://api.test:8888"


def test_check_backend_health():
    """Verify check_backend_health handles 200, 500, and connection errors."""
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        assert check_backend_health("http://localhost:8000") is True

        mock_resp.status_code = 500
        assert check_backend_health("http://localhost:8000") is False

        mock_get.side_effect = Exception("Connection refused")
        assert check_backend_health("http://localhost:8000") is False


def test_stream_local_events_mock():
    """Verify stream_local_events yields thought, final_answer, and tokens."""
    events = list(stream_local_events("Kỹ thuật viết hook 3 dòng đầu", "mock"))
    event_types = [e.get("type") for e in events]

    assert "thought" in event_types
    assert "final_answer" in event_types
    assert "token" in event_types


def test_stream_backend_events_sse():
    """Verify stream_backend_events parses SSE lines into event dicts."""
    sse_data = (
        b'data: {"type": "thought", "content": "Thinking..."}\n\n'
        b'data: {"type": "final_answer", "content": "Done!"}\n\n'
        b'data: {"type": "done"}\n\n'
    )
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = [
        'data: {"type": "thought", "content": "Thinking..."}',
        "",
        'data: {"type": "final_answer", "content": "Done!"}',
        "",
        'data: {"type": "done"}',
    ]

    with patch("requests.post", return_value=mock_resp):
        events = list(stream_backend_events("http://localhost:8000", "test query", "mock"))
        assert len(events) == 2
        assert events[0]["type"] == "thought"
        assert events[1]["type"] == "final_answer"


def test_stream_events_with_backend_success():
    """Verify stream_events streams events from backend when use_backend is True."""
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = [
        'data: {"type": "thought", "content": "Backend thinking"}',
        'data: {"type": "final_answer", "content": "Backend response"}',
        'data: {"type": "done"}',
    ]
    with patch("requests.post", return_value=mock_resp):
        events = list(stream_events("Test query", "mock", use_backend=True, backend_url="http://localhost:8000"))
        assert len(events) == 2
        assert events[0]["type"] == "thought"
        assert events[0]["content"] == "Backend thinking"
        assert events[1]["type"] == "final_answer"
        assert events[1]["content"] == "Backend response"


def test_stream_events_fallback_to_local_on_backend_error():
    """Verify stream_events falls back to local execution if backend fails."""
    with patch("requests.post", side_effect=Exception("Backend down")):
        events = list(stream_events("Chào bạn", "mock", use_backend=True, backend_url="http://fake:9999"))
        event_types = [e.get("type") for e in events]
        # Should have fallback warning thought followed by local events
        assert "thought" in event_types
        assert "final_answer" in event_types


def test_streamlit_apptest_mount_and_widgets():
    """Verify Streamlit app mounts, initializes session state, and renders key sidebar widgets."""
    app_path = os.path.abspath("src/streamlit_app.py")
    at = AppTest.from_file(app_path)
    at.run()

    assert not at.exception
    assert at.session_state["messages"] == []
    assert at.session_state["pending_interaction"] is None
    assert at.session_state["waterfall_traces"] == []

    # Sidebar contains provider selectbox
    assert len(at.sidebar.selectbox) >= 1
    # Sidebar contains test case buttons and actions
    assert len(at.sidebar.button) >= 5


def test_streamlit_apptest_hitl_permission_card():
    """Verify that when pending_interaction has type 'permission', warning and buttons render."""
    app_path = os.path.abspath("src/streamlit_app.py")
    at = AppTest.from_file(app_path)
    at.run()

    at.session_state["pending_interaction"] = {
        "type": "permission",
        "tool_name": "threads_create_thread",
        "arguments": {"text": "Test Draft", "reply_control": "everyone"},
        "query": "Đăng bài mới",
        "step": 1,
    }
    at.run()

    assert not at.exception
    # Should have warning message
    assert len(at.warning) >= 1
    assert "Yêu cầu phê duyệt" in at.warning[0].value

    # Should have approve and reject buttons
    button_labels = [b.label for b in at.button]
    assert any("Phê duyệt" in label for label in button_labels)
    assert any("Từ chối" in label for label in button_labels)


def test_streamlit_apptest_hitl_input_card():
    """Verify that when pending_interaction has type 'ask_input', prompt and input render."""
    app_path = os.path.abspath("src/streamlit_app.py")
    at = AppTest.from_file(app_path)
    at.run()

    at.session_state["pending_interaction"] = {
        "type": "ask_input",
        "prompt": "Nhập hashtag của bạn:",
        "tool_name": "ask_user_input",
        "query": "Đăng bài",
        "step": 1,
    }
    at.run()

    assert not at.exception
    assert len(at.info) >= 1
    assert "hashtag" in at.info[0].value
    assert len(at.text_input) >= 1


def test_streamlit_apptest_hitl_choice_card():
    """Verify that when pending_interaction has type 'ask_choice', radio options render."""
    app_path = os.path.abspath("src/streamlit_app.py")
    at = AppTest.from_file(app_path)
    at.run()

    at.session_state["pending_interaction"] = {
        "type": "ask_choice",
        "prompt": "Chọn đối tượng:",
        "options": ["Mọi người", "Người theo dõi"],
        "tool_name": "ask_user_choice",
        "query": "Đăng bài",
        "step": 1,
    }
    at.run()

    assert not at.exception
    assert len(at.radio) >= 1
    assert at.radio[0].options == ["Mọi người", "Người theo dõi"]
