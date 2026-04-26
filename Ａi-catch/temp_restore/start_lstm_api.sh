#!/bin/bash

# LSTM API快速启动脚本

echo "======================================================================="
echo "🚀 LSTM Price Prediction API - 快速启动"
echo "======================================================================="
echo ""

# 检查是否在正确的目录
if [ ! -d "backend-v3" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    echo "   当前目录: $(pwd)"
    exit 1
fi

echo "📦 检查环境..."

# 检查Python虚拟环境
if [ ! -d "backend-v3/venv" ]; then
    echo "⚠️  未找到虚拟环境，创建中..."
    cd backend-v3
    python3 -m venv venv
    cd ..
fi

# 激活虚拟环境
echo "✅ 激活虚拟环境..."
source backend-v3/venv/bin/activate

# 检查TensorFlow
echo "📊 检查TensorFlow..."
python3 -c "import tensorflow" 2>/dev/null || {
    echo "⚠️  TensorFlow未安装，正在安装..."
    pip install tensorflow
}

# 检查其他依赖
echo "📦 检查依赖包..."
pip install -q fastapi uvicorn joblib scikit-learn 2>/dev/null

echo ""
echo "======================================================================="
echo "✅ 环境检查完成"
echo "======================================================================="
echo ""

# 显示可用模型
echo "📊 可用的LSTM模型:"
for model in models/lstm/*_model.h5; do
    if [ -f "$model" ]; then
        symbol=$(basename "$model" _model.h5)
        echo "   ✓ $symbol"
    fi
done

echo ""
echo "======================================================================="
echo "🚀 启动FastAPI服务器..."
echo "======================================================================="
echo ""
echo "📡 服务器地址: http://127.0.0.1:8000"
echo "📚 API文档: http://127.0.0.1:8000/api/docs"
echo "🔮 LSTM预测: http://127.0.0.1:8000/api/lstm/predict/2330"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""
echo "======================================================================="
echo ""

# 启动服务器
cd backend-v3
python3 -m app.main
