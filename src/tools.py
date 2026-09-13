"""
🛠️ THREADS MODEL CONTEXT PROTOCOL (MCP) TOOLS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ Threads MCP Server.
Triển khai tuân thủ chuẩn quinnjr/threads-mcp.
"""

import json
from datetime import datetime, timezone
from typing import Any

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
# 2. MÔ PHỎNG DỮ LIỆU & THỰC THI TOOLS (EXECUTION LAYER)
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
