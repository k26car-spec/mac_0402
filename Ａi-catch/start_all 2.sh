#!/bin/bash

# =====================================================
# AI 股票分析系統 - 全部啟動腳本
# 一次啟動所有服務：後端 + 前端 + 當沖 ORB
# =====================================================

echo ""
echo "🚀 ====================================="
echo "   AI 股票分析系統"
echo "   全部服務啟動腳本"
echo "======================================="
echo ""

# 建立 logs 目錄
mkdir -p /Users/Mac/Documents/ETF/AI/Ａi-catch/logs

# 釋放所有端口
echo "🔄 釋放端口..."
lsof -ti :8000 | xargs kill -9 2>/dev/null
lsof -ti :3000 | xargs kill -9 2>/dev/null
lsof -ti :3001 | xargs kill -9 2>/dev/null
lsof -ti :5173 | xargs kill -9 2>/dev/null
lsof -ti :5174 | xargs kill -9 2>/dev/null
sleep 2

# ===== 1. 啟動後端 API =====
echo "📡 啟動後端 API..."
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
if [ -d "venv" ]; then
    source venv/bin/activate
fi
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ 後端 API 已啟動 (PID: $BACKEND_PID)"
echo "   URL: http://localhost:8000"

sleep 3

# ===== 2. 啟動主前端 (frontend-v3) =====
echo ""
echo "🖥️  啟動主前端 (frontend-v3)..."
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/frontend-v3
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ 主前端已啟動 (PID: $FRONTEND_PID)"
echo "   URL: http://localhost:3000"

sleep 2

# ===== 3. 啟動當沖 ORB 系統 =====
echo ""
echo "📊 啟動當沖 ORB 系統 (day-trading-orb)..."
cd /Users/Mac/Documents/ETF/AI/day-trading-orb
npm run dev > /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/orb.log 2>&1 &
ORB_PID=$!
echo "✅ 當沖 ORB 系統已啟動 (PID: $ORB_PID)"
echo "   URL: http://localhost:5174"

# 保存 PID 到檔案
echo "$BACKEND_PID" > /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/pids.txt
echo "$FRONTEND_PID" >> /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/pids.txt
echo "$ORB_PID" >> /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/pids.txt

# ===== 總結 =====
echo ""
echo "======================================="
echo "🎉 所有服務已啟動！"
echo "======================================="
echo ""
echo "📋 服務列表:"
echo "   🔹 後端 API:      http://localhost:8000"
echo "   🔹 API 文檔:      http://localhost:8000/docs"
echo "   🔹 主前端:        http://localhost:3000"
echo "   🔹 當沖 ORB:      http://localhost:5174"
echo ""
echo "📌 進程 ID:"
echo "   後端 API:     $BACKEND_PID"
echo "   主前端:       $FRONTEND_PID"
echo "   當沖 ORB:     $ORB_PID"
echo ""
echo "📁 日誌檔案:"
echo "   後端: logs/backend.log"
echo "   前端: logs/frontend.log"
echo "   ORB:  logs/orb.log"
echo ""
echo "🛑 停止所有服務: ./stop_all.sh"
echo "======================================="
