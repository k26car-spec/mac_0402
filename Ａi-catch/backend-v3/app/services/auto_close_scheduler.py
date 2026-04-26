"""
自動平倉排程監控服務 v2.0
Auto Close Scheduler Service

功能：
1. 盤中每 30 秒自動檢查持倉（縮短間隔）
2. 達到目標價/停損價時自動平倉
3. 🆕 智能移動停利追蹤
4. 只在交易時間 (09:00-13:30) 運行
5. 平倉後發送通知
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import AsyncSessionLocal
from app.services.auto_close_monitor import AutoCloseMonitor

logger = logging.getLogger(__name__)


class AutoCloseScheduler:
    """自動平倉排程器 v2.0 - 含智能移動停利"""
    
    def __init__(self):
        self.is_running = False
        self.check_interval_seconds = 30  # 🆕 縮短到 30 秒
        self.last_check_time: Optional[datetime] = None
        self.total_checks = 0
        self.total_closes = 0
        self.total_trailing_updates = 0  # 🆕 移動停利更新次數
        self.total_trailing_closes = 0   # 🆕 移動停利觸發平倉次數
        
        # 交易時間（台灣股市）
        self.market_open = time(9, 0)   # 09:00
        self.market_close = time(13, 30)  # 13:30
    
    def is_trading_hours(self) -> bool:
        """檢查是否在交易時間內（包含休市日曆檢查）"""
        from app.utils.twse_calendar import twse_calendar
        return twse_calendar.is_market_open()
    
    async def run_check(self) -> dict:
        """執行一次完整檢查（包含移動停利）"""
        async with AsyncSessionLocal() as db:
            try:
                result = {
                    "checked": 0,
                    "closed": 0,
                    "trailing_updated": 0,
                    "trailing_closed": 0,
                    "details": [],
                    "trailing_details": []
                }
                
                # 1. 🆕 智能移動停利監控（優先執行）
                try:
                    from app.services.smart_trailing_stop import SmartTrailingStopService
                    trailing_service = SmartTrailingStopService(db)
                    trailing_result = await trailing_service.monitor_all_positions(simulated_only=True)
                    
                    result["trailing_updated"] = trailing_result.get("updated", 0)
                    result["trailing_closed"] = trailing_result.get("closed", 0)
                    result["trailing_details"] = trailing_result.get("close_details", [])
                    
                    self.total_trailing_updates += result["trailing_updated"]
                    self.total_trailing_closes += result["trailing_closed"]
                    
                    if result["trailing_updated"] > 0:
                        logger.info(f"📈 移動停利更新: {result['trailing_updated']} 個持倉")
                    
                    if result["trailing_closed"] > 0:
                        logger.info(f"🛑 移動停利觸發: {result['trailing_closed']} 個平倉")
                        
                except Exception as trailing_error:
                    logger.error(f"⚠️ 移動停利監控失敗: {trailing_error}")
                
                # 2. 傳統停損/停利檢查
                monitor = AutoCloseMonitor(db)
                close_result = await monitor.monitor_all_positions(simulated_only=True)
                
                result["checked"] = close_result.get("checked", 0)
                result["closed"] = close_result.get("closed", 0)
                result["details"] = close_result.get("details", [])
                
                self.last_check_time = datetime.now()
                self.total_checks += 1
                self.total_closes += result["closed"]
                
                # 如果有平倉，記錄詳細信息
                if result["closed"] > 0:
                    logger.info(f"🔔 自動平倉觸發！共 {result['closed']} 筆")
                    for detail in result.get("details", []):
                        logger.info(
                            f"   📈 {detail['symbol']} {detail.get('stock_name', '')} | "
                            f"損益: {detail['profit']:+.0f} ({detail['profit_percent']:+.1f}%) | "
                            f"原因: {detail['reason']}"
                        )
                
                return result
                
            except Exception as e:
                logger.error(f"❌ 自動平倉檢查失敗: {e}")
                return {"error": str(e), "checked": 0, "closed": 0}
    
    async def start_scheduler(self):
        """啟動排程器"""
        if self.is_running:
            logger.warning("⚠️ 排程器已經在運行中")
            return
        
        self.is_running = True
        logger.info("🚀 自動平倉排程器 v2.0 已啟動")
        logger.info(f"   ⏰ 檢查間隔: {self.check_interval_seconds} 秒")
        logger.info(f"   📅 交易時間: {self.market_open} - {self.market_close}")
        logger.info(f"   📈 含智能移動停利監控")
        
        while self.is_running:
            try:
                if self.is_trading_hours():
                    # 在交易時間內，執行檢查
                    result = await self.run_check()
                    
                    checked = result.get("checked", 0)
                    closed = result.get("closed", 0)
                    trailing_updated = result.get("trailing_updated", 0)
                    trailing_closed = result.get("trailing_closed", 0)
                    
                    if checked > 0 or trailing_updated > 0:
                        logger.debug(
                            f"📊 檢查完成: {checked} 個持倉, "
                            f"平倉 {closed}, 移動停利更新 {trailing_updated}, "
                            f"移動停利觸發 {trailing_closed}"
                        )
                else:
                    # 不在交易時間
                    now = datetime.now()
                    if now.minute == 0 and now.second < self.check_interval_seconds:
                        logger.debug(f"💤 非交易時間，暫停監控 (當前: {now.strftime('%H:%M')})")
                
                # 等待下一次檢查
                await asyncio.sleep(self.check_interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("🛑 收到停止信號，停止排程器")
                break
            except Exception as e:
                logger.error(f"❌ 排程器錯誤: {e}")
                await asyncio.sleep(self.check_interval_seconds)
        
        self.is_running = False
        logger.info("🔴 自動平倉排程器已停止")
    
    def stop_scheduler(self):
        """停止排程器"""
        self.is_running = False
        logger.info("🛑 正在停止自動平倉排程器...")
    
    def get_status(self) -> dict:
        """取得排程器狀態"""
        return {
            "version": "v2.0",
            "is_running": self.is_running,
            "is_trading_hours": self.is_trading_hours(),
            "check_interval_seconds": self.check_interval_seconds,
            "market_open": str(self.market_open),
            "market_close": str(self.market_close),
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "total_checks": self.total_checks,
            "total_closes": self.total_closes,
            "total_trailing_updates": self.total_trailing_updates,
            "total_trailing_closes": self.total_trailing_closes,
            "features": [
                "停損/停利監控",
                "智能移動停利 (階梯式)",
                "最高價追蹤",
                "Email 通知"
            ],
            "current_time": datetime.now().isoformat()
        }


# 全域排程器實例
auto_close_scheduler = AutoCloseScheduler()
