"""
交易分析報告排程器
Trade Analyzer Report Scheduler

在每日開盤後5分鐘 (09:05) 自動發送最愛股票報告
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Dict, List
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class TradeReportScheduler:
    """交易報告排程器"""
    
    def __init__(self):
        self.scheduled_stocks: List[str] = []
        self.send_time: str = "09:05"
        self.enabled: bool = False
        self.is_running: bool = False
        self.last_sent_date: str = ""
        
        # Email 設定
        self.email_config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "k26car@gmail.com",
            "password": "zrgogmielnvpykrv",
            "recipients": ["k26car@gmail.com", "neimou1225@gmail.com"]
        }
    
    def set_schedule(self, stock_codes: List[str], send_time: str = "09:05"):
        """設定排程"""
        self.scheduled_stocks = stock_codes
        self.send_time = send_time
        self.enabled = True
        logger.info(f"📧 已設定排程: {len(stock_codes)} 檔股票於 {send_time} 發送")
        return {
            "success": True,
            "stocks": stock_codes,
            "send_time": send_time
        }
    
    def cancel_schedule(self):
        """取消排程"""
        self.scheduled_stocks = []
        self.enabled = False
        logger.info("❌ 已取消排程")
        return {"success": True}
    
    def get_status(self) -> Dict:
        """取得排程狀態"""
        return {
            "enabled": self.enabled,
            "stocks": self.scheduled_stocks,
            "send_time": self.send_time,
            "is_running": self.is_running,
            "last_sent_date": self.last_sent_date
        }
    
    async def check_and_send(self):
        """檢查時間並發送"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")
        
        # 檢查是否該發送
        if (self.enabled and 
            self.scheduled_stocks and 
            current_time == self.send_time and
            current_date != self.last_sent_date):
            
            logger.info(f"⏰ 時間到! 開始發送 {len(self.scheduled_stocks)} 檔股票報告...")
            await self.send_all_reports()
            self.last_sent_date = current_date
    
    async def send_all_reports(self) -> Dict:
        """發送所有排程股票的報告"""
        if not self.scheduled_stocks:
            return {"success": False, "error": "沒有排程股票"}
        
        results = []
        for code in self.scheduled_stocks:
            try:
                result = await self.send_single_report(code)
                results.append({"code": code, "success": result.get("success", False)})
            except Exception as e:
                logger.error(f"發送 {code} 報告失敗: {e}")
                results.append({"code": code, "success": False, "error": str(e)})
        
        success_count = sum(1 for r in results if r.get("success"))
        logger.info(f"✅ 報告發送完成: {success_count}/{len(results)} 成功")
        
        return {
            "success": True,
            "total": len(results),
            "success_count": success_count,
            "results": results
        }
    
    async def send_single_report(self, stock_code: str) -> Dict:
        """發送單一股票報告"""
        try:
            from app.services.support_resistance_analyzer import support_resistance_analyzer
            from app.services.trade_analyzer_report import generate_trade_analyzer_html
            import yfinance as yf
            
            # 取得分析數據
            sr_result = await support_resistance_analyzer.analyze(stock_code)
            if not sr_result:
                return {"success": False, "error": f"無法取得 {stock_code} 資料"}
            
            # 取得當沖數據
            ticker = yf.Ticker(f"{stock_code}.TW")
            hist = ticker.history(period="1d", interval="1m")
            
            if hist.empty:
                ticker = yf.Ticker(f"{stock_code}.TWO")
                hist = ticker.history(period="1d", interval="1m")
            
            intraday_data = {}
            if not hist.empty and len(hist) >= 5:  # 開盤5分鐘後至少有5根K線
                first_bars = hist.head(min(15, len(hist)))  # 取前15分鐘或現有數據
                range_high = float(first_bars['High'].max())
                range_low = float(first_bars['Low'].min())
                current = float(hist['Close'].iloc[-1])
                range_size = range_high - range_low if range_high > range_low else 1
                
                # 判斷訊號
                if current > range_high:
                    signal = "bullish_breakout"
                    signal_text = "🔴 突破高點 - 強勢多頭"
                elif current < range_low:
                    signal = "bearish_breakout"
                    signal_text = "🟢 跌破低點 - 弱勢空頭"
                else:
                    signal = "neutral"
                    signal_text = "⚖️ 中性盤整"
                
                intraday_data = {
                    'range_high': range_high,
                    'range_low': range_low,
                    'current': current,
                    'signal': signal,
                    'signal_text': signal_text,
                    'long_target1': current + range_size * 0.5,
                    'long_stop': range_high - range_size * 0.2,
                    'short_target1': current - range_size * 0.5,
                    'short_stop': range_low + range_size * 0.2
                }
            
            # 組裝報告數據
            report_data = {
                'stock_code': sr_result['stock_code'],
                'stock_name': sr_result['stock_name'],
                'current_price': sr_result['current_price'],
                'support_resistance': {
                    'trend_status': sr_result.get('trend_status', {}),
                    'reversal_signal': sr_result.get('reversal_signal', {}),
                    'risk_reward_analysis': sr_result.get('risk_reward_analysis', {}),
                    'resistance_levels': sr_result.get('resistance_levels', []),
                    'support_levels': sr_result.get('support_levels', [])
                },
                'checklist': [],
                'score': sr_result.get('overall_score', 60),
                'recommendation': sr_result.get('recommendation', '持有觀望'),
                'risk_calculator': {
                    'entry_price': sr_result['current_price'],
                    'stop_loss': sr_result.get('risk_reward_analysis', {}).get('stop_loss_price', 0),
                    'target_price': sr_result.get('risk_reward_analysis', {}).get('target_price', 0),
                    'position_size': 1000,
                    'risk_reward_ratio': sr_result.get('risk_reward_analysis', {}).get('risk_reward_ratio', 0)
                },
                'fibonacci': {
                    'high': sr_result['current_price'] * 1.1,
                    'low': sr_result['current_price'] * 0.9,
                    'trend': 'uptrend',
                    'fib_382': 0,
                    'fib_500': 0,
                    'fib_618': 0
                },
                'intraday': intraday_data,
                'volume_profile': {}
            }
            
            # 計算斐波那契
            fib_range = report_data['fibonacci']['high'] - report_data['fibonacci']['low']
            report_data['fibonacci']['fib_382'] = report_data['fibonacci']['high'] - fib_range * 0.382
            report_data['fibonacci']['fib_500'] = report_data['fibonacci']['high'] - fib_range * 0.5
            report_data['fibonacci']['fib_618'] = report_data['fibonacci']['high'] - fib_range * 0.618
            
            # 生成 HTML
            html_content = generate_trade_analyzer_html(report_data)
            
            # 發送郵件
            return await self._send_email(
                subject=f"[開盤快報] {stock_code} {sr_result['stock_name']} - {datetime.now().strftime('%H:%M')}",
                html_body=html_content
            )
            
        except Exception as e:
            logger.error(f"生成報告失敗 {stock_code}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_email(self, subject: str, html_body: str) -> Dict:
        """發送郵件"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_config['username']
            msg['To'] = ", ".join(self.email_config['recipients'])
            msg['Subject'] = subject
            
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            server.sendmail(self.email_config['username'], self.email_config['recipients'], msg.as_string())
            server.quit()
            
            logger.info(f"📧 郵件已發送: {subject}")
            return {"success": True, "recipients": len(self.email_config['recipients'])}
            
        except Exception as e:
            logger.error(f"發送郵件失敗: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_scheduler(self):
        """啟動背景排程器"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("🚀 交易報告排程器已啟動")
        
        while self.is_running:
            try:
                await self.check_and_send()
            except Exception as e:
                logger.error(f"排程檢查錯誤: {e}")
            
            # 每30秒檢查一次
            await asyncio.sleep(30)
    
    def stop_scheduler(self):
        """停止排程器"""
        self.is_running = False
        logger.info("⏹️ 交易報告排程器已停止")


# 創建全局實例
trade_report_scheduler = TradeReportScheduler()
