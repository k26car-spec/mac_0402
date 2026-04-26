#!/bin/bash

echo "🚀 啟動潛力股監控儀表板"
echo "========================="

cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 檢查 Streamlit 是否已安裝
if ! command -v streamlit &> /dev/null; then
    echo "⚠️  Streamlit 未安裝，正在安裝..."
    pip3 install streamlit
fi

# 啟動 Streamlit 應用
echo "✅ 啟動儀表板..."
echo "📊 請在瀏覽器中訪問: http://localhost:8501"
echo ""

streamlit run streamlit_stock_monitor.py --server.port 8501
