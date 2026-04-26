
"""
Support Confirmation Watcher
專門用於「支撐測試中」的背景監控任務
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from app.services.fubon_service import get_realtime_quote
from app.services.stock_comprehensive_analyzer import analyze_stock_comprehensive
from app.services.notification_manager import notification_manager

logger = logging.getLogger(__name__)

class SupportWatcher:
    def __init__(self):
        self.watching_tasks = {}

    async def start_watching(self, symbol: str, target_support: float, duration_minutes: int = 60):
        if symbol in self.watching_tasks:
            self.watching_tasks[symbol].cancel()
            
        task = asyncio.create_task(self._watch_loop(symbol, target_support, duration_minutes))
        self.watching_tasks[symbol] = task
        logger.info(f"開始背景監控 {symbol} 支撐位 {target_support}")
        return True

    async def _watch_loop(self, symbol: str, target_support: float, duration_minutes: int):
        end_time = datetime.now() + asyncio.timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time:
            try:
                # 取得即時價格與分析
                quote = await get_realtime_quote(symbol)
                analysis = await analyze_stock_comprehensive(symbol)
                
                if not quote or not analysis:
                    await asyncio.sleep(60)
                    continue
                    
                price = quote.get('price', 0)
                vpa = analysis.get('volume_price_analysis', {})
                ofi = vpa.get('ofi', 0)
                confirmation = vpa.get('confirmation_signal', '')
                
                # 止跌確認條件：
                # 1. 價格在支撐位附近 (+1%) 且沒有破位
                # 2. 或者價格從支撐位反彈
                # 3. 大戶資金流 (OFI) 轉正
                
                is_near_support = target_support * 0.995 <= price <= target_support * 1.015
                is_rebound = price > target_support and ofi > 0
                
                if is_near_support:
                    if ofi > 0 or "bullish" in confirmation:
                        # 止跌確認！
                        msg = f"🎯 【支撐確認】{symbol} 已在 ${target_support} 附近止跌！\n現價: ${price}\n大戶流向: {ofi}\n建議: 可以分批進場"
                        await notification_manager.send_notification(msg)
                        logger.info(f"Confirmed support for {symbol} at {price}")
                        break
                
                # 如果嚴重破位 (-2%)，停止監控並警告
                if price < target_support * 0.98:
                    msg = f"⚠️ 【支撐破位】{symbol} 跌破預期支撐 ${target_support}\n現價: ${price}\n建議: 暫勿接刀，等待下一個支撐"
                    await notification_manager.send_notification(msg)
                    break
                    
            except Exception as e:
                logger.error(f"Error watching support for {symbol}: {e}")
                
            await asyncio.sleep(30) # 每 30 秒檢查一次
            
        if symbol in self.watching_tasks:
            del self.watching_tasks[symbol]

support_watcher = SupportWatcher()
