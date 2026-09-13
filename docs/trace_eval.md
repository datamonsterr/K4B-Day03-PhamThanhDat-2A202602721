# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Phạm Thành Đạt
> **Mã Sinh Viên / Mã Học viên:** 2A202602721
> **Chủ đề Lựa chọn:** nhà quản lý kênh Threads tự động, có khả năng tự tạo và
> xuất bản nội dung cũng như phản hồi các cuộc thảo luận với người dùng 24/7.
> Đồng thời, nó liên tục theo dõi các chỉ số tương tác và phân tích hội thoại để
> đề xuất chiến lược tối ưu nội dung cho bạn.

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 5 / 5 | Bài toán quản lý kênh Threads tự động đòi hỏi chuỗi tư duy ReAct đa bước phức tạp: (1) Lắng nghe và phân tích ngữ cảnh bài đăng/thảo luận của cộng đồng $\rightarrow$ (2) Đánh giá lịch sử tương tác và xu hướng nội dung (trending topics) $\rightarrow$ (3) Lên ý tưởng và biên soạn nội dung/phản hồi phù hợp với tính cách thương hiệu (brand voice) $\rightarrow$ (4) Kiểm duyệt quy chuẩn an toàn nội dung (Content Moderation / Community Guidelines) trước khi xuất bản $\rightarrow$ (5) Theo dõi hiệu suất sau đăng và tổng hợp phản hồi để đề xuất chiến lược nội dung tiếp theo. Một LLM Chatbot đơn lẻ không thể thực hiện trọn vẹn chuỗi suy luận logic nối tiếp này trong 1 lượt sinh text tĩnh. |
| **2. Tool Interaction** | 5 / 5 | Hệ thống bắt buộc phải tương tác với môi trường bên ngoài qua MCP Server / Threads Graph API: (1) Công cụ đọc dữ liệu thời gian thực (lấy danh sách mention, comment mới, chỉ số views, likes, replies, reposts) $\rightarrow$ (2) Công cụ hành động (Action Tools: `publish_thread_post` để xuất bản bài viết, `reply_to_thread` để phản hồi người dùng) $\rightarrow$ (3) Công cụ phân tích (Analytics Tools: lưu vết và truy vấn cơ sở dữ liệu số liệu tương tác). Dữ liệu này biến động liên tục theo thời gian thực 24/7, hoàn toàn nằm ngoài tri thức tĩnh của mô hình LLM. |
| **3. Dynamic Decision** | 5 / 5 | Quyết định ở bước tiếp theo của Agent phụ thuộc hoàn toàn vào kết quả quan sát (Observation) từ môi trường: Nếu bài đăng đạt tốc độ tương tác cao đột biến (viral signal) $\rightarrow$ Agent quyết định viết thêm comment bổ sung (Thread series) hoặc ghim nội dung; Nếu phát hiện bình luận tiêu cực/khiếu nại nghiêm trọng $\rightarrow$ Agent chuyển hướng sang kịch bản phản hồi xoa dịu hoặc chuyển cảnh báo cho quản trị viên con người; Nếu kết quả phân tích số liệu cho thấy định dạng bài viết ngắn có tỷ lệ thảo luận cao hơn bài viết dài $\rightarrow$ Agent tự động điều chỉnh độ dài nội dung cho các bài đăng sau. |
| **4. Long Horizon Goal** | 4 / 5 | Hệ thống hướng đến mục tiêu dài hạn: "Tối ưu hóa độ nhận diện, duy trì thảo luận liên tục 24/7 và tăng trưởng tương tác người theo dõi cho kênh Threads một cách bền vững". Để đạt mục tiêu này, Agent cần duy trì trạng thái ngữ cảnh nhất quán, quản lý bộ nhớ đệm lịch sử tương tác của người dùng quen, theo dõi biểu đồ tăng trưởng số liệu theo tuần/tháng và liên tục tinh chỉnh kế hoạch đăng bài theo thời gian. |
| **TỔNG ĐIỂM AGENTIC FIT** | **19 / 20** | *Với tổng điểm 19/20 (> 12/20), bài toán "Nhà quản lý kênh Threads tự động 24/7" hoàn toàn thỏa mãn các tiêu chuẩn cốt lõi của một Hệ thống Tác tử Thông minh (Agentic System) cấp độ 3 (ReAct Agent kết hợp giao thức MCP), vượt trội hoàn toàn so với mô hình LLM Chatbot phản hồi tĩnh Cấp độ 2.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật (OpenRouter Provider - Model: `nvidia/nemotron-3.5-lightning:free`):

```json
[
  {
    "step": 1,
    "query": "Hãy tìm cho tôi bài viết có nhiều lượt xem nhất liên quan đến chủ đề AI trên kênh",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "threads_search",
    "arguments": {
      "limit": 5,
      "query": "AI",
      "sort_by": "top_views"
    },
    "observation": {
      "status": "SUCCESS",
      "query": "AI",
      "sort_by": "top_views",
      "count": 1,
      "data": [
        {
          "id": "th_post_001",
          "text": "ReAct Agent và MCP Protocol là bước ngoặt đưa AI từ Chatbot phản hồi tĩnh sang Hệ thống Tác tử tự chủ hành động. Cùng thảo luận nhé! #VinUniAI #ReActAgent",
          "timestamp": "2026-09-12T10:00:00Z",
          "media_type": "TEXT_POST",
          "permalink": "https://www.threads.net/@vinuni_ai_hub/post/th_post_001",
          "reply_control": "everyone",
          "views": 25400,
          "likes": 1820,
          "replies": 125,
          "reposts": 88
        }
      ]
    },
    "latency_ms": 11248.37
  },
  {
    "step": 2,
    "query": "Hãy tìm cho tôi bài viết có nhiều lượt xem nhất liên quan đến chủ đề AI trên kênh",
    "action_type": "FINAL_ANSWER",
    "thought": "Tổng hợp kết quả từ MCP Server thành công.",
    "output": "Kết quả tìm kiếm cho chủ đề 'AI' (Lượt xem cao nhất):\n1. [th_post_001]: \"ReAct Agent và MCP Protocol là bước ngoặt đưa AI từ Chatbot phản hồi tĩnh sang Hệ thống Tác tử tự chủ hành động. Cùng thảo luận nhé! #VinUniAI #ReActAgent\" (25,400 Views, 1,820 Likes) - Link: https://www.threads.net/@vinuni_ai_hub/post/th_post_001",
    "latency_ms": 10.0
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (OpenRouter - nemotron-3.5-lightning:free).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 4 / 4 lượt gọi Tool (TC02: threads_get_insights, TC03: threads_create_thread, TC04: threads_search, TC05: threads_get_thread với trường hợp lỗi NOT_FOUND).
- **Kết quả đẩy Repo nộp bài:** [x] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
