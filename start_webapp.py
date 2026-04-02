import sys
import os
import subprocess
import time
import webbrowser
import threading

def run_backend():
    print("🚀 Khởi động Backend API (FastAPI)...")
    backend_dir = os.path.join(os.path.dirname(__file__), "WebApp", "backend")
    
    # Dùng list arguments giúp quá trình được escape tốt hơn
    cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"]
    subprocess.run(cmd, cwd=backend_dir)

def run_frontend():
    print("🎨 Khởi động Frontend (Web UI)...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "WebApp", "frontend")
    
    cmd = [sys.executable, "-m", "http.server", "5173"]
    subprocess.run(cmd, cwd=frontend_dir)

if __name__ == "__main__":
    print("=============================================")
    print("🤖 Đang khởi động AutoFormBot Dashboard...")
    print("=============================================")
    
    # Cài đặt requirements cho Web API nếu chưa cài
    print("⚙️ Đang kiểm tra thư viện...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", os.path.join("WebApp", "backend", "requirements-web.txt")])
    except Exception as e:
        print(f"⚠️ Không thể cài đặt tự động requirements: {e}")
    
    # Chạy thành 2 luồng
    t1 = threading.Thread(target=run_backend, daemon=True)
    t2 = threading.Thread(target=run_frontend, daemon=True)
    
    t1.start()
    t2.start()
    
    # Chờ 2 giây để server kịp lên
    time.sleep(2)
    
    print("\n✅ Mở trình duyệt Web của bạn tại địa chỉ: http://127.0.0.1:5173")
    print("💡 Bấm Ctrl+C để thoát bất cứ lúc nào.")
    
    # Tự động mở trình duyệt
    try:
        webbrowser.open("http://127.0.0.1:5173")
    except:
        pass
        
    try:
        # Giữ luồng chính sống
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Đang tắt hệ thống. Tạm biệt!")
        sys.exit(0)
