#!/bin/bash
# 系統狀態檢查腳本

echo "🔍 AI 主力監控系統 v2.0 狀態檢查"
echo "═══════════════════════════════════════════════"
echo ""

# 檢查進程
if [ -f .monitor.pid ]; then
    PID=$(cat .monitor.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ 監控系統運行中 (PID: $PID)"
        
        # 檢查運行時間
        START_TIME=$(ps -p $PID -o lstart=)
        echo "📅 啟動時間: $START_TIME"
    else
        echo "❌ 監控系統未運行 (PID 檔案存在但進程不存在)"
    fi
else
    echo "❌ 監控系統未運行 (找不到 PID 檔案)"
fi

echo ""
echo "───────────────────────────────────────────────"
echo "📊 版本資訊"
echo "───────────────────────────────────────────────"
echo "版本: v2.0"
echo "更新日期: 2025-12-15"
echo ""
echo "✨ 新功能:"
echo "  • 換手率特徵 (15% 權重)"
echo "  • 改進大單檢測 (標準差方法)"
echo "  • 優化權重配置"
echo "  • 連續大單識別"
echo ""

echo "───────────────────────────────────────────────"
echo "📈 最近分析結果 (最後 5 筆)"
echo "───────────────────────────────────────────────"
tail -n 50 logs/stock_monitor.log | grep -E "分析|偵測到主力|未偵測到主力" | tail -10

echo ""
echo "───────────────────────────────────────────────"
echo "📋 今日警報統計"
echo "───────────────────────────────────────────────"
TODAY=$(date +"%Y-%m-%d")
ALERTS=$(grep "$TODAY" logs/stock_monitor.log | grep "🚨 偵測到主力" | wc -l | xargs)
echo "今日警報數: $ALERTS"

if [ $ALERTS -gt 0 ]; then
    echo ""
    echo "警報詳情:"
    grep "$TODAY" logs/stock_monitor.log | grep "🚨 偵測到主力"
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "💡 提示:"
echo "  • 查看完整日誌: tail -f logs/stock_monitor.log"
echo "  • 停止系統: ./stop_monitor.sh"
echo "  • Web 平台: http://127.0.0.1:8082"
echo "═══════════════════════════════════════════════"
