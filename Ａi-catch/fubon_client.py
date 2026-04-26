from typing import Optional, Dict, Any, List
import logging
import os
import ssl
import asyncio
import websocket
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from functools import partial

# ===== TWSE 盤後交易量快取 (一次批次取全市場，不限速) =====
_TWSE_VOL_CACHE: Dict[str, int] = {}   # { symbol: volume_in_lots }
_TWSE_VOL_FETCHED_AT: Optional[datetime] = None
_TWSE_VOL_TTL = 1800  # 30 分鐘
_TWSE_VOL_LOCK: Optional[asyncio.Lock] = None  # 防止競爭條件

async def _fetch_twse_volume_cache() -> Dict[str, int]:
    """從 TWSE+TPEX 批次取今日全市場交易量（張），盤後使用"""
    global _TWSE_VOL_CACHE, _TWSE_VOL_FETCHED_AT, _TWSE_VOL_LOCK
    _log = logging.getLogger(__name__)
    now = datetime.now()
    # 快取有效直接回傳（不需等 Lock）
    if _TWSE_VOL_FETCHED_AT and (now - _TWSE_VOL_FETCHED_AT).total_seconds() < _TWSE_VOL_TTL:
        return _TWSE_VOL_CACHE
    # 建立 Lock（需在 event loop 內建立）
    if _TWSE_VOL_LOCK is None:
        _TWSE_VOL_LOCK = asyncio.Lock()
    async with _TWSE_VOL_LOCK:
        # 雙重檢查：等待 Lock 期間可能已被其他 coroutine 更新
        now = datetime.now()
        if _TWSE_VOL_FETCHED_AT and (now - _TWSE_VOL_FETCHED_AT).total_seconds() < _TWSE_VOL_TTL:
            return _TWSE_VOL_CACHE
        try:
            import httpx
            cache = {}
            async with httpx.AsyncClient(verify=False, timeout=15) as client:
                # 1. TWSE 上市
                twse_url = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_ALL?response=json"
                resp = await client.get(twse_url, headers={'User-Agent': 'Mozilla/5.0'})
                twse_data = resp.json()
                for row in twse_data.get('data', []):
                    try:
                        code = row[0].strip()
                        vol_shares = int(row[2].replace(',', ''))
                        cache[code] = vol_shares // 1000  # 股 → 張
                    except Exception:
                        pass

                # 2. TPEX 上櫃
                tpex_url = "https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php?l=zh-tw&o=json&se=AL&s=0,asc"
                resp2 = await client.get(tpex_url, headers={'User-Agent': 'Mozilla/5.0'})
                tpex_data = resp2.json()
                for table in tpex_data.get('tables', []):
                    for row in table.get('data', []):
                        try:
                            code = row[0].strip()
                            vol_shares = int(row[7].replace(',', ''))
                            cache[code] = vol_shares // 1000  # 股 → 張
                        except Exception:
                            pass

            if cache:
                _TWSE_VOL_CACHE = cache
                _TWSE_VOL_FETCHED_AT = now
                _log.info(f"[TWSE/TPEX] 📊 取得 {len(cache)} 支股票盤後交易量（上市+上櫃）2337={cache.get('2337',0):,}張")
            return _TWSE_VOL_CACHE
        except Exception as e:
            _log.debug(f"[TWSE/TPEX] 取交易量失敗: {e}")
            return _TWSE_VOL_CACHE

# #### 富邦 WebSocket 異常靜默修補 ####
FUBON_SSL_SKIP = os.getenv("FUBON_SSL_SKIP", "1") == "1"

try:
    import fubon_neo.fugle_marketdata.websocket.client as fb_ws
    _orig_fb_send_ping = fb_ws.WebSocketClient.send_ping
    def _patched_fb_send_ping(self):
        try:
            return _orig_fb_send_ping(self)
        except (AttributeError, Exception):
            # 靜默處理背景執行緒的連線異常，防止日誌洗版與崩潰
            pass
    fb_ws.WebSocketClient.send_ping = _patched_fb_send_ping
    
    _orig_fb_send = fb_ws.WebSocketClient.ping # 可能是 ping 方法調用 __send
    # 有些版本是 __send (私有方法需要特殊處理)，如果是 __send 則跳過
except:
    pass

if FUBON_SSL_SKIP:
    _original_run_forever = websocket.WebSocketApp.run_forever
    def _patched_run_forever(self, **kwargs):
        if 'sslopt' not in kwargs:
            kwargs['sslopt'] = {"cert_reqs": ssl.CERT_NONE, "check_hostname": False}
        try: return _original_run_forever(self, **kwargs)
        except Exception: pass
    websocket.WebSocketApp.run_forever = _patched_run_forever
    ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)

class FubonClient:
    """富邦 SDK 客戶端封裝 - 異步增強版"""
    
    def __init__(self):
        self.sdk = None
        self.is_connected = False
        self.credentials = None
        self.active_account = None  
        self.streamer = None  
        self.executor = ThreadPoolExecutor(max_workers=20)  # ✅ 線程池處理同步 SDK
        self._is_connecting = False
        self._last_connect_attempt = 0
        self._connect_cooldown = 10
        self._ws_handlers_setup = False
        self._shared_trades_callbacks = []
        
    async def connect(self) -> bool:
        """連接到富邦 API (異步) - 具備冷卻與併發保護"""
        if self._is_connecting:
            return False
            
        import time
        now = time.time()
        if now - self._last_connect_attempt < self._connect_cooldown:
            logger.debug(f"[FubonClient] 連接冷卻中... 尚需等待 {int(self._connect_cooldown - (now - self._last_connect_attempt))} 秒")
            return False
            
        self._is_connecting = True
        self._last_connect_attempt = now
        
        try:
            from fubon_neo.sdk import FubonSDK
            
            # 使用線程池初始化 SDK
            # 如果已有 SDK 且正在報錯，可能需要重新建立整個物件，但為了穩定性我們先只做 login 重連
            if not self.sdk:
                self.sdk = await asyncio.get_event_loop().run_in_executor(
                    self.executor, 
                    FubonSDK
                )
            
            from dotenv import load_dotenv
            env_path = '/Users/Mac/Documents/ETF/AI/Ａi-catch/.env'
            load_dotenv(env_path)
            
            from fubon_config import get_decrypted_credentials
            self.credentials = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                get_decrypted_credentials
            )
            
            if not self.credentials["user_id"] or not self.credentials["password"]:
                return False

            # 登入為同步阻塞，必須在線程池運行
            logger.info(f"[FubonClient] Logging in as {self.credentials['user_id'][:3]}***")
            accounts = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                partial(
                    self.sdk.login,
                    self.credentials["user_id"],
                    self.credentials["password"],
                    self.credentials["cert_path"],
                    self.credentials["cert_password"]
                )
            )
            
            # 處理帳戶清單
            if hasattr(accounts, 'data') and accounts.data:
                self.active_account = accounts.data[0]
            elif isinstance(accounts, list) and accounts:
                self.active_account = accounts[0]
            else:
                self.active_account = accounts
                
            # 啟動即時行情 (REST API 所需，即使 WebSocket 禁用也建議啟動)
            try:
                await asyncio.to_thread(self.sdk.init_realtime)
                logger.info("[FubonClient] ✅ init_realtime() 已啟動 (支援 REST 5檔)")
            except Exception as e:
                logger.warning(f"[FubonClient] init_realtime() 啟動失敗 (可能 WebSocket 異常): {e}")

            # 暫時禁用即時行情 WebSocket 以穩定系統 (WebSocket currently causing 400 Bad Request)
            logger.info("[FubonClient] ⚠️ WebSocket 即時行情已監控但不主動訂閱 (優先使用 REST API)")
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"[FubonClient] Connection failed: {e}")
            self.is_connected = False
            return False
        finally:
            self._is_connecting = False

    def _setup_ws_handlers(self):
        """設置全域 WebSocket 處理器 (僅執行一次)"""
        if self._ws_handlers_setup or not hasattr(self.sdk, 'marketdata'):
            return
            
        try:
            ws_stock = self.sdk.marketdata.websocket_client.stock
            
            def handle_connect():
                logger.debug("[FubonClient] 🔌 WebSocket 已連線")
                self.is_connected = True
                
            def handle_disconnect(code, message):
                logger.debug(f"[FubonClient] ⚠️ WebSocket 已斷線: code={code}")
                self.is_connected = False
                
            def handle_error(error):
                # 靜默處理常見的連線異常
                err_msg = str(error).lower()
                if "closed" in err_msg or "sock" in err_msg:
                    logger.debug(f"[FubonClient] 📡 WebSocket 連線異常 (已靜默): {error}")
                else:
                    logger.error(f"[FubonClient] ❌ WebSocket 錯誤: {error}")
                    
            def handle_message(message):
                # 這裡可以分發訊息給各個訂閱者
                # 目前主要給 websocket_monitor 使用
                pass

            ws_stock.on('connect', handle_connect)
            ws_stock.on('disconnect', handle_disconnect)
            ws_stock.on('error', handle_error)
            # message 處理由各個具體訂閱者自行處理，或統一分發
            
            self._ws_handlers_setup = True
            logger.info("[FubonClient] ✅ 全域 WebSocket 處理器已設置")
        except Exception as e:
            logger.error(f"[FubonClient] 設置 WebSocket 處理器失敗: {e}")

    async def batch_get_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        tasks = [self.get_quote(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            sym: res if not isinstance(res, Exception) else None
            for sym, res in zip(symbols, results)
        }

    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """取得即時報價 - 使用正確的SDK方法 (含自動重連)"""

        # ── 非交易時段（週末或盤後）直接用 yfinance 收盤價 ──
        from datetime import time as _time
        _now = datetime.now()
        _is_weekend   = _now.weekday() >= 5          # 週六=5, 週日=6
        _is_pre_open  = _now.time() < _time(9, 0)    # 開盤前
        _is_after_cls = _now.time() > _time(13, 35)  # 盤後（多 5 分鐘緩衝）
        _use_yf_close = _is_weekend or _is_pre_open or _is_after_cls

        if _use_yf_close:
            try:
                import yfinance as _yf, asyncio as _aio
                clean_sym = symbol.replace('.TW','').replace('.TWO','')
                for suffix in ['.TW', '.TWO']:
                    _tk = _yf.Ticker(f'{clean_sym}{suffix}')
                    _hist = await _aio.to_thread(_tk.history, period='5d')
                    if not _hist.empty:
                        # 過濾掉週末資料，取最後一個平日收盤
                        _hist = _hist[_hist.index.dayofweek < 5]
                        if _hist.empty:
                            continue
                        _last = _hist.iloc[-1]
                        _prev = _hist.iloc[-2] if len(_hist) >= 2 else _last
                        _price      = round(float(_last['Close']), 2)
                        _prev_close = round(float(_prev['Close']), 2)
                        _change_amt = round(_price - _prev_close, 2)
                        _change_pct = round(_change_amt / _prev_close * 100, 2) if _prev_close else 0
                        logger.info(f"[FubonClient] 📅 非交易時段 → yfinance 收盤價 {clean_sym}: {_price} (昨收 {_prev_close})")
                        return {
                            "price":          _price,
                            "prev_close":     _prev_close,
                            "change_amount":  _change_amt,
                            "change_percent": _change_pct,
                            "change":         _change_pct,
                            "open":           round(float(_last['Open']), 2),
                            "high":           round(float(_last['High']), 2),
                            "low":            round(float(_last['Low']), 2),
                            "volume":         int(_last['Volume']) // 1000,
                            "vwap":           _price,
                            "source":         "Yahoo(收盤)",
                            "symbol":         symbol,
                            "name":           "",   # 不回傳代碼，讓前端保留原有名稱
                        }
            except Exception as _yf_e:
                logger.warning(f"[FubonClient] 非交易時段 yfinance 備援失敗 {symbol}: {_yf_e}")
            # yfinance 也失敗就走底下原有流程

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
                # 🆕 自癒機制：如果 marketdata 遺失，嘗試重新初始化
                if self.is_connected and (not hasattr(self.sdk, 'marketdata') or not self.sdk.marketdata):
                    try:
                        await asyncio.to_thread(self.sdk.init_realtime)
                        logger.info("[FubonClient] ✅ MarketData 已重新初始化")
                    except Exception as e:
                        logger.warning(f"[FubonClient] 重新初始化 MarketData 失敗: {e}")

                # 移除 .TW / .TWO 後綴
                clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
                
                # 🆕 優先使用行情 REST API 獲取最準確數據 (含盤後/VWAP)
                price = 0
                vwap = 0
                prev_close = 0 # 昨收價，用於計算漲跌幅
                stock_name = None
                data = None
                source_label = "富邦API"
                
                try:
                    if hasattr(self.sdk, 'marketdata') and self.sdk.marketdata:
                        # 1. 獲取基本行情 (Price, High, Low, Volume, VWAP)
                        # 增加 timeout 防止卡死
                        m_res = await asyncio.wait_for(
                            asyncio.to_thread(self.sdk.marketdata.rest_client.stock.intraday.quote, symbol=clean_symbol),
                            timeout=3.0
                        )
                        
                        if m_res:
                            data = m_res
                            # 處理物件或字典格式
                            price = float(getattr(data, 'last_price', 0) or getattr(data, 'close_price', 0) or 0)
                            if not price and isinstance(data, dict):
                                price = float(data.get('last_price', data.get('close_price', 0)) or 0)

                            # 🛡️ [數據歸元]：移除所有針對 2337 的硬編碼偏見，回歸富邦實時報價。
                            if not price or price == 0:
                                ref_price = float(getattr(data, 'reference_price', 0) or 0)
                                if not ref_price and isinstance(data, dict):
                                    ref_price = float(data.get('reference_price', 0) or 0)
                                if ref_price > 0:
                                    price = ref_price
                                    logger.info(f"[FubonClient] 📊 使用官方參考價: {price} for {symbol}")
                            
                            vwap = float(getattr(data, 'avg_price', 0) or 0)
                            if not vwap and isinstance(data, dict):
                                vwap = float(data.get('avg_price', 0) or 0)
                                
                            # 昨收價 (參考價)
                            prev_close = float(getattr(data, 'reference_price', 0) or getattr(data, 'previous_close', 0) or 0)
                            if not prev_close and isinstance(data, dict):
                                prev_close = float(data.get('reference_price', data.get('previous_close', 0)) or 0)

                        # 2. 獲取標的名稱 (優先嘗試)
                        try:
                            # 檢查緩存或之前的 context (未實作，直接調用 API)
                            if not stock_name:
                                t_res = await asyncio.wait_for(
                                    asyncio.to_thread(self.sdk.marketdata.rest_client.stock.intraday.ticker, symbol=clean_symbol),
                                    timeout=2.0
                                )   
                                if t_res:
                                    # 嘗試多種可能的屬性名稱
                                    stock_name = getattr(t_res, 'name', None) or t_res.get('name') or getattr(t_res, 'symbolName', None)
                                    if stock_name:
                                        logger.info(f"[FubonClient] 🏷️ 獲取到中文名稱: {stock_name}")
                        except Exception as e:
                            logger.debug(f"[FubonClient] Name fetch warning: {e}")
                except Exception as m_e:
                    logger.debug(f"[FubonClient] MarketData REST API 獲取失敗或超時 ({symbol}): {m_e}")

                # 3. 備援使用原本的 query_symbol_quote (僅限盤中或 REST 失敗時)
                if not price:
                    try:
                        # 🆕 修正：使用 to_thread 避免阻塞事件循環
                        q_res = await asyncio.to_thread(self.sdk.stock.query_symbol_quote, self.active_account, clean_symbol)
                        q_data = getattr(q_res, 'data', q_res)
                        
                        # 處理 last_price 可能為 None 的情況
                        last_p = getattr(q_data, 'last_price', 0)
                        if last_p is None: last_p = 0
                        price = float(last_p)
                        
                        if isinstance(q_data, dict) and price == 0:
                            last_p = q_data.get('last_price', 0)
                            if last_p is None: last_p = 0
                            price = float(last_p)
                        
                        # 🆕 收盤後也允許使用 reference_price (優先級低於 last_price)
                        if not price or price == 0:
                            ref_p = getattr(q_data, 'reference_price', 0)
                            if ref_p is None: ref_p = 0  # 防止 None
                            
                            if not ref_p and isinstance(q_data, dict):
                                ref_p = q_data.get('reference_price', 0)
                            
                            ref_price = float(ref_p) if ref_p is not None else 0
                            
                            if ref_price > 0:
                                price = ref_price
                                logger.info(f"[FubonClient] 📊 Trading API 備援使用 reference_price: {price}")
                            
                        # 確保抓到昨天收盤價
                        if not prev_close:
                            ref_p = getattr(q_data, 'reference_price', 0) or getattr(q_data, 'previous_close', 0)
                            if ref_p is None: ref_p = 0
                            prev_close = float(ref_p)
                            
                            if not prev_close and isinstance(q_data, dict):
                                prev_close = float(q_data.get('reference_price', q_data.get('previous_close', 0)) or 0)
                        
                        if not data: data = q_data
                    except Exception as q_e:
                        logger.debug(f"[FubonClient] query_symbol_quote error: {q_e}")


                if not price or price <= 0:
                    # 🆕 備援使用 yfinance (保證真實數據)
                    try:
                        import yfinance as yf
                        logger.info(f"[FubonClient] 🔄 Price missing for {clean_symbol}, trying yfinance fallback...")
                        
                        # 直接獲取 5 天歷史以同時取得現價與昨收
                        for suffix in [".TW", ".TWO"]:
                            ticker = yf.Ticker(f"{clean_symbol}{suffix}")
                            hist_full = await asyncio.to_thread(ticker.history, period="5d")
                            
                            if not hist_full.empty:
                                last_row = hist_full.iloc[-1]
                                price = round(float(last_row['Close']), 2)
                                vwap = price
                                
                                # 取前一天作為昨收
                                if len(hist_full) >= 2:
                                    prev_close = round(float(hist_full.iloc[-2]['Close']), 2)
                                else:
                                    # 如果只有一天，嘗試從 info 獲取昨收
                                    ticker_info = await asyncio.to_thread(lambda: ticker.info)
                                    prev_close = float(ticker_info.get('previousClose') or ticker_info.get('regularMarketPreviousClose') or price)
                                
                                data = {
                                    "open_price": float(last_row['Open']),
                                    "high_price": float(last_row['High']),
                                    "low_price": float(last_row['Low']),
                                    "total_volume": int(last_row['Volume']) // 1000,  # yfinance 單位是「股」，除以 1000 轉換為「張」
                                    "update_time": datetime.now().isoformat()
                                }
                                logger.info(f"[FubonClient] ✅ yfinance ({suffix}) returned {price} (prev: {prev_close}) for {clean_symbol}")
                                source_label = "Yahoo"
                                break
                    except Exception as yf_e:
                        logger.error(f"[FubonClient] yfinance quote fallback failed for {clean_symbol}: {yf_e}")


                if not price or price == 0:
                    # 詳細記錄失敗原因，幫助除錯
                    if retry == max_retries - 1:
                        logger.warning(f"[FubonClient] 無法獲取 {clean_symbol} 的有效價格。")
                    return None
                
                # 💡 如果 vwap 為 0，回退到現價
                # 💡 如果 vwap 為 0，回退到現價
                if not vwap or vwap == 0:
                    vwap = price

                # 轉換為統一格式
                quote = {
                    "symbol": symbol,
                    "name": stock_name,
                    "price": price,
                    "vwap": vwap,
                    "prev_close": prev_close,
                    "open": float(getattr(data, 'open_price', price) or price) if data else price,            
                    "high": float(getattr(data, 'high_price', price) or price) if data else price,            
                    "low": float(getattr(data, 'low_price', price) or price) if data else price,               
                    "volume": int(getattr(data, 'total_volume', 0) or 0) if data else 0,        
                    "bid": float(getattr(data, 'bid_price', 0) or 0) if data else 0,   
                    "ask": float(getattr(data, 'ask_price', 0) or 0) if data else 0,   
                    "limitUp": float(getattr(data, 'limitup_price', 0) or 0) if data else 0,      
                    "limitDown": float(getattr(data, 'limitdown_price', 0) or 0) if data else 0, 
                    "time": str(getattr(data, 'update_time', datetime.now().isoformat())) if data else datetime.now().isoformat(),
                    "change": 0,
                    "source": "fubon",
                    "dataSource": source_label
                }
                
                # 特殊處理字典格式的屬性獲取 (防止 getattr 失敗)
                if isinstance(data, dict):
                    for key in ["open", "high", "low", "volume"]:
                        # 對應富邦鍵名
                        fb_key = {"open": "open_price", "high": "high_price", "low": "low_price", "volume": "total_volume"}.get(key, key)
                        val = data.get(fb_key)
                        if val is not None: quote[key] = val
                    
                    if not prev_close:
                        quote["prev_close"] = float(data.get("reference_price", 0) or 0)

                # 獲取 API 原生漲跌資訊 (如果有的話)
                api_change_price = float(data.get("change_price", 0) or 0) if isinstance(data, dict) else 0
                api_change_rate = float(data.get("change_rate", 0) or 0) if isinstance(data, dict) else 0

                # 計算 change (優先相信 API，若無則手動計算)
                calculated_change_amount = 0
                calculated_change_percent = 0
                
                if quote["prev_close"] > 0:
                    calculated_change_amount = round(quote["price"] - quote["prev_close"], 2)
                    calculated_change_percent = round(calculated_change_amount / quote["prev_close"] * 100, 2)
                
                # 決定最終使用的數值
                # 如果 API 有給 change_rate 且不為 0 (防止 API 缺值時誤用 0)，優先使用
                # 但要注意：有時候價格沒變就是 0，需結合價格判斷
                use_api_values = (api_change_rate != 0 or api_change_price != 0)
                
                quote["change_amount"] = api_change_price if use_api_values else calculated_change_amount
                quote["change_percent"] = api_change_rate if use_api_values else calculated_change_percent
                
                # 為了相容前端舊代碼，將 change 設為百分比
                quote["change"] = quote["change_percent"]

                # ✅ 盤後補充完整日量：13:30 後改用 TWSE 官方 API（一次批次、不限速）
                current_time_obj = datetime.now().time()
                from datetime import time as _time
                is_after_close = current_time_obj > _time(13, 30)
                if is_after_close:
                    try:
                        twse_vol = await _fetch_twse_volume_cache()
                        if clean_symbol in twse_vol and twse_vol[clean_symbol] > 0:
                            quote['volume'] = twse_vol[clean_symbol]
                            logger.info(f"[FubonClient] 📊 TWSE 盤後交易量: {twse_vol[clean_symbol]:,} 張 ({clean_symbol})")
                    except Exception as _ve:
                        logger.debug(f"[FubonClient] TWSE 交易量補充失敗 {clean_symbol}: {_ve}")

                logger.info(f"[FubonClient] 📈 Symbol: {symbol}, Price: {quote['price']}, Prev: {quote['prev_close']}, "
                            f"Amt: {quote['change_amount']}, Pct: {quote['change']}%, "
                            f"Source: {quote['source']} (Calc: {calculated_change_amount}/{calculated_change_percent}%, API: {api_change_price}/{api_change_rate}%)")
                return quote
                
            except Exception as e:
                error_str = str(e).lower()
                # 🆕 偵測連線相關錯誤，自動重連
                if any(kw in error_str for kw in ["connection", "closed", "websocket", "socket", "timeout"]):
                    logger.warning(f"[FubonClient] 連線錯誤 ({symbol}): {e}，標記需要重連")
                    self.is_connected = False
                    if retry < max_retries - 1:
                        await asyncio.sleep(0.5)
                        continue
                else:
                    logger.error(f"[FubonClient] getQuote error for {symbol}: {e}", exc_info=True)
                return None
        
        return None
    
    async def get_candles(
        self, 
        symbol: str, 
        from_date: str = "",
        to_date: str = "",
        timeframe: str = "D"
    ) -> Optional[list]:
        """
        取得歷史 K 線
        
        v2 升級：
        1. 加入 30 秒快取，防止 Fugle API Rate Limit (429)
        2. 如果富邦 API 失敗或無數據，自動回退到 yfinance
        3. 支援 5 分鐘線 (yfinance fallback)
        """
        clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
        cache_key = f"{clean_symbol}_{timeframe}"
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # ✨ 30 秒快取：防止對 Fugle Rate Limit 連發
        if hasattr(self, '_candle_cache'):
            cached = self._candle_cache.get(cache_key)
            if cached and (now - cached['ts']).total_seconds() < 30:
                logger.debug(f"[FubonClient] 📦 K棒快取命中 ({cache_key}), {len(cached['data'])} 根")
                return cached['data']
        else:
            self._candle_cache = {}
        
        # 1. 嘗試富邦 API
        fubon_data = []
        

        if self.is_connected and hasattr(self.sdk, 'marketdata') and self.sdk.marketdata:
            try:
                # 預設 to_date 為今天
                if not to_date: to_date = today_str
                # 預設 from_date 為 30 天前
                if not from_date: from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                
                # A. 優先獲取歷史 K 線
                logger.info(f"[FubonClient] Fetching Fubon historical candles: {from_date} ~ {to_date}")
                h_res = await asyncio.to_thread(
                    self.sdk.marketdata.rest_client.stock.historical.candles,
                    symbol=clean_symbol,
                    **{"from": from_date, "to": to_date}
                )
                
                if h_res and isinstance(h_res, dict) and h_res.get('data'):
                    fubon_data.extend(h_res['data'])

                # B. 如果包含今天，且歷史數據中沒有今天（或不夠即時），補上盤中實時 K 線
                # 注意：歷史數據 API 通常直到收盤後才會更新當日 K 線
                if to_date >= today_str:
                    logger.info(f"[FubonClient] 試圖獲取盤中實時 K 線 (Intraday API)")
                    i_res = await asyncio.to_thread(
                        self.sdk.marketdata.rest_client.stock.intraday.candles,
                        symbol=clean_symbol
                    )
                    if i_res and isinstance(i_res, dict) and i_res.get('data'):
                        intra_candles = i_res['data']
                        
                        # 💡 如果請求的是 5 分鐘線，但盤中 API 回傳的是 1 分鐘線，需進行重採樣 (Resampling)
                        if timeframe == "5" and len(intra_candles) > 0:
                            logger.info(f"[FubonClient] 進行盤中數據重採樣 (1m -> 5m)")
                            import pandas as pd  # 確保已 import
                            idf = pd.DataFrame(intra_candles)
                            idf['date'] = pd.to_datetime(idf['date'])
                            idf.set_index('date', inplace=True)
                            
                            # 每 5 分鐘一根 K 線，取 Open 的第一個，High 的最大，Low 的最小，Close 的最後，Volume 的加總
                            resampled = idf.resample('5min', label='left', closed='left').agg({
                                'open': 'first',
                                'high': 'max',
                                'low': 'min',
                                'close': 'last',
                                'volume': 'sum'
                            }).dropna()
                            
                            # 轉回原始格式
                            intra_candles = []
                            for idx, row in resampled.iterrows():
                                intra_candles.append({
                                    "date": idx.isoformat(),
                                    "open": float(row['open']),
                                    "high": float(row['high']),
                                    "low": float(row['low']),
                                    "close": float(row['close']),
                                    "volume": int(row['volume'])
                                })

                        # ✨ 修正：直接用最新 intraday 資料替換今日 K 棒
                        #    舊邏輯用前 16 字元比對去重，會把時間不同的新 K 棒當重複丟棄
                        #    新邏輯：先移除 fubon_data 中所有今日資料，再補入最新 intraday
                        fubon_data = [
                            c for c in fubon_data
                            if not c.get('date', '').startswith(today_str)
                        ] + intra_candles
                        fubon_data.sort(key=lambda x: x['date'])

                if fubon_data:
                    last_date = fubon_data[-1].get('date', '')
                    logger.info(f"[FubonClient] ✅ Fubon API returned {len(fubon_data)} candles (Last: {last_date})")
                    self._candle_cache[cache_key] = {'data': fubon_data, 'ts': now}
                    return fubon_data

            except Exception as e:
                logger.warning(f"[FubonClient] Fubon SDK get_candles 異常: {e}")

        # 2. 回退到 yfinance (保證真實數據)
        try:
            import yfinance as yf
            logger.info(f"[FubonClient] 🔄 Falling back to yfinance for {clean_symbol}")
            
            # yfinance interval 映射
            yf_interval = "1d"
            if timeframe == "1": yf_interval = "1m"
            elif timeframe == "5": yf_interval = "5m"
            
            # 決定 yfinance 獲取範圍
            yf_period = "1mo" # 預設一個月
            if timeframe in ["1", "5"]:
                yf_period = "5d" # 盤中數據限制 5 天
            
            # 優先試 .TW
            ticker_sym = f"{clean_symbol}.TW"
            ticker = yf.Ticker(ticker_sym)
            hist = await asyncio.to_thread(ticker.history, period=yf_period, interval=yf_interval)
            
            if hist.empty:
                # 試 .TWO
                ticker_sym = f"{clean_symbol}.TWO"
                ticker = yf.Ticker(ticker_sym)
                hist = await asyncio.to_thread(ticker.history, period=yf_period, interval=yf_interval)
            
            if not hist.empty:
                formatted_candles = []
                for idx, row in hist.iterrows():
                    formatted_candles.append({
                        "date": idx.isoformat(),
                        "open": float(row['Open']),
                        "high": float(row['High']),
                        "low": float(row['Low']),
                        "close": float(row['Close']),
                        "volume": int(row['Volume'])
                    })
                logger.info(f"[FubonClient] ✅ yfinance returned {len(formatted_candles)} real candles for {clean_symbol}")
                self._candle_cache[cache_key] = {'data': formatted_candles, 'ts': now}
                return formatted_candles
                
        except Exception as ey:
            logger.error(f"[FubonClient] yfinance fallback failed for {symbol}: {ey}")

        return None

    
    async def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        取得五檔掛單數據 - 使用 REST API 獲取真實 5 檔
        """
        if not self.is_connected:
            await self.connect()
        
        if not self.is_connected:
            return None
            
        clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
        
        try:
            # 🆕 自癒機制：如果 marketdata 遺失，嘗試重新初始化
            if not hasattr(self.sdk, 'marketdata') or not self.sdk.marketdata:
                await asyncio.to_thread(self.sdk.init_realtime)
            
            # 使用 REST API 獲取 quote (內含 5 檔)
            data = await asyncio.to_thread(
                self.sdk.marketdata.rest_client.stock.intraday.quote, 
                symbol=clean_symbol
            )
            
            if not data:
                return None
                
            # 即使暫無五檔數據，只要有報價就視為富邦真實來源
            bids = []
            asks = []
            
            raw_bids = getattr(data, "bids", []) or (data.get("bids", []) if isinstance(data, dict) else [])
            raw_asks = getattr(data, "asks", []) or (data.get("asks", []) if isinstance(data, dict) else [])
            
            if raw_bids:
                bids = [{"price": float(b.get("price") if isinstance(b, dict) else getattr(b, "price")), 
                         "volume": int(b.get("size", b.get("volume", 0)) if isinstance(b, dict) else getattr(b, "size", getattr(b, "volume", 0)))} 
                        for b in raw_bids[:5]]
            
            if raw_asks:
                asks = [{"price": float(a.get("price") if isinstance(a, dict) else getattr(a, "price")), 
                         "volume": int(a.get("size", a.get("volume", 0)) if isinstance(a, dict) else getattr(a, "size", getattr(a, "volume", 0)))} 
                        for a in raw_asks[:5]]
            
            last_price = getattr(data, 'last_price', 0) or (data.get('lastPrice', 0) if isinstance(data, dict) else 0)
                
            return {
                "success": True,
                "symbol": symbol,
                "source": "fubon",
                "lastPrice": float(last_price),
                "bids": bids,
                "asks": asks,
                "totalBidVolume": sum(b["volume"] for b in bids),
                "totalAskVolume": sum(a["volume"] for a in asks),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"[FubonClient] get_orderbook error for {symbol}: {e}")
            return None
    
    async def get_stock_name(self, symbol: str) -> str:
        """
        取得股票名稱 - 使用 Fubon API Ticker 查詢
        """
        if not self.is_connected:
            await self.connect()
        
        if not self.is_connected:
            return symbol
            
        clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
        
        try:
            # 🆕 自癒機制：如果 marketdata 遺失，嘗試重新初始化
            if not hasattr(self.sdk, 'marketdata') or not self.sdk.marketdata:
                await asyncio.to_thread(self.sdk.init_realtime)
            
            # 使用 REST API 獲取 ticker (內含名稱)
            res = await asyncio.to_thread(
                self.sdk.marketdata.rest_client.stock.intraday.ticker, 
                symbol=clean_symbol
            )
            
            if res:
                name = getattr(res, 'name', None) or (res.get('name') if isinstance(res, dict) else None)
                if name:
                    return name
        except Exception as e:
            logger.error(f"[FubonClient] get_stock_name error for {symbol}: {e}")
            
        return symbol

    async def get_trades(self, symbol: str, count: int = 50) -> Optional[list]:
        """
        取得成交明細數據 (Time & Sales) - 使用 REST API
        """
        if not self.is_connected:
            await self.connect()
        
        if not self.is_connected:
            return None
            
        clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
        
        try:
            # 🆕 自癒機制：如果 marketdata 遺失，嘗試重新初始化
            if not hasattr(self.sdk, 'marketdata') or not self.sdk.marketdata:
                await asyncio.to_thread(self.sdk.init_realtime)
            
            # 使用 REST API 獲取 trades
            res = await asyncio.to_thread(
                self.sdk.marketdata.rest_client.stock.intraday.trades, 
                symbol=clean_symbol
            )
            
            if not res:
                return []
                
            # 獲取 trades 列表 (相容物件與字典)
            raw_trades = getattr(res, 'trades', None) or (res.get('trades') if isinstance(res, dict) else [])
            
            if not raw_trades:
                return []
                
            # 轉換為前端統一格式
            formatted_trades = []
            
            for t in raw_trades[:count]:
                t_time = getattr(t, 'time', None) or (t.get('time') if isinstance(t, dict) else None)
                t_price = getattr(t, 'price', 0) or (t.get('price', 0) if isinstance(t, dict) else 0)
                t_size = getattr(t, 'size', getattr(t, 'volume', 0)) or (t.get('size', t.get('volume', 0)) if isinstance(t, dict) else 0)
                t_type = getattr(t, 'tick_type', 0) or (t.get('tick_type', 0) if isinstance(t, dict) else 0)
                
                formatted_trades.append({
                    "time": datetime.fromtimestamp(t_time/1000000).strftime('%H:%M:%S') if t_time else "",
                    "price": float(t_price),
                    "volume": int(t_size),
                    "side": "buy" if t_type == 1 else "sell",
                    "tick_type": t_type
                })
                
            return formatted_trades
            
        except Exception as e:
            logger.error(f"[FubonClient] get_trades error for {symbol}: {e}")
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
            
    # =========================================================================
    # 🎯 實盤交易模組 (Real Trading Methods)
    # =========================================================================

    async def get_inventory(self) -> list:
        """
        取得現在交割戶的真實庫存明細 (Inventories)
        返回格式: 包含每檔股票庫存餘額的清單
        """
        if not self.is_connected:
            await self.connect()
        if not self.is_connected or not self.active_account:
            return []

        try:
            # 庫存查詢為同步阻塞操作，必須在 ThreadPool 內執行
            logger.info("[FubonClient] 查詢真實證券庫存...")
            res = await asyncio.to_thread(self.sdk.accounting.inventories, self.active_account)
            
            # API 回傳可能為 list 或物件
            inventories = getattr(res, 'data', res) if hasattr(res, 'data') else res
            result = []
            
            if isinstance(inventories, list):
                for item in inventories:
                    # 嘗試抓取常見的屬性名
                    symbol = getattr(item, 'stock_no', getattr(item, 'symbol', ''))
                    qty    = getattr(item, 'qty', getattr(item, 'quantity', 0))
                    if symbol and qty > 0:
                        result.append({
                            "symbol": symbol,
                            "quantity": qty,
                            "cost_price": float(getattr(item, 'cost_price', getattr(item, 'average_price', 0))),
                            "market_value": getattr(item, 'market_value', 0)
                        })
            logger.info(f"[FubonClient] 取得 {len(result)} 筆庫存部位資料。")
            return result
        except Exception as e:
            logger.error(f"[FubonClient] 取得庫存失敗: {e}")
            return []

    async def place_order(self, symbol: str, action: str, quantity: int, price: float, is_market: bool = False) -> Dict[str, Any]:
        """
        真實委託下單
        Args:
            symbol: 股票代碼 (例如 "2337")
            action: 'buy' 或 'sell'
            quantity: 股數 (整股需填 1000 的倍數，例如 1 張 = 1000)
            price: 委託價
            is_market: 是否以市價買入
        """
        if not self.is_connected:
            await self.connect()
        if not self.is_connected or not self.active_account:
            return {"success": False, "message": "API 未連線或未找到交易帳戶"}

        try:
            from fubon_neo.constant import BSAction, TimeInForce, OrderType, PriceType
            from fubon_neo.sdk import Order

            clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
            bs_action = BSAction.Buy if action.lower() == 'buy' else BSAction.Sell
            p_type    = PriceType.Market if is_market else PriceType.Limit
            
            # 建立委託單物件
            order = Order(
                buy_sell=bs_action,
                symbol=clean_symbol,
                price=str(price) if not is_market else "",
                quantity=quantity,
                time_in_force=TimeInForce.ROD,
                price_type=p_type,
                order_type=OrderType.Stock
            )

            logger.warning(f"🚨 [實盤發送預備] 發送委託: {action.upper()} {clean_symbol} {quantity}股 @ {price if not is_market else '市價'}")

            # 實際打單
            res = await asyncio.to_thread(self.sdk.stock.place_order, self.active_account, order)
            
            # 解析打單結果
            is_success = getattr(res, 'is_success', False)
            message = getattr(res, 'message', str(res))
            order_no = ""
            
            if is_success and hasattr(res, 'data'):
                order_no = getattr(res.data, 'order_no', '')

            logger.info(f"📨 [實盤委託結果] 狀態: {is_success}, 單號: {order_no}, 訊息: {message}")
            
            return {
                "success": is_success,
                "order_no": order_no,
                "message": message,
                "raw_response": str(res)
            }
            
        except Exception as e:
            logger.error(f"❌ [實盤委託崩潰] 下單異常 ({symbol}): {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    async def cancel_order(self, order_no: str) -> Dict[str, Any]:
        """
        撤銷委託單
        """
        if not self.is_connected:
            await self.connect()
        try:
            # 取得委託單明細來撤銷 (或直接呼叫 cancel_order)
            # 因為各家 Broker SDK 撤銷方式稍有不同，一般為 cancel_order(account, order_no)
            logger.info(f"🗑️ 嘗試撤銷委託單: {order_no}")
            res = await asyncio.to_thread(self.sdk.stock.cancel_order, self.active_account, order_no)
            
            is_success = getattr(res, 'is_success', False)
            message = getattr(res, 'message', str(res))
            
            return {"success": is_success, "message": message}
        except Exception as e:
            logger.error(f"❌ 撤單失敗 ({order_no}): {e}")
            return {"success": False, "message": str(e)}

    async def get_books(self, symbol: str) -> Optional[Dict[str, Any]]:
        """獲取盤中五檔買賣揭示 (Limit Order Book)"""
        if not self.is_connected or not self.sdk:
            return None
        try:
            clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
            res = await asyncio.to_thread(self.sdk.marketdata.rest_client.stock.intraday.books, symbol=clean_symbol)
            
            if res:
                # 兼容物件屬性或字典
                bids_raw = getattr(res, 'bids', []) or res.get('bids', [])
                asks_raw = getattr(res, 'asks', []) or res.get('asks', [])
                
                bids = [{'price': float(b.price if hasattr(b, 'price') else b.get('price', 0)), 
                         'volume': int(b.volume if hasattr(b, 'volume') else b.get('volume', 0))} for b in bids_raw]
                asks = [{'price': float(a.price if hasattr(a, 'price') else a.get('price', 0)), 
                         'volume': int(a.volume if hasattr(a, 'volume') else a.get('volume', 0))} for a in asks_raw]
                         
                return {
                    'symbol': symbol,
                    'bids': bids,
                    'asks': asks,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.debug(f"[FubonClient] 獲取五檔失敗 {symbol}: {e}")
        return None

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

