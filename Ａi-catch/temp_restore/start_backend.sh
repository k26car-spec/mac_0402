#!/bin/bash

# =====================================================
# AI 股票分析系統 - V3.0 完整全能啟動腳本
# 整合內容：後端 API + 前端 UI + Sniper 戰情室 + 資料庫檢查
# =====================================================

# 1. 環境變數設定
ROOT_DIR="/Users/Mac/Documents/ETF/AI/Ａi-catch"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

cleanup() {
    echo -e "\n${YELLOW}🛑 正在關閉所有 AI 系統服務...${NC}"
    lsof -ti :8000,3000,5173,8888 | xargs kill -9 2>/dev/null
    echo -e "${GREEN}✅ 所有服務已安全停止${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${BLUE}🚀 啟動 AI Stock Intelligence V3 - Sniper 模式${NC}"
echo "===================================================="

# 2. 基礎設施檢查
echo -e "${CYAN}🔍 [1/5] 檢查基礎設施...${NC}"
if pg_isready -q 2>/dev/null; then
    echo -e "   ${GREEN}✓ PostgreSQL 資料庫已就緒${NC}"
else
    echo -e "   ${YELLOW}⚠️  PostgreSQL 未啟動，部分分析功能可能受限${NC}"
fi

# 3. 啟動後端 API (Port 8000)
echo -e "${CYAN}📡 [2/5] 啟動後端 V3 核心 API (Port 8000)...${NC}"
kill -9 $(lsof -ti:8000) 2>/dev/null
cd "$ROOT_DIR/backend-v3"

# 優先使用虛擬環境
if [ -d "venv" ]; then
    PYTHON_BIN="./venv/bin/python"
    echo "   ✓ 使用虛擬環境 Python"
else
    PYTHON_BIN="python3"
fi

nohup $PYTHON_BIN -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
echo -e "   ${GREEN}✅ 後端 API 啟動中 (富邦 SDK 自動連線中)${NC}"
sleep 5

# 4. 啟動前端 UI (Port 3000)
echo -e "${CYAN}🎨 [3/5] 啟動 Next.js 前端介面 (Port 3000)...${NC}"
kill -9 $(lsof -ti:3000) 2>/dev/null
cd "$ROOT_DIR/frontend-v3"
nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
echo -e "   ${GREEN}✅ V3 前端已啟動${NC}"

# 5. 啟動當沖 ORB 系統 (Port 5173 / 5174)
echo -e "${CYAN}📊 [4/5] 啟動當沖 ORB 監控 (Port 5173)...${NC}"
kill -9 $(lsof -ti:5173) 2>/dev/null
if [ -d "$ROOT_DIR/day-trading-orb" ]; then
    cd "$ROOT_DIR/day-trading-orb"
    nohup npm run dev > "$LOG_DIR/orb.log" 2>&1 &
    echo -e "   ${GREEN}✅ ORB 監控就緒${NC}"
else
    echo "   ⚠️ 找不到 day-trading-orb 目錄，跳過"
fi

# 6. 啟動管理頁面 (Port 8888)
echo -e "${CYAN}⚙️  [5/5] 啟動清單管理工具 (Port 8888)...${NC}"
kill -9 $(lsof -ti:8888) 2>/dev/null
cd "$ROOT_DIR/static"
nohup python3 -m http.server 8888 > "$LOG_DIR/static.log" 2>&1 &
echo -e "   ${GREEN}✅ 管理頁面已啟動${NC}"

# 7. 總結
clear
echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}🎉 AI Sniper 系統啟動成功！${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "📖 常用存取連結："
echo -e "   🎯 ${CYAN}V3 Sniper 戰情室:${NC}  http://localhost:3000/dashboard/sniper"
echo -e "   🏠 ${CYAN}系統首頁:${NC}          http://localhost:3000"
echo -e "   📡 ${CYAN}後端 API 文檔:${NC}     http://localhost:8000/api/docs"
echo -e "   ⚙️  ${CYAN}監控清單管理:${NC}     http://localhost:8888/orb_watchlist.html"
echo -e "${BLUE}====================================================${NC}"
echo -e "${YELLOW}💡 提示: 按 Ctrl+C 可一鍵關閉所有相關服務${NC}"
echo -e "${BLUE}====================================================${NC}"

# 監控後端日誌
tail -f "$LOG_DIR/backend.log"
