"""
📚 [REFERENCE ONLY / CODE MẪU THAM KHẢO]
🧠 CẤP ĐỘ 3: NATIVE MCP AGENT (Native Tool Calling + MCP Server Integration)
⚠️ Lưu ý: File này chỉ dùng để đọc tham khảo kiến trúc. Không chỉnh sửa hay debug file này.
"""


def get_weather(city: str) -> str:
    return f"Thời tiết {city}: 28°C, Nắng nhẹ."


def run_level3_demo():
    print("=== DEMO CẤP ĐỘ 3: NATIVE MCP AGENT ===")
    user_goal = "Tra cứu thông tin học vụ sinh viên SV2026001"
    print(f"🎯 Goal: {user_goal}")
    print("🧠 [Thought]: Phát sinh Native Tool Call 'academic_query'...")
    print("🛠️ [Native Tool Call]: academic_query({'student_id': 'SV2026001'})")
    print(
        "👁️ [MCP Server Observation]: {'student_id': 'SV2026001', 'name': 'Nguyễn Văn An', 'gpa': 3.85}"
    )
    print("🏁 [Final Answer]: Học viên Nguyễn Văn An (SV2026001) đạt GPA 3.85.")


if __name__ == "__main__":
    run_level3_demo()
