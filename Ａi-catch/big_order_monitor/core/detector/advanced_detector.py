"""
進階大單偵測器
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
import logging

if TYPE_CHECKING:
    from ..config.trading_config import AdvancedSystemConfig

logger = logging.getLogger(__name__)


@dataclass
class EnhancedSignal:
    """增強型訊號"""
    # 基本資訊
    stock_code: str
    stock_name: str
    signal_type: str  # 'BUY' or 'SELL'
    timestamp: datetime
    price: float
    
    # 多維度分數
    composite_score: float  # 綜合分數
    confidence: float  # 信心度
    quality_score: float  # 品質分數
    momentum_score: float  # 動能分數
    volume_score: float  # 成交量分數
    pattern_score: float  # 型態分數
    
    # 其他資訊
    reason: str  # 觸發原因
    warnings: List[str] = field(default_factory=list)  # 警告訊息
    stop_loss: float = 0.0  # 參考停損價
    take_profit: float = 0.0  # 參考停利價
    position_size: float = 0.0  # 建議部位（僅供參考）
    
    # 詳細數據
    metadata: Dict = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        """訊號是否有效"""
        return (
            self.composite_score >= 0.65 and
            self.confidence >= 0.6 and
            self.quality_score >= 0.6 and
            len(self.warnings) < 5 and
            '假單疑慮' not in self.warnings
        )
    
    @property
    def quality_level(self) -> str:
        """品質等級"""
        if self.quality_score >= 0.8:
            return "優秀"
        elif self.quality_score >= 0.7:
            return "良好"
        elif self.quality_score >= 0.6:
            return "普通"
        else:
            return "不佳"
    
    def to_dict(self) -> Dict:
        """轉為字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'signal_type': self.signal_type,
            'price': self.price,
            'composite_score': round(self.composite_score, 4),
            'confidence': round(self.confidence, 4),
            'quality_score': round(self.quality_score, 4),
            'momentum_score': round(self.momentum_score, 4),
            'volume_score': round(self.volume_score, 4),
            'pattern_score': round(self.pattern_score, 4),
            'quality_level': self.quality_level,
            'reason': self.reason,
            'warnings': '|'.join(self.warnings),
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_size': self.position_size
        }
    
    def to_email_html(self) -> str:
        """轉為 Email HTML 格式"""
        color = "#22c55e" if self.signal_type == "BUY" else "#ef4444"
        quality_color = "#22c55e" if self.quality_score >= 0.8 else "#f59e0b" if self.quality_score >= 0.7 else "#6b7280"
        
        return f"""
        <div style="border: 2px solid {color}; border-radius: 12px; padding: 20px; margin: 10px 0; background: #f9fafb;">
            <h2 style="color: {color}; margin: 0 0 15px 0;">
                {'🟢 買進訊號' if self.signal_type == 'BUY' else '🔴 賣出訊號'} - {self.stock_code} {self.stock_name}
            </h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>價格</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right; font-size: 18px; font-weight: bold;">${self.price:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>綜合評分</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">{self.composite_score:.1%}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>信心度</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">{self.confidence:.1%}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>品質等級</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right; color: {quality_color}; font-weight: bold;">{self.quality_level} ({self.quality_score:.1%})</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>動能分數</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">{self.momentum_score:.1%}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>成交量分數</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">{self.volume_score:.1%}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>型態分數</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">{self.pattern_score:.1%}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>觸發原因</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">{self.reason}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>參考停損</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">${self.stop_loss:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>參考停利</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">${self.take_profit:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>時間</strong></td>
                    <td style="padding: 8px; text-align: right;">{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            {f'<p style="color: #f59e0b; margin-top: 15px;">⚠️ 警告: {", ".join(self.warnings)}</p>' if self.warnings else ''}
        </div>
        """


class AdvancedBigOrderDetector:
    """進階大單偵測器"""
    
    def __init__(self, config: "AdvancedSystemConfig"):
        self.config = config
        
        # Tick資料緩衝區
        self.tick_buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5000))
        
        # 訊號歷史
        self.signal_history: List[EnhancedSignal] = []
        
        # 統計數據
        self.stats = {
            'total_ticks': 0,
            'big_orders': 0,
            'fake_orders': 0,
            'signals_generated': 0,
            'valid_signals': 0,
            'quality_excellent': 0,
            'quality_good': 0,
            'quality_fair': 0,
            'quality_poor': 0
        }
        
        logger.info("✅ 進階大單偵測器初始化完成")
    
    async def process_tick_stream(self, stock_code: str, tick: Dict) -> Optional[EnhancedSignal]:
        """處理tick串流"""
        try:
            # 加入緩衝區
            self.tick_buffers[stock_code].append(tick)
            self.stats['total_ticks'] += 1
            
            # 檢查是否為大單
            if not self._is_big_order(stock_code, tick):
                return None
            
            self.stats['big_orders'] += 1
            
            # 檢查假單
            if self._is_fake_order(stock_code, tick):
                self.stats['fake_orders'] += 1
                logger.debug(f"{stock_code} 偵測到假單，已過濾")
                return None
            
            # 分析並產生訊號
            signal = self._generate_enhanced_signal(stock_code, tick)
            
            if signal:
                self.stats['signals_generated'] += 1
                
                # 更新品質統計
                if signal.quality_score >= 0.8:
                    self.stats['quality_excellent'] += 1
                elif signal.quality_score >= 0.7:
                    self.stats['quality_good'] += 1
                elif signal.quality_score >= 0.6:
                    self.stats['quality_fair'] += 1
                else:
                    self.stats['quality_poor'] += 1
                
                if signal.is_valid:
                    self.stats['valid_signals'] += 1
                    self.signal_history.append(signal)
                    return signal
            
            return None
            
        except Exception as e:
            logger.error(f"處理tick失敗: {e}", exc_info=True)
            return None
    
    def _is_big_order(self, stock_code: str, tick: Dict) -> bool:
        """檢查是否為大單"""
        if stock_code not in self.config.watchlist:
            return False
        
        stock_config = self.config.watchlist[stock_code]
        threshold = stock_config.big_order_threshold
        volume = tick.get('volume', 0)
        
        if volume < threshold:
            return False
        
        # 檢查時間窗口內的累積大單
        return self._check_accumulated_big_orders(stock_code, tick)
    
    def _check_accumulated_big_orders(self, stock_code: str, current_tick: Dict) -> bool:
        """檢查時間窗口內的累積大單"""
        stock_config = self.config.watchlist[stock_code]
        threshold = stock_config.big_order_threshold
        
        # 取得時間窗口
        current_time = current_tick.get('timestamp', datetime.now())
        if isinstance(current_time, str):
            current_time = datetime.fromisoformat(current_time)
        
        window_start = current_time - timedelta(
            minutes=self.config.detector_config.base_time_window
        )
        
        # 篩選窗口內的大單
        recent_ticks = []
        for t in self.tick_buffers[stock_code]:
            t_time = t.get('timestamp', datetime.min)
            if isinstance(t_time, str):
                try:
                    t_time = datetime.fromisoformat(t_time)
                except:
                    t_time = datetime.min
            if t_time >= window_start:
                recent_ticks.append(t)
        
        big_orders = [t for t in recent_ticks if t.get('volume', 0) >= threshold]
        
        if len(big_orders) < self.config.detector_config.base_min_big_orders:
            return False
        
        # 檢查方向一致性
        buy_volume = sum(t.get('volume', 0) for t in big_orders if t.get('bs_flag') == 'B')
        sell_volume = sum(t.get('volume', 0) for t in big_orders if t.get('bs_flag') == 'S')
        total_big_volume = buy_volume + sell_volume
        
        if total_big_volume == 0:
            return False
        
        direction_ratio = max(buy_volume, sell_volume) / total_big_volume
        
        if direction_ratio < self.config.detector_config.min_direction_ratio:
            logger.debug(f"{stock_code} 大單方向不一致: {direction_ratio:.2%}")
            return False
        
        # 檢查大單佔比
        total_volume = sum(t.get('volume', 0) for t in recent_ticks)
        if total_volume > 0:
            big_order_ratio = total_big_volume / total_volume
            return big_order_ratio >= self.config.detector_config.base_min_volume_ratio
        
        return False
    
    def _is_fake_order(self, stock_code: str, tick: Dict) -> bool:
        """檢查是否為假單"""
        if not self.config.detector_config.enable_fake_order_detection:
            return False
        
        # 檢查連續同價大單
        recent = list(self.tick_buffers[stock_code])[-20:]
        current_price = tick.get('price', 0)
        stock_config = self.config.watchlist[stock_code]
        threshold = stock_config.big_order_threshold
        
        same_price_big_orders = [
            t for t in recent
            if t.get('price') == current_price and
               t.get('volume', 0) >= threshold
        ]
        
        if len(same_price_big_orders) >= self.config.detector_config.max_same_price_orders:
            return True
        
        # 檢查價格衝擊
        if len(recent) >= 10:
            prices = [t.get('price', 0) for t in recent[-10:] if t.get('price', 0) > 0]
            if prices:
                price_before = prices[0]
                price_impact = abs(current_price - price_before) / price_before if price_before > 0 else 0
                
                # 超大單應有明顯價格衝擊
                if tick.get('volume', 0) >= threshold * 3:
                    if price_impact < 0.001:  # 價格變動不到0.1%
                        return True
        
        return False
    
    def _generate_enhanced_signal(self, stock_code: str, tick: Dict) -> Optional[EnhancedSignal]:
        """產生增強訊號"""
        try:
            stock_config = self.config.watchlist[stock_code]
            
            # 分析訂單流
            analysis = self._analyze_order_flow(stock_code)
            
            if not analysis:
                return None
            
            # 計算各維度分數
            quality_score = self._calculate_quality_score(analysis)
            momentum_score = self._calculate_momentum_score(analysis)
            volume_score = self._calculate_volume_score(stock_code, analysis)
            pattern_score = self._calculate_pattern_score(analysis)
            
            # 綜合分數（加權平均）
            composite_score = (
                quality_score * 0.30 +
                momentum_score * 0.25 +
                volume_score * 0.25 +
                pattern_score * 0.20
            )
            
            # 決定訊號方向
            buy_ratio = analysis.get('buy_ratio', 0.5)
            price_change = analysis.get('price_change_pct', 0)
            
            if buy_ratio > 0.65 and price_change > 0.003:
                signal_type = 'BUY'
                confidence = buy_ratio
            elif buy_ratio < 0.35 and price_change < -0.003:
                signal_type = 'SELL'
                confidence = 1 - buy_ratio
            else:
                return None
            
            # 檢查是否達到最低標準
            if composite_score < self.config.detector_config.min_composite_score:
                return None
            
            # 計算參考停損停利
            current_price = tick.get('price', 0)
            if signal_type == 'BUY':
                stop_loss = current_price * 0.985  # -1.5%
                take_profit = current_price * 1.025  # +2.5%
            else:
                stop_loss = current_price * 1.015  # +1.5%
                take_profit = current_price * 0.975  # -2.5%
            
            # 建議部位（僅供參考，不執行交易）
            position_size = 300000  # 固定30萬參考值
            
            # 產生警告
            warnings = self._generate_warnings(analysis, quality_score, composite_score)
            
            # 取得時間戳
            timestamp = tick.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            # 建立訊號
            signal = EnhancedSignal(
                stock_code=stock_code,
                stock_name=stock_config.name,
                signal_type=signal_type,
                timestamp=timestamp,
                price=current_price,
                composite_score=composite_score,
                confidence=confidence,
                quality_score=quality_score,
                momentum_score=momentum_score,
                volume_score=volume_score,
                pattern_score=pattern_score,
                reason=self._generate_reason(analysis, signal_type),
                warnings=warnings,
                stop_loss=round(stop_loss, 2),
                take_profit=round(take_profit, 2),
                position_size=position_size,
                metadata=analysis
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"產生訊號失敗: {e}", exc_info=True)
            return None
    
    def _analyze_order_flow(self, stock_code: str) -> Dict:
        """分析訂單流"""
        window_minutes = self.config.detector_config.base_time_window
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        
        recent_ticks = []
        for t in self.tick_buffers[stock_code]:
            t_time = t.get('timestamp', datetime.min)
            if isinstance(t_time, str):
                try:
                    t_time = datetime.fromisoformat(t_time)
                except:
                    t_time = datetime.min
            if t_time >= cutoff_time:
                recent_ticks.append(t)
        
        if len(recent_ticks) < 5:
            return {}
        
        # 基本統計
        buy_ticks = [t for t in recent_ticks if t.get('bs_flag') == 'B']
        sell_ticks = [t for t in recent_ticks if t.get('bs_flag') == 'S']
        
        buy_volume = sum(t.get('volume', 0) for t in buy_ticks)
        sell_volume = sum(t.get('volume', 0) for t in sell_ticks)
        total_volume = buy_volume + sell_volume
        
        # 價格動態
        prices = [t.get('price', 0) for t in recent_ticks if t.get('price', 0) > 0]
        if not prices or len(prices) < 2:
            return {}
        
        price_change_pct = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
        price_volatility = np.std(prices) / np.mean(prices) if len(prices) > 1 else 0
        
        # 大單分析
        stock_config = self.config.watchlist[stock_code]
        threshold = stock_config.big_order_threshold
        
        big_buy_ticks = [t for t in buy_ticks if t.get('volume', 0) >= threshold]
        big_sell_ticks = [t for t in sell_ticks if t.get('volume', 0) >= threshold]
        
        big_buy_volume = sum(t.get('volume', 0) for t in big_buy_ticks)
        big_sell_volume = sum(t.get('volume', 0) for t in big_sell_ticks)
        
        return {
            'total_volume': total_volume,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'buy_ratio': buy_volume / total_volume if total_volume > 0 else 0.5,
            'price_change_pct': price_change_pct,
            'price_volatility': price_volatility,
            'price_high': max(prices),
            'price_low': min(prices),
            'big_buy_volume': big_buy_volume,
            'big_sell_volume': big_sell_volume,
            'big_buy_ratio': big_buy_volume / buy_volume if buy_volume > 0 else 0,
            'big_sell_ratio': big_sell_volume / sell_volume if sell_volume > 0 else 0,
            'num_big_orders': len(big_buy_ticks) + len(big_sell_ticks),
            'avg_tick_volume': float(np.mean([t.get('volume', 0) for t in recent_ticks])),
            'max_tick_volume': max(t.get('volume', 0) for t in recent_ticks)
        }
    
    def _calculate_quality_score(self, analysis: Dict) -> float:
        """計算品質分數"""
        score = 1.0
        
        # 方向明確度
        buy_ratio = analysis.get('buy_ratio', 0.5)
        if 0.45 <= buy_ratio <= 0.55:
            score *= 0.5  # 方向不明確
        elif 0.40 <= buy_ratio <= 0.60:
            score *= 0.8  # 方向偏弱
        else:
            score *= 1.0  # 方向明確
        
        # 大單集中度
        big_buy_ratio = analysis.get('big_buy_ratio', 0)
        big_sell_ratio = analysis.get('big_sell_ratio', 0)
        big_order_clarity = abs(big_buy_ratio - big_sell_ratio)
        
        if big_order_clarity < 0.3:
            score *= 0.6
        elif big_order_clarity < 0.5:
            score *= 0.85
        else:
            score *= 1.0
        
        return min(score, 1.0)
    
    def _calculate_momentum_score(self, analysis: Dict) -> float:
        """計算動能分數"""
        price_change = abs(analysis.get('price_change_pct', 0))
        
        # 理想範圍: 0.5% ~ 3%
        if 0.005 < price_change < 0.03:
            return 0.9
        elif 0.003 < price_change < 0.05:
            return 0.7
        elif price_change >= 0.001:
            return 0.5
        else:
            return 0.3
    
    def _calculate_volume_score(self, stock_code: str, analysis: Dict) -> float:
        """計算成交量分數"""
        stock_config = self.config.watchlist[stock_code]
        total_volume = analysis.get('total_volume', 0)
        avg_daily = stock_config.avg_daily_volume
        
        # 與日均量比較
        if avg_daily > 0:
            volume_ratio = total_volume / (avg_daily * 0.1)  # 窗口內預期量
            if volume_ratio > 1.5:
                return 0.9
            elif volume_ratio > 1.0:
                return 0.75
            elif volume_ratio > 0.5:
                return 0.6
            else:
                return 0.4
        
        # 絕對量判斷
        if total_volume > 1000:
            return 0.8
        elif total_volume > 500:
            return 0.6
        else:
            return 0.4
    
    def _calculate_pattern_score(self, analysis: Dict) -> float:
        """計算型態分數（價量配合）"""
        buy_ratio = analysis.get('buy_ratio', 0.5)
        price_change = analysis.get('price_change_pct', 0)
        big_buy_ratio = analysis.get('big_buy_ratio', 0)
        big_sell_ratio = analysis.get('big_sell_ratio', 0)
        
        score = 0.5  # 基礎分
        
        # 價量配合檢查
        if buy_ratio > 0.6 and price_change > 0:
            # 買盤強 + 價格上漲
            if big_buy_ratio > big_sell_ratio:
                score = 0.9  # 完美配合
            else:
                score = 0.7  # 基本配合
        elif buy_ratio < 0.4 and price_change < 0:
            # 賣壓重 + 價格下跌
            if big_sell_ratio > big_buy_ratio:
                score = 0.9
            else:
                score = 0.7
        elif (buy_ratio > 0.6 and price_change < -0.005) or (buy_ratio < 0.4 and price_change > 0.005):
            # 價量背離
            score = 0.3
        
        return score
    
    def _generate_warnings(self, analysis: Dict, quality_score: float, composite_score: float) -> List[str]:
        """產生警告訊息"""
        warnings = []
        
        # 品質警告
        if quality_score < 0.6:
            warnings.append("品質偏低")
        
        # 方向警告
        buy_ratio = analysis.get('buy_ratio', 0.5)
        if 0.45 <= buy_ratio <= 0.55:
            warnings.append("方向不明確")
        
        # 價量背離
        price_change = analysis.get('price_change_pct', 0)
        if (buy_ratio > 0.6 and price_change < -0.005):
            warnings.append("價量背離(買盤強但價跌)")
        elif (buy_ratio < 0.4 and price_change > 0.005):
            warnings.append("價量背離(賣壓重但價漲)")
        
        # 波動警告
        if abs(price_change) > 0.05:
            warnings.append("波動過大")
        
        # 成交量警告
        total_volume = analysis.get('total_volume', 0)
        if total_volume < 300:
            warnings.append("成交量偏低")
        
        return warnings
    
    def _generate_reason(self, analysis: Dict, signal_type: str) -> str:
        """產生訊號原因"""
        reasons = []
        
        buy_ratio = analysis.get('buy_ratio', 0.5)
        price_change = analysis.get('price_change_pct', 0)
        num_big_orders = analysis.get('num_big_orders', 0)
        
        # 主要力道
        if signal_type == 'BUY':
            reasons.append(f"買盤力道{buy_ratio:.1%}")
        else:
            reasons.append(f"賣壓力道{1-buy_ratio:.1%}")
        
        # 大單數量
        if num_big_orders >= 5:
            reasons.append(f"{num_big_orders}筆大單集中")
        
        # 價格動向
        if abs(price_change) > 0.01:
            direction = "上漲" if price_change > 0 else "下跌"
            reasons.append(f"價格{direction}{abs(price_change):.2%}")
        
        # 大單主導
        big_buy_ratio = analysis.get('big_buy_ratio', 0)
        big_sell_ratio = analysis.get('big_sell_ratio', 0)
        if max(big_buy_ratio, big_sell_ratio) > 0.5:
            ratio = max(big_buy_ratio, big_sell_ratio)
            reasons.append(f"大單主導{ratio:.1%}")
        
        return "，".join(reasons) if reasons else "大單訊號"
    
    def get_performance_metrics(self) -> Dict:
        """取得效能指標"""
        total_signals = self.stats['signals_generated']
        
        return {
            'total_ticks': self.stats['total_ticks'],
            'big_orders': self.stats['big_orders'],
            'fake_orders': self.stats['fake_orders'],
            'signals_generated': total_signals,
            'valid_signals': self.stats['valid_signals'],
            'fake_order_rate': self.stats['fake_orders'] / max(self.stats['big_orders'], 1),
            'valid_signal_rate': self.stats['valid_signals'] / max(total_signals, 1),
            'signal_quality_distribution': {
                'excellent': self.stats['quality_excellent'],
                'good': self.stats['quality_good'],
                'fair': self.stats['quality_fair'],
                'poor': self.stats['quality_poor']
            },
            'avg_quality_score': float(np.mean([s.quality_score for s in self.signal_history[-100:]])) if self.signal_history else 0,
            'avg_composite_score': float(np.mean([s.composite_score for s in self.signal_history[-100:]])) if self.signal_history else 0
        }
    
    def export_signals(self, filepath: str = None) -> Optional[str]:
        """匯出訊號記錄"""
        import pandas as pd
        
        if not self.signal_history:
            logger.warning("沒有訊號可匯出")
            return None
        
        if filepath is None:
            filepath = f"signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        data = [signal.to_dict() for signal in self.signal_history]
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        logger.info(f"✅ 訊號已匯出至: {filepath}")
        return filepath
