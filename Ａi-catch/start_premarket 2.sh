#!/bin/bash

# 開盤前5分鐘精準選股系統 - 快速啟動腳本

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 開盤前5分鐘精準選股系統 - 快速啟動"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 檢查當前目錄
if [ ! -f "dashboard.py" ]; then
    echo "❌ 錯誤: 請在 AI-catch 目錄下執行此腳本"
    exit 1
fi

# 顯示選單
echo "請選擇啟動模式:"
echo ""
echo "  1️⃣  完整啟動 (後端 + Dashboard)"
echo "  2️⃣  僅啟動後端 API (port 8000)"
echo "  3️⃣  僅啟動 Dashboard (port 8082)"
echo "  4️⃣  檢查系統狀態"
echo "  5️⃣  停止所有服務"
echo "  6️⃣  查看文檔"
echo ""
read -p "請輸入選項 (1-6): " choice

case $choice in
    1)
        echo ""
        echo "🚀 完整啟動模式"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # 啟動後端
        echo "📡 啟動後端 API (port 8000)..."
        cd backend-v3
        python3 -m uvicorn app.main:app --reload --port 8000 &
        BACKEND_PID=$!
        cd ..
        
        sleep 2
        
        # 啟動 Dashboard
        echo "🌐 啟動 Dashboard (port 8082)..."
        python3 dashboard.py &
        DASHBOARD_PID=$!
        
        sleep 3
        
        echo ""
        echo "✅ 系統啟動完成！"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🌐 訪問地址:"
        echo "  • Dashboard: http://127.0.0.1:8082"
        echo "  • 精準選股: http://127.0.0.1:8082/premarket"
        echo "  • API 文檔: http://127.0.0.1:8000/api/docs"
        echo ""
        echo "進程 PID:"
        echo "  • Backend: $BACKEND_PID"
        echo "  • Dashboard: $DASHBOARD_PID"
        echo ""
        echo "🛑 停止服務: ./start_premarket.sh 然後選擇 5"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # 保存 PID
        echo $BACKEND_PID > .premarket_backend.pid
        echo $DASHBOARD_PID > .premarket_dashboard.pid
        
        # 等待用戶按鍵
        echo ""
        read -p "按 Enter 鍵打開瀏覽器..."
        open http://127.0.0.1:8082/premarket
        ;;
        
    2)
        echo ""
        echo "📡 啟動後端 API"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        cd backend-v3
        python3 -m uvicorn app.main:app --reload --port 8000
        ;;
        
    3)
        echo ""
        echo "🌐 啟動 Dashboard"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        python3 dashboard.py
        ;;
        
    4)
        echo ""
        echo "📊 系統狀態檢查"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # 檢查後端
        if lsof -i :8000 > /dev/null 2>&1; then
            echo "✅ 後端 API (port 8000): 運行中"
            lsof -i :8000 | grep LISTEN
        else
            echo "❌ 後端 API (port 8000): 未運行"
        fi
        
        echo ""
        
        # 檢查 Dashboard
        if lsof -i :8082 > /dev/null 2>&1; then
            echo "✅ Dashboard (port 8082): 運行中"
            lsof -i :8082 | grep LISTEN
        else
            echo "❌ Dashboard (port 8082): 未運行"
        fi
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ;;
        
    5)
        echo ""
        echo "🛑 停止所有服務"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # 從 PID 文件停止
        if [ -f ".premarket_backend.pid" ]; then
            BACKEND_PID=$(cat .premarket_backend.pid)
            kill $BACKEND_PID 2>/dev/null && echo "✅ 停止後端 (PID: $BACKEND_PID)"
            rm .premarket_backend.pid
        fi
        
        if [ -f ".premarket_dashboard.pid" ]; then
            DASHBOARD_PID=$(cat .premarket_dashboard.pid)
            kill $DASHBOARD_PID 2>/dev/null && echo "✅ 停止 Dashboard (PID: $DASHBOARD_PID)"
            rm .premarket_dashboard.pid
        fi
        
        # 強制停止（備援）
        pkill -f "uvicorn app.main:app" && echo "✅ 停止所有 uvicorn 進程"
        pkill -f "dashboard.py" && echo "✅ 停止所有 dashboard 進程"
        
        echo ""
        echo "所有服務已停止"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ;;
        
    6)
        echo ""
        echo "📚 查看系統文檔"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [ -f "PREMARKET_SELECTION_SYSTEM.md" ]; then
            echo "✅ 找到文檔: PREMARKET_SELECTION_SYSTEM.md"
            echo ""
            read -p "是否用編輯器打開? (y/n): " open_doc
            
            if [ "$open_doc" = "y" ]; then
                if command -v code > /dev/null; then
                    code PREMARKET_SELECTION_SYSTEM.md
                elif command -v vim > /dev/null; then
                    vim PREMARKET_SELECTION_SYSTEM.md
                else
                    open PREMARKET_SELECTION_SYSTEM.md
                fi
            else
                echo ""
                echo "文檔路徑: $(pwd)/PREMARKET_SELECTION_SYSTEM.md"
            fi
        else
            echo "❌ 找不到文檔文件"
        fi
        
        echo ""
        echo "其他文檔:"
        echo "  • HOW_TO_START_V3.md - v3.0 快速啟動指南"
        echo "  • V3_QUICK_COMMANDS.md - 快速命令參考"
        echo "  • FULL_SYSTEM_ROADMAP.md - 完整系統規劃"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ;;
        
    *)
        echo "❌ 無效選項"
        exit 1
        ;;
esac

echo ""
