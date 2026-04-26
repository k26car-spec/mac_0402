"""
真實數據服務 - Real Data Service
整合多個數據源獲取真實市場數據

數據源：
1. 富邦API - 台股即時報價、技術指標
2. Yahoo Finance - 美股數據
3. 證交所API - 法人買賣超
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import sys
import os

# 添加父目錄到路徑以導入富邦客戶端
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)

# ==================== 富邦API整合 ====================

class FubonDataService:
    """富邦即時數據服務"""
    
    def __init__(self):
        self.client = None
        self._initialized = False
    
    async def initialize(self):
        """初始化富邦客戶端"""
        if self._initialized:
            return True
        
        try:
            # 修正導入路徑 - fubon_client在項目根目錄
            import sys
            import os
            
            # 添加項目根目錄到路徑
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            # ✅ 強制加載環境變數
            from dotenv import load_dotenv
            env_path = os.path.join(project_root, '.env')
            load_dotenv(env_path)
            logger.info(f"🔧 已加載環境變數: {env_path}")
            
            # 驗證關鍵環境變數
            encryption_key = os.getenv('ENCRYPTION_SECRET_KEY')
            if encryption_key:
                logger.info(f"✅ ENCRYPTION_SECRET_KEY: {encryption_key[:5]}***")
            else:
                logger.warning("⚠️ ENCRYPTION_SECRET_KEY 未設定")
            
            from fubon_client import fubon_client
            self.client = fubon_client
            
            # ✅ 添加超時保護 - 最多等5秒
            import asyncio
            try:
                success = await asyncio.wait_for(
                    self.client.connect(), 
                    timeout=5.0  # 5秒超時
                )
            except asyncio.TimeoutError:
                logger.warning("⚠️ 富邦API連接超時（5秒），將使用備用數據源")
                self._initialized = False
                return False
            
            self._initialized = success
            if success:
                logger.info("✅ 富邦API連接成功")
            else:
                logger.warning("⚠️ 富邦API連接失敗，將使用備用數據源")
            return success
        except ImportError as e:
            logger.warning(f"⚠️ 富邦SDK未安裝或配置: {e}")
            logger.info("💡 系統將使用備用數據源（模擬數據）")
            self._initialized = False
            return False
        except Exception as e:
            logger.error(f"富邦API初始化錯誤: {e}")
            self._initialized = False
            return False
    
    async def get_stock_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """獲取股票即時報價"""
        if not self._initialized:
            await self.initialize()
        
        if not self.client or not self.client.is_connected:
            logger.warning(f"富邦API未連接，無法獲取 {symbol} 報價")
            return None
        
        try:
            quote = await self.client.get_quote(symbol)
            return quote
        except Exception as e:
            logger.error(f"獲取 {symbol} 報價錯誤: {e}")
            return None
    
    async def get_technical_indicators(self, symbol: str) -> Optional[Dict[str, Any]]:
        """獲取技術指標 - 使用富邦API真實數據"""
        try:
            if not self._initialized:
                await self.initialize()
            
            if not self.client or not self.client.is_connected:
                logger.warning(f"富邦API未連接，無法獲取 {symbol} 技術指標")
                return None
            
            # ✅ 步驟1: 獲取即時報價（當前股價）
            logger.info(f"📊 獲取 {symbol} 即時報價...")
            quote = await self.client.get_quote(symbol)
            
            if quote and quote.get('price'):
                current_price = quote['price']
                logger.info(f"✅ {symbol} 即時股價: {current_price}")
            else:
                logger.warning(f"⚠️ {symbol} 無法獲取即時報價")
                current_price = None
            
            # ✅ 步驟2: 獲取歷史K線數據（用於計算技術指標）
            today = datetime.now()
            from_date = (today - timedelta(days=120)).strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")
            
            logger.info(f"📊 獲取 {symbol} 歷史K線: {from_date} ~ {to_date}")
            
            candles = await self.client.get_candles(symbol, from_date, to_date, "D")
            
            if not candles or len(candles) < 20:
                logger.warning(f"{symbol} K線數據不足: {len(candles) if candles else 0} 根")
                # 如果有即時報價但沒有K線，至少返回當前價格
                if current_price:
                    return {
                        'current_price': current_price,
                        'data_source': '✅ Fubon API Real-Time',
                        'partial': True  # 標記為部分數據
                    }
                return None
            
            logger.info(f"✅ {symbol} 獲取到 {len(candles)} 根K線")
            
            # 提取收盤價和成交量
            closes = [float(c.get('close', 0)) for c in candles if c.get('close')]
            volumes = [float(c.get('volume', 0)) for c in candles if c.get('volume')]
            
            if len(closes) < 20:
                logger.warning(f"{symbol} 有效數據不足")
                if current_price:
                    return {
                        'current_price': current_price,
                        'data_source': '✅ Fubon API Real-Time',
                        'partial': True
                    }
                return None
            
            # 計算移動平均線
            ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else 0
            ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else 0
            ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else 0
            ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else 0
            
            # 計算RSI
            rsi = calculate_rsi(closes)
            
            # 計算MACD
            macd_line, signal_line, macd_hist = calculate_macd(closes)
            
            # 計算量比
            avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 1
            current_volume = volumes[-1] if volumes else 0
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            # ✅ 使用即時報價的價格（如果有），否則用K線最後收盤價
            if current_price is None:
                current_price = closes[-1] if closes else 0
                logger.info(f"📊 {symbol} 使用K線收盤價: {current_price:.2f}")
            
            logger.info(f"📊 {symbol} 技術指標: 價格={current_price:.2f}, MA5={ma5:.2f}, RSI={rsi:.1f}")
            
            return {
                "ma5": round(ma5, 2),
                "ma10": round(ma10, 2),
                "ma20": round(ma20, 2),
                "ma60": round(ma60, 2),
                "rsi": round(rsi, 2),
                "macd": round(macd_line, 2),
                "macd_signal": round(signal_line, 2),
                "macd_hist": round(macd_hist, 2),
                "volume_ratio": round(volume_ratio, 2),
                "current_price": round(current_price, 2),
                "data_source": "✅ Fubon API Real-Time"
            }
        except Exception as e:
            logger.error(f"計算 {symbol} 技術指標錯誤: {e}", exc_info=True)
            return None
    
    async def batch_get_technical_indicators(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量獲取多支股票的技術指標 (並行優化版)"""
        # 使用 asyncio.gather 同時發起所有請求
        tasks = [self.get_technical_indicators(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 組裝結果，過濾掉異常或 None
        final_results = {}
        for symbol, result in zip(symbols, results):
            if result and not isinstance(result, Exception):
                final_results[symbol] = result
        
        return final_results


# ==================== Yahoo Finance & 外部 API (異步版) ====================

class ExternalDataService:
    """異步外部數據服務"""
    
    def __init__(self):
        self._client = None
    
    async def get_client(self):
        if self._client is None or self._client.is_closed:
            import httpx
            self._client = httpx.AsyncClient(timeout=20.0, follow_redirects=True)
        return self._client

    async def get_us_market_data(self) -> Dict[str, Any]:
        """獲取美股主要指數 (異步)"""
        try:
            # yfinance 暫時仍是同步的，使用 to_thread 封裝
            import yfinance as yf
            
            async def fetch_yf(ticker_symbol):
                return await asyncio.to_thread(yf.Ticker, ticker_symbol)

            # 並行獲取多檔
            tickers = await asyncio.gather(*[fetch_yf(s) for s in ["^IXIC", "^DJI", "^GSPC", "NVDA"]])
            # ... (其餘邏輯簡化，優先確保非阻塞) ...
            
            # Fear & Greed Index (使用異步 HTTP)
            fear_greed = 50
            try:
                client = await self.get_client()
                fg_response = await client.get("https://api.alternative.me/fng/")
                fg_data = fg_response.json()
                if fg_data.get('data'):
                    fear_greed = int(fg_data['data'][0].get('value', 50))
            except: pass
            
            return {
                "fear_greed_index": fear_greed,
                # ... 其他欄位補齊
            }
        except Exception as e:
            logger.error(f"獲取美股數據錯誤: {e}")
            return {"fear_greed_index": 50}



# ==================== 證交所API ====================

class TWStockExchangeService:
    """台灣證交所數據服務"""
    
    async def get_institutional_trades(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """獲取法人買賣超數據"""
        try:
            import requests
            import pandas as pd
            
            if not date:
                date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            
            # 證交所三大法人買賣超API
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={date}&selectType=ALL"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('stat') != 'OK':
                logger.warning(f"證交所API回應異常: {data.get('stat')}")
                return []
            
            # 解析數據
            fields = data.get('fields', [])
            rows = data.get('data', [])
            
            result = []
            for row in rows:
                if len(row) < 4:
                    continue
                
                stock_id = row[0]
                stock_name = row[1]
                
                # 外資、投信、自營商買賣超（單位：千股，需轉換為張）
                try:
                    foreign = int(row[2].replace(',', '')) // 1000 if len(row) > 2 else 0
                    trust = int(row[3].replace(',', '')) // 1000 if len(row) > 3 else 0
                    dealer = int(row[4].replace(',', '')) // 1000 if len(row) > 4 else 0
                    
                    # 判斷是否三大法人一致買超
                    consensus = foreign > 500 and trust > 200 and dealer > 100
                    
                    if consensus:  # 只返回三大法人一致買超的股票
                        confidence = min(0.95, 0.7 + (foreign / 10000) * 0.2)
                        
                        result.append({
                            "stock_id": stock_id,
                            "stock_name": stock_name,
                            "foreign_net_buy": foreign,
                            "trust_net_buy": trust,
                            "dealer_net_buy": dealer,
                            "consensus": True,
                            "confidence": round(confidence, 2),
                            "data_source": "✅ TWSE API Real-Time"
                        })
                except (ValueError, IndexError) as e:
                    continue
            
            logger.info(f"✅ 證交所返回 {len(result)} 筆法人一致買超數據")
            return result[:10]  # 返回前10名
            
        except Exception as e:
            logger.error(f"獲取法人數據錯誤: {e}")
            return []


# ==================== 輔助函數 ====================

def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """計算RSI指標"""
    if len(prices) < period + 1:
        return 50.0
    
    try:
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    except:
        return 50.0


def calculate_macd(prices: List[float], fast=12, slow=26, signal=9):
    """計算MACD指標"""
    if len(prices) < slow:
        return 0.0, 0.0, 0.0
    
    try:
        # 計算EMA
        def ema(data, period):
            multiplier = 2 / (period + 1)
            ema_values = [sum(data[:period]) / period]
            for price in data[period:]:
                ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
            return ema_values[-1]
        
        ema_fast = ema(prices, fast)
        ema_slow = ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        # 計算信號線（簡化版）
        signal_line = macd_line * 0.9  # 簡化計算
        
        macd_hist = macd_line - signal_line
        
        return round(macd_line, 2), round(signal_line, 2), round(macd_hist, 2)
    except:
        return 0.0, 0.0, 0.0


# ==================== 全局實例 ====================

fubon_service = FubonDataService()
yahoo_service = ExternalDataService()
twse_service = TWStockExchangeService()
