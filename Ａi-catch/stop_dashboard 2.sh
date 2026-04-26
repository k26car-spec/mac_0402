#!/bin/bash
cd "$(dirname "$0")"
if [ -f dashboard.pid ]; then
    PID=$(cat dashboard.pid)
    kill $PID 2>/dev/null
    rm dashboard.pid
    echo "✅ Web 平台已停止"
else
    pkill -f "python3 dashboard.py"
    echo "ℹ️  已嘗試停止所有 dashboard 進程"
fi
