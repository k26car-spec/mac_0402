"""
投資信號產生器 v1.0
整合所有模組分析，輸出買進/賣出/持有信號 + 配置建議

系統名稱：循環驅動多因子投資系統
最終模組：投資信號產生器
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import sys
import os
import warnings

warnings.filterwarnings('ignore')

# 加入模組路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from technical_timing.technical_analyzer import TechnicalAnalyzer
except ImportError:
    TechnicalAnalyzer = None

try:
    from asset_allocation.asset_allocator import AssetAllocator, RiskProfile
except ImportError:
    AssetAllocator = None
    RiskProfile = None

try:
    from electronics_monitor.electronics_monitor import ElectronicsMonitor
except ImportError:
    ElectronicsMonitor = None

# 新增: 總經循環模組
try:
    from economic_cycle import EconomicCycleDetector
except ImportError:
    EconomicCycleDetector = None

# 新增: 產業鏈分析模組
try:
    from industry_chain.industry_chain_analyzer import IndustryChainAnalyzer
except ImportError:
    IndustryChainAnalyzer = None

# 新增: 財報篩選模組
try:
    from financial_screener.financial_screener import FinancialScreener
except ImportError:
    FinancialScreener = None


class SignalType(Enum):
    """信號類型"""
    STRONG_BUY = "強力買進"
    BUY = "買進"
    HOLD = "持有"
    SELL = "賣出"
    STRONG_SELL = "強力賣出"


class TimeHorizon(Enum):
    """投資期限"""
    SHORT_TERM = "短期 (1-3個月)"
    MEDIUM_TERM = "中期 (3-12個月)"
    LONG_TERM = "長期 (1年以上)"


@dataclass
class InvestmentSignal:
    """投資信號"""
    ticker: str
    name: str
    signal: SignalType
    confidence: float  # 0-1
    score: float  # 0-100
    
    # 分析來源 (6大維度) - 必填
    technical_signal: str
    technical_score: float       # 技術面分數
    trend_exposure: float        # 趨勢曝險分數
    order_momentum: float        # 訂單動能分數
    
    # 建議 - 必填
    action: str
    target_weight: float  # 建議配置比例
    stop_loss: float  # 停損價
    take_profit: float  # 停利價
    time_horizon: TimeHorizon
    
    # 6維度額外分數 - 有預設值
    economic_cycle_score: float = 50.0  # 總經循環分數
    industry_power_score: float = 50.0  # 產業定價權分數
    financial_score: float = 50.0       # 財報健康分數
    
    # 理由 - 有預設值
    reasons: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    
    def to_dict(self):
        result = asdict(self)
        result['signal'] = self.signal.value
        result['time_horizon'] = self.time_horizon.value
        return result


@dataclass
class PortfolioRecommendation:
    """投資組合建議"""
    risk_profile: str
    total_capital: float
    market_condition: str
    
    # 資產配置
    equity_allocation: float
    bond_allocation: float
    cash_allocation: float
    alternative_allocation: float
    
    # 個股建議
    stock_recommendations: List[InvestmentSignal]
    
    # ETF建議
    etf_recommendations: List[Dict]
    
    # 整體建議
    overall_action: str
    key_themes: List[str]
    risk_warnings: List[str]
    
    # 有預設值的欄位放最後
    economic_cycle_stage: str = "未知"
    generated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def to_dict(self):
        result = asdict(self)
        result['stock_recommendations'] = [s.to_dict() for s in self.stock_recommendations]
        return result


class SignalGenerator:
    """
    投資信號產生器 v2.0 (全模組整合版)
    整合 6 大模組：
    1. 總經循環定位
    2. 產業鏈與定價權分析
    3. 財報與營收量化篩選
    4. 技術面與線型時機
    5. 資產配置與風險控制
    6. 電子股趨勢與訂單監測
    """
    
    def __init__(self, risk_profile: str = "MODERATE", 
                 initial_capital: float = 1000000):
        """
        初始化信號產生器
        
        Parameters:
        -----------
        risk_profile : str
            風險承受度 (CONSERVATIVE, MODERATE, AGGRESSIVE)
        initial_capital : float
            初始資金
        """
        self.risk_profile = risk_profile
        self.initial_capital = initial_capital
        
        # === 初始化 6 大子模組 ===
        # 模組1: 總經循環定位
        self.economic_cycle = EconomicCycleDetector() if EconomicCycleDetector else None
        # 模組2: 產業鏈分析
        self.industry_analyzer = IndustryChainAnalyzer(industry="ai_server") if IndustryChainAnalyzer else None
        # 模組3: 財報篩選
        self.financial_screener = FinancialScreener(market="TW") if FinancialScreener else None
        # 模組4: 技術分析
        self.technical_analyzer = TechnicalAnalyzer(market="TW") if TechnicalAnalyzer else None
        # 模組5: 資產配置
        self.asset_allocator = AssetAllocator(risk_profile, initial_capital) if AssetAllocator else None
        # 模組6: 電子股監測
        self.electronics_monitor = ElectronicsMonitor() if ElectronicsMonitor else None
        
        # 緩存總經循環數據
        self._economic_cycle_data = None
        self._industry_data_cache = {}
        self._financial_data_cache = {}
        
        # === 新的 6 維度權重配置 ===
        self.signal_weights = {
            "technical": 0.25,         # 技術面分析權重
            "economic_cycle": 0.15,    # 總經循環權重
            "industry_power": 0.15,    # 產業定價權權重
            "financial": 0.15,         # 財報健康權重
            "trend": 0.15,             # 趨勢曝險權重
            "order_momentum": 0.15     # 訂單動能權重
        }
        
        # 信號閾值
        self.thresholds = {
            "strong_buy": 80,
            "buy": 60,
            "hold_upper": 60,
            "hold_lower": 40,
            "sell": 40,
            "strong_sell": 20
        }
        
        # 股票資料庫
        self.stock_database = self._initialize_stock_database()
        
        # 股票名稱緩存
        self._stock_name_cache = {}
        # 分析結果緩存
        self.analysis_cache = {}
    
    def _initialize_stock_database(self) -> Dict[str, Dict]:
        """初始化股票資料庫"""
        return {
            # ========== AI 伺服器概念股 ==========
            "2382": {"name": "廣達", "sector": "電子", "type": "AI伺服器", "theme": ["AI伺服器", "雲端運算"]},
            "3231": {"name": "緯創", "sector": "電子", "type": "AI伺服器", "theme": ["AI伺服器", "筆電"]},
            "6669": {"name": "緯穎", "sector": "電子", "type": "AI伺服器", "theme": ["AI伺服器", "雲端運算"]},
            "2356": {"name": "英業達", "sector": "電子", "type": "AI伺服器", "theme": ["AI伺服器", "筆電"]},
            "3017": {"name": "奇鑫", "sector": "電子", "type": "AI伺服器", "theme": ["AI伺服器", "機殼"]},
            "2376": {"name": "技嘉", "sector": "電子", "type": "AI伺服器", "theme": ["AI伺服器", "主機板"]},
            "3443": {"name": "創意", "sector": "半導體", "type": "ASIC", "theme": ["AI伺服器", "IC設計"]},
            "6515": {"name": "穎崴", "sector": "電子", "type": "測試介面", "theme": ["AI伺服器", "半導體設備"]},
            "3661": {"name": "世芯-KY", "sector": "半導體", "type": "ASIC", "theme": ["AI伺服器", "IC設計"]},
            "6104": {"name": "創惟", "sector": "半導體", "type": "USB IC", "theme": ["AI伺服器"]},
            
            # ========== 矽光子概念股 ==========
            "3324": {"name": "雙鴻", "sector": "電子", "type": "散熱", "theme": ["矽光子", "散熱"]},
            "6285": {"name": "啟碁", "sector": "電子", "type": "通訊", "theme": ["矽光子", "5G"]},
            "3037": {"name": "欣興", "sector": "電子", "type": "PCB", "theme": ["矽光子", "IC載板"]},
            "2327": {"name": "國巨", "sector": "被動元件", "type": "MLCC", "theme": ["矽光子", "被動元件"]},
            "3533": {"name": "嘉澤", "sector": "電子", "type": "連接器", "theme": ["矽光子", "AI伺服器"]},
            "6409": {"name": "旭隼", "sector": "電子", "type": "電源供應器", "theme": ["矽光子", "電源"]},
            "3105": {"name": "穩懋", "sector": "半導體", "type": "砷化鎵", "theme": ["矽光子", "化合物半導體"]},
            "8299": {"name": "群聯", "sector": "半導體", "type": "IC設計", "theme": ["矽光子", "記憶體控制"]},
            "2449": {"name": "京元電子", "sector": "半導體", "type": "測試", "theme": ["矽光子", "封測"]},
            "6446": {"name": "藥華藥", "sector": "電子", "type": "光通訊", "theme": ["矽光子"]},
            
            # ========== 半導體 ==========
            "2330": {"name": "台積電", "sector": "半導體", "type": "晶圓代工", "theme": ["AI伺服器", "半導體"]},
            "2454": {"name": "聯發科", "sector": "半導體", "type": "IC設計", "theme": ["AI伺服器", "5G"]},
            "2303": {"name": "聯電", "sector": "半導體", "type": "晶圓代工", "theme": ["半導體"]},
            "3034": {"name": "聯詠", "sector": "半導體", "type": "IC設計", "theme": ["半導體", "顯示器"]},
            "2379": {"name": "瑞昱", "sector": "半導體", "type": "IC設計", "theme": ["半導體", "網通"]},
            "3711": {"name": "日月光投控", "sector": "半導體", "type": "封測", "theme": ["半導體", "封測"]},
            "2408": {"name": "南亞科", "sector": "半導體", "type": "DRAM", "theme": ["半導體", "記憶體"]},
            "3529": {"name": "力旺", "sector": "半導體", "type": "IP", "theme": ["半導體", "記憶體IP"]},
            
            # ========== 組裝代工 ==========
            "2317": {"name": "鴻海", "sector": "電子", "type": "EMS", "theme": ["AI伺服器", "電動車"]},
            "4938": {"name": "和碩", "sector": "電子", "type": "組裝", "theme": ["筆電", "消費電子"]},
            "2324": {"name": "仁寶", "sector": "電子", "type": "筆電", "theme": ["筆電"]},
            
            # ========== 光學/鏡頭 ==========
            "3008": {"name": "大立光", "sector": "光學", "type": "鏡頭", "theme": ["光學", "手機"]},
            "3406": {"name": "玉晶光", "sector": "光學", "type": "鏡頭", "theme": ["光學", "手機"]},
            
            # ========== 電源/散熱 ==========
            "2308": {"name": "台達電", "sector": "電子", "type": "電源", "theme": ["AI伺服器", "電動車", "電源"]},
            "6461": {"name": "益得", "sector": "電子", "type": "電源模組", "theme": ["AI伺服器", "電源"]},
            
            # ========== 網通/5G ==========
            "2345": {"name": "智邦", "sector": "電子", "type": "網通", "theme": ["AI伺服器", "網通", "低軌衛星"]},
            "8086": {"name": "宏捷科", "sector": "半導體", "type": "砷化鎵", "theme": ["5G", "化合物半導體"]},
            
            # ========== 國防軍工 ==========
            "2634": {"name": "漢翔", "sector": "航太", "type": "國防", "theme": ["國防軍工", "航太"]},
            "2208": {"name": "台船", "sector": "造船", "type": "國防", "theme": ["國防軍工", "造船"]},
            "2231": {"name": "為升", "sector": "電子", "type": "國防", "theme": ["國防軍工", "車用電子"]},
            "1476": {"name": "儒鴻", "sector": "紡織", "type": "軍用紡織", "theme": ["國防軍工"]},
            "2023": {"name": "燁興", "sector": "鋼鐵", "type": "軍用鋼材", "theme": ["國防軍工"]},
            "2206": {"name": "三陽工業", "sector": "汽車", "type": "軍用車輛", "theme": ["國防軍工"]},
            "1513": {"name": "中興電", "sector": "電機", "type": "國防電子", "theme": ["國防軍工", "電力"]},
            
            # ========== 機器人 ==========
            "2049": {"name": "上銀", "sector": "機械", "type": "傳動元件", "theme": ["機器人", "自動化"]},
            "4523": {"name": "永彰", "sector": "機電", "type": "工業電機", "theme": ["機器人", "自動化"]},
            "3515": {"name": "華擎", "sector": "電子", "type": "工業電腦", "theme": ["機器人", "AI伺服器"]},
            "6121": {"name": "新普", "sector": "電子", "type": "電池模組", "theme": ["機器人", "電池"]},
            "1536": {"name": "和大", "sector": "汽車零件", "type": "傳動系統", "theme": ["機器人", "電動車"]},
            "2059": {"name": "川湖", "sector": "機械", "type": "滑軌", "theme": ["機器人", "AI伺服器"]},
            "1558": {"name": "伸興", "sector": "電機", "type": "縫紉機", "theme": ["機器人"]},
            
            # ========== 低軌衛星 ==========
            "3704": {"name": "合勤控", "sector": "網通", "type": "網通設備", "theme": ["低軌衛星", "5G"]},
            "2455": {"name": "全新", "sector": "半導體", "type": "砷化鎵", "theme": ["低軌衛星", "5G"]},
            "3682": {"name": "亞太電", "sector": "電信", "type": "衛星通訊", "theme": ["低軌衛星"]},
            "4977": {"name": "眾達-KY", "sector": "電子", "type": "射頻元件", "theme": ["低軌衛星", "5G"]},
            "3450": {"name": "聯鈞", "sector": "電子", "type": "光通訊", "theme": ["低軌衛星", "矽光子"]},
            "2498": {"name": "宏達電", "sector": "電子", "type": "通訊設備", "theme": ["低軌衛星"]},
            
            # ========== 補充常用股票 ==========
            "1815": {"name": "富喬", "sector": "電子", "type": "玻纖", "theme": ["5G", "PCB"]},
            "8039": {"name": "台虹", "sector": "電子", "type": "軟板材料", "theme": ["5G", "消費電子"]},
            "3030": {"name": "德律", "sector": "電子", "type": "測試設備", "theme": ["半導體", "自動化"]},
            "8074": {"name": "鍘發", "sector": "電子", "type": "印刷電路板", "theme": ["5G", "PCB"]},
            "1589": {"name": "永冠-KY", "sector": "機械", "type": "風電鑄件", "theme": ["綠能"]},
            "3653": {"name": "健策", "sector": "電子", "type": "散熱", "theme": ["AI伺服器", "散熱"]},
            "4919": {"name": "新唐", "sector": "半導體", "type": "微控制器", "theme": ["車用電子"]},
            "5274": {"name": "信驊", "sector": "半導體", "type": "伺服器晶片", "theme": ["AI伺服器", "IC設計"]},
            "6239": {"name": "力成", "sector": "半導體", "type": "封測", "theme": ["封測", "記憶體"]},
            "6770": {"name": "力積電", "sector": "半導體", "type": "晶圓代工", "theme": ["半導體"]},
            "3702": {"name": "大聯大", "sector": "電子", "type": "IC通路", "theme": ["半導體"]},
            "8155": {"name": "漢微科", "sector": "半導體", "type": "檢測設備", "theme": ["半導體", "設備"]},
            "6510": {"name": "精測", "sector": "半導體", "type": "測試", "theme": ["半導體", "設備"]},
            "3529": {"name": "力旺", "sector": "半導體", "type": "IP", "theme": ["半導體"]},
            "6547": {"name": "高端疫苗", "sector": "生技", "type": "疫苗", "theme": ["生技"]},
            "3035": {"name": "智原", "sector": "半導體", "type": "ASIC", "theme": ["IC設計"]},
            "6756": {"name": "威鋒電子", "sector": "半導體", "type": "USB IC", "theme": ["消費電子"]},
            
            # ========== ETF ==========
            "0050": {"name": "元大台灣50", "sector": "ETF", "type": "指數", "theme": ["ETF"]},
            "0056": {"name": "元大高股息", "sector": "ETF", "type": "高股息", "theme": ["ETF"]},
            "00878": {"name": "國泰永續高股息", "sector": "ETF", "type": "ESG高股息", "theme": ["ETF"]}
        }
    
    # 預設掃描清單 (按主題分類)
    THEME_STOCKS = {
        "AI伺服器": ["2382", "3231", "6669", "2356", "3017", "2376", "3443", "6515", "3661", "2330", "2317", "2308", "2345"],
        "矽光子": ["3324", "6285", "3037", "2327", "3533", "6409", "3105", "8299", "2449", "3450"],
        "半導體": ["2330", "2454", "2303", "3034", "2379", "3711", "2408", "3529", "3443", "3661"],
        "電動車": ["2317", "2308", "2327", "3037", "1536"],
        "5G網通": ["2454", "2379", "6285", "2345", "8086", "3704", "2455"],
        "國防軍工": ["2634", "2208", "2231", "1476", "2023", "2206", "1513"],
        "機器人": ["2317", "2049", "4523", "3515", "6121", "1536", "2059", "1558"],
        "低軌衛星": ["3704", "2455", "3682", "6285", "2345", "4977", "3450", "2498"],
    }
    
    def generate_stock_signal(self, ticker: str) -> InvestmentSignal:
        """
        生成單一股票的投資信號 (6維度整合版)
        
        Parameters:
        -----------
        ticker : str
            股票代號
            
        Returns:
        --------
        InvestmentSignal: 投資信號
        """
        stock_info = self.stock_database.get(ticker, {"name": ticker, "sector": "未知", "type": "未知"})
        
        # 如果名稱等於代碼，嘗試從 API 獲取真實名稱
        if stock_info["name"] == ticker:
            stock_name = self._get_stock_name_from_api(ticker)
            if stock_name:
                stock_info["name"] = stock_name
        
        # === 6大維度評分 ===
        
        # 1. 技術分析 (模組4)
        technical_score, technical_signal, tech_data = self._get_technical_analysis(ticker)
        
        # 2. 總經循環評分 (模組1)
        economic_cycle_score = self._get_economic_cycle_score()
        
        # 3. 產業定價權評分 (模組2)
        industry_power_score = self._get_industry_power_score(ticker, stock_info)
        
        # 4. 財報健康評分 (模組3)
        financial_score = self._get_financial_score(ticker)
        
        # 5. 趨勢曝險 (模組6)
        trend_exposure = self._get_trend_exposure(ticker)
        
        # 6. 訂單動能 (模組6)
        order_momentum = self._get_order_momentum(ticker)
        
        # 7. 計算綜合分數 (6維度加權)
        composite_score = self._calculate_composite_score_v2(
            technical_score, economic_cycle_score, industry_power_score,
            financial_score, trend_exposure, order_momentum
        )
        
        # 8. 決定信號類型
        signal_type = self._determine_signal_type(composite_score)
        
        # 9. 計算信心度 (6維度)
        confidence = self._calculate_confidence_v2(
            technical_score, economic_cycle_score, industry_power_score,
            financial_score, trend_exposure, order_momentum
        )
        
        # 10. 生成建議
        action, target_weight = self._generate_action_recommendation(signal_type, confidence)
        
        # 11. 計算停損停利
        current_price = tech_data.get("current_price", 100)
        stop_loss, take_profit = self._calculate_price_targets(signal_type, current_price, tech_data)
        
        # 12. 決定投資期限
        time_horizon = self._determine_time_horizon(signal_type, trend_exposure)
        
        # 13. 生成理由 (6維度)
        reasons = self._generate_signal_reasons_v2(
            signal_type, technical_signal, tech_data, 
            economic_cycle_score, industry_power_score, financial_score,
            trend_exposure, order_momentum
        )
        
        # 14. 風險提示
        risks = self._generate_risk_warnings(ticker, signal_type, tech_data)
        
        return InvestmentSignal(
            ticker=ticker,
            name=stock_info["name"],
            signal=signal_type,
            confidence=confidence,
            score=composite_score,
            technical_signal=technical_signal,
            technical_score=technical_score,
            trend_exposure=trend_exposure,
            order_momentum=order_momentum,
            economic_cycle_score=economic_cycle_score,
            industry_power_score=industry_power_score,
            financial_score=financial_score,
            action=action,
            target_weight=target_weight,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_horizon=time_horizon,
            reasons=reasons,
            risks=risks
        )
    
    def _get_economic_cycle_score(self) -> float:
        """獲取總經循環評分 (模組1)
        
        注意: 為加速分析，預設使用快速模式（不從 API 獲取即時數據）
        如需獲取即時總經數據，請呼叫 refresh_economic_data()
        """
        # 使用已緩存的數據
        if self._economic_cycle_data is not None:
            stage = self._economic_cycle_data.get("stage", "unknown")
            stage_scores = {
                "recovery": 80,      # 復甦期 - 最佳進場時機
                "expansion": 70,     # 擴張期 - 仍可持有
                "peak": 40,          # 高峰期 - 小心
                "contraction": 20,   # 收縮期 - 避開
                "unknown": 50
            }
            return stage_scores.get(stage, 50)
        
        # 預設: 當前處於擴張期末段（2024年底市場判斷）
        # TODO: 可手動更新或呼叫 refresh_economic_data() 獲取即時數據
        self._economic_cycle_data = {
            "stage": "expansion",
            "confidence": 0.65,
            "scores": {}
        }
        return 65.0  # 擴張期偏高點
    
    def _get_stock_name_from_api(self, ticker: str) -> str:
        """從 API 自動獲取股票名稱 (使用現有的 stock_names 模組)"""
        # 優先使用緩存
        if ticker in self._stock_name_cache:
            return self._stock_name_cache[ticker]
        
        # 清理代碼
        clean_ticker = ticker.replace('.TW', '').replace('.TWO', '')
        
        # 使用現有的 stock_names 模組自動獲取
        try:
            import sys
            sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')
            from stock_names import get_stock_name
            
            name = get_stock_name(clean_ticker)
            if name and name != clean_ticker:
                self._stock_name_cache[clean_ticker] = name
                return name
        except Exception as e:
            pass
        
        # 備援：使用 tw-stocks API (後端)
        try:
            import requests
            response = requests.get(
                f"http://localhost:8000/api/tw-stocks/search?q={clean_ticker}&limit=1",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                stocks = data.get("stocks", [])
                if stocks:
                    for stock in stocks:
                        if stock.get("symbol") == clean_ticker:
                            name = stock.get("name", clean_ticker)
                            self._stock_name_cache[clean_ticker] = name
                            return name
        except:
            pass
        
        # 返回代號本身
        return clean_ticker
    
    def _get_industry_power_score(self, ticker: str, stock_info: Dict) -> float:
        """獲取產業定價權評分 (模組2) - 使用 yfinance 真實數據"""
        # 優先使用緩存
        if ticker in self._industry_data_cache:
            return self._industry_data_cache[ticker]
        
        try:
            import yfinance as yf
            
            # 同時支援上市和上櫃
            info = None
            for suffix in ['.TW', '.TWO']:
                try:
                    symbol = f"{ticker}{suffix}"
                    stock = yf.Ticker(symbol)
                    info = stock.info
                    if info.get('regularMarketPrice') or info.get('currentPrice'):
                        break
                except:
                    continue
            
            score = 50.0  # 基礎分數
            
            # 1. 毛利率 (Gross Margin) - 高毛利 = 高定價權
            gross_margin = info.get('grossMargins', 0) or 0
            if gross_margin > 0.4:
                score += 20  # 毛利率 > 40%
            elif gross_margin > 0.25:
                score += 12
            elif gross_margin > 0.15:
                score += 5
            
            # 2. 營業利潤率 (Operating Margin)
            operating_margin = info.get('operatingMargins', 0) or 0
            if operating_margin > 0.2:
                score += 15
            elif operating_margin > 0.1:
                score += 8
            
            # 3. 市值規模 - 大公司通常有更強定價權
            market_cap = info.get('marketCap', 0) or 0
            if market_cap > 1e12:  # > 1兆
                score += 15
            elif market_cap > 1e11:  # > 1000億
                score += 10
            elif market_cap > 1e10:  # > 100億
                score += 5
            
            score = min(100, max(0, score))
            self._industry_data_cache[ticker] = score
            print(f"  {ticker} 定價權: {score:.0f} (毛利率:{gross_margin*100:.1f}%)")
            return score
            
        except Exception as e:
            pass  # 靜默失敗，使用備援
        
        # 備援: 根據股票類型給予預估分數
        type_scores = {
            "晶圓代工": 85, "ASIC": 80, "IC設計": 70, "AI伺服器": 65,
            "EMS": 50, "組裝": 45, "PCB": 55, "被動元件": 50,
        }
        stock_type = stock_info.get("type", "其他")
        score = type_scores.get(stock_type, 50)
        self._industry_data_cache[ticker] = score
        return score
    
    def _get_financial_score(self, ticker: str) -> float:
        """獲取財報健康評分 (模組3) - 使用 yfinance 真實數據"""
        # 優先使用緩存
        if ticker in self._financial_data_cache:
            return self._financial_data_cache[ticker]
        
        try:
            import yfinance as yf
            
            # 同時支援上市和上櫃
            info = None
            for suffix in ['.TW', '.TWO']:
                try:
                    symbol = f"{ticker}{suffix}"
                    stock = yf.Ticker(symbol)
                    info = stock.info
                    if info.get('regularMarketPrice') or info.get('currentPrice'):
                        break
                except:
                    continue
            
            if not info:
                return 50.0  # 無法獲取，返回中性分數
            
            score = 50.0  # 基礎分數
            
            # 1. ROE (Return on Equity)
            roe = info.get('returnOnEquity', 0) or 0
            if roe > 0.2:
                score += 15  # ROE > 20%
            elif roe > 0.12:
                score += 10
            elif roe > 0.08:
                score += 5
            elif roe < 0:
                score -= 10  # 負ROE扣分
            
            # 2. 負債比率 (Debt to Equity)
            debt_to_equity = info.get('debtToEquity', 0) or 0
            if debt_to_equity < 50:
                score += 10  # 低負債
            elif debt_to_equity < 100:
                score += 5
            elif debt_to_equity > 200:
                score -= 10  # 高負債扣分
            
            # 3. 營收成長率 (Revenue Growth)
            revenue_growth = info.get('revenueGrowth', 0) or 0
            if revenue_growth > 0.2:
                score += 15  # 成長 > 20%
            elif revenue_growth > 0.1:
                score += 10
            elif revenue_growth > 0:
                score += 5
            elif revenue_growth < -0.1:
                score -= 10  # 衰退扣分
            
            # 4. 自由現金流 (Free Cash Flow)
            free_cash_flow = info.get('freeCashflow', 0) or 0
            if free_cash_flow > 0:
                score += 10  # 正現金流
            else:
                score -= 5  # 負現金流
            
            score = min(100, max(0, score))
            self._financial_data_cache[ticker] = score
            print(f"  {ticker} 財報: {score:.0f} (ROE:{roe*100:.1f}%)")
            return score
            
        except Exception as e:
            pass  # 靜默失敗
        
        # 預設中性分數
        return 50.0
    
    def _get_technical_analysis(self, ticker: str) -> Tuple[float, str, Dict]:
        """獲取技術分析結果"""
        tech_data = {"current_price": 100, "support": 95, "resistance": 110}
        
        if self.technical_analyzer:
            try:
                # 使用技術分析模組
                plan = self.technical_analyzer.generate_trading_plan(ticker)
                
                signal = plan.get("final_signal", "hold")
                strength = plan.get("signal_strength", 0.5)
                
                # 轉換為分數 (0-100)
                signal_scores = {
                    "strong_buy": 90, "buy": 70, "hold": 50, "sell": 30, "strong_sell": 10
                }
                score = signal_scores.get(signal, 50)
                
                tech_data = {
                    "current_price": plan.get("current_price", 100),
                    "support": plan.get("risk_management", {}).get("stop_loss", 95),
                    "resistance": plan.get("risk_management", {}).get("take_profit", 110),
                    "position_zone": plan.get("position_analysis", {}).get("zone", "中間"),
                    "position_score": plan.get("position_analysis", {}).get("score", 50),
                    "rsi": plan.get("indicators_summary", {}).get("rsi", 50),
                    "trend": plan.get("indicators_summary", {}).get("trend", "盤整")
                }
                
                return score, signal, tech_data
                
            except Exception as e:
                print(f"  技術分析 {ticker} 錯誤: {e}")
        
        # 模擬數據
        score = np.random.uniform(30, 70)
        signal = "hold"
        if score > 65:
            signal = "buy"
        elif score < 35:
            signal = "sell"
        
        return score, signal, tech_data
    
    def _get_trend_exposure(self, ticker: str) -> float:
        """獲取趨勢曝險分數 (0-100)"""
        if self.electronics_monitor:
            try:
                # 分析技術趨勢
                if not self.electronics_monitor.technology_trends:
                    self.electronics_monitor.analyze_technology_trends()
                
                # 計算曝險
                exposure = 50  # 基礎分數
                
                for trend_id, trend_info in self.electronics_monitor.technology_trends.items():
                    for beneficiary in trend_info.get("beneficiaries", []):
                        if beneficiary.get("ticker") == ticker:
                            # 根據趨勢影響分數和曝險度計算
                            trend_impact = trend_info.get("impact_score", 5) / 10
                            company_exposure = beneficiary.get("exposure", 0.5)
                            exposure += trend_impact * company_exposure * 50
                
                return min(100, exposure)
                
            except Exception as e:
                print(f"  趨勢分析 {ticker} 錯誤: {e}")
        
        # 預設曝險 (根據股票類型)
        stock_info = self.stock_database.get(ticker, {})
        if stock_info.get("type") in ["AI伺服器", "晶圓代工"]:
            return np.random.uniform(60, 80)
        elif stock_info.get("type") in ["IC設計", "電源"]:
            return np.random.uniform(50, 70)
        else:
            return np.random.uniform(40, 60)
    
    def _get_order_momentum(self, ticker: str) -> float:
        """
        獲取訂單動能分數 (0-100)
        
        使用多因子模型評估:
        - 營收成長率 (30%)
        - 法人買賣超 (25%)
        - 大單比率 (20%)
        - 產業趨勢 (15%)
        - 價格動能 (10%)
        """
        # 優先使用新的訂單動能評估器
        try:
            import asyncio
            from order_momentum_evaluator import get_order_momentum_evaluator
            
            evaluator = get_order_momentum_evaluator()
            stock_info = self.stock_database.get(ticker, {})
            stock_type = stock_info.get("type", "default")
            
            # 同步執行異步函數
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(evaluator.evaluate(ticker, stock_type))
            loop.close()
            
            print(f"  {ticker} 訂單動能: {result.score:.0f} (信心度: {result.confidence:.2f})")
            return result.score
            
        except Exception as e:
            pass  # 新評估器失敗時使用備援
        
        # 備援: 使用舊版 ElectronicsMonitor
        if self.electronics_monitor:
            try:
                if "latest" not in self.electronics_monitor.order_signals:
                    self.electronics_monitor.generate_order_signals()
                
                signals = self.electronics_monitor.order_signals.get("latest", [])
                
                for signal in signals:
                    if signal.company == ticker:
                        if signal.signal_type == "order_increase":
                            return signal.strength * 100
                        elif signal.signal_type == "order_decrease":
                            return (1 - signal.strength) * 50
                
            except Exception as e:
                print(f"  訂單分析 {ticker} 錯誤: {e}")
        
        # 最終備援: 根據股票類型
        stock_info = self.stock_database.get(ticker, {})
        stock_type = stock_info.get("type", "其他")
        
        type_scores = {
            "AI伺服器": 75,
            "晶圓代工": 65,
            "IC設計": 60,
            "封測": 55,
            "PCB": 55,
            "被動元件": 50,
            "default": 50
        }
        
        return type_scores.get(stock_type, type_scores["default"])
    
    def _calculate_composite_score(self, technical: float, trend: float, order: float) -> float:
        """計算綜合分數 (舊版 3 維度)"""
        score = (
            technical * self.signal_weights["technical"] +
            trend * self.signal_weights["trend"] +
            order * self.signal_weights["order_momentum"] +
            50 * 0.15  # 基本面預設中性
        )
        return round(min(100, max(0, score)), 1)
    
    def _calculate_composite_score_v2(self, technical: float, economic: float, 
                                       industry: float, financial: float,
                                       trend: float, order: float) -> float:
        """計算綜合分數 (新版 6 維度)"""
        score = (
            technical * self.signal_weights["technical"] +
            economic * self.signal_weights["economic_cycle"] +
            industry * self.signal_weights["industry_power"] +
            financial * self.signal_weights["financial"] +
            trend * self.signal_weights["trend"] +
            order * self.signal_weights["order_momentum"]
        )
        return round(min(100, max(0, score)), 1)
    
    def _determine_signal_type(self, score: float) -> SignalType:
        """決定信號類型"""
        if score >= self.thresholds["strong_buy"]:
            return SignalType.STRONG_BUY
        elif score >= self.thresholds["buy"]:
            return SignalType.BUY
        elif score > self.thresholds["sell"]:
            return SignalType.HOLD
        elif score > self.thresholds["strong_sell"]:
            return SignalType.SELL
        else:
            return SignalType.STRONG_SELL
    
    def _calculate_confidence(self, technical: float, trend: float, order: float) -> float:
        """計算信心度 (舊版)"""
        scores = [technical, trend, order]
        avg = np.mean(scores)
        std = np.std(scores)
        consistency = 1 - (std / 50)
        return min(0.95, max(0.3, consistency * (avg / 100)))
    
    def _calculate_confidence_v2(self, technical: float, economic: float,
                                  industry: float, financial: float,
                                  trend: float, order: float) -> float:
        """計算信心度 (新版 6 維度)"""
        scores = [technical, economic, industry, financial, trend, order]
        avg = np.mean(scores)
        std = np.std(scores)
        
        # 標準差越小，一致性越高
        consistency = max(0, 1 - std / 50)
        
        # 分數越極端（接近0或100），信心度越高
        extremity = abs(avg - 50) / 50
        
        confidence = 0.6 * consistency + 0.4 * extremity
        return round(min(1.0, max(0.3, confidence)), 2)
    
    def _generate_action_recommendation(self, signal: SignalType, confidence: float) -> Tuple[str, float]:
        """生成操作建議"""
        actions = {
            SignalType.STRONG_BUY: ("積極買入，可加大部位", 0.08),
            SignalType.BUY: ("買入，建立基本部位", 0.05),
            SignalType.HOLD: ("持有觀望，維持現有部位", 0.03),
            SignalType.SELL: ("減碼，降低部位", 0.01),
            SignalType.STRONG_SELL: ("清倉或避開", 0.00)
        }
        
        action, base_weight = actions.get(signal, ("持有", 0.03))
        
        # 根據信心度調整權重
        adjusted_weight = base_weight * (0.8 + 0.4 * confidence)
        
        return action, round(adjusted_weight, 3)
    
    def _calculate_price_targets(self, signal: SignalType, current_price: float, 
                                tech_data: Dict) -> Tuple[float, float]:
        """計算停損停利價"""
        support = tech_data.get("support", current_price * 0.92)
        resistance = tech_data.get("resistance", current_price * 1.15)
        
        if signal in [SignalType.STRONG_BUY, SignalType.BUY]:
            # 買入：停損設在支撐下方，停利設在阻力
            stop_loss = round(min(support, current_price * 0.92), 2)
            take_profit = round(max(resistance, current_price * 1.15), 2)
        elif signal in [SignalType.SELL, SignalType.STRONG_SELL]:
            # 賣出：停損設在阻力上方
            stop_loss = round(max(resistance, current_price * 1.05), 2)
            take_profit = round(min(support, current_price * 0.90), 2)
        else:
            # 持有
            stop_loss = round(current_price * 0.95, 2)
            take_profit = round(current_price * 1.10, 2)
        
        return stop_loss, take_profit
    
    def _determine_time_horizon(self, signal: SignalType, trend_exposure: float) -> TimeHorizon:
        """決定投資期限"""
        if trend_exposure > 70:
            # 高趨勢曝險，適合中長期
            return TimeHorizon.MEDIUM_TERM
        elif signal in [SignalType.STRONG_BUY, SignalType.STRONG_SELL]:
            # 強烈信號，可短期操作
            return TimeHorizon.SHORT_TERM
        else:
            return TimeHorizon.MEDIUM_TERM
    
    def _generate_signal_reasons(self, signal: SignalType, technical_signal: str,
                                tech_data: Dict, trend_exposure: float, 
                                order_momentum: float) -> List[str]:
        """生成信號理由 (舊版)"""
        reasons = []
        
        # 技術面理由
        if technical_signal in ["strong_buy", "buy"]:
            reasons.append(f"技術面偏多: {tech_data.get('trend', '上升趨勢')}")
        elif technical_signal in ["strong_sell", "sell"]:
            reasons.append(f"技術面偏空: 位於相對高檔，注意回調風險")
        else:
            reasons.append("技術面中性: 處於盤整區間")
        
        # 趨勢曝險理由
        if trend_exposure > 70:
            reasons.append("高度受惠於AI/電動車等成長趨勢")
        elif trend_exposure > 50:
            reasons.append("中度受惠於產業趨勢")
        else:
            reasons.append("趨勢曝險較低")
        
        # 訂單動能理由
        if order_momentum > 70:
            reasons.append("訂單動能強勁，產能利用率高")
        elif order_momentum > 50:
            reasons.append("訂單動能正常")
        else:
            reasons.append("訂單動能較弱，需關注需求變化")
        
        # 價格位置
        position_zone = tech_data.get("position_zone", "中間")
        if "低" in position_zone:
            reasons.append("價格位於五年相對低檔，安全邊際較高")
        elif "高" in position_zone:
            reasons.append("價格位於五年相對高檔，需注意追高風險")
        
        return reasons
    
    def _generate_signal_reasons_v2(self, signal: SignalType, technical_signal: str,
                                    tech_data: Dict, economic_cycle: float,
                                    industry_power: float, financial: float,
                                    trend_exposure: float, order_momentum: float) -> List[str]:
        """生成信號理由 (新版 6 維度)"""
        reasons = []
        
        # 1. 技術面理由
        if technical_signal in ["strong_buy", "buy"]:
            reasons.append(f"📈 技術面偏多({tech_data.get('trend', '上升趨勢')})")
        elif technical_signal in ["strong_sell", "sell"]:
            reasons.append("📉 技術面偏空(五年高檔區)")
        else:
            reasons.append("⚖️ 技術面中性(盤整區間)")
        
        # 2. 總經循環理由
        if economic_cycle >= 70:
            reasons.append("🌍 總經循環利多(復甦/擴張期)")
        elif economic_cycle <= 30:
            reasons.append("🌍 總經循環利空(收縮期)")
        else:
            reasons.append("🌍 總經循環中性")
        
        # 3. 產業定價權理由
        if industry_power >= 75:
            reasons.append("🏭 產業定價權強(具護城河)")
        elif industry_power >= 60:
            reasons.append("🏭 產業定價權中等")
        else:
            reasons.append("🏭 產業定價權弱(競爭激烈)")
        
        # 4. 財報健康理由
        if financial >= 70:
            reasons.append("💰 財報健康(毛利率/現金流佳)")
        elif financial >= 50:
            reasons.append("💰 財報尚可")
        else:
            reasons.append("💰 財報需留意(關注現金流)")
        
        # 5. 趨勢曝險理由
        if trend_exposure > 70:
            reasons.append("🚀 高度受惠AI/電動車趨勢")
        elif trend_exposure > 50:
            reasons.append("📊 中度受惠產業趨勢")
        
        # 6. 訂單動能理由
        if order_momentum > 70:
            reasons.append("📦 訂單動能強勁")
        elif order_momentum < 40:
            reasons.append("📦 訂單動能較弱")
        
        return reasons
    
    def _generate_risk_warnings(self, ticker: str, signal: SignalType, 
                               tech_data: Dict) -> List[str]:
        """生成風險警示"""
        risks = []
        
        stock_info = self.stock_database.get(ticker, {})
        
        # 價格位置風險
        position_score = tech_data.get("position_score", 50)
        if position_score < 20:  # 高檔
            risks.append("⚠️ 股價處於歷史高檔，追漲風險高")
        
        # RSI 過熱/過冷
        rsi = tech_data.get("rsi", 50)
        if rsi > 70:
            risks.append("⚠️ RSI 過熱，短期可能回調")
        elif rsi < 30:
            risks.append("⚠️ RSI 超賣，但可能持續弱勢")
        
        # 產業特定風險
        sector = stock_info.get("sector", "")
        if sector == "半導體":
            risks.append("📌 半導體週期性強，需注意庫存變化")
        elif sector == "電子":
            risks.append("📌 電子股受消費電子需求影響")
        
        # 信號矛盾風險
        if signal == SignalType.HOLD:
            risks.append("📌 多空不明，建議觀望或小幅操作")
        
        return risks
    
    def generate_portfolio_recommendation(self, 
                                         focus_stocks: List[str] = None) -> PortfolioRecommendation:
        """
        生成投資組合建議
        
        Parameters:
        -----------
        focus_stocks : List[str]
            關注的股票列表
            
        Returns:
        --------
        PortfolioRecommendation: 投資組合建議
        """
        if focus_stocks is None:
            focus_stocks = ["2330", "2454", "2382", "3231", "6669", "2317", "3008", "2308"]
        
        print(f"📊 生成投資組合建議")
        print(f"   風險偏好: {self.risk_profile}")
        print(f"   投資資金: NT${self.initial_capital:,.0f}")
        print("=" * 60)
        
        # 1. 生成個股信號
        print("\n分析個股信號...")
        stock_signals = []
        for ticker in focus_stocks:
            try:
                signal = self.generate_stock_signal(ticker)
                stock_signals.append(signal)
                print(f"  {ticker} ({signal.name}): {signal.signal.value} 評分 {signal.score:.0f}")
            except Exception as e:
                print(f"  {ticker}: ❌ {e}")
        
        # 按評分排序
        stock_signals.sort(key=lambda x: x.score, reverse=True)
        
        # 2. 獲取資產配置
        print("\n生成資產配置...")
        equity_alloc, bond_alloc, cash_alloc, alt_alloc = self._get_asset_allocation()
        print(f"  股票: {equity_alloc*100:.0f}% | 債券: {bond_alloc*100:.0f}% | 現金: {cash_alloc*100:.0f}% | 另類: {alt_alloc*100:.0f}%")
        
        # 3. ETF 建議
        print("\n生成ETF建議...")
        etf_recommendations = self._generate_etf_recommendations(equity_alloc, bond_alloc)
        
        # 4. 市場狀況
        market_condition = self._assess_market_condition(stock_signals)
        print(f"\n市場狀況: {market_condition}")
        
        # 5. 整體建議
        overall_action = self._generate_overall_action(stock_signals, market_condition)
        
        # 6. 關鍵主題
        key_themes = self._identify_key_themes(stock_signals)
        
        # 7. 風險警示
        risk_warnings = self._aggregate_risk_warnings(stock_signals, market_condition)
        
        recommendation = PortfolioRecommendation(
            risk_profile=self.risk_profile,
            total_capital=self.initial_capital,
            market_condition=market_condition,
            equity_allocation=equity_alloc,
            bond_allocation=bond_alloc,
            cash_allocation=cash_alloc,
            alternative_allocation=alt_alloc,
            stock_recommendations=stock_signals,
            etf_recommendations=etf_recommendations,
            overall_action=overall_action,
            key_themes=key_themes,
            risk_warnings=risk_warnings
        )
        
        return recommendation
    
    def _get_asset_allocation(self) -> Tuple[float, float, float, float]:
        """獲取資產配置"""
        if self.asset_allocator:
            try:
                allocations = self.asset_allocator.generate_portfolio_allocation()
                
                equity = sum(a.allocation for a in allocations if "equity" in a.asset_class)
                bonds = sum(a.allocation for a in allocations if "fixed" in a.asset_class)
                cash = sum(a.allocation for a in allocations if "cash" in a.asset_class)
                alt = sum(a.allocation for a in allocations if "alternative" in a.asset_class)
                
                return equity, bonds, cash, alt
                
            except Exception as e:
                print(f"  資產配置錯誤: {e}")
        
        # 預設配置
        if self.risk_profile == "CONSERVATIVE":
            return 0.30, 0.50, 0.15, 0.05
        elif self.risk_profile == "AGGRESSIVE":
            return 0.70, 0.20, 0.05, 0.05
        else:  # MODERATE
            return 0.50, 0.35, 0.10, 0.05
    
    def _generate_etf_recommendations(self, equity_alloc: float, 
                                     bond_alloc: float) -> List[Dict]:
        """生成ETF建議"""
        etf_list = []
        
        # 股票型ETF
        if equity_alloc > 0:
            etf_list.append({
                "ticker": "0050.TW",
                "name": "元大台灣50",
                "allocation": round(equity_alloc * 0.4, 3),
                "reason": "核心持股: 台灣大型股指數"
            })
            etf_list.append({
                "ticker": "0056.TW",
                "name": "元大高股息",
                "allocation": round(equity_alloc * 0.3, 3),
                "reason": "高股息: 穩定現金流"
            })
            etf_list.append({
                "ticker": "SPY",
                "name": "S&P 500 ETF",
                "allocation": round(equity_alloc * 0.3, 3),
                "reason": "海外配置: 美股大盤"
            })
        
        # 債券型ETF
        if bond_alloc > 0:
            etf_list.append({
                "ticker": "AGG",
                "name": "綜合債券ETF",
                "allocation": round(bond_alloc * 0.6, 3),
                "reason": "債券配置: 降低波動"
            })
            etf_list.append({
                "ticker": "TLT",
                "name": "長期公債ETF",
                "allocation": round(bond_alloc * 0.4, 3),
                "reason": "長債配置: 利率避險"
            })
        
        return etf_list
    
    def _assess_market_condition(self, signals: List[InvestmentSignal]) -> str:
        """評估市場狀況"""
        if not signals:
            return "盤整市場"
        
        avg_score = np.mean([s.score for s in signals])
        buy_count = sum(1 for s in signals if s.signal in [SignalType.STRONG_BUY, SignalType.BUY])
        sell_count = sum(1 for s in signals if s.signal in [SignalType.STRONG_SELL, SignalType.SELL])
        
        if avg_score > 70 and buy_count > len(signals) * 0.6:
            return "多頭市場"
        elif avg_score < 40 and sell_count > len(signals) * 0.5:
            return "空頭市場"
        elif avg_score > 55:
            return "偏多盤整"
        elif avg_score < 45:
            return "偏空盤整"
        else:
            return "盤整市場"
    
    def _generate_overall_action(self, signals: List[InvestmentSignal], 
                                market_condition: str) -> str:
        """生成整體操作建議"""
        if "多頭" in market_condition:
            return "積極操作: 可適度加碼，關注強勢股"
        elif "空頭" in market_condition:
            return "保守操作: 減碼觀望，保留現金"
        elif "偏多" in market_condition:
            return "穩健操作: 維持部位，逢低加碼"
        elif "偏空" in market_condition:
            return "謹慎操作: 減輕部位，等待轉機"
        else:
            return "中性操作: 維持平衡配置，等待明確方向"
    
    def _identify_key_themes(self, signals: List[InvestmentSignal]) -> List[str]:
        """識別關鍵主題"""
        themes = []
        
        # 檢查AI相關股票表現
        ai_stocks = [s for s in signals if s.ticker in ["2330", "2382", "3231", "6669"]]
        if ai_stocks:
            avg_ai_score = np.mean([s.score for s in ai_stocks])
            if avg_ai_score > 60:
                themes.append("🔥 AI伺服器概念股表現強勢")
        
        # 檢查半導體表現
        semi_stocks = [s for s in signals if s.ticker in ["2330", "2454", "2303", "3034"]]
        if semi_stocks:
            avg_semi_score = np.mean([s.score for s in semi_stocks])
            if avg_semi_score > 60:
                themes.append("💎 半導體族群動能佳")
        
        # 高技術曝險股票
        high_trend = [s for s in signals if s.trend_exposure > 70]
        if len(high_trend) > 2:
            themes.append("📈 多檔個股受惠產業趨勢")
        
        # 訂單動能
        high_order = [s for s in signals if s.order_momentum > 70]
        if high_order:
            themes.append("📦 部分公司訂單能見度佳")
        
        if not themes:
            themes.append("📊 市場處於觀望階段")
        
        return themes
    
    def _aggregate_risk_warnings(self, signals: List[InvestmentSignal], 
                                market_condition: str) -> List[str]:
        """彙整風險警示"""
        warnings = []
        
        # 市場風險
        if "空頭" in market_condition:
            warnings.append("⚠️ 市場整體偏弱，注意系統性風險")
        
        # 高檔風險
        high_position = [s for s in signals if s.score < 30]
        if len(high_position) > len(signals) * 0.3:
            warnings.append("⚠️ 多檔個股位於相對高檔，追高風險增加")
        
        # 集中風險
        warnings.append("📌 建議分散投資，單一個股不超過總資金10%")
        
        # 停損提醒
        warnings.append("📌 嚴格執行停損紀律，保護資金安全")
        
        return warnings
    
    def generate_report(self, recommendation: PortfolioRecommendation = None,
                       focus_stocks: List[str] = None) -> str:
        """
        生成完整報告
        
        Returns:
        --------
        str: 報告內容
        """
        if recommendation is None:
            recommendation = self.generate_portfolio_recommendation(focus_stocks)
        
        report = f"""
{'='*80}
🎯 投資信號與配置建議報告
{'='*80}

📅 報告時間: {recommendation.generated_at}
👤 風險偏好: {recommendation.risk_profile}
💰 投資資金: NT${recommendation.total_capital:,.0f}
📈 市場狀況: {recommendation.market_condition}

{'─'*80}
💼 【資產配置建議】
{'─'*80}

總資金配置:
  📊 股票: {recommendation.equity_allocation*100:.0f}% (NT${recommendation.total_capital*recommendation.equity_allocation:,.0f})
  📈 債券: {recommendation.bond_allocation*100:.0f}% (NT${recommendation.total_capital*recommendation.bond_allocation:,.0f})
  💵 現金: {recommendation.cash_allocation*100:.0f}% (NT${recommendation.total_capital*recommendation.cash_allocation:,.0f})
  🏠 另類: {recommendation.alternative_allocation*100:.0f}% (NT${recommendation.total_capital*recommendation.alternative_allocation:,.0f})

{'─'*80}
📊 【個股投資信號】
{'─'*80}
"""
        
        # 個股信號
        for signal in recommendation.stock_recommendations:
            emoji = {"強力買進": "🔥", "買進": "✅", "持有": "⏸️", "賣出": "⚠️", "強力賣出": "🔴"}
            signal_emoji = emoji.get(signal.signal.value, "⏸️")
            
            report += f"""
{signal_emoji} {signal.ticker} ({signal.name}) - {signal.signal.value}
   綜合評分: {signal.score:.0f}/100
   信心度: {signal.confidence*100:.0f}%
   操作建議: {signal.action}
   建議配置: {signal.target_weight*100:.1f}%
   停損價: {signal.stop_loss} | 停利價: {signal.take_profit}
   投資期限: {signal.time_horizon.value}
   
   📝 理由:
"""
            for reason in signal.reasons[:3]:
                report += f"      • {reason}\n"
            
            if signal.risks:
                report += f"   ⚠️ 風險:\n"
                for risk in signal.risks[:2]:
                    report += f"      • {risk}\n"
        
        report += f"""
{'─'*80}
📈 【ETF配置建議】
{'─'*80}
"""
        
        for etf in recommendation.etf_recommendations:
            amount = recommendation.total_capital * etf["allocation"]
            report += f"""
  {etf['ticker']} ({etf['name']})
    配置比重: {etf['allocation']*100:.1f}% (NT${amount:,.0f})
    配置理由: {etf['reason']}
"""
        
        report += f"""
{'─'*80}
🎯 【整體操作建議】
{'─'*80}

{recommendation.overall_action}

📌 關鍵主題:
"""
        for theme in recommendation.key_themes:
            report += f"  {theme}\n"
        
        report += f"""
⚠️ 風險提示:
"""
        for warning in recommendation.risk_warnings:
            report += f"  {warning}\n"
        
        report += f"""
{'─'*80}
📋 【快速行動清單】
{'─'*80}
"""
        
        # 買進建議
        buy_signals = [s for s in recommendation.stock_recommendations 
                      if s.signal in [SignalType.STRONG_BUY, SignalType.BUY]]
        if buy_signals:
            report += "\n🟢 可考慮買進:\n"
            for s in buy_signals[:3]:
                report += f"   • {s.ticker} ({s.name}) @ 停損 {s.stop_loss}\n"
        
        # 持有建議
        hold_signals = [s for s in recommendation.stock_recommendations 
                       if s.signal == SignalType.HOLD]
        if hold_signals:
            report += "\n🟡 維持觀望:\n"
            for s in hold_signals[:3]:
                report += f"   • {s.ticker} ({s.name})\n"
        
        # 賣出建議
        sell_signals = [s for s in recommendation.stock_recommendations 
                       if s.signal in [SignalType.STRONG_SELL, SignalType.SELL]]
        if sell_signals:
            report += "\n🔴 考慮減碼:\n"
            for s in sell_signals[:3]:
                report += f"   • {s.ticker} ({s.name})\n"
        
        report += f"""
{'='*80}
⚠️ 免責聲明：本報告僅供參考，不構成投資建議。投資有風險，請謹慎評估。
{'='*80}
"""
        
        return report
    
    def to_dict(self) -> Dict:
        """轉換為字典格式"""
        return {
            "risk_profile": self.risk_profile,
            "initial_capital": self.initial_capital,
            "signal_weights": self.signal_weights,
            "thresholds": self.thresholds,
            "generated_at": datetime.now().isoformat()
        }


def main():
    """主程式"""
    print("=" * 80)
    print("🎯 投資信號產生器 v1.0")
    print("=" * 80)
    
    # 選擇風險偏好
    print("\n風險偏好選項:")
    print("1. 保守型 (CONSERVATIVE)")
    print("2. 穩健型 (MODERATE)")
    print("3. 積極型 (AGGRESSIVE)")
    
    choice = input("\n請選擇風險偏好 (1/2/3, 預設2): ").strip()
    
    risk_map = {"1": "CONSERVATIVE", "2": "MODERATE", "3": "AGGRESSIVE"}
    risk_profile = risk_map.get(choice, "MODERATE")
    
    # 輸入投資資金
    capital_input = input("請輸入投資資金 (預設100萬): ").strip()
    try:
        initial_capital = float(capital_input) if capital_input else 1000000
    except:
        initial_capital = 1000000
    
    # 初始化信號產生器
    print(f"\n初始化信號產生器 ({risk_profile}, NT${initial_capital:,.0f})...")
    generator = SignalGenerator(risk_profile=risk_profile, initial_capital=initial_capital)
    
    # 生成報告
    focus_stocks = ["2330", "2454", "2382", "3231", "6669", "2317", "3008", "2308"]
    recommendation = generator.generate_portfolio_recommendation(focus_stocks)
    
    # 輸出報告
    report = generator.generate_report(recommendation)
    print(report)
    
    # 保存報告
    report_filename = f"investment_signal_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n📄 報告已保存至: {report_filename}")
    
    print("\n✅ 投資信號產生完成!")
    
    return generator, recommendation


if __name__ == "__main__":
    main()
