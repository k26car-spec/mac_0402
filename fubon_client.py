from typing import Optional, Dict, Any
import logging
import os
from config import get_decrypted_credentials

logger = logging.getLogger(__name__)

class FubonClient:
    """富邦 SDK 客戶端封裝"""
    
    def __init__(self):
        self.sdk = None
        self.is_connected = False
        self.credentials = None
        
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
            
            # 取得解密後的憑證
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
            
            # 初始化即時連線
            logger.info("[FubonClient] Initializing realtime...")
            self.sdk.init_realtime()
            
            self.is_connected = True
            logger.info("[FubonClient] ✅ Connected to Fubon API")
            
            return True
            
        except Exception as e:
            logger.error(f"[FubonClient] Connection failed: {e}")
            self.is_connected = False
            return False
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """取得即時報價"""
        if not self.is_connected:
            success = await self.connect()
            if not success:
                return None
        
        try:
            # 移除 .TW / .TWO 後綴
            clean_symbol = symbol.replace('.TW', '').replace('.TWO', '')
            
            # 使用 SDK 取得報價
            # 注意：Python SDK 的調用方式可能與 Node.js 略有不同，這裡假設結構相似
            # 如果是 REST client
            if hasattr(self.sdk, 'marketdata') and hasattr(self.sdk.marketdata, 'rest_client'):
                snapshot = self.sdk.marketdata.rest_client.stock.snapshot.quotes(
                    symbol=clean_symbol
                )
            else:
                # 備用路徑，視 SDK 結構而定
                logger.warning("SDK structure mismatch, attempting direct access")
                return None
            
            if not snapshot or not snapshot.get('data'):
                return None
            
            data = snapshot['data'][0] if isinstance(snapshot['data'], list) else snapshot['data']
            
            # 轉換為統一格式
            return {
                "symbol": symbol,
                "name": data.get("name", ""),
                "openPrice": data.get("open", 0),
                "highPrice": data.get("high", 0),
                "lowPrice": data.get("low", 0),
                "closePrice": data.get("close", 0),
                "change": data.get("change", 0),
                "changePercent": data.get("changePercent", 0),
                "volume": data.get("volume", 0),
                "lastUpdated": data.get("lastUpdated", 0)
            }
            
        except Exception as e:
            logger.error(f"[FubonClient] getQuote error for {symbol}: {e}")
            # 如果出錯，可能是連線斷了，重試一次連線
            if "connection" in str(e).lower():
                self.is_connected = False
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
