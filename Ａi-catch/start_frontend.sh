#!/bin/bash

# =====================================================
# AI 股票分析系統 - 前端啟動腳本
# 同時啟動 frontend-v3 和 day-trading-orb
# =====================================================

echo ""
echo "🖥️  啟動前端服務"
echo "=================================="

# 建立 logs 目錄
mkdir -p /Users/Mac/Documents/ETF/AI/Ａi-catch/logs

# 釋放可能佔用的端口
echo "🔄 釋放端口..."
lsof -ti :3000 | xargs kill -9 2>/dev/null
lsof -ti :3001 | xargs kill -9 2>/dev/null
lsof -ti :5173 | xargs kill -9 2>/dev/null
lsof -ti :5174 | xargs kill -9 2>/dev/null
sleep 1

# ===== 1. 啟動主前端 (frontend-v3) =====
echo ""
echo "🚀 啟動主前端 (frontend-v3)..."
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/frontend-v3
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ 主前端已啟動 (PID: $FRONTEND_PID)"

sleep 3

# ===== 2. 啟動當沖 ORB 系統 =====
echo ""
echo "📊 啟動當沖 ORB 系統 (day-trading-orb)..."
cd /Users/Mac/Documents/ETF/AI/day-trading-orb
npm run dev > /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/orb.log 2>&1 &
ORB_PID=$!
echo "✅ 當沖 ORB 系統已啟動 (PID: $ORB_PID)"

# 保存 PID
echo "$FRONTEND_PID" > /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/frontend_pids.txt
echo "$ORB_PID" >> /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/frontend_pids.txt

sleep 3

# ===== 總結 =====
echo ""
echo "=================================="
echo "🎉 前端服務已啟動！"
echo "=================================="
echo ""
echo "📋 服務列表:"
echo "   🔹 主前端:        http://localhost:3000"
echo "   🔹 當沖 ORB:      http://localhost:5174 (或 5173)"
echo ""
echo "📁 日誌檔案:"
echo "   主前端: logs/frontend.log"
echo "   ORB:    logs/orb.log"
echo ""
echo "🛑 停止服務: kill $FRONTEND_PID $ORB_PID"
echo "=================================="

# 保持腳本運行 (可選)
# wait
