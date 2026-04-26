"""
多管道通知系統
支援 Telegram, Email, Line Notify
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from typing import Dict, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod
import os

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """通知管道抽象基類"""
    
    @abstractmethod
    def send(self, message: str, **kwargs) -> bool:
        pass


class TelegramNotifier(NotificationChannel):
    """Telegram 通知器"""
    
    def __init__(self, bot_token: str = None, chat_ids: List[str] = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_ids = chat_ids or os.getenv('TELEGRAM_CHAT_IDS', '').split(',')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send(self, message: str, parse_mode: str = 'HTML', **kwargs) -> bool:
        if not self.bot_token:
            logger.warning("Telegram bot token 未設定")
            return False
        
        success_count = 0
        
        for chat_id in self.chat_ids:
            if not chat_id.strip():
                continue
            try:
                url = f"{self.api_url}/sendMessage"
                payload = {
                    'chat_id': chat_id.strip(),
                    'text': message,
                    'parse_mode': parse_mode,
                    'disable_web_page_preview': True
                }
                
                response = requests.post(url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    success_count += 1
                    logger.info(f"Telegram 訊息已發送至 {chat_id}")
                else:
                    logger.error(f"Telegram 發送失敗: {response.text}")
                    
            except Exception as e:
                logger.error(f"Telegram 發送異常: {e}")
        
        return success_count > 0
    
    def send_photo(self, photo_path: str, caption: str = "") -> bool:
        if not self.bot_token or not self.chat_ids:
            return False
        
        for chat_id in self.chat_ids:
            if not chat_id.strip():
                continue
            try:
                url = f"{self.api_url}/sendPhoto"
                
                with open(photo_path, 'rb') as photo:
                    files = {'photo': photo}
                    data = {
                        'chat_id': chat_id.strip(),
                        'caption': caption,
                        'parse_mode': 'HTML'
                    }
                    
                    response = requests.post(url, files=files, data=data, timeout=30)
                    
                    if response.status_code == 200:
                        logger.info(f"Telegram 圖片已發送至 {chat_id}")
                        return True
                    
            except Exception as e:
                logger.error(f"Telegram 圖片發送異常: {e}")
        
        return False


class EmailNotifier(NotificationChannel):
    """Email 通知器"""
    
    def __init__(self, 
                 smtp_server: str = None,
                 smtp_port: int = None,
                 sender_email: str = None,
                 sender_password: str = None,
                 recipient_emails: List[str] = None):
        
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = sender_email or os.getenv('EMAIL_USERNAME', '')
        self.sender_password = sender_password or os.getenv('EMAIL_PASSWORD', '')
        self.recipient_emails = recipient_emails or os.getenv('EMAIL_RECIPIENTS', '').split(',')
    
    def send(self, message: str, subject: str = "交易系統通知", **kwargs) -> bool:
        if not self.sender_email or not self.sender_password:
            logger.warning("Email 認證資訊未設定")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = ', '.join([e.strip() for e in self.recipient_emails if e.strip()])
            msg['Subject'] = subject
            
            html_message = kwargs.get('html', None)
            if html_message:
                msg.attach(MIMEText(html_message, 'html', 'utf-8'))
            else:
                html = f"<html><body><pre>{message}</pre></body></html>"
                msg.attach(MIMEText(html, 'html', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Email 已發送至 {len(self.recipient_emails)} 位收件人")
            return True
            
        except Exception as e:
            logger.error(f"Email 發送失敗: {e}")
            return False


class LineNotifier(NotificationChannel):
    """Line Notify 通知器"""
    
    def __init__(self, access_token: str = None):
        self.access_token = access_token or os.getenv('LINE_NOTIFY_TOKEN', '')
        self.api_url = "https://notify-api.line.me/api/notify"
    
    def send(self, message: str, **kwargs) -> bool:
        if not self.access_token:
            logger.warning("Line Notify token 未設定")
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            payload = {'message': message}
            
            response = requests.post(
                self.api_url,
                headers=headers,
                data=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Line 訊息已發送")
                return True
            else:
                logger.error(f"Line 發送失敗: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Line 發送異常: {e}")
            return False


class NotificationManager:
    """通知管理器（統一管理所有通知管道）"""
    
    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {}
        self.notification_history = []
        self._auto_register_channels()
    
    def _auto_register_channels(self):
        """自動註冊可用的通知管道"""
        
        # Telegram
        if os.getenv('TELEGRAM_BOT_TOKEN'):
            self.register_channel('telegram', TelegramNotifier())
            logger.info("已自動註冊 Telegram 通知")
        
        # Email
        if os.getenv('EMAIL_USERNAME'):
            self.register_channel('email', EmailNotifier())
            logger.info("已自動註冊 Email 通知")
        
        # Line
        if os.getenv('LINE_NOTIFY_TOKEN'):
            self.register_channel('line', LineNotifier())
            logger.info("已自動註冊 Line 通知")
    
    def register_channel(self, name: str, channel: NotificationChannel):
        """註冊通知管道"""
        self.channels[name] = channel
        logger.info(f"已註冊通知管道: {name}")
    
    def send_to_all(self, message: str, **kwargs) -> Dict[str, bool]:
        """發送到所有管道"""
        
        results = {}
        
        for name, channel in self.channels.items():
            try:
                success = channel.send(message, **kwargs)
                results[name] = success
            except Exception as e:
                logger.error(f"管道 {name} 發送失敗: {e}")
                results[name] = False
        
        self.notification_history.append({
            'timestamp': datetime.now(),
            'message': message[:100],
            'results': results
        })
        
        return results
    
    def send_to_channel(self, channel_name: str, message: str, **kwargs) -> bool:
        """發送到指定管道"""
        
        if channel_name not in self.channels:
            logger.warning(f"管道 {channel_name} 不存在")
            return False
        
        return self.channels[channel_name].send(message, **kwargs)
    
    def format_signal_notification(self, signal_data: Dict, decision: Dict) -> str:
        """格式化訊號通知"""
        
        decision_emoji = "✅" if decision.get('decision') == 'ALLOW' else "❌"
        decision_text = "建議進場" if decision.get('decision') == 'ALLOW' else "建議觀望"
        
        message = f"""
<b>{decision_emoji} {decision_text}</b>

📊 <b>股票資訊</b>
代號：{signal_data.get('stock_code', 'N/A')} {signal_data.get('stock_name', '')}
現價：${signal_data.get('current_price', 0):.2f}

📈 <b>指標</b>
VWAP 乖離：{signal_data.get('vwap_deviation', 0):+.2f}%
KD：K={signal_data.get('kd_k', 0):.1f}
OFI：{signal_data.get('ofi', 0):+.1f}

🤖 <b>決策</b>
方法：{decision.get('method', 'N/A')}
"""
        
        if decision.get('decision') == 'ALLOW':
            message += f"信心度：{decision.get('confidence', 0)*100:.1f}%\n"
        else:
            reasons = decision.get('reasons', decision.get('recommendation', ''))
            if isinstance(reasons, list):
                message += f"原因：\n" + "\n".join([f"• {r}" for r in reasons])
            elif reasons:
                message += f"原因：{reasons}\n"
        
        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    def send_signal_alert(self, signal_data: Dict, decision: Dict):
        """發送訊號提醒"""
        
        message = self.format_signal_notification(signal_data, decision)
        
        # 發送到 Telegram
        if 'telegram' in self.channels:
            self.send_to_channel('telegram', message)
        
        # Email 只發重要訊號
        if decision.get('decision') == 'ALLOW' and 'email' in self.channels:
            subject = f"交易訊號: {signal_data.get('stock_code')} 建議進場"
            self.send_to_channel('email', message, subject=subject)
        
        # Line
        if 'line' in self.channels:
            plain_message = message.replace('<b>', '').replace('</b>', '')
            self.send_to_channel('line', plain_message)
    
    def send_daily_summary(self, stats: Dict):
        """發送每日總結"""
        
        message = f"""
📊 <b>每日交易統計</b>

🗓️ {datetime.now().strftime('%Y-%m-%d')}

📈 訊號統計
總訊號：{stats.get('total_signals', 0)}
允許進場：{stats.get('allowed', 0)}
建議觀望：{stats.get('rejected', 0)}

✅ 決策品質
準確率：{stats.get('accuracy', 0)*100:.1f}%
期望值：{stats.get('expected_value', 0):+.2f}%

⚙️ 系統狀態
ML：{'已啟用' if stats.get('ml_enabled') else '未啟用'}
追蹤中：{stats.get('active_tracking', 0)} 筆
        """
        
        self.send_to_all(message)


# 全局實例
notification_manager = NotificationManager()
