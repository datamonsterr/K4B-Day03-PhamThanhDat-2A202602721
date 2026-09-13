"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI, OpenRouter & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import contextlib
import io
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv

if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding != "utf-8":
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()


class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(
        self, prompt: str, tools_schema: list[dict[str, Any]], system_prompt: str = ""
    ) -> dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""

    def __init__(self) -> None:
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu Threads API thời gian thực)."

    def generate_with_tools(
        self, prompt: str, tools_schema: list[dict[str, Any]], system_prompt: str = ""
    ) -> dict[str, Any]:
        prompt_lower = prompt.lower()

        # TC05: Edge case / tool failure simulation (post non-existent)
        if "th_post_999" in prompt_lower or "th-post-999" in prompt_lower or "nonexistent" in prompt_lower:
            return {
                "type": "tool_call",
                "tool_name": "threads_get_thread",
                "arguments": {"thread_id": "th_post_999"},
                "thought": "Người dùng yêu cầu kiểm tra bài đăng 'th_post_999'. Tôi sẽ gọi threads_get_thread để xác thực mã bài viết trên hệ thống.",
            }

        # TC03: Content publishing (create thread)
        if "xuất bản" in prompt_lower or "đăng bài" in prompt_lower or "tạo bài viết" in prompt_lower:
            # Extract content if quoted, or default text
            post_text = (
                "ReAct Agent và MCP Protocol là bước ngoặt đưa AI từ Chatbot phản hồi tĩnh sang Hệ thống Tác tử tự chủ hành động. Cùng thảo luận nhé! #VinUniAI #ReActAgent"
                if "react agent" in prompt_lower
                else prompt
            )
            return {
                "type": "tool_call",
                "tool_name": "threads_create_thread",
                "arguments": {
                    "text": post_text,
                    "reply_control": "everyone",
                },
                "thought": "Người dùng yêu cầu xuất bản bài viết mới lên kênh Threads. Tôi sẽ gọi tool threads_create_thread.",
            }

        # Search query (top views / keyword search)
        if "tìm" in prompt_lower or "search" in prompt_lower or "nhiều view" in prompt_lower or "nhieu view" in prompt_lower or "liên quan" in prompt_lower or "lien quan" in prompt_lower:
            keyword = "AI" if ("ai" in prompt_lower or "react" in prompt_lower) else ("Hook" if "hook" in prompt_lower else "Threads")
            sort_by = "top_views" if ("view" in prompt_lower or "nhieu" in prompt_lower or "nhiều" in prompt_lower or "top" in prompt_lower) else "recent"
            return {
                "type": "tool_call",
                "tool_name": "threads_search",
                "arguments": {"query": keyword, "sort_by": sort_by, "limit": 5},
                "thought": f"Người dùng muốn tìm bài viết liên quan đến '{keyword}' theo tiêu chí '{sort_by}'. Tôi sẽ gọi tool threads_search.",
            }

        # TC04: Multi-step reasoning (top engagement / list threads)
        if "cao nhất" in prompt_lower or "top" in prompt_lower or "danh sách bài đăng" in prompt_lower:
            return {
                "type": "tool_call",
                "tool_name": "threads_get_threads",
                "arguments": {"limit": 5},
                "thought": "Người dùng yêu cầu tìm bài đăng có tương tác cao nhất. Tôi sẽ gọi tool threads_get_threads để lấy danh sách bài đăng gần đây và phân tích số liệu.",
            }

        # TC02: Single tool query (get metrics / insights)
        if "chỉ số" in prompt_lower or "tương tác" in prompt_lower or "insights" in prompt_lower or "views" in prompt_lower:
            thread_id = "th_post_001"
            if "th_post_002" in prompt_lower:
                thread_id = "th_post_002"
            return {
                "type": "tool_call",
                "tool_name": "threads_get_insights",
                "arguments": {"thread_id": thread_id},
                "thought": f"Người dùng yêu cầu tra cứu chỉ số tương tác bài đăng {thread_id}. Tôi sẽ gọi tool threads_get_insights.",
            }

        # Profile lookup
        if "hồ sơ" in prompt_lower or "profile" in prompt_lower or "kênh" in prompt_lower and "thông tin" in prompt_lower:
            return {
                "type": "tool_call",
                "tool_name": "threads_get_profile",
                "arguments": {},
                "thought": "Người dùng muốn xem thông tin hồ sơ kênh Threads. Tôi sẽ gọi tool threads_get_profile.",
            }

        # TC01: General direct query (No tool call needed)
        return {
            "type": "text",
            "content": "[Mock Agent Response]: Độ dài lý tưởng cho bài đăng Threads thường từ 150 - 300 ký tự (khoảng 3 - 5 câu). 3 dòng đầu tiên (Hook) cần: 1. Đặt câu hỏi kích thích sự tò mò, 2. Đưa ra con số thống kê hoặc kết quả bất ngờ, 3. Chia sẻ một quan điểm ngược dòng (contrarian view) để giữ chân người đọc trước nút 'Xem thêm'.",
            "thought": "Đây là câu hỏi tư vấn chung về kỹ thuật viết bài Threads, có thể trả lời trực tiếp mà không cần gọi Tool.",
        }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(
                model=self.model_name, contents=contents
            )
            return response.text or ""
        except Exception as e:  # noqa: BLE001
            return f"[Gemini Exception]: {e!s}"

    def generate_with_tools(
        self, prompt: str, tools_schema: list[dict[str, Any]], system_prompt: str = ""
    ) -> dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print(
                "ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline."
            )
            return MockOfflineProvider().generate_with_tools(
                prompt, tools_schema, system_prompt
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append(
                    {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {}),
                    }
                )

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}]
                if function_declarations
                else None,
                temperature=0.2,
            )

            response = client.models.generate_content(
                model=self.model_name, contents=prompt, config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, "args") and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}",
                }
            return {
                "type": "text",
                "content": response.text or "",
                "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
            }

        except Exception as e:  # noqa: BLE001
            print(
                f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({e!s}). Tự động fallback về Mock."
            )
            return MockOfflineProvider().generate_with_tools(
                prompt, tools_schema, system_prompt
            )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK, hỗ trợ custom base_url / 9router)"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = (
            api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        )
        self.model_name = model or os.getenv("LLM_MODEL") or "gh/gpt-4o-mini"
        self.base_url = (
            base_url
            or os.getenv("OPENAI_BASE_URL")
            or "http://localhost:20128/v1"
        )

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI

            client_kwargs: dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            client = OpenAI(**client_kwargs)
            messages: list[Any] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=self.model_name, messages=messages
            )
            return response.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001
            return f"[OpenAI Exception]: {e!s}"

    def generate_with_tools(
        self, prompt: str, tools_schema: list[dict[str, Any]], system_prompt: str = ""
    ) -> dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print(
                "ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline."
            )
            return MockOfflineProvider().generate_with_tools(
                prompt, tools_schema, system_prompt
            )

        try:
            from openai import OpenAI

            client_kwargs: dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            client = OpenAI(**client_kwargs)

            tools: list[Any] = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool.get("parameters", {}),
                        },
                    }
                )

            messages: list[Any] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            if tools:
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
            else:
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                func = getattr(call, "function", None)
                func_name = getattr(func, "name", "")
                func_args = getattr(func, "arguments", "")
                args = (
                    json.loads(func_args)
                    if isinstance(func_args, str) and func_args
                    else (func_args if isinstance(func_args, dict) else {})
                )
                return {
                    "type": "tool_call",
                    "tool_name": func_name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{func_name}' với tham số: {json.dumps(args, ensure_ascii=False)}",
                }
            return {
                "type": "text",
                "content": msg.content or "",
                "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
            }
        except Exception as e:  # noqa: BLE001
            print(
                f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({e!s}). Tự động fallback về Mock."
            )
            return MockOfflineProvider().generate_with_tools(
                prompt, tools_schema, system_prompt
            )


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter Provider (Native Tool Calling với OpenRouter SDK)"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = (
            api_key if api_key is not None else os.getenv("OPENROUTER_API_KEY")
        )
        self.model_name = (
            model or os.getenv("LLM_MODEL") or "nvidia/nemotron-3.5-lightning:free"
        )
        self.base_url = (
            base_url
            or os.getenv("OPENROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        )

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            return "[OpenRouter Error]: Chưa cấu hình OPENROUTER_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openrouter import OpenRouter

            with OpenRouter(api_key=self.api_key, server_url=self.base_url) as client:
                messages: list[Any] = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = client.chat.send(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=500,
                    timeout_ms=25000,
                )
                if hasattr(response, "choices") and response.choices:
                    content = response.choices[0].message.content
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        return " ".join(str(c) for c in content)
                return ""
        except Exception as e:  # noqa: BLE001
            return f"[OpenRouter Exception]: {e!s}"

    def generate_with_tools(
        self, prompt: str, tools_schema: list[dict[str, Any]], system_prompt: str = ""
    ) -> dict[str, Any]:
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            print(
                "ℹ️ [OpenRouter Provider]: Chưa tìm thấy OPENROUTER_API_KEY hợp lệ. Tự động chuyển sang Mock Offline."
            )
            return MockOfflineProvider().generate_with_tools(
                prompt, tools_schema, system_prompt
            )

        try:
            from openrouter import OpenRouter

            tools: list[Any] = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool.get("parameters", {}),
                        },
                    }
                )

            messages: list[Any] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            with OpenRouter(api_key=self.api_key, server_url=self.base_url) as client:
                if tools:
                    response = client.chat.send(
                        model=self.model_name,
                        messages=messages,
                        tools=tools,
                        max_tokens=500,
                        timeout_ms=25000,
                    )
                else:
                    response = client.chat.send(
                        model=self.model_name,
                        messages=messages,
                        max_tokens=500,
                        timeout_ms=25000,
                    )

                if hasattr(response, "choices") and response.choices:
                    msg = response.choices[0].message
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        call = msg.tool_calls[0]
                        func = getattr(call, "function", None)
                        func_name = getattr(func, "name", "")
                        func_args = getattr(func, "arguments", "")
                        args = (
                            json.loads(func_args)
                            if isinstance(func_args, str) and func_args
                            else (func_args if isinstance(func_args, dict) else {})
                        )
                        return {
                            "type": "tool_call",
                            "tool_name": func_name,
                            "arguments": args,
                            "thought": f"OpenRouter quyết định gọi công cụ '{func_name}' với tham số: {json.dumps(args, ensure_ascii=False)}",
                        }
                    content = msg.content
                    content_str = (
                        content
                        if isinstance(content, str)
                        else (str(content) if content else "")
                    )
                    return {
                        "type": "text",
                        "content": content_str,
                        "thought": "OpenRouter phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
                    }
                return {
                    "type": "text",
                    "content": "",
                    "thought": "OpenRouter không trả về choices hợp lệ.",
                }
        except Exception as e:  # noqa: BLE001
            print(
                f"⚠️ [OpenRouter API Warning]: Không thể kết nối live API ({e!s}). Tự động fallback về Mock."
            )
            return MockOfflineProvider().generate_with_tools(
                prompt, tools_schema, system_prompt
            )


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider_type == "openrouter":
        key = os.getenv("OPENROUTER_API_KEY")
        if key and key != "your_openrouter_api_key_here":
            return OpenRouterProvider()
        return MockOfflineProvider()
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        return MockOfflineProvider()
    if provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        return MockOfflineProvider()
    if provider_type == "mock":
        return MockOfflineProvider()
    return MockOfflineProvider()
