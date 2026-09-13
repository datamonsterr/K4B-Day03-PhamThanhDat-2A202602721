"""
🛠️ THREADS MODEL CONTEXT PROTOCOL (MCP) TOOLS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ Threads MCP Server.
Triển khai tuân thủ chuẩn quinnjr/threads-mcp.
"""

import json
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (quinnjr/threads-mcp)
# ==============================================================================

TOOLS_SCHEMA = [
    {
        "name": "threads_get_profile",
        "description": "Lấy thông tin hồ sơ kênh Threads đã xác thực (username, biography, followers_count).",
        "parameters": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách các trường cần lấy (ví dụ: ['id', 'username', 'name', 'threads_biography', 'followers_count']).",
                }
            },
            "required": [],
        },
    },
    {
        "name": "threads_get_threads",
        "description": "Lấy danh sách các bài đăng (threads) trên kênh kèm phân trang.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Số lượng bài đăng tối đa cần lấy (mặc định: 10).",
                },
                "before": {
                    "type": "string",
                    "description": "Con trỏ phân trang trước.",
                },
                "after": {
                    "type": "string",
                    "description": "Con trỏ phân trang sau.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "threads_get_thread",
        "description": "Lấy thông tin chi tiết của một bài đăng Threads cụ thể theo mã thread_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "Mã định danh bài đăng Threads (ví dụ: 'th_post_001').",
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách các trường chi tiết cần lấy.",
                },
            },
            "required": ["thread_id"],
        },
    },
    {
        "name": "threads_create_thread",
        "description": "Tạo và xuất bản bài viết mới lên kênh Threads.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Nội dung bài viết cần đăng tải lên Threads (tối đa 500 ký tự).",
                },
                "reply_control": {
                    "type": "string",
                    "enum": ["everyone", "accounts_you_follow", "mentioned_only"],
                    "description": "Quyền phản hồi bài viết: everyone, accounts_you_follow, mentioned_only.",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "threads_reply_to_thread",
        "description": "Phản hồi/trả lời một bài đăng hoặc thảo luận trên Threads theo thread_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "Mã bài viết cần phản hồi (ví dụ: 'th_post_001').",
                },
                "text": {
                    "type": "string",
                    "description": "Nội dung phản hồi.",
                },
                "reply_control": {
                    "type": "string",
                    "enum": ["everyone", "accounts_you_follow", "mentioned_only"],
                    "description": "Quyền phản hồi của bình luận.",
                },
            },
            "required": ["thread_id", "text"],
        },
    },
    {
        "name": "threads_get_insights",
        "description": "Truy vấn các chỉ số tương tác và phân tích hiệu suất (views, likes, replies, reposts, quotes) của một bài đăng Threads.",
        "parameters": {
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "Mã bài đăng cần tra cứu số liệu (ví dụ: 'th_post_001').",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách chỉ số cần lấy: views, likes, replies, reposts, quotes.",
                },
            },
            "required": ["thread_id"],
        },
    },
    {
        "name": "threads_get_replies",
        "description": "Lấy danh sách các phản hồi và bình luận của người dùng đối với một bài đăng Threads.",
        "parameters": {
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "Mã bài đăng cần lấy danh sách phản hồi.",
                }
            },
            "required": ["thread_id"],
        },
    },
    {
        "name": "threads_get_conversation",
        "description": "Lấy toàn bộ luồng hội thoại bao gồm bài viết gốc và các lượt phản hồi liên quan.",
        "parameters": {
            "type": "object",
            "properties": {
                "thread_id": {
                    "type": "string",
                    "description": "Mã bài đăng gốc để truy xuất cây hội thoại.",
                }
            },
            "required": ["thread_id"],
        },
    },
    {
        "name": "threads_search",
        "description": "Tìm kiếm các bài viết trên kênh Threads theo từ khóa, hỗ trợ sắp xếp theo lượt xem nhiều nhất (top_views), lượt thích nhiều nhất (top_likes), hoặc mới nhất (recent).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Từ khóa hoặc chủ đề cần tìm kiếm (ví dụ: 'AI', 'ReAct', 'Hook').",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["top_views", "top_likes", "recent"],
                    "description": "Tiêu chí sắp xếp: 'top_views' (nhiều view nhất), 'top_likes' (nhiều like nhất), 'recent' (mới nhất). Mặc định là 'top_views'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Số lượng bài viết tối đa cần trả về (mặc định: 5).",
                },
            },
            "required": ["query"],
        },
    },
]

# ==============================================================================
# 2. CLIENT THREADS API THỰC TẾ & XÁC THỰC OAUTH (quinnjr/threads-mcp)
# ==============================================================================


class ThreadsOAuth:
    """Quản lý xác thực OAuth 2.0 theo chuẩn Meta Threads Graph API."""

    def __init__(
        self,
        app_id: str | None = None,
        app_secret: str | None = None,
        redirect_uri: str = "http://localhost:48810/callback",
    ) -> None:
        self.app_id = (
            app_id
            or os.getenv("THREAD_APP_ID")
            or os.getenv("THREADS_APP_ID")
            or ""
        )
        self.app_secret = (
            app_secret
            or os.getenv("THREAD_APP_SECRET")
            or os.getenv("THREADS_APP_SECRET")
            or ""
        )
        self.redirect_uri = redirect_uri
        self.auth_url = "https://threads.net/oauth/authorize"
        self.token_url = "https://graph.threads.net/oauth/access_token"
        self.long_lived_token_url = "https://graph.threads.net/access_token"
        self.refresh_token_url = "https://graph.threads.net/refresh_access_token"

    def get_authorization_url(
        self,
        scope: list[str] | None = None,
        state: str | None = None,
    ) -> str:
        """Tạo đường dẫn URL cấp quyền xác thực cho người dùng trên Threads."""
        scopes = scope or [
            "threads_basic",
            "threads_content_publish",
            "threads_manage_insights",
            "threads_manage_replies",
            "threads_read_replies",
        ]
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": ",".join(scopes),
            "response_type": "code",
        }
        if state:
            params["state"] = state
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> dict[str, Any]:
        """Đổi Authorization Code lấy Short-lived Token (hạn 1 giờ)."""
        data = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "code": code,
        }
        res = requests.post(self.token_url, data=data, timeout=30)
        return res.json()

    def get_long_lived_token(self, short_lived_token: str) -> dict[str, Any]:
        """Đổi Short-lived Token lấy Long-lived Token có hạn 60 ngày."""
        params = {
            "grant_type": "th_exchange_token",
            "client_secret": self.app_secret,
            "access_token": short_lived_token,
        }
        res = requests.get(self.long_lived_token_url, params=params, timeout=30)
        return res.json()

    def refresh_long_lived_token(self, long_lived_token: str) -> dict[str, Any]:
        """Gia hạn Long-lived Token trước khi hết hạn."""
        params = {
            "grant_type": "th_refresh_token",
            "access_token": long_lived_token,
        }
        res = requests.get(self.refresh_token_url, params=params, timeout=30)
        return res.json()

    def get_user_id(self, access_token: str) -> str:
        """Lấy User ID của tài khoản được ủy quyền."""
        res = requests.get(
            "https://graph.threads.net/v1.0/me",
            params={"fields": "id", "access_token": access_token},
            timeout=30,
        )
        data = res.json()
        return data.get("id", "me")

    def save_token_to_file(
        self, token_data: dict[str, Any], filepath: str = ".threads-token.json"
    ) -> None:
        """Lưu token ra file JSON cục bộ."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)

    def load_token_from_file(
        self, filepath: str = ".threads-token.json"
    ) -> dict[str, Any] | None:
        """Tải token từ file JSON cục bộ nếu tồn tại."""
        candidates = [filepath, os.path.expanduser("~/.threads-token.json")]
        for p in candidates:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    continue
        return None


class ThreadsClient:
    """Client kết nối trực tiếp đến Meta Threads Graph API v1.0."""

    def __init__(
        self,
        access_token: str | None = None,
        user_id: str | None = None,
        api_version: str = "v1.0",
        base_url: str = "https://graph.threads.net",
    ) -> None:
        self.api_version = api_version
        self.base_url = f"{base_url.rstrip('/')}/{self.api_version}"
        self.user_id = (
            user_id
            or os.getenv("THREAD_USER_ID")
            or os.getenv("THREADS_USER_ID")
            or "me"
        )

        # Ưu tiên: tham số truyền vào > biến môi trường > file .threads-token.json
        self.access_token = (
            access_token
            or os.getenv("THREAD_ACCESS_TOKEN")
            or os.getenv("THREADS_ACCESS_TOKEN")
        )
        if not self.access_token:
            saved = ThreadsOAuth().load_token_from_file()
            if saved and isinstance(saved, dict) and "access_token" in saved:
                self.access_token = saved["access_token"]
                if "user_id" in saved and not user_id:
                    self.user_id = saved["user_id"]

        self.session = requests.Session()

    def is_authenticated(self) -> bool:
        """Kiểm tra xem Client đã có Access Token hợp lệ để gọi API trực tiếp hay chưa."""
        if os.getenv("PYTEST_CURRENT_TEST") and not os.getenv("TEST_LIVE_THREADS"):
            return False
        if not self.access_token:
            return False
        return self.access_token not in [
            "your_threads_access_token_here",
            "your_access_token_here",
            "",
        ]

    def _auth_params(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        p = dict(params or {})
        if self.access_token:
            p["access_token"] = self.access_token
        return p

    def get_profile(self, fields: list[str] | None = None) -> dict[str, Any]:
        """GET /{user_id} - Lấy thông tin tài khoản Threads."""
        default_fields = [
            "id",
            "username",
            "name",
            "threads_profile_picture_url",
            "threads_biography",
        ]
        f_str = ",".join(fields or default_fields)
        url = f"{self.base_url}/{self.user_id}"
        res = self.session.get(
            url, params=self._auth_params({"fields": f_str}), timeout=30
        )
        return res.json()

    def get_threads(
        self,
        limit: int = 10,
        before: str | None = None,
        after: str | None = None,
    ) -> dict[str, Any]:
        """GET /{user_id}/threads - Lấy danh sách bài đăng."""
        url = f"{self.base_url}/{self.user_id}/threads"
        params: dict[str, Any] = {
            "fields": "id,media_product_type,media_type,media_url,permalink,username,text,timestamp,shortcode",
            "limit": limit,
        }
        if before:
            params["before"] = before
        if after:
            params["after"] = after
        res = self.session.get(url, params=self._auth_params(params), timeout=30)
        return res.json()

    def get_thread(
        self, thread_id: str, fields: list[str] | None = None
    ) -> dict[str, Any]:
        """GET /{thread_id} - Lấy chi tiết một bài viết."""
        url = f"{self.base_url}/{thread_id.strip()}"
        default_fields = [
            "id",
            "media_product_type",
            "media_type",
            "media_url",
            "permalink",
            "username",
            "text",
            "timestamp",
            "shortcode",
        ]
        params = {"fields": ",".join(fields or default_fields)}
        res = self.session.get(url, params=self._auth_params(params), timeout=30)
        return res.json()

    def create_thread(
        self, text: str, reply_control: str = "everyone"
    ) -> dict[str, Any]:
        """Xuất bản bài viết 2 bước lên Threads: 1. Tạo container, 2. Publish."""
        container_url = f"{self.base_url}/{self.user_id}/threads"
        c_params = {
            "media_type": "TEXT",
            "text": text,
            "reply_control": reply_control,
        }
        c_res = self.session.post(
            container_url, params=self._auth_params(c_params), timeout=30
        )
        c_data = c_res.json()
        if "id" not in c_data:
            return c_data

        container_id = c_data["id"]
        publish_url = f"{self.base_url}/{self.user_id}/threads_publish"
        p_params = {"creation_id": container_id}
        p_res = self.session.post(
            publish_url, params=self._auth_params(p_params), timeout=30
        )
        return p_res.json()

    def reply_to_thread(
        self, thread_id: str, text: str, reply_control: str = "everyone"
    ) -> dict[str, Any]:
        """Phản hồi bài viết qua việc tạo media container gắn reply_to_id rồi xuất bản."""
        container_url = f"{self.base_url}/{self.user_id}/threads"
        c_params = {
            "media_type": "TEXT",
            "text": text,
            "reply_to_id": thread_id.strip(),
            "reply_control": reply_control,
        }
        c_res = self.session.post(
            container_url, params=self._auth_params(c_params), timeout=30
        )
        c_data = c_res.json()
        if "id" not in c_data:
            return c_data

        container_id = c_data["id"]
        publish_url = f"{self.base_url}/{self.user_id}/threads_publish"
        p_params = {"creation_id": container_id}
        p_res = self.session.post(
            publish_url, params=self._auth_params(p_params), timeout=30
        )
        return p_res.json()

    def get_insights(
        self, thread_id: str, metrics: list[str] | None = None
    ) -> dict[str, int]:
        """GET /{thread_id}/insights - Truy vấn số liệu views, likes, replies, v.v."""
        url = f"{self.base_url}/{thread_id.strip()}/insights"
        m_list = metrics or ["views", "likes", "replies", "reposts", "quotes"]
        params = {"metric": ",".join(m_list)}
        res = self.session.get(url, params=self._auth_params(params), timeout=30)
        raw_data = res.json()
        metrics_dict: dict[str, int] = {}
        if "data" in raw_data and isinstance(raw_data["data"], list):
            for item in raw_data["data"]:
                name = item.get("name")
                values = item.get("values", [])
                if name and values and isinstance(values, list):
                    metrics_dict[name] = values[0].get("value", 0)
        return metrics_dict

    def get_replies(self, thread_id: str) -> dict[str, Any]:
        """GET /{thread_id}/replies - Lấy danh sách bình luận của bài viết."""
        url = f"{self.base_url}/{thread_id.strip()}/replies"
        params = {"fields": "id,text,username,permalink,timestamp"}
        res = self.session.get(url, params=self._auth_params(params), timeout=30)
        return res.json()

    def get_conversation(self, thread_id: str) -> dict[str, Any]:
        """GET /{thread_id}/conversation - Lấy toàn bộ luồng hội thoại."""
        url = f"{self.base_url}/{thread_id.strip()}/conversation"
        params = {"fields": "id,text,username,permalink,timestamp"}
        res = self.session.get(url, params=self._auth_params(params), timeout=30)
        return res.json()


_GLOBAL_THREADS_CLIENT: ThreadsClient | None = None


def get_threads_client() -> ThreadsClient:
    """Factory lấy singleton instance của ThreadsClient."""
    global _GLOBAL_THREADS_CLIENT
    if _GLOBAL_THREADS_CLIENT is None:
        _GLOBAL_THREADS_CLIENT = ThreadsClient()
    return _GLOBAL_THREADS_CLIENT


def start_local_oauth_server(port: int = 48810) -> dict[str, Any]:
    """Khởi động local HTTP callback server tại localhost:48810 để nhận token từ Threads OAuth."""
    import webbrowser
    from http.server import BaseHTTPRequestHandler, HTTPServer

    oauth = ThreadsOAuth(redirect_uri=f"http://localhost:{port}/callback")
    auth_url = oauth.get_authorization_url()

    auth_code_holder: dict[str, str] = {}

    class OAuthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/callback":
                query = urllib.parse.parse_qs(parsed.query)
                code = query.get("code", [None])[0]
                if code:
                    auth_code_holder["code"] = code
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    html = """
                    <html>
                    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                        <h1 style="color: #10b981;">🎉 Threads Authorization Successful!</h1>
                        <p>Xác thực thành công! Bạn có thể đóng tab trình duyệt này.</p>
                    </body>
                    </html>
                    """
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Error: Missing authorization code.")

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = HTTPServer(("localhost", port), OAuthHandler)
    print(f"\n🔗 Mở đường dẫn sau để đăng nhập và cấp quyền cho Threads App:\n{auth_url}\n")
    print(f"⏳ Đang chờ phản hồi OAuth tại http://localhost:{port}/callback ...")

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    while "code" not in auth_code_holder:
        server.handle_request()

    code = auth_code_holder["code"]
    print("✅ Đã nhận được Authorization Code từ Meta!")
    print("🔄 Đang chuyển đổi sang Long-Lived Token (60 ngày)...")

    token_data = oauth.exchange_code_for_token(code)
    short_token = token_data.get("access_token")
    if short_token:
        long_data = oauth.get_long_lived_token(short_token)
        long_token = long_data.get("access_token", short_token)
        expires_in = long_data.get("expires_in", 5184000)
        user_id = oauth.get_user_id(long_token)
        final_token = {
            "access_token": long_token,
            "user_id": user_id,
            "expires_in": expires_in,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        oauth.save_token_to_file(final_token)
        print(f"🎉 Lưu Token thành công vào '.threads-token.json'! (User ID: {user_id})")
        return final_token
    return token_data


# ==============================================================================
# 3. MÔ PHỎNG DỮ LIỆU & THỰC THI TOOLS (EXECUTION LAYER)
# ==============================================================================

MOCK_PROFILE: dict[str, Any] = {
    "id": "usr_vinuni_threads_01",
    "username": "vinuni_ai_hub",
    "name": "VinUni AI Research Hub",
    "threads_biography": "Kênh thông tin chính thức của VinUni AI Hub 24/7. Cập nhật nghiên cứu AI Agent, ReAct Loop và Model Context Protocol.",
    "followers_count": 12840,
    "threads_profile_picture_url": "https://vinuni.edu.vn/images/ai_hub_avatar.png",
}

MOCK_THREADS: dict[str, dict[str, Any]] = {
    "th_post_001": {
        "id": "th_post_001",
        "text": "ReAct Agent và MCP Protocol là bước ngoặt đưa AI từ Chatbot phản hồi tĩnh sang Hệ thống Tác tử tự chủ hành động. Cùng thảo luận nhé! #VinUniAI #ReActAgent",
        "timestamp": "2026-09-12T10:00:00Z",
        "media_type": "TEXT_POST",
        "permalink": "https://www.threads.net/@vinuni_ai_hub/post/th_post_001",
        "reply_control": "everyone",
    },
    "th_post_002": {
        "id": "th_post_002",
        "text": "5 Kỹ thuật viết Hook giữ chân người đọc trên Threads trong 3 dòng đầu: 1. Mở đầu bằng câu hỏi đối nghịch, 2. Dẫn chứng con số bất ngờ, 3. Đưa ra quan điểm ngược dòng. Bạn áp dụng cách nào?",
        "timestamp": "2026-09-13T08:00:00Z",
        "media_type": "TEXT_POST",
        "permalink": "https://www.threads.net/@vinuni_ai_hub/post/th_post_002",
        "reply_control": "everyone",
    },
}

MOCK_INSIGHTS: dict[str, dict[str, int]] = {
    "th_post_001": {
        "views": 25400,
        "likes": 1820,
        "replies": 125,
        "reposts": 88,
        "quotes": 34,
    },
    "th_post_002": {
        "views": 9800,
        "likes": 640,
        "replies": 45,
        "reposts": 22,
        "quotes": 8,
    },
}

MOCK_REPLIES: dict[str, list[dict[str, Any]]] = {
    "th_post_001": [
        {
            "id": "rep_001_01",
            "user": "tech_dev_99",
            "text": "MCP Server hoạt động với ReAct agent như thế nào vậy admin?",
            "timestamp": "2026-09-12T11:00:00Z",
        },
        {
            "id": "rep_001_02",
            "user": "ai_learner",
            "text": "Rất mong được xem thêm file trace waterfall để phân tích độ trễ.",
            "timestamp": "2026-09-12T11:30:00Z",
        },
    ],
    "th_post_002": [
        {
            "id": "rep_002_01",
            "user": "content_creator",
            "text": "Mẹo số 2 hiệu quả bất ngờ luôn ad ơi!",
            "timestamp": "2026-09-13T09:00:00Z",
        }
    ],
}


def execute_threads_get_profile(fields: list[str] | None = None) -> str:
    """Lấy thông tin profile người dùng đã đăng nhập."""
    client = get_threads_client()
    if client.is_authenticated():
        try:
            res = client.get_profile(fields)
            if isinstance(res, dict) and "error" in res:
                return json.dumps({"status": "API_ERROR", "error": res["error"]}, ensure_ascii=False)
            return json.dumps({"status": "SUCCESS", "data": res}, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False)

    data = (
        {k: v for k, v in MOCK_PROFILE.items() if k in fields}
        if fields
        else dict(MOCK_PROFILE)
    )
    return json.dumps({"status": "SUCCESS", "data": data}, ensure_ascii=False)


def execute_threads_get_threads(
    limit: int = 10,
    before: str | None = None,
    after: str | None = None,
) -> str:
    """Lấy danh sách bài đăng gần nhất."""
    client = get_threads_client()
    if client.is_authenticated():
        try:
            res = client.get_threads(limit=limit, before=before, after=after)
            if isinstance(res, dict) and "error" in res:
                return json.dumps({"status": "API_ERROR", "error": res["error"]}, ensure_ascii=False)
            data = res.get("data", [])
            return json.dumps(
                {
                    "status": "SUCCESS",
                    "data": data,
                    "paging": res.get("paging", {"count": len(data)}),
                },
                ensure_ascii=False,
            )
        except Exception as e:  # noqa: BLE001
            return json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False)

    threads_list = list(MOCK_THREADS.values())[:limit]
    return json.dumps(
        {
            "status": "SUCCESS",
            "data": threads_list,
            "paging": {"count": len(threads_list)},
        },
        ensure_ascii=False,
    )


def execute_threads_get_thread(
    thread_id: str, fields: list[str] | None = None
) -> str:
    """Lấy thông tin chi tiết bài đăng theo ID."""
    clean_id = thread_id.strip()
    client = get_threads_client()
    if client.is_authenticated():
        try:
            res = client.get_thread(clean_id, fields)
            if isinstance(res, dict) and "error" in res:
                err_code = res["error"].get("code", 0)
                if err_code in [100, 803, 10] or "not found" in str(res["error"]).lower():
                    return json.dumps(
                        {
                            "status": "NOT_FOUND",
                            "message": f"Thread with ID '{clean_id}' not found on Threads API.",
                        },
                        ensure_ascii=False,
                    )
                return json.dumps({"status": "API_ERROR", "error": res["error"]}, ensure_ascii=False)
            return json.dumps({"status": "SUCCESS", "thread_id": clean_id, "data": res}, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False)

    thread = MOCK_THREADS.get(clean_id)
    if not thread:
        return json.dumps(
            {
                "status": "NOT_FOUND",
                "message": f"Thread with ID '{clean_id}' not found on Threads API.",
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {"status": "SUCCESS", "thread_id": clean_id, "data": thread},
        ensure_ascii=False,
    )


def execute_threads_create_thread(
    text: str, reply_control: str = "everyone"
) -> str:
    """Đăng bài viết mới lên kênh Threads."""
    client = get_threads_client()
    if client.is_authenticated():
        try:
            res = client.create_thread(text=text, reply_control=reply_control)
            if isinstance(res, dict) and "error" in res:
                return json.dumps({"status": "API_ERROR", "error": res["error"]}, ensure_ascii=False)
            new_id = res.get("id", "")
            permalink = f"https://www.threads.net/post/{new_id}"
            return json.dumps(
                {
                    "status": "SUCCESS",
                    "id": new_id,
                    "text": text,
                    "permalink": permalink,
                    "message": f"Xuất bản bài viết thành công lên Threads với ID '{new_id}'.",
                },
                ensure_ascii=False,
            )
        except Exception as e:  # noqa: BLE001
            return json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False)

    new_id = f"th_post_{len(MOCK_THREADS) + 1:03d}"
    now_iso = datetime.now(timezone.utc).isoformat()
    new_post = {
        "id": new_id,
        "text": text,
        "timestamp": now_iso,
        "media_type": "TEXT_POST",
        "permalink": f"https://www.threads.net/@vinuni_ai_hub/post/{new_id}",
        "reply_control": reply_control,
    }
    MOCK_THREADS[new_id] = new_post
    MOCK_INSIGHTS[new_id] = {"views": 1, "likes": 0, "replies": 0, "reposts": 0, "quotes": 0}
    return json.dumps(
        {
            "status": "SUCCESS",
            "id": new_id,
            "text": text,
            "permalink": new_post["permalink"],
            "message": f"Xuất bản bài viết thành công lên Threads với ID '{new_id}'.",
        },
        ensure_ascii=False,
    )


def execute_threads_reply_to_thread(
    thread_id: str, text: str, reply_control: str = "everyone"
) -> str:
    """Phản hồi một bài viết Threads."""
    clean_id = thread_id.strip()
    client = get_threads_client()
    if client.is_authenticated():
        try:
            res = client.reply_to_thread(clean_id, text=text, reply_control=reply_control)
            if isinstance(res, dict) and "error" in res:
                err_str = str(res["error"]).lower()
                if "not found" in err_str or res["error"].get("code") in [100, 803]:
                    return json.dumps(
                        {
                            "status": "NOT_FOUND",
                            "message": f"Không thể phản hồi: bài viết '{clean_id}' không tồn tại.",
                        },
                        ensure_ascii=False,
                    )
                return json.dumps({"status": "API_ERROR", "error": res["error"]}, ensure_ascii=False)
            reply_id = res.get("id", "")
            return json.dumps(
                {
                    "status": "SUCCESS",
                    "id": reply_id,
                    "thread_id": clean_id,
                    "text": text,
                    "message": f"Phản hồi thành công vào bài viết '{clean_id}'.",
                },
                ensure_ascii=False,
            )
        except Exception as e:  # noqa: BLE001
            return json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False)

    if clean_id not in MOCK_THREADS:
        return json.dumps(
            {
                "status": "NOT_FOUND",
                "message": f"Không thể phản hồi: bài viết '{clean_id}' không tồn tại.",
            },
            ensure_ascii=False,
        )

    reply_id = f"rep_{clean_id[-3:]}_{len(MOCK_REPLIES.get(clean_id, [])) + 1:02d}"
    reply_obj = {
        "id": reply_id,
        "user": "vinuni_ai_hub",
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reply_control": reply_control,
    }
    if clean_id not in MOCK_REPLIES:
        MOCK_REPLIES[clean_id] = []
    MOCK_REPLIES[clean_id].append(reply_obj)

    # Cập nhật số lượt reply trong insights
    if clean_id in MOCK_INSIGHTS:
        MOCK_INSIGHTS[clean_id]["replies"] += 1

    return json.dumps(
        {
            "status": "SUCCESS",
            "id": reply_id,
            "thread_id": clean_id,
            "text": text,
            "message": f"Phản hồi thành công vào bài viết '{clean_id}'.",
        },
        ensure_ascii=False,
    )


def execute_threads_get_insights(
    thread_id: str, metrics: list[str] | None = None
) -> str:
    """Lấy số liệu phân tích của bài đăng."""
    clean_id = thread_id.strip()
    client = get_threads_client()
    if client.is_authenticated():
        try:
            metrics_dict = client.get_insights(clean_id, metrics)
            if not metrics_dict:
                return json.dumps(
                    {
                        "status": "NOT_FOUND",
                        "message": f"Không tìm thấy số liệu tương tác cho bài viết '{clean_id}'.",
                    },
                    ensure_ascii=False,
                )
            return json.dumps(
                {"status": "SUCCESS", "thread_id": clean_id, "metrics": metrics_dict},
                ensure_ascii=False,
            )
        except Exception as e:  # noqa: BLE001
            return json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False)

    insights = MOCK_INSIGHTS.get(clean_id)
    if not insights:
        return json.dumps(
            {
                "status": "NOT_FOUND",
                "message": f"Không tìm thấy số liệu tương tác cho bài viết '{clean_id}'.",
            },
            ensure_ascii=False,
        )

    res_metrics = (
        {k: v for k, v in insights.items() if k in metrics}
        if metrics
        else dict(insights)
    )
    return json.dumps(
        {"status": "SUCCESS", "thread_id": clean_id, "metrics": res_metrics},
        ensure_ascii=False,
    )


def execute_threads_get_replies(thread_id: str) -> str:
    """Lấy danh sách các replies của một bài đăng."""
    clean_id = thread_id.strip()
    client = get_threads_client()
    if client.is_authenticated():
        try:
            res = client.get_replies(clean_id)
            if isinstance(res, dict) and "error" in res:
                return json.dumps(
                    {
                        "status": "NOT_FOUND",
                        "message": f"Bài viết '{clean_id}' không tồn tại.",
                    },
                    ensure_ascii=False,
                )
            return json.dumps(
                {"status": "SUCCESS", "thread_id": clean_id, "data": res.get("data", [])},
                ensure_ascii=False,
            )
        except Exception as e:  # noqa: BLE001
            return json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False)

    if clean_id not in MOCK_THREADS:
        return json.dumps(
            {
                "status": "NOT_FOUND",
                "message": f"Bài viết '{clean_id}' không tồn tại.",
            },
            ensure_ascii=False,
        )
    replies = MOCK_REPLIES.get(clean_id, [])
    return json.dumps(
        {"status": "SUCCESS", "thread_id": clean_id, "data": replies},
        ensure_ascii=False,
    )


def execute_threads_get_conversation(thread_id: str) -> str:
    """Lấy luồng hội thoại bài đăng và phản hồi."""
    clean_id = thread_id.strip()
    client = get_threads_client()
    if client.is_authenticated():
        try:
            res = client.get_conversation(clean_id)
            if isinstance(res, dict) and "error" in res:
                return json.dumps(
                    {
                        "status": "NOT_FOUND",
                        "message": f"Bài viết '{clean_id}' không tồn tại.",
                    },
                    ensure_ascii=False,
                )
            return json.dumps(
                {
                    "status": "SUCCESS",
                    "thread_id": clean_id,
                    "thread": res.get("data", {}),
                    "replies": res.get("replies", []),
                },
                ensure_ascii=False,
            )
        except Exception as e:  # noqa: BLE001
            return json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False)

    thread = MOCK_THREADS.get(clean_id)
    if not thread:
        return json.dumps(
            {
                "status": "NOT_FOUND",
                "message": f"Bài viết '{clean_id}' không tồn tại.",
            },
            ensure_ascii=False,
        )
    replies = MOCK_REPLIES.get(clean_id, [])
    return json.dumps(
        {
            "status": "SUCCESS",
            "thread_id": clean_id,
            "thread": thread,
            "replies": replies,
        },
        ensure_ascii=False,
    )


def execute_threads_search(
    query: str, sort_by: str = "top_views", limit: int = 5
) -> str:
    """Tìm kiếm bài viết theo từ khóa và sắp xếp theo lượt xem, lượt thích, hoặc thời gian."""
    q = query.strip().lower()
    client = get_threads_client()
    if client.is_authenticated():
        try:
            threads_res = client.get_threads(limit=50)
            items = threads_res.get("data", [])
            matched = []
            for item in items:
                text = item.get("text", "")
                tid = item.get("id", "")
                if q in text.lower() or q in tid.lower():
                    insights = client.get_insights(tid)
                    entry = dict(item)
                    entry["views"] = insights.get("views", 0)
                    entry["likes"] = insights.get("likes", 0)
                    entry["replies"] = insights.get("replies", 0)
                    entry["reposts"] = insights.get("reposts", 0)
                    matched.append(entry)
            if not matched:
                return json.dumps(
                    {
                        "status": "NOT_FOUND",
                        "query": query,
                        "message": f"Không tìm thấy bài viết nào phù hợp với từ khóa '{query}'.",
                    },
                    ensure_ascii=False,
                )
            if sort_by == "top_views":
                matched.sort(key=lambda x: x.get("views", 0), reverse=True)
            elif sort_by == "top_likes":
                matched.sort(key=lambda x: x.get("likes", 0), reverse=True)
            elif sort_by == "recent":
                matched.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            results = matched[:limit]
            return json.dumps(
                {
                    "status": "SUCCESS",
                    "query": query,
                    "sort_by": sort_by,
                    "count": len(results),
                    "data": results,
                },
                ensure_ascii=False,
            )
        except Exception as e:  # noqa: BLE001
            return json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False)

    matched = []
    for pid, post in MOCK_THREADS.items():
        if q in post.get("text", "").lower() or q in post.get("id", "").lower():
            insights = MOCK_INSIGHTS.get(pid, {})
            item = dict(post)
            item["views"] = insights.get("views", 0)
            item["likes"] = insights.get("likes", 0)
            item["replies"] = insights.get("replies", 0)
            item["reposts"] = insights.get("reposts", 0)
            matched.append(item)

    if not matched:
        return json.dumps(
            {
                "status": "NOT_FOUND",
                "query": query,
                "message": f"Không tìm thấy bài viết nào phù hợp với từ khóa '{query}'.",
            },
            ensure_ascii=False,
        )

    if sort_by == "top_views":
        matched.sort(key=lambda x: x.get("views", 0), reverse=True)
    elif sort_by == "top_likes":
        matched.sort(key=lambda x: x.get("likes", 0), reverse=True)
    elif sort_by == "recent":
        matched.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    results = matched[:limit]
    return json.dumps(
        {
            "status": "SUCCESS",
            "query": query,
            "sort_by": sort_by,
            "count": len(results),
            "data": results,
        },
        ensure_ascii=False,
    )


# Router gọi tool thực tế
TOOL_ROUTER = {
    "threads_get_profile": execute_threads_get_profile,
    "threads_get_threads": execute_threads_get_threads,
    "threads_get_thread": execute_threads_get_thread,
    "threads_create_thread": execute_threads_create_thread,
    "threads_reply_to_thread": execute_threads_reply_to_thread,
    "threads_get_insights": execute_threads_get_insights,
    "threads_get_replies": execute_threads_get_replies,
    "threads_get_conversation": execute_threads_get_conversation,
    "threads_search": execute_threads_search,
}


def dispatch_tool_call(tool_name: str, arguments: dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:  # noqa: BLE001
            return json.dumps(
                {"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False
            )
    return json.dumps(
        {"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"},
        ensure_ascii=False,
    )


if __name__ == "__main__":
    import sys

    if "--auth" in sys.argv:
        start_local_oauth_server()
    else:
        print("Threads MCP Tools Module.")
        print("Chạy 'python src/tools.py --auth' để xác thực tài khoản với Meta Threads API.")

