#!/bin/bash
# stop_monitor.sh - 停止主力監控系統

echo "🛑 停止 AI 主力監控系統..."

# 設定顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 檢查 PID 文件
if [ -f ".monitor.pid" ]; then
    pid=$(cat .monitor.pid)
    
    # 檢查進程是否存在
    if ps -p $pid > /dev/null; then
        echo "發現運行中的監控系統 (PID: $pid)"
        
        # 發送 SIGTERM 信號
        echo "發送停止信號..."
        kill -TERM $pid
        
        # 等待進程結束
        for i in {1..10}; do
            if ! ps -p $pid > /dev/null; then
                echo -e "${GREEN}✓ 系統已正常停止${NC}"
                rm .monitor.pid
                exit 0
            fi
            echo "等待進程結束... ($i/10)"
            sleep 1
        done
        
        # 如果還沒停止，強制結束
        if ps -p $pid > /dev/null; then
            echo -e "${YELLOW}⚠️  正常停止超時，強制結束中...${NC}"
            kill -9 $pid
            rm .monitor.pid
            echo -e "${GREEN}✓ 系統已強制停止${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  進程 $pid 不存在，清理 PID 文件${NC}"
        rm .monitor.pid
    fi
else
    # 嘗試找到 Python 進程
    pid=$(ps aux | grep '[s]tock_monitor.py' | awk '{print $2}')
    
    if [ -n "$pid" ]; then
        echo "發現監控進程 (PID: $pid)"
        kill -TERM $pid
        echo -e "${GREEN}✓ 系統已停止${NC}"
    else
        echo -e "${YELLOW}⚠️  未找到運行中的監控系統${NC}"
    fi
fi

echo ""
echo "📊 最後10行日誌:"
echo "---"
tail -n 10 logs/stock_monitor.log 2>/dev/null || echo "無日誌文件"
echo "---"
