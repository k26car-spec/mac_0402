#!/bin/bash
# 快速重啟後端API服務

echo "🔄 正在重啟後端 API 服務..."

# 停止現有服務
PID=$(lsof -ti:8000)
if [ -n "$PID" ]; then
    echo "停止現有服務 (PID: $PID)..."
    kill -9 $PID 2>/dev/null
    sleep 2
fi

# 啟動後端
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3

# 檢查虛擬環境
if [ -d "venv" ]; then
    PYTHON_BIN="./venv/bin/python"
    echo "使用虛擬環境 Python"
else
    PYTHON_BIN="python3"
fi

echo "啟動後端服務..."
nohup $PYTHON_BIN -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../logs/backend_restart.log 2>&1 &

sleep 5

# 檢查是否啟動成功
if lsof -ti:8000 > /dev/null; then
    echo "✅ 後端服務已成功啟動 (Port 8000)"
    echo "📊 API文檔: http://localhost:8000/api/docs"
else
    echo "❌ 後端服務啟動失敗"
    echo "查看日誌: tail -f ../logs/backend_restart.log"
fi
