#!/bin/bash

# =====================================================
# AI 股票分析系統 - 服務健康檢查
# 檢查所有必要的服務和依賴是否正常運行
# =====================================================

echo ""
echo "🔍 AI Stock Intelligence - 系統健康檢查"
echo "=========================================="
echo ""

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ISSUES=0

# =====================================================
# 1. 檢查端口服務
# =====================================================
echo "📡 檢查服務端口..."
echo ""

# 後端 API (8000)
if lsof -i :8000 | grep -q LISTEN; then
    echo -e "  ${GREEN}✅${NC} 後端 API (Port 8000) - 運行中"
    
    # 檢查 API 健康狀態
    if curl -s --max-time 5 "http://localhost:8000/api/big-order/status" | grep -q "online"; then
        echo -e "     ${GREEN}→${NC} API 回應正常"
    else
        echo -e "     ${YELLOW}⚠️${NC}  API 無回應或異常"
        ISSUES=$((ISSUES+1))
    fi
    
    # 檢查富邦 API
    FUBON_STATUS=$(curl -s --max-time 5 "http://localhost:8000/api/fubon/status" 2>/dev/null)
    if echo "$FUBON_STATUS" | grep -q '"connected":true'; then
        echo -e "     ${GREEN}→${NC} 富邦 API 連線成功"
    else
        echo -e "     ${YELLOW}⚠️${NC}  富邦 API 未連線（非交易時段正常）"
    fi
else
    echo -e "  ${RED}❌${NC} 後端 API (Port 8000) - 未運行"
    ISSUES=$((ISSUES+1))
fi

echo ""

# 前端 UI (3000)
if lsof -i :3000 | grep -q LISTEN; then
    echo -e "  ${GREEN}✅${NC} 前端 UI (Port 3000) - 運行中"
else
    echo -e "  ${RED}❌${NC} 前端 UI (Port 3000) - 未運行"
    ISSUES=$((ISSUES+1))
fi

echo ""

# 當沖戰情室 (5173/5174)
if lsof -i :5173 | grep -q LISTEN; then
    echo -e "  ${GREEN}✅${NC} 當沖戰情室 (Port 5173) - 運行中"
elif lsof -i :5174 | grep -q LISTEN; then
    echo -e "  ${GREEN}✅${NC} 當沖戰情室 (Port 5174) - 運行中"
else
    echo -e "  ${RED}❌${NC} 當沖戰情室 (Port 5173/5174) - 未運行"
    ISSUES=$((ISSUES+1))
fi

echo ""

# 管理頁面 (8888)
if lsof -i :8888 | grep -q LISTEN; then
    echo -e "  ${GREEN}✅${NC} 管理頁面 (Port 8888) - 運行中"
else
    echo -e "  ${YELLOW}⚠️${NC}  管理頁面 (Port 8888) - 未運行（非必要）"
fi

echo ""
echo "=========================================="

# =====================================================
# 2. 檢查資料庫連線（PostgreSQL）
# =====================================================
echo ""
echo "🗄️  檢查資料庫..."
echo ""

if command -v psql &> /dev/null; then
    if psql -U stock_admin -d stock_intelligence -c '\q' 2>/dev/null; then
        echo -e "  ${GREEN}✅${NC} PostgreSQL 連線成功"
    else
        echo -e "  ${YELLOW}⚠️${NC}  PostgreSQL 連線失敗（請確認資料庫是否啟動）"
        echo "     檢查方法: brew services list | grep postgresql"
        ISSUES=$((ISSUES+1))
    fi
else
    echo -e "  ${YELLOW}⚠️${NC}  未安裝 PostgreSQL 或未設定環境變數"
    echo "     安裝方法: brew install postgresql@14"
    ISSUES=$((ISSUES+1))
fi

echo ""
echo "=========================================="

# =====================================================
# 3. 檢查 Python 環境和依賴
# =====================================================
echo ""
echo "🐍 檢查 Python 環境..."
echo ""

PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

if $PYTHON_BIN --version &> /dev/null; then
    PYTHON_VER=$($PYTHON_BIN --version 2>&1)
    echo -e "  ${GREEN}✅${NC} Python: $PYTHON_VER"
    
    # 檢查關鍵套件
    echo ""
    echo "  檢查關鍵 Python 套件:"
    
    if $PYTHON_BIN -c "import fastapi" 2>/dev/null; then
        echo -e "     ${GREEN}✅${NC} FastAPI"
    else
        echo -e "     ${RED}❌${NC} FastAPI (缺少)"
        ISSUES=$((ISSUES+1))
    fi
    
    if $PYTHON_BIN -c "import yfinance" 2>/dev/null; then
        echo -e "     ${GREEN}✅${NC} yfinance"
    else
        echo -e "     ${RED}❌${NC} yfinance (缺少)"
        ISSUES=$((ISSUES+1))
    fi
    
    if $PYTHON_BIN -c "import pandas" 2>/dev/null; then
        echo -e "     ${GREEN}✅${NC} pandas"
    else
        echo -e "     ${RED}❌${NC} pandas (缺少)"
        ISSUES=$((ISSUES+1))
    fi
    
else
    echo -e "  ${RED}❌${NC} Python 未安裝或無法執行"
    ISSUES=$((ISSUES+1))
fi

echo ""
echo "=========================================="

# =====================================================
# 4. 檢查 Node.js 環境
# =====================================================
echo ""
echo "📦 檢查 Node.js 環境..."
echo ""

if command -v node &> /dev/null; then
    NODE_VER=$(node --version)
    echo -e "  ${GREEN}✅${NC} Node.js: $NODE_VER"
    
    if command -v npm &> /dev/null; then
        NPM_VER=$(npm --version)
        echo -e "  ${GREEN}✅${NC} npm: $NPM_VER"
    else
        echo -e "  ${RED}❌${NC} npm 未安裝"
        ISSUES=$((ISSUES+1))
    fi
else
    echo -e "  ${RED}❌${NC} Node.js 未安裝"
    echo "     安裝方法: brew install node"
    ISSUES=$((ISSUES+1))
fi

echo ""
echo "=========================================="

# =====================================================
# 5. 檢查日誌檔案
# =====================================================
echo ""
echo "📋 最近的日誌錯誤..."
echo ""

LOG_DIR="/Users/Mac/Documents/ETF/AI/Ａi-catch/logs"

if [ -d "$LOG_DIR" ]; then
    echo "  後端日誌 (最後 5 個錯誤):"
    if [ -f "$LOG_DIR/backend.log" ]; then
        tail -100 "$LOG_DIR/backend.log" | grep -i "error\|exception\|failed" | tail -5 | sed 's/^/     /'
        if [ $? -ne 0 ]; then
            echo -e "     ${GREEN}無錯誤${NC}"
        fi
    else
        echo "     (日誌檔案不存在)"
    fi
else
    echo -e "  ${YELLOW}⚠️${NC}  日誌目錄不存在: $LOG_DIR"
fi

echo ""
echo "=========================================="

# =====================================================
# 總結
# =====================================================
echo ""
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}🎉 所有檢查通過！系統運行正常${NC}"
    echo ""
    echo "📡 可用服務:"
    echo "   • 前端 UI:        http://localhost:3000"
    echo "   • 後端 API:       http://localhost:8000"
    echo "   • API 文檔:       http://localhost:8000/docs"
    echo "   • 當沖戰情室:     http://localhost:5173 或 5174"
    echo "   • 管理頁面:       http://localhost:8888/orb_watchlist.html"
else
    echo -e "${YELLOW}⚠️  發現 $ISSUES 個問題，請檢查上方輸出${NC}"
    echo ""
    echo "常見解決方法:"
    echo "  1. 啟動所有服務: ./start_backend.sh"
    echo "  2. 檢查 PostgreSQL: brew services restart postgresql@14"
    echo "  3. 重新安裝 Python 套件: cd backend-v3 && pip3 install -r requirements-v3.txt"
    echo "  4. 重新安裝 Node 套件: cd frontend-v3 && npm install"
fi

echo ""
echo "=========================================="
echo ""

exit $ISSUES
