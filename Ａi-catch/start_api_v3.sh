#!/bin/bash

# 🚀 啟動 FastAPI v3.0 服務
# 使用方式: ./start_api_v3.sh

echo "🚀 啟動 AI Stock Intelligence API v3.0"
echo "======================================"
echo ""

# 檢查是否在正確的目錄
if [ ! -d "backend-v3" ]; then
    echo "❌ 錯誤: 請在專案根目錄執行此腳本"
    echo "   當前目錄: $(pwd)"
    echo "   正確目錄: /Users/Mac/Documents/ETF/AI/Ａi-catch"
    exit 1
fi

cd backend-v3

# 檢查虛擬環境
if [ ! -d "venv" ]; then
    echo "📦 創建虛擬環境..."
    python3 -m venv venv
    echo "✅ 虛擬環境創建完成"
    echo ""
fi

# 啟動虛擬環境
echo "🔧 啟動虛擬環境..."
source venv/bin/activate

# 檢查是否需要安裝依賴
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📥 安裝核心依賴..."
    pip install --quiet fastapi uvicorn[standard] websockets
    echo "✅ 依賴安裝完成"
    echo ""
fi

# 顯示信息
echo "======================================"
echo "✅ 環境準備完成！"
echo "======================================"
echo ""
echo "📡 服務信息:"
echo "   - API 端點: http://127.0.0.1:8000"
echo "   - API 文檔: http://127.0.0.1:8000/api/docs"
echo "   - 健康檢查: http://127.0.0.1:8000/health"
echo "   - WebSocket: ws://127.0.0.1:8000/ws/test"
echo ""
echo "🛑 停止服務: 按 Ctrl+C"
echo "======================================"
echo ""

# 啟動 FastAPI
export PYTHONPATH=$PYTHONPATH:$(pwd)
# 注意：--reload 不能與 --workers 同時使用。為了穩定性，盤中建議使用多 worker。
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
