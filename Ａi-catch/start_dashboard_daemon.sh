#!/bin/bash
cd "$(dirname "$0")"
nohup python3 dashboard.py > logs/dashboard.log 2>&1 &
PID=$!
echo $PID > dashboard.pid
echo "✅ Web 平台已啟動 (PID: $PID)"
echo "📊 網址: http://127.0.0.1:5000"
echo "📝 日誌: logs/dashboard.log"
