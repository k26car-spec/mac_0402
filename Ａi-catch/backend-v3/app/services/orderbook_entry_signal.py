"""
五檔進場訊號系統 v1.0
目標：讓用戶一眼看出是否該買進

整合到當沖戰情室，提供即時進場建議
"""

from datetime import datetime
from typing import Dict, Optional, List, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EntrySignal(Enum):
    """進場訊號等級"""
    STRONG_BUY = "🟢 強力買進"       # 最佳買點
    BUY = "🟡 可以買進"              # 好買點
    WAIT = "⚪ 等待觀望"              # 觀望
    AVOID = "🔴 避免買進"             # 不要買


class OrderBookEntrySignal:
    """五檔進場訊號分析器"""
    
    def __init__(
        self,
        current_price: float,
        ma5: float = 0,
        ma10: float = 0,
        vwap: Optional[float] = None,
        open_price: float = 0,
        high_price: float = 0,
        low_price: float = 0
    ):
        self.current_price = current_price
        self.ma5 = ma5 if ma5 > 0 else current_price
        self.ma10 = ma10 if ma10 > 0 else current_price
        self.vwap = vwap if vwap and vwap > 0 else current_price
        self.open_price = open_price if open_price > 0 else current_price
        self.high_price = high_price if high_price > 0 else current_price
        self.low_price = low_price if low_price > 0 else current_price
        
        # 計算技術位置
        self.ma5_deviation = ((current_price - self.ma5) / self.ma5) * 100 if self.ma5 > 0 else 0
        self.vwap_deviation = ((current_price - self.vwap) / self.vwap) * 100 if self.vwap > 0 else 0
        
        # 計算今日漲跌幅
        self.change_pct = ((current_price - self.open_price) / self.open_price) * 100 if self.open_price > 0 else 0
    
    def analyze_for_entry(
        self,
        bid_volume: int,      # 買盤總量
        ask_volume: int,      # 賣盤總量
        bid_levels: List[Tuple[float, int]] = None,  # [(價格, 量), ...]
        ask_levels: List[Tuple[float, int]] = None,
        outside_ratio: Optional[float] = None  # 外盤比例 (0-100)
    ) -> Dict:
        """
        分析五檔並生成進場訊號
        
        Returns:
            Dict: 進場訊號分析結果
        """
        
        # 計算買賣力道
        total_volume = bid_volume + ask_volume
        bid_power = (bid_volume / total_volume * 100) if total_volume > 0 else 50
        ask_power = 100 - bid_power
        
        # === 多維度分析進場訊號 ===
        
        signal_score = 0  # 評分系統（0-100）
        reasons = []
        
        # 1. 五檔買賣力道（30分）
        if bid_power > ask_power + 20:
            signal_score += 30
            reasons.append(f"✅ 買盤壓倒性優勢（{bid_power:.1f}% vs {ask_power:.1f}%）")
        elif bid_power > ask_power + 10:
            signal_score += 20
            reasons.append(f"✅ 買盤較強（{bid_power:.1f}% vs {ask_power:.1f}%）")
        elif bid_power > ask_power:
            signal_score += 10
            reasons.append(f"⚪ 買盤略強（{bid_power:.1f}% vs {ask_power:.1f}%）")
        else:
            signal_score -= 10
            reasons.append(f"❌ 賣壓較重（賣 {ask_power:.1f}% vs 買 {bid_power:.1f}%）")
        
        # 2. 外盤比例（20分）
        if outside_ratio is not None:
            if outside_ratio > 60:
                signal_score += 20
                reasons.append(f"✅ 外盤主導（{outside_ratio:.0f}%）- 買盤積極")
            elif outside_ratio < 40:
                signal_score -= 10
                reasons.append(f"❌ 內盤主導（外盤 {outside_ratio:.0f}%）- 賣盤積極")
            else:
                signal_score += 5
                reasons.append(f"⚪ 內外盤均衡（{outside_ratio:.0f}%）")
        
        # 3. 技術位置（MA5）（30分）
        if -3 < self.ma5_deviation < 0:
            # 價格在 MA5 下方 0-3%（最佳買點）
            signal_score += 30
            reasons.append(f"✅ 回測 MA5 買點（乖離 {self.ma5_deviation:.2f}%）")
        elif 0 <= self.ma5_deviation < 2:
            # 價格在 MA5 上方 0-2%（還可以）
            signal_score += 15
            reasons.append(f"⚪ 接近 MA5（乖離 {self.ma5_deviation:+.2f}%）")
        elif self.ma5_deviation >= 5:
            # 價格離 MA5 太遠（追高）
            signal_score -= 20
            reasons.append(f"❌ 乖離過大（{self.ma5_deviation:+.2f}%），追高風險")
        elif self.ma5_deviation < -5:
            # 價格跌太深（可能破底）
            signal_score -= 15
            reasons.append(f"❌ 跌幅過深（{self.ma5_deviation:.2f}%），趨勢轉弱")
        else:
            signal_score += 5
            reasons.append(f"⚪ MA5 乖離 {self.ma5_deviation:+.2f}%")
        
        # 4. VWAP 位置（20分）
        if -2 < self.vwap_deviation < 0:
            signal_score += 20
            reasons.append(f"✅ VWAP 支撐（乖離 {self.vwap_deviation:.2f}%）")
        elif 0 <= self.vwap_deviation < 3:
            signal_score += 10
            reasons.append(f"⚪ 接近 VWAP（{self.vwap_deviation:+.2f}%）")
        elif self.vwap_deviation < -5:
            signal_score -= 10
            reasons.append(f"❌ 遠低於 VWAP（{self.vwap_deviation:.2f}%）")
        else:
            signal_score += 5
            reasons.append(f"⚪ VWAP 乖離 {self.vwap_deviation:+.2f}%")
        
        # 5. 今日走勢加分（額外）
        if 0 < self.change_pct < 3:
            signal_score += 10
            reasons.append(f"✅ 今日溫和上漲（{self.change_pct:+.2f}%）")
        elif self.change_pct >= 5:
            signal_score -= 5
            reasons.append(f"⚠️ 今日漲幅已大（{self.change_pct:+.2f}%）")
        elif self.change_pct < -3:
            signal_score -= 5
            reasons.append(f"⚠️ 今日跌幅較深（{self.change_pct:+.2f}%）")
        
        # === 決定進場訊號 ===
        
        if signal_score >= 70:
            signal = EntrySignal.STRONG_BUY
            confidence = min(95, signal_score)
            action = "立即進場（市價單或限價單），可用 70-80% 資金"
        elif signal_score >= 50:
            signal = EntrySignal.BUY
            confidence = signal_score
            action = "分批進場，先用 50% 資金"
        elif signal_score >= 30:
            signal = EntrySignal.WAIT
            confidence = signal_score
            action = f"暫時觀望，等待價格回測 ${self.ma5:.1f} 附近"
        else:
            signal = EntrySignal.AVOID
            confidence = max(0, signal_score)
            action = "不要買進，風險過高"
        
        # === 計算建議價格與停損停利 ===
        
        recommended_price = self.current_price
        
        # 停損：MA5 下方 3% 或今日低點下方 1%
        stop_loss = min(self.ma5 * 0.97, self.low_price * 0.99)
        
        # 停利：根據訊號強度
        if signal == EntrySignal.STRONG_BUY:
            take_profit = self.current_price * 1.08  # +8%
        elif signal == EntrySignal.BUY:
            take_profit = self.current_price * 1.05  # +5%
        else:
            take_profit = self.current_price * 1.03  # +3%
        
        # 計算風險報酬比
        risk = abs(recommended_price - stop_loss)
        reward = abs(take_profit - recommended_price)
        risk_reward = reward / risk if risk > 0 else 0
        
        return {
            'signal': signal.name,  # 用於 JSON 序列化
            'signal_text': signal.value,
            'signal_level': self._signal_to_level(signal),
            'signal_color': self._signal_to_color(signal),
            'confidence': confidence,
            'score': signal_score,
            'action': action,
            'reasons': reasons,
            'bid_power': round(bid_power, 1),
            'ask_power': round(ask_power, 1),
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'current_price': self.current_price,
            'recommended_price': round(recommended_price, 2),
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'risk_reward': round(risk_reward, 2),
            'ma5': round(self.ma5, 2),
            'ma5_deviation': round(self.ma5_deviation, 2),
            'vwap': round(self.vwap, 2),
            'vwap_deviation': round(self.vwap_deviation, 2),
            'change_pct': round(self.change_pct, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    def _signal_to_level(self, signal: EntrySignal) -> int:
        """訊號轉數字（用於排序）"""
        mapping = {
            EntrySignal.STRONG_BUY: 4,
            EntrySignal.BUY: 3,
            EntrySignal.WAIT: 2,
            EntrySignal.AVOID: 1
        }
        return mapping.get(signal, 1)
    
    def _signal_to_color(self, signal: EntrySignal) -> str:
        """訊號轉顏色"""
        mapping = {
            EntrySignal.STRONG_BUY: "green",
            EntrySignal.BUY: "yellow",
            EntrySignal.WAIT: "gray",
            EntrySignal.AVOID: "red"
        }
        return mapping.get(signal, "gray")


def analyze_entry_signal(
    symbol: str,
    current_price: float,
    bid_volume: int,
    ask_volume: int,
    ma5: float = 0,
    vwap: float = 0,
    open_price: float = 0,
    high_price: float = 0,
    low_price: float = 0,
    outside_ratio: float = None
) -> Dict:
    """
    便利函數：分析進場訊號
    
    Args:
        symbol: 股票代碼
        current_price: 現價
        bid_volume: 買盤總量
        ask_volume: 賣盤總量
        ma5: 5 日均線
        vwap: VWAP
        open_price: 今開
        high_price: 今高
        low_price: 今低
        outside_ratio: 外盤比例 (0-100)
    
    Returns:
        Dict: 進場訊號分析結果
    """
    
    analyzer = OrderBookEntrySignal(
        current_price=current_price,
        ma5=ma5,
        vwap=vwap,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price
    )
    
    result = analyzer.analyze_for_entry(
        bid_volume=bid_volume,
        ask_volume=ask_volume,
        outside_ratio=outside_ratio
    )
    
    result['symbol'] = symbol
    
    return result


# === 測試 ===
if __name__ == "__main__":
    
    print("=" * 60)
    print("案例 1：強力買進（買盤強勢 + 回測 MA5）")
    print("=" * 60)
    
    result = analyze_entry_signal(
        symbol="2337",
        current_price=76.5,
        bid_volume=700,
        ask_volume=400,
        ma5=77.0,
        vwap=76.8,
        open_price=76.0,
        high_price=77.5,
        low_price=75.8,
        outside_ratio=65
    )
    
    print(f"訊號: {result['signal_text']}")
    print(f"信心度: {result['confidence']}%")
    print(f"評分: {result['score']}/100")
    print(f"建議: {result['action']}")
    print(f"停損: ${result['stop_loss']}")
    print(f"停利: ${result['take_profit']}")
    print(f"風報比: 1:{result['risk_reward']}")
    print("\n分析原因:")
    for reason in result['reasons']:
        print(f"  {reason}")
