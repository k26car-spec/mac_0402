"""
即時 VWAP 追蹤系統
計算當日即時成交量加權平均價
"""

import logging
from datetime import datetime, date
from typing import Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RealTimeVWAP:
    """單檔股票的即時 VWAP 計算器"""
    
    # 累計成交金額 (Σ price × volume)
    cumulative_pv: float = 0.0
    
    # 累計成交量 (Σ volume)
    cumulative_volume: float = 0.0
    
    # 當日日期（用於判斷是否需要重置）
    trading_date: date = None
    
    # 上次更新時間
    last_update: datetime = None
    
    # tick 數量
    tick_count: int = 0
    
    def update(self, price: float, volume: int) -> float:
        """
        更新 VWAP
        
        Args:
            price: 成交價
            volume: 成交量
            
        Returns:
            當前 VWAP
        """
        if price <= 0 or volume <= 0:
            return self.get_vwap()
        
        # 累加
        self.cumulative_pv += price * volume
        self.cumulative_volume += volume
        self.tick_count += 1
        self.last_update = datetime.now()
        
        return self.get_vwap()
    
    def get_vwap(self) -> float:
        """獲取當前 VWAP"""
        if self.cumulative_volume <= 0:
            return 0.0
        
        return self.cumulative_pv / self.cumulative_volume
    
    def get_deviation(self, current_price: float) -> float:
        """
        計算當前價格對 VWAP 的乖離度
        
        Returns:
            乖離度百分比（正值=高於VWAP，負值=低於VWAP）
        """
        vwap = self.get_vwap()
        
        if vwap <= 0:
            return 0.0
        
        return ((current_price - vwap) / vwap) * 100
    
    def reset(self):
        """重置（新的一天）"""
        self.cumulative_pv = 0.0
        self.cumulative_volume = 0.0
        self.trading_date = date.today()
        self.last_update = None
        self.tick_count = 0


class VWAPTracker:
    """VWAP 追蹤管理器"""
    
    def __init__(self):
        # 每檔股票一個計算器
        self.vwap_calculators: Dict[str, RealTimeVWAP] = {}
        
        # 交易時段
        self.trading_start = 9  # 09:00
        self.trading_end = 13   # 13:30
        
        logger.info("📊 即時 VWAP 追蹤器已初始化")
    
    def _is_new_day(self, stock_code: str, timestamp: datetime = None) -> bool:
        """檢查是否新的一天"""
        
        if stock_code not in self.vwap_calculators:
            return True
        
        calculator = self.vwap_calculators[stock_code]
        
        if calculator.trading_date is None:
            return True
        
        today = date.today()
        return calculator.trading_date != today
    
    def _ensure_calculator(self, stock_code: str):
        """確保計算器存在且是當日的"""
        
        if self._is_new_day(stock_code):
            self.vwap_calculators[stock_code] = RealTimeVWAP(trading_date=date.today())
            logger.debug(f"為 {stock_code} 創建新的 VWAP 計算器")
    
    def update(self, stock_code: str, price: float, volume: int, timestamp: datetime = None) -> float:
        """
        更新股票的 VWAP
        
        Args:
            stock_code: 股票代號
            price: 成交價
            volume: 成交量
            timestamp: 成交時間
            
        Returns:
            當前 VWAP
        """
        # 確保計算器存在
        self._ensure_calculator(stock_code)
        
        # 更新 VWAP
        vwap = self.vwap_calculators[stock_code].update(price, volume)
        
        return vwap
    
    def get_vwap(self, stock_code: str) -> float:
        """獲取股票當前 VWAP"""
        
        if stock_code not in self.vwap_calculators:
            return 0.0
        
        return self.vwap_calculators[stock_code].get_vwap()
    
    def get_deviation(self, stock_code: str, current_price: float) -> float:
        """
        獲取當前價格對 VWAP 的乖離度
        
        Args:
            stock_code: 股票代號
            current_price: 當前價格
            
        Returns:
            乖離度百分比
        """
        if stock_code not in self.vwap_calculators:
            return 0.0
        
        return self.vwap_calculators[stock_code].get_deviation(current_price)
    
    def get_stats(self, stock_code: str) -> Dict:
        """獲取股票 VWAP 統計"""
        
        if stock_code not in self.vwap_calculators:
            return {
                'vwap': 0.0,
                'cumulative_volume': 0,
                'tick_count': 0,
                'last_update': None
            }
        
        calc = self.vwap_calculators[stock_code]
        
        return {
            'vwap': calc.get_vwap(),
            'cumulative_volume': calc.cumulative_volume,
            'tick_count': calc.tick_count,
            'last_update': calc.last_update.isoformat() if calc.last_update else None,
            'trading_date': calc.trading_date.isoformat() if calc.trading_date else None
        }
    
    def reset_stock(self, stock_code: str):
        """重置單檔股票"""
        
        if stock_code in self.vwap_calculators:
            self.vwap_calculators[stock_code].reset()
            logger.info(f"已重置 {stock_code} 的 VWAP")
    
    def reset_all(self):
        """重置所有股票（盤後或新的一天）"""
        
        for code in self.vwap_calculators:
            self.vwap_calculators[code].reset()
        
        logger.info(f"已重置所有 {len(self.vwap_calculators)} 檔股票的 VWAP")
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """獲取所有股票的 VWAP 統計"""
        
        return {
            code: self.get_stats(code)
            for code in self.vwap_calculators
        }
    
    def batch_update(self, trades: list):
        """
        批次更新（從 tick 資料）
        
        Args:
            trades: [{'stock_code': '2330', 'price': 580.0, 'volume': 100}, ...]
        """
        for trade in trades:
            self.update(
                stock_code=trade['stock_code'],
                price=trade['price'],
                volume=trade['volume'],
                timestamp=trade.get('timestamp')
            )


# 全局實例
vwap_tracker = VWAPTracker()


def initialize_vwap_from_quote(stock_code: str, quote_data: dict) -> float:
    """
    從即時報價初始化當日 VWAP（當沒有 tick 資料時使用）
    
    Args:
        stock_code: 股票代號
        quote_data: 包含 open, high, low, close, volume 的報價資料
        
    Returns:
        估算的當日 VWAP
    """
    open_price = quote_data.get('open', 0)
    high_price = quote_data.get('high', 0)
    low_price = quote_data.get('low', 0)
    close_price = quote_data.get('close', 0) or quote_data.get('price', 0)
    volume = quote_data.get('volume', 0)
    
    if not all([open_price, high_price, low_price, close_price, volume]):
        return 0.0
    
    # 估算當日 VWAP = (開盤 + 最高 + 最低 + 收盤×2) / 5
    # 這是一個合理的估算，因為收盤（現價）通常成交量較大
    estimated_vwap = (open_price + high_price + low_price + close_price * 2) / 5
    
    # 用估算值初始化追蹤器
    vwap_tracker._ensure_calculator(stock_code)
    
    # 用估算的 VWAP 模擬一筆大成交量
    # 這樣後續的即時 tick 會逐漸修正這個值
    if vwap_tracker.vwap_calculators[stock_code].cumulative_volume == 0:
        vwap_tracker.vwap_calculators[stock_code].cumulative_pv = estimated_vwap * volume
        vwap_tracker.vwap_calculators[stock_code].cumulative_volume = volume
        vwap_tracker.vwap_calculators[stock_code].tick_count = 1
        vwap_tracker.vwap_calculators[stock_code].last_update = datetime.now()
        
        logger.info(f"📊 {stock_code} 從報價初始化 VWAP: {estimated_vwap:.2f}")
    
    return estimated_vwap


async def get_or_estimate_vwap(stock_code: str) -> tuple:
    """
    獲取或估算股票的當日 VWAP
    
    Returns:
        (vwap, deviation, source) - VWAP值, 乖離度, 來源('realtime'/'estimated')
    """
    # 先嘗試從追蹤器獲取即時 VWAP
    realtime_vwap = vwap_tracker.get_vwap(stock_code)
    
    if realtime_vwap > 0:
        # 有即時數據，獲取當前價格計算乖離
        try:
            from app.services.fubon_service import get_realtime_quote
            quote = await get_realtime_quote(stock_code)
            if quote and quote.get('price'):
                deviation = vwap_tracker.get_deviation(stock_code, quote['price'])
                return (realtime_vwap, deviation, 'realtime')
        except:
            pass
        return (realtime_vwap, 0.0, 'realtime')
    
    # 沒有即時數據，從報價估算
    try:
        from app.services.fubon_service import get_realtime_quote
        quote = await get_realtime_quote(stock_code)
        
        if quote:
            estimated_vwap = initialize_vwap_from_quote(stock_code, quote)
            if estimated_vwap > 0:
                current_price = quote.get('price', 0)
                deviation = ((current_price - estimated_vwap) / estimated_vwap * 100) if estimated_vwap and current_price else 0
                return (estimated_vwap, deviation, 'estimated')
    except Exception as e:
        logger.warning(f"獲取報價失敗: {e}")
    
    return (0.0, 0.0, 'none')


# ============ 與 Fubon API 整合範例 ============

async def process_fubon_tick(tick_data: Dict):
    """
    處理富邦 API 的 tick 資料
    
    tick_data 格式：
    {
        'symbol': '2330',
        'price': 580.0,
        'volume': 1000,
        'time': '09:01:23'
    }
    """
    stock_code = tick_data.get('symbol', '')
    price = tick_data.get('price', 0)
    volume = tick_data.get('volume', 0)
    
    if stock_code and price > 0 and volume > 0:
        vwap = vwap_tracker.update(stock_code, price, volume)
        deviation = vwap_tracker.get_deviation(stock_code, price)
        
        logger.debug(f"{stock_code}: Price={price}, VWAP={vwap:.2f}, 乖離={deviation:+.2f}%")
        
        return {
            'stock_code': stock_code,
            'price': price,
            'vwap': vwap,
            'deviation': deviation
        }
    
    return None
