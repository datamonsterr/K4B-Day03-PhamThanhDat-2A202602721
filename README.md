# 🏫 BÀI LAB 3: CHATBOT VS REACT AGENT — TỪ LÝ THUYẾT ĐẾN THỰC THI (MCP ENHANCED)

> **Mã bài học:** `DAY03-REACT-AGENT`  
> **Hình thức thực hiện:** **CÁ NHÂN** (`workMode: "individual"`)  
> **Họ và Tên Học viên:** **Phạm Thành Đạt**  
> **Mã Sinh Viên / Mã Học viên:** **2A202602721**  
> **Chủ đề Đề tài:** **Tác tử Quản lý Kênh Threads Thông minh 24/7 (Threads AI Management & Growth Agent)**  
> **Quy chuẩn nộp bài:** Repo cá nhân `K4B-Day03-PhamThanhDat-2A202602721`  

---

## 🌟 TỔNG QUAN HỆ THỐNG & CÁC TÍNH NĂNG ĐỘT PHÁ

Dự án phát triển một hệ thống **Tác tử ReAct Cấp độ 3 (ReAct Agent - MCP Enhanced)** toàn diện, tuân thủ chuẩn giao thức **Model Context Protocol (MCP)** của Meta Threads ([quinnjr/threads-mcp](https://github.com/quinnjr/threads-mcp)).

Bên cạnh lõi ReAct Agent Loop truyền thống, dự án được trang bị kiến trúc **Client-Server mở rộng** cùng **Giao diện Web ChatGPT-Style thời gian thực**:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│               STREAMLIT WEB CHAT UI (ChatGPT-Style, No Sidebar)             │
│  - Trạng thái Backend Online/Offline (Badge chính giữa trên cùng)           │
│  - 4 Thẻ gợi ý (Suggestion Cards) dạng ô vuông ở trung tâm khi mới mở      │
│  - Thanh điều khiển cấu hình LLM & Xóa chat/Tải trace nằm dưới prompt      │
│  - Dynamic st.status: 🧠 Thought ➔ 🛠️ Action ➔ 👁️ Observation            │
│  - Human-in-the-Loop (HITL): Approve/Reject + Trực tiếp sửa bài viết       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ 
                 POST /api/chat/stream │ (Server-Sent Events - SSE)
                 hoặc Fallback Local   │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│          STARLETTE SSE BACKEND SERVER (python src/app.py --server)          │
│  - REST Endpoints: GET /health, GET /api/tools, GET /api/test-cases         │
│  - SSE Endpoint:   POST /api/chat/stream (Real-time Event Streaming)        │
│  - Cấu hình Port từ .env (BACKEND_PORT=8000, STREAMLIT_PORT=8501)          │
│  - CORS Middleware kích hoạt cho mọi Client bên ngoài                       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│         META THREADS MCP SERVER & INTELLECTUAL TOOL EXECUTION LAYER         │
│  - Quản lý 7 công cụ chuẩn Native JSON Schema:                              │
│    + threads_get_profile, threads_get_threads, threads_get_thread           │
│    + threads_get_insights, threads_get_replies, threads_get_conversation    │
│    + threads_search (Tự động trích xuất từ khóa bằng LLM & Lọc Stopwords)  │
│    + threads_create_thread, threads_reply_to_thread (Bắt buộc duyệt HITL)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ 1. QUICKSTART — CÀI ĐẶT MÔI TRƯỜNG & KHỞI CHẠY (3 PHÚT)

> 🐍 **Yêu cầu môi trường Python:** **Python 3.10 – 3.12** *(Khuyên dùng Python 3.11 hoặc 3.12)*.

### Bước 1: Clone Repo & Thiết lập Môi trường ảo

```bash
git clone https://github.com/datamonsterr/K4B-Day03-PhamThanhDat-2A202602721.git
cd K4B-Day03-PhamThanhDat-2A202602721

python -m venv .venv

# Trên macOS / Linux / Bash / Zsh:
source .venv/bin/activate

# Trên Windows PowerShell:
.venv\Scripts\Activate.ps1
```

### Bước 2: Cài đặt Thư viện & Cấu hình Biến môi trường

```bash
pip install -r requirements.txt

# Tạo file cấu hình từ template:
cp .env.example .env
cp config/test_cases.example.json config/test_cases.json
```

Cấu hình các tham số cổng và mô hình trong tệp `.env`:
```ini
# Cấu hình Cổng máy chủ
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
MCP_SERVER_PORT=8000
STREAMLIT_PORT=8501
BACKEND_URL=http://localhost:8000

# Cấu hình LLM Provider (Hỗ trợ: openai, gemini, mock)
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=FreeBrain
OPENAI_BASE_URL=http://localhost:20128/v1
```

---

## 🚀 2. CÁC CHẾ ĐỘ CHẠY HỆ THỐNG

Dự án cung cấp 4 chế độ vận hành chuyên nghiệp phục vụ cả kiểm thử tự động, giao tiếp dòng lệnh và trải nghiệm giao diện người dùng:

### Chế độ 1: Khởi chạy Giao diện Web ChatGPT-Style (Khuyên dùng)
```bash
# Sử dụng script launcher (tự động nạp cổng từ .env):
python run_ui.py

# Hoặc khởi chạy trực tiếp bằng Streamlit:
streamlit run src/streamlit_app.py --server.port 8501
```
> Truy cập trình duyệt tại: **`http://localhost:8501`**

### Chế độ 2: Khởi chạy Backend Server (Kiến trúc Client - Server với SSE)
```bash
# Khởi chạy Starlette SSE Streaming Server trên cổng 8000:
python src/app.py --server
```
- **Kiểm tra sức khỏe hệ thống:** `curl -s http://localhost:8000/health`
- **Danh sách công cụ MCP:** `curl -s http://localhost:8000/api/tools`
- **Bộ dữ liệu kiểm thử:** `curl -s http://localhost:8000/api/test-cases`
- **Endpoint Stream sự kiện ReAct:** `POST /api/chat/stream` *(Server-Sent Events)*

### Chế độ 3: Chạy Toàn bộ 5 Test Cases Nghiệm thu (CLI Automated Evaluation)
```bash
python src/app.py --all
```
Tự động thực thi toàn bộ 5 kịch bản nghiệm thu từ `config/test_cases.json` và lưu vết suy luận vào file `docs/trace_waterfall.json`.

### Chế độ 4: Trò chuyện Dòng lệnh Trực tiếp (CLI Interactive Chat)
```bash
python src/app.py --interactive
```
Cho phép gõ lệnh tra cứu trực tiếp trên Terminal với đầy đủ hiển thị ReAct Loop. Gõ `exit` hoặc `quit` để thoát.

---

## 🎨 3. CHI TIẾT CẢI TIẾN GIAO DIỆN WEB UI (CHATGPT STYLE)

Giao diện Web Streamlit (`src/streamlit_app.py`) được thiết kế lại toàn diện theo chuẩn UI/UX hiện đại:

1. **Loại bỏ hoàn toàn Sidebar (Zero Sidebar):**  
   - Ẩn hoàn toàn khung bên trái (`[data-testid="stSidebar"] { display: none !important; }`), dành 100% không gian tập trung vào hội thoại liền mạch.
2. **Huy hiệu trạng thái Backend chính giữa trên cùng (Centered Live Status Badge):**  
   - Hiển thị rõ ràng trạng thái kết nối máy chủ:  
     🟢 `Backend Online: http://localhost:8000` (khi Starlette Server đang hoạt động)  
     🔴 `Backend Offline: Chuyển sang Local Engine` (tự động chuyển hướng không gián đoạn).
3. **4 Thẻ gợi ý câu hỏi dạng ô vuông (Centered 2x2 Suggestion Cards):**  
   - Hiển thị ở chính giữa màn hình khi hội thoại trống theo phong cách ChatGPT:  
     - 💡 *Tư vấn chiến lược Hook 3 dòng đầu (Lý thuyết - Không gọi tool)*  
     - 📊 *Tra cứu tương tác bài viết `th_post_001` (Read Tool - Tự động)*  
     - ✍️ *Đăng bài viết mới lên Threads (Write Tool - Kích hoạt HITL)*  
     - 🔥 *Tìm bài viết có nhiều lượt xem nhất (Multi-step Reasoning & Search)*  
   - Nhấp vào thẻ sẽ tự động gửi câu hỏi vào luồng xử lý.
4. **Khu vực cấu hình & điều khiển đặt ngay bên dưới khung nhập liệu:**  
   - **Bộ chọn Provider LLM:** Chuyển đổi linh hoạt giữa *OpenAI (FreeBrain)*, *Google Gemini*, và *Mock Offline*.  
   - **🗑️ Xóa hội thoại:** Làm mới phiên làm việc và xóa trạng thái tương tác treo.  
   - **📥 Tải Trace (JSON):** Tải ngay file `trace_waterfall.json` của phiên làm việc hiện tại để nộp bài hoặc đối soát.

---

## 🛡️ 4. CƠ CHẾ HUMAN-IN-THE-LOOP (HITL) & BẢO VỆ DỮ LIỆU

Hệ thống thiết lập hàng rào an toàn thông minh giữa các hành động đọc và ghi:

### 1. Phân quyền Tự động Thực thi vs Cần Phê duyệt
- **Công cụ Đọc & Tìm kiếm (`threads_search`, `threads_get_*`):** Tác tử được quyền tự do gọi ngay lập tức để lấy dữ liệu phân tích mà không làm gián đoạn trải nghiệm người dùng.
- **Công cụ Ghi / Đột biến (`threads_create_thread`, `threads_reply_to_thread`):** Tác tử **bắt buộc phải tạm dừng vòng lặp** và tạo thẻ yêu cầu phê duyệt trực tiếp.

### 2. Thẻ Tương tác Phê duyệt Thông minh (Interactive Approval Card)
Khi phát hiện yêu cầu ghi bài, giao diện hiển thị thẻ tương tác:
- **Cảnh báo màu cam** nêu rõ tên công cụ và tham số dự định gọi.
- **Khung soạn thảo trực tiếp (Editable Text Area):** Người dùng có thể đọc lại nội dung bài viết và **trực tiếp chỉnh sửa câu chữ, hashtag, link** trước khi bấm đăng!
- **Nút [✅ Phê duyệt & Thực thi]:** Tác tử nhận lại nội dung đã sửa, gọi API MCP Server xuất bản bài viết và trả về link bài đăng.
- **Nút [❌ Từ chối]:** Tác tử hủy thao tác, ghi nhận trạng thái `REJECTED_BY_USER` và phản hồi lịch sự cho người dùng.

### 3. Tương tác Hỏi - Đáp và Lựa chọn (Clarification & Choice)
- Hỗ trợ sự kiện `ask_input`: Tác tử hỏi thêm thông tin (chủ đề, hashtag, phong cách bài viết) kèm ô nhập liệu.
- Hỗ trợ sự kiện `ask_choice`: Tác tử đề xuất danh sách lựa chọn dạng radio button (`ask_user_choice`) để người dùng chọn nhanh.

---

## 🔍 5. TỰ ĐỘNG SINH TỪ KHÓA TÌM KIẾM BẰNG LLM & LỌC TRUY VẤN THÔNG MINH

Giải quyết triệt để vấn đề tìm kiếm chỉ query từ khóa cứng `"Threads"`:

1. **Chỉ dẫn System Prompt (`REACT_AGENT_SYSTEM_PROMPT`):**  
   - Tác tử được huấn luyện phân tích câu hỏi tự nhiên của người dùng để trích xuất **từ khóa nội dung cốt lõi** (ví dụ: `"AI"`, `"Hook"`, `"Marketing"`) đưa vào tham số `query` của `threads_search`.
   - Các từ ngữ chỉ tiêu chí sắp xếp (như *"nhiều view nhất"*, *"mới nhất"*) được tách riêng và đưa vào tham số `sort_by="top_views"` hoặc `sort_by="recent"`.
2. **Bộ lọc truy vấn thông minh (`_matches_threads_query` trong `src/tools.py`):**  
   - Tự động lọc bỏ các stop words tìm kiếm tiếng Việt (`tìm`, `kiếm`, `các`, `bài viết`, `nhiều view nhất`, `lượt xem`, `cao nhất`).
   - Nếu câu lệnh là câu tìm kiếm tổng quan (ví dụ: *"tìm bài viết có nhiều lượt xem nhất"*), hệ thống tự động nhận diện là truy vấn toàn bộ và sắp xếp theo lượt xem giảm dần.
   - Hỗ trợ trích xuất chính xác bài viết trên cả dữ liệu thực tế Meta Threads API và Mock Data.

---

## 🛠️ 6. DANH MỤC CÔNG CỤ MODEL CONTEXT PROTOCOL (MCP)

Tất cả công cụ được khai báo chuẩn Native JSON Schema trong `src/tools.py` và điều phối qua `MCPThreadsServer` (`src/mcp_server.py`):

| Tên Công cụ (Tool Name) | Quyền hạn | Mục đích nghiệp vụ |
| :--- | :---: | :--- |
| `threads_get_profile` | Đọc (Auto) | Lấy thông tin hồ sơ kênh (username, bio, followers_count). |
| `threads_get_threads` | Đọc (Auto) | Lấy danh sách bài đăng gần đây kèm phân trang. |
| `threads_get_thread` | Đọc (Auto) | Tra cứu chi tiết một bài viết cụ thể theo `thread_id`. |
| `threads_get_insights` | Đọc (Auto) | Tra cứu số liệu tương tác thời gian thực (views, likes, replies, reposts). |
| `threads_get_replies` | Đọc (Auto) | Đọc danh sách phản hồi/bình luận của người đọc trên bài viết. |
| `threads_get_conversation` | Đọc (Auto) | Xem toàn bộ luồng thảo luận giữa tác giả và người theo dõi. |
| `threads_search` | Đọc (Auto) | Tìm kiếm bài viết theo từ khóa và sắp xếp theo views/likes/thời gian. |
| `threads_create_thread` | **Ghi (Cần duyệt)** | Xuất bản bài viết mới lên kênh Threads (tối đa 500 ký tự). |
| `threads_reply_to_thread` | **Ghi (Cần duyệt)** | Phản hồi vào một bài viết/thảo luận cụ thể theo `thread_id`. |

---

## 🧪 7. KIỂM THỬ VÀ ĐÁNH GIÁ CHẤT LƯỢNG (TEST SUITE)

Dự án sở hữu bộ kiểm thử tự động toàn diện với **87 Unit & Smoke Tests** đạt tỷ lệ thành công 100%:

```bash
# Chạy toàn bộ test suite:
pytest -v
```

**Bảng thống kê kiểm thử:**
- `src/test_agent_stream.py`: 8 tests (Kiểm thử Event Streaming, ReAct Generator, Gating Read/Write, Resumption).
- `src/test_server.py`: 10 tests (Kiểm thử `/health`, `/api/tools`, `/api/test-cases`, SSE streaming `/api/chat/stream`, CORS).
- `tests/test_streamlit_smoke.py`: 13 tests (Kiểm thử AppTest Streamlit, nút bấm gợi ý, thẻ duyệt HITL, thẻ radio/input, fallback).
- `src/test_tools.py`: 25 tests (Kiểm thử 7 Tool Schemas, OAuth token exchange, client API thật, tìm kiếm thông minh).
- `src/test_app.py`: 5 tests (Kiểm thử Baseline Chatbot vs ReAct Agent loop).
- `src/test_prompts.py`: 8 tests (Kiểm thử phân tích chính sách duyệt, parse khối approval).
- `src/test_mcp_server.py`: 7 tests (Kiểm thử khởi tạo máy chủ MCP, đăng ký tool, dispatch tool).
- `src/test_providers.py`: 11 tests (Kiểm thử multi-provider LLM Gemini, OpenAI, OpenRouter, Mock).

---

## 📂 8. CẤU TRÚC DỰ ÁN

```text
📁 K4B-Day03-PhamThanhDat-2A202602721/
├── 📄 README.md                 <-- ⚡ Hướng dẫn cài đặt, kiến trúc hệ thống & tính năng bổ sung
├── 📄 .env.example              <-- 🔑 Mẫu cấu hình cổng & LLM API Keys
├── 📄 requirements.txt          <-- 📦 Danh sách thư viện Python
├── 📄 run_ui.py                 <-- 🚀 Launcher khởi chạy Streamlit Web UI tự nhận diện .env
├── 📁 .streamlit/
│   └── 📄 config.toml           <-- ⚙️ Cấu hình máy chủ Streamlit (headless, port 8501, CORS)
│
├── 📁 config/
│   ├── 📄 test_cases.example.json <-- 🟢 Mẫu bộ 5 kịch bản kiểm thử
│   └── 📄 test_cases.json         <-- 🟢 Bộ 5 kịch bản kiểm thử đề tài Threads Agent
│
├── 📁 src/                      <-- 💻 MÃ NGUỒN CHÍNH
│   ├── 📄 mcp_server.py         <-- 🌐 Meta Threads MCP Server & JSON-RPC Dispatcher
│   ├── 📄 tools.py              <-- 🛠️ 7 Tool Schemas JSON Schema & Query Matcher
│   ├── 📄 prompts.py            <-- 🛡️ System Prompts ReAct Agent, Chatbot Baseline & HITL Spec
│   ├── 📄 providers.py          <-- 🔌 Multi-Provider LLM Adapter (OpenAI/Gemini/Mock)
│   ├── 📄 app.py                <-- 🚀 Core ReAct Loop CLI & Starlette SSE Backend Server
│   ├── 📄 agent_stream.py       <-- ⚡ Generator Streaming ReAct Engine & HITL Gating
│   └── 📄 streamlit_app.py      <-- 📱 Giao diện Web ChatGPT-Style không Sidebar, Live Status
│
└── 📁 docs/                     <-- 📚 TÀI LIỆU BÀI LAB & NỘP BÀI
    ├── 📄 CODELAB.md            <-- 🎓 Hướng dẫn Codelab chi tiết theo các Checkpoint
    ├── 📄 trace_waterfall.json  <-- 🌊 File vết Waterfall Trace Log xuất ra từ LLM API thật
    └── 📄 trace_eval.md          <-- 📊 Báo cáo nghiệm thu bài Lab (Scoring Matrix 19/20)
```

---

## 💯 9. ĐỐI CHIẾU THANG ĐIỂM ĐÁNH GIÁ (SCORING RUBRIC 100%)

| Tiêu chí | Trọng số | Trạng thái đạt được trong dự án | Bằng chứng kiểm tra |
| :--- | :---: | :--- | :--- |
| **1. Agentic Fit & Tool Specs** | **25%** | **Đạt tối đa (5/5 sao):** Điểm Agentic Fit 19/20 với giải trình sâu sắc 4 tiêu chí. Khai báo 7 Tool Schemas chuẩn JSON Schema. | [`docs/trace_eval.md`](docs/trace_eval.md) + [`config/test_cases.json`](config/test_cases.json) + [`src/tools.py`](src/tools.py). |
| **2. ReAct Loop & MCP Integration** | **35%** | **Đạt tối đa (5/5 sao):** Vòng lặp Thought ➔ Action ➔ Observation thực thi mượt mà trên LLM API thật, kết nối MCP Server chuẩn JSON-RPC 2.0. | [`src/app.py`](src/app.py) + [`src/mcp_server.py`](src/mcp_server.py) + [`src/agent_stream.py`](src/agent_stream.py). |
| **3. Waterfall Trace & Observation** | **25%** | **Đạt tối đa (5/5 sao):** Trích xuất đầy đủ file vết `trace_waterfall.json` ghi nhận độ trễ (latency), kết quả quan sát thực tế và phân tích tại báo cáo. | [`docs/trace_waterfall.json`](docs/trace_waterfall.json) + [`docs/trace_eval.md`](docs/trace_eval.md). |
| **4. Git Repository & Submission** | **15%** | **Đạt tối đa (5/5 sao):** Lịch sử commit chỉn chu (Conventional Commits), cấu trúc repo sạch sẽ, sẵn sàng nộp link LMS VLearn. | Git commit tree & Repo URL. |
| **🎁 Điểm Thưởng Sáng tạo (Bonus)** | **+** | **Xuất sắc:** Backend Server Starlette SSE, Giao diện Web ChatGPT-Style không sidebar, cơ chế duyệt bài HITL cho phép trực tiếp chỉnh sửa nội dung bài viết trước khi xuất bản. | [`src/streamlit_app.py`](src/streamlit_app.py) + [`run_ui.py`](run_ui.py). |

---

> ✅ **HOÀN THÀNH TOÀN BỘ YÊU CẦU BÀI LAB 3:** Sẵn sàng nộp link GitHub Repository lên hệ thống LMS VLearn!
