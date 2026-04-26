#!/bin/bash
# 智能進場系統 - 每日操作腳本
# 用法: ./start_smart_trading.sh

echo "==========================================="
echo "🤖 智能進場系統 v2.0"
echo "==========================================="
echo ""

cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 檢查後端是否已啟動
check_backend() {
    curl -s http://localhost:8000/health > /dev/null 2>&1
    return $?
}

# 啟動後端
start_backend() {
    echo "🚀 啟動後端服務..."
    cd backend-v3
    source venv/bin/activate
    uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    sleep 5
    cd ..
}

# 掃描並建倉
scan_and_trade() {
    echo ""
    echo "📊 掃描股票信號..."
    result=$(curl -s -X POST http://localhost:8000/api/smart-entry/smart-system/scan-and-trade)
    
    signals=$(echo $result | python3 -c "import sys,json; print(json.load(sys.stdin).get('signals_found', 0))")
    positions=$(echo $result | python3 -c "import sys,json; print(json.load(sys.stdin).get('positions_opened', 0))")
    
    echo "✅ 發現信號: $signals 個"
    echo "✅ 建倉數量: $positions 筆"
    echo ""
}

# 查看持倉
show_positions() {
    echo "📋 今日持倉:"
    curl -s "http://localhost:8000/api/portfolio/positions?status=open" | python3 -c "
import sys, json
try:
    positions = json.load(sys.stdin)
    for p in positions[-10:]:
        print(f\"  {p['symbol']} {p.get('stock_name', '')} @ \${p['entry_price']} | 停損 \${p.get('stop_loss_price', 'N/A')}\")
except:
    print('  無法獲取持倉')
"
}

# 主程式
main() {
    if ! check_backend; then
        echo "⚠️ 後端未啟動"
        read -p "要啟動後端嗎? (y/n): " answer
        if [ "$answer" = "y" ]; then
            start_backend
        else
            exit 1
        fi
    else
        echo "✅ 後端已運行"
    fi
    
    echo ""
    echo "請選擇操作:"
    echo "1. 掃描並建倉"
    echo "2. 查看持倉"
    echo "3. 重置信號（重新掃描）"
    echo "4. 退出"
    echo ""
    
    read -p "選擇 (1-4): " choice
    
    case $choice in
        1)
            scan_and_trade
            show_positions
            ;;
        2)
            show_positions
            ;;
        3)
            curl -s -X POST http://localhost:8000/api/smart-entry/smart-system/reset
            echo "✅ 已重置"
            scan_and_trade
            ;;
        4)
            exit 0
            ;;
        *)
            echo "無效選擇"
            ;;
    esac
}

main
