# 使用 Python 3.9 Slim 映像
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴 (如果需要)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴檔案
COPY requirements.txt .
COPY fubon_neo-2.2.5-cp37-abi3-macosx_10_12_x86_64.whl .

# 安裝 Python 依賴
# 注意：先安裝 wheel 檔案，再安裝其他依賴
RUN pip install --no-cache-dir fubon_neo-2.2.5-cp37-abi3-macosx_10_12_x86_64.whl
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 暴露端口
EXPOSE 8000

# 啟動命令
CMD ["python", "main.py"]
