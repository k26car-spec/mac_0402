
import asyncio
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 模擬導入相關模組
from notifier import MultiChannelNotifier
from stock_names import get_stock_name, get_full_name

async def send_manual_alert():
    print("🚀 準備發送手動警報測試...")
    
    # 1. 準備配置
    config = {
        'email': {
            'enabled': True,
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            # 從環境變數讀取
            'username': os.getenv('EMAIL_USERNAME'),
            'password': os.getenv('EMAIL_PASSWORD'),
            'recipients': ['k26car@gmail.com', 'neimou1225@gmail.com']
        }
    }
    
    # 2. 初始化通知器
    notifier = MultiChannelNotifier(config)
    
    # 3. 設定要測試的股票
    stock_code = "5521.TW"  # 或 "5521"
    confidence = 0.9234
    
    # 4. 獲取中文名稱 (這是關鍵步驟！)
    stock_name = get_stock_name(stock_code)
    full_name = get_full_name(stock_code)
    print(f"✅ 獲取到名稱: {stock_code} -> {full_name}")
    
    # 5. 構建訊息 (複製 stock_monitor.py 的格式)
    message = f"""
🚨 **主力大單警報 (手動測試)** 🚨

📈 股票: {full_name}
⭐ 信心指數: {confidence:.2%}
🕒 時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 關鍵特徵 (模擬數據):
• 量能比率: 2.5
• 大單比例: 15.3%
• 資金流向: 5000.00
• 法人追蹤: 120.50
• 型態突破: 100.00%

🔗 快速連結:
• Yahoo主力: https://tw.stock.yahoo.com/quote/{stock_code}/agent
• 富邦分析: https://www.fubon.com/stock/{stock_code}
    """
    
    # 檢查環境變數
    email_user = os.getenv('EMAIL_USERNAME')
    if not email_user:
        print("❌ 錯誤：未讀取到 EMAIL_USERNAME 環境變數，請確認 .env 存在")
        return

    # 6. 發送
    print(f"📤 正在發送 Email 到: {config['email']['recipients']} ...")
    await notifier.send_all(
        title=f"主力大單警報 - {full_name}",
        message=message.strip(),
        priority="high"
    )
    
    # 7. 等待 Email 發送完成
    print("⏳ 等待發送運作...")
    await asyncio.sleep(5)  # 等待 5 秒讓背景任務完成
    print("✅ 發送程序結束")

if __name__ == "__main__":
    asyncio.run(send_manual_alert())
