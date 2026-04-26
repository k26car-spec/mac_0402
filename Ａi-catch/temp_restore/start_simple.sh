#!/bin/bash
# start_simple.sh - 簡化版啟動腳本
# 直接在前景啟動 backend，避免 nohup 相關問題

cd /Users/Mac/Documents/ETF/AI/Ａi-catch

echo "🚀 AI 股票智能分析平台 - 簡化啟動"
echo "=================================="

# 清理舊進程
echo "🧹 清理舊進程..."
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 2

# 啟動 Frontend (背景)
echo "🎨 啟動 Frontend..."
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/frontend-v3
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# 啟動 Backend (前景)
echo "📦 啟動 Backend..."
echo "   (TensorFlow 載入需要 30-60 秒，請耐心等待)"
echo ""
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3

# 設置環境變數減少超時問題
export TF_CPP_MIN_LOG_LEVEL=2
export PYTHONDONTWRITEBYTECODE=1

exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
