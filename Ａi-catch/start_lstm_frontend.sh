#!/bin/bash

# LSTM前端集成快速启动脚本

echo "======================================================================="
echo "🚀 LSTM前端集成快速启动"
echo "======================================================================="
echo ""

# 检查当前目录
if [ ! -d "frontend-v3" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

echo "步骤 1/3: 检查API服务..."
echo "-----------------------------------------------------------------------"

# 检查API是否运行
if curl -s http://127.0.0.1:8000/api/lstm/health > /dev/null 2>&1; then
    echo "✅ API服务已运行"
else
    echo "⚠️  API服务未运行，正在启动..."
    ./start_lstm_api.sh &
    sleep 5
    
    if curl -s http://127.0.0.1:8000/api/lstm/health > /dev/null 2>&1; then
        echo "✅ API服务启动成功"
    else
        echo "❌ API服务启动失败，请手动运行: ./start_lstm_api.sh"
        exit 1
    fi
fi

echo ""
echo "步骤 2/3: 检查前端依赖..."
echo "-----------------------------------------------------------------------"

cd frontend-v3

# 检查node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    npm install
fi

# 检查lucide-react
if ! npm list lucide-react > /dev/null 2>&1; then
    echo "📦 安装lucide-react..."
    npm install lucide-react
fi

echo "✅ 依赖检查完成"

echo ""
echo "步骤 3/3: 启动前端服务..."
echo "-----------------------------------------------------------------------"

echo ""
echo "======================================================================="
echo "✅ 准备就绪！"
echo "======================================================================="
echo ""
echo "🌐 前端将在以下地址启动:"
echo "   http://localhost:3000"
echo ""
echo "📊 LSTM预测页面:"
echo "   http://localhost:3000/lstm"
echo ""
echo "🔌 API服务:"
echo "   http://127.0.0.1:8000/api/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo "======================================================================="
echo ""

# 启动前端开发服务器
npm run dev
