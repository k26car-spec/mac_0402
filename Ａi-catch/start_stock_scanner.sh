#!/bin/bash

echo "🚀 啟動台股全市場績優股掃描器"
echo "================================="

cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 檢查 Python 環境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安裝"
    exit 1
fi

# 啟動掃描器
echo "✅ 啟動掃描程式..."
echo ""

python3 scan_market_stocks.py
