#!/usr/bin/env python3
# fubon_data_source.py - 富邦 SDK 數據源整合

"""
富邦 Neo SDK 數據源
提供股票即時報價、歷史K線等功能
"""

import logging
import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 嘗試導入富邦客戶端
try:
    from fubon_client import fubon_client
    FUBON_AVAILABLE = True
    logger.info("✅ 富邦 SDK 已載入")
except ImportError as e:
    FUBON_AVAILABLE = False
    logger.warning(f"⚠️ 富邦 SDK 未可用: {e}")

class FubonDataSource:
    """富邦數據源"""
    
    def __init__(self):
        self.client = fubon_client if FUBON_AVAILABLE else None
        self._connected = False
    
    async def connect(self) -> bool:
        """連接到富邦 API"""
        if not FUBON_AVAILABLE:
            return False
        
        if self._connected:
            return True
        
        try:
            success = await self.client.connect()
            self._connected = success
            if success:
                logger.info("✅ 富邦 API 連接成功")
            else:
                logger.warning("❌ 富邦 API 連接失敗")
            return success
        except Exception as e:
            logger.error(f"富邦 API 連接錯誤: {e}")
            return False
    
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        獲取即時報價
        
        Args:
            symbol: 股票代碼 (如: 2330.TW 或 2330)
        
        Returns:
            {
                'code': '2330',
                'name': '台積電',
                'price': 582.0,
                'change': 2.0,
                'changePercent': 0.34,
                'volume': 28500,
                'open': 580.0,
                'high': 585.0,
                'low': 578.0
            }
        """
        if not FUBON_AVAILABLE:
            return None
        
        # 確保連接
        if not self._connected:
            await self.connect()
        
        if not self._connected:
            return None
        
        try:
            quote = await self.client.get_quote(symbol)
            
            if quote:
                # 轉換為統一格式
                clean_code = symbol.replace('.TW', '').replace('.TWO', '')
                return {
                    'code': clean_code,
                    'name': quote.get('name', clean_code),
                    'price': quote.get('closePrice', 0),
                    'change': quote.get('change', 0),
                    'changePercent': quote.get('changePercent', 0),
                    'volume': quote.get('volume', 0),
                    'open': quote.get('openPrice', 0),
                    'high': quote.get('highPrice', 0),
                    'low': quote.get('lowPrice', 0),
                    'lastUpdated': quote.get('lastUpdated', datetime.now().timestamp())
                }
            
        except Exception as e:
            logger.error(f"獲取報價失敗 {symbol}: {e}")
        
        return None
    
    async def get_historical_data(
        self, 
        symbol: str, 
        days: int = 30
    ) -> Optional[List[Dict]]:
        """
        獲取歷史K線數據
        
        Args:
            symbol: 股票代碼
            days: 天數（預設30天）
        
        Returns:
            [{date, open, high, low, close, volume}, ...]
        """
        if not FUBON_AVAILABLE or not self._connected:
            return None
        
        try:
            to_date = datetime.now().strftime('%Y-%m-%d')
            from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            candles = await self.client.get_candles(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                timeframe='D'
            )
            
            if candles:
                # 轉換為標準格式
                result = []
                for candle in candles:
                    result.append({
                        'date': candle.get('date'),
                        'open': candle.get('open', 0),
                        'high': candle.get('high', 0),
                        'low': candle.get('low', 0),
                        'close': candle.get('close', 0),
                        'volume': candle.get('volume', 0)
                    })
                return result
                
        except Exception as e:
            logger.error(f"獲取歷史數據失敗 {symbol}: {e}")
        
        return None
    
    def is_available(self) -> bool:
        """檢查富邦 SDK 是否可用"""
        return FUBON_AVAILABLE and self._connected


# 全局實例
fubon_data_source = FubonDataSource()


# 便捷函數
async def get_stock_quote(symbol: str) -> Optional[Dict]:
    """獲取股票報價"""
    return await fubon_data_source.get_quote(symbol)


async def get_stock_history(symbol: str, days: int = 30) -> Optional[List[Dict]]:
    """獲取歷史數據"""
    return await fubon_data_source.get_historical_data(symbol, days)


# 測試函數
async def test_fubon_data_source():
    """測試富邦數據源"""
    print("🧪 測試富邦數據源\n")
    
    if not FUBON_AVAILABLE:
        print("❌ 富邦 SDK 未安裝")
        return
    
    # 連接
    print("📡 連接中...")
    success = await fubon_data_source.connect()
    
    if not success:
        print("❌ 連接失敗")
        print("\n💡 提示: 請檢查 fubon.env 中的憑證設定")
        return
    
    print("✅ 連接成功\n")
    
    # 測試股票
    test_stocks = ['2330', '2317', '0050']
    
    for stock in test_stocks:
        print(f"查詢: {stock}")
        quote = await get_stock_quote(stock)
        
        if quote:
            print(f"  ✅ {quote['code']:6s} {quote['name']:8s}")
            print(f"     價格: {quote['price']:7.2f}  漲跌: {quote['change']:+6.2f}  成交量: {quote['volume']:,}")
        else:
            print(f"  ❌ 查詢失敗")
        print()
    
    print("✅ 測試完成")


if __name__ == '__main__':
    # 運行測試
    asyncio.run(test_fubon_data_source())
