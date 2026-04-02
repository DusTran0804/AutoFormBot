# Khởi tạo Base Image với Python 3.10
FROM python:3.10-slim

# Thiết lập biến môi trường báo hiệu đang chạy trên Container/Linux
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Cài đặt các gói hệ thống cơ bản
RUN apt-get update && apt-get install -y \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Chuyển thư mục vào /app
WORKDIR /app

# Copy các tệp yêu cầu
COPY requirements.txt .
COPY WebApp/backend/requirements-web.txt ./requirements-web.txt

# Cài đặt thư viện Python (Kèm selenium webdriver manager)
RUN pip install --no-cache-dir -r requirements.txt -r requirements-web.txt

# Copy bộ Core (Src) và Backend (API) và Frontend
COPY Src/ ./Src/
COPY WebApp/backend/ ./WebApp/backend/
COPY WebApp/frontend/ ./WebApp/frontend/

# Khai báo port của Render
EXPOSE 8000

# Chạy máy chủ Uvicorn FastAPI
CMD ["sh", "-c", "uvicorn WebApp.backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
