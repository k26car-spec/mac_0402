"""
被拒絕訊號追蹤系統
用於驗證系統是否過度保守
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
import json


@dataclass
class RejectedSignal:
    """被拒絕的訊號記錄"""
    
    # 基本資訊
    signal_id: str              # 唯一識別碼
    stock_code: str             # 股票代號
    stock_name: str             # 股票名稱
    reject_time: datetime       # 拒絕時間
    
    # 拒絕時的市場狀況
    price_at_reject: float      # 拒絕時價格
    vwap: float                 # VWAP
    vwap_deviation: float       # VWAP 乖離度
    kd_k: float                 # KD K 值
    kd_d: float                 # KD D 值
    ofi: float                  # 大戶資金流
    volume_trend: str           # 成交量趨勢
    price_trend: str            # 價格趨勢
    
    # 拒絕原因
    rejection_reasons: List[str] = field(default_factory=list)
    risk_score: int = 0
    
    # 虛擬進場參數
    virtual_entry_price: float = 0
    virtual_stop_loss: float = 0
    virtual_take_profit: float = 0
    
    # 追蹤數據（後續更新）
    price_after_30min: Optional[float] = None
    price_after_1hour: Optional[float] = None
    price_after_2hour: Optional[float] = None
    highest_price: Optional[float] = None
    lowest_price: Optional[float] = None
    
    # 分析結果
    would_profit: Optional[bool] = None
    would_hit_stop_loss: Optional[bool] = None
    would_hit_take_profit: Optional[bool] = None
    virtual_pnl_percent: Optional[float] = None
    
    # 結論
    decision_quality: Optional[str] = None
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            'signal_id': self.signal_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'reject_time': self.reject_time.isoformat() if self.reject_time else None,
            'price_at_reject': self.price_at_reject,
            'vwap': self.vwap,
            'vwap_deviation': self.vwap_deviation,
            'kd_k': self.kd_k,
            'kd_d': self.kd_d,
            'ofi': self.ofi,
            'volume_trend': self.volume_trend,
            'price_trend': self.price_trend,
            'rejection_reasons': self.rejection_reasons,
            'risk_score': self.risk_score,
            'virtual_entry_price': self.virtual_entry_price,
            'virtual_stop_loss': self.virtual_stop_loss,
            'virtual_take_profit': self.virtual_take_profit,
            'price_after_30min': self.price_after_30min,
            'price_after_1hour': self.price_after_1hour,
            'price_after_2hour': self.price_after_2hour,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price,
            'would_profit': self.would_profit,
            'would_hit_stop_loss': self.would_hit_stop_loss,
            'would_hit_take_profit': self.would_hit_take_profit,
            'virtual_pnl_percent': self.virtual_pnl_percent,
            'decision_quality': self.decision_quality
        }


@dataclass
class TrackingSnapshot:
    """追蹤快照"""
    timestamp: datetime
    price: float
    volume: int = 0
    ofi: float = 0
