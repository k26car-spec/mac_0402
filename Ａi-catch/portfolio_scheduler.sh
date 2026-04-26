#!/bin/bash

# ============================================
# 持有股票自動化排程腳本
# ============================================
# 
# 開市任務 (9:00):
#   - 模擬前幾天的分析信號
#   - 驗證分析準確性
#
# 收盤任務 (13:30):
#   - 更新所有持倉的當前價格
#   - 自動執行停損/達標
#   - 計算準確性統計
#
# 使用方式:
#   ./portfolio_scheduler.sh morning   # 開市任務
#   ./portfolio_scheduler.sh afternoon # 收盤任務
#   ./portfolio_scheduler.sh update    # 手動更新價格
#   ./portfolio_scheduler.sh status    # 查看狀態
# ============================================

cd "$(dirname "$0")"
BASE_DIR=$(pwd)

# 顏色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# 日誌檔案
LOG_FILE="$BASE_DIR/log/portfolio_automation.log"
mkdir -p "$BASE_DIR/log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

case "$1" in
    morning)
        log "🌅 開始執行開市任務..."
        cd backend-v3
        source venv/bin/activate
        python -m app.services.portfolio_automation morning 2>&1 | tee -a "$LOG_FILE"
        log "✅ 開市任務完成"
        ;;
    
    afternoon)
        log "🌇 開始執行收盤任務..."
        cd backend-v3
        source venv/bin/activate
        python -m app.services.portfolio_automation afternoon 2>&1 | tee -a "$LOG_FILE"
        log "✅ 收盤任務完成"
        ;;
    
    update)
        log "🔄 手動更新持倉價格..."
        cd backend-v3
        source venv/bin/activate
        python -m app.services.portfolio_automation update 2>&1 | tee -a "$LOG_FILE"
        log "✅ 更新完成"
        ;;
    
    simulate)
        log "🤖 手動執行模擬..."
        cd backend-v3
        source venv/bin/activate
        python -m app.services.portfolio_automation simulate 2>&1 | tee -a "$LOG_FILE"
        log "✅ 模擬完成"
        ;;
    
    status)
        echo ""
        echo -e "${BLUE}📊 持有股票自動化狀態${NC}"
        echo "========================================"
        echo ""
        
        # 檢查排程是否已設定
        if launchctl list | grep -q "com.ai-stock.portfolio"; then
            echo -e "${GREEN}✅ 排程任務已設定${NC}"
            echo ""
            echo "已設定的任務:"
            launchctl list | grep "com.ai-stock.portfolio" | while read line; do
                echo "   - $line"
            done
        else
            echo -e "${YELLOW}⚠️ 排程任務尚未設定${NC}"
            echo ""
            echo "請執行以下命令來設定排程:"
            echo "   ./portfolio_scheduler.sh install"
        fi
        echo ""
        
        # 顯示最近日誌
        if [ -f "$LOG_FILE" ]; then
            echo "最近的執行紀錄:"
            echo "----------------------------------------"
            tail -20 "$LOG_FILE"
        fi
        ;;
    
    install)
        echo -e "${BLUE}📦 安裝持有股票自動化排程...${NC}"
        
        # 創建開市任務 plist
        cat > ~/Library/LaunchAgents/com.ai-stock.portfolio-morning.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ai-stock.portfolio-morning</string>
    <key>ProgramArguments</key>
    <array>
        <string>$BASE_DIR/portfolio_scheduler.sh</string>
        <string>morning</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$BASE_DIR/log/portfolio_morning.log</string>
    <key>StandardErrorPath</key>
    <string>$BASE_DIR/log/portfolio_morning_error.log</string>
    <key>WorkingDirectory</key>
    <string>$BASE_DIR</string>
</dict>
</plist>
EOF
        
        # 創建收盤任務 plist
        cat > ~/Library/LaunchAgents/com.ai-stock.portfolio-afternoon.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ai-stock.portfolio-afternoon</string>
    <key>ProgramArguments</key>
    <array>
        <string>$BASE_DIR/portfolio_scheduler.sh</string>
        <string>afternoon</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>13</integer>
        <key>Minute</key>
        <integer>35</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$BASE_DIR/log/portfolio_afternoon.log</string>
    <key>StandardErrorPath</key>
    <string>$BASE_DIR/log/portfolio_afternoon_error.log</string>
    <key>WorkingDirectory</key>
    <string>$BASE_DIR</string>
</dict>
</plist>
EOF
        
        # 載入排程
        launchctl unload ~/Library/LaunchAgents/com.ai-stock.portfolio-morning.plist 2>/dev/null
        launchctl unload ~/Library/LaunchAgents/com.ai-stock.portfolio-afternoon.plist 2>/dev/null
        launchctl load ~/Library/LaunchAgents/com.ai-stock.portfolio-morning.plist
        launchctl load ~/Library/LaunchAgents/com.ai-stock.portfolio-afternoon.plist
        
        echo -e "${GREEN}✅ 排程安裝完成！${NC}"
        echo ""
        echo "已設定的排程:"
        echo "   📅 開市任務: 每天 09:00 執行"
        echo "   📅 收盤任務: 每天 13:35 執行"
        echo ""
        echo "查看狀態: ./portfolio_scheduler.sh status"
        ;;
    
    uninstall)
        echo -e "${YELLOW}🗑️ 移除持有股票自動化排程...${NC}"
        
        launchctl unload ~/Library/LaunchAgents/com.ai-stock.portfolio-morning.plist 2>/dev/null
        launchctl unload ~/Library/LaunchAgents/com.ai-stock.portfolio-afternoon.plist 2>/dev/null
        rm -f ~/Library/LaunchAgents/com.ai-stock.portfolio-morning.plist
        rm -f ~/Library/LaunchAgents/com.ai-stock.portfolio-afternoon.plist
        
        echo -e "${GREEN}✅ 排程已移除${NC}"
        ;;
    
    *)
        echo ""
        echo "📊 持有股票自動化排程工具"
        echo "========================================"
        echo ""
        echo "用法: ./portfolio_scheduler.sh <command>"
        echo ""
        echo "Commands:"
        echo "   morning     執行開市任務 (模擬信號)"
        echo "   afternoon   執行收盤任務 (更新價格)"
        echo "   update      手動更新持倉價格"
        echo "   simulate    手動執行模擬交易"
        echo "   status      查看排程狀態"
        echo "   install     安裝排程 (每天自動執行)"
        echo "   uninstall   移除排程"
        echo ""
        ;;
esac
