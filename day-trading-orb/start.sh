#!/bin/bash
# 當沖戰情室啟動腳本

echo "🚀 啟動當沖戰情室..."

# 啟動後端 API
echo "📡 啟動後端 API (port 8000)..."
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 等待後端啟動
sleep 5

# 啟動前端
echo "🌐 啟動前端應用 (port 5173)..."
cd /Users/Mac/Documents/ETF/AI/day-trading-orb
npm run dev &
FRONTEND_PID=$!

# 等待前端啟動
sleep 3

echo ""
echo "✅ 當沖戰情室已啟動！"
echo ""
echo "📊 前端網址: http://localhost:5173/"
echo "📡 API 文件: http://localhost:8000/api/docs"
echo ""
echo "按 Ctrl+C 停止所有服務"

# 等待用戶按 Ctrl+C
wait
