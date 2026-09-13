#!/usr/bin/env python3
"""
Convenience launcher for Streamlit Web UI.
Loads configuration from .env and starts the Streamlit server.
"""
import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python run_ui.py [OPTIONS]")
        print("\nKhởi chạy giao diện Streamlit Chat UI cho Threads ReAct Agent.")
        print("\nBiến môi trường (.env):")
        print("  STREAMLIT_PORT (hoặc STREAMLIT_SERVER_PORT): Cổng chạy Streamlit UI (mặc định: 8501)")
        print("  BACKEND_HOST (hoặc MCP_SERVER_HOST): Địa chỉ Backend Server (mặc định: localhost)")
        print("  BACKEND_PORT (hoặc MCP_SERVER_PORT): Cổng Backend Server (mặc định: 8000)")
        print("  BACKEND_URL: URL đầy đủ của Backend Server (mặc định: http://<BACKEND_HOST>:<BACKEND_PORT>)")
        print("\nTùy chọn:")
        print("  --help, -h   Hiển thị hướng dẫn sử dụng")
        print("  Các tham số bổ sung khác sẽ được chuyển tiếp trực tiếp sang lệnh 'streamlit run'.")
        sys.exit(0)

    streamlit_port = (
        os.getenv("STREAMLIT_PORT") or os.getenv("STREAMLIT_SERVER_PORT") or "8501"
    )
    backend_host = (
        os.getenv("BACKEND_HOST") or os.getenv("MCP_SERVER_HOST") or "localhost"
    )
    backend_port = (
        os.getenv("BACKEND_PORT") or os.getenv("MCP_SERVER_PORT") or "8000"
    )
    backend_url = os.getenv("BACKEND_URL", f"http://{backend_host}:{backend_port}")

    app_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "src", "streamlit_app.py"
    )

    print("==========================================================")
    print("🚀 THREADS REACT AGENT - STREAMLIT WEB UI LAUNCHER")
    print("==========================================================")
    print(f"📱 Streamlit Target: {app_path}")
    print(f"🔌 Streamlit Port:   {streamlit_port}")
    print(f"🌐 Backend URL:      {backend_url}")
    print("==========================================================\n")

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_path,
        "--server.port",
        str(streamlit_port),
    ] + sys.argv[1:]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Đã dừng Streamlit UI.")
    except Exception as e:
        print(f"❌ Lỗi khởi chạy Streamlit: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
