#!/bin/bash
# ================================================================
# 每日 AI 選股報告自動排程腳本
# 建議執行時間: 每天 20:00 (盤後分析)
# ================================================================

# 設定路徑
PROJECT_DIR="/Users/Mac/Documents/ETF/AI/Ａi-catch"
BACKEND_DIR="$PROJECT_DIR/backend-v3"
VENV_DIR="$BACKEND_DIR/venv"
LOG_DIR="$PROJECT_DIR/log"
REPORT_DIR="$PROJECT_DIR/data/daily_reports"

# 確保目錄存在
mkdir -p "$LOG_DIR"
mkdir -p "$REPORT_DIR"

# 日期
TODAY=$(date +"%Y-%m-%d")
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
LOG_FILE="$LOG_DIR/daily_report_$TODAY.log"

echo "[$TIMESTAMP] 開始執行每日 AI 選股報告..." >> "$LOG_FILE"

# 啟動虛擬環境
source "$VENV_DIR/bin/activate"

# 執行報告生成腳本
cd "$BACKEND_DIR"
python -c "
import asyncio
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# 設定環境變數路徑
import sys
sys.path.insert(0, '$BACKEND_DIR')

async def generate_and_send_report():
    print(f'[$TIMESTAMP] 載入服務...')
    
    # 導入服務
    from app.services.news_crawler_service import news_crawler
    from app.api.smart_picks import get_smart_picks, SmartPickFilters
    
    # 1. 生成新聞報告
    print('📰 正在爬取新聞...')
    news_report = await news_crawler.generate_daily_report()
    
    # 2. 生成選股報告
    print('🤖 正在進行 AI 選股分析...')
    filters = SmartPickFilters(max_price=200, min_volume=500)
    picks_report = await get_smart_picks(filters)
    
    # 3. 儲存報告
    report_file = '$REPORT_DIR/report_$TODAY.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': '$TODAY',
            'news': news_report,
            'picks': picks_report
        }, f, ensure_ascii=False, indent=2)
    print(f'💾 報告已儲存: {report_file}')
    
    # 4. 發送 Email
    send_email_report(news_report, picks_report)
    
    # 5. 關閉爬蟲 session
    await news_crawler.close()
    
    print('✅ 每日報告完成!')

def send_email_report(news_report, picks_report):
    '''發送 Email 報告'''
    
    # 讀取環境變數
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    sender_email = os.getenv('EMAIL_USERNAME') or os.getenv('SENDER_EMAIL', '')
    sender_password = os.getenv('EMAIL_PASSWORD') or os.getenv('SENDER_PASSWORD', '')
    recipients_str = os.getenv('EMAIL_RECIPIENTS') or os.getenv('RECIPIENT_EMAILS', '')
    recipients = [r.strip() for r in recipients_str.split(',') if r.strip()]
    
    if not sender_email or not sender_password or not recipients:
        print('⚠️ Email 設定不完整，跳過發送')
        return
    
    # 準備內容
    short_term = picks_report.get('short_term', [])
    mid_term = picks_report.get('mid_term', [])
    long_term = picks_report.get('long_term', [])
    
    news_themes = picks_report.get('news_report', {}).get('key_themes', [])
    market_mood = picks_report.get('market_summary', {}).get('news_sentiment', '中性')
    
    # 生成 HTML
    html = f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset=\"utf-8\"><title>每日 AI 選股報告</title></head>
    <body style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;\">
        <div style=\"background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 16px; text-align: center;\">
            <h1 style=\"margin: 0; font-size: 28px;\">🤖 每日 AI 選股報告</h1>
            <p style=\"margin: 10px 0 0; opacity: 0.9;\">{datetime.now().strftime('%Y年%m月%d日')}</p>
        </div>
        
        <div style=\"background: #f8f9fa; padding: 20px; border-radius: 12px; margin-top: 20px;\">
            <h3 style=\"margin-top: 0;\">📰 今日新聞重點</h3>
            <p>市場情緒: <strong style=\"color: #667eea;\">{market_mood}</strong></p>
            {''.join([f'<span style=\"background: #e3f2fd; color: #1976d2; padding: 4px 12px; border-radius: 20px; margin-right: 8px; display: inline-block; margin-bottom: 8px;\">{t.get(\"theme\", \"\")} ({t.get(\"news_count\", 0)}則)</span>' for t in news_themes])}
        </div>
        
        <div style=\"margin-top: 20px;\">
            <h3>⚡ 短期推薦 (1-5天)</h3>
            {''.join([f'<div style=\"background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; margin-bottom: 12px;\"><strong>{s.get(\"stock_code\", \"\")} {s.get(\"stock_name\", \"\")}</strong><br><span style=\"color: #1976d2;\">現價: ${s.get(\"price\", 0):.1f}</span> | <span style=\"color: #4caf50;\">AI評分: {s.get(\"expert_score\", 0):.0f}%</span></div>' for s in short_term[:3]]) or '<p style=\"color: #999;\">暫無符合條件的短期推薦</p>'}
        </div>
        
        <div style=\"margin-top: 20px;\">
            <h3>📊 中期推薦 (1-4週)</h3>
            {''.join([f'<div style=\"background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; margin-bottom: 12px;\"><strong>{s.get(\"stock_code\", \"\")} {s.get(\"stock_name\", \"\")}</strong><br><span style=\"color: #1976d2;\">現價: ${s.get(\"price\", 0):.1f}</span> | <span style=\"color: #4caf50;\">AI評分: {s.get(\"expert_score\", 0):.0f}%</span></div>' for s in mid_term[:3]]) or '<p style=\"color: #999;\">暫無符合條件的中期推薦</p>'}
        </div>
        
        <div style=\"margin-top: 20px;\">
            <h3>🌟 長期推薦 (1-3個月)</h3>
            {''.join([f'<div style=\"background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px; margin-bottom: 12px;\"><strong>{s.get(\"stock_code\", \"\")} {s.get(\"stock_name\", \"\")}</strong><br><span style=\"color: #1976d2;\">現價: ${s.get(\"price\", 0):.1f}</span> | <span style=\"color: #4caf50;\">AI評分: {s.get(\"expert_score\", 0):.0f}%</span></div>' for s in long_term[:3]]) or '<p style=\"color: #999;\">暫無符合條件的長期推薦</p>'}
        </div>
        
        <div style=\"background: #fff3e0; padding: 16px; border-radius: 12px; margin-top: 20px; color: #e65100;\">
            ⚠️ 投資警語: 本報告僅供參考，不構成投資建議。投資有風險，請謹慎評估。
        </div>
        
        <div style=\"text-align: center; color: #999; margin-top: 30px; font-size: 12px;\">
            AI Stock Intelligence v3.0<br>
            此為自動發送報告
        </div>
    </body>
    </html>
    '''
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'📊 每日 AI 選股報告 - {datetime.now().strftime(\"%Y/%m/%d\")}'
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())
        
        print(f'📧 Email 報告已發送至 {len(recipients)} 位收件人')
    except Exception as e:
        print(f'❌ Email 發送失敗: {e}')

# 執行
asyncio.run(generate_and_send_report())
" 2>&1 >> "$LOG_FILE"

echo "[$TIMESTAMP] 每日報告執行完成" >> "$LOG_FILE"
echo "=====================================" >> "$LOG_FILE"

# 清理超過 30 天的舊報告
find "$REPORT_DIR" -name "report_*.json" -mtime +30 -delete 2>/dev/null
find "$LOG_DIR" -name "daily_report_*.log" -mtime +30 -delete 2>/dev/null
