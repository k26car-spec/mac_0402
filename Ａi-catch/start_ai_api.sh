#!/bin/bash

# =====================================================
# AI 股票分析系統 v3.1 - 一鍵啟動腳本
# =====================================================

echo ""
echo "🚀 ====================================="
echo "   AI 股票分析系統 v3.1"
echo "   一鍵啟動腳本"
echo "======================================="
echo ""

# 進入後端目錄
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3

# 檢查虛擬環境
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ 已啟動虛擬環境"
else
    echo "⚠️ 虛擬環境不存在，使用系統 Python"
fi

echo ""
echo "📡 API 服務位址:"
echo "   後端 API:  http://localhost:8000"
echo "   API 文檔:  http://localhost:8000/docs"
echo ""
echo "🤖 AI 功能快速命令:"
echo ""
echo "   1. 每日掃描強勢股 (漲幅 5-10%, 量比 >1.5):"
echo '      curl -X POST "http://localhost:8000/api/watchlist/scan-strong-stocks?min_gain_pct=5&max_gain_pct=10&min_volume_ratio=1.5&limit=10"'
echo ""
echo "   2. 快速檢查某股票是否可進場:"
echo '      curl http://localhost:8000/api/entry-check/quick/2330'
echo ""
echo "   3. 查看今日觀察名單:"
echo '      curl http://localhost:8000/api/watchlist/today'
echo ""
echo "   4. 檢討所有停損交易:"
echo '      curl -X POST http://localhost:8000/api/trade-review/review-all-stopped'
echo ""
echo "   5. 查看績效統計:"
echo '      curl http://localhost:8000/api/portfolio/summary'
echo ""
echo "======================================="
echo "按 Ctrl+C 停止服務"
echo "======================================="
echo ""

# 啟動 uvicorn
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
