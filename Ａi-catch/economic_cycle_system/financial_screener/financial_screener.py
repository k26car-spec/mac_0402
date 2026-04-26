"""
財報與營收量化篩選模組 v2.0
使用三大關鍵數字快速篩選優質公司

系統名稱：循環驅動多因子投資系統
模組3：財報與營收量化篩選模組
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import os
import json
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

# 設定中文字體
try:
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Microsoft JhengHei', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass


class FinancialScreener:
    """
    財報與營收量化篩選器
    專注於三大關鍵數字：毛利率、營收年增率、自由現金流
    """
    
    def __init__(self, market: str = "TW"):
        """
        初始化篩選器
        
        Parameters:
        -----------
        market : str
            市場代號: "TW"(台灣), "US"(美國)
        """
        self.market = market
        self.screened_companies = []
        self.financial_data = {}
        self.scoring_results = {}
        self.last_update = None
        
        # 三大關鍵數字的權重設定
        self.key_metrics_weights = {
            "gross_margin": {
                "weight": 0.35,
                "min_threshold": 0.20,
                "preferred_range": (0.30, 0.60)
            },
            "revenue_growth": {
                "weight": 0.35,
                "min_threshold": 0.05,
                "preferred_range": (0.10, 0.50)
            },
            "free_cash_flow": {
                "weight": 0.30,
                "min_threshold": 0,
                "preferred_range": (0.05, 0.30)
            }
        }
        
        # 輔助財務指標
        self.supporting_metrics = {
            "roe": {"weight": 0.15, "min": 0.10},
            "current_ratio": {"weight": 0.10, "min": 1.5},
            "debt_to_equity": {"weight": 0.10, "max": 0.8},
            "r_d_intensity": {"weight": 0.05, "min": 0.03},
            "dividend_yield": {"weight": 0.05, "min": 0.02},
            "operating_margin": {"weight": 0.15, "min": 0.08}
        }
        
        # 評分等級定義
        self.rating_scale = {
            "A+": (90, 100, "極優質，強烈推薦"),
            "A": (80, 90, "優質，推薦買入"),
            "B+": (70, 80, "良好，值得關注"),
            "B": (60, 70, "中等，可考慮"),
            "C": (50, 60, "普通，需謹慎"),
            "D": (40, 50, "偏弱，不建議"),
            "F": (0, 40, "不佳，避開")
        }
        
        # 股票池
        self.stock_universes = self._load_stock_universes()
        
        # 公司財務數據估計值
        self.company_estimates = self._load_company_estimates()
    
    def _load_stock_universes(self) -> Dict:
        """載入股票池"""
        if self.market == "TW":
            return {
                "large_cap": [
                    "2330", "2454", "2317", "2308", "2303",
                    "2882", "2881", "2886", "2891", "2884",
                    "2412", "1301", "1303", "1326", "1402",
                    "2002", "1101", "1102", "1216", "2912",
                    "3711", "2357", "2382", "3008", "2379"
                ],
                "mid_cap": [
                    "3034", "2379", "2382", "3231", "2356",
                    "2324", "4938", "3008", "6415", "5274",
                    "3661", "3443", "3105", "6488", "2408",
                    "6239", "2449", "3017", "3324", "6669"
                ],
                "dividend": [
                    "2412", "2882", "2881", "2886", "2891",
                    "2884", "2880", "2892", "5880", "2801",
                    "1216", "2002", "1301", "1102", "9904"
                ],
                "ai_server": [
                    "2382", "3231", "6669", "2356", "2317",
                    "2308", "2301", "3017", "3324", "3711"
                ]
            }
        else:
            return {
                "tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META",
                        "NVDA", "TSLA", "AVGO", "ADBE", "CRM"],
                "finance": ["JPM", "BAC", "WFC", "GS", "MS"],
                "healthcare": ["JNJ", "PFE", "ABT", "MRK", "LLY"]
            }
    
    def _load_company_estimates(self) -> Dict:
        """載入公司財務數據估計值"""
        return {
            # 半導體龍頭
            "2330": {"gross_margin": 0.558, "roe": 0.28, "revenue_growth": 0.25, "fcf_margin": 0.25, "current_ratio": 2.5, "debt_to_equity": 0.12, "operating_margin": 0.45, "r_d_intensity": 0.08, "dividend_yield": 0.015},
            "2454": {"gross_margin": 0.485, "roe": 0.22, "revenue_growth": 0.18, "fcf_margin": 0.20, "current_ratio": 2.2, "debt_to_equity": 0.25, "operating_margin": 0.35, "r_d_intensity": 0.18, "dividend_yield": 0.025},
            "2303": {"gross_margin": 0.35, "roe": 0.12, "revenue_growth": 0.10, "fcf_margin": 0.15, "current_ratio": 2.0, "debt_to_equity": 0.35, "operating_margin": 0.22, "r_d_intensity": 0.05, "dividend_yield": 0.04},
            
            # IC設計
            "3034": {"gross_margin": 0.42, "roe": 0.18, "revenue_growth": 0.12, "fcf_margin": 0.18, "current_ratio": 2.3, "debt_to_equity": 0.20, "operating_margin": 0.28, "r_d_intensity": 0.15, "dividend_yield": 0.03},
            "2379": {"gross_margin": 0.48, "roe": 0.20, "revenue_growth": 0.15, "fcf_margin": 0.20, "current_ratio": 2.5, "debt_to_equity": 0.15, "operating_margin": 0.30, "r_d_intensity": 0.16, "dividend_yield": 0.025},
            "5274": {"gross_margin": 0.52, "roe": 0.25, "revenue_growth": 0.22, "fcf_margin": 0.25, "current_ratio": 3.0, "debt_to_equity": 0.10, "operating_margin": 0.40, "r_d_intensity": 0.20, "dividend_yield": 0.015},
            "6415": {"gross_margin": 0.55, "roe": 0.28, "revenue_growth": 0.20, "fcf_margin": 0.22, "current_ratio": 2.8, "debt_to_equity": 0.12, "operating_margin": 0.38, "r_d_intensity": 0.18, "dividend_yield": 0.02},
            
            # AI伺服器
            "2382": {"gross_margin": 0.055, "roe": 0.12, "revenue_growth": 0.35, "fcf_margin": 0.08, "current_ratio": 1.5, "debt_to_equity": 0.45, "operating_margin": 0.04, "r_d_intensity": 0.02, "dividend_yield": 0.025},
            "3231": {"gross_margin": 0.05, "roe": 0.15, "revenue_growth": 0.40, "fcf_margin": 0.06, "current_ratio": 1.4, "debt_to_equity": 0.50, "operating_margin": 0.035, "r_d_intensity": 0.02, "dividend_yield": 0.02},
            "6669": {"gross_margin": 0.08, "roe": 0.35, "revenue_growth": 0.45, "fcf_margin": 0.10, "current_ratio": 1.8, "debt_to_equity": 0.30, "operating_margin": 0.06, "r_d_intensity": 0.03, "dividend_yield": 0.01},
            "2356": {"gross_margin": 0.045, "roe": 0.08, "revenue_growth": 0.25, "fcf_margin": 0.05, "current_ratio": 1.3, "debt_to_equity": 0.55, "operating_margin": 0.03, "r_d_intensity": 0.015, "dividend_yield": 0.035},
            
            # 電子代工
            "2317": {"gross_margin": 0.06, "roe": 0.08, "revenue_growth": 0.15, "fcf_margin": 0.05, "current_ratio": 1.4, "debt_to_equity": 0.50, "operating_margin": 0.03, "r_d_intensity": 0.02, "dividend_yield": 0.04},
            "4938": {"gross_margin": 0.045, "roe": 0.06, "revenue_growth": 0.08, "fcf_margin": 0.04, "current_ratio": 1.3, "debt_to_equity": 0.60, "operating_margin": 0.025, "r_d_intensity": 0.01, "dividend_yield": 0.05},
            "2324": {"gross_margin": 0.04, "roe": 0.05, "revenue_growth": 0.05, "fcf_margin": 0.03, "current_ratio": 1.2, "debt_to_equity": 0.65, "operating_margin": 0.02, "r_d_intensity": 0.01, "dividend_yield": 0.055},
            
            # 封測
            "3711": {"gross_margin": 0.22, "roe": 0.12, "revenue_growth": 0.12, "fcf_margin": 0.12, "current_ratio": 1.8, "debt_to_equity": 0.40, "operating_margin": 0.15, "r_d_intensity": 0.04, "dividend_yield": 0.04},
            "6239": {"gross_margin": 0.20, "roe": 0.10, "revenue_growth": 0.08, "fcf_margin": 0.10, "current_ratio": 1.6, "debt_to_equity": 0.45, "operating_margin": 0.12, "r_d_intensity": 0.03, "dividend_yield": 0.045},
            "2449": {"gross_margin": 0.25, "roe": 0.15, "revenue_growth": 0.10, "fcf_margin": 0.12, "current_ratio": 1.8, "debt_to_equity": 0.35, "operating_margin": 0.18, "r_d_intensity": 0.04, "dividend_yield": 0.035},
            
            # 電源/散熱
            "2308": {"gross_margin": 0.28, "roe": 0.18, "revenue_growth": 0.15, "fcf_margin": 0.15, "current_ratio": 2.0, "debt_to_equity": 0.25, "operating_margin": 0.12, "r_d_intensity": 0.08, "dividend_yield": 0.035},
            "2301": {"gross_margin": 0.18, "roe": 0.10, "revenue_growth": 0.08, "fcf_margin": 0.10, "current_ratio": 1.6, "debt_to_equity": 0.40, "operating_margin": 0.08, "r_d_intensity": 0.04, "dividend_yield": 0.05},
            "3017": {"gross_margin": 0.28, "roe": 0.25, "revenue_growth": 0.30, "fcf_margin": 0.18, "current_ratio": 2.2, "debt_to_equity": 0.20, "operating_margin": 0.20, "r_d_intensity": 0.05, "dividend_yield": 0.02},
            "3324": {"gross_margin": 0.25, "roe": 0.20, "revenue_growth": 0.25, "fcf_margin": 0.15, "current_ratio": 2.0, "debt_to_equity": 0.25, "operating_margin": 0.18, "r_d_intensity": 0.04, "dividend_yield": 0.025},
            
            # 金融
            "2882": {"gross_margin": 0.55, "roe": 0.12, "revenue_growth": 0.08, "fcf_margin": 0.20, "current_ratio": 1.2, "debt_to_equity": 0.15, "operating_margin": 0.35, "r_d_intensity": 0.01, "dividend_yield": 0.04},
            "2881": {"gross_margin": 0.52, "roe": 0.10, "revenue_growth": 0.06, "fcf_margin": 0.18, "current_ratio": 1.2, "debt_to_equity": 0.18, "operating_margin": 0.32, "r_d_intensity": 0.01, "dividend_yield": 0.045},
            "2886": {"gross_margin": 0.50, "roe": 0.10, "revenue_growth": 0.05, "fcf_margin": 0.15, "current_ratio": 1.3, "debt_to_equity": 0.20, "operating_margin": 0.30, "r_d_intensity": 0.01, "dividend_yield": 0.05},
            "2891": {"gross_margin": 0.48, "roe": 0.09, "revenue_growth": 0.04, "fcf_margin": 0.12, "current_ratio": 1.2, "debt_to_equity": 0.22, "operating_margin": 0.28, "r_d_intensity": 0.01, "dividend_yield": 0.055},
            "2884": {"gross_margin": 0.45, "roe": 0.08, "revenue_growth": 0.03, "fcf_margin": 0.10, "current_ratio": 1.2, "debt_to_equity": 0.25, "operating_margin": 0.25, "r_d_intensity": 0.01, "dividend_yield": 0.05},
            
            # 傳產/消費
            "1216": {"gross_margin": 0.32, "roe": 0.12, "revenue_growth": 0.05, "fcf_margin": 0.12, "current_ratio": 1.8, "debt_to_equity": 0.30, "operating_margin": 0.08, "r_d_intensity": 0.02, "dividend_yield": 0.03},
            "2912": {"gross_margin": 0.35, "roe": 0.25, "revenue_growth": 0.08, "fcf_margin": 0.15, "current_ratio": 1.5, "debt_to_equity": 0.35, "operating_margin": 0.10, "r_d_intensity": 0.01, "dividend_yield": 0.025},
            "9904": {"gross_margin": 0.28, "roe": 0.10, "revenue_growth": 0.03, "fcf_margin": 0.08, "current_ratio": 1.6, "debt_to_equity": 0.40, "operating_margin": 0.06, "r_d_intensity": 0.02, "dividend_yield": 0.055},
            
            # 電信
            "2412": {"gross_margin": 0.35, "roe": 0.10, "revenue_growth": 0.02, "fcf_margin": 0.20, "current_ratio": 1.0, "debt_to_equity": 0.50, "operating_margin": 0.18, "r_d_intensity": 0.03, "dividend_yield": 0.045},
            
            # 光學
            "3008": {"gross_margin": 0.60, "roe": 0.15, "revenue_growth": 0.05, "fcf_margin": 0.30, "current_ratio": 4.0, "debt_to_equity": 0.05, "operating_margin": 0.50, "r_d_intensity": 0.12, "dividend_yield": 0.015},
            
            # 材料
            "6488": {"gross_margin": 0.45, "roe": 0.18, "revenue_growth": 0.12, "fcf_margin": 0.20, "current_ratio": 2.5, "debt_to_equity": 0.20, "operating_margin": 0.30, "r_d_intensity": 0.06, "dividend_yield": 0.02},
            "2408": {"gross_margin": 0.30, "roe": 0.08, "revenue_growth": 0.15, "fcf_margin": 0.10, "current_ratio": 1.5, "debt_to_equity": 0.45, "operating_margin": 0.15, "r_d_intensity": 0.08, "dividend_yield": 0.02},
        }
    
    def fetch_financial_data(self, ticker: str) -> Dict:
        """獲取公司財務數據"""
        try:
            # 優先使用估計數據
            if ticker in self.company_estimates:
                estimates = self.company_estimates[ticker]
                
                # 嘗試獲取真實價格
                try:
                    yf_ticker = f"{ticker}.TW" if self.market == "TW" else ticker
                    stock = yf.Ticker(yf_ticker)
                    hist = stock.history(period="1y")
                    info = stock.info
                    
                    current_price = hist["Close"].iloc[-1] if not hist.empty else 0
                    price_52w_high = hist["High"].max() if not hist.empty else 0
                    price_52w_low = hist["Low"].min() if not hist.empty else 0
                    market_cap = info.get("marketCap", 0)
                    name = info.get("longName", ticker)
                    sector = info.get("sector", "科技")
                    industry = info.get("industry", "半導體")
                except:
                    current_price = 0
                    price_52w_high = 0
                    price_52w_low = 0
                    market_cap = 0
                    name = f"公司_{ticker}"
                    sector = "科技"
                    industry = "半導體"
                
                company_data = {
                    "ticker": ticker,
                    "name": name,
                    "sector": sector,
                    "industry": industry,
                    "market_cap": market_cap,
                    "gross_margin": estimates.get("gross_margin", 0.25),
                    "revenue_growth": estimates.get("revenue_growth", 0.10),
                    "free_cash_flow_margin": estimates.get("fcf_margin", 0.10),
                    "roe": estimates.get("roe", 0.12),
                    "current_ratio": estimates.get("current_ratio", 1.5),
                    "debt_to_equity": estimates.get("debt_to_equity", 0.40),
                    "operating_margin": estimates.get("operating_margin", 0.10),
                    "r_d_intensity": estimates.get("r_d_intensity", 0.05),
                    "dividend_yield": estimates.get("dividend_yield", 0.03),
                    "current_price": current_price,
                    "price_52w_high": price_52w_high,
                    "price_52w_low": price_52w_low,
                    "price_position": 0,
                    "data_quality": "good",
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "data_source": "estimates+yfinance"
                }
                
                # 計算價格位置
                if price_52w_high > price_52w_low and price_52w_low > 0:
                    company_data["price_position"] = (current_price - price_52w_low) / (price_52w_high - price_52w_low)
                
                self.financial_data[ticker] = company_data
                return company_data
            
            # 沒有估計數據時使用 yfinance
            return self._fetch_from_yfinance(ticker)
            
        except Exception as e:
            print(f"  ⚠️ 獲取 {ticker} 數據錯誤: {e}")
            return self._get_demo_data(ticker)
    
    def _fetch_from_yfinance(self, ticker: str) -> Dict:
        """從 yfinance 獲取數據"""
        try:
            yf_ticker = f"{ticker}.TW" if self.market == "TW" else ticker
            stock = yf.Ticker(yf_ticker)
            info = stock.info
            hist = stock.history(period="1y")
            
            company_data = {
                "ticker": ticker,
                "name": info.get("longName", ticker),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "market_cap": info.get("marketCap", 0),
                "gross_margin": info.get("grossMargins", 0) or 0.20,
                "revenue_growth": info.get("revenueGrowth", 0) or 0.05,
                "free_cash_flow_margin": 0.10,
                "roe": info.get("returnOnEquity", 0) or 0.10,
                "current_ratio": info.get("currentRatio", 0) or 1.5,
                "debt_to_equity": (info.get("debtToEquity", 0) or 50) / 100,
                "operating_margin": info.get("operatingMargins", 0) or 0.08,
                "r_d_intensity": 0.05,
                "dividend_yield": info.get("dividendYield", 0) or 0.02,
                "current_price": hist["Close"].iloc[-1] if not hist.empty else 0,
                "price_52w_high": hist["High"].max() if not hist.empty else 0,
                "price_52w_low": hist["Low"].min() if not hist.empty else 0,
                "price_position": 0,
                "data_quality": "good",
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_source": "yfinance"
            }
            
            if company_data["price_52w_high"] > company_data["price_52w_low"]:
                company_data["price_position"] = (
                    (company_data["current_price"] - company_data["price_52w_low"]) /
                    (company_data["price_52w_high"] - company_data["price_52w_low"])
                )
            
            self.financial_data[ticker] = company_data
            return company_data
            
        except Exception as e:
            return self._get_demo_data(ticker)
    
    def _get_demo_data(self, ticker: str) -> Dict:
        """生成演示數據"""
        np.random.seed(hash(ticker) % 10000)
        
        return {
            "ticker": ticker,
            "name": f"公司_{ticker}",
            "sector": "科技",
            "industry": "半導體",
            "market_cap": np.random.uniform(100, 5000) * 1e8,
            "gross_margin": np.random.uniform(0.20, 0.50),
            "revenue_growth": np.random.uniform(-0.05, 0.30),
            "free_cash_flow_margin": np.random.uniform(0.05, 0.25),
            "roe": np.random.uniform(0.08, 0.25),
            "current_ratio": np.random.uniform(1.2, 3.0),
            "debt_to_equity": np.random.uniform(0.15, 0.60),
            "operating_margin": np.random.uniform(0.05, 0.30),
            "r_d_intensity": np.random.uniform(0.02, 0.15),
            "dividend_yield": np.random.uniform(0.01, 0.06),
            "current_price": np.random.uniform(50, 500),
            "price_52w_high": np.random.uniform(300, 600),
            "price_52w_low": np.random.uniform(40, 200),
            "price_position": np.random.uniform(0.3, 0.8),
            "data_quality": "demo",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_source": "demo"
        }
    
    def calculate_financial_score(self, company_data: Dict) -> Tuple[float, Dict]:
        """
        計算財務健康分數 (0-100)
        """
        score_details = {}
        
        try:
            # === 1. 三大關鍵數字評分 (70%) ===
            key_metrics_score = 0
            
            # 毛利率評分 (35%)
            gm = company_data.get("gross_margin", 0)
            gm_config = self.key_metrics_weights["gross_margin"]
            
            if gm < gm_config["min_threshold"]:
                gm_score = max(0, gm / gm_config["min_threshold"] * 50)
            elif gm_config["preferred_range"][0] <= gm <= gm_config["preferred_range"][1]:
                gm_score = 100
            elif gm < gm_config["preferred_range"][0]:
                gm_score = 50 + (gm - gm_config["min_threshold"]) / (gm_config["preferred_range"][0] - gm_config["min_threshold"]) * 50
            else:
                gm_score = max(70, 100 - (gm - gm_config["preferred_range"][1]) * 100)
            
            score_details["gross_margin"] = {"value": gm, "score": round(gm_score, 1)}
            key_metrics_score += gm_score * gm_config["weight"]
            
            # 營收成長率評分 (35%)
            rg = company_data.get("revenue_growth", 0)
            rg_config = self.key_metrics_weights["revenue_growth"]
            
            if rg < 0:
                rg_score = max(0, 30 + rg * 100)
            elif rg < rg_config["min_threshold"]:
                rg_score = 30 + rg / rg_config["min_threshold"] * 30
            elif rg_config["preferred_range"][0] <= rg <= rg_config["preferred_range"][1]:
                rg_score = 100
            elif rg < rg_config["preferred_range"][0]:
                rg_score = 60 + (rg - rg_config["min_threshold"]) / (rg_config["preferred_range"][0] - rg_config["min_threshold"]) * 40
            else:
                rg_score = max(80, 100 - (rg - rg_config["preferred_range"][1]) * 50)
            
            score_details["revenue_growth"] = {"value": rg, "score": round(rg_score, 1)}
            key_metrics_score += rg_score * rg_config["weight"]
            
            # 自由現金流評分 (30%)
            fcf = company_data.get("free_cash_flow_margin", 0)
            fcf_config = self.key_metrics_weights["free_cash_flow"]
            
            if fcf <= 0:
                fcf_score = max(0, 20 + fcf * 200)
            elif fcf_config["preferred_range"][0] <= fcf <= fcf_config["preferred_range"][1]:
                fcf_score = 100
            elif fcf < fcf_config["preferred_range"][0]:
                fcf_score = 50 + fcf / fcf_config["preferred_range"][0] * 50
            else:
                fcf_score = max(80, 100 - (fcf - fcf_config["preferred_range"][1]) * 100)
            
            score_details["free_cash_flow"] = {"value": fcf, "score": round(fcf_score, 1)}
            key_metrics_score += fcf_score * fcf_config["weight"]
            
            # 標準化為 70 分
            key_metrics_normalized = key_metrics_score * 0.7
            
            # === 2. 輔助指標評分 (30%) ===
            supporting_score = 0
            
            # ROE
            roe = company_data.get("roe", 0)
            roe_score = min(100, max(0, roe * 400)) if roe >= 0.10 else max(0, roe * 500)
            score_details["roe"] = {"value": roe, "score": round(roe_score, 1)}
            supporting_score += roe_score * self.supporting_metrics["roe"]["weight"]
            
            # 流動比率
            cr = company_data.get("current_ratio", 1.0)
            cr_score = 100 if cr >= 1.5 else max(0, cr / 1.5 * 100)
            score_details["current_ratio"] = {"value": cr, "score": round(cr_score, 1)}
            supporting_score += cr_score * self.supporting_metrics["current_ratio"]["weight"]
            
            # 負債比率
            de = company_data.get("debt_to_equity", 0.5)
            de_score = 100 if de <= 0.5 else max(0, 100 - (de - 0.5) * 200)
            score_details["debt_to_equity"] = {"value": de, "score": round(de_score, 1)}
            supporting_score += de_score * self.supporting_metrics["debt_to_equity"]["weight"]
            
            # 營業利益率
            om = company_data.get("operating_margin", 0)
            om_score = min(100, max(0, om * 500)) if om >= 0.08 else max(0, om * 600)
            score_details["operating_margin"] = {"value": om, "score": round(om_score, 1)}
            supporting_score += om_score * self.supporting_metrics["operating_margin"]["weight"]
            
            # 研發強度
            rdi = company_data.get("r_d_intensity", 0)
            rdi_score = min(100, rdi * 500) if rdi >= 0.03 else rdi * 1000
            score_details["r_d_intensity"] = {"value": rdi, "score": round(rdi_score, 1)}
            supporting_score += rdi_score * self.supporting_metrics["r_d_intensity"]["weight"]
            
            # 股息殖利率
            dy = company_data.get("dividend_yield", 0)
            dy_score = min(100, dy * 2000) if dy >= 0.02 else dy * 2500
            score_details["dividend_yield"] = {"value": dy, "score": round(dy_score, 1)}
            supporting_score += dy_score * self.supporting_metrics["dividend_yield"]["weight"]
            
            # 標準化為 30 分
            supporting_normalized = supporting_score * 0.3
            
            # === 3. 總分計算 ===
            total_score = key_metrics_normalized + supporting_normalized
            
            # 數據品質調整
            quality = company_data.get("data_quality", "good")
            quality_multiplier = {"excellent": 1.0, "good": 0.98, "fair": 0.90, "demo": 0.85}.get(quality, 0.90)
            total_score *= quality_multiplier
            
            total_score = max(0, min(100, total_score))
            
            score_details["total"] = round(total_score, 1)
            score_details["key_metrics"] = round(key_metrics_normalized, 1)
            score_details["supporting"] = round(supporting_normalized, 1)
            
            return total_score, score_details
            
        except Exception as e:
            print(f"計算分數錯誤: {e}")
            return 50.0, {"error": str(e)}
    
    def get_rating(self, score: float) -> Tuple[str, str]:
        """根據分數獲取評級"""
        for rating, (low, high, desc) in self.rating_scale.items():
            if low <= score < high:
                return rating, desc
        return "F", "不佳，避開"
    
    def screen_companies(self, 
                         universe_type: str = "large_cap",
                         min_score: float = 60,
                         use_real_data: bool = True,
                         max_companies: int = 30) -> List[Dict]:
        """
        篩選符合條件的公司
        """
        print(f"\n📊 開始篩選 {universe_type} 股票池...")
        print("=" * 60)
        
        if universe_type not in self.stock_universes:
            print(f"❌ 股票池 {universe_type} 不存在")
            return []
        
        tickers = self.stock_universes[universe_type][:max_companies]
        screened_results = []
        
        for i, ticker in enumerate(tickers):
            print(f"  處理 {i+1}/{len(tickers)}: {ticker}", end="")
            
            try:
                company_data = self.fetch_financial_data(ticker)
                score, score_details = self.calculate_financial_score(company_data)
                rating, rating_desc = self.get_rating(score)
                
                result = {
                    "rank": 0,
                    "ticker": ticker,
                    "name": company_data.get("name", ticker),
                    "sector": company_data.get("sector", "N/A"),
                    "industry": company_data.get("industry", "N/A"),
                    "score": round(score, 1),
                    "rating": rating,
                    "rating_description": rating_desc,
                    
                    # 三大關鍵數字
                    "gross_margin": round(company_data.get("gross_margin", 0) * 100, 1),
                    "revenue_growth": round(company_data.get("revenue_growth", 0) * 100, 1),
                    "free_cash_flow_margin": round(company_data.get("free_cash_flow_margin", 0) * 100, 1),
                    
                    # 輔助指標
                    "roe": round(company_data.get("roe", 0) * 100, 1),
                    "current_ratio": round(company_data.get("current_ratio", 0), 2),
                    "debt_to_equity": round(company_data.get("debt_to_equity", 0) * 100, 1),
                    "operating_margin": round(company_data.get("operating_margin", 0) * 100, 1),
                    "dividend_yield": round(company_data.get("dividend_yield", 0) * 100, 2),
                    
                    # 價格
                    "current_price": round(company_data.get("current_price", 0), 2),
                    "price_position": round(company_data.get("price_position", 0) * 100, 1),
                    
                    "score_details": score_details,
                    "data_quality": company_data.get("data_quality", "unknown")
                }
                
                if score >= min_score:
                    screened_results.append(result)
                    print(f" ✅ {score:.1f}分 ({rating})")
                else:
                    print(f" ⏭️ {score:.1f}分 (低於門檻)")
                
                self.scoring_results[ticker] = result
                
            except Exception as e:
                print(f" ❌ 錯誤: {e}")
                continue
        
        # 排序
        screened_results.sort(key=lambda x: x["score"], reverse=True)
        for i, result in enumerate(screened_results):
            result["rank"] = i + 1
        
        self.screened_companies = screened_results
        self.last_update = datetime.now()
        
        print("\n" + "=" * 60)
        print(f"✅ 篩選完成！找到 {len(screened_results)} 家符合條件的公司")
        
        return screened_results
    
    def generate_report(self) -> str:
        """生成篩選報告"""
        if not self.screened_companies:
            return "請先執行 screen_companies() 方法"
        
        report = f"""
{'='*90}
📊 財報與營收量化篩選報告
{'='*90}

📋 市場: {self.market}
📅 篩選時間: {self.last_update.strftime('%Y-%m-%d %H:%M:%S') if self.last_update else 'N/A'}
📈 篩選公司數: {len(self.screened_companies)}

{'─'*90}
🏆 【頂級評級公司 (A/A+級)】
{'─'*90}
"""
        
        top_companies = [c for c in self.screened_companies if c["rating"] in ["A", "A+"]]
        
        for company in top_companies[:10]:
            report += f"\n{company['rank']:2d}. {company['ticker']} - {company['name'][:15]}"
            report += f"\n    評級: {company['rating']} ({company['score']:.1f}分)"
            report += f" | 毛利率: {company['gross_margin']:.1f}%"
            report += f" | 營收成長: {company['revenue_growth']:+.1f}%"
            report += f" | ROE: {company['roe']:.1f}%"
            report += f"\n"
        
        # 統計
        if self.screened_companies:
            gm_values = [c["gross_margin"] for c in self.screened_companies]
            rg_values = [c["revenue_growth"] for c in self.screened_companies]
            score_values = [c["score"] for c in self.screened_companies]
            
            report += f"""
{'─'*90}
📈 【三大關鍵數字統計】
{'─'*90}

平均毛利率: {np.mean(gm_values):.1f}%
平均營收成長率: {np.mean(rg_values):.1f}%
平均財務分數: {np.mean(score_values):.1f}
最高分數: {np.max(score_values):.1f}
最低分數: {np.min(score_values):.1f}
"""
        
        # 評級分布
        report += f"""
{'─'*90}
📊 【評級分布】
{'─'*90}
"""
        
        rating_counts = {}
        for c in self.screened_companies:
            rating_counts[c["rating"]] = rating_counts.get(c["rating"], 0) + 1
        
        for rating in ["A+", "A", "B+", "B", "C", "D", "F"]:
            if rating in rating_counts:
                count = rating_counts[rating]
                pct = count / len(self.screened_companies) * 100
                bar = "█" * int(pct / 5)
                report += f"{rating:3}: {bar} {count} 家 ({pct:.1f}%)\n"
        
        # 投資建議
        report += f"""
{'─'*90}
💡 【投資建議】
{'─'*90}

1. 優先考慮 A/A+ 級公司作為核心持股
2. 重點關注毛利率 > 30% 且營收成長 > 10% 的公司
3. 避免評級 D 或 F 的公司
4. 自由現金流為負的公司需特別謹慎

{'─'*90}
⚠️ 【風險提示】
{'─'*90}

1. 財務數據有延遲，可能不反映最新狀況
2. 量化篩選應與基本面分析結合使用
3. 過去表現不代表未來結果
4. 投資前應進行獨立研究

{'='*90}
"""
        
        return report
    
    def save_report(self, directory: str = "reports"):
        """保存報告"""
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(
            directory,
            f"{self.market}_screening_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        report = self.generate_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 報告已保存至: {filename}")
        return filename
    
    def export_to_excel(self, directory: str = "exports"):
        """導出 Excel"""
        if not self.screened_companies:
            print("沒有數據可導出")
            return
        
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(
            directory,
            f"{self.market}_screening_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
        
        try:
            df = pd.DataFrame([{
                "排名": c["rank"],
                "股票代號": c["ticker"],
                "公司名稱": c["name"],
                "評級": c["rating"],
                "總分": c["score"],
                "毛利率(%)": c["gross_margin"],
                "營收成長(%)": c["revenue_growth"],
                "自由現金流(%)": c["free_cash_flow_margin"],
                "ROE(%)": c["roe"],
                "流動比率": c["current_ratio"],
                "負債比(%)": c["debt_to_equity"],
                "營益率(%)": c["operating_margin"],
                "殖利率(%)": c["dividend_yield"],
                "股價": c["current_price"],
                "52週位置(%)": c["price_position"]
            } for c in self.screened_companies])
            
            df.to_excel(filename, index=False, sheet_name="篩選結果")
            print(f"📊 Excel 已保存至: {filename}")
            return filename
            
        except ImportError:
            print("⚠️ 請安裝 openpyxl: pip install openpyxl")
            return None
    
    def get_top_companies(self, n: int = 10) -> List[Dict]:
        """獲取評分最高的公司"""
        return self.screened_companies[:n]
    
    def to_dict(self) -> Dict:
        """轉換為字典格式（用於 API）"""
        return {
            "market": self.market,
            "screened_count": len(self.screened_companies),
            "companies": self.screened_companies,
            "statistics": {
                "avg_score": np.mean([c["score"] for c in self.screened_companies]) if self.screened_companies else 0,
                "avg_gross_margin": np.mean([c["gross_margin"] for c in self.screened_companies]) if self.screened_companies else 0,
                "avg_revenue_growth": np.mean([c["revenue_growth"] for c in self.screened_companies]) if self.screened_companies else 0,
            },
            "rating_distribution": self._get_rating_distribution(),
            "last_update": self.last_update.isoformat() if self.last_update else None
        }
    
    def _get_rating_distribution(self) -> Dict:
        """獲取評級分布"""
        distribution = {}
        for c in self.screened_companies:
            rating = c["rating"]
            distribution[rating] = distribution.get(rating, 0) + 1
        return distribution


def main():
    """主程式"""
    print("=" * 90)
    print("📊 財報與營收量化篩選系統 v2.0")
    print("=" * 90)
    
    # 選擇市場
    print("\n📋 可選市場:")
    print("  1. TW - 台灣股市")
    print("  2. US - 美國股市")
    
    market_choice = input("\n請選擇市場 (預設 TW): ").strip()
    market = "US" if market_choice == "2" else "TW"
    
    # 選擇股票池
    print(f"\n📋 {market} 市場可選股票池:")
    if market == "TW":
        print("  1. large_cap  - 大型股")
        print("  2. mid_cap    - 中型股")
        print("  3. dividend   - 高股息股")
        print("  4. ai_server  - AI伺服器概念股")
    else:
        print("  1. tech       - 科技股")
        print("  2. finance    - 金融股")
        print("  3. healthcare - 醫療股")
    
    universe_choice = input("\n請選擇股票池 (預設 1): ").strip()
    
    if market == "TW":
        universe_map = {"1": "large_cap", "2": "mid_cap", "3": "dividend", "4": "ai_server"}
    else:
        universe_map = {"1": "tech", "2": "finance", "3": "healthcare"}
    
    universe_type = universe_map.get(universe_choice, list(universe_map.values())[0])
    
    # 設定門檻
    try:
        min_score = float(input("\n設定最低分數門檻 (0-100，預設 60): ").strip() or "60")
    except:
        min_score = 60
    
    # 初始化
    print(f"\n🔄 初始化 {market} 市場篩選器...")
    screener = FinancialScreener(market=market)
    
    # 執行篩選
    print("\n[步驟 1] 執行財務篩選...")
    screened = screener.screen_companies(
        universe_type=universe_type,
        min_score=min_score,
        use_real_data=True
    )
    
    if not screened:
        print("❌ 沒有公司符合條件")
        return
    
    # 生成報告
    print("\n[步驟 2] 生成分析報告...")
    report = screener.generate_report()
    print(report)
    
    # 保存
    screener.save_report(directory="financial_screener/reports")
    
    # 導出 Excel
    print("\n[步驟 3] 導出 Excel...")
    screener.export_to_excel(directory="financial_screener/exports")
    
    # 顯示 Top 10
    print("\n📈 財務評分 Top 10:")
    print("-" * 70)
    for c in screener.get_top_companies(10):
        print(f"  {c['rank']:2}. {c['ticker']:6} {c['name'][:12]:12} | {c['rating']:3} {c['score']:5.1f}分 "
              f"| 毛利{c['gross_margin']:5.1f}% | 成長{c['revenue_growth']:+5.1f}%")
    
    print("\n" + "=" * 90)
    print("✅ 篩選完成！")
    print("=" * 90)
    
    return screener


if __name__ == "__main__":
    main()
