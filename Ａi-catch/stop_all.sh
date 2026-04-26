#!/bin/bash

# =====================================================
# AI 股票分析系統 - 停止所有服務
# =====================================================

echo ""
echo "🛑 停止所有服務..."
echo "==================="

# 停止後端 API
if lsof -ti :8000 > /dev/null 2>&1; then
    lsof -ti :8000 | xargs kill -9 2>/dev/null
    echo "✅ 已停止後端 API (Port 8000)"
else
    echo "ℹ️  後端 API 未運行"
fi

# 停止 ORB Calculator
if lsof -ti :5173 > /dev/null 2>&1; then
    lsof -ti :5173 | xargs kill -9 2>/dev/null
    echo "✅ 已停止當沖戰情室 (Port 5173)"
else
    echo "ℹ️  當沖戰情室未運行"
fi

# 停止前端 (如果有)
if lsof -ti :3000 > /dev/null 2>&1; then
    lsof -ti :3000 | xargs kill -9 2>/dev/null
    echo "✅ 已停止前端 (Port 3000)"
fi

# 停止 Streamlit 監控儀表板
if lsof -ti :8501 > /dev/null 2>&1; then
    lsof -ti :8501 | xargs kill -9 2>/dev/null
    echo "✅ 已停止 Streamlit 監控儀表板 (Port 8501)"
else
    echo "ℹ️  Streamlit 儀表板未運行"
fi

# 停止管理頁面
if lsof -ti :8888 > /dev/null 2>&1; then
    lsof -ti :8888 | xargs kill -9 2>/dev/null
    echo "✅ 已停止管理頁面 (Port 8888)"
fi

echo ""
echo "🎉 所有服務已停止"
echo ""
