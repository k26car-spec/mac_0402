#!/bin/bash
#
# AI 股票智能分析平台 V3 停止腳本
# 停止所有服務：Backend, Frontend, 當沖戰情室, 管理頁面
#

echo "=========================================="
echo "🛑 停止 AI 股票智能分析平台 V3..."
echo "=========================================="

ROOT_DIR="/Users/Mac/Documents/ETF/AI/Ａi-catch"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 函數：停止端口服務
stop_port() {
    local port=$1
    local name=$2
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        kill -9 $pid 2>/dev/null
        echo -e "${GREEN}✅ $name (端口 $port) 已停止${NC}"
    else
        echo -e "${YELLOW}⚠️  $name (端口 $port) 未運行${NC}"
    fi
}

echo ""
echo "停止服務中..."
echo ""

# 停止 Backend API
stop_port 8000 "Backend API"

# 停止 Frontend UI
stop_port 3000 "Frontend UI"

# 停止當沖戰情室
stop_port 5173 "當沖戰情室 Pro"

# 停止管理頁面服務
stop_port 8888 "管理頁面服務"

# 清理 PID 檔案
rm -f "$ROOT_DIR/.backend.pid" "$ROOT_DIR/.frontend.pid" 2>/dev/null

echo ""
echo "=========================================="
echo -e "${GREEN}✅ 所有服務已停止${NC}"
echo "=========================================="
echo ""
echo "📋 已停止的服務:"
echo "   • Backend API (Port 8000)"
echo "   • Frontend UI (Port 3000)"
echo "   • 當沖戰情室 Pro (Port 5173)"
echo "   • 管理頁面服務 (Port 8888)"
echo ""
