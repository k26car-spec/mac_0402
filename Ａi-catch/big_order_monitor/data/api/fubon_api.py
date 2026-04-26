"""
富邦API介面 - 整合現有的 fubon_client
"""
from typing import Dict, Optional, List
import asyncio
from datetime import datetime
import logging
import sys

logger = logging.getLogger(__name__)

# 添加專案根目錄到路徑
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')


class EnhancedFubonAPI:
    """
    富邦API介面 - 整合現有的 fubon_client
    
    提供即時 tick 數據和報價功能
    """
    
    def __init__(self, account: str = None, password: str = None, cert_path: str = None):
        self.account = account
        self.password = password
        self.cert_path = cert_path
        self.connected = False
        self.subscribed_stocks = set()
        
        # 富邦客戶端
        self.fubon_client = None
        
        # 模擬資料用（備用）
        self.base_prices: Dict[str, float] = {}
        self.use_simulation = False
    
    async def connect(self) -> bool:
        """連接API"""
        try:
            logger.info("🔗 嘗試連接富邦API...")
            
            # 嘗試導入並連接真實的 fubon_client
            try:
                from fubon_client import fubon_client
                self.fubon_client = fubon_client
                
                # 嘗試連接
                connected = await self.fubon_client.connect()
                if connected:
                    self.connected = True
                    self.use_simulation = False
                    logger.info("✅ 富邦API連接成功！")
                    return True
                else:
                    logger.warning("⚠️ 富邦API連接失敗，切換到模擬模式")
                    self.use_simulation = True
                    self.connected = True
                    return True
                    
            except ImportError as e:
                logger.warning(f"⚠️ 無法導入 fubon_client: {e}")
                self.use_simulation = True
                self.connected = True
                logger.info("✅ 已切換到模擬模式")
                return True
            except Exception as e:
                logger.warning(f"⚠️ 連接富邦API失敗: {e}")
                self.use_simulation = True
                self.connected = True
                return True
                
        except Exception as e:
            logger.error(f"連接失敗: {e}")
            return False
    
    async def subscribe_realtime(self, stock_code: str) -> bool:
        """訂閱即時資料"""
        if not self.connected:
            logger.warning("尚未連接API")
            return False
        
        self.subscribed_stocks.add(stock_code)
        
        # 初始化基準價格
        if stock_code not in self.base_prices:
            self.base_prices[stock_code] = await self._get_initial_price(stock_code)
        
        logger.debug(f"已訂閱 {stock_code} 即時資料")
        return True
    
    async def get_latest_tick(self, stock_code: str) -> Optional[Dict]:
        """
        取得最新tick資料
        
        Returns:
            {
                'timestamp': datetime,
                'price': float,
                'volume': int,  # 張數
                'bs_flag': 'B' or 'S',
                'ask_price': float,
                'bid_price': float,
                'ask_volume': int,
                'bid_volume': int
            }
        """
        if stock_code not in self.subscribed_stocks:
            return None
        
        # 如果有真實 API，嘗試獲取真實數據
        if not self.use_simulation and self.fubon_client:
            try:
                quote = await self.fubon_client.get_quote(stock_code)
                if quote:
                    return {
                        'timestamp': datetime.now(),
                        'price': quote.get('price', 0),
                        'volume': quote.get('volume', 0) // 1000,  # 轉換為張
                        'bs_flag': 'B' if quote.get('change', 0) >= 0 else 'S',
                        'ask_price': quote.get('ask', quote.get('price', 0) + 0.5),
                        'bid_price': quote.get('bid', quote.get('price', 0) - 0.5),
                        'ask_volume': quote.get('ask_volume', 50),
                        'bid_volume': quote.get('bid_volume', 50)
                    }
            except Exception as e:
                logger.debug(f"獲取真實數據失敗，使用模擬: {e}")
        
        # 模擬資料
        return await self._generate_simulated_tick(stock_code)
    
    async def _generate_simulated_tick(self, stock_code: str) -> Dict:
        """產生模擬 tick 資料"""
        import random
        
        base_price = self.base_prices.get(stock_code, 100.0)
        
        # 隨機波動
        price_change = random.uniform(-0.01, 0.01)
        current_price = base_price * (1 + price_change)
        
        # 更新基準價（模擬連續性）
        self.base_prices[stock_code] = current_price
        
        # 產生模擬tick
        return {
            'timestamp': datetime.now(),
            'price': round(current_price, 2),
            'volume': random.randint(5, 200),  # 5-200張
            'bs_flag': 'B' if random.random() > 0.5 else 'S',
            'ask_price': round(current_price + 0.5, 2),
            'bid_price': round(current_price - 0.5, 2),
            'ask_volume': random.randint(20, 100),
            'bid_volume': random.randint(20, 100)
        }
    
    async def _get_initial_price(self, stock_code: str) -> float:
        """取得初始價格"""
        # 嘗試從真實 API 獲取
        if not self.use_simulation and self.fubon_client:
            try:
                quote = await self.fubon_client.get_quote(stock_code)
                if quote and quote.get('price'):
                    return quote['price']
            except:
                pass
        
        # 預設價格對照表
        price_map = {
            '2330': 580.0,   # 台積電
            '2454': 1100.0,  # 聯發科
            '2317': 110.0,   # 鴻海
            '2881': 75.0,    # 富邦金
            '2882': 58.0,    # 國泰金
            '2603': 200.0,   # 長榮
            '2308': 380.0,   # 台達電
            '2382': 280.0,   # 廣達
            '3443': 1200.0,  # 創意
            '5498': 35.0,    # 凱崴
        }
        return price_map.get(stock_code, 100.0)
    
    async def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """取得股票基本資訊"""
        try:
            # 從台股清單 API 獲取
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"http://localhost:8000/api/tw-stocks/search?q={stock_code}&limit=1"
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get('stocks') and len(data['stocks']) > 0:
                        stock = data['stocks'][0]
                        if stock['symbol'] == stock_code:
                            return stock
        except Exception as e:
            logger.debug(f"獲取股票資訊失敗: {e}")
        
        return None
    
    async def unsubscribe_all(self):
        """取消所有訂閱"""
        self.subscribed_stocks.clear()
        logger.info("已取消所有訂閱")
    
    async def disconnect(self):
        """斷開連接"""
        await self.unsubscribe_all()
        self.connected = False
        logger.info("已斷開連接")
