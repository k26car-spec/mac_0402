# notifier.py - 多管道通知系統

import aiohttp
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class MultiChannelNotifier:
    """
    多管道通知器（LINE、Telegram、Email、Webhook）
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化通知器
        
        Args:
            config: 通知配置字典
        """
        self.config = config or {}
        
        # LINE Notify 設定
        self.line_token = os.getenv('LINE_NOTIFY_TOKEN') or self.config.get('line', {}).get('token')
        self.line_enabled = self.config.get('line', {}).get('enabled', False) and self.line_token
        
        # Telegram 設定
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN') or self.config.get('telegram', {}).get('bot_token')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID') or self.config.get('telegram', {}).get('chat_id')
        self.telegram_enabled = (
            self.config.get('telegram', {}).get('enabled', False) and 
            self.telegram_token and 
            self.telegram_chat_id
        )
        
        # Email 設定
        email_config = self.config.get('email', {})
        self.email_enabled = email_config.get('enabled', False)
        self.smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = email_config.get('smtp_port', 587)
        self.email_username = os.getenv('EMAIL_USERNAME') or email_config.get('username')
        self.email_password = os.getenv('EMAIL_PASSWORD') or email_config.get('password')
        self.email_recipients = email_config.get('recipients', [])
        
        # Webhook 設定
        webhook_config = self.config.get('webhook', {})
        self.webhook_enabled = webhook_config.get('enabled', False)
        self.webhook_url = webhook_config.get('url')
    
    async def send_line(self, message: str) -> bool:
        """
        發送 LINE Notify 通知
        
        Args:
            message: 訊息內容
            
        Returns:
            是否成功
        """
        if not self.line_enabled:
            logger.warning("LINE Notify 未啟用或未設定 Token")
            return False
        
        url = 'https://notify-api.line.me/api/notify'
        headers = {
            'Authorization': f'Bearer {self.line_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {'message': message}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status == 200:
                        logger.info("LINE 通知發送成功")
                        return True
                    else:
                        logger.error(f"LINE 通知發送失敗: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"LINE 通知發送錯誤: {e}")
            return False
    
    async def send_telegram(self, title: str, message: str) -> bool:
        """
        發送 Telegram 通知
        
        Args:
            title: 標題
            message: 訊息內容
            
        Returns:
            是否成功
        """
        if not self.telegram_enabled:
            logger.warning("Telegram 未啟用或未設定")
            return False
        
        url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
        
        # 格式化訊息（Markdown格式）
        formatted_message = f"**{title}**\n\n{message}"
        
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': formatted_message,
            'parse_mode': 'Markdown'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Telegram 通知發送成功")
                        return True
                    else:
                        logger.error(f"Telegram 通知發送失敗: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Telegram 通知發送錯誤: {e}")
            return False
    
    def send_email(self, subject: str, message: str) -> bool:
        """
        發送 Email 通知
        
        Args:
            subject: 主旨
            message: 訊息內容
            
        Returns:
            是否成功
        """
        if not self.email_enabled:
            logger.warning("Email 未啟用或未設定")
            return False
        
        if not self.email_recipients:
            logger.warning("未設定 Email 收件人")
            return False
        
        try:
            # 建立郵件
            msg = MIMEMultipart()
            msg['From'] = self.email_username
            msg['To'] = ', '.join(self.email_recipients)
            msg['Subject'] = subject
            
            # 郵件內容（HTML格式）
            html_message = f"""
            <html>
                <body>
                    <h2>{subject}</h2>
                    <pre>{message}</pre>
                    <hr>
                    <p><small>發送時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html_message, 'html', 'utf-8'))
            
            # 連接SMTP伺服器
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_username, self.email_password)
                server.send_message(msg)
            
            logger.info(f"Email 通知發送成功 ({len(self.email_recipients)} 位收件人)")
            return True
            
        except Exception as e:
            logger.error(f"Email 通知發送錯誤: {e}")
            return False
    
    async def send_webhook(self, data: Dict) -> bool:
        """
        發送 Webhook 通知
        
        Args:
            data: 要發送的數據
            
        Returns:
            是否成功
        """
        if not self.webhook_enabled or not self.webhook_url:
            logger.warning("Webhook 未啟用或未設定 URL")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=data) as response:
                    if response.status == 200:
                        logger.info("Webhook 通知發送成功")
                        return True
                    else:
                        logger.error(f"Webhook 通知發送失敗: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Webhook 通知發送錯誤: {e}")
            return False
    
    async def send_all(self, title: str, message: str, priority: str = 'normal', data: Dict = None):
        """
        向所有啟用的管道發送通知
        
        Args:
            title: 標題
            message: 訊息內容
            priority: 優先級 (low/normal/high)
            data: 額外數據（用於webhook）
        """
        tasks = []
        
        # LINE Notify
        if self.line_enabled:
            line_message = f"\n{title}\n{'-' * 30}\n{message}"
            tasks.append(self.send_line(line_message))
        
        # Telegram
        if self.telegram_enabled:
            tasks.append(self.send_telegram(title, message))
        
        # Email (同步執行，因為 smtplib 不是異步的)
        if self.email_enabled:
            # 在後台執行
            asyncio.create_task(asyncio.to_thread(self.send_email, title, message))
        
        # Webhook
        if self.webhook_enabled and data:
            webhook_data = {
                'title': title,
                'message': message,
                'priority': priority,
                'timestamp': datetime.now().isoformat(),
                **data
            }
            tasks.append(self.send_webhook(webhook_data))
        
        # 並發執行所有異步任務
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = sum(1 for r in results if r is True)
            logger.info(f"通知發送完成: {success_count}/{len(tasks)} 成功")
        else:
            logger.warning("沒有啟用任何通知管道")


# 使用示例
async def example_usage():
    # 配置
    config = {
        'line': {
            'enabled': True,
            'token': 'YOUR_LINE_TOKEN'
        },
        'telegram': {
            'enabled': True,
            'bot_token': 'YOUR_BOT_TOKEN',
            'chat_id': 'YOUR_CHAT_ID'
        },
        'email': {
            'enabled': True,
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': 'your_email@gmail.com',
            'password': 'YOUR_APP_PASSWORD',
            'recipients': ['recipient@example.com']
        }
    }
    
    # 建立通知器
    notifier = MultiChannelNotifier(config)
    
    # 發送通知
    await notifier.send_all(
        title="主力大單警報 - 2330.TW",
        message="偵測到主力進場，信心度: 85%",
        priority="high",
        data={'stock_code': '2330.TW', 'confidence': 0.85}
    )


if __name__ == '__main__':
    # 配置日誌
    logging.basicConfig(level=logging.INFO)
    
    # 運行示例
    asyncio.run(example_usage())
