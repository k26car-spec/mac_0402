"""
五檔出場訊號系統 v1.0
目標：讓用戶一眼看出是否該出場

整合到當沖戰情室，提供即時出場建議
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """持倉方向"""
    LONG = "做多"
    SHORT = "做空"
    NONE = "無持倉"


class ExitUrgency(Enum):
    """出場緊急度"""
    CRITICAL = "🔴 立即出場"      # 最高優先級
    HIGH = "🟠 建議出場"          # 高優先級
    MEDIUM = "🟡 考慮出場"        # 中等優先級
    LOW = "🟢 繼續持有"           # 低優先級/不出場


class OrderBookExitSignal:
    """五檔出場訊號分析器"""
    
    def __init__(
        self,
        position_side: PositionSide,
        entry_price: float,
        current_price: float
    ):
        self.position_side = position_side
        self.entry_price = entry_price
        self.current_price = current_price
        
        # 計算盈虧
        if position_side == PositionSide.LONG:
            self.pnl_pct = ((current_price - entry_price) / entry_price) * 100
        elif position_side == PositionSide.SHORT:
            self.pnl_pct = ((entry_price - current_price) / entry_price) * 100
        else:
            self.pnl_pct = 0
    
    def analyze_order_book(
        self,
        bid_volume: int,      # 買盤總量
        ask_volume: int,      # 賣盤總量
        bid_levels: List[Tuple[float, int]] = None,  # 買盤五檔 [(價格, 量), ...]
        ask_levels: List[Tuple[float, int]] = None   # 賣盤五檔 [(價格, 量), ...]
    ) -> Dict:
        """
        分析五檔並生成出場訊號
        
        Returns:
            Dict: {
                'should_exit': bool,
                'urgency': ExitUrgency,
                'urgency_text': str,
                'urgency_level': int,  # 1-4, 4=最緊急
                'reason': str,
                'confidence': int,
                'action': str
            }
        """
        
        # 計算買賣力道
        total_volume = bid_volume + ask_volume
        bid_power = (bid_volume / total_volume * 100) if total_volume > 0 else 50
        ask_power = 100 - bid_power
        
        # 分析結果
        result = {
            'bid_power': round(bid_power, 1),
            'ask_power': round(ask_power, 1),
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'position_side': self.position_side.value,
            'pnl_pct': round(self.pnl_pct, 2),
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'timestamp': datetime.now().isoformat()
        }
        
        # === 根據持倉方向分析 ===
        
        if self.position_side == PositionSide.LONG:
            exit_signal = self._analyze_long_position(
                bid_power, ask_power, bid_volume, ask_volume
            )
        
        elif self.position_side == PositionSide.SHORT:
            exit_signal = self._analyze_short_position(
                bid_power, ask_power, bid_volume, ask_volume
            )
        
        else:
            exit_signal = {
                'should_exit': False,
                'urgency': ExitUrgency.LOW,
                'reason': '無持倉',
                'confidence': 0,
                'action': '無需操作'
            }
        
        # 轉換 urgency 為可序列化格式
        urgency = exit_signal['urgency']
        exit_signal['urgency_text'] = urgency.value
        exit_signal['urgency_level'] = self._urgency_to_level(urgency)
        exit_signal['urgency_color'] = self._urgency_to_color(urgency)
        del exit_signal['urgency']
        
        # 合併結果
        result.update(exit_signal)
        
        return result
    
    def _urgency_to_level(self, urgency: ExitUrgency) -> int:
        """緊急度轉數字（用於排序）"""
        mapping = {
            ExitUrgency.CRITICAL: 4,
            ExitUrgency.HIGH: 3,
            ExitUrgency.MEDIUM: 2,
            ExitUrgency.LOW: 1
        }
        return mapping.get(urgency, 1)
    
    def _urgency_to_color(self, urgency: ExitUrgency) -> str:
        """緊急度轉顏色"""
        mapping = {
            ExitUrgency.CRITICAL: "red",
            ExitUrgency.HIGH: "orange",
            ExitUrgency.MEDIUM: "yellow",
            ExitUrgency.LOW: "green"
        }
        return mapping.get(urgency, "gray")
    
    def _analyze_long_position(
        self,
        bid_power: float,
        ask_power: float,
        bid_volume: int,
        ask_volume: int
    ) -> Dict:
        """分析做多持倉的出場訊號"""
        
        # === 做多出場邏輯 ===
        # 賣壓越大 = 越該出場
        
        # 1. 賣壓壓倒性優勢（賣盤 > 買盤 20%）
        if ask_power > bid_power + 20:
            
            if self.pnl_pct > 0:
                return {
                    'should_exit': True,
                    'urgency': ExitUrgency.HIGH,
                    'reason': f'賣壓沉重（{ask_power:.1f}% vs {bid_power:.1f}%），建議鎖利',
                    'confidence': 85,
                    'action': f'立即掛賣單（獲利 {self.pnl_pct:+.2f}%）'
                }
            else:
                return {
                    'should_exit': True,
                    'urgency': ExitUrgency.CRITICAL,
                    'reason': f'賣壓沉重且虧損（{self.pnl_pct:+.2f}%），趕快止損',
                    'confidence': 90,
                    'action': '市價單立即出場'
                }
        
        # 2. 賣壓稍強（賣盤 > 買盤 10-20%）
        elif ask_power > bid_power + 10:
            
            if self.pnl_pct > 3:
                return {
                    'should_exit': True,
                    'urgency': ExitUrgency.MEDIUM,
                    'reason': f'賣壓增加，已獲利 {self.pnl_pct:+.2f}%',
                    'confidence': 70,
                    'action': '考慮分批出場（先出 50%）'
                }
            elif self.pnl_pct < -1:
                return {
                    'should_exit': True,
                    'urgency': ExitUrgency.HIGH,
                    'reason': f'賣壓增加且虧損（{self.pnl_pct:+.2f}%）',
                    'confidence': 75,
                    'action': '準備停損'
                }
            else:
                return {
                    'should_exit': False,
                    'urgency': ExitUrgency.MEDIUM,
                    'reason': f'賣壓稍強，密切觀察（{self.pnl_pct:+.2f}%）',
                    'confidence': 60,
                    'action': '設好停損，繼續觀察'
                }
        
        # 3. 買賣平衡（±10% 內）
        elif abs(bid_power - ask_power) <= 10:
            
            if self.pnl_pct > 5:
                return {
                    'should_exit': True,
                    'urgency': ExitUrgency.MEDIUM,
                    'reason': f'已獲利 {self.pnl_pct:+.2f}%，多空均衡',
                    'confidence': 65,
                    'action': '可考慮出場一半'
                }
            else:
                return {
                    'should_exit': False,
                    'urgency': ExitUrgency.LOW,
                    'reason': f'多空均衡，繼續持有（{self.pnl_pct:+.2f}%）',
                    'confidence': 50,
                    'action': '維持部位，注意停損'
                }
        
        # 4. 買盤強勢（買盤 > 賣盤）
        else:
            return {
                'should_exit': False,
                'urgency': ExitUrgency.LOW,
                'reason': f'買盤強勢（{bid_power:.1f}% vs {ask_power:.1f}%），繼續持有',
                'confidence': 80,
                'action': f'繼續持有（{self.pnl_pct:+.2f}%），向上移動停損'
            }
    
    def _analyze_short_position(
        self,
        bid_power: float,
        ask_power: float,
        bid_volume: int,
        ask_volume: int
    ) -> Dict:
        """分析做空持倉的出場訊號"""
        
        # === 做空出場邏輯 ===
        # 買盤越強 = 越該出場
        
        # 1. 買盤壓倒性優勢（買盤 > 賣盤 20%）
        if bid_power > ask_power + 20:
            
            if self.pnl_pct > 0:
                return {
                    'should_exit': True,
                    'urgency': ExitUrgency.HIGH,
                    'reason': f'買盤強勢（{bid_power:.1f}% vs {ask_power:.1f}%），建議回補',
                    'confidence': 85,
                    'action': f'立即回補（獲利 {self.pnl_pct:+.2f}%）'
                }
            else:
                return {
                    'should_exit': True,
                    'urgency': ExitUrgency.CRITICAL,
                    'reason': f'買盤強勢且虧損（{self.pnl_pct:+.2f}%），趕快回補',
                    'confidence': 90,
                    'action': '市價單立即回補'
                }
        
        # 2. 買盤稍強（買盤 > 賣盤 10-20%）
        elif bid_power > ask_power + 10:
            
            if self.pnl_pct > 3:
                return {
                    'should_exit': True,
                    'urgency': ExitUrgency.MEDIUM,
                    'reason': f'買盤增加，已獲利 {self.pnl_pct:+.2f}%',
                    'confidence': 70,
                    'action': '考慮分批回補（先回補 50%）'
                }
            elif self.pnl_pct < -1:
                return {
                    'should_exit': True,
                    'urgency': ExitUrgency.HIGH,
                    'reason': f'買盤增加且虧損（{self.pnl_pct:+.2f}%）',
                    'confidence': 75,
                    'action': '準備停損回補'
                }
            else:
                return {
                    'should_exit': False,
                    'urgency': ExitUrgency.MEDIUM,
                    'reason': f'買盤稍強，密切觀察（{self.pnl_pct:+.2f}%）',
                    'confidence': 60,
                    'action': '設好停損，繼續觀察'
                }
        
        # 3. 買賣平衡
        elif abs(bid_power - ask_power) <= 10:
            
            if self.pnl_pct > 5:
                return {
                    'should_exit': True,
                    'urgency': ExitUrgency.MEDIUM,
                    'reason': f'已獲利 {self.pnl_pct:+.2f}%，多空均衡',
                    'confidence': 65,
                    'action': '可考慮回補一半'
                }
            else:
                return {
                    'should_exit': False,
                    'urgency': ExitUrgency.LOW,
                    'reason': f'多空均衡，繼續持有（{self.pnl_pct:+.2f}%）',
                    'confidence': 50,
                    'action': '維持部位，注意停損'
                }
        
        # 4. 賣盤強勢（賣盤 > 買盤）
        else:
            return {
                'should_exit': False,
                'urgency': ExitUrgency.LOW,
                'reason': f'賣盤強勢（{ask_power:.1f}% vs {bid_power:.1f}%），繼續持有',
                'confidence': 80,
                'action': f'繼續持有（{self.pnl_pct:+.2f}%），向下移動停損'
            }
    
    def generate_exit_report(self, order_book_data: Dict) -> str:
        """生成清晰的出場報告"""
        
        signal = self.analyze_order_book(
            bid_volume=order_book_data.get('bid_volume', 0),
            ask_volume=order_book_data.get('ask_volume', 0),
            bid_levels=order_book_data.get('bid_levels', []),
            ask_levels=order_book_data.get('ask_levels', [])
        )
        
        lines = []
        
        lines.append("╔════════════════════════════════════════════════════════╗")
        lines.append("║              即時五檔出場訊號                           ║")
        lines.append("╚════════════════════════════════════════════════════════╝")
        
        lines.append(f"\n📊 持倉狀態")
        lines.append("-" * 60)
        lines.append(f"方向：{signal['position_side']}")
        lines.append(f"進場價：${self.entry_price:.2f}")
        lines.append(f"現價：${self.current_price:.2f}")
        lines.append(f"損益：{signal['pnl_pct']:+.2f}%")
        
        lines.append(f"\n📈 五檔力道")
        lines.append("-" * 60)
        lines.append(f"買盤：{signal['bid_volume']} 張（{signal['bid_power']:.1f}%）")
        lines.append(f"賣盤：{signal['ask_volume']} 張（{signal['ask_power']:.1f}%）")
        
        lines.append(f"\n{signal['urgency_text']}")
        lines.append("=" * 60)
        lines.append(f"原因：{signal['reason']}")
        lines.append(f"建議：{signal['action']}")
        lines.append(f"信心度：{signal['confidence']}%")
        
        urgency_level = signal['urgency_level']
        if urgency_level == 4:
            lines.append("\n⚠️ 極度緊急！立即執行！")
        elif urgency_level == 3:
            lines.append("\n⚠️ 高度建議出場，盡快執行")
        elif urgency_level == 2:
            lines.append("\n⚠️ 考慮出場，做好準備")
        else:
            lines.append("\n✅ 可繼續持有，保持警覺")
        
        return "\n".join(lines)


def analyze_exit_signal(
    symbol: str,
    position_side: str,  # "long" or "short"
    entry_price: float,
    current_price: float,
    bid_volume: int,
    ask_volume: int,
    bid_levels: List = None,
    ask_levels: List = None
) -> Dict:
    """
    便利函數：分析出場訊號
    
    Args:
        symbol: 股票代碼
        position_side: "long" 或 "short"
        entry_price: 進場價
        current_price: 現價
        bid_volume: 買盤總量
        ask_volume: 賣盤總量
    
    Returns:
        Dict: 出場訊號分析結果
    """
    
    # 轉換持倉方向
    if position_side.lower() == "long":
        side = PositionSide.LONG
    elif position_side.lower() == "short":
        side = PositionSide.SHORT
    else:
        side = PositionSide.NONE
    
    analyzer = OrderBookExitSignal(
        position_side=side,
        entry_price=entry_price,
        current_price=current_price
    )
    
    result = analyzer.analyze_order_book(
        bid_volume=bid_volume,
        ask_volume=ask_volume,
        bid_levels=bid_levels or [],
        ask_levels=ask_levels or []
    )
    
    result['symbol'] = symbol
    
    return result


# === 測試 ===
if __name__ == "__main__":
    
    print("=" * 60)
    print("案例 1：做多持倉，買盤較強")
    print("=" * 60)
    
    result = analyze_exit_signal(
        symbol="2337",
        position_side="long",
        entry_price=76.0,
        current_price=77.1,
        bid_volume=554,
        ask_volume=539
    )
    
    print(f"持倉方向: {result['position_side']}")
    print(f"損益: {result['pnl_pct']:+.2f}%")
    print(f"買力: {result['bid_power']}% | 賣力: {result['ask_power']}%")
    print(f"緊急度: {result['urgency_text']}")
    print(f"原因: {result['reason']}")
    print(f"建議: {result['action']}")
    print(f"信心度: {result['confidence']}%")
