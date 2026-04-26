"""
WebSocket 實時監控系統 v1.0

🎯 功能：
1. 訂閱 53 支 ORB 監控股票的逐筆成交
2. 實時計算 VWAP、量比等指標
3. 偵測突破信號並自動建倉
4. 整合 SmartEntryScheduler 時間控制

📡 支持的數據源：
- 富邦 API WebSocket（需啟用 init_realtime）
- 備援：HTTP 輪詢模式
"""

import asyncio
import json
import logging
from datetime import datetime, time, timedelta
from typing import Dict, Any, List, Optional, Set, Callable
from collections import deque

logger = logging.getLogger(__name__)


class RealtimeStockData:
    """單一股票的實時數據"""
    
    def __init__(self, symbol: str, max_ticks: int = 500):
        self.symbol = symbol
        self.ticks = deque(maxlen=max_ticks)
        self.vwap = 0.0
        self.volume_total = 0
        self.pv_total = 0.0  # price * volume 累計
        self.high = 0.0
        self.low = float('inf')
        self.open = 0.0
        self.last_price = 0.0
        self.last_volume = 0
        self.last_update = None
        
        # 進階指標
        self.ma5 = 0.0
        self.ma20 = 0.0
        self.volume_ratio = 0.0
    
    def update(self, price: float, volume: int, timestamp: datetime = None):
        """更新報價"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.ticks.append({
            'price': price,
            'volume': volume,
            'timestamp': timestamp
        })
        
        # 更新基本數據
        self.last_price = price
        self.last_volume = volume
        self.last_update = timestamp
        
        if self.open == 0:
            self.open = price
        
        if price > self.high:
            self.high = price
        if price < self.low:
            self.low = price
        
        # 更新 VWAP
        self.pv_total += price * volume
        self.volume_total += volume
        
        if self.volume_total > 0:
            self.vwap = self.pv_total / self.volume_total
        
        # 更新 MA
        self._update_moving_averages()
    
    def _update_moving_averages(self):
        """更新移動平均"""
        prices = [t['price'] for t in self.ticks]
        
        if len(prices) >= 5:
            self.ma5 = sum(prices[-5:]) / 5
        
        if len(prices) >= 20:
            self.ma20 = sum(prices[-20:]) / 20
    
    def get_deviation(self) -> float:
        """計算 VWAP 乖離率"""
        if self.vwap <= 0:
            return 0
        return ((self.last_price - self.vwap) / self.vwap) * 100
    
    def get_change_pct(self) -> float:
        """計算漲跌幅"""
        if self.open <= 0:
            return 0
        return ((self.last_price - self.open) / self.open) * 100
    
    def to_dict(self) -> Dict:
        """轉為字典"""
        return {
            'symbol': self.symbol,
            'price': self.last_price,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'vwap': round(self.vwap, 2),
            'volume': self.volume_total,
            'ma5': round(self.ma5, 2),
            'ma20': round(self.ma20, 2),
            'deviation': round(self.get_deviation(), 2),
            'change_pct': round(self.get_change_pct(), 2),
            'tick_count': len(self.ticks),
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


class WebSocketMonitor:
    """
    WebSocket 實時監控器
    
    監控 53 支 ORB 股票，偵測突破信號
    """
    
    def __init__(self, watchlist: List[str] = None):
        # 監控清單
        self.watchlist = watchlist or []
        
        # 實時數據存儲
        self.stock_data: Dict[str, RealtimeStockData] = {}
        
        # 訂閱狀態
        self.subscribed_symbols: Set[str] = set()
        self.is_running = False
        
        # 信號回調
        self.signal_callbacks: List[Callable] = []
        
        # 信號記錄（避免重複）
        self.signals_sent_today: Dict[str, datetime] = {}
        
        # 統計
        self.ticks_received = 0
        self.signals_generated = 0
        
        # 從 smart_entry_system 載入進場排程器
        try:
            from app.services.smart_entry_system import entry_scheduler
            self.entry_scheduler = entry_scheduler
        except ImportError:
            self.entry_scheduler = None
    
    def add_watchlist(self, symbols: List[str]):
        """新增監控股票"""
        for symbol in symbols:
            if symbol not in self.watchlist:
                self.watchlist.append(symbol)
                self.stock_data[symbol] = RealtimeStockData(symbol)
    
    def set_watchlist(self, symbols: List[str]):
        """設定監控清單"""
        self.watchlist = symbols
        self.stock_data = {s: RealtimeStockData(s) for s in symbols}
    
    def on_signal(self, callback: Callable):
        """註冊信號回調"""
        self.signal_callbacks.append(callback)
    
    async def start_monitoring(self):
        """啟動智慧雙模監控"""
        self.is_running = True
        logger.info(f"🚀 啟動雙模監控 | 監控 {len(self.watchlist)} 支股票")
        
        # 1. 初始化 WebSocket 管理器
        import sys
        sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')
        from fubon_client import fubon_client
        from app.services.fubon_websocket_manager import FubonWebSocketManager
        
        self.ws_manager = FubonWebSocketManager(fubon_client.sdk)
        ws_success = await self.ws_manager.connect()
        
        if ws_success:
            logger.info("📡 模式：WebSocket 即時監控")
            await self._setup_websocket_subscriptions()
        else:
            logger.info("🔄 模式：REST 批次輪詢 (降級模式)")
            asyncio.create_task(self._batch_polling_loop())

    async def _setup_websocket_subscriptions(self):
        """設置 WebSocket 訂閱與回調 (優化版：僅註冊單一處理器)"""
        from fubon_client import fubon_client
        ws_stock = fubon_client.sdk.marketdata.websocket_client.stock
        
        # 確保只註冊一個處理器
        if not hasattr(self, '_ws_handler_registered'):
            def handle_ws_message(message):
                try:
                    import json
                    msg = json.loads(message) if isinstance(message, str) else message
                    if msg.get("event") == "data" and msg.get("channel") == "trades":
                        data = msg.get("data", {})
                        self._handle_trade_tick(data)
                except Exception: pass

            ws_stock.on('message', handle_ws_message)
            self._ws_handler_registered = True
        
        ws_stock.connect()
        
        for symbol in self.watchlist:
            # 修改後：不傳入 callback，避免重複註冊
            await self.ws_manager.subscribe('trades', symbol)

    async def _batch_polling_loop(self):
        """
        🔥 高效批次輪詢
        將所有監控標的合併為單一請求，避免網路擁塞
        """
        from fubon_client import fubon_client
        
        while self.is_running:
            try:
                from app.utils.twse_calendar import twse_calendar
                now = datetime.now()
                if not twse_calendar.is_market_open(now):
                    await asyncio.sleep(60)
                    continue

                if not self.watchlist:
                    await asyncio.sleep(5)
                    continue

                # 批次獲取報價 (一勞永逸)
                quotes = await fubon_client.batch_get_quotes(self.watchlist)
                
                for symbol, quote in quotes.items():
                    if quote and quote.get('price', 0) > 0:
                        self._handle_polling_data(symbol, quote)
                
            except Exception as e:
                logger.error(f"❌ 批次輪詢異常: {e}")
            
            await asyncio.sleep(5)

    def _handle_polling_data(self, symbol: str, quote: dict):
        """處理輪詢數據並觸發信號"""
        price = float(quote.get('price', 0))
        volume = int(quote.get('volume', 0))
        
        if symbol not in self.stock_data:
            self.stock_data[symbol] = RealtimeStockData(symbol)
            
        self.stock_data[symbol].update(price, volume)
        
        # 異步檢查信號
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._check_signals(symbol))
        except: pass
    
    async def _check_signals(self, symbol: str):
        """檢查是否觸發信號"""
        # 放棄在非交易時段產生信號
        from app.utils.twse_calendar import twse_calendar
        if not twse_calendar.is_market_open(datetime.now()):
            return
            
        # 檢查進場時間
        if self.entry_scheduler:
            entry_check = self.entry_scheduler.can_enter_new_position()
            if not entry_check.get('can_enter', False):
                return  # 禁止進場時段
        
        # 檢查今天是否已發信號
        if symbol in self.signals_sent_today:
            return
        
        data = self.stock_data.get(symbol)
        if not data or data.last_price <= 0:
            return
        
        signal = None
        
        # 策略 1：VWAP 突破
        if self._check_vwap_breakout(data):
            signal = {
                'symbol': symbol,
                'strategy': 'vwap_breakout',
                'price': data.last_price,
                'vwap': data.vwap,
                'deviation': data.get_deviation(),
                'confidence': 80,
                'reason': f"VWAP 突破（乖離 {data.get_deviation():+.2f}%）"
            }
        
        # 策略 2：動能爆發
        elif self._check_momentum_burst(data):
            signal = {
                'symbol': symbol,
                'strategy': 'momentum',
                'price': data.last_price,
                'change_pct': data.get_change_pct(),
                'confidence': 85,
                'reason': f"動能爆發（漲幅 {data.get_change_pct():+.2f}%）"
            }
        
        # 策略 3：MA5 突破 MA20
        elif self._check_ma_crossover(data):
            signal = {
                'symbol': symbol,
                'strategy': 'ma_crossover',
                'price': data.last_price,
                'ma5': data.ma5,
                'ma20': data.ma20,
                'confidence': 75,
                'reason': f"MA5({data.ma5:.1f}) > MA20({data.ma20:.1f})"
            }
        
        if signal:
            signal['timestamp'] = datetime.now().isoformat()
            self.signals_sent_today[symbol] = datetime.now()
            self.signals_generated += 1
            
            logger.info(
                f"🎯 信號！{symbol} {signal['strategy']} @ ${signal['price']:.2f} | "
                f"{signal['reason']}"
            )
            
            # 觸發回調
            for callback in self.signal_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(signal)
                    else:
                        callback(signal)
                except Exception as e:
                    logger.error(f"回調執行失敗: {e}")
    
    def _check_vwap_breakout(self, data: RealtimeStockData) -> bool:
        """檢查 VWAP 突破"""
        if data.vwap <= 0 or len(data.ticks) < 10:
            return False
        
        deviation = data.get_deviation()
        
        # 突破條件：剛突破 VWAP（0.2% ~ 2%）
        if not (0.2 < deviation < 2.0):
            return False
        
        # 檢查之前是否在 VWAP 下方
        recent_prices = [t['price'] for t in list(data.ticks)[-10:-1]]
        was_below = any(p < data.vwap for p in recent_prices)
        
        if not was_below:
            return False
        
        return True
    
    def _check_momentum_burst(self, data: RealtimeStockData) -> bool:
        """檢查動能爆發"""
        change_pct = data.get_change_pct()
        
        # 漲幅 2.5% ~ 5%
        if not (2.5 <= change_pct <= 5.0):
            return False
        
        # 價格在高點附近
        if data.high > 0:
            high_ratio = data.last_price / data.high
            if high_ratio < 0.97:
                return False
        
        return True
    
    def _check_ma_crossover(self, data: RealtimeStockData) -> bool:
        """檢查 MA 交叉"""
        if data.ma5 <= 0 or data.ma20 <= 0:
            return False
        
        # MA5 > MA20 且差距不大（剛交叉）
        ma_diff = (data.ma5 - data.ma20) / data.ma20 * 100
        
        if not (0 < ma_diff < 1.0):
            return False
        
        return True
    
    def stop(self):
        """停止監控"""
        self.is_running = False
        logger.info("🛑 WebSocket 監控已停止")
    
    def get_status(self) -> Dict:
        """獲取監控狀態"""
        return {
            'is_running': self.is_running,
            'watchlist_count': len(self.watchlist),
            'subscribed_count': len(self.subscribed_symbols),
            'ticks_received': self.ticks_received,
            'signals_generated': self.signals_generated,
            'signals_sent_today': len(self.signals_sent_today),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_all_stock_data(self) -> Dict:
        """獲取所有股票的即時數據"""
        return {
            symbol: data.to_dict() 
            for symbol, data in self.stock_data.items()
            if data.last_price > 0
        }
    
    def reset_daily(self):
        """每日重置"""
        self.signals_sent_today.clear()
        self.ticks_received = 0
        self.signals_generated = 0
        
        for data in self.stock_data.values():
            data.ticks.clear()
            data.vwap = 0
            data.volume_total = 0
            data.pv_total = 0
            data.high = 0
            data.low = float('inf')
            data.open = 0
        
        logger.info("🔄 WebSocket 監控已重置（每日）")


# 導出單例
try:
    from fubon_client import fubon_client
    websocket_monitor = WebSocketMonitor(fubon_client.sdk)
except Exception:
    websocket_monitor = WebSocketMonitor(None)

ws_monitor = websocket_monitor # 相容舊代碼
