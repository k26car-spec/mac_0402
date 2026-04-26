"""
資產配置與風險控制模組 v2.0
動態資產配置、風險控制、投資組合優化

系統名稱：循環驅動多因子投資系統
模組5：資產配置與風險控制模組
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import os
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from scipy import stats
import scipy.optimize as optimize

warnings.filterwarnings('ignore')


class RiskProfile(Enum):
    """風險承受度分類"""
    CONSERVATIVE = "保守型"
    MODERATE = "穩健型"
    AGGRESSIVE = "積極型"


class MarketCondition(Enum):
    """市場狀況分類"""
    BULL = "多頭市場"
    BEAR = "空頭市場"
    SIDEWAYS = "盤整市場"
    RECOVERY = "復甦市場"
    RECESSION = "衰退市場"


@dataclass
class AssetClass:
    """資產類別定義"""
    name: str
    category: str
    tickers: List[str]
    expected_return: float
    volatility: float


@dataclass
class PortfolioAllocation:
    """投資組合配置"""
    asset_class: str
    ticker: str
    allocation: float
    expected_return: float
    risk: float
    description: str
    
    def to_dict(self):
        return asdict(self)


class AssetAllocator:
    """
    資產配置與風險控制管理器
    實現動態資產配置、風險控制、投資組合優化
    """
    
    def __init__(self, risk_profile: str = "MODERATE", 
                 initial_capital: float = 1000000):
        """
        初始化資產配置器
        
        Parameters:
        -----------
        risk_profile : str
            風險承受度 (CONSERVATIVE, MODERATE, AGGRESSIVE)
        initial_capital : float
            初始資金
        """
        self.risk_profile = RiskProfile[risk_profile.upper()]
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.portfolio = {}
        self.historical_data = {}
        self.performance_metrics = {}
        self.rebalancing_history = []
        
        # 資產類別定義
        self.asset_classes = self._define_asset_classes()
        
        # 風險參數配置
        self.risk_parameters = self._define_risk_parameters()
        
        # ETF與債券配置
        self.etf_universe = self._define_etf_universe()
        
        # 市場狀態
        self.market_condition = MarketCondition.SIDEWAYS
        self.last_rebalance_date = None
        
        # 績效追蹤
        self.performance_history = pd.DataFrame()
        self.target_allocation = None
        self.dca_plan = None
        self.rebalancing_suggestions = []
    
    def _define_asset_classes(self) -> Dict[str, AssetClass]:
        """定義資產類別"""
        return {
            "equity_tw": AssetClass(
                name="台股",
                category="equity",
                tickers=["0050.TW", "0056.TW", "006208.TW", "00878.TW"],
                expected_return=0.08,
                volatility=0.18
            ),
            "equity_us": AssetClass(
                name="美股",
                category="equity",
                tickers=["SPY", "QQQ", "VTI", "VOO"],
                expected_return=0.10,
                volatility=0.16
            ),
            "fixed_income": AssetClass(
                name="固定收益",
                category="fixed_income",
                tickers=["TLT", "IEF", "AGG", "BND"],
                expected_return=0.04,
                volatility=0.06
            ),
            "cash": AssetClass(
                name="現金",
                category="cash",
                tickers=["SHY", "BIL"],
                expected_return=0.02,
                volatility=0.01
            ),
            "alternative": AssetClass(
                name="另類投資",
                category="alternative",
                tickers=["GLD", "VNQ", "SLV"],
                expected_return=0.06,
                volatility=0.12
            )
        }
    
    def _define_risk_parameters(self) -> Dict:
        """定義風險參數"""
        return {
            "CONSERVATIVE": {
                "max_drawdown": 0.10,
                "target_return": 0.05,
                "volatility_limit": 0.08,
                "equity_limit": 0.40,
                "bond_min": 0.40,
                "cash_min": 0.10,
                "name": "保守型"
            },
            "MODERATE": {
                "max_drawdown": 0.15,
                "target_return": 0.07,
                "volatility_limit": 0.12,
                "equity_limit": 0.60,
                "bond_min": 0.30,
                "cash_min": 0.05,
                "name": "穩健型"
            },
            "AGGRESSIVE": {
                "max_drawdown": 0.25,
                "target_return": 0.10,
                "volatility_limit": 0.18,
                "equity_limit": 0.80,
                "bond_min": 0.10,
                "cash_min": 0.02,
                "name": "積極型"
            }
        }
    
    def _define_etf_universe(self) -> Dict[str, Dict]:
        """定義ETF與債券投資標的"""
        return {
            # 台股ETF
            "0050.TW": {
                "name": "元大台灣50",
                "asset_class": "equity_tw",
                "category": "index",
                "expense_ratio": 0.0032,
                "description": "台灣50指數ETF，追蹤台灣前50大上市公司"
            },
            "0056.TW": {
                "name": "元大高股息",
                "asset_class": "equity_tw",
                "category": "dividend",
                "expense_ratio": 0.0043,
                "description": "高股息ETF，投資台灣高股息股票"
            },
            "00878.TW": {
                "name": "國泰永續高股息",
                "asset_class": "equity_tw",
                "category": "dividend_esg",
                "expense_ratio": 0.0025,
                "description": "ESG高股息ETF"
            },
            
            # 美股ETF
            "SPY": {
                "name": "SPDR S&P 500 ETF",
                "asset_class": "equity_us",
                "category": "index",
                "expense_ratio": 0.00094,
                "description": "追蹤S&P 500指數"
            },
            "QQQ": {
                "name": "Invesco QQQ Trust",
                "asset_class": "equity_us",
                "category": "tech",
                "expense_ratio": 0.002,
                "description": "追蹤NASDAQ 100指數"
            },
            "VTI": {
                "name": "Vanguard Total Stock Market ETF",
                "asset_class": "equity_us",
                "category": "total_market",
                "expense_ratio": 0.0003,
                "description": "美國全市場股票ETF"
            },
            
            # 債券ETF
            "TLT": {
                "name": "iShares 20+ Year Treasury Bond ETF",
                "asset_class": "fixed_income",
                "category": "long_term_bond",
                "expense_ratio": 0.0015,
                "description": "美國20年以上公債"
            },
            "IEF": {
                "name": "iShares 7-10 Year Treasury Bond ETF",
                "asset_class": "fixed_income",
                "category": "intermediate_bond",
                "expense_ratio": 0.0015,
                "description": "美國7-10年期公債"
            },
            "AGG": {
                "name": "iShares Core U.S. Aggregate Bond ETF",
                "asset_class": "fixed_income",
                "category": "total_bond",
                "expense_ratio": 0.0004,
                "description": "美國綜合債券"
            },
            "BND": {
                "name": "Vanguard Total Bond Market ETF",
                "asset_class": "fixed_income",
                "category": "total_bond",
                "expense_ratio": 0.00035,
                "description": "Vanguard綜合債券ETF"
            },
            
            # 現金與短債
            "SHY": {
                "name": "iShares 1-3 Year Treasury Bond ETF",
                "asset_class": "cash",
                "category": "short_term_bond",
                "expense_ratio": 0.0015,
                "description": "1-3年期公債，近似現金"
            },
            "BIL": {
                "name": "SPDR Bloomberg 1-3 Month T-Bill ETF",
                "asset_class": "cash",
                "category": "t_bill",
                "expense_ratio": 0.0014,
                "description": "1-3個月期國庫券"
            },
            
            # 另類投資
            "GLD": {
                "name": "SPDR Gold Shares",
                "asset_class": "alternative",
                "category": "gold",
                "expense_ratio": 0.004,
                "description": "黃金ETF"
            },
            "VNQ": {
                "name": "Vanguard Real Estate ETF",
                "asset_class": "alternative",
                "category": "reit",
                "expense_ratio": 0.0012,
                "description": "房地產投資信託ETF"
            }
        }
    
    def fetch_market_data(self, tickers: List[str], period: str = "3y") -> pd.DataFrame:
        """獲取市場數據"""
        try:
            print(f"  獲取 {len(tickers)} 個ETF市場數據...", end="")
            
            data = {}
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period=period)
                    
                    if not hist.empty:
                        hist['Returns'] = hist['Close'].pct_change()
                        data[ticker] = hist['Returns'].dropna()
                        self.historical_data[ticker] = hist
                except:
                    pass
            
            if not data:
                print(" 使用模擬數據")
                return self._generate_mock_returns(tickers, period)
            
            returns_df = pd.DataFrame(data)
            print(f" 獲取 {returns_df.shape[1]} 個")
            return returns_df
            
        except Exception as e:
            print(f" 錯誤: {e}")
            return self._generate_mock_returns(tickers, period)
    
    def _generate_mock_returns(self, tickers: List[str], period: str) -> pd.DataFrame:
        """生成模擬報酬率數據"""
        days_map = {"1y": 252, "2y": 504, "3y": 756, "5y": 1260}
        days = days_map.get(period, 756)
        
        dates = pd.date_range(end=datetime.now(), periods=days, freq='B')
        returns_data = {}
        
        for ticker in tickers:
            # 根據資產類別設定參數
            if ticker in ["SPY", "VTI", "0050.TW", "VOO"]:
                annual_return, annual_vol = 0.08, 0.16
            elif ticker in ["QQQ"]:
                annual_return, annual_vol = 0.10, 0.20
            elif ticker in ["TLT", "IEF", "AGG", "BND"]:
                annual_return, annual_vol = 0.04, 0.06
            elif ticker in ["SHY", "BIL"]:
                annual_return, annual_vol = 0.02, 0.01
            elif ticker in ["GLD"]:
                annual_return, annual_vol = 0.05, 0.15
            else:
                annual_return, annual_vol = 0.06, 0.12
            
            daily_return = annual_return / 252
            daily_vol = annual_vol / np.sqrt(252)
            
            np.random.seed(hash(ticker) % 10000)
            returns = np.random.normal(daily_return, daily_vol, days)
            returns_data[ticker] = pd.Series(returns, index=dates)
        
        return pd.DataFrame(returns_data).dropna()
    
    def assess_market_condition(self, returns_df: pd.DataFrame) -> MarketCondition:
        """評估市場狀況"""
        try:
            if returns_df.empty:
                return MarketCondition.SIDEWAYS
            
            market_ticker = "SPY" if "SPY" in returns_df.columns else returns_df.columns[0]
            market_returns = returns_df[market_ticker]
            
            cumulative_return = (1 + market_returns).prod() - 1
            
            window = min(60, len(market_returns))
            recent_returns = market_returns.tail(window)
            x = np.arange(len(recent_returns))
            slope, _, _, _, _ = stats.linregress(x, recent_returns.values)
            
            if cumulative_return > 0.15 and slope > 0:
                return MarketCondition.BULL
            elif cumulative_return < -0.10 and slope < 0:
                return MarketCondition.BEAR
            elif cumulative_return < 0 and slope > 0:
                return MarketCondition.RECOVERY
            elif cumulative_return > 0 and slope < 0:
                return MarketCondition.RECESSION
            else:
                return MarketCondition.SIDEWAYS
                
        except:
            return MarketCondition.SIDEWAYS
    
    def generate_base_allocation(self) -> Dict[str, float]:
        """生成基礎資產配置"""
        if self.risk_profile == RiskProfile.CONSERVATIVE:
            allocation = {
                "equity_tw": 0.10,
                "equity_us": 0.10,
                "fixed_income": 0.50,
                "cash": 0.20,
                "alternative": 0.10
            }
        elif self.risk_profile == RiskProfile.MODERATE:
            allocation = {
                "equity_tw": 0.15,
                "equity_us": 0.25,
                "fixed_income": 0.40,
                "cash": 0.10,
                "alternative": 0.10
            }
        else:  # AGGRESSIVE
            allocation = {
                "equity_tw": 0.20,
                "equity_us": 0.40,
                "fixed_income": 0.25,
                "cash": 0.05,
                "alternative": 0.10
            }
        
        total = sum(allocation.values())
        return {k: v/total for k, v in allocation.items()}
    
    def adjust_allocation_for_market(self, base_allocation: Dict[str, float],
                                    market_condition: MarketCondition) -> Dict[str, float]:
        """根據市場狀況調整配置"""
        adjusted = base_allocation.copy()
        
        adjustments = {
            MarketCondition.BULL: {"equity_tw": 0.10, "equity_us": 0.10, "fixed_income": -0.10, "cash": -0.08, "alternative": -0.02},
            MarketCondition.BEAR: {"equity_tw": -0.10, "equity_us": -0.10, "fixed_income": 0.10, "cash": 0.08, "alternative": 0.02},
            MarketCondition.RECOVERY: {"equity_tw": 0.05, "equity_us": 0.05, "fixed_income": -0.05, "cash": -0.04, "alternative": -0.01},
            MarketCondition.RECESSION: {"equity_tw": -0.05, "equity_us": -0.05, "fixed_income": 0.05, "cash": 0.03, "alternative": 0.02},
            MarketCondition.SIDEWAYS: {"equity_tw": 0, "equity_us": 0, "fixed_income": 0, "cash": 0, "alternative": 0}
        }
        
        adj = adjustments.get(market_condition, {})
        for asset_class in adjusted:
            if asset_class in adj:
                adjusted[asset_class] += adj[asset_class]
        
        adjusted = {k: max(0, v) for k, v in adjusted.items()}
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v/total for k, v in adjusted.items()}
        
        return adjusted
    
    def select_etfs(self, asset_class: str, allocation: float) -> List[PortfolioAllocation]:
        """選擇ETF並分配比例"""
        etf_candidates = [(t, info) for t, info in self.etf_universe.items() 
                         if info["asset_class"] == asset_class]
        
        if not etf_candidates:
            return []
        
        allocations = []
        asset_info = self.asset_classes.get(asset_class)
        
        if asset_class in ["equity_tw", "equity_us"]:
            # 股票類：核心+衛星配置
            if len(etf_candidates) >= 2:
                core = etf_candidates[0]
                allocations.append(PortfolioAllocation(
                    asset_class=asset_class,
                    ticker=core[0],
                    allocation=allocation * 0.6,
                    expected_return=asset_info.expected_return if asset_info else 0.08,
                    risk=asset_info.volatility if asset_info else 0.16,
                    description=f"核心: {core[1]['description']}"
                ))
                
                for t, info in etf_candidates[1:2]:
                    allocations.append(PortfolioAllocation(
                        asset_class=asset_class,
                        ticker=t,
                        allocation=allocation * 0.4,
                        expected_return=(asset_info.expected_return if asset_info else 0.08) * 1.1,
                        risk=(asset_info.volatility if asset_info else 0.16) * 1.2,
                        description=f"衛星: {info['description']}"
                    ))
            else:
                t, info = etf_candidates[0]
                allocations.append(PortfolioAllocation(
                    asset_class=asset_class, ticker=t, allocation=allocation,
                    expected_return=asset_info.expected_return if asset_info else 0.06,
                    risk=asset_info.volatility if asset_info else 0.12,
                    description=info['description']
                ))
                
        elif asset_class == "fixed_income":
            # 債券類：多樣化
            for i, (t, info) in enumerate(etf_candidates[:3]):
                weight = allocation * (0.4 if i == 0 else 0.3)
                allocations.append(PortfolioAllocation(
                    asset_class=asset_class, ticker=t, allocation=weight,
                    expected_return=asset_info.expected_return if asset_info else 0.04,
                    risk=asset_info.volatility if asset_info else 0.06,
                    description=f"債券: {info['description']}"
                ))
        else:
            # 其他類別
            for t, info in etf_candidates[:2]:
                weight = allocation / min(2, len(etf_candidates))
                allocations.append(PortfolioAllocation(
                    asset_class=asset_class, ticker=t, allocation=weight,
                    expected_return=asset_info.expected_return if asset_info else 0.04,
                    risk=asset_info.volatility if asset_info else 0.06,
                    description=info['description']
                ))
        
        return allocations
    
    def generate_portfolio_allocation(self, market_data: pd.DataFrame = None) -> List[PortfolioAllocation]:
        """生成完整的投資組合配置"""
        print("生成投資組合配置...")
        
        if market_data is None:
            all_tickers = []
            for asset_class in self.asset_classes.values():
                all_tickers.extend(asset_class.tickers[:2])
            market_data = self.fetch_market_data(all_tickers, period="3y")
        
        self.market_condition = self.assess_market_condition(market_data)
        print(f"  市場狀況: {self.market_condition.value}")
        
        base_allocation = self.generate_base_allocation()
        adjusted_allocation = self.adjust_allocation_for_market(base_allocation, self.market_condition)
        
        portfolio_allocations = []
        for asset_class, allocation in adjusted_allocation.items():
            if allocation > 0:
                etf_allocations = self.select_etfs(asset_class, allocation)
                portfolio_allocations.extend(etf_allocations)
        
        # 正規化
        total_weight = sum([pa.allocation for pa in portfolio_allocations])
        if total_weight > 0:
            for pa in portfolio_allocations:
                pa.allocation = pa.allocation / total_weight
        
        self.portfolio = {
            "allocations": portfolio_allocations,
            "market_condition": self.market_condition,
            "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self._calculate_portfolio_performance(portfolio_allocations)
        self.target_allocation = portfolio_allocations
        
        return portfolio_allocations
    
    def _calculate_portfolio_performance(self, allocations: List[PortfolioAllocation]):
        """計算投資組合預期績效"""
        total_return = sum(a.allocation * a.expected_return for a in allocations)
        total_risk = np.sqrt(sum((a.allocation * a.risk) ** 2 for a in allocations))
        
        risk_free_rate = 0.02
        sharpe = (total_return - risk_free_rate) / total_risk if total_risk > 0 else 0
        
        self.performance_metrics = {
            "expected_return": total_return,
            "expected_volatility": total_risk,
            "sharpe_ratio": sharpe,
            "risk_free_rate": risk_free_rate,
            "market_condition": self.market_condition.value,
            "risk_profile": self.risk_profile.value
        }
    
    def calculate_risk_metrics(self, portfolio_returns: pd.Series) -> Dict:
        """計算風險指標"""
        if portfolio_returns.empty:
            return {}
        
        annual_return = portfolio_returns.mean() * 252
        annual_vol = portfolio_returns.std() * np.sqrt(252)
        
        risk_free = 0.02
        sharpe = (annual_return - risk_free) / annual_vol if annual_vol > 0 else 0
        
        downside = portfolio_returns[portfolio_returns < 0]
        downside_vol = downside.std() * np.sqrt(252) if len(downside) > 1 else 0
        sortino = (annual_return - risk_free) / downside_vol if downside_vol > 0 else 0
        
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        var_95 = np.percentile(portfolio_returns, 5) * np.sqrt(252)
        cvar_95 = portfolio_returns[portfolio_returns <= np.percentile(portfolio_returns, 5)].mean() * np.sqrt(252)
        
        return {
            "annual_return": annual_return,
            "annual_volatility": annual_vol,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_dd,
            "var_95": var_95,
            "cvar_95": cvar_95,
            "positive_ratio": (portfolio_returns > 0).mean(),
            "worst_day": portfolio_returns.min()
        }
    
    def simulate_portfolio_performance(self, allocations: List[PortfolioAllocation],
                                       period: str = "5y") -> pd.DataFrame:
        """模擬投資組合績效"""
        tickers = [a.ticker for a in allocations]
        weights = [a.allocation for a in allocations]
        
        returns_df = self.fetch_market_data(tickers, period)
        
        if returns_df.empty:
            return pd.DataFrame()
        
        valid_tickers = [t for t in tickers if t in returns_df.columns]
        valid_weights = [weights[tickers.index(t)] for t in valid_tickers]
        
        total = sum(valid_weights)
        if total > 0:
            valid_weights = [w/total for w in valid_weights]
        
        portfolio_returns = returns_df[valid_tickers].dot(valid_weights)
        cumulative = (1 + portfolio_returns).cumprod()
        portfolio_value = self.initial_capital * cumulative
        
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        
        performance_df = pd.DataFrame({
            'Portfolio_Value': portfolio_value,
            'Daily_Return': portfolio_returns,
            'Cumulative_Return': cumulative - 1,
            'Drawdown': drawdown
        }, index=returns_df.index)
        
        risk_metrics = self.calculate_risk_metrics(portfolio_returns)
        
        years = len(performance_df) / 252
        total_return = performance_df['Cumulative_Return'].iloc[-1]
        annualized = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        self.performance_history = performance_df
        self.performance_metrics.update({
            "simulated_annual_return": annualized,
            "simulated_annual_volatility": portfolio_returns.std() * np.sqrt(252),
            "total_return": total_return,
            "final_value": portfolio_value.iloc[-1],
            **risk_metrics
        })
        
        return performance_df
    
    def check_rebalancing_needed(self, current_allocation: List[PortfolioAllocation],
                                 tolerance: float = 0.05) -> Tuple[bool, List[Dict]]:
        """檢查是否需要再平衡"""
        if not self.target_allocation:
            return False, []
        
        current_dict = {pa.ticker: pa.allocation for pa in current_allocation}
        target_dict = {pa.ticker: pa.allocation for pa in self.target_allocation}
        
        adjustments = []
        rebalance_needed = False
        
        for ticker, target in target_dict.items():
            current = current_dict.get(ticker, 0)
            deviation = abs(current - target)
            
            if deviation > tolerance:
                rebalance_needed = True
                adjustment = target - current
                adjustments.append({
                    "ticker": ticker,
                    "current_weight": current,
                    "target_weight": target,
                    "deviation": deviation,
                    "adjustment": adjustment,
                    "action": "買入" if adjustment > 0 else "賣出",
                    "amount": abs(adjustment) * self.current_capital
                })
        
        self.rebalancing_suggestions = adjustments
        return rebalance_needed, adjustments
    
    def create_dca_plan(self, allocations: List[PortfolioAllocation],
                        monthly_investment: float = 30000,
                        investment_period: int = 60) -> Dict:
        """創建定期定額投資計劃"""
        dca_plan = {
            "monthly_investment": monthly_investment,
            "investment_period": investment_period,
            "total_investment": monthly_investment * investment_period,
            "allocations": []
        }
        
        for alloc in allocations:
            monthly_amount = monthly_investment * alloc.allocation
            dca_plan["allocations"].append({
                "ticker": alloc.ticker,
                "allocation_percentage": alloc.allocation,
                "monthly_amount": round(monthly_amount, 2),
                "total_amount": round(monthly_amount * investment_period, 2),
                "description": alloc.description
            })
        
        self.dca_plan = dca_plan
        return dca_plan
    
    def generate_report(self) -> str:
        """生成風險報告"""
        metrics = self.performance_metrics
        params = self.risk_parameters[self.risk_profile.name]
        
        report = f"""
{'='*80}
⚖️ 資產配置與風險控制報告
{'='*80}

【基本資訊】
風險承受度: {self.risk_profile.value}
初始資金: NT${self.initial_capital:,.0f}
市場狀況: {self.market_condition.value}
報告日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'─'*80}
📊 【預期績效】
{'─'*80}

預期年化報酬率: {metrics.get('expected_return', 0)*100:.2f}%
預期年化波動率: {metrics.get('expected_volatility', 0)*100:.2f}%
預期夏普比率: {metrics.get('sharpe_ratio', 0):.2f}
"""
        
        if 'simulated_annual_return' in metrics:
            report += f"""
{'─'*80}
📈 【模擬績效】
{'─'*80}

模擬年化報酬率: {metrics['simulated_annual_return']*100:.2f}%
模擬年化波動率: {metrics['simulated_annual_volatility']*100:.2f}%
夏普比率: {metrics.get('sharpe_ratio', 0):.2f}
索提諾比率: {metrics.get('sortino_ratio', 0):.2f}
總報酬率: {metrics.get('total_return', 0)*100:.2f}%
最大回撤: {abs(metrics.get('max_drawdown', 0))*100:.2f}%
95% VaR: {abs(metrics.get('var_95', 0))*100:.2f}%
正報酬比例: {metrics.get('positive_ratio', 0)*100:.1f}%
最終資產價值: NT${metrics.get('final_value', 0):,.0f}
"""
        
        report += f"""
{'─'*80}
⚠️ 【風險限制】
{'─'*80}

最大允許虧損: {params['max_drawdown']*100:.1f}%
波動率上限: {params['volatility_limit']*100:.1f}%
股票配置上限: {params['equity_limit']*100:.1f}%
債券配置下限: {params['bond_min']*100:.1f}%
現金配置下限: {params['cash_min']*100:.1f}%

{'─'*80}
💼 【投資組合配置】
{'─'*80}
"""
        
        if self.portfolio.get('allocations'):
            for alloc in self.portfolio['allocations']:
                report += f"  • {alloc.ticker}: {alloc.allocation*100:.1f}% (NT${alloc.allocation*self.initial_capital:,.0f})\n"
                report += f"    {alloc.description}\n"
        
        report += f"""
{'─'*80}
💡 【建議】
{'─'*80}

1. 每月檢視投資組合風險指標
2. 每季進行投資組合再平衡
3. 當風險指標超過限制時，立即調整配置
4. 保留足夠的現金以應對市場波動

{'='*80}
"""
        return report
    
    def batch_analyze(self, risk_profiles: List[str] = None) -> List[Dict]:
        """批量分析不同風險偏好"""
        if risk_profiles is None:
            risk_profiles = ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]
        
        results = []
        original_profile = self.risk_profile
        
        for profile in risk_profiles:
            self.risk_profile = RiskProfile[profile]
            allocations = self.generate_portfolio_allocation()
            
            results.append({
                "risk_profile": profile,
                "risk_profile_name": self.risk_profile.value,
                "allocations": [a.to_dict() for a in allocations],
                "performance": self.performance_metrics.copy(),
                "market_condition": self.market_condition.value
            })
        
        self.risk_profile = original_profile
        return results
    
    def to_dict(self) -> Dict:
        """轉換為字典格式"""
        return {
            "risk_profile": self.risk_profile.value,
            "initial_capital": self.initial_capital,
            "market_condition": self.market_condition.value,
            "performance_metrics": self.performance_metrics,
            "allocations": [a.to_dict() for a in self.portfolio.get('allocations', [])],
            "generated_date": datetime.now().isoformat()
        }


def main():
    """主程式"""
    print("=" * 80)
    print("⚖️ 資產配置與風險控制系統 v2.0")
    print("=" * 80)
    
    # 測試三種風險承受度
    profiles = ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]
    
    for profile in profiles:
        print(f"\n{'─'*60}")
        print(f"📊 {RiskProfile[profile].value} 配置分析")
        print(f"{'─'*60}")
        
        allocator = AssetAllocator(risk_profile=profile, initial_capital=1000000)
        allocations = allocator.generate_portfolio_allocation()
        
        print(f"\n投資組合配置:")
        total_equity = 0
        total_bond = 0
        total_cash = 0
        total_alt = 0
        
        for alloc in allocations:
            print(f"  {alloc.ticker}: {alloc.allocation*100:.1f}% (NT${alloc.allocation*1000000:,.0f})")
            if "equity" in alloc.asset_class:
                total_equity += alloc.allocation
            elif "fixed" in alloc.asset_class:
                total_bond += alloc.allocation
            elif "cash" in alloc.asset_class:
                total_cash += alloc.allocation
            else:
                total_alt += alloc.allocation
        
        print(f"\n資產類別總覽:")
        print(f"  股票: {total_equity*100:.1f}%")
        print(f"  債券: {total_bond*100:.1f}%")
        print(f"  現金: {total_cash*100:.1f}%")
        print(f"  另類: {total_alt*100:.1f}%")
        
        print(f"\n預期績效:")
        print(f"  年化報酬: {allocator.performance_metrics['expected_return']*100:.2f}%")
        print(f"  年化波動: {allocator.performance_metrics['expected_volatility']*100:.2f}%")
        print(f"  夏普比率: {allocator.performance_metrics['sharpe_ratio']:.2f}")
    
    # 生成詳細報告
    print("\n" + "=" * 80)
    allocator = AssetAllocator(risk_profile="MODERATE", initial_capital=1000000)
    allocations = allocator.generate_portfolio_allocation()
    
    # 模擬績效
    print("\n模擬投資組合績效...")
    perf = allocator.simulate_portfolio_performance(allocations, period="3y")
    
    if not perf.empty:
        print(f"  最終價值: NT${allocator.performance_metrics.get('final_value', 0):,.0f}")
        print(f"  總報酬率: {allocator.performance_metrics.get('total_return', 0)*100:.1f}%")
        print(f"  最大回撤: {abs(allocator.performance_metrics.get('max_drawdown', 0))*100:.1f}%")
    
    # 生成報告
    report = allocator.generate_report()
    print(report)
    
    # 創建定期定額計劃
    dca = allocator.create_dca_plan(allocations, monthly_investment=30000, investment_period=60)
    print("\n定期定額計劃:")
    print(f"  每月投資: NT${dca['monthly_investment']:,.0f}")
    print(f"  總投資額: NT${dca['total_investment']:,.0f}")
    for a in dca['allocations'][:5]:
        print(f"  {a['ticker']}: 每月 NT${a['monthly_amount']:,.0f}")
    
    print("\n✅ 資產配置分析完成!")
    
    return allocator


if __name__ == "__main__":
    main()
