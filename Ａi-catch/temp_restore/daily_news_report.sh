#!/bin/bash

# ============================================
# 每日產業新聞報告排程腳本
# 每天 09:00 執行，生成 PDF 並發送郵件
# ============================================

cd "$(dirname "$0")"
BASE_DIR=$(pwd)

# 載入環境變數
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export EMAIL_USERNAME="${EMAIL_USERNAME:-k26car@gmail.com}"
export EMAIL_PASSWORD="${EMAIL_PASSWORD:-zrgogmielnvpykrv}"
export EMAIL_RECIPIENTS="${EMAIL_RECIPIENTS:-k26car@gmail.com,neimou1225@gmail.com}"
export SMTP_SERVER="${SMTP_SERVER:-smtp.gmail.com}"
export SMTP_PORT="${SMTP_PORT:-587}"

LOG_FILE="$BASE_DIR/log/daily_news_report.log"
mkdir -p "$BASE_DIR/log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "📰 開始執行每日新聞報告排程"
log "=========================================="

# 啟用虛擬環境
cd "$BASE_DIR/backend-v3"
source venv/bin/activate

# 執行報告生成與發送
python3 -c "
import sys
import os
sys.path.insert(0, '$BASE_DIR/backend-v3')

# 設定環境變數
os.environ['EMAIL_USERNAME'] = '$EMAIL_USERNAME'
os.environ['EMAIL_PASSWORD'] = '$EMAIL_PASSWORD'
os.environ['EMAIL_RECIPIENTS'] = '$EMAIL_RECIPIENTS'
os.environ['SMTP_SERVER'] = '$SMTP_SERVER'
os.environ['SMTP_PORT'] = '$SMTP_PORT'

from app.services.news_report_generator import generate_daily_news_report, send_daily_news_email

print('📊 正在抓取最新產業新聞...')

# 生成報告
report = generate_daily_news_report()

if report['success']:
    print(f'✅ 報告生成成功')
    print(f'   日期: {report[\"date\"]}')
    print(f'   PDF: {report[\"pdf_path\"]}')
    print()
    
    # 顯示重點
    summary = report['summary']
    print('📈 今日關注股票:')
    for stock in summary['investment_focus'][:5]:
        print(f'   • {stock[\"symbol\"]} {stock[\"name\"]}: {stock[\"action\"]}')
    
    print()
    print('📧 正在發送郵件...')
    
    # 發送郵件
    email_result = send_daily_news_email()
    
    if email_result['success']:
        print(f'✅ 郵件發送成功')
        print(f'   收件人: {\", \".join(email_result[\"recipients\"])}')
    else:
        print(f'❌ 郵件發送失敗: {email_result.get(\"error\", \"未知錯誤\")}')
else:
    print('❌ 報告生成失敗')
    sys.exit(1)
" 2>&1 | tee -a "$LOG_FILE"

log "=========================================="
log "📰 每日新聞報告排程完成"
log "=========================================="
