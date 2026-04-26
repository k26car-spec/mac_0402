"""
富邦 WebSocket 串流管理器
包含自動重連、心跳機制

解決 WebSocket 斷線問題：
1. 加入 2330 (台積電) 作為心跳包
2. 自動重連機制
3. 事件綁定
"""

import time
import json
import logging
import threading
from typing import List, Callable, Dict, Any, Optional
from datetime import datetime
from websocket import WebSocketConnectionClosedException

logger = logging.getLogger(__name__)


class FubonStreamer:
    """富邦 WebSocket 串流管理器"""
    
    def __init__(self, sdk_instance, symbols: List[str] = None):
        """
        :param sdk_instance: 已經登入的 FubonSDK 物件
        :param symbols: 要監控的股票代碼列表
        """
        self.sdk = sdk_instance
        self.target_symbols = symbols or []
        self.is_running = False
        self.stock_client = None
        self.stream_thread = None
        
        # 心跳股票 (台積電，交易量大，確保有數據流)
        self.heartbeat_symbol = '2330'
        self.is_heartbeat_only = False
        
        # 數據快取
        self.trades: Dict[str, List[dict]] = {}
        self.orderbooks: Dict[str, dict] = {}
        self.last_update: Dict[str, datetime] = {}
        
        # 確保心跳股票在列表中
        if self.heartbeat_symbol not in self.target_symbols:
            self.target_symbols.append(self.heartbeat_symbol)
            self.is_heartbeat_only = True
        else:
            self.is_heartbeat_only = False
        
        logger.info(f"📊 FubonStreamer 初始化: 監控 {len(self.target_symbols)} 檔股票 (含五檔與成交)")

    def set_on_trade(self, callback: Callable):
        """設定成交回調"""
        self.on_trade_callback = callback
    
    def set_on_quote(self, callback: Callable):
        """設定報價回調"""
        self.on_quote_callback = callback

    def _on_message(self, message):
        """處理接收到的報價與五檔"""
        try:
            data = json.loads(message) if isinstance(message, str) else message
            channel = data.get('channel', '')
            event = data.get('event', '')
            
            if event != 'data':
                return
                
            payload = data.get('data', {})
            symbol = payload.get('symbol', data.get('symbol', ''))
            
            # --- 處理成交明細 (trades) ---
            if channel == 'trades':
                price = payload.get('price')
                volume = payload.get('size', payload.get('volume', 0))
                
                if price and price > 0:
                    # 快取最近成交 (保留 50 筆)
                    if symbol not in self.trades:
                        self.trades[symbol] = []
                    
                    trade_info = {
                        'symbol': symbol,
                        'price': float(price),
                        'volume': int(volume),
                        'side': 'buy' if payload.get('tick_type', 0) == 1 else 'sell',
                        'time': payload.get('time') or datetime.now().strftime('%H:%M:%S'),
                        'timestamp': datetime.now()
                    }
                    self.trades[symbol].append(trade_info)
                    if len(self.trades[symbol]) > 50:
                        self.trades[symbol].pop(0)
                        
                    self.last_update[symbol] = datetime.now()
                    
                    if self.vwap_enabled:
                        try:
                            from app.services.vwap_tracker import vwap_tracker
                            vwap_tracker.update(symbol, float(price), int(volume))
                        except Exception:
                            pass
                    
                    if self.on_trade_callback:
                        self.on_trade_callback(trade_info)
                        
                logger.debug(f"[Streamer] {symbol} 成交: ${price} x {volume}")

            # --- 處理五檔資料 (books) ---
            elif channel == 'books':
                self.orderbooks[symbol] = {
                    "symbol": symbol,
                    "lastPrice": float(payload.get("close", 0) or payload.get("price", 0) or 0),
                    "bids": [
                        {"price": float(b["price"]), "volume": int(b.get("size", b.get("volume", 0)))}
                        for b in payload.get("bids", [])[:5]
                    ],
                    "asks": [
                        {"price": float(a["price"]), "volume": int(a.get("size", a.get("volume", 0)))}
                        for a in payload.get("asks", [])[:5]
                    ],
                    "totalBidVolume": sum(int(b.get("size", b.get("volume", 0))) for b in payload.get("bids", [])),
                    "totalAskVolume": sum(int(a.get("size", a.get("volume", 0))) for a in payload.get("asks", [])),
                    "source": "fubon_streamer",
                    "timestamp": str(payload.get("time", ""))
                }
                self.last_update[symbol] = datetime.now()
                
                if self.on_quote_callback:
                    self.on_quote_callback(self.orderbooks[symbol])

        except Exception as e:
            logger.debug(f"解析訊息錯誤: {e}")

    def _on_connect(self):
        """連線成功"""
        logger.info("✅ 富邦 WebSocket 連線成功")

    def _on_disconnect(self, code, reason):
        """斷線處理"""
        logger.warning(f"⚠️ 富邦 WebSocket 斷線 (Code: {code}, Reason: {reason})")

    def _on_error(self, error):
        """錯誤處理"""
        logger.error(f"❌ 富邦 WebSocket 錯誤: {error}")

    def _stream_loop(self):
        """串流主迴圈 (含自動重連)"""
        
        try:
            self.stock_client = self.sdk.marketdata.websocket_client.stock
        except Exception as e:
            logger.error(f"無法獲取 stock_client: {e}")
            return
        
        # 綁定事件
        self.stock_client.on('message', self._on_message)
        self.stock_client.on('connect', self._on_connect)
        self.stock_client.on('disconnect', self._on_disconnect)
        self.stock_client.on('error', self._on_error)
        
        while self.is_running:
            try:
                logger.info(f"🚀 開始連線，訂閱清單: {self.target_symbols}")
                self.stock_client.connect()
                
                # 訂閱股票 (成交與五檔)
                for symbol in self.target_symbols:
                    try:
                        # 訂閱成交
                        self.stock_client.subscribe({
                            'channel': 'trades',
                            'symbol': symbol
                        })
                        # 訂閱五檔
                        self.stock_client.subscribe({
                            'channel': 'books',
                            'symbol': symbol
                        })
                        logger.debug(f"已訂閱 {symbol} trades & books")
                    except Exception as sub_e:
                        logger.warning(f"訂閱 {symbol} 失敗: {sub_e}")
                
                # 監控迴圈
                while self.is_running:
                    time.sleep(5)
                    
            except (WebSocketConnectionClosedException, ConnectionError) as e:
                logger.warning(f"🔥 偵測到斷線: {e}")
                if self.is_running:
                    logger.info("⏳ 5 秒後嘗試重新連線...")
                    try:
                        self.stock_client.disconnect()
                    except:
                        pass
                    time.sleep(5)
                    continue
                    
            except Exception as e:
                logger.error(f"串流異常: {e}")
                if self.is_running:
                    time.sleep(5)
                    continue
        
        logger.info("📴 串流已停止")

    def start(self):
        """啟動串流 (非阻塞)"""
        if self.is_running:
            logger.warning("Streamer 已在運行")
            return
        
        self.is_running = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()
        logger.info("🟢 Fubon Streamer 已啟動")

    def stop(self):
        """停止串流"""
        self.is_running = False
        if self.stock_client:
            try:
                self.stock_client.disconnect()
            except:
                pass
        logger.info("🔴 Fubon Streamer 已停止")

    def add_symbol(self, symbol: str):
        """動態添加監控股票"""
        if symbol not in self.target_symbols:
            self.target_symbols.append(symbol)
            if self.stock_client and self.is_running:
                try:
                    self.stock_client.subscribe({
                        'channel': 'trades',
                        'symbol': symbol
                    })
                    logger.info(f"➕ 已添加監控: {symbol}")
                except Exception as e:
                    logger.warning(f"訂閱 {symbol} 失敗: {e}")

    def remove_symbol(self, symbol: str):
        """移除監控股票"""
        if symbol in self.target_symbols and symbol != self.heartbeat_symbol:
            self.target_symbols.remove(symbol)
            if self.stock_client:
                try:
                    self.stock_client.unsubscribe({
                        'channel': 'trades',
                        'symbol': symbol
                    })
                    logger.info(f"➖ 已移除監控: {symbol}")
                except Exception:
                    pass

    def get_status(self) -> Dict[str, Any]:
        """獲取狀態"""
        return {
            'is_running': self.is_running,
            'symbols': self.target_symbols,
            'heartbeat_symbol': self.heartbeat_symbol,
            'timestamp': datetime.now().isoformat()
        }


# 全局實例
fubon_streamer: Optional[FubonStreamer] = None


def init_streamer(sdk_instance, symbols: List[str] = None) -> FubonStreamer:
    """初始化並啟動串流器"""
    global fubon_streamer
    
    if fubon_streamer and fubon_streamer.is_running:
        fubon_streamer.stop()
    
    fubon_streamer = FubonStreamer(sdk_instance, symbols)
    fubon_streamer.start()
    
    return fubon_streamer


def get_streamer() -> Optional[FubonStreamer]:
    """獲取串流器實例"""
    return fubon_streamer
