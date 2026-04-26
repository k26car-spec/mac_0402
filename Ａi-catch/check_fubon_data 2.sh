#!/bin/bash
# 富邦 API 真實數據狀態檢查腳本

echo "=========================================="
echo "   🔍 富邦 API 真實數據狀態檢查"
echo "   $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 定義顏色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 檢查後端是否運行
echo "📡 檢查後端服務..."
if curl -s --max-time 5 "http://127.0.0.1:8000/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 後端服務正常運行${NC}"
else
    echo -e "${RED}❌ 後端服務未運行！請先啟動後端${NC}"
    exit 1
fi
echo ""

# 檢查富邦連接狀態
echo "🔗 檢查富邦 API 連接..."
FUBON_STATUS=$(curl -s --max-time 10 "http://127.0.0.1:8000/api/fubon/status" 2>&1)
CONNECTED=$(echo $FUBON_STATUS | grep -o '"connected":true' | wc -l)

if [ "$CONNECTED" -gt 0 ]; then
    echo -e "${GREEN}✅ 富邦 API 已連接！${NC}"
else
    echo -e "${YELLOW}⚠️ 富邦 API 未連接${NC}"
    echo "   嘗試連接..."
    curl -s -X POST "http://127.0.0.1:8000/api/fubon/connect" > /dev/null 2>&1
    sleep 2
    FUBON_STATUS=$(curl -s --max-time 10 "http://127.0.0.1:8000/api/fubon/status" 2>&1)
    CONNECTED=$(echo $FUBON_STATUS | grep -o '"connected":true' | wc -l)
    if [ "$CONNECTED" -gt 0 ]; then
        echo -e "${GREEN}✅ 富邦 API 連接成功！${NC}"
    else
        echo -e "${RED}❌ 富邦 API 連接失敗${NC}"
    fi
fi
echo ""

# 檢查報價數據
echo "📈 檢查報價數據 (2330 台積電)..."
QUOTE=$(curl -s --max-time 15 "http://127.0.0.1:8000/api/fubon/quote/2330" 2>&1)
SOURCE=$(echo $QUOTE | grep -o '"source":"[^"]*"' | cut -d'"' -f4)
PRICE=$(echo $QUOTE | grep -o '"price":[0-9.]*' | cut -d':' -f2)

echo "   數據源: $SOURCE"
echo "   當前股價: $PRICE"

if [ "$SOURCE" = "fubon" ]; then
    echo -e "${GREEN}✅ 報價來自富邦 API（真實數據）${NC}"
elif [[ "$SOURCE" == *"yahoo"* ]]; then
    echo -e "${YELLOW}⚠️ 報價來自 Yahoo Finance（回退數據源）${NC}"
else
    echo -e "${YELLOW}⚠️ 報價來自模擬數據（非交易時段）${NC}"
fi
echo ""

# 檢查五檔報價
echo "📊 檢查五檔報價..."
ORDERBOOK=$(curl -s --max-time 20 "http://127.0.0.1:8000/api/fubon/orderbook/2330" 2>&1)
OB_SOURCE=$(echo $ORDERBOOK | grep -o '"source":"[^"]*"' | cut -d'"' -f4)

echo "   數據源: $OB_SOURCE"

if [ "$OB_SOURCE" = "fubon" ] || [ "$OB_SOURCE" = "fubon_ws" ]; then
    echo -e "${GREEN}✅ 五檔來自富邦 API（真實數據）${NC}"
elif [ "$OB_SOURCE" = "mock" ]; then
    echo -e "${YELLOW}⚠️ 五檔為模擬數據（非交易時段或連接問題）${NC}"
fi
echo ""

# 檢查成交明細
echo "📋 檢查成交明細..."
TRADES=$(curl -s --max-time 20 "http://127.0.0.1:8000/api/fubon/trades/2330?count=5" 2>&1)
TR_SOURCE=$(echo $TRADES | grep -o '"source":"[^"]*"' | cut -d'"' -f4)
TR_COUNT=$(echo $TRADES | grep -o '"count":[0-9]*' | cut -d':' -f2)

echo "   數據源: $TR_SOURCE"
echo "   成交筆數: $TR_COUNT"

if [ "$TR_SOURCE" = "fubon" ]; then
    echo -e "${GREEN}✅ 成交明細來自富邦 API（真實數據）${NC}"
elif [ "$TR_SOURCE" = "mock" ]; then
    echo -e "${YELLOW}⚠️ 成交明細為模擬數據（非交易時段或連接問題）${NC}"
fi
echo ""

# 總結
echo "=========================================="
echo "   📊 數據狀態總結"
echo "=========================================="
echo ""

TODAY=$(date '+%A')
HOUR=$(date '+%H')

# 判斷是否為交易時段
IS_TRADING=0
if [[ "$TODAY" != "Saturday" && "$TODAY" != "Sunday" ]]; then
    if [[ "$HOUR" -ge 9 && "$HOUR" -lt 14 ]]; then
        IS_TRADING=1
    fi
fi

if [ $IS_TRADING -eq 1 ]; then
    echo "⏰ 當前為交易時段，應該有即時數據"
else
    echo "🌙 當前為非交易時段（收盤/假日）"
    echo "   五檔和成交明細將使用模擬數據"
    echo "   報價會回退到 Yahoo Finance"
fi
echo ""

echo "📝 API 端點一覽："
echo "   報價:     http://localhost:8000/api/fubon/quote/{symbol}"
echo "   五檔:     http://localhost:8000/api/fubon/orderbook/{symbol}"
echo "   成交明細: http://localhost:8000/api/fubon/trades/{symbol}?count=50"
echo "   連接狀態: http://localhost:8000/api/fubon/status"
echo ""

echo "🔗 詳細設定請參考: REAL_DATA_UPGRADE_GUIDE.md"
echo "=========================================="
