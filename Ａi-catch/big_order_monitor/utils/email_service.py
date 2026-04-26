"""
Email 通知服務
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
import logging
import os

if TYPE_CHECKING:
    from ..core.detector.advanced_detector import EnhancedSignal
    from ..config.trading_config import EmailConfig

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Email 通知服務"""
    
    def __init__(self, config: "EmailConfig" = None):
        self.config = config
        self.enabled = False
        
        # 從環境變數或配置載入設定
        self.smtp_server = config.smtp_server if config else os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = config.smtp_port if config else int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = config.sender_email if config else os.getenv('SENDER_EMAIL', '')
        self.sender_password = config.sender_password if config else os.getenv('SENDER_PASSWORD', '')
        self.recipient_emails = config.recipient_emails if config else os.getenv('RECIPIENT_EMAILS', '').split(',')
        self.min_quality_for_email = config.min_quality_for_email if config else 0.70
        
        # 檢查是否已配置
        if self.sender_email and self.sender_password and self.recipient_emails:
            self.enabled = True
            logger.info(f"✅ Email 通知服務已啟用，將發送至: {', '.join(self.recipient_emails)}")
        else:
            logger.warning("⚠️ Email 通知服務未配置，請設定 SENDER_EMAIL、SENDER_PASSWORD、RECIPIENT_EMAILS 環境變數")
    
    async def send_signal_notification(self, signal: "EnhancedSignal") -> bool:
        """發送訊號通知"""
        if not self.enabled:
            logger.debug("Email 通知未啟用")
            return False
        
        # 檢查品質門檻
        if signal.quality_score < self.min_quality_for_email:
            logger.debug(f"訊號品質 {signal.quality_score:.1%} 未達門檻 {self.min_quality_for_email:.1%}，不發送 Email")
            return False
        
        try:
            # 建立 Email
            subject = self._create_subject(signal)
            html_body = self._create_html_body(signal)
            
            # 發送
            success = await self._send_email(subject, html_body)
            
            if success:
                logger.info(f"✅ 訊號通知已發送: {signal.stock_code} {signal.signal_type}")
            
            return success
            
        except Exception as e:
            logger.error(f"發送 Email 失敗: {e}")
            return False
    
    def _create_subject(self, signal: "EnhancedSignal") -> str:
        """建立 Email 主旨"""
        emoji = "🟢" if signal.signal_type == "BUY" else "🔴"
        action = "買進" if signal.signal_type == "BUY" else "賣出"
        quality = signal.quality_level
        
        return f"{emoji} 大單{action}訊號 - {signal.stock_code} {signal.stock_name} ({quality})"
    
    def _create_html_body(self, signal: "EnhancedSignal") -> str:
        """建立 Email HTML 內容"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f3f4f6; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
                .content {{ padding: 30px; }}
                .footer {{ background: #f9fafb; padding: 20px; text-align: center; color: #6b7280; font-size: 12px; border-top: 1px solid #e5e7eb; }}
                .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin-top: 20px; border-radius: 0 8px 8px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔍 大單偵測監控系統 v3.0</h1>
                    <p>即時訊號通知</p>
                </div>
                <div class="content">
                    {signal.to_email_html()}
                    
                    <div class="warning">
                        <strong>⚠️ 重要提醒</strong><br>
                        本訊號僅供參考，不構成投資建議。投資有風險，請謹慎評估後自行決定。
                    </div>
                </div>
                <div class="footer">
                    <p>大單偵測監控系統 v3.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>此為系統自動發送的通知郵件</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    async def _send_email(self, subject: str, html_body: str) -> bool:
        """發送 Email"""
        try:
            # 建立郵件
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = ", ".join(self.recipient_emails)
            
            # 附加 HTML 內容
            html_part = MIMEText(html_body, "html", "utf-8")
            message.attach(html_part)
            
            # 建立安全連接並發送
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
                server.sendmail(
                    self.sender_email,
                    self.recipient_emails,
                    message.as_string()
                )
            
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("Email 認證失敗，請檢查帳號密碼")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP 錯誤: {e}")
            return False
        except Exception as e:
            logger.error(f"發送 Email 失敗: {e}")
            return False
    
    async def send_daily_report(self, stats: dict, signals: List["EnhancedSignal"]) -> bool:
        """發送每日報告"""
        if not self.enabled:
            return False
        
        try:
            subject = f"📊 大單偵測日報 - {datetime.now().strftime('%Y-%m-%d')}"
            
            # 統計訊號
            buy_signals = [s for s in signals if s.signal_type == "BUY"]
            sell_signals = [s for s in signals if s.signal_type == "SELL"]
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f3f4f6; padding: 20px; }}
                    .container {{ max-width: 700px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
                    th {{ background: #f9fafb; font-weight: 600; }}
                    .stat-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
                    .stat-card {{ background: #f9fafb; padding: 15px; border-radius: 8px; text-align: center; }}
                    .stat-value {{ font-size: 24px; font-weight: bold; color: #1f2937; }}
                    .stat-label {{ font-size: 12px; color: #6b7280; margin-top: 5px; }}
                    .footer {{ background: #f9fafb; padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📊 大單偵測日報</h1>
                        <p>{datetime.now().strftime('%Y年%m月%d日')}</p>
                    </div>
                    <div class="content">
                        <h2>📈 今日統計</h2>
                        <div class="stat-grid">
                            <div class="stat-card">
                                <div class="stat-value">{stats.get('total_ticks', 0):,}</div>
                                <div class="stat-label">處理 Tick 數</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">{stats.get('big_orders', 0)}</div>
                                <div class="stat-label">偵測大單數</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">{len(signals)}</div>
                                <div class="stat-label">產生訊號數</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" style="color: #22c55e;">{len(buy_signals)}</div>
                                <div class="stat-label">買進訊號</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" style="color: #ef4444;">{len(sell_signals)}</div>
                                <div class="stat-label">賣出訊號</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">{stats.get('fake_orders', 0)}</div>
                                <div class="stat-label">過濾假單數</div>
                            </div>
                        </div>
                        
                        <h2>🔔 今日訊號列表</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>時間</th>
                                    <th>股票</th>
                                    <th>方向</th>
                                    <th>價格</th>
                                    <th>品質</th>
                                    <th>評分</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join([f'''
                                <tr>
                                    <td>{s.timestamp.strftime('%H:%M:%S')}</td>
                                    <td>{s.stock_code} {s.stock_name}</td>
                                    <td style="color: {'#22c55e' if s.signal_type == 'BUY' else '#ef4444'};">{'買進' if s.signal_type == 'BUY' else '賣出'}</td>
                                    <td>${s.price:,.2f}</td>
                                    <td>{s.quality_level}</td>
                                    <td>{s.composite_score:.1%}</td>
                                </tr>
                                ''' for s in signals[-20:]])}
                            </tbody>
                        </table>
                        {f'<p style="color: #6b7280; text-align: center;">僅顯示最近 20 筆（共 {len(signals)} 筆）</p>' if len(signals) > 20 else ''}
                    </div>
                    <div class="footer">
                        <p>大單偵測監控系統 v3.0 | 此為系統自動發送的日報</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return await self._send_email(subject, html_body)
            
        except Exception as e:
            logger.error(f"發送日報失敗: {e}")
            return False
    
    async def send_test_email(self) -> bool:
        """發送測試郵件"""
        if not self.enabled:
            logger.error("Email 通知未配置")
            return False
        
        subject = "🧪 大單偵測監控系統 - 測試郵件"
        html_body = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: sans-serif; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: #f0f9ff; padding: 30px; border-radius: 12px; text-align: center;">
                <h1 style="color: #0369a1;">✅ 測試成功！</h1>
                <p style="color: #64748b;">您的 Email 通知服務已正確配置。</p>
                <p style="color: #64748b;">大單偵測監控系統 v3.0</p>
                <p style="font-size: 12px; color: #94a3b8;">發送時間: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
            </div>
        </body>
        </html>
        """
        
        success = await self._send_email(subject, html_body)
        if success:
            logger.info("✅ 測試郵件發送成功")
        return success
