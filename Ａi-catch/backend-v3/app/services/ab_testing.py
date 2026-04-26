"""
A/B 測試系統
多策略並行測試與比較
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Callable, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class Strategy:
    """策略定義"""
    name: str
    decision_function: Callable
    description: str
    params: Dict


@dataclass
class ABTestResult:
    """A/B 測試結果"""
    strategy_a: str
    strategy_b: str
    
    # 性能指標
    a_total_return: float
    b_total_return: float
    a_win_rate: float
    b_win_rate: float
    a_sharpe: float
    b_sharpe: float
    a_num_trades: int
    b_num_trades: int
    
    # 統計檢驗
    return_p_value: float
    is_significant: bool
    
    # 建議
    recommended_strategy: str
    reason: str


class ABTestingEngine:
    """A/B 測試引擎"""
    
    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
        self.test_results: List[ABTestResult] = []
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """註冊預設策略"""
        
        # 策略 1：保守規則
        def conservative_rules(data, params):
            should_reject = (
                data.get('vwap_deviation', 0) > params['vwap_threshold'] or
                data.get('kd_k', 50) > params['kd_threshold'] or
                data.get('ofi', 0) < params['ofi_threshold']
            )
            return {'should_enter': not should_reject}
        
        self.register_strategy(Strategy(
            name="Conservative",
            decision_function=conservative_rules,
            description="保守規則 (VWAP>20, KD>85, OFI<-50)",
            params={'vwap_threshold': 20, 'kd_threshold': 85, 'ofi_threshold': -50}
        ))
        
        # 策略 2：中等規則
        self.register_strategy(Strategy(
            name="Moderate",
            decision_function=conservative_rules,
            description="中等規則 (VWAP>30, KD>90, OFI<-70)",
            params={'vwap_threshold': 30, 'kd_threshold': 90, 'ofi_threshold': -70}
        ))
        
        # 策略 3：激進規則
        self.register_strategy(Strategy(
            name="Aggressive",
            decision_function=conservative_rules,
            description="激進規則 (VWAP>40, KD>95, OFI<-100)",
            params={'vwap_threshold': 40, 'kd_threshold': 95, 'ofi_threshold': -100}
        ))
    
    def register_strategy(self, strategy: Strategy):
        """註冊策略"""
        self.strategies[strategy.name] = strategy
        logger.info(f"已註冊策略: {strategy.name} - {strategy.description}")
    
    def run_ab_test(self, 
                    strategy_a_name: str,
                    strategy_b_name: str,
                    signals: List[Dict],
                    initial_capital: float = 1000000) -> ABTestResult:
        """運行 A/B 測試"""
        
        if strategy_a_name not in self.strategies:
            raise ValueError(f"策略 {strategy_a_name} 不存在")
        if strategy_b_name not in self.strategies:
            raise ValueError(f"策略 {strategy_b_name} 不存在")
        
        strategy_a = self.strategies[strategy_a_name]
        strategy_b = self.strategies[strategy_b_name]
        
        logger.info(f"開始 A/B 測試: {strategy_a_name} vs {strategy_b_name}")
        
        # 運行兩個策略
        results_a = self._run_strategy(strategy_a, signals, initial_capital)
        results_b = self._run_strategy(strategy_b, signals, initial_capital)
        
        # 統計檢驗
        p_value, is_significant = self._statistical_test(
            results_a['returns'],
            results_b['returns']
        )
        
        # 決定推薦策略
        recommended, reason = self._determine_recommendation(
            strategy_a_name, results_a,
            strategy_b_name, results_b
        )
        
        result = ABTestResult(
            strategy_a=strategy_a_name,
            strategy_b=strategy_b_name,
            a_total_return=results_a['total_return'],
            b_total_return=results_b['total_return'],
            a_win_rate=results_a['win_rate'],
            b_win_rate=results_b['win_rate'],
            a_sharpe=results_a['sharpe_ratio'],
            b_sharpe=results_b['sharpe_ratio'],
            a_num_trades=results_a['num_trades'],
            b_num_trades=results_b['num_trades'],
            return_p_value=p_value,
            is_significant=is_significant,
            recommended_strategy=recommended,
            reason=reason
        )
        
        self.test_results.append(result)
        
        logger.info(f"A/B 測試完成: 推薦 {recommended}")
        
        return result
    
    def _run_strategy(self, 
                     strategy: Strategy, 
                     signals: List[Dict],
                     initial_capital: float) -> Dict:
        """運行單一策略"""
        
        capital = initial_capital
        trades = []
        returns = []
        
        for signal in signals:
            # 重建訊號數據
            signal_data = {
                'stock_code': signal.get('stock_code'),
                'current_price': signal.get('price_at_reject'),
                'vwap': signal.get('vwap'),
                'vwap_deviation': signal.get('vwap_deviation', 0),
                'kd_k': signal.get('kd_k', 50),
                'kd_d': signal.get('kd_d', 50),
                'ofi': signal.get('ofi', 0),
            }
            
            # 策略決策
            decision = strategy.decision_function(signal_data, strategy.params)
            
            # 如果決定進場
            if decision.get('should_enter', False):
                pnl_percent = signal.get('virtual_pnl_percent', 0)
                if pnl_percent is not None:
                    pnl = capital * (pnl_percent / 100)
                    capital += pnl
                    returns.append(pnl_percent)
                    trades.append({'pnl': pnl, 'pnl_percent': pnl_percent})
        
        # 計算統計指標
        if not trades:
            return {
                'total_return': 0,
                'win_rate': 0,
                'sharpe_ratio': 0,
                'num_trades': 0,
                'returns': []
            }
        
        trades_df = pd.DataFrame(trades)
        
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        win_rate = winning_trades / len(trades_df) if len(trades_df) > 0 else 0
        
        total_return = ((capital - initial_capital) / initial_capital) * 100
        
        sharpe_ratio = (
            np.mean(returns) / np.std(returns) * np.sqrt(252)
            if np.std(returns) > 0 else 0
        )
        
        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'num_trades': len(trades),
            'returns': returns
        }
    
    def _statistical_test(self, 
                         returns_a: List[float], 
                         returns_b: List[float]) -> Tuple[float, bool]:
        """統計檢驗（t 檢驗）"""
        
        if len(returns_a) < 2 or len(returns_b) < 2:
            return 1.0, False
        
        try:
            from scipy import stats
            t_stat, p_value = stats.ttest_ind(returns_a, returns_b)
            is_significant = p_value < 0.05
            return float(p_value), is_significant
        except ImportError:
            # 沒有 scipy，使用簡單比較
            mean_diff = abs(np.mean(returns_a) - np.mean(returns_b))
            is_significant = mean_diff > 2.0  # 簡化：差異超過 2% 視為顯著
            return 0.0, is_significant
    
    def _determine_recommendation(self, 
                                 name_a: str, results_a: Dict,
                                 name_b: str, results_b: Dict) -> Tuple[str, str]:
        """決定推薦策略"""
        
        score_a = 0
        score_b = 0
        reasons = []
        
        # 1. 總報酬（權重 30%）
        if results_a['total_return'] > results_b['total_return']:
            score_a += 30
            reasons.append(f"報酬: {name_a} ({results_a['total_return']:.2f}%) > {name_b} ({results_b['total_return']:.2f}%)")
        else:
            score_b += 30
        
        # 2. 夏普比率（權重 30%）
        if results_a['sharpe_ratio'] > results_b['sharpe_ratio']:
            score_a += 30
            reasons.append(f"夏普: {name_a} ({results_a['sharpe_ratio']:.2f}) > {name_b} ({results_b['sharpe_ratio']:.2f})")
        else:
            score_b += 30
        
        # 3. 勝率（權重 20%）
        if results_a['win_rate'] > results_b['win_rate']:
            score_a += 20
        else:
            score_b += 20
        
        # 4. 交易次數（權重 20%，適中為好）
        target_trades = 20  # 假設理想交易次數
        diff_a = abs(results_a['num_trades'] - target_trades)
        diff_b = abs(results_b['num_trades'] - target_trades)
        if diff_a < diff_b:
            score_a += 20
        else:
            score_b += 20
        
        # 決定
        if score_a > score_b:
            recommended = name_a
            reason = " | ".join(reasons[:2]) if reasons else f"{name_a} 綜合評分較高"
        elif score_b > score_a:
            recommended = name_b
            reason = f"{name_b} 綜合評分較高"
        else:
            recommended = 'Tie'
            reason = "兩策略表現相當"
        
        return recommended, reason
    
    def get_strategy_list(self) -> List[Dict]:
        """獲取所有策略列表"""
        return [
            {
                'name': s.name,
                'description': s.description,
                'params': s.params
            }
            for s in self.strategies.values()
        ]
    
    def get_test_results(self) -> List[Dict]:
        """獲取所有測試結果"""
        return [
            {
                'strategy_a': r.strategy_a,
                'strategy_b': r.strategy_b,
                'a_return': r.a_total_return,
                'b_return': r.b_total_return,
                'a_win_rate': r.a_win_rate,
                'b_win_rate': r.b_win_rate,
                'recommended': r.recommended_strategy,
                'reason': r.reason,
                'is_significant': r.is_significant
            }
            for r in self.test_results
        ]


# 全局實例
ab_testing_engine = ABTestingEngine()
