#!/bin/bash
echo "🚀 啟動 AI 主力監控 Web 平台..."
echo ""

# 啟動虛擬環境
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ 虛擬環境已啟動"
fi

echo ""
echo "📊 平台網址："
echo "   本機: http://127.0.0.1:8082"

# macOS 獲取 IP 的方式
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "未知")
if [ "$LOCAL_IP" != "未知" ]; then
    echo "   區網: http://$LOCAL_IP:8082"
fi

echo ""
echo "🛑 停止平台: 按 Ctrl+C"
echo ""

python3 dashboard.py
