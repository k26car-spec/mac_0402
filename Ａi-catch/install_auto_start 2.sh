#!/bin/bash

# =====================================================
# AI 股票分析系統 - 自動啟動安裝程式
# 設定每天 08:50 自動啟動後端服務
# =====================================================

echo ""
echo "🚀 安裝 AI Stock Intelligence 自動啟動服務"
echo "============================================"
echo ""

PLIST_NAME="com.ai-stock.backend.plist"
SOURCE="/Users/Mac/Documents/ETF/AI/Ａi-catch/${PLIST_NAME}"
TARGET="$HOME/Library/LaunchAgents/${PLIST_NAME}"

# 檢查來源檔案是否存在
if [ ! -f "$SOURCE" ]; then
    echo "❌ 錯誤：找不到 ${SOURCE}"
    exit 1
fi

# 如果已經存在，先卸載
if [ -f "$TARGET" ]; then
    echo "🔄 移除舊的設定..."
    launchctl unload "$TARGET" 2>/dev/null
    rm -f "$TARGET"
fi

# 複製到 LaunchAgents
echo "📋 複製設定檔..."
cp "$SOURCE" "$TARGET"

# 設定權限
chmod 644 "$TARGET"

# 載入 LaunchAgent
echo "⚡ 載入自動啟動服務..."
launchctl load "$TARGET"

# 確認狀態
echo ""
echo "✅ 安裝完成！"
echo ""
echo "📋 服務資訊："
echo "   服務名稱：com.ai-stock.backend"
echo "   啟動時間：每天 08:50"
echo "   開機啟動：是"
echo ""
echo "📍 日誌位置："
echo "   /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/launchd.log"
echo "   /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/launchd_out.log"
echo "   /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/launchd_err.log"
echo ""

# 顯示服務狀態
echo "📊 服務狀態："
launchctl list | grep com.ai-stock || echo "   (服務已載入但尚未運行)"
echo ""

echo "============================================"
echo "🎉 設定完成！系統將在每天 08:50 自動啟動服務"
echo "============================================"
echo ""
echo "📌 常用指令："
echo "   查看狀態：launchctl list | grep ai-stock"
echo "   手動啟動：launchctl start com.ai-stock.backend"
echo "   停止服務：launchctl stop com.ai-stock.backend"  
echo "   卸載服務：launchctl unload ~/Library/LaunchAgents/com.ai-stock.backend.plist"
echo ""
