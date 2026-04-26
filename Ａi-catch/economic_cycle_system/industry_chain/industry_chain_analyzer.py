"""
產業鏈與定價權分析模組 v2.0
分析產業鏈結構，識別具有定價權的關鍵企業

系統名稱：循環驅動多因子投資系統
模組2：產業鏈與定價權分析模組
"""

import pandas as pd
import numpy as np
import yfinance as yf
import requests
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
import warnings
import os

warnings.filterwarnings('ignore')

# 設定中文字體
try:
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Microsoft JhengHei', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass


class IndustryChainAnalyzer:
    """
    產業鏈與定價權分析器
    專注於分析半導體、電子製造、新能源等產業鏈結構
    """
    
    def __init__(self, industry: str = "semiconductor"):
        """
        初始化分析器
        
        Parameters:
        -----------
        industry : str
            要分析的產業類別，可選：
            - "semiconductor": 半導體產業
            - "electric_vehicle": 電動車產業
            - "ai_server": AI伺服器產業
            - "smartphone": 智慧手機產業
            - "renewable_energy": 再生能源產業
        """
        self.industry = industry
        self.chain_structure = {}
        self.companies_data = {}
        self.pricing_power_scores = {}
        self.last_update = None
        
        # 定義各產業的鏈結構
        self.industry_chains = {
            "semiconductor": {
                "name": "半導體產業鏈",
                "description": "從IC設計到終端應用的完整產業鏈",
                "segments": {
                    "上游": ["IC設計", "EDA工具", "IP授權", "材料"],
                    "中游": ["晶圓製造", "晶圓代工", "封裝測試", "設備製造"],
                    "下游": ["系統整合", "品牌廠商", "終端應用"]
                },
                "key_companies": {
                    "上游": [
                        {"name": "聯發科", "ticker": "2454", "subsegment": "IC設計"},
                        {"name": "聯詠", "ticker": "3034", "subsegment": "IC設計"},
                        {"name": "瑞昱", "ticker": "2379", "subsegment": "IC設計"},
                        {"name": "信驊", "ticker": "5274", "subsegment": "IC設計"},
                        {"name": "創意", "ticker": "3443", "subsegment": "IC設計"},
                        {"name": "世芯-KY", "ticker": "3661", "subsegment": "IC設計"},
                    ],
                    "中游": [
                        {"name": "台積電", "ticker": "2330", "subsegment": "晶圓代工"},
                        {"name": "聯電", "ticker": "2303", "subsegment": "晶圓代工"},
                        {"name": "日月光投控", "ticker": "3711", "subsegment": "封裝測試"},
                        {"name": "力成", "ticker": "6239", "subsegment": "封裝測試"},
                        {"name": "京元電子", "ticker": "2449", "subsegment": "封裝測試"},
                        {"name": "環球晶", "ticker": "6488", "subsegment": "材料"},
                    ],
                    "下游": [
                        {"name": "鴻海", "ticker": "2317", "subsegment": "系統整合"},
                        {"name": "和碩", "ticker": "4938", "subsegment": "系統整合"},
                        {"name": "廣達", "ticker": "2382", "subsegment": "系統整合"},
                        {"name": "仁寶", "ticker": "2324", "subsegment": "系統整合"},
                        {"name": "英業達", "ticker": "2356", "subsegment": "系統整合"},
                        {"name": "緯創", "ticker": "3231", "subsegment": "系統整合"},
                    ]
                }
            },
            "electric_vehicle": {
                "name": "電動車產業鏈",
                "description": "從材料到整車的電動車完整產業鏈",
                "segments": {
                    "上游": ["鋰礦", "鈷礦", "電池材料", "馬達材料"],
                    "中游": ["電池製造", "電機系統", "電控系統", "充電設備"],
                    "下游": ["整車製造", "充電服務", "維修服務"]
                },
                "key_companies": {
                    "上游": [
                        {"name": "康普", "ticker": "4739", "subsegment": "電池材料"},
                        {"name": "美琪瑪", "ticker": "4721", "subsegment": "電池材料"},
                        {"name": "立凱-KY", "ticker": "5227", "subsegment": "電池材料"},
                        {"name": "聚和", "ticker": "6509", "subsegment": "電池材料"},
                    ],
                    "中游": [
                        {"name": "台達電", "ticker": "2308", "subsegment": "電控系統"},
                        {"name": "光寶科", "ticker": "2301", "subsegment": "電控系統"},
                        {"name": "和大", "ticker": "1536", "subsegment": "傳動系統"},
                        {"name": "貿聯-KY", "ticker": "3665", "subsegment": "連接器"},
                        {"name": "飛宏", "ticker": "2457", "subsegment": "充電設備"},
                    ],
                    "下游": [
                        {"name": "鴻海", "ticker": "2317", "subsegment": "整車製造"},
                        {"name": "裕隆", "ticker": "2201", "subsegment": "整車製造"},
                        {"name": "中華車", "ticker": "2204", "subsegment": "整車製造"},
                        {"name": "和泰車", "ticker": "2207", "subsegment": "汽車銷售"},
                    ]
                }
            },
            "ai_server": {
                "name": "AI伺服器產業鏈",
                "description": "AI算力基礎設施的完整產業鏈",
                "segments": {
                    "上游": ["GPU/ASIC晶片", "記憶體", "散熱材料", "電源IC"],
                    "中游": ["伺服器製造", "電源供應", "機殼/機架", "連接器"],
                    "下游": ["雲端服務", "企業客戶", "資料中心"]
                },
                "key_companies": {
                    "上游": [
                        {"name": "台積電", "ticker": "2330", "subsegment": "晶片代工"},
                        {"name": "日月光投控", "ticker": "3711", "subsegment": "封裝"},
                        {"name": "南亞科", "ticker": "2408", "subsegment": "記憶體"},
                        {"name": "力成", "ticker": "6239", "subsegment": "封裝"},
                        {"name": "奇鋐", "ticker": "3017", "subsegment": "散熱"},
                        {"name": "雙鴻", "ticker": "3324", "subsegment": "散熱"},
                    ],
                    "中游": [
                        {"name": "廣達", "ticker": "2382", "subsegment": "伺服器製造"},
                        {"name": "緯創", "ticker": "3231", "subsegment": "伺服器製造"},
                        {"name": "緯穎", "ticker": "6669", "subsegment": "伺服器製造"},
                        {"name": "英業達", "ticker": "2356", "subsegment": "伺服器製造"},
                        {"name": "鴻海", "ticker": "2317", "subsegment": "伺服器製造"},
                        {"name": "台達電", "ticker": "2308", "subsegment": "電源供應"},
                        {"name": "光寶科", "ticker": "2301", "subsegment": "電源供應"},
                    ],
                    "下游": [
                        {"name": "中華電", "ticker": "2412", "subsegment": "雲端服務"},
                        {"name": "是方", "ticker": "6561", "subsegment": "資料中心"},
                    ]
                }
            },
            "smartphone": {
                "name": "智慧手機產業鏈",
                "description": "從零組件到終端品牌的智慧手機產業鏈",
                "segments": {
                    "上游": ["晶片設計", "鏡頭模組", "顯示面板", "被動元件"],
                    "中游": ["零組件製造", "機殼", "PCB", "組裝代工"],
                    "下游": ["品牌廠商", "通路銷售"]
                },
                "key_companies": {
                    "上游": [
                        {"name": "聯發科", "ticker": "2454", "subsegment": "晶片設計"},
                        {"name": "大立光", "ticker": "3008", "subsegment": "鏡頭模組"},
                        {"name": "玉晶光", "ticker": "3406", "subsegment": "鏡頭模組"},
                        {"name": "友達", "ticker": "2409", "subsegment": "顯示面板"},
                        {"name": "群創", "ticker": "3481", "subsegment": "顯示面板"},
                        {"name": "國巨", "ticker": "2327", "subsegment": "被動元件"},
                    ],
                    "中游": [
                        {"name": "可成", "ticker": "2474", "subsegment": "機殼"},
                        {"name": "鴻準", "ticker": "2354", "subsegment": "機殼"},
                        {"name": "臻鼎-KY", "ticker": "4958", "subsegment": "PCB"},
                        {"name": "欣興", "ticker": "3037", "subsegment": "PCB"},
                        {"name": "鴻海", "ticker": "2317", "subsegment": "組裝代工"},
                        {"name": "和碩", "ticker": "4938", "subsegment": "組裝代工"},
                    ],
                    "下游": [
                        {"name": "宏達電", "ticker": "2498", "subsegment": "品牌廠商"},
                        {"name": "華碩", "ticker": "2357", "subsegment": "品牌廠商"},
                    ]
                }
            }
        }
        
        # 定價權評估指標權重
        self.pricing_power_weights = {
            "market_share": 0.25,
            "gross_margin": 0.25,
            "roe": 0.15,
            "r_d_intensity": 0.15,
            "customer_concentration": 0.10,
            "patent_count": 0.10
        }
        
        # 公司財務數據估計值（當無法獲取真實數據時使用）
        self.company_estimates = {
            # 半導體上游 - IC設計
            "2454": {"gross_margin": 0.485, "roe": 0.22, "market_share": 35.0, "r_d_intensity": 0.18, "customer_concentration": 0.35, "patent_count": 12000},
            "3034": {"gross_margin": 0.42, "roe": 0.18, "market_share": 25.0, "r_d_intensity": 0.15, "customer_concentration": 0.40, "patent_count": 5000},
            "2379": {"gross_margin": 0.48, "roe": 0.20, "market_share": 20.0, "r_d_intensity": 0.16, "customer_concentration": 0.30, "patent_count": 4000},
            "5274": {"gross_margin": 0.52, "roe": 0.25, "market_share": 75.0, "r_d_intensity": 0.20, "customer_concentration": 0.45, "patent_count": 800},
            "3443": {"gross_margin": 0.35, "roe": 0.15, "market_share": 15.0, "r_d_intensity": 0.12, "customer_concentration": 0.50, "patent_count": 600},
            "3661": {"gross_margin": 0.38, "roe": 0.28, "market_share": 18.0, "r_d_intensity": 0.14, "customer_concentration": 0.60, "patent_count": 500},
            
            # 半導體中游 - 晶圓代工/封測
            "2330": {"gross_margin": 0.558, "roe": 0.28, "market_share": 55.0, "r_d_intensity": 0.08, "customer_concentration": 0.25, "patent_count": 50000},
            "2303": {"gross_margin": 0.35, "roe": 0.12, "market_share": 7.0, "r_d_intensity": 0.05, "customer_concentration": 0.35, "patent_count": 8000},
            "3711": {"gross_margin": 0.22, "roe": 0.12, "market_share": 25.0, "r_d_intensity": 0.04, "customer_concentration": 0.30, "patent_count": 6000},
            "6239": {"gross_margin": 0.20, "roe": 0.10, "market_share": 8.0, "r_d_intensity": 0.03, "customer_concentration": 0.45, "patent_count": 1500},
            "2449": {"gross_margin": 0.25, "roe": 0.15, "market_share": 5.0, "r_d_intensity": 0.04, "customer_concentration": 0.40, "patent_count": 1000},
            "6488": {"gross_margin": 0.45, "roe": 0.18, "market_share": 18.0, "r_d_intensity": 0.06, "customer_concentration": 0.35, "patent_count": 2000},
            
            # 半導體下游 - 系統整合
            "2317": {"gross_margin": 0.06, "roe": 0.08, "market_share": 40.0, "r_d_intensity": 0.02, "customer_concentration": 0.30, "patent_count": 15000},
            "4938": {"gross_margin": 0.045, "roe": 0.06, "market_share": 12.0, "r_d_intensity": 0.01, "customer_concentration": 0.65, "patent_count": 3000},
            "2382": {"gross_margin": 0.055, "roe": 0.12, "market_share": 15.0, "r_d_intensity": 0.02, "customer_concentration": 0.35, "patent_count": 4000},
            "2324": {"gross_margin": 0.04, "roe": 0.05, "market_share": 10.0, "r_d_intensity": 0.01, "customer_concentration": 0.40, "patent_count": 2000},
            "2356": {"gross_margin": 0.045, "roe": 0.06, "market_share": 8.0, "r_d_intensity": 0.015, "customer_concentration": 0.35, "patent_count": 2500},
            "3231": {"gross_margin": 0.05, "roe": 0.10, "market_share": 10.0, "r_d_intensity": 0.02, "customer_concentration": 0.40, "patent_count": 3000},
            
            # AI伺服器
            "6669": {"gross_margin": 0.08, "roe": 0.35, "market_share": 20.0, "r_d_intensity": 0.03, "customer_concentration": 0.50, "patent_count": 800},
            "3017": {"gross_margin": 0.28, "roe": 0.25, "market_share": 30.0, "r_d_intensity": 0.05, "customer_concentration": 0.35, "patent_count": 600},
            "3324": {"gross_margin": 0.25, "roe": 0.20, "market_share": 20.0, "r_d_intensity": 0.04, "customer_concentration": 0.40, "patent_count": 400},
            "2408": {"gross_margin": 0.30, "roe": 0.08, "market_share": 5.0, "r_d_intensity": 0.08, "customer_concentration": 0.25, "patent_count": 3000},
            
            # 電動車
            "2308": {"gross_margin": 0.28, "roe": 0.18, "market_share": 45.0, "r_d_intensity": 0.08, "customer_concentration": 0.25, "patent_count": 8000},
            "2301": {"gross_margin": 0.18, "roe": 0.10, "market_share": 15.0, "r_d_intensity": 0.04, "customer_concentration": 0.30, "patent_count": 4000},
            "1536": {"gross_margin": 0.22, "roe": 0.15, "market_share": 25.0, "r_d_intensity": 0.05, "customer_concentration": 0.55, "patent_count": 500},
            "3665": {"gross_margin": 0.32, "roe": 0.22, "market_share": 15.0, "r_d_intensity": 0.06, "customer_concentration": 0.45, "patent_count": 600},
            
            # 智慧手機
            "3008": {"gross_margin": 0.60, "roe": 0.15, "market_share": 60.0, "r_d_intensity": 0.12, "customer_concentration": 0.70, "patent_count": 3000},
            "2327": {"gross_margin": 0.35, "roe": 0.12, "market_share": 35.0, "r_d_intensity": 0.05, "customer_concentration": 0.30, "patent_count": 2000},
            "2474": {"gross_margin": 0.25, "roe": 0.08, "market_share": 25.0, "r_d_intensity": 0.04, "customer_concentration": 0.75, "patent_count": 2000},
            "3037": {"gross_margin": 0.20, "roe": 0.15, "market_share": 15.0, "r_d_intensity": 0.05, "customer_concentration": 0.35, "patent_count": 3500},
            "4958": {"gross_margin": 0.22, "roe": 0.18, "market_share": 20.0, "r_d_intensity": 0.04, "customer_concentration": 0.40, "patent_count": 2500},
            
            # 電信/資料中心
            "2412": {"gross_margin": 0.35, "roe": 0.10, "market_share": 35.0, "r_d_intensity": 0.03, "customer_concentration": 0.15, "patent_count": 1500},
        }
    
    def fetch_company_data(self, ticker: str, company_name: str = "") -> Dict:
        """
        獲取公司財務數據
        """
        try:
            yf_ticker = f"{ticker}.TW"
            stock = yf.Ticker(yf_ticker)
            info = stock.info
            
            # 嘗試獲取真實數據
            company_data = {
                "ticker": ticker,
                "name": company_name or info.get("longName", ticker),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", 0),
                "current_price": info.get("currentPrice", 0),
                "52w_high": info.get("fiftyTwoWeekHigh", 0),
                "52w_low": info.get("fiftyTwoWeekLow", 0),
            }
            
            # 使用估計值補充關鍵指標
            estimates = self.company_estimates.get(ticker, {})
            
            company_data["gross_margin"] = estimates.get("gross_margin", info.get("grossMargins", 0.15))
            company_data["roe"] = estimates.get("roe", info.get("returnOnEquity", 0.10))
            company_data["market_share"] = estimates.get("market_share", 5.0)
            company_data["r_d_intensity"] = estimates.get("r_d_intensity", 0.05)
            company_data["customer_concentration"] = estimates.get("customer_concentration", 0.40)
            company_data["patent_count"] = estimates.get("patent_count", 1000)
            company_data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            company_data["data_source"] = "yfinance+estimates"
            
            return company_data
            
        except Exception as e:
            print(f"  ⚠️ 獲取 {ticker} 數據時使用估計值: {e}")
            return self._get_estimated_data(ticker, company_name)
    
    def _get_estimated_data(self, ticker: str, company_name: str = "") -> Dict:
        """使用估計值生成公司數據"""
        estimates = self.company_estimates.get(ticker, {})
        
        return {
            "ticker": ticker,
            "name": company_name or f"公司_{ticker}",
            "market_cap": 0,
            "gross_margin": estimates.get("gross_margin", np.random.uniform(0.15, 0.45)),
            "roe": estimates.get("roe", np.random.uniform(0.08, 0.20)),
            "market_share": estimates.get("market_share", np.random.uniform(5, 30)),
            "r_d_intensity": estimates.get("r_d_intensity", np.random.uniform(0.03, 0.12)),
            "customer_concentration": estimates.get("customer_concentration", np.random.uniform(0.25, 0.55)),
            "patent_count": estimates.get("patent_count", np.random.randint(500, 5000)),
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "data_source": "estimates"
        }
    
    def calculate_pricing_power_score(self, company_data: Dict) -> Tuple[float, Dict]:
        """
        計算定價權分數 (0-100)
        
        Returns:
        --------
        Tuple[float, Dict]: (總分, 各項細分分數)
        """
        scores_detail = {}
        total_score = 0
        
        # 1. 市占率評分 (0-25分)
        market_share = company_data.get("market_share", 0)
        market_share_score = min(25, market_share * 0.5)  # 50%市占得25分
        scores_detail["market_share"] = {"value": market_share, "score": market_share_score, "max": 25}
        total_score += market_share_score * self.pricing_power_weights["market_share"] * 4
        
        # 2. 毛利率評分 (0-25分)
        gross_margin = company_data.get("gross_margin", 0)
        gross_margin_score = min(25, gross_margin * 50)  # 50%毛利率得25分
        scores_detail["gross_margin"] = {"value": gross_margin, "score": gross_margin_score, "max": 25}
        total_score += gross_margin_score * self.pricing_power_weights["gross_margin"] * 4
        
        # 3. ROE評分 (0-15分)
        roe = company_data.get("roe", 0)
        roe_score = min(15, roe * 60)  # 25% ROE得15分
        scores_detail["roe"] = {"value": roe, "score": roe_score, "max": 15}
        total_score += roe_score * self.pricing_power_weights["roe"] * (100/15)
        
        # 4. 研發強度評分 (0-15分)
        r_d_intensity = company_data.get("r_d_intensity", 0)
        r_d_score = min(15, r_d_intensity * 100)  # 15%研發強度得15分
        scores_detail["r_d_intensity"] = {"value": r_d_intensity, "score": r_d_score, "max": 15}
        total_score += r_d_score * self.pricing_power_weights["r_d_intensity"] * (100/15)
        
        # 5. 客戶集中度評分 (0-10分) - 越低越好
        concentration = company_data.get("customer_concentration", 0.5)
        concentration_score = 10 * (1 - concentration)  # 集中度0%得10分
        scores_detail["customer_concentration"] = {"value": concentration, "score": concentration_score, "max": 10}
        total_score += concentration_score * self.pricing_power_weights["customer_concentration"] * 10
        
        # 6. 專利數量評分 (0-10分)
        patents = company_data.get("patent_count", 0)
        patent_score = min(10, patents / 1000)  # 每1000個專利得1分，最高10分
        scores_detail["patent_count"] = {"value": patents, "score": patent_score, "max": 10}
        total_score += patent_score * self.pricing_power_weights["patent_count"] * 10
        
        final_score = round(min(100, total_score), 1)
        
        return final_score, scores_detail
    
    def analyze_industry_chain(self, fetch_real_data: bool = True) -> Dict:
        """
        分析整個產業鏈
        """
        print(f"\n🏭 開始分析 {self.industry_chains[self.industry]['name']}...")
        print("=" * 60)
        
        if self.industry not in self.industry_chains:
            print(f"❌ 不支援的產業: {self.industry}")
            return {}
        
        chain_info = self.industry_chains[self.industry]
        
        analysis_result = {
            "industry": self.industry,
            "industry_name": chain_info["name"],
            "description": chain_info.get("description", ""),
            "segments": {},
            "pricing_power_leaders": {},
            "bottlenecks": [],
            "investment_advice": [],
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        all_companies = []
        
        # 分析每個產業環節
        for segment in chain_info["segments"].keys():
            print(f"\n📊 分析 {segment}...")
            
            segment_companies = chain_info["key_companies"].get(segment, [])
            segment_result = {
                "subsegments": chain_info["segments"][segment],
                "companies": [],
                "avg_pricing_power": 0,
                "top_companies": [],
                "company_count": len(segment_companies)
            }
            
            company_scores = []
            
            for company_info in segment_companies:
                company_name = company_info["name"]
                ticker = company_info["ticker"]
                subsegment = company_info.get("subsegment", "")
                
                # 獲取公司數據
                if fetch_real_data:
                    company_data = self.fetch_company_data(ticker, company_name)
                else:
                    company_data = self._get_estimated_data(ticker, company_name)
                
                # 計算定價權分數
                pricing_power_score, score_detail = self.calculate_pricing_power_score(company_data)
                
                company_result = {
                    "name": company_name,
                    "ticker": ticker,
                    "subsegment": subsegment,
                    "pricing_power_score": pricing_power_score,
                    "gross_margin": company_data.get("gross_margin", 0),
                    "market_share": company_data.get("market_share", 0),
                    "roe": company_data.get("roe", 0),
                    "r_d_intensity": company_data.get("r_d_intensity", 0),
                    "customer_concentration": company_data.get("customer_concentration", 0),
                    "patent_count": company_data.get("patent_count", 0),
                    "score_detail": score_detail,
                    "data": company_data
                }
                
                segment_result["companies"].append(company_result)
                company_scores.append(pricing_power_score)
                all_companies.append({**company_result, "segment": segment})
                
                # 保存到全局數據
                self.companies_data[ticker] = company_data
                self.pricing_power_scores[ticker] = pricing_power_score
                
                print(f"  ✅ {company_name} ({ticker}): 定價權分數 {pricing_power_score}")
            
            # 計算環節統計
            if company_scores:
                segment_result["avg_pricing_power"] = round(np.mean(company_scores), 1)
                segment_result["max_pricing_power"] = round(max(company_scores), 1)
                segment_result["min_pricing_power"] = round(min(company_scores), 1)
                
                # 找出定價權最高的公司
                sorted_companies = sorted(
                    segment_result["companies"],
                    key=lambda x: x["pricing_power_score"],
                    reverse=True
                )
                segment_result["top_companies"] = sorted_companies[:3]
            
            analysis_result["segments"][segment] = segment_result
            
            # 識別環節領導者
            if segment_result["top_companies"]:
                analysis_result["pricing_power_leaders"][segment] = segment_result["top_companies"][0]
        
        # 識別瓶頸
        analysis_result["bottlenecks"] = self._identify_bottlenecks(analysis_result["segments"])
        
        # 生成投資建議
        analysis_result["investment_advice"] = self._generate_investment_advice(analysis_result, all_companies)
        
        self.chain_structure = analysis_result
        self.last_update = datetime.now()
        
        print("\n" + "=" * 60)
        print("✅ 產業鏈分析完成！")
        
        return analysis_result
    
    def _identify_bottlenecks(self, segments: Dict) -> List[Dict]:
        """識別產業鏈瓶頸"""
        bottlenecks = []
        
        for segment, segment_data in segments.items():
            companies = segment_data.get("companies", [])
            
            if not companies:
                continue
            
            # 計算集中度指標
            top_3_share = sum(sorted([c.get("market_share", 0) for c in companies], reverse=True)[:3])
            avg_gross_margin = np.mean([c.get("gross_margin", 0) for c in companies])
            avg_pricing_power = segment_data.get("avg_pricing_power", 0)
            
            # 瓶頸判斷邏輯
            is_bottleneck = False
            reasons = []
            
            if top_3_share > 70:
                is_bottleneck = True
                reasons.append(f"前三大市占率達 {top_3_share:.1f}%，供應集中")
            
            if avg_gross_margin > 0.35:
                is_bottleneck = True
                reasons.append(f"平均毛利率 {avg_gross_margin*100:.1f}%，定價能力強")
            
            if avg_pricing_power > 65:
                is_bottleneck = True
                reasons.append(f"平均定價權分數 {avg_pricing_power}，護城河高")
            
            if is_bottleneck:
                bottleneck = {
                    "segment": segment,
                    "reasons": reasons,
                    "top_companies": [c["name"] for c in companies[:3]],
                    "avg_market_share": round(top_3_share / 3, 1),
                    "avg_gross_margin": round(avg_gross_margin, 3),
                    "avg_pricing_power": avg_pricing_power,
                    "risk_level": "高" if top_3_share > 80 or avg_gross_margin > 0.45 else "中"
                }
                bottlenecks.append(bottleneck)
        
        return bottlenecks
    
    def _generate_investment_advice(self, analysis_result: Dict, all_companies: List[Dict]) -> List[Dict]:
        """生成投資建議"""
        advice_list = []
        
        # 按定價權分數排序所有公司
        sorted_companies = sorted(all_companies, key=lambda x: x["pricing_power_score"], reverse=True)
        
        # 頂級推薦（分數 >= 70）
        top_picks = [c for c in sorted_companies if c["pricing_power_score"] >= 70]
        if top_picks:
            advice_list.append({
                "category": "🏆 頂級推薦",
                "description": "定價權極強，具有深厚護城河的龍頭企業",
                "strategy": "積極布局，長期持有",
                "stocks": [{"name": c["name"], "ticker": c["ticker"], "score": c["pricing_power_score"], 
                           "segment": c["segment"], "reason": f"毛利率{c['gross_margin']*100:.1f}%，市占{c['market_share']:.1f}%"} 
                          for c in top_picks[:5]]
            })
        
        # 優質選擇（分數 55-70）
        quality_picks = [c for c in sorted_companies if 55 <= c["pricing_power_score"] < 70]
        if quality_picks:
            advice_list.append({
                "category": "⭐ 優質選擇",
                "description": "定價權良好，在細分領域具有優勢",
                "strategy": "選擇性投資，關注成長性",
                "stocks": [{"name": c["name"], "ticker": c["ticker"], "score": c["pricing_power_score"],
                           "segment": c["segment"], "reason": f"毛利率{c['gross_margin']*100:.1f}%"} 
                          for c in quality_picks[:5]]
            })
        
        # 觀察名單（分數 40-55）
        watch_list = [c for c in sorted_companies if 40 <= c["pricing_power_score"] < 55]
        if watch_list:
            advice_list.append({
                "category": "👀 觀察名單",
                "description": "定價權一般，需觀察競爭態勢變化",
                "strategy": "等待更好進場點位",
                "stocks": [{"name": c["name"], "ticker": c["ticker"], "score": c["pricing_power_score"],
                           "segment": c["segment"]} 
                          for c in watch_list[:5]]
            })
        
        # 環節投資建議
        for segment, segment_data in analysis_result["segments"].items():
            avg_score = segment_data.get("avg_pricing_power", 0)
            
            if avg_score >= 65:
                strategy = "該環節定價權強，建議超配"
            elif avg_score >= 50:
                strategy = "該環節定價權中等，配置標配"
            else:
                strategy = "該環節定價權弱，建議低配或避開"
            
            advice_list.append({
                "category": f"📊 {segment}環節",
                "description": f"平均定價權分數: {avg_score}",
                "strategy": strategy,
                "top_pick": segment_data["top_companies"][0] if segment_data["top_companies"] else None
            })
        
        return advice_list
    
    def generate_report(self) -> str:
        """生成分析報告"""
        if not self.chain_structure:
            return "請先執行 analyze_industry_chain() 方法"
        
        report = f"""
{'='*80}
🏭 產業鏈與定價權分析報告
{'='*80}

📋 產業: {self.chain_structure['industry_name']}
📝 說明: {self.chain_structure.get('description', '')}
📅 分析時間: {self.chain_structure['analysis_date']}

{'─'*80}
📊 【產業鏈結構概述】
{'─'*80}
"""
        
        # 產業鏈結構
        for segment, segment_data in self.chain_structure["segments"].items():
            report += f"""
▶ {segment}
  子環節: {', '.join(segment_data['subsegments'])}
  公司數量: {segment_data['company_count']}
  平均定價權分數: {segment_data['avg_pricing_power']}
  最高分數: {segment_data.get('max_pricing_power', 'N/A')}
  
  定價權領導者:
"""
            for i, company in enumerate(segment_data['top_companies'][:3], 1):
                report += f"    {i}. {company['name']} ({company['ticker']})"
                report += f" - 分數: {company['pricing_power_score']}"
                report += f", 毛利率: {company['gross_margin']*100:.1f}%"
                report += f", 市占: {company['market_share']:.1f}%\n"
        
        # 瓶頸分析
        report += f"""
{'─'*80}
🔍 【產業鏈瓶頸分析】
{'─'*80}
"""
        
        bottlenecks = self.chain_structure.get("bottlenecks", [])
        if bottlenecks:
            for bottleneck in bottlenecks:
                report += f"""
▶ 環節: {bottleneck['segment']}
  風險等級: {bottleneck['risk_level']}
  原因:
"""
                for reason in bottleneck['reasons']:
                    report += f"    • {reason}\n"
                report += f"  主要公司: {', '.join(bottleneck['top_companies'])}\n"
        else:
            report += "\n  未發現明顯產業鏈瓶頸\n"
        
        # 投資建議
        report += f"""
{'─'*80}
💰 【投資建議】
{'─'*80}
"""
        
        for advice in self.chain_structure.get("investment_advice", []):
            report += f"\n{advice['category']}\n"
            report += f"  說明: {advice['description']}\n"
            report += f"  策略: {advice['strategy']}\n"
            
            if 'stocks' in advice:
                report += "  推薦標的:\n"
                for stock in advice['stocks'][:3]:
                    report += f"    • {stock['name']} ({stock['ticker']}) - 分數: {stock['score']}"
                    if 'reason' in stock:
                        report += f" | {stock['reason']}"
                    report += "\n"
        
        # 風險提示
        report += f"""
{'─'*80}
⚠️ 【風險提示】
{'─'*80}

1. 定價權可能隨技術變遷而改變
2. 客戶集中度高的公司營運風險較大
3. 需結合總經環境與產業週期綜合判斷
4. 數據包含估算值，實際投資前應查閱公司財報
5. 市占率數據為產業研究估算，可能與實際有偏差

{'='*80}
"""
        return report
    
    def save_report(self, directory: str = "reports"):
        """保存報告到檔案"""
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(
            directory, 
            f"{self.industry}_chain_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        report = self.generate_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 報告已保存至: {filename}")
        return filename
    
    def export_to_excel(self, directory: str = "exports"):
        """導出數據到Excel"""
        if not self.chain_structure:
            print("請先執行 analyze_industry_chain()")
            return
        
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(
            directory,
            f"{self.industry}_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # 公司詳細數據
                all_data = []
                for segment, segment_data in self.chain_structure["segments"].items():
                    for company in segment_data["companies"]:
                        row = {
                            "產業環節": segment,
                            "子環節": company.get("subsegment", ""),
                            "公司名稱": company["name"],
                            "股票代號": company["ticker"],
                            "定價權分數": company["pricing_power_score"],
                            "毛利率(%)": round(company["gross_margin"] * 100, 2),
                            "市占率(%)": round(company["market_share"], 2),
                            "ROE(%)": round(company["roe"] * 100, 2),
                            "客戶集中度(%)": round(company["customer_concentration"] * 100, 2),
                            "研發強度(%)": round(company["r_d_intensity"] * 100, 2),
                            "專利數量": company["patent_count"]
                        }
                        all_data.append(row)
                
                df_companies = pd.DataFrame(all_data)
                df_companies.to_excel(writer, sheet_name='公司分析', index=False)
                
                # 環節匯總
                segment_summary = []
                for segment, segment_data in self.chain_structure["segments"].items():
                    row = {
                        "產業環節": segment,
                        "子環節": ", ".join(segment_data["subsegments"]),
                        "公司數量": segment_data["company_count"],
                        "平均定價權分數": segment_data["avg_pricing_power"],
                        "最高分數": segment_data.get("max_pricing_power", 0),
                        "定價權領導者": segment_data["top_companies"][0]["name"] if segment_data["top_companies"] else "N/A",
                        "領導者分數": segment_data["top_companies"][0]["pricing_power_score"] if segment_data["top_companies"] else 0
                    }
                    segment_summary.append(row)
                
                df_segments = pd.DataFrame(segment_summary)
                df_segments.to_excel(writer, sheet_name='環節匯總', index=False)
                
                # 瓶頸分析
                bottlenecks = self.chain_structure.get("bottlenecks", [])
                if bottlenecks:
                    df_bottlenecks = pd.DataFrame(bottlenecks)
                    df_bottlenecks.to_excel(writer, sheet_name='瓶頸分析', index=False)
            
            print(f"📊 數據已導出至: {filename}")
            return filename
            
        except ImportError:
            print("⚠️ 無法導出Excel，請安裝 openpyxl: pip install openpyxl")
            return None
    
    def to_dict(self) -> Dict:
        """將分析結果轉換為字典（用於API）"""
        return {
            "industry": self.industry,
            "industry_name": self.chain_structure.get("industry_name", ""),
            "description": self.chain_structure.get("description", ""),
            "segments": self.chain_structure.get("segments", {}),
            "pricing_power_leaders": self.chain_structure.get("pricing_power_leaders", {}),
            "bottlenecks": self.chain_structure.get("bottlenecks", []),
            "investment_advice": self.chain_structure.get("investment_advice", []),
            "analysis_date": self.chain_structure.get("analysis_date", ""),
            "last_update": self.last_update.isoformat() if self.last_update else None
        }
    
    def get_top_stocks(self, n: int = 10) -> List[Dict]:
        """獲取定價權最高的前N支股票"""
        all_companies = []
        for segment, segment_data in self.chain_structure.get("segments", {}).items():
            for company in segment_data.get("companies", []):
                all_companies.append({
                    **company,
                    "segment": segment
                })
        
        sorted_companies = sorted(all_companies, key=lambda x: x["pricing_power_score"], reverse=True)
        return sorted_companies[:n]


def main():
    """主程式"""
    print("=" * 80)
    print("🏭 產業鏈與定價權分析系統 v2.0")
    print("=" * 80)
    
    # 顯示可選產業
    print("\n📋 可選產業:")
    print("  1. semiconductor    - 半導體產業鏈")
    print("  2. electric_vehicle - 電動車產業鏈")
    print("  3. ai_server        - AI伺服器產業鏈")
    print("  4. smartphone       - 智慧手機產業鏈")
    
    # 選擇產業（預設半導體）
    industry_choice = input("\n請選擇要分析的產業 (輸入數字1-4，預設1): ").strip()
    
    industry_map = {
        "1": "semiconductor",
        "2": "electric_vehicle",
        "3": "ai_server",
        "4": "smartphone",
        "": "semiconductor"
    }
    
    industry = industry_map.get(industry_choice, "semiconductor")
    
    # 選擇數據源
    use_real_data_input = input("\n是否嘗試獲取真實數據? (y/n，預設y): ").strip().lower()
    use_real_data = use_real_data_input != 'n'
    
    # 初始化分析器
    print(f"\n🔄 初始化 {industry} 產業鏈分析器...")
    analyzer = IndustryChainAnalyzer(industry=industry)
    
    # 分析產業鏈
    print("\n[步驟1] 分析產業鏈結構...")
    analysis_result = analyzer.analyze_industry_chain(fetch_real_data=use_real_data)
    
    # 生成報告
    print("\n[步驟2] 生成分析報告...")
    report = analyzer.generate_report()
    print(report)
    
    # 保存報告
    analyzer.save_report(directory="industry_chain/reports")
    
    # 導出Excel
    print("\n[步驟3] 導出Excel數據...")
    analyzer.export_to_excel(directory="industry_chain/exports")
    
    # 顯示定價權Top 10
    print("\n[步驟4] 定價權 Top 10 股票:")
    print("-" * 60)
    top_stocks = analyzer.get_top_stocks(10)
    for i, stock in enumerate(top_stocks, 1):
        print(f"  {i:2}. {stock['name']:8} ({stock['ticker']}) "
              f"| 分數: {stock['pricing_power_score']:5.1f} "
              f"| 毛利率: {stock['gross_margin']*100:5.1f}% "
              f"| {stock['segment']}")
    
    print("\n" + "=" * 80)
    print("✅ 分析完成！")
    print("=" * 80)
    
    return analyzer


if __name__ == "__main__":
    main()
