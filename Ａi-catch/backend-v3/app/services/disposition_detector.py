"""
處置股自動偵測器（使用富邦 API）

無法直接從富邦 API 獲取處置股資訊，但可以透過以下方式偵測：

1. 成交時間間隔分析：處置股每 5 分鐘/20 分鐘撮合一次
2. 成交量異常萎縮：處置股流動性大幅下降
3. 證交所公告抓取：定期抓取官方處置股名單

使用：
    from app.services.disposition_detector import disposition_detector
    result = await disposition_detector.detect("2337")
"""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


class DispositionDetector:
    """處置股自動偵測器"""
    
    def __init__(self):
        # 撮合間隔標準
        self.NORMAL_MATCH_INTERVAL = 0  # 正常股：連續撮合
        self.DISPOSITION_5MIN = 5       # 處置股：5分鐘撮合
        self.DISPOSITION_20MIN = 20     # 重度處置：20分鐘撮合
        
        # 偵測閾值
        self.VOL_SHRINK_THRESHOLD = 0.3  # 量縮到 30%
        self.MATCH_GAP_THRESHOLD = 240   # 成交間隔 > 240 秒視為處置
        
        # 快取
        self.cache = {}
        self.cache_ttl = 600  # 10 分鐘快取
    
    async def detect(self, symbol: str) -> Dict:
        """
        偵測股票是否為處置股
        
        Returns:
            {
                'is_disposition': bool,
                'match_interval': int,  # 撮合間隔（分鐘）
                'detection_method': str,
                'confidence': int,
                'evidence': dict
            }
        """
        # 檢查快取
        cache_key = symbol
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached['time']).seconds < self.cache_ttl:
                return cached['data']
        
        result = {
            'symbol': symbol,
            'is_disposition': False,
            'match_interval': 0,
            'detection_method': None,
            'confidence': 0,
            'evidence': {}
        }
        
        # 方法 1：分析成交時間間隔（使用富邦 API）
        try:
            trade_analysis = await self._analyze_trade_intervals(symbol)
            if trade_analysis['is_disposition']:
                result.update(trade_analysis)
        except Exception as e:
            logger.debug(f"成交時間分析失敗: {e}")
        
        # 方法 2：檢查已知處置股清單
        try:
            from app.services.disposition_stock_manager import disposition_manager
            if disposition_manager.is_disposition_stock(symbol):
                info = disposition_manager.get_disposition_info(symbol)
                result['is_disposition'] = True
                result['match_interval'] = info.get('match_interval', 5)
                result['detection_method'] = 'known_list'
                result['confidence'] = 100
                result['evidence']['source'] = 'disposition_stock_manager'
        except Exception as e:
            logger.debug(f"處置股清單檢查失敗: {e}")
        
        # 快取結果
        self.cache[cache_key] = {
            'time': datetime.now(),
            'data': result
        }
        
        return result
    
    async def _analyze_trade_intervals(self, symbol: str) -> Dict:
        """
        分析成交時間間隔來判斷是否為處置股
        
        處置股特徵：
        - 5 分鐘撮合：每 5 分鐘才有成交（09:05, 09:10, ...）
        - 20 分鐘撮合：每 20 分鐘才有成交（09:20, 09:40, ...）
        """
        result = {
            'is_disposition': False,
            'match_interval': 0,
            'detection_method': 'trade_interval_analysis',
            'confidence': 0,
            'evidence': {}
        }
        
        try:
            # 呼叫富邦 API 獲取成交明細
            import sys
            sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')
            from fubon_client import fubon_client
            
            trades = await fubon_client.get_trades(symbol, count=50)
            
            if not trades or len(trades) < 5:
                return result
            
            # 分析成交時間間隔
            intervals = []
            for i in range(1, len(trades)):
                time1 = trades[i-1].get('time') or trades[i-1].get('timestamp')
                time2 = trades[i].get('time') or trades[i].get('timestamp')
                
                if time1 and time2:
                    # 計算間隔（秒）
                    if isinstance(time1, str):
                        t1 = datetime.fromisoformat(time1.replace('Z', '+00:00'))
                        t2 = datetime.fromisoformat(time2.replace('Z', '+00:00'))
                    else:
                        t1 = time1
                        t2 = time2
                    
                    interval = abs((t2 - t1).total_seconds())
                    intervals.append(interval)
            
            if not intervals:
                return result
            
            # 分析間隔模式
            avg_interval = sum(intervals) / len(intervals)
            max_interval = max(intervals)
            
            result['evidence'] = {
                'avg_interval_seconds': round(avg_interval, 1),
                'max_interval_seconds': round(max_interval, 1),
                'trade_count': len(trades)
            }
            
            # 判斷處置股
            if avg_interval >= 280:  # 平均間隔 ~5 分鐘
                result['is_disposition'] = True
                result['match_interval'] = 5
                result['confidence'] = 85
            elif avg_interval >= 1100:  # 平均間隔 ~20 分鐘
                result['is_disposition'] = True
                result['match_interval'] = 20
                result['confidence'] = 90
            elif max_interval >= self.MATCH_GAP_THRESHOLD:
                result['is_disposition'] = True
                result['match_interval'] = 5
                result['confidence'] = 70
            
            return result
            
        except Exception as e:
            logger.warning(f"成交時間分析失敗 {symbol}: {e}")
            return result
    
    async def detect_all(self, symbols: List[str]) -> Dict:
        """
        批量偵測處置股
        """
        results = {
            'total': len(symbols),
            'disposition_count': 0,
            'disposition_stocks': [],
            'normal_stocks': []
        }
        
        for symbol in symbols:
            try:
                detection = await self.detect(symbol)
                
                if detection['is_disposition']:
                    results['disposition_count'] += 1
                    results['disposition_stocks'].append({
                        'symbol': symbol,
                        'match_interval': detection['match_interval'],
                        'confidence': detection['confidence'],
                        'method': detection['detection_method']
                    })
                else:
                    results['normal_stocks'].append(symbol)
                    
            except Exception as e:
                logger.warning(f"偵測 {symbol} 失敗: {e}")
                results['normal_stocks'].append(symbol)
        
        return results
    
    def get_next_match_time(self, symbol: str, interval: int = 5) -> str:
        """
        計算下一次撮合時間
        
        Args:
            symbol: 股票代碼
            interval: 撮合間隔（分鐘）
        """
        now = datetime.now()
        
        # 交易時段檢查
        if now.time() < time(9, 0):
            return "09:00（開盤）"
        elif now.time() > time(13, 30):
            return "明日 09:00"
        
        # 計算下一個撮合點
        current_minute = now.minute
        minutes_to_next = interval - (current_minute % interval)
        
        if minutes_to_next == interval:
            minutes_to_next = 0
        
        next_match = now + timedelta(minutes=minutes_to_next)
        next_match = next_match.replace(second=0, microsecond=0)
        
        return next_match.strftime("%H:%M")


# 單例
disposition_detector = DispositionDetector()


# 測試
if __name__ == "__main__":
    async def test():
        print("="*60)
        print("  處置股自動偵測器")
        print("="*60)
        
        # 測試單股
        result = await disposition_detector.detect("2337")
        print(f"\n2337 偵測結果:")
        print(f"   處置股: {result['is_disposition']}")
        print(f"   撮合間隔: {result['match_interval']} 分鐘")
        print(f"   偵測方法: {result['detection_method']}")
        print(f"   信心度: {result['confidence']}%")
        
        # 下一次撮合時間
        if result['is_disposition']:
            next_time = disposition_detector.get_next_match_time("2337", result['match_interval'])
            print(f"   下次撮合: {next_time}")
    
    asyncio.run(test())
