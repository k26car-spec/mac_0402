from typing import Optional, Dict, Any
import logging
import os
import ssl
import asyncio
import websocket

# #### 富邦 WebSocket SSL 設定 ####
# 富邦 WebSocket 使用自簽名憑證，需要跳過 SSL 驗證
# 透過環境變數 FUBON_SSL_SKIP 控制（預設啟用，因為富邦憑證問題）
# 生產環境可設定 FUBON_SSL_SKIP=0 來啟用 SSL 驗證

FUBON_SSL_SKIP = os.getenv("FUBON_SSL_SKIP", "1") == "1"

if FUBON_SSL_SKIP:
    # Patch websocket 的 run_forever 方法，注入 sslopt 參數
    _original_run_forever = websocket.WebSocketApp.run_forever

    def _patched_run_forever(self, **kwargs):
        """注入 SSL 選項以跳過憑證驗證"""
        if 'sslopt' not in kwargs:
            kwargs['sslopt'] = {
                "cert_reqs": ssl.CERT_NONE,
                "check_hostname": False
            }
        try:
            return _original_run_forever(self, **kwargs)
        except websocket.WebSocketException as e:
            # 🆕 忽略 socket already opened 錯誤
            if "already opened" in str(e):
                pass
            else:
                raise

    websocket.WebSocketApp.run_forever = _patched_run_forever
    
    # 也設定 HTTPS context（影響 REST API）
    ssl._create_default_https_context = ssl._create_unverified_context
# ################################

logger = logging.getLogger(__name__)

class FubonClient:
    """富邦 SDK 客戶端封裝"""
    
    def __init__(self):
        self.sdk = None
        self.is_connected = False
        self.credentials = None
        self.active_account = None  # ✅ 用於query_symbol_quote
        self.streamer = None  # 🆕 WebSocket 串流管理器
        
    async def connect(self) -> bool:
        """連接到富邦 API"""
        try:
            # 動態載入 fubon_neo
            try:
                from fubon_neo.sdk import FubonSDK
            except ImportError:
                # 嘗試不同的導入路徑，以防版本差異
                import fubon_neo
                from fubon_neo import FubonSDK
            
            logger.info("[FubonClient] Loading fubon_neo SDK...")
            self.sdk = FubonSDK()
            
            # ✅ 延遲導入 - 在這裡才導入和讀取憑證
            # 確保環境變數已經被加載
            from dotenv import load_dotenv
            env_path = '/Users/Mac/Documents/ETF/AI/Ａi-catch/.env'
            load_dotenv(env_path)  # 使用絕對路徑
            logger.info(f"[FubonClient] Reloaded environment variables from {env_path}")
            
            # 現在才導入和獲取憑證
            from fubon_config import get_decrypted_credentials
            self.credentials = get_decrypted_credentials()
            
            if not self.credentials["user_id"] or not self.credentials["password"]:
                logger.warning("[FubonClient] Missing credentials")
                return False

            logger.info(f"[FubonClient] Logging in with User ID: {self.credentials['user_id'][:3]}***")
            
            # 檢查憑證檔案是否存在
            if self.credentials["cert_path"] and not os.path.exists(self.credentials["cert_path"]):
                logger.warning(f"[FubonClient] Certificate file not found at {self.credentials['cert_path']}")
            
            accounts = self.sdk.login(
                self.credentials["user_id"],
                self.credentials["password"],
                self.credentials["cert_path"],
                self.credentials["cert_password"]
            )
            
            logger.info(f"[FubonClient] Login successful: {accounts}")
            logger.info(f"[FubonClient] Accounts type: {type(accounts)}")
            
            # ✅ 處理不同格式的 accounts 返回值
            try:
                # 嘗試獲取帳戶列表
                if hasattr(accounts, 'data'):
                    # CustomReturnType 格式
                    account_list = accounts.data if accounts.data else []
                    logger.info(f"[FubonClient] Got accounts.data: {account_list}")
                elif hasattr(accounts, '__iter__') and not isinstance(accounts, str):
                    account_list = list(accounts)
                else:
                    account_list = [accounts] if accounts else []
                
                if account_list:
                    self.active_account = account_list[0]
                    logger.info(f"[FubonClient] Active account: {self.active_account}")
                else:
                    logger.warning("[FubonClient] No accounts found")
                    self.active_account = None
            except Exception as acc_e:
                logger.warning(f"[FubonClient] Error processing accounts: {acc_e}")
                self.active_account = accounts  # 直接使用返回值
            
            # 🆕 啟用 WebSocket 實時數據
            try:
                logger.info("[FubonClient] Initializing realtime WebSocket...")
                self.sdk.init_realtime()
                logger.info("[FubonClient] ✅ WebSocket 已啟用")
            except Exception as ws_e:
                logger.warning(f"[FubonClient] ⚠️ WebSocket 初始化失敗: {ws_e}")
                logger.info("[FubonClient] 將使用 REST API 作為備援")
            
            self.is_connected = True
            logger.info("[FubonClient] ✅ Connected to Fubon API")
            
            # 🚀 啟動持久化 Streamer (負責所有 WebSocket 訂閱)
            try:
                from fubon_streamer import FubonStreamer
                if not self.streamer or not self.streamer.is_running:
                    # 預設監控一些權值股作為心跳
                    default_symbols = ['2330', '2317', '2454', '2313']
                    # 從環境變數或資料庫載入更多... 目前先用預設
                    self.streamer = FubonStreamer(self.sdk, default_symbols)
                    self.streamer.start()
                    logger.info("[FubonClient] 🚀 WebSocket Streamer 已啟動")
            except Exception as stream_e:
                logger.warning(f"[FubonClient] Streamer 啟動失敗: {stream_e}")
            
            return True
            
        except Exception as e:
            logger.error(f"[FubonClient] Connection failed: {e}")
            self.is_connected = False
            return False
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """取得即時報價 - 使用正確的SDK方法 (含自動重連)"""
        # 🆕 增強的連線檢查與重連
        max_retries = 2
        for retry in range(max_retries):
            if not self.is_connected:
                logger.info(f"[FubonClient] 連線斷開，嘗試重連... (第 {retry+1} 次)")
                success = await self.connect()
                if not success:
                    if retry < max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                    return None
            
            if not self.active_account:
                logger.error("[FubonClient] No active account for query_symbol_quote")
                return None
            
            try:
                # 移除 .TW / .TWO 後綴
                clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
                
                # 🆕 優先使用行情 REST API 獲取最準確數據 (含盤後/VWAP)
                price = 0
                vwap = 0
                stock_name = None
                data = None
                
                try:
                    if hasattr(self.sdk, 'marketdata') and self.sdk.marketdata:
                        # 1. 獲取基本行情 (Price, High, Low, Volume, VWAP)
                        m_res = self.sdk.marketdata.rest_client.stock.intraday.quote(symbol=clean_symbol)
                        if m_res:
                            data = m_res
                            # 處理物件或字典格式
                            price = float(getattr(data, 'last_price', 0) or getattr(data, 'close_price', 0) or 0)
                            if not price and isinstance(data, dict):
                                price = float(data.get('last_price', 0) or data.get('close_price', 0) or 0)
                            
                            vwap = float(getattr(data, 'avg_price', 0) or 0)
                            if not vwap and isinstance(data, dict):
                                vwap = float(data.get('avg_price', 0) or 0)
                                
                        # 2. 獲取標的名稱
                        t_res = self.sdk.marketdata.rest_client.stock.intraday.ticker(symbol=clean_symbol)
                        if t_res:
                            stock_name = getattr(t_res, 'name', None) or (t_res.get('name') if isinstance(t_res, dict) else None)
                except Exception as m_e:
                    logger.debug(f"[FubonClient] MarketData REST API 獲取失敗: {m_e}")

                # 3. 備援使用原本的 query_symbol_quote (僅限盤中)
                if not price:
                    try:
                        q_res = self.sdk.stock.query_symbol_quote(self.active_account, clean_symbol)
                        q_data = getattr(q_res, 'data', q_res)
                        price = float(getattr(q_data, 'last_price', 0) or getattr(q_data, 'reference_price', 0) or 0)
                        if not data: data = q_data
                    except:
                        pass

                if not price or price == 0:
                    logger.warning(f"[FubonClient] 無法獲取 {clean_symbol} 的有效價格")
                    return None
                
                # 💡 如果 vwap 為 0，回退到現價
                if not vwap or vwap == 0:
                    vwap = price

                # 轉換為統一格式
                quote = {
                    "symbol": symbol,
                    "name": stock_name,
                    "price": price,
                    "vwap": vwap,
                    "prev_close": float(getattr(data, 'reference_price', 0) or 0) if data else 0,
                    "open": float(getattr(data, 'open_price', price) or price) if data else price,            
                    "high": float(getattr(data, 'high_price', price) or price) if data else price,            
                    "low": float(getattr(data, 'low_price', price) or price) if data else price,               
                    "volume": int(getattr(data, 'total_volume', 0) or 0) if data else 0,        
                    "bid": float(getattr(data, 'bid_price', 0) or 0) if data else 0,   
                    "ask": float(getattr(data, 'ask_price', 0) or 0) if data else 0,   
                    "limitUp": float(getattr(data, 'limitup_price', 0) or 0) if data else 0,      
                    "limitDown": float(getattr(data, 'limitdown_price', 0) or 0) if data else 0, 
                    "time": getattr(data, 'update_time', None) if data else None,
                    "change": 0,
                    "source": "fubon"
                }
                
                # 特殊處理字典格式的屬性獲取 (防止 getattr 失敗)
                if isinstance(data, dict):
                    for key in ["prev_close", "open", "high", "low", "volume"]:
                        # 對應富邦鍵名
                        fb_key = {"prev_close": "reference_price", "open": "open_price", "high": "high_price", "low": "low_price", "volume": "total_volume"}.get(key, key)
                        if data.get(fb_key): quote[key] = data[fb_key]

                return quote
                
            except Exception as e:
                error_str = str(e).lower()
                # 🆕 偵測連線相關錯誤，自動重連
                if any(kw in error_str for kw in ["connection", "closed", "websocket", "socket", "timeout"]):
                    logger.warning(f"[FubonClient] 連線錯誤: {e}，標記需要重連")
                    self.is_connected = False
                    if retry < max_retries - 1:
                        await asyncio.sleep(0.5)
                        continue
                else:
                    logger.error(f"[FubonClient] getQuote error for {symbol}: {e}")
                return None
        
        return None
    
    async def get_candles(
        self, 
        symbol: str, 
        from_date: str, 
        to_date: str,
        timeframe: str = "D"
    ) -> Optional[list]:
        """取得歷史 K 線"""
        if not self.is_connected:
            await self.connect()
        
        if not self.is_connected:
            return None
        
        # 🆕 檢查 marketdata 是否可用（WebSocket 已禁用）
        if not hasattr(self.sdk, 'marketdata') or self.sdk.marketdata is None:
            logger.debug(f"[FubonClient] marketdata 不可用，跳過 get_candles (WebSocket 已禁用)")
            return None
        
        try:
            clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
            
            candles = self.sdk.marketdata.rest_client.stock.historical.candles(
                symbol=clean_symbol,
                **{"from": from_date, "to": to_date},
                timeframe=timeframe
            )
            
            if not candles or not candles.get('data'):
                return None
            
            return candles['data']
            
        except Exception as e:
            logger.error(f"[FubonClient] getCandles error for {symbol}: {e}")
            return None
    
    async def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        取得五檔掛單數據 - 優先使用 Streamer 快取
        """
        if not self.is_connected:
            await self.connect()
        
        clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
        
        # 1. 檢查 Streamer 是否有快取
        if self.streamer and self.streamer.is_running:
            # 如果還沒監控這支股票，動態加入
            if clean_symbol not in self.streamer.target_symbols:
                logger.info(f"[FubonClient] 動態添加 {clean_symbol} 到 Streamer 監控清單")
                self.streamer.add_symbol(clean_symbol)
            
            # 從快取獲取資料
            if clean_symbol in self.streamer.orderbooks:
                # 檢查資料是否太舊 (超過 10 秒)
                last_time = self.streamer.last_update.get(clean_symbol)
                if last_time and (datetime.now() - last_time).total_seconds() < 10:
                    return self.streamer.orderbooks[clean_symbol]
                else:
                    logger.debug(f"[FubonClient] {clean_symbol} 五檔快取過期，等待推送...")
            
            # 等待一小段時間讓串流接收數據
            import asyncio
            for _ in range(6): # 最多等 3 秒
                await asyncio.sleep(0.5)
                if clean_symbol in self.streamer.orderbooks:
                    return self.streamer.orderbooks[clean_symbol]
        
        # 2. 如果 Streamer 不可用，回退到原始方式 (或返回失敗)
        logger.warning(f"[FubonClient] Streamer 無法提供 {clean_symbol} 五檔資料")
        return None
    
    async def get_trades(self, symbol: str, count: int = 50) -> Optional[list]:
        """
        取得成交明細數據 (Time & Sales)
        
        訂閱富邦 WebSocket 的 trades channel 獲取即時成交資料
        
        Args:
            symbol: 股票代碼
            count: 最多返回的成交筆數（預設50筆）
        
        Returns:
            成交明細列表，每筆包含：
            - time: 成交時間
            - price: 成交價
            - volume: 成交量（張）
            - side: 買盤/賣盤 (buy/sell)
            - tick_type: 內盤/外盤 (0/1)
        
        官方文檔: https://www.fbs.com.tw/TradeAPI/docs/market-data/websocket-api/market-data-channels/trades/
        """
        if not self.is_connected:
            success = await self.connect()
            if not success:
                return None
        
        # 🆕 檢查 marketdata 是否可用（WebSocket 已禁用）
        if not hasattr(self.sdk, 'marketdata') or self.sdk.marketdata is None:
            logger.debug(f"[FubonClient] marketdata 不可用，跳過 get_trades (WebSocket 已禁用)")
            return []  # 返回空列表而非錯誤
        
        try:
            import asyncio
            clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
            
            logger.info(f"[FubonClient] 嘗試取得 {clean_symbol} 成交明細 (WebSocket)...")
            
            # 取得 WebSocket Client
            ws_stock = self.sdk.marketdata.websocket_client.stock
            
            # 用於儲存接收到的數據
            trades_data = {"received": False, "data": [], "connected": False}
            
            # 設定事件處理器
            def handle_connect():
                logger.info("[FubonClient] 🔌 WebSocket 已連線 (trades)")
                trades_data["connected"] = True
            
            def handle_message(message):
                logger.debug(f"[FubonClient] 📨 收到 trades 訊息: {message}")
                try:
                    import json
                    if isinstance(message, str):
                        msg = json.loads(message)
                    else:
                        msg = message
                    
                    # 檢查是否為成交數據
                    if msg.get("event") == "data" and msg.get("channel") == "trades":
                        data = msg.get("data", {})
                        if data.get("symbol") == clean_symbol:
                            trades_data["received"] = True
                            
                            # 解析成交資料
                            trade_info = {
                                "time": data.get("time", ""),
                                "price": float(data.get("price", 0)),
                                "volume": int(data.get("size", data.get("volume", 0))),
                                "side": "buy" if data.get("tick_type", 0) == 1 else "sell",
                                "tick_type": data.get("tick_type", 0),  # 0=內盤, 1=外盤
                                "total_volume": int(data.get("total_volume", 0)),
                                "bid_price": float(data.get("bid_price", 0)),
                                "ask_price": float(data.get("ask_price", 0))
                            }
                            trades_data["data"].append(trade_info)
                            
                            if len(trades_data["data"]) >= count:
                                logger.info(f"[FubonClient] ✅ 已收集 {len(trades_data['data'])} 筆成交")
                except Exception as e:
                    logger.debug(f"[FubonClient] 解析 trades 訊息失敗: {e}")
            
            def handle_disconnect(code, message):
                logger.info(f"[FubonClient] ⚠️ WebSocket 已斷線 (trades): code={code}")
                trades_data["connected"] = False
            
            def handle_error(error):
                logger.error(f"[FubonClient] ❌ WebSocket 錯誤 (trades): {error}")
            
            # 綁定事件處理器
            ws_stock.on('connect', handle_connect)
            ws_stock.on('message', handle_message)
            ws_stock.on('disconnect', handle_disconnect)
            ws_stock.on('error', handle_error)
            
            # 連線 WebSocket
            logger.info("[FubonClient] 嘗試連線 WebSocket (trades)...")
            try:
                ws_stock.connect()
            except Exception as e:
                logger.error(f"[FubonClient] ❌ 連線錯誤 (trades): {e}")
                return None
            
            # 等待連線建立
            await asyncio.sleep(1)
            
            # 訂閱成交明細
            logger.info(f"[FubonClient] 訂閱 {clean_symbol} 成交明細...")
            try:
                ws_stock.subscribe({
                    'channel': 'trades',
                    'symbol': clean_symbol
                })
                logger.info("[FubonClient] ✅ trades 訂閱請求已送出")
            except Exception as e:
                logger.error(f"[FubonClient] ❌ trades 訂閱失敗: {e}")
                return None
            
            # 等待接收數據（最多 5 秒，或收集到足夠數據）
            for i in range(10):
                await asyncio.sleep(0.5)
                if len(trades_data["data"]) >= count:
                    break
            
            # 斷開連線
            try:
                ws_stock.disconnect()
            except Exception as e:
                logger.debug(f"[FubonClient] trades 斷線時發生錯誤: {e}")
            
            # 返回數據
            if trades_data["data"]:
                logger.info(f"[FubonClient] 成功取得 {clean_symbol} 成交明細: {len(trades_data['data'])} 筆")
                return trades_data["data"]
            else:
                logger.warning(f"[FubonClient] 未收到 {clean_symbol} 成交明細（可能已收盤或無交易）")
                return None
                
        except Exception as e:
            logger.error(f"[FubonClient] get_trades 錯誤: {e}")
            return None
    
    async def subscribe_realtime_trades(self, symbol: str, callback) -> bool:
        """
        訂閱即時成交串流（持續接收）
        
        Args:
            symbol: 股票代碼
            callback: 回調函數，每收到一筆成交就呼叫
        
        Returns:
            是否成功訂閱
        """
        if not self.is_connected:
            success = await self.connect()
            if not success:
                return False
        
        # 🆕 檢查 marketdata 是否可用（WebSocket 已禁用）
        if not hasattr(self.sdk, 'marketdata') or self.sdk.marketdata is None:
            logger.debug(f"[FubonClient] marketdata 不可用，跳過 subscribe_realtime_trades (WebSocket 已禁用)")
            return False
        
        try:
            clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
            ws_stock = self.sdk.marketdata.websocket_client.stock
            
            def handle_message(message):
                try:
                    import json
                    if isinstance(message, str):
                        msg = json.loads(message)
                    else:
                        msg = message
                    
                    if msg.get("event") == "data" and msg.get("channel") == "trades":
                        data = msg.get("data", {})
                        if data.get("symbol") == clean_symbol:
                            trade_info = {
                                "time": data.get("time", ""),
                                "price": float(data.get("price", 0)),
                                "volume": int(data.get("size", data.get("volume", 0))),
                                "side": "buy" if data.get("tick_type", 0) == 1 else "sell",
                                "tick_type": data.get("tick_type", 0)
                            }
                            callback(trade_info)
                except Exception as e:
                    logger.debug(f"解析即時成交失敗: {e}")
            
            ws_stock.on('message', handle_message)
            ws_stock.connect()
            ws_stock.subscribe({'channel': 'trades', 'symbol': clean_symbol})
            
            logger.info(f"[FubonClient] ✅ 已訂閱 {clean_symbol} 即時成交串流")
            return True
            
        except Exception as e:
            logger.error(f"[FubonClient] subscribe_realtime_trades 錯誤: {e}")
            return False
    
    def disconnect(self):
        """斷開連線"""
        if self.sdk:
            try:
                # 清理資源
                # self.sdk.logout() # 如果有 logout 方法
                self.is_connected = False
                logger.info("[FubonClient] Disconnected")
            except Exception as e:
                logger.error(f"[FubonClient] Disconnect error: {e}")

# 單例實例
fubon_client = FubonClient()

