#!/bin/bash
#
# AI 股票智能分析平台 V3 一鍵啟動腳本 (完整版)
# 
# 使用方式: cd /Users/Mac/Documents/ETF/AI/Ａi-catch && ./start_v3.sh
#
# 更新日期: 2026-01-02
# 新增功能:
# - yfinance 上市/上櫃修補
# - FinMind API 整合
# - 新聞爬蟲備援
# - 健康檢查端點
# - 全自動選股決策引擎
# - 券商進出分析
# - 法人籌碼系統 (NEW!)
#   • 期交所期貨/選擇權法人未平倉
#   • 融資融券爬蟲
#   • 籌碼綜合分析 API
#   • 散戶情緒指標

echo "==========================================="
echo "🚀 AI 股票智能分析平台 V3.0-Fixed"
echo "==========================================="
echo ""

# 設定根目錄
ROOT_DIR="/Users/Mac/Documents/ETF/AI/Ａi-catch"
cd "$ROOT_DIR"

# 確保 logs 目錄存在
mkdir -p "$ROOT_DIR/logs"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ==================== 郵件設定 ====================
# 請填入您的郵件設定以啟用產業新聞郵件發送功能
# Gmail 用戶請使用「應用程式密碼」而非登入密碼
# 生成方式: Google 帳戶 > 安全性 > 兩步驟驗證 > 應用程式密碼

export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
# ⚠️ 請取消註解並填入您的郵件帳號密碼
# export EMAIL_USERNAME="your_email@gmail.com"
# export EMAIL_PASSWORD="your_app_password_here"
# export EMAIL_RECIPIENTS="recipient1@email.com,recipient2@email.com"


# 函數：檢查並殺掉佔用端口的進程
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}⚠️  端口 $port 已被佔用，正在釋放...${NC}"
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
}

# 函數：等待服務就緒
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=90  # 90 秒，TensorFlow 載入需要較長時間
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $name 已就緒${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    echo -e "${RED}❌ $name 啟動超時${NC}"
    return 1
}

# ===== 0. 檢查必要依賴 =====
echo -e "${BLUE}📦 檢查必要依賴...${NC}"

# 檢查 fake-useragent
python3 -c "import fake_useragent" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}🔧 安裝 fake-useragent...${NC}"
    pip3 install fake-useragent -q
fi

# 檢查 beautifulsoup4
python3 -c "from bs4 import BeautifulSoup" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}🔧 安裝 beautifulsoup4...${NC}"
    pip3 install beautifulsoup4 lxml -q
fi

echo -e "${GREEN}✅ 依賴檢查完成${NC}"

# ===== 1. 啟動 PostgreSQL (可選) =====
echo ""
echo -e "${BLUE}📦 檢查 PostgreSQL...${NC}"
if pg_isready -q 2>/dev/null; then
    echo -e "${GREEN}✅ PostgreSQL 已運行${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL 未運行 (使用簡化模式)${NC}"
fi

# ===== 2. 啟動 Backend API (Port 8000) =====
echo ""
echo -e "${BLUE}🔧 啟動 Backend API (Port 8000)...${NC}"

# 檢查 Backend 是否已經在運行
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend API 已在運行${NC}"
else
    echo -e "${YELLOW}⚠️  Backend API 未運行，正在啟動...${NC}"
    kill_port 8000
    
    cd "$ROOT_DIR/backend-v3"
    
    # 在背景啟動 Backend
    nohup /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$ROOT_DIR/logs/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo "   Backend PID: $BACKEND_PID"
    echo "$BACKEND_PID" > "$ROOT_DIR/.backend.pid"
    
    # 等待 Backend 啟動
    echo -e "${YELLOW}⏳ 等待 Backend 啟動 (約 30-60 秒)...${NC}"
    sleep 5
fi

# ===== 3. 啟動 Frontend (Port 3000) =====
echo ""
echo -e "${BLUE}🎨 啟動 Frontend (Port 3000)...${NC}"
kill_port 3000

cd "$ROOT_DIR/frontend-v3"

# 在背景啟動 Frontend
nohup npm run dev > "$ROOT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# ===== 4. 可選：啟動富邦 Bridge (Port 8003) =====
echo ""
echo -e "${BLUE}🏦 檢查富邦 Bridge...${NC}"
if [ -f "$ROOT_DIR/fubon_bridge/server.py" ]; then
    kill_port 8003
    cd "$ROOT_DIR/fubon_bridge"
    nohup python3 server.py > "$ROOT_DIR/logs/fubon.log" 2>&1 &
    FUBON_PID=$!
    echo "   Fubon Bridge PID: $FUBON_PID"
    echo "$FUBON_PID" > "$ROOT_DIR/.fubon.pid"
else
    echo -e "${YELLOW}⚠️  富邦 Bridge 未設定 (使用 Yahoo Finance)${NC}"
fi

# ===== 5. 等待服務就緒 =====
echo ""
echo -e "${BLUE}⏳ 等待服務就緒...${NC}"
sleep 3

wait_for_service "http://localhost:8000/health" "Backend API"
wait_for_service "http://localhost:3000" "Frontend"

# ===== 6. 檢查修復狀態 =====
echo ""
echo -e "${BLUE}🔍 檢查系統狀態...${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health 2>/dev/null)
if [ ! -z "$HEALTH_RESPONSE" ]; then
    echo -e "${GREEN}✅ 健康檢查 API 正常${NC}"
    
    # 檢查 yfinance 修補
    if echo "$HEALTH_RESPONSE" | grep -q "yfinance_patch.*active"; then
        echo -e "${GREEN}✅ YFinance 修補已啟用${NC}"
    else
        echo -e "${YELLOW}⚠️  YFinance 修補未啟用${NC}"
    fi
fi

# ===== 7. 顯示啟動資訊 =====
echo ""
echo "==========================================="
echo -e "${GREEN}🎉 所有服務已啟動！${NC}"
echo "==========================================="
echo ""
echo -e "${CYAN}📌 前端服務 (Port 3000)：${NC}"
echo "   • 首頁:          http://localhost:3000"
echo "   • Dashboard:     http://localhost:3000/dashboard"
echo "   • 股票分析:      http://localhost:3000/dashboard/stock-analysis"
echo "   • 訂單流分析:    http://localhost:3000/dashboard/order-flow"
echo "   • 經濟循環:      http://localhost:3000/dashboard/economic-cycle"
echo "   • 盤前選股:      http://localhost:3000/dashboard/premarket"
echo "   • 新聞分析:      http://localhost:3000/dashboard/news"
echo "   • 選股引擎:      http://localhost:3000/dashboard/stock-selector (NEW!)"
echo "   • 撐壓轉折:      http://localhost:3000/dashboard/trade-analyzer (NEW!)"
echo ""
echo -e "${CYAN}📌 後端服務 (Port 8000)：${NC}"
echo "   • API 文件:      http://localhost:8000/api/docs"
echo "   • 健康檢查:      http://localhost:8000/health"
echo "   • 即時行情:      http://localhost:8000/api/market/quotes"
echo "   • 新聞分析:      http://localhost:8000/api/news/analysis"
echo "   • 上櫃清單:      http://localhost:8000/api/stocks/otc-list"
echo "   • 選股引擎:      http://localhost:8000/api/stock-selector/health"
echo ""
echo -e "${CYAN}📌 今日更新 (2026-01-04)：${NC}"
echo "   ✅ 撐壓趨勢轉折分析系統（NEW!）"
echo "   ✅ 訂單流模式識別系統"
echo "   ✅ 全自動選股決策引擎"
echo "   ✅ 券商進出分析"
echo "   ✅ 法人籌碼系統"
echo ""
echo -e "${CYAN}📌 訂單流 API (Port 8000)：${NC}"
echo "   • 實時分析:      http://localhost:8000/api/order-flow/realtime/{symbol}"
echo "   • 模式檢測:      http://localhost:8000/api/order-flow/patterns/{symbol}"
echo "   • 準確率報告:    http://localhost:8000/api/order-flow/accuracy/report"
echo ""
echo -e "${CYAN}📌 選股引擎 API (Port 8000)：${NC}"
echo "   • 分析單股:      http://localhost:8000/api/stock-selector/analyze/2330"
echo "   • 批量分析:      http://localhost:8000/api/stock-selector/analyze/batch"
echo "   • 推薦股票:      http://localhost:8000/api/stock-selector/recommendations"
echo ""
echo -e "${CYAN}📌 智能進場系統 v2.0 API (Port 8000) [NEW!]：${NC}"
echo "   • 系統狀態:        http://localhost:8000/api/smart-entry/system-status"
echo "   • 掃描信號:        http://localhost:8000/api/smart-entry/scan"
echo "   • 掃描並交易:      http://localhost:8000/api/smart-entry/scan-and-trade"
echo "   • 評估單股:        http://localhost:8000/api/smart-entry/evaluate/{symbol}"
echo "   💡 說明: 交易時段每5分鐘自動掃描 - 4種策略評估（回檔/突破/動能/VWAP反彈）"
echo ""
echo -e "${CYAN}📌 法人籌碼 API (Port 8000) [NEW!]：${NC}"
echo "   • 籌碼綜合摘要:    http://localhost:8000/api/institutional/chip-summary"
echo "   • 期貨法人部位:    http://localhost:8000/api/institutional/futures"
echo "   • 選擇權法人部位:  http://localhost:8000/api/institutional/options"
echo "   • 市場情緒指標:    http://localhost:8000/api/institutional/market-sentiment"
echo "   • 融資融券餘額:    http://localhost:8000/api/institutional/margin-trading"
echo "   • 融資融券異常:    http://localhost:8000/api/institutional/margin-abnormal"
echo "   • 散戶情緒:        http://localhost:8000/api/institutional/retail-sentiment"
echo "   • 法人連續買賣超:  http://localhost:8000/api/institutional/continuous/{symbol}"
echo ""
echo -e "${CYAN}📌 撐壓趨勢轉折 API (Port 8000) [NEW!]：${NC}"
echo "   • 單股分析:        http://localhost:8000/api/support-resistance/analyze/{stock_code}"
echo "   • 批量分析:        http://localhost:8000/api/support-resistance/batch?stock_codes=2330,2454"
echo "   • 轉折訊號:        http://localhost:8000/api/support-resistance/reversal-signals"
echo "   • 關鍵價位:        http://localhost:8000/api/support-resistance/key-levels/{stock_code}"
echo ""
echo -e "${CYAN}📌 日誌檔案：${NC}"
echo "   • Backend:  $ROOT_DIR/logs/backend.log"
echo "   • Frontend: $ROOT_DIR/logs/frontend.log"
echo ""

# ===== 8. 選股引擎使用提示 =====
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎯 全自動選股決策引擎${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}📊 透過網頁使用選股引擎：${NC}"
echo "   http://localhost:3000/dashboard/stock-selector"
echo ""
echo -e "${CYAN}💡 或手動執行選股分析：${NC}"
echo "   cd /Users/Mac/Documents/ETF/AI/Ａi-catch"
echo "   python3 run_full_analysis.py"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}💡 按 Ctrl+C 停止所有服務${NC}"
echo ""

# 保存 PID 以便停止
echo "$BACKEND_PID" > "$ROOT_DIR/.backend.pid"
echo "$FRONTEND_PID" > "$ROOT_DIR/.frontend.pid"

# 設定 Ctrl+C 處理
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 正在停止所有服務...${NC}"
    kill_port 8000
    kill_port 3000
    kill_port 8003 2>/dev/null
    rm -f "$ROOT_DIR/.backend.pid" "$ROOT_DIR/.frontend.pid" "$ROOT_DIR/.fubon.pid"
    echo -e "${GREEN}✅ 所有服務已停止${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 保持腳本運行，監控日誌
tail -f "$ROOT_DIR/logs/backend.log" 2>/dev/null
