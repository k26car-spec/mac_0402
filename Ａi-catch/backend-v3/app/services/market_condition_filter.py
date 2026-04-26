"""
市場狀況過濾器 v2.0

功能：
1. 大盤過濾：大盤跌 > 1% 時禁止做多
2. 進階熔斷：外資賣超 > 500億 或開盤30分鐘跌 > 1.5% 時完全停止開倉
3. 動態信心加成：大盤漲時增加信心度
4. 最大持倉限制：同時持倉 ≤ 12 支，每日新建倉 ≤ 5 支
"""

import yfinance as yf
import logging
from datetime import datetime, time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MarketConditionFilter:
    """市場狀況過濾器 v2.0"""
    
    def __init__(self):
        self.twii_symbol = "^TWII"  # 加權指數
        self.cache = {}
        self.cache_time = None
        self.cache_duration = 300  # 5 分鐘快取
        
        # 過濾參數
        self.bear_threshold = -1.0   # 跌 > 1% 視為空頭
        self.bull_threshold = 1.0    # 漲 > 1% 視為多頭
        self.confidence_boost = 10   # 多頭時信心加成

        # 🆕 進階熔斷參數
        self.foreign_circuit_breaker = -500   # 外資賣超 > 500億 → 完全停止開倉
        self.open30min_drop_limit = -1.5      # 開盤30分鐘跌 > 1.5% → 停止開倉
        self.circuit_cache = {}
        self.circuit_cache_time = None
        self.circuit_cache_duration = 600  # 10 分鐘快取
    
    def get_market_condition(self, force_refresh: bool = False) -> Dict:
        """
        獲取大盤狀況 (優先使用 MIS 實時 API)
        
        Returns:
            {
                'allow_long': bool,
                'condition': 'BULL' | 'BEAR' | 'NEUTRAL',
                'change_pct': float,
                'confidence_boost': int,
                'reason': str
            }
        """
        now = datetime.now()
        
        # 檢查快取
        if not force_refresh and self.cache and self.cache_time:
            elapsed = (now - self.cache_time).total_seconds()
            if elapsed < self.cache_duration:
                return self.cache
        
        try:
            import requests
            # 獲取加權指數數據 (MIS API)
            mis_url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw"
            response = requests.get(mis_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("msgArray") and len(data["msgArray"]) > 0:
                    info = data["msgArray"][0]
                    current = float(info.get("z", info.get("o", "0")))
                    yesterday = float(info.get("y", "0"))
                    
                    if current > 0 and yesterday > 0:
                        change_pct = ((current - yesterday) / yesterday) * 100
                        index_value = round(current, 2)
                        
                        # 判斷市場狀況
                        if change_pct <= self.bear_threshold:
                            result = {
                                'allow_long': False,
                                'condition': 'BEAR',
                                'change_pct': round(change_pct, 2),
                                'confidence_boost': -10,
                                'reason': f'🐻 大盤下跌 {change_pct:.2f}% ({round(current-yesterday, 2)} 點)，不適合做多',
                                'index_value': index_value
                            }
                        elif change_pct >= self.bull_threshold:
                            result = {
                                'allow_long': True,
                                'condition': 'BULL',
                                'change_pct': round(change_pct, 2),
                                'confidence_boost': self.confidence_boost,
                                'reason': f'🐂 大盤上漲 {change_pct:.2f}% ({round(current-yesterday, 2)} 點)，多方氣氛佳',
                                'index_value': index_value
                            }
                        else:
                            result = {
                                'allow_long': True,
                                'condition': 'NEUTRAL',
                                'change_pct': round(change_pct, 2),
                                'confidence_boost': 0,
                                'reason': f'⚖️ 大盤平盤 {change_pct:.2f}% ({round(current-yesterday, 2)} 點)',
                                'index_value': index_value
                            }
                        
                        self.cache = result
                        self.cache_time = now
                        return result

            # 如果 MIS 失敗，回退到 yfinance
            ticker = yf.Ticker(self.twii_symbol)
            hist = ticker.history(period="2d")
            
            if len(hist) < 2:
                # 如果都失敗，回傳最後已知的快取或中性結果
                if self.cache: return self.cache
                return self._neutral_result("無法獲取大盤數據")
            
            prev_close = hist['Close'].iloc[-2]
            current = hist['Close'].iloc[-1]
            change_pct = ((current - prev_close) / prev_close) * 100
            
            # ... (原本的邏輯) ...
            if change_pct <= self.bear_threshold:
                result = {'allow_long': False, 'condition': 'BEAR', 'change_pct': round(change_pct, 2), 'confidence_boost': -10, 
                          'reason': f'🐻 大盤下跌 {change_pct:.2f}%，不適合做多', 'index_value': round(current, 2)}
            elif change_pct >= self.bull_threshold:
                result = {'allow_long': True, 'condition': 'BULL', 'change_pct': round(change_pct, 2), 'confidence_boost': self.confidence_boost,
                          'reason': f'🐂 大盤上漲 {change_pct:.2f}%，多方氣氛佳', 'index_value': round(current, 2)}
            else:
                result = {'allow_long': True, 'condition': 'NEUTRAL', 'change_pct': round(change_pct, 2), 'confidence_boost': 0,
                          'reason': f'⚖️ 大盤平盤 {change_pct:.2f}%', 'index_value': round(current, 2)}
            
            self.cache = result
            self.cache_time = now
            return result
            
        except Exception as e:
            logger.warning(f"獲取大盤狀況失敗: {e}")
            if self.cache: return self.cache
            return self._neutral_result(f"獲取失敗: {e}")
    
    def _neutral_result(self, reason: str) -> Dict:
        """返回中性結果"""
        return {
            'allow_long': True,
            'condition': 'NEUTRAL',
            'change_pct': 0,
            'confidence_boost': 0,
            'reason': reason
        }
    
    def check_circuit_breaker(self) -> Dict:
        """
        🆕 進階熔斷機制
        條件1：外資賣超金額 > 500億
        條件2：開盤後30分鐘內大盤跌幅 > 1.5%
        """
        now = datetime.now()
        # 快取10分鐘
        if self.circuit_cache and self.circuit_cache_time:
            if (now - self.circuit_cache_time).total_seconds() < self.circuit_cache_duration:
                return self.circuit_cache

        result = {'triggered': False, 'reason': '', 'details': {}}

        try:
            import requests

            # --- 外資賣超檢查 ---
            try:
                resp = requests.get(
                    "http://localhost:8000/api/market-decision/status",
                    timeout=5
                )
                if resp.status_code == 200:
                    data = resp.json()
                    market_data = data.get('market_data', {})
                    foreign_net = market_data.get('foreign_net', 0)   # 億元
                    change_pct  = market_data.get('change_pct', 0)

                    result['details']['foreign_net'] = foreign_net
                    result['details']['change_pct'] = change_pct

                    if foreign_net <= self.foreign_circuit_breaker:
                        result['triggered'] = True
                        result['reason'] = (
                            f"🚨 外資大賣超 {foreign_net:.0f} 億 "
                            f"（超過熔斷門檻 {self.foreign_circuit_breaker} 億），"
                            f"停止所有新建倉"
                        )
                        logger.warning(result['reason'])
                        self.circuit_cache = result
                        self.circuit_cache_time = now
                        return result
            except Exception as e:
                logger.debug(f"外資數據取得失敗: {e}")

            # --- 開盤30分鐘跌幅檢查 ---
            current_time = now.time()
            market_open = time(9, 0)
            thirty_min   = time(9, 30)

            if market_open <= current_time <= thirty_min:
                try:
                    mis_url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw"
                    resp = requests.get(mis_url, timeout=5)
                    if resp.status_code == 200:
                        info = resp.json().get('msgArray', [{}])[0]
                        current_price = float(info.get('z', info.get('o', '0')) or 0)
                        open_price    = float(info.get('o', '0') or 0)
                        if open_price > 0 and current_price > 0:
                            open_drop_pct = (current_price - open_price) / open_price * 100
                            result['details']['open30_drop_pct'] = round(open_drop_pct, 2)
                            if open_drop_pct <= self.open30min_drop_limit:
                                result['triggered'] = True
                                result['reason'] = (
                                    f"🚨 開盤30分鐘內跌幅 {open_drop_pct:.2f}% "
                                    f"（超過門檻 {self.open30min_drop_limit}%），"
                                    f"停止新建倉"
                                )
                                logger.warning(result['reason'])
                except Exception as e:
                    logger.debug(f"開盤跌幅檢查失敗: {e}")

        except Exception as e:
            logger.debug(f"熔斷檢查異常: {e}")

        self.circuit_cache = result
        self.circuit_cache_time = now
        return result

    def should_enter_position(self, signal: Dict) -> Dict:
        """
        判斷是否應該進場（含進階熔斷 + 大盤過濾）
        
        Args:
            signal: 進場信號
        
        Returns:
            {
                'allow': bool,
                'reason': str,
                'adjusted_confidence': int
            }
        """
        original_confidence = signal.get('confidence', 75)

        # ① 進階熔斷優先檢查
        circuit = self.check_circuit_breaker()
        if circuit.get('triggered'):
            return {
                'allow': False,
                'reason': circuit['reason'],
                'adjusted_confidence': original_confidence,
                'circuit_breaker': True
            }

        # ② 一般大盤過濾
        market = self.get_market_condition()
        if not market['allow_long']:
            logger.info(f"❌ 大盤過濾：{market['reason']}")
            return {
                'allow': False,
                'reason': market['reason'],
                'adjusted_confidence': original_confidence
            }
        
        # ③ 調整信心度
        adjusted = original_confidence + market['confidence_boost']
        adjusted = min(100, max(0, adjusted))
        
        return {
            'allow': True,
            'reason': market['reason'],
            'adjusted_confidence': adjusted,
            'market_condition': market['condition']
        }


# =====================================================
# 🆕 最大持倉數量限制器
# =====================================================

class PositionSizeLimiter:
    """
    控制同時持倉數量，避免過度分散導致手續費損耗過高。
    
    規則：
    - 最多同時持倉：MAX_OPEN_POSITIONS 支（預設 12）
    - 每日最多新建倉：MAX_NEW_POSITIONS_PER_DAY 支（預設 5）
    """

    MAX_OPEN_POSITIONS = 12      # 最多同時持倉數
    MAX_NEW_PER_DAY    = 5       # 每日最多新建倉數

    def __init__(self):
        self._today_opened = 0
        self._last_reset_date: Optional[str] = None

    def _reset_if_new_day(self):
        today_str = datetime.now().strftime('%Y-%m-%d')
        if self._last_reset_date != today_str:
            self._today_opened = 0
            self._last_reset_date = today_str

    async def can_open_new_position(self, db=None) -> Dict:
        """
        檢查是否可以開新倉。
        Returns: {'allow': bool, 'reason': str, 'open_count': int, 'today_count': int}
        """
        self._reset_if_new_day()

        # 查詢目前持倉數
        open_count = 0
        if db is not None:
            try:
                from app.models.portfolio import Portfolio
                from sqlalchemy import select, func
                result = await db.execute(
                    select(func.count()).where(
                        Portfolio.status == 'open',
                        Portfolio.is_simulated == True
                    )
                )
                open_count = result.scalar() or 0
            except Exception as e:
                logger.warning(f"查詢持倉數失敗: {e}")

        if open_count >= self.MAX_OPEN_POSITIONS:
            reason = (
                f"🚦 持倉數量已達上限（{open_count}/{self.MAX_OPEN_POSITIONS} 支），"
                f"請先等待現有持倉結束再開新倉"
            )
            logger.warning(reason)
            return {'allow': False, 'reason': reason,
                    'open_count': open_count, 'today_count': self._today_opened}

        if self._today_opened >= self.MAX_NEW_PER_DAY:
            reason = (
                f"🚦 今日已開 {self._today_opened}/{self.MAX_NEW_PER_DAY} 筆新倉，"
                f"達到每日上限，明日再開"
            )
            logger.warning(reason)
            return {'allow': False, 'reason': reason,
                    'open_count': open_count, 'today_count': self._today_opened}

        return {
            'allow': True,
            'reason': f'持倉 {open_count}/{self.MAX_OPEN_POSITIONS} | 今日已開 {self._today_opened}/{self.MAX_NEW_PER_DAY}',
            'open_count': open_count,
            'today_count': self._today_opened
        }

    def record_opened(self):
        """記錄已成功開倉一筆"""
        self._reset_if_new_day()
        self._today_opened += 1
        logger.info(f"📈 今日已建倉 {self._today_opened}/{self.MAX_NEW_PER_DAY} 筆")


class DynamicStopLoss:
    """動態停損管理器"""
    
    def __init__(self):
        # 停損參數
        self.initial_stop_loss = 0.5      # 初始停損 0.5%
        self.profit_protect_threshold = 2  # 獲利 2% 後啟動保護
        self.profit_protect_level = 0.5   # 保護到 0.5% 利潤
        self.trailing_activation = 3       # 3% 啟動移動停損
        self.trailing_distance = 1         # 移動停損距離 1%
    
    def check_exit(self, position: Dict, current_price: float) -> Dict:
        """
        檢查是否應該出場
        
        Args:
            position: 持倉資料，包含 entry_price, high_since_entry
            current_price: 當前價格
        
        Returns:
            {
                'should_exit': bool,
                'reason': str,
                'exit_type': 'stop_loss' | 'profit_protect' | 'trailing' | None
            }
        """
        entry_price = position.get('entry_price', 0)
        if entry_price <= 0:
            return {'should_exit': False, 'reason': '無效進場價'}
        
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        high_price = position.get('high_since_entry', current_price)
        
        # 策略 1：初始停損
        if pnl_pct <= -self.initial_stop_loss:
            return {
                'should_exit': True,
                'reason': f'觸發初始停損（-{self.initial_stop_loss}%）',
                'exit_type': 'stop_loss',
                'exit_price': entry_price * (1 - self.initial_stop_loss / 100)
            }
        
        # 策略 2：獲利保護
        if pnl_pct > self.profit_protect_threshold:
            # 如果獲利回吐到只剩 0.5%，出場
            protect_price = entry_price * (1 + self.profit_protect_level / 100)
            if current_price <= protect_price:
                return {
                    'should_exit': True,
                    'reason': f'獲利保護（曾獲利 {pnl_pct:.1f}% 回吐）',
                    'exit_type': 'profit_protect',
                    'exit_price': current_price
                }
        
        # 策略 3：移動停損
        if high_price > 0:
            high_pnl = ((high_price - entry_price) / entry_price) * 100
            
            if high_pnl >= self.trailing_activation:
                trailing_stop = high_price * (1 - self.trailing_distance / 100)
                if current_price <= trailing_stop:
                    return {
                        'should_exit': True,
                        'reason': f'移動停損（高點 ${high_price:.2f} 回落 {self.trailing_distance}%）',
                        'exit_type': 'trailing',
                        'exit_price': trailing_stop
                    }
        
        return {'should_exit': False, 'reason': '持續持有'}
    
    def get_status(self, position: Dict, current_price: float) -> Dict:
        """獲取當前停損狀態"""
        entry_price = position.get('entry_price', 0)
        high_price = position.get('high_since_entry', current_price)
        
        if entry_price <= 0:
            return {}
        
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        
        # 計算各種停損價位
        initial_stop = entry_price * (1 - self.initial_stop_loss / 100)
        protect_price = entry_price * (1 + self.profit_protect_level / 100) if pnl_pct > self.profit_protect_threshold else None
        trailing_stop = high_price * (1 - self.trailing_distance / 100) if high_price > entry_price * (1 + self.trailing_activation / 100) else None
        
        # 取最高的停損價
        active_stop = max(filter(None, [initial_stop, protect_price, trailing_stop]))
        
        return {
            'entry_price': entry_price,
            'current_price': current_price,
            'pnl_pct': round(pnl_pct, 2),
            'initial_stop': round(initial_stop, 2),
            'protect_stop': round(protect_price, 2) if protect_price else None,
            'trailing_stop': round(trailing_stop, 2) if trailing_stop else None,
            'active_stop': round(active_stop, 2) if active_stop else None
        }


# 單例
market_filter = MarketConditionFilter()
dynamic_stop = DynamicStopLoss()
position_limiter = PositionSizeLimiter()   # 🆕 持倉數量限制器


# 測試
if __name__ == "__main__":
    print("="*60)
    print("  市場狀況過濾器測試")
    print("="*60)
    
    # 測試大盤狀況
    condition = market_filter.get_market_condition()
    print(f"\n📊 大盤狀況:")
    print(f"   狀態: {condition['condition']}")
    print(f"   漲跌: {condition['change_pct']:+.2f}%")
    print(f"   允許做多: {condition['allow_long']}")
    print(f"   原因: {condition['reason']}")
    
    # 測試進場過濾
    test_signal = {'symbol': '2330', 'confidence': 75}
    result = market_filter.should_enter_position(test_signal)
    print(f"\n🎯 進場過濾測試:")
    print(f"   允許: {result['allow']}")
    print(f"   調整後信心度: {result['adjusted_confidence']}")
    print(f"   原因: {result['reason']}")
    
    # 測試動態停損
    print(f"\n🛡️ 動態停損測試:")
    
    test_position = {'entry_price': 100, 'high_since_entry': 105}
    
    test_prices = [99.5, 98, 102, 101, 104]
    for price in test_prices:
        exit_check = dynamic_stop.check_exit(test_position, price)
        pnl = (price - 100) / 100 * 100
        print(f"   價格 ${price} ({pnl:+.1f}%): {exit_check['reason']}")
