"""
Unit tests for tools module (Threads MCP Tools implementation).
"""

import json
import pytest

from src.tools import TOOLS_SCHEMA, dispatch_tool_call


def test_tools_schema_contains_threads_tools():
    """TOOLS_SCHEMA must declare official quinnjr/threads-mcp tools."""
    tool_names = [tool["name"] for tool in TOOLS_SCHEMA]
    expected_tools = [
        "threads_get_profile",
        "threads_get_threads",
        "threads_get_thread",
        "threads_create_thread",
        "threads_reply_to_thread",
        "threads_get_insights",
        "threads_get_replies",
        "threads_get_conversation",
        "threads_search",
    ]
    for expected in expected_tools:
        assert expected in tool_names, f"Tool '{expected}' is missing from TOOLS_SCHEMA"

    for tool in TOOLS_SCHEMA:
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool
        assert tool["parameters"].get("type") == "object"


def test_threads_get_profile_success():
    """threads_get_profile returns account profile."""
    raw = dispatch_tool_call("threads_get_profile", {})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert "data" in result
    profile = result["data"]
    assert "username" in profile
    assert "followers_count" in profile


def test_threads_get_threads_success():
    """threads_get_threads returns list of threads."""
    raw = dispatch_tool_call("threads_get_threads", {})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert "data" in result
    assert isinstance(result["data"], list)
    assert len(result["data"]) > 0


def test_threads_get_thread_success():
    """threads_get_thread returns details of an existing thread."""
    raw = dispatch_tool_call("threads_get_thread", {"thread_id": "th_post_001"})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert result["thread_id"] == "th_post_001"
    assert "text" in result["data"]


def test_threads_get_thread_not_found():
    """threads_get_thread returns NOT_FOUND when thread does not exist."""
    raw = dispatch_tool_call("threads_get_thread", {"thread_id": "th_nonexistent_999"})
    result = json.loads(raw)
    assert result["status"] == "NOT_FOUND"
    assert "not found" in result["message"].lower()


def test_threads_create_thread_success():
    """threads_create_thread adds a new thread post."""
    text = "Exploring AI agents with Model Context Protocol! 🚀"
    raw = dispatch_tool_call("threads_create_thread", {"text": text})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert "id" in result
    assert result["text"] == text
    assert "permalink" in result


def test_threads_reply_to_thread_success():
    """threads_reply_to_thread adds a reply to an existing thread."""
    raw = dispatch_tool_call(
        "threads_reply_to_thread",
        {"thread_id": "th_post_001", "text": "Great insights on AI Agents!"},
    )
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert result["thread_id"] == "th_post_001"
    assert "id" in result


def test_threads_reply_to_thread_not_found():
    """threads_reply_to_thread returns NOT_FOUND when target thread does not exist."""
    raw = dispatch_tool_call(
        "threads_reply_to_thread",
        {"thread_id": "th_nonexistent_999", "text": "Invalid reply"},
    )
    result = json.loads(raw)
    assert result["status"] == "NOT_FOUND"


def test_threads_get_insights_success():
    """threads_get_insights returns performance metrics for a thread."""
    raw = dispatch_tool_call("threads_get_insights", {"thread_id": "th_post_001"})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert result["thread_id"] == "th_post_001"
    assert "metrics" in result
    metrics = result["metrics"]
    for metric_name in ["views", "likes", "replies", "reposts"]:
        assert metric_name in metrics


def test_threads_get_insights_not_found():
    """threads_get_insights returns NOT_FOUND for an unknown thread_id."""
    raw = dispatch_tool_call("threads_get_insights", {"thread_id": "th_nonexistent_999"})
    result = json.loads(raw)
    assert result["status"] == "NOT_FOUND"


def test_threads_get_replies_success():
    """threads_get_replies returns replies for a thread."""
    raw = dispatch_tool_call("threads_get_replies", {"thread_id": "th_post_001"})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert result["thread_id"] == "th_post_001"
    assert isinstance(result["data"], list)


def test_threads_get_conversation_success():
    """threads_get_conversation returns thread and its replies."""
    raw = dispatch_tool_call("threads_get_conversation", {"thread_id": "th_post_001"})
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert "thread" in result
    assert "replies" in result


def test_dispatch_tool_call_unknown_tool():
    """Unknown tool name returns UNKNOWN_TOOL error."""
    raw = dispatch_tool_call("non_existent_tool", {})
    result = json.loads(raw)
    assert result["status"] == "UNKNOWN_TOOL"


def test_threads_search_top_views():
    """threads_search finds matching posts and sorts by top views."""
    raw = dispatch_tool_call(
        "threads_search", {"query": "AI", "sort_by": "top_views", "limit": 5}
    )
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert result["query"] == "AI"
    assert len(result["data"]) > 0
    top_post = result["data"][0]
    assert "AI" in top_post["text"]
    assert "views" in top_post
    assert top_post["id"] == "th_post_001"


def test_threads_search_recent():
    """threads_search sorts by recent timestamp when requested."""
    raw = dispatch_tool_call(
        "threads_search", {"query": "Threads", "sort_by": "recent", "limit": 5}
    )
    result = json.loads(raw)
    assert result["status"] == "SUCCESS"
    assert len(result["data"]) > 0


def test_threads_search_not_found():
    """threads_search returns NOT_FOUND when no posts match query."""
    raw = dispatch_tool_call(
        "threads_search", {"query": "non_existent_keyword_xyz", "limit": 5}
    )
    result = json.loads(raw)
    assert result["status"] == "NOT_FOUND"


def test_threads_search_natural_language_and_intent_matching():
    """threads_search matches posts using natural language queries and intent stopwords."""
    # 1. Natural language query with sorting phrase "AI nhiều view nhất"
    raw = dispatch_tool_call(
        "threads_search", {"query": "AI nhiều view nhất", "sort_by": "top_views", "limit": 5}
    )
    res = json.loads(raw)
    assert res["status"] == "SUCCESS"
    assert res["data"][0]["id"] == "th_post_001"

    # 2. Pure intent phrase "Tìm bài viết có nhiều lượt xem nhất"
    raw_intent = dispatch_tool_call(
        "threads_search", {"query": "Tìm bài viết có nhiều lượt xem nhất", "sort_by": "top_views", "limit": 5}
    )
    res_intent = json.loads(raw_intent)
    assert res_intent["status"] == "SUCCESS"
    assert len(res_intent["data"]) >= 2
    assert res_intent["data"][0]["views"] >= res_intent["data"][1]["views"]

    # 3. Topic keyword "Hook"
    raw_hook = dispatch_tool_call(
        "threads_search", {"query": "kỹ thuật viết hook", "sort_by": "top_views", "limit": 5}
    )
    res_hook = json.loads(raw_hook)
    assert res_hook["status"] == "SUCCESS"
    assert res_hook["data"][0]["id"] == "th_post_002"


def test_threads_oauth_authorization_url():
    """ThreadsOAuth generates valid Meta Threads authorization URL with required scopes."""
    from src.tools import ThreadsOAuth

    oauth = ThreadsOAuth(app_id="test_app_123", app_secret="test_secret_456")
    url = oauth.get_authorization_url()
    assert "https://threads.net/oauth/authorize" in url
    assert "client_id=test_app_123" in url
    assert "redirect_uri=" in url
    assert "scope=" in url
    assert "response_type=code" in url


def test_threads_oauth_exchange_code_and_long_lived_token():
    """ThreadsOAuth exchanges auth code for short-lived token then for long-lived token."""
    from unittest.mock import patch
    from src.tools import ThreadsOAuth

    oauth = ThreadsOAuth(app_id="test_app_123", app_secret="test_secret_456")
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "short_lived_token",
            "user_id": "12345",
        }
        short_res = oauth.exchange_code_for_token("test_auth_code")
        assert short_res["access_token"] == "short_lived_token"

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "access_token": "long_lived_token_xyz",
            "token_type": "bearer",
            "expires_in": 5184000,
        }
        long_res = oauth.get_long_lived_token("short_lived_token")
        assert long_res["access_token"] == "long_lived_token_xyz"


def test_threads_oauth_save_and_load_token(tmp_path):
    """ThreadsOAuth saves and loads tokens from JSON file."""
    from src.tools import ThreadsOAuth

    token_file = str(tmp_path / ".threads-token.json")
    oauth = ThreadsOAuth(app_id="test_app", app_secret="test_secret")
    oauth.save_token_to_file(
        {"access_token": "tok_123", "user_id": "u1", "expires_at": 1800000000},
        filepath=token_file,
    )
    loaded = oauth.load_token_from_file(filepath=token_file)
    assert loaded is not None
    assert loaded["access_token"] == "tok_123"
    assert loaded["user_id"] == "u1"


def test_threads_client_get_profile_live():
    """ThreadsClient fetches profile via real Graph API GET /me."""
    from unittest.mock import patch
    from src.tools import ThreadsClient

    client = ThreadsClient(access_token="valid_token", user_id="me")
    with patch.object(client.session, "get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "id": "123456",
            "username": "live_user",
            "name": "Live Threads User",
        }
        profile = client.get_profile()
        assert profile["username"] == "live_user"
        mock_get.assert_called_once()
        call_args, call_kwargs = mock_get.call_args
        assert "https://graph.threads.net/v1.0/me" in call_args[0]
        assert call_kwargs["params"]["access_token"] == "valid_token"


def test_threads_client_create_thread_two_step():
    """ThreadsClient publishes thread in 2 steps: media container and publish."""
    from unittest.mock import MagicMock, patch
    from src.tools import ThreadsClient

    client = ThreadsClient(access_token="valid_token", user_id="me")
    with patch.object(client.session, "post") as mock_post:
        res1 = MagicMock(status_code=200)
        res1.json.return_value = {"id": "container_999"}
        res2 = MagicMock(status_code=200)
        res2.json.return_value = {"id": "published_thread_111"}
        mock_post.side_effect = [res1, res2]

        result = client.create_thread(text="Hello from live real Threads API!")
        assert result["id"] == "published_thread_111"
        assert mock_post.call_count == 2
        # Check Step 1 endpoint & params
        step1_url = mock_post.call_args_list[0][0][0]
        step1_params = mock_post.call_args_list[0][1]["params"]
        assert "threads" in step1_url
        assert step1_params["text"] == "Hello from live real Threads API!"
        assert step1_params["media_type"] == "TEXT"

        # Check Step 2 endpoint & params
        step2_url = mock_post.call_args_list[1][0][0]
        step2_params = mock_post.call_args_list[1][1]["params"]
        assert "threads_publish" in step2_url
        assert step2_params["creation_id"] == "container_999"


def test_threads_client_reply_to_thread():
    """ThreadsClient replies to a thread using reply_to_id in media container."""
    from unittest.mock import MagicMock, patch
    from src.tools import ThreadsClient

    client = ThreadsClient(access_token="valid_token", user_id="me")
    with patch.object(client.session, "post") as mock_post:
        res1 = MagicMock(status_code=200)
        res1.json.return_value = {"id": "container_rep_01"}
        res2 = MagicMock(status_code=200)
        res2.json.return_value = {"id": "published_rep_01"}
        mock_post.side_effect = [res1, res2]

        result = client.reply_to_thread(thread_id="th_001", text="Great post!")
        assert result["id"] == "published_rep_01"
        assert mock_post.call_args_list[0][1]["params"]["reply_to_id"] == "th_001"


def test_threads_client_get_insights():
    """ThreadsClient parses metrics from insights API response."""
    from unittest.mock import patch
    from src.tools import ThreadsClient

    client = ThreadsClient(access_token="valid_token")
    with patch.object(client.session, "get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [
                {"name": "views", "values": [{"value": 15000}]},
                {"name": "likes", "values": [{"value": 850}]},
            ]
        }
        insights = client.get_insights("th_post_001")
        assert insights["views"] == 15000
        assert insights["likes"] == 850


def test_dispatch_tool_call_uses_live_client_when_authenticated():
    """dispatch_tool_call routes to ThreadsClient when authenticated with token."""
    from unittest.mock import MagicMock, patch

    with patch("src.tools.get_threads_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client.get_profile.return_value = {
            "id": "live_user_1",
            "username": "live_real_user",
            "followers_count": 500,
        }
        mock_get_client.return_value = mock_client

        raw = dispatch_tool_call("threads_get_profile", {})
        result = json.loads(raw)
        assert result["status"] == "SUCCESS"
        assert result["data"]["username"] == "live_real_user"
        mock_client.get_profile.assert_called_once()


