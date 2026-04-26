"""
電子股趨勢與訂單監測模組 v2.0
分析電子股產業趨勢、產品週期、訂單能見度

系統名稱：循環驅動多因子投資系統
模組6：電子股趨勢與訂單監測模組
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

warnings.filterwarnings('ignore')


class ProductCyclePhase(Enum):
    """產品週期階段"""
    INTRODUCTION = "導入期"
    GROWTH = "成長期"
    MATURITY = "成熟期"
    DECLINE = "衰退期"
    TRANSITION = "轉換期"


class TechnologyTrend(Enum):
    """技術趨勢"""
    AI_ACCELERATION = "AI加速運算"
    EV_TRANSITION = "電動車轉型"
    IOT_EXPANSION = "物聯網擴展"
    AR_VR_DEVELOPMENT = "AR/VR發展"
    EDGE_COMPUTING = "邊緣運算"
    AUTONOMOUS_DRIVING = "自動駕駛"


@dataclass
class ElectronicCompany:
    """電子公司資料"""
    ticker: str
    name: str
    sector: str
    sub_sector: str
    market_cap: float
    revenue_ttm: float
    product_focus: List[str]
    key_customers: List[str]
    order_visibility: int
    technology_leadership: float
    
    def to_dict(self):
        return asdict(self)


@dataclass
class OrderSignal:
    """訂單信號"""
    company: str
    signal_type: str
    strength: float
    evidence: List[str]
    confidence: float
    date: str
    
    def to_dict(self):
        return asdict(self)


@dataclass
class ProductCycleAnalysis:
    """產品週期分析"""
    product: str
    current_phase: ProductCyclePhase
    growth_rate: float
    market_size: float
    penetration_rate: float
    next_catalyst: str
    catalyst_date: str
    
    def to_dict(self):
        return {
            "product": self.product,
            "current_phase": self.current_phase.value,
            "growth_rate": self.growth_rate,
            "market_size": self.market_size,
            "penetration_rate": self.penetration_rate,
            "next_catalyst": self.next_catalyst,
            "catalyst_date": self.catalyst_date
        }


class ElectronicsMonitor:
    """
    電子股趨勢與訂單監測器
    分析電子股產業趨勢、產品週期、訂單能見度
    """
    
    def __init__(self, focus_sectors: List[str] = None):
        """初始化監測器"""
        self.focus_sectors = focus_sectors or [
            "semiconductor", "pcb", "passive", "connector", 
            "assembly", "display", "lens", "battery"
        ]
        
        self.companies_data = {}
        self.industry_data = {}
        self.order_signals = {}
        self.product_cycles = {}
        self.technology_trends = {}
        self.supply_chain_data = {}
        
        # 電子股資料庫
        self.electronics_database = self._initialize_electronics_database()
        
        # 產品週期資料
        self.product_cycle_info = self._initialize_product_cycles()
        
        # 技術趨勢資料
        self.technology_trend_info = self._initialize_technology_trends()
        
        # 關鍵詞庫
        self.keywords = {
            "order_increase": ["訂單增加", "接單暢旺", "產能滿載", "追加訂單", "需求強勁"],
            "order_decrease": ["訂單下滑", "需求放緩", "產能利用率下降", "訂單能見度縮短"],
            "inventory_build": ["庫存上升", "庫存天數增加", "庫存水位升高"],
            "inventory_draw": ["庫存下降", "庫存去化", "庫存水位健康"],
            "capacity_expansion": ["擴產", "新廠投產", "產能擴充", "資本支出增加"],
            "price_increase": ["漲價", "調漲價格", "價格上揚"],
            "price_decrease": ["降價", "價格壓力", "價格競爭"]
        }
    
    def _initialize_electronics_database(self) -> Dict[str, Dict]:
        """初始化電子股資料庫"""
        return {
            "semiconductor": {
                "name": "半導體",
                "companies": {
                    "2330": {"name": "台積電", "sub_sector": "晶圓代工"},
                    "2303": {"name": "聯電", "sub_sector": "晶圓代工"},
                    "5347": {"name": "世界先進", "sub_sector": "晶圓代工"},
                    "2454": {"name": "聯發科", "sub_sector": "IC設計"},
                    "3034": {"name": "聯詠", "sub_sector": "IC設計"},
                    "2379": {"name": "瑞昱", "sub_sector": "IC設計"},
                    "6415": {"name": "矽力-KY", "sub_sector": "IC設計"},
                    "3443": {"name": "創意", "sub_sector": "IC設計服務"},
                    "3661": {"name": "世芯-KY", "sub_sector": "IC設計服務"},
                    "3711": {"name": "日月光投控", "sub_sector": "封裝測試"},
                    "6239": {"name": "力成", "sub_sector": "封裝測試"},
                    "2449": {"name": "京元電子", "sub_sector": "測試"}
                }
            },
            "pcb": {
                "name": "印刷電路板",
                "companies": {
                    "2313": {"name": "華通", "sub_sector": "HDI板"},
                    "2367": {"name": "燿華", "sub_sector": "HDI板"},
                    "6269": {"name": "台郡", "sub_sector": "軟板"},
                    "4958": {"name": "臻鼎-KY", "sub_sector": "PCB"},
                    "3044": {"name": "健鼎", "sub_sector": "PCB"},
                    "8358": {"name": "金居", "sub_sector": "銅箔"}
                }
            },
            "passive": {
                "name": "被動元件",
                "companies": {
                    "2327": {"name": "國巨", "sub_sector": "電阻/MLCC"},
                    "2492": {"name": "華新科", "sub_sector": "MLCC"},
                    "3026": {"name": "禾伸堂", "sub_sector": "MLCC"},
                    "2456": {"name": "奇力新", "sub_sector": "電感"},
                    "2478": {"name": "大毅", "sub_sector": "電阻"}
                }
            },
            "connector": {
                "name": "連接器",
                "companies": {
                    "3003": {"name": "健和興", "sub_sector": "連接器"},
                    "3533": {"name": "嘉澤", "sub_sector": "連接器"},
                    "6196": {"name": "帆宣", "sub_sector": "設備"}
                }
            },
            "assembly": {
                "name": "組裝代工",
                "companies": {
                    "2317": {"name": "鴻海", "sub_sector": "EMS"},
                    "2356": {"name": "英業達", "sub_sector": "筆電代工"},
                    "2382": {"name": "廣達", "sub_sector": "筆電/伺服器"},
                    "3231": {"name": "緯創", "sub_sector": "筆電代工"},
                    "2324": {"name": "仁寶", "sub_sector": "筆電代工"},
                    "4938": {"name": "和碩", "sub_sector": "組裝代工"},
                    "6669": {"name": "緯穎", "sub_sector": "伺服器"}
                }
            },
            "display": {
                "name": "顯示器",
                "companies": {
                    "2409": {"name": "友達", "sub_sector": "面板"},
                    "3481": {"name": "群創", "sub_sector": "面板"},
                    "8069": {"name": "元太", "sub_sector": "電子紙"}
                }
            },
            "lens": {
                "name": "光學鏡頭",
                "companies": {
                    "3008": {"name": "大立光", "sub_sector": "手機鏡頭"},
                    "3406": {"name": "玉晶光", "sub_sector": "手機鏡頭"},
                    "3504": {"name": "揚明光", "sub_sector": "光學元件"}
                }
            },
            "battery": {
                "name": "電池材料",
                "companies": {
                    "4739": {"name": "康普", "sub_sector": "電池材料"},
                    "4721": {"name": "美琪瑪", "sub_sector": "電池材料"},
                    "2308": {"name": "台達電", "sub_sector": "電源管理"}
                }
            }
        }
    
    def _initialize_product_cycles(self) -> Dict[str, Dict]:
        """初始化產品週期資料"""
        return {
            "smartphone": {
                "current_phase": ProductCyclePhase.MATURITY,
                "growth_rate": 0.02,
                "market_size": 5000,
                "penetration_rate": 0.85,
                "key_drivers": ["5G升級", "摺疊手機", "AI手機"],
                "cycle_length": "12-18個月"
            },
            "ai_server": {
                "current_phase": ProductCyclePhase.GROWTH,
                "growth_rate": 0.35,
                "market_size": 1500,
                "penetration_rate": 0.15,
                "key_drivers": ["生成式AI", "大語言模型", "雲端運算"],
                "cycle_length": "24-36個月"
            },
            "electric_vehicle": {
                "current_phase": ProductCyclePhase.GROWTH,
                "growth_rate": 0.25,
                "market_size": 8000,
                "penetration_rate": 0.10,
                "key_drivers": ["政策支持", "電池技術", "充電基礎設施"],
                "cycle_length": "36-48個月"
            },
            "iot_devices": {
                "current_phase": ProductCyclePhase.GROWTH,
                "growth_rate": 0.15,
                "market_size": 1200,
                "penetration_rate": 0.20,
                "key_drivers": ["智慧家居", "工業4.0", "穿戴裝置"],
                "cycle_length": "18-24個月"
            },
            "ar_vr": {
                "current_phase": ProductCyclePhase.INTRODUCTION,
                "growth_rate": 0.40,
                "market_size": 300,
                "penetration_rate": 0.05,
                "key_drivers": ["蘋果Vision Pro", "企業應用", "遊戲"],
                "cycle_length": "24-36個月"
            },
            "pc_nb": {
                "current_phase": ProductCyclePhase.DECLINE,
                "growth_rate": -0.05,
                "market_size": 2000,
                "penetration_rate": 0.90,
                "key_drivers": ["AI PC", "企業換機", "遠距工作"],
                "cycle_length": "36-48個月"
            }
        }
    
    def _initialize_technology_trends(self) -> Dict[str, Dict]:
        """初始化技術趨勢資料"""
        return {
            "ai_acceleration": {
                "trend": TechnologyTrend.AI_ACCELERATION,
                "adoption_rate": 0.30,
                "growth_forecast": 0.40,
                "key_companies": ["2330", "2382", "3231", "6669"],
                "impact_sectors": ["semiconductor", "assembly"],
                "description": "生成式AI帶動GPU需求爆發，AI伺服器與相關半導體需求強勁"
            },
            "ev_transition": {
                "trend": TechnologyTrend.EV_TRANSITION,
                "adoption_rate": 0.15,
                "growth_forecast": 0.25,
                "key_companies": ["2308", "4739", "4721", "2327"],
                "impact_sectors": ["battery", "passive", "connector"],
                "description": "全球電動車滲透率提升，帶動電池、電源管理、車用半導體需求"
            },
            "edge_computing": {
                "trend": TechnologyTrend.EDGE_COMPUTING,
                "adoption_rate": 0.20,
                "growth_forecast": 0.30,
                "key_companies": ["2454", "2379", "3034"],
                "impact_sectors": ["semiconductor", "pcb"],
                "description": "邊緣運算需求增長，低功耗AI晶片與網通設備受惠"
            },
            "ar_vr": {
                "trend": TechnologyTrend.AR_VR_DEVELOPMENT,
                "adoption_rate": 0.05,
                "growth_forecast": 0.50,
                "key_companies": ["3008", "3406", "2330"],
                "impact_sectors": ["lens", "display", "semiconductor"],
                "description": "AR/VR裝置逐漸普及，光學與顯示技術持續進步"
            }
        }
    
    def fetch_company_data(self, ticker: str) -> ElectronicCompany:
        """獲取電子公司資料"""
        try:
            yf_ticker = f"{ticker}.TW" if ".TW" not in ticker else ticker
            
            print(f"  獲取 {ticker} 資料...", end="")
            stock = yf.Ticker(yf_ticker)
            info = stock.info
            
            sector_info = self._find_company_sector(ticker)
            order_visibility = self._estimate_order_visibility(ticker)
            tech_leadership = self._assess_technology_leadership(ticker, info)
            key_customers = self._estimate_key_customers(ticker)
            product_focus = self._identify_product_focus(ticker, sector_info)
            
            company = ElectronicCompany(
                ticker=ticker,
                name=info.get("longName", sector_info.get("name", ticker)),
                sector=sector_info.get("sector", "unknown"),
                sub_sector=sector_info.get("sub_sector", "unknown"),
                market_cap=info.get("marketCap", 0),
                revenue_ttm=info.get("totalRevenue", 0),
                product_focus=product_focus,
                key_customers=key_customers,
                order_visibility=order_visibility,
                technology_leadership=tech_leadership
            )
            
            self.companies_data[ticker] = company
            print(" 完成")
            return company
            
        except Exception as e:
            print(f" 使用模擬資料")
            return self._create_mock_company(ticker)
    
    def _find_company_sector(self, ticker: str) -> Dict[str, str]:
        """從資料庫尋找公司所屬產業"""
        for sector, sector_info in self.electronics_database.items():
            if ticker in sector_info["companies"]:
                company_info = sector_info["companies"][ticker]
                return {
                    "sector": sector,
                    "name": company_info["name"],
                    "sub_sector": company_info["sub_sector"]
                }
        return {"sector": "unknown", "name": f"公司_{ticker}", "sub_sector": "unknown"}
    
    def _estimate_order_visibility(self, ticker: str) -> int:
        """估算訂單能見度 (季度)"""
        visibility_map = {
            "2330": 4, "2303": 3, "5347": 3,  # 晶圓代工
            "2454": 2, "3034": 2, "2379": 2,  # IC設計
            "2317": 1, "2382": 2, "3231": 2, "6669": 2,  # 組裝代工
            "3008": 2, "3406": 2,  # 光學鏡頭
            "2308": 2, "2327": 1   # 被動元件/電源
        }
        return visibility_map.get(ticker, 1)
    
    def _assess_technology_leadership(self, ticker: str, info: Dict) -> float:
        """評估技術領導力 (0-10分)"""
        leadership_map = {
            "2330": 9.5, "2454": 8.0, "3008": 8.5, "2308": 7.5,
            "2382": 7.0, "3231": 6.5, "6669": 7.5, "2317": 6.0,
            "2303": 7.0, "3034": 7.0, "2379": 7.5, "6415": 7.5
        }
        return leadership_map.get(ticker, 5.0)
    
    def _estimate_key_customers(self, ticker: str) -> List[str]:
        """估算主要客戶"""
        customer_map = {
            "2330": ["Apple", "NVIDIA", "AMD", "Qualcomm"],
            "2454": ["Xiaomi", "OPPO", "vivo", "Samsung"],
            "2317": ["Apple", "Dell", "HP", "Cisco"],
            "2382": ["Apple", "Dell", "HP", "Microsoft"],
            "3231": ["Microsoft", "Google", "Meta", "Dell"],
            "6669": ["Microsoft", "Google", "Meta", "AWS"],
            "3008": ["Apple", "Samsung", "Huawei"],
            "2308": ["Apple", "Tesla", "Microsoft", "Dell"]
        }
        return customer_map.get(ticker, ["主要OEM廠商"])
    
    def _identify_product_focus(self, ticker: str, sector_info: Dict) -> List[str]:
        """識別產品聚焦領域"""
        focus_map = {
            "2330": ["先進製程", "AI晶片", "HPC", "5G晶片"],
            "2454": ["手機晶片", "Wi-Fi 7", "車用晶片", "智慧家居"],
            "2382": ["AI伺服器", "筆電", "雲端運算"],
            "3231": ["AI伺服器", "筆電", "雲端運算"],
            "6669": ["AI伺服器", "雲端運算", "資料中心"],
            "2317": ["iPhone組裝", "伺服器", "電動車"],
            "3008": ["手機鏡頭", "車載鏡頭", "AR/VR鏡頭"],
            "2308": ["電源供應", "電動車充電", "工業自動化"]
        }
        return focus_map.get(ticker, [sector_info.get("sub_sector", "電子產品")])
    
    def _create_mock_company(self, ticker: str) -> ElectronicCompany:
        """創建模擬公司資料"""
        sector_info = self._find_company_sector(ticker)
        return ElectronicCompany(
            ticker=ticker,
            name=sector_info.get("name", f"公司_{ticker}"),
            sector=sector_info.get("sector", "unknown"),
            sub_sector=sector_info.get("sub_sector", "unknown"),
            market_cap=np.random.uniform(100, 1000) * 1e8,
            revenue_ttm=np.random.uniform(50, 500) * 1e8,
            product_focus=[sector_info.get("sub_sector", "電子產品")],
            key_customers=["主要OEM廠商"],
            order_visibility=np.random.randint(1, 4),
            technology_leadership=np.random.uniform(4, 8)
        )
    
    def analyze_product_cycle(self, product: str) -> ProductCycleAnalysis:
        """分析產品週期"""
        if product not in self.product_cycle_info:
            cycle_info = {
                "current_phase": ProductCyclePhase.GROWTH,
                "growth_rate": 0.10,
                "market_size": 500,
                "penetration_rate": 0.30,
                "key_drivers": ["技術創新", "市場需求"],
                "cycle_length": "24個月"
            }
        else:
            cycle_info = self.product_cycle_info[product]
        
        next_catalyst, catalyst_date = self._predict_next_catalyst(product)
        
        analysis = ProductCycleAnalysis(
            product=product,
            current_phase=cycle_info["current_phase"],
            growth_rate=cycle_info["growth_rate"],
            market_size=cycle_info["market_size"],
            penetration_rate=cycle_info["penetration_rate"],
            next_catalyst=next_catalyst,
            catalyst_date=catalyst_date
        )
        
        self.product_cycles[product] = analysis
        return analysis
    
    def _predict_next_catalyst(self, product: str) -> Tuple[str, str]:
        """預測下一個催化劑"""
        now = datetime.now()
        catalysts = {
            "smartphone": ("新款iPhone發布", f"{now.year if now.month < 9 else now.year + 1}-09"),
            "ai_server": ("新一代GPU發布", f"{now.year if now.month < 3 else now.year + 1}-03"),
            "electric_vehicle": ("新車型發布", f"{now.year if now.month < 6 else now.year + 1}-06"),
            "iot_devices": ("新標準發布", f"{now.year}-12"),
            "ar_vr": ("新產品發布", f"{now.year if now.month < 10 else now.year + 1}-10"),
            "pc_nb": ("新平台發布", f"{now.year + 1}-01")
        }
        return catalysts.get(product, ("技術突破", f"{now.year}-Q4"))
    
    def analyze_technology_trends(self) -> Dict[str, Dict]:
        """分析技術趨勢"""
        print("分析技術趨勢...")
        
        trends_analysis = {}
        for trend_id, trend_info in self.technology_trend_info.items():
            impact_score = self._calculate_trend_impact(trend_info)
            beneficiaries = self._identify_trend_beneficiaries(trend_info)
            adoption_timeline = self._predict_adoption_timeline(trend_info)
            
            trends_analysis[trend_id] = {
                "trend": trend_info["trend"].value,
                "adoption_rate": trend_info["adoption_rate"],
                "growth_forecast": trend_info["growth_forecast"],
                "impact_score": impact_score,
                "key_companies": trend_info["key_companies"],
                "beneficiaries": beneficiaries,
                "adoption_timeline": adoption_timeline,
                "description": trend_info["description"]
            }
        
        self.technology_trends = trends_analysis
        print(f"  分析完成 {len(trends_analysis)} 個技術趨勢")
        return trends_analysis
    
    def _calculate_trend_impact(self, trend_info: Dict) -> float:
        """計算趨勢影響分數 (0-10)"""
        base_score = trend_info["adoption_rate"] * 5 + trend_info["growth_forecast"] * 5
        
        trend = trend_info["trend"]
        if trend == TechnologyTrend.AI_ACCELERATION:
            base_score += 3.0
        elif trend == TechnologyTrend.EV_TRANSITION:
            base_score += 2.5
        
        return min(10.0, base_score)
    
    def _identify_trend_beneficiaries(self, trend_info: Dict) -> List[Dict]:
        """識別受益公司"""
        beneficiaries = []
        trend = trend_info["trend"]
        
        if trend == TechnologyTrend.AI_ACCELERATION:
            beneficiaries = [
                {"ticker": "2330", "reason": "AI晶片代工", "exposure": 0.8},
                {"ticker": "2382", "reason": "AI伺服器組裝", "exposure": 0.6},
                {"ticker": "3231", "reason": "AI伺服器代工", "exposure": 0.5},
                {"ticker": "6669", "reason": "AI伺服器品牌", "exposure": 0.7}
            ]
        elif trend == TechnologyTrend.EV_TRANSITION:
            beneficiaries = [
                {"ticker": "2308", "reason": "電源管理", "exposure": 0.7},
                {"ticker": "4739", "reason": "電池材料", "exposure": 0.8},
                {"ticker": "2327", "reason": "車用被動元件", "exposure": 0.5}
            ]
        elif trend == TechnologyTrend.EDGE_COMPUTING:
            beneficiaries = [
                {"ticker": "2454", "reason": "邊緣AI晶片", "exposure": 0.6},
                {"ticker": "2379", "reason": "網通晶片", "exposure": 0.5}
            ]
        elif trend == TechnologyTrend.AR_VR_DEVELOPMENT:
            beneficiaries = [
                {"ticker": "3008", "reason": "AR/VR鏡頭", "exposure": 0.7},
                {"ticker": "3406", "reason": "AR/VR鏡頭", "exposure": 0.6}
            ]
        
        return beneficiaries
    
    def _predict_adoption_timeline(self, trend_info: Dict) -> Dict[str, str]:
        """預測採用時間線"""
        adoption_rate = trend_info["adoption_rate"]
        
        if adoption_rate > 0.25:
            return {"current": "早期多數", "next_12m": "主流採用", "next_24m": "成熟階段"}
        elif adoption_rate > 0.10:
            return {"current": "早期採用", "next_12m": "早期多數", "next_24m": "主流採用"}
        else:
            return {"current": "創新者", "next_12m": "早期採用", "next_24m": "早期多數"}
    
    def generate_order_signals(self) -> List[OrderSignal]:
        """生成訂單信號 (模擬)"""
        print("生成訂單信號...")
        
        signals = []
        sample_companies = ["2330", "2454", "2382", "3231", "6669", "2317", "3008", "2308"]
        
        signal_templates = [
            ("order_increase", 0.8, "客戶追加訂單，產能利用率提升至95%"),
            ("order_increase", 0.7, "AI伺服器需求強勁，訂單能見度延長至2季"),
            ("order_decrease", 0.6, "消費電子需求放緩，訂單能見度縮短"),
            ("capacity_expansion", 0.7, "宣布擴產計劃，資本支出增加"),
            ("inventory_draw", 0.6, "庫存水位回到健康水準"),
            ("price_increase", 0.5, "產品漲價，毛利率有望提升")
        ]
        
        for company in sample_companies:
            # 根據公司特性生成相關信號
            if company in ["2330", "2382", "3231", "6669"]:
                # AI相關公司，訂單增加信號較強
                signal_type, base_strength, evidence = signal_templates[0]
                strength = base_strength * np.random.uniform(0.9, 1.1)
            elif company in ["2454", "3008"]:
                # 手機相關，可能有季節性
                idx = np.random.choice([0, 2])
                signal_type, base_strength, evidence = signal_templates[idx]
                strength = base_strength * np.random.uniform(0.8, 1.0)
            else:
                # 隨機信號
                idx = np.random.randint(0, len(signal_templates))
                signal_type, base_strength, evidence = signal_templates[idx]
                strength = base_strength * np.random.uniform(0.7, 1.0)
            
            signal = OrderSignal(
                company=company,
                signal_type=signal_type,
                strength=round(min(1.0, strength), 2),
                evidence=[evidence],
                confidence=round(strength * 0.9, 2),
                date=datetime.now().strftime("%Y-%m-%d")
            )
            signals.append(signal)
        
        # 按強度排序
        signals.sort(key=lambda x: x.strength * x.confidence, reverse=True)
        self.order_signals["latest"] = signals
        
        print(f"  生成 {len(signals)} 個訂單信號")
        return signals
    
    def monitor_supply_chain(self, focus_companies: List[str] = None) -> Dict[str, Dict]:
        """監測供應鏈狀況"""
        if focus_companies is None:
            focus_companies = ["2330", "2454", "2382", "3231", "6669"]
        
        print("監測供應鏈狀況...")
        supply_chain_analysis = {}
        
        for company in focus_companies:
            if company not in self.companies_data:
                self.fetch_company_data(company)
            
            company_data = self.companies_data.get(company)
            if not company_data:
                continue
            
            chain_position = self._analyze_supply_chain_position(company_data)
            key_suppliers = self._identify_key_suppliers(company)
            supply_chain_risk = self._assess_supply_chain_risk(key_suppliers)
            inventory_status = self._monitor_inventory_status(company)
            
            supply_chain_analysis[company] = {
                "company_name": company_data.name,
                "supply_chain_position": chain_position,
                "key_suppliers": key_suppliers,
                "key_customers": company_data.key_customers[:5],
                "supply_chain_risk": supply_chain_risk,
                "inventory_status": inventory_status,
                "bottlenecks": self._identify_bottlenecks(company_data),
                "recommendations": self._generate_recommendations(chain_position, supply_chain_risk)
            }
        
        self.supply_chain_data = supply_chain_analysis
        print(f"  分析完成 {len(supply_chain_analysis)} 家公司")
        return supply_chain_analysis
    
    def _analyze_supply_chain_position(self, company: ElectronicCompany) -> Dict[str, Any]:
        """分析供應鏈位置"""
        position_map = {
            "晶圓代工": "上游關鍵", "IC設計": "中上游", "封裝測試": "中游",
            "EMS": "下游組裝", "筆電代工": "下游組裝", "筆電/伺服器": "下游組裝",
            "伺服器": "下游系統", "手機鏡頭": "中游關鍵", "電源管理": "中游"
        }
        
        position = position_map.get(company.sub_sector, "中游")
        bargaining_power = min(1.0, company.technology_leadership / 10)
        
        return {
            "sector": company.sector,
            "sub_sector": company.sub_sector,
            "position": position,
            "bargaining_power": {"overall": bargaining_power}
        }
    
    def _identify_key_suppliers(self, ticker: str) -> List[Dict]:
        """識別關鍵供應商"""
        supplier_map = {
            "2330": [{"name": "ASML", "role": "EUV設備", "criticality": 0.9},
                    {"name": "Applied Materials", "role": "製程設備", "criticality": 0.7}],
            "2454": [{"name": "台積電", "role": "晶圓代工", "criticality": 0.8},
                    {"name": "日月光", "role": "封裝測試", "criticality": 0.6}],
            "2382": [{"name": "Intel/AMD", "role": "CPU", "criticality": 0.7},
                    {"name": "NVIDIA", "role": "GPU", "criticality": 0.8}],
            "6669": [{"name": "Intel/AMD", "role": "CPU", "criticality": 0.7},
                    {"name": "NVIDIA", "role": "GPU", "criticality": 0.9}]
        }
        return supplier_map.get(ticker, [{"name": "關鍵供應商", "role": "生產設備", "criticality": 0.5}])
    
    def _assess_supply_chain_risk(self, key_suppliers: List[Dict]) -> Dict[str, float]:
        """評估供應鏈風險"""
        concentration = len(key_suppliers)
        concentration_risk = 0.8 if concentration <= 2 else (0.5 if concentration <= 4 else 0.3)
        
        single_source = sum(1 for s in key_suppliers if s.get("criticality", 0) > 0.7) * 0.2
        single_source_risk = min(1.0, single_source)
        
        overall_risk = (concentration_risk + single_source_risk) / 2
        risk_level = "高" if overall_risk > 0.6 else ("中" if overall_risk > 0.4 else "低")
        
        return {
            "concentration_risk": concentration_risk,
            "single_source_risk": single_source_risk,
            "overall_risk": overall_risk,
            "risk_level": risk_level
        }
    
    def _monitor_inventory_status(self, ticker: str) -> Dict[str, Any]:
        """監測庫存狀況"""
        inventory_map = {
            "2330": {"level": "正常", "days": 45, "trend": "穩定"},
            "2454": {"level": "偏高", "days": 55, "trend": "改善中"},
            "2382": {"level": "正常", "days": 30, "trend": "穩定"},
            "3231": {"level": "正常", "days": 28, "trend": "穩定"},
            "6669": {"level": "偏低", "days": 20, "trend": "補庫存"}
        }
        
        status = inventory_map.get(ticker, {"level": "正常", "days": 40, "trend": "穩定"})
        return {
            "inventory_level": status["level"],
            "days_of_inventory": status["days"],
            "trend": status["trend"],
            "concern": "低" if status["level"] == "正常" else "中"
        }
    
    def _identify_bottlenecks(self, company: ElectronicCompany) -> List[str]:
        """識別供應鏈瓶頸"""
        bottlenecks = []
        
        if company.sector == "semiconductor":
            if company.sub_sector == "晶圓代工":
                bottlenecks.append("先進製程設備供應限制")
            elif company.sub_sector == "IC設計":
                bottlenecks.append("晶圓代工產能分配")
        elif company.sector == "assembly":
            bottlenecks.append("關鍵零組件供應")
            if "AI伺服器" in company.product_focus or "伺服器" in company.sub_sector:
                bottlenecks.append("GPU供應緊張")
        
        return bottlenecks[:3]
    
    def _generate_recommendations(self, position: Dict, risk: Dict) -> List[str]:
        """生成供應鏈建議"""
        recommendations = []
        
        if "上游" in position.get("position", ""):
            recommendations.append("加強技術壁壘，維持議價優勢")
        else:
            recommendations.append("與供應商建立策略合作")
        
        if risk.get("risk_level") == "高":
            recommendations.append("優先改善供應鏈集中度風險")
        
        recommendations.append("持續監控庫存水位與訂單變化")
        return recommendations
    
    def generate_investment_ideas(self, top_n: int = 10) -> List[Dict]:
        """生成投資想法"""
        print("生成投資想法...")
        
        investment_ideas = []
        
        # 從技術趨勢識別機會
        for trend_id, trend_info in self.technology_trends.items():
            for beneficiary in trend_info.get("beneficiaries", []):
                ticker = beneficiary.get("ticker", "")
                exposure = beneficiary.get("exposure", 0)
                
                if ticker and exposure > 0.4:
                    idea = {
                        "ticker": ticker,
                        "name": self._get_company_name(ticker),
                        "theme": trend_info["trend"],
                        "type": "trend_driven",
                        "catalyst": trend_info["description"][:50],
                        "time_horizon": "中期",
                        "upside_potential": round(trend_info["growth_forecast"] * exposure * 100, 1),
                        "risk_level": "中",
                        "score": 0
                    }
                    investment_ideas.append(idea)
        
        # 從訂單信號識別機會
        signals = self.order_signals.get("latest", [])
        for signal in signals:
            if signal.signal_type == "order_increase" and signal.strength > 0.7:
                idea = {
                    "ticker": signal.company,
                    "name": self._get_company_name(signal.company),
                    "theme": "訂單動能",
                    "type": "momentum_driven",
                    "catalyst": signal.evidence[0] if signal.evidence else "訂單增加",
                    "time_horizon": "短期",
                    "upside_potential": round(signal.strength * 30, 1),
                    "risk_level": "中",
                    "score": 0
                }
                investment_ideas.append(idea)
        
        # 評分並排序
        for idea in investment_ideas:
            idea["score"] = self._score_investment_idea(idea)
        
        investment_ideas.sort(key=lambda x: x["score"], reverse=True)
        
        # 去重
        seen = set()
        unique_ideas = []
        for idea in investment_ideas:
            if idea["ticker"] not in seen:
                seen.add(idea["ticker"])
                unique_ideas.append(idea)
        
        print(f"  生成 {len(unique_ideas[:top_n])} 個投資想法")
        return unique_ideas[:top_n]
    
    def _get_company_name(self, ticker: str) -> str:
        """獲取公司名稱"""
        for sector, info in self.electronics_database.items():
            if ticker in info["companies"]:
                return info["companies"][ticker]["name"]
        return ticker
    
    def _score_investment_idea(self, idea: Dict) -> float:
        """評分投資想法"""
        score = 0
        
        type_weights = {"trend_driven": 0.9, "momentum_driven": 0.7, "cycle_driven": 0.8}
        score += type_weights.get(idea.get("type", ""), 0.5) * 20
        score += min(30, idea.get("upside_potential", 0))
        
        risk = idea.get("risk_level", "中")
        score += {"低": 20, "中低": 15, "中": 10, "中高": 5, "高": 0}.get(risk, 10)
        
        horizon = idea.get("time_horizon", "中期")
        score += {"短期": 5, "中期": 15, "長期": 10}.get(horizon, 10)
        
        return min(100, score)
    
    def generate_report(self) -> str:
        """生成監測報告"""
        report = f"""
{'='*80}
📱 電子股趨勢與訂單監測報告
{'='*80}

生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
關注產業: {', '.join(self.focus_sectors)}

{'─'*80}
🔬 【技術趨勢分析】
{'─'*80}
"""
        
        for trend_id, trend_info in self.technology_trends.items():
            report += f"""
{trend_info['trend']}:
  採用率: {trend_info['adoption_rate']*100:.1f}%
  成長預測: {trend_info['growth_forecast']*100:.1f}%
  影響分數: {trend_info['impact_score']:.1f}/10
  關鍵公司: {', '.join(trend_info['key_companies'][:4])}
  描述: {trend_info['description']}
"""
        
        report += f"""
{'─'*80}
📦 【產品週期分析】
{'─'*80}
"""
        
        for product, cycle in self.product_cycles.items():
            report += f"""
{product}:
  當前階段: {cycle.current_phase.value}
  成長率: {cycle.growth_rate*100:.1f}%
  市場規模: ${cycle.market_size}億美元
  滲透率: {cycle.penetration_rate*100:.1f}%
  下個催化劑: {cycle.next_catalyst} ({cycle.catalyst_date})
"""
        
        report += f"""
{'─'*80}
📊 【訂單信號監測】
{'─'*80}
"""
        
        signals = self.order_signals.get("latest", [])
        if signals:
            for signal in signals[:5]:
                name = self._get_company_name(signal.company)
                report += f"""
{signal.company} ({name}):
  信號類型: {signal.signal_type}
  信號強度: {signal.strength:.2f}
  信心度: {signal.confidence:.2f}
  證據: {signal.evidence[0] if signal.evidence else 'N/A'}
"""
        else:
            report += "\n  暫無明顯訂單信號\n"
        
        report += f"""
{'─'*80}
🔗 【供應鏈分析】
{'─'*80}
"""
        
        for company, chain in list(self.supply_chain_data.items())[:3]:
            report += f"""
{company} ({chain['company_name']}):
  供應鏈位置: {chain['supply_chain_position']['position']}
  議價能力: {chain['supply_chain_position']['bargaining_power']['overall']:.2f}
  供應鏈風險: {chain['supply_chain_risk']['risk_level']}
  庫存狀況: {chain['inventory_status']['inventory_level']}
  瓶頸: {', '.join(chain['bottlenecks'][:2]) if chain['bottlenecks'] else '無'}
"""
        
        report += f"""
{'─'*80}
💡 【投資機會】
{'─'*80}
"""
        
        ideas = self.generate_investment_ideas(top_n=5)
        for i, idea in enumerate(ideas, 1):
            report += f"""
{i}. {idea['ticker']} ({idea['name']})
   主題: {idea['theme']}
   催化劑: {idea['catalyst'][:40]}...
   上行潛力: {idea['upside_potential']:.1f}%
   風險: {idea['risk_level']}
   評分: {idea['score']:.1f}/100
"""
        
        report += f"""
{'─'*80}
📋 【綜合建議】
{'─'*80}

1. 當前最強趨勢: {self._identify_strongest_trend()}
2. 最佳週期產品: {self._identify_best_cycle()}
3. 訂單動能最強: {self._identify_strongest_momentum()}

{'='*80}
"""
        return report
    
    def _identify_strongest_trend(self) -> str:
        """識別最強趨勢"""
        if not self.technology_trends:
            return "AI加速運算"
        strongest = max(self.technology_trends.values(), key=lambda x: x.get('impact_score', 0))
        return strongest.get('trend', 'AI加速運算')
    
    def _identify_best_cycle(self) -> str:
        """識別最佳週期"""
        growth_products = []
        for product, cycle in self.product_cycles.items():
            if cycle.current_phase in [ProductCyclePhase.INTRODUCTION, ProductCyclePhase.GROWTH]:
                growth_products.append(f"{product}({cycle.growth_rate*100:.0f}%)")
        return ", ".join(growth_products[:2]) if growth_products else "暫無明顯成長產品"
    
    def _identify_strongest_momentum(self) -> str:
        """識別最強動能"""
        signals = self.order_signals.get("latest", [])
        increase_signals = [s for s in signals if s.signal_type == "order_increase"]
        if increase_signals:
            strongest = max(increase_signals, key=lambda x: x.strength)
            return f"{strongest.company} ({self._get_company_name(strongest.company)})"
        return "暫無明顯動能"
    
    def batch_analyze(self, tickers: List[str] = None) -> List[Dict]:
        """批量分析電子股"""
        if tickers is None:
            # 預設分析主要電子股
            tickers = ["2330", "2454", "2382", "3231", "6669", "2317", "3008", "2308"]
        
        print(f"\n📱 批量分析 {len(tickers)} 檔電子股")
        print("=" * 60)
        
        results = []
        for ticker in tickers:
            try:
                company = self.fetch_company_data(ticker)
                results.append({
                    "ticker": ticker,
                    "name": company.name,
                    "sector": company.sector,
                    "sub_sector": company.sub_sector,
                    "tech_leadership": company.technology_leadership,
                    "order_visibility": f"{company.order_visibility}季",
                    "key_customers": ", ".join(company.key_customers[:2])
                })
            except Exception as e:
                print(f"  {ticker}: ❌ {e}")
        
        print("\n" + "=" * 60)
        print("✅ 批量分析完成!")
        return results
    
    def to_dict(self) -> Dict:
        """轉換為字典格式"""
        return {
            "focus_sectors": self.focus_sectors,
            "technology_trends": self.technology_trends,
            "product_cycles": {k: v.to_dict() for k, v in self.product_cycles.items()},
            "order_signals": {k: [s.to_dict() for s in v] for k, v in self.order_signals.items()},
            "supply_chain_data": self.supply_chain_data,
            "generated_date": datetime.now().isoformat()
        }


def main():
    """主程式"""
    print("=" * 80)
    print("📱 電子股趨勢與訂單監測系統 v2.0")
    print("=" * 80)
    
    # 初始化監測器
    monitor = ElectronicsMonitor()
    
    # 分析技術趨勢
    print("\n[步驟1] 分析技術趨勢...")
    trends = monitor.analyze_technology_trends()
    for trend_id, info in list(trends.items())[:3]:
        print(f"  • {info['trend']}: 影響分數 {info['impact_score']:.1f}/10")
    
    # 分析產品週期
    print("\n[步驟2] 分析產品週期...")
    products = ["smartphone", "ai_server", "electric_vehicle", "ar_vr"]
    for product in products:
        cycle = monitor.analyze_product_cycle(product)
        print(f"  • {product}: {cycle.current_phase.value} (成長 {cycle.growth_rate*100:.0f}%)")
    
    # 生成訂單信號
    print("\n[步驟3] 生成訂單信號...")
    signals = monitor.generate_order_signals()
    for s in signals[:3]:
        name = monitor._get_company_name(s.company)
        print(f"  • {s.company} ({name}): {s.signal_type} 強度 {s.strength:.2f}")
    
    # 監測供應鏈
    print("\n[步驟4] 監測供應鏈...")
    supply_chain = monitor.monitor_supply_chain()
    for company, info in list(supply_chain.items())[:3]:
        print(f"  • {company}: {info['supply_chain_risk']['risk_level']}風險")
    
    # 生成投資想法
    print("\n[步驟5] 生成投資想法...")
    ideas = monitor.generate_investment_ideas(top_n=5)
    for i, idea in enumerate(ideas[:3], 1):
        print(f"  {i}. {idea['ticker']} ({idea['name']}): {idea['theme']} 評分 {idea['score']:.0f}")
    
    # 生成報告
    print("\n[步驟6] 生成監測報告...")
    report = monitor.generate_report()
    print(report)
    
    print("\n✅ 電子股監測完成!")
    
    return monitor


if __name__ == "__main__":
    main()
