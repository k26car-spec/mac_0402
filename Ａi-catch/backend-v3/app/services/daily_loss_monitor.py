"""
單日虧損上限風控系統
Daily Loss Limit Risk Control System

功能：
1. 設定單日最大虧損金額或百分比
2. 即時追蹤當日已實現 + 未實現損益
3. 觸及上限時自動停止交易
4. 發送警告通知
"""

import asyncio
import logging
import os
import smtplib
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DailyLossConfig:
    """單日虧損上限設定"""
    max_loss_amount: float = 50000  # 單日最大虧損金額 (預設 5 萬)
    max_loss_percent: float = 2.0   # 單日最大虧損比例 (2%)
    total_capital: float = 1000000  # 總資金 (預設 100 萬)
    warning_threshold: float = 0.7  # 預警門檻 (70% 時開始警告)
    auto_close_on_limit: bool = True  # 觸及上限時自動平倉
    block_new_trades: bool = True     # 觸及上限時禁止新開倉


@dataclass
class DailyLossStatus:
    """當日損益狀態"""
    date: str
    realized_pnl: float = 0       # 已實現損益
    unrealized_pnl: float = 0     # 未實現損益
    total_pnl: float = 0          # 總損益
    trade_count: int = 0          # 當日交易次數
    
    loss_percent: float = 0       # 虧損百分比
    limit_percent: float = 0      # 已使用的上限比例
    
    is_warning: bool = False      # 是否進入預警
    is_limit_hit: bool = False    # 是否觸及上限
    trading_blocked: bool = False # 是否禁止交易
    
    last_check: str = ""


class DailyLossMonitor:
    """單日虧損監控器"""
    
    def __init__(self):
        self.config = DailyLossConfig()
        self.status = DailyLossStatus(date=date.today().isoformat())
        self.is_running = False
        self._warning_sent_today = False
        self._limit_sent_today = False
        
        # Email 設定
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = os.getenv('EMAIL_USERNAME') or os.getenv('SENDER_EMAIL', '')
        self.sender_password = os.getenv('EMAIL_PASSWORD') or os.getenv('SENDER_PASSWORD', '')
        self.recipients = self._get_recipients()
        
        logger.info("🛡️ 單日虧損監控器已初始化")
    
    def _get_recipients(self) -> List[str]:
        recipients_str = os.getenv('EMAIL_RECIPIENTS') or os.getenv('RECIPIENT_EMAILS', '')
        return [r.strip() for r in recipients_str.split(',') if r.strip()]
    
    def configure(
        self,
        max_loss_amount: float = None,
        max_loss_percent: float = None,
        total_capital: float = None,
        warning_threshold: float = None,
        auto_close_on_limit: bool = None,
        block_new_trades: bool = None
    ):
        """更新設定"""
        if max_loss_amount is not None:
            self.config.max_loss_amount = max_loss_amount
        if max_loss_percent is not None:
            self.config.max_loss_percent = max_loss_percent
        if total_capital is not None:
            self.config.total_capital = total_capital
        if warning_threshold is not None:
            self.config.warning_threshold = warning_threshold
        if auto_close_on_limit is not None:
            self.config.auto_close_on_limit = auto_close_on_limit
        if block_new_trades is not None:
            self.config.block_new_trades = block_new_trades
        
        logger.info(f"🛡️ 風控設定已更新: 最大虧損 ${self.config.max_loss_amount:,.0f} / {self.config.max_loss_percent}%")
    
    async def start(self):
        """啟動監控"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("🚀 單日虧損監控器已啟動")
        asyncio.create_task(self._monitor_loop())
    
    async def stop(self):
        """停止監控"""
        self.is_running = False
        logger.info("🛑 單日虧損監控器已停止")
    
    async def _monitor_loop(self):
        """主監控循環"""
        while self.is_running:
            try:
                # 每分鐘檢查一次
                await self._check_daily_loss()
                await asyncio.sleep(60)
                
                # 每日重置
                if date.today().isoformat() != self.status.date:
                    self._reset_daily()
                    
            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                await asyncio.sleep(30)
    
    def _reset_daily(self):
        """每日重置"""
        self.status = DailyLossStatus(date=date.today().isoformat())
        self._warning_sent_today = False
        self._limit_sent_today = False
        logger.info(f"📅 每日重置完成: {self.status.date}")
    
    async def _check_daily_loss(self):
        """檢查當日損益"""
        try:
            # 取得當日已實現損益
            realized = await self._get_realized_pnl()
            
            # 取得未實現損益
            unrealized = await self._get_unrealized_pnl()
            
            # 更新狀態
            self.status.realized_pnl = realized
            self.status.unrealized_pnl = unrealized
            self.status.total_pnl = realized + unrealized
            self.status.last_check = datetime.now().isoformat()
            
            # 計算虧損比例
            max_loss = min(
                self.config.max_loss_amount,
                self.config.total_capital * self.config.max_loss_percent / 100
            )
            
            if self.status.total_pnl < 0:
                self.status.loss_percent = abs(self.status.total_pnl) / self.config.total_capital * 100
                self.status.limit_percent = abs(self.status.total_pnl) / max_loss * 100
            else:
                self.status.loss_percent = 0
                self.status.limit_percent = 0
            
            # 檢查是否進入預警
            if self.status.limit_percent >= self.config.warning_threshold * 100:
                self.status.is_warning = True
                if not self._warning_sent_today:
                    await self._send_warning_notification()
                    self._warning_sent_today = True
            
            # 檢查是否觸及上限
            if self.status.limit_percent >= 100:
                self.status.is_limit_hit = True
                self.status.trading_blocked = self.config.block_new_trades
                
                if not self._limit_sent_today:
                    await self._handle_limit_hit()
                    self._limit_sent_today = True
            
        except Exception as e:
            logger.error(f"檢查損益失敗: {e}")
    
    async def _get_realized_pnl(self) -> float:
        """取得當日已實現損益"""
        try:
            from app.database.connection import get_async_session
            from app.models.portfolio import TradeRecord
            from sqlalchemy import select, func, and_
            
            today_start = datetime.combine(date.today(), datetime.min.time())
            
            async with get_async_session() as session:
                result = await session.execute(
                    select(func.sum(TradeRecord.realized_pnl)).where(
                        and_(
                            TradeRecord.trade_type == 'SELL',
                            TradeRecord.timestamp >= today_start
                        )
                    )
                )
                total = result.scalar()
                return float(total) if total else 0
                
        except Exception as e:
            logger.debug(f"取得已實現損益失敗: {e}")
            return 0
    
    async def _get_unrealized_pnl(self) -> float:
        """取得未實現損益"""
        try:
            from app.database.connection import get_async_session
            from app.models.portfolio import Portfolio
            from sqlalchemy import select, func
            
            async with get_async_session() as session:
                result = await session.execute(
                    select(func.sum(Portfolio.unrealized_pnl)).where(
                        Portfolio.status == 'OPEN'
                    )
                )
                total = result.scalar()
                return float(total) if total else 0
                
        except Exception as e:
            logger.debug(f"取得未實現損益失敗: {e}")
            return 0
    
    async def _handle_limit_hit(self):
        """處理觸及上限"""
        logger.warning(f"🚨 觸及單日虧損上限！當日損益: ${self.status.total_pnl:,.0f}")
        
        # 自動平倉
        if self.config.auto_close_on_limit:
            await self._force_close_all()
        
        # 發送通知
        await self._send_limit_notification()
    
    async def _force_close_all(self):
        """強制平倉所有持倉"""
        try:
            from app.services.smart_simulation_trader import smart_trader
            
            # 呼叫智能交易器的強制平倉
            if hasattr(smart_trader, 'force_close_all_positions'):
                await smart_trader.force_close_all_positions('風控: 觸及單日虧損上限')
                logger.warning("🛡️ 已強制平倉所有持倉")
            else:
                logger.warning("⚠️ 無法強制平倉: 智能交易器不支持")
                
        except Exception as e:
            logger.error(f"強制平倉失敗: {e}")
    
    async def _send_warning_notification(self):
        """發送預警通知"""
        await self._send_email(
            subject=f"⚠️ 【預警】單日虧損已達 {self.status.limit_percent:.0f}%",
            is_warning=True
        )
    
    async def _send_limit_notification(self):
        """發送觸及上限通知"""
        await self._send_email(
            subject=f"🚨 【風控】單日虧損上限已觸及！交易已暫停",
            is_warning=False
        )
    
    async def _send_email(self, subject: str, is_warning: bool):
        """發送通知郵件"""
        if not self.sender_email or not self.sender_password or not self.recipients:
            logger.warning("Email 設定不完整，跳過通知")
            return
        
        try:
            bg_color = "#f59e0b" if is_warning else "#dc2626"
            status_text = "預警" if is_warning else "觸及上限"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"></head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 20px; background: #f5f5f5;">
                <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                    <div style="background: {bg_color}; color: white; padding: 24px; text-align: center;">
                        <h1 style="margin: 0; font-size: 24px;">🛡️ 風控{status_text}</h1>
                        <p style="margin: 8px 0 0; font-size: 16px;">單日虧損監控系統</p>
                    </div>
                    <div style="padding: 24px;">
                        <div style="display: grid; gap: 12px;">
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #fef2f2; border-radius: 8px; border: 1px solid #fecaca;">
                                <span style="color: #dc2626;">💰 當日損益</span>
                                <span style="font-weight: bold; color: #dc2626; font-size: 18px;">${self.status.total_pnl:,.0f}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #f9fafb; border-radius: 8px;">
                                <span style="color: #6b7280;">📊 已實現</span>
                                <span style="font-weight: bold;">${self.status.realized_pnl:,.0f}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #f9fafb; border-radius: 8px;">
                                <span style="color: #6b7280;">📈 未實現</span>
                                <span style="font-weight: bold;">${self.status.unrealized_pnl:,.0f}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #fef3c7; border-radius: 8px; border: 1px solid #fcd34d;">
                                <span style="color: #92400e;">📏 虧損比例</span>
                                <span style="font-weight: bold; color: #92400e;">{self.status.loss_percent:.2f}%</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #fef3c7; border-radius: 8px; border: 1px solid #fcd34d;">
                                <span style="color: #92400e;">🎯 上限使用</span>
                                <span style="font-weight: bold; color: #92400e;">{self.status.limit_percent:.0f}%</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #f9fafb; border-radius: 8px;">
                                <span style="color: #6b7280;">🚫 交易狀態</span>
                                <span style="font-weight: bold; color: {'#dc2626' if self.status.trading_blocked else '#16a34a'};">{'已暫停' if self.status.trading_blocked else '正常'}</span>
                            </div>
                        </div>
                        
                        {"<div style='margin-top: 20px; padding: 16px; background: #fef2f2; border-radius: 8px; border: 2px solid #dc2626;'><p style='margin: 0; color: #dc2626; font-weight: bold;'>⚠️ 已觸及單日虧損上限，今日交易已暫停！</p></div>" if not is_warning else ""}
                    </div>
                    <div style="padding: 16px 24px; background: #f9fafb; text-align: center; color: #9ca3af; font-size: 12px;">
                        AI 智能交易系統 - 風控模組 v1.0
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipients)
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipients, msg.as_string())
            
            logger.info(f"✅ 風控通知已發送: {subject}")
            
        except Exception as e:
            logger.error(f"❌ 發送郵件失敗: {e}")
    
    def can_open_position(self) -> tuple[bool, str]:
        """檢查是否可以開新倉"""
        if self.status.trading_blocked:
            return False, "🚫 已觸及單日虧損上限，今日禁止新開倉"
        
        if self.status.is_warning:
            return True, f"⚠️ 注意：已使用 {self.status.limit_percent:.0f}% 虧損上限"
        
        return True, "✅ 風控正常"
    
    def get_status(self) -> Dict:
        """取得完整狀態"""
        can_trade, reason = self.can_open_position()
        
        return {
            "date": self.status.date,
            "config": {
                "max_loss_amount": self.config.max_loss_amount,
                "max_loss_percent": self.config.max_loss_percent,
                "total_capital": self.config.total_capital,
                "warning_threshold": self.config.warning_threshold,
                "auto_close_on_limit": self.config.auto_close_on_limit,
                "block_new_trades": self.config.block_new_trades
            },
            "status": {
                "realized_pnl": self.status.realized_pnl,
                "unrealized_pnl": self.status.unrealized_pnl,
                "total_pnl": self.status.total_pnl,
                "trade_count": self.status.trade_count,
                "loss_percent": self.status.loss_percent,
                "limit_percent": self.status.limit_percent,
                "is_warning": self.status.is_warning,
                "is_limit_hit": self.status.is_limit_hit,
                "trading_blocked": self.status.trading_blocked,
                "last_check": self.status.last_check
            },
            "can_trade": can_trade,
            "message": reason,
            "is_running": self.is_running
        }


# 全域單例
daily_loss_monitor = DailyLossMonitor()
