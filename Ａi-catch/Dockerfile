# Dockerfile - Docker 容器化部署

FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 設定時區為台北
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    sqlite3 \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY . .

# 建立必要目錄
RUN mkdir -p logs data models

# 設定權限
RUN chmod +x start_monitor.sh stop_monitor.sh

# 健康檢查
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import sqlite3; conn = sqlite3.connect('data/stock_monitor.db'); conn.close()" || exit 1

# 暴露端口（如果有Web介面）
# EXPOSE 8000

# 啟動命令
CMD ["python3", "stock_monitor.py"]
