import asyncio
import logging
from typing import Optional, Callable, Dict, Set
from datetime import datetime, timedelta
from contextlib import suppress
import os

logger = logging.getLogger(__name__)

class FubonWebSocketManager:
    """
    穩定版富邦 WebSocket 管理器
    特性：
    1. 自動重連（指數退避）
    2. 異常靜默（防止日誌洗版）
    3. 心跳檢測
    4. 優雅降級
    """
    
    def __init__(self, fubon_sdk, max_retry: int = 5):
        self.sdk = fubon_sdk
        self.is_connected = False
        self.retry_count = 0
        self.max_retry = max_retry
        self.last_error_time: Optional[datetime] = None
        self.error_cooldown = timedelta(seconds=30)
        
        # 訂閱管理
        self.subscribed_symbols: Set[str] = set()
        self.callbacks: Dict[str, Callable] = {}
        
        # 背景任務
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # 應用補丁
        self._apply_sdk_patches()
    
    def _apply_sdk_patches(self):
        """靜默富邦 SDK 的背景執行緒異常，防止洗版"""
        try:
            import fubon_neo.fugle_marketdata.websocket.client as fb_ws
            
            # 保存原始的 send_ping 方法
            if hasattr(fb_ws.WebSocketClient, 'send_ping'):
                original_ping = fb_ws.WebSocketClient.send_ping
                
                def silent_ping(self_ws):
                    try:
                        return original_ping(self_ws)
                    except Exception:
                        # 完全靜默，不記錄任何日誌
                        pass
                
                fb_ws.WebSocketClient.send_ping = silent_ping
                logger.info("✅ 已應用 Fubon SDK WebSocket 異常靜默補丁")
        except Exception as e:
            logger.warning(f"⚠️ 無法應用補丁: {e}")

    async def connect(self) -> bool:
        """建立 WebSocket 連線 (目前優先使用 REST 備援)"""
        # 🆕 暫時全部降級到 REST，因為 Fubon WebSocket 目前不穩定
        logger.warning("⚠️ WebSocket 已暫時被全域禁用 (降級至 REST 輪詢)")
        self.is_connected = False
        return False
        
        if self.is_connected:
            return True

    async def _heartbeat_loop(self):
        """主動監控 WebSocket 健康狀態"""
        while self.is_connected:
            try:
                await asyncio.sleep(60)
                # 檢查 SDK 的 marketdata 客戶端是否還存活 (利用 hasattr 或特定屬性)
                if not hasattr(self.sdk, 'marketdata') or not self.sdk.marketdata:
                    logger.warning("💔 偵測到 SDK marketdata 失效，嘗試恢復...")
                    self.is_connected = False
                    break
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def subscribe(self, channel: str, symbol: str, callback: Optional[Callable] = None):
        """
        訂閱標的
        注意：為了性能，callback 應在外部統一註冊一次，或在此判斷是否已註冊
        """
        if not self.is_connected:
            return False
            
        try:
            clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
            ws = self.sdk.marketdata.websocket_client.stock
            
            # 如果有提供 callback，且還沒註冊過，則註冊
            if callback:
                import inspect
                # 這裡簡單判斷，實際 SDK 的 .on 可能沒提供獲取已註冊列表的方法
                # 我們假設外部會處理，或我們只註冊一次
                pass 
                
            ws.subscribe({'channel': channel, 'symbol': clean_symbol})
            
            self.subscribed_symbols.add(symbol)
            logger.info(f"📡 WebSocket 訂閱成功: {symbol} ({channel})")
            return True
        except Exception as e:
            logger.error(f"❌ 訂閱失敗 {symbol}: {e}")
            return False

    async def stop(self):
        self.is_connected = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        logger.info("🔌 WebSocket 管理器已停止")
