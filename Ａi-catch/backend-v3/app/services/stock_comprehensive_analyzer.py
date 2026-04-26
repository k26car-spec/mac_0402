"""
股票綜合分析服務
提供全方位的股票分析功能

功能:
1. 綜合評分 (成長性、估值、財務品質、技術面)
2. 買入訊號分析
3. 賣出訊號分析
4. 風險警示
5. 三大法人籌碼分析
6. 財務健康評估
7. 股票相關新聞 (Perplexity API)
"""

import os
import json
import logging
import aiohttp
import asyncio
import ssl
import certifi
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# ==================== 設定 ====================

PERPLEXITY_TOKEN = os.environ.get("PERPLEXITY_TOKEN", "")
PERPLEXITY_MODEL = "sonar"  # Perplexity 線上搜尋模型

from stock_mappings import get_stock_name as mapper_get_name, get_market_suffix

# 動態快取（程式運行期間自動累積）
STOCK_NAMES_CACHE: Dict[str, str] = {}

async def get_stock_name(code: str) -> str:
    """
    取得股票中文名稱 (異步優化版)
    """
    base_code = code.replace('.TW', '').replace('.TWO', '')
    
    # 1. 從動態快取查詢
    if base_code in STOCK_NAMES_CACHE:
        return STOCK_NAMES_CACHE[base_code]
        
    # 2. 🆕 優先使用富邦 API (用戶要求)
    try:
        from fubon_client import fubon_client
        name = await fubon_client.get_stock_name(base_code)
        if name and name != base_code:
            STOCK_NAMES_CACHE[base_code] = name
            return name
    except Exception as e:
        logger.debug(f"富邦 API 獲取名稱失敗: {e}")

    # 3. 嘗試從證交所獲取
    try:
        name = _fetch_name_from_twse(base_code)
        if name:
            STOCK_NAMES_CACHE[base_code] = name
            return name
    except:
        pass
        
    # 4. 嘗試從 Yahoo 獲取
    try:
        name = _fetch_name_from_yahoo(base_code)
        if name:
            STOCK_NAMES_CACHE[base_code] = name
            return name
    except:
        pass

    # 5. 備援：由集中的映射獲取
    name = mapper_get_name(code)
    if name != code:
        STOCK_NAMES_CACHE[base_code] = name
        return name

    return code



def _is_english_name(name: str) -> bool:
    """檢查是否為英文名稱"""
    if not name:
        return False
    # 如果超過 50% 是英文字母，視為英文名稱
    english_chars = sum(1 for c in name if c.isascii() and c.isalpha())
    return english_chars > len(name) * 0.5


def _fetch_name_from_twse(code: str) -> str:
    """從 TWSE 證交所 API 取得股票名稱"""
    import requests
    
    try:
        # 使用證交所個股資料查詢
        url = f"https://www.twse.com.tw/zh/api/codeQuery?query={code}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.twse.com.tw/'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            suggestions = data.get('suggestions', [])
            for suggestion in suggestions:
                if suggestion.startswith(code):
                    # 格式: "2330\t台積電"
                    parts = suggestion.split('\t')
                    if len(parts) >= 2:
                        return parts[1].strip()
    except Exception:
        pass
    
    return ""


def _fetch_name_from_yahoo(code: str) -> str:
    """從 Yahoo Finance 取得股票名稱"""
    try:
        import yfinance as yf
        symbol = f"{code}.TW"
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if info:
            # 優先取 shortName (通常是中文)
            name = info.get('shortName') or info.get('longName') or ''
            return name
    except Exception:
        pass
    
    return ""


async def batch_fetch_stock_names(codes: list) -> Dict[str, str]:
    """批次取得股票名稱"""
    results = {}
    for code in codes:
        results[code] = await get_stock_name(code)
    return results


# ==================== 資料模型 ====================

class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Signal:
    """交易訊號"""
    type: SignalType
    name: str
    description: str
    confidence: float  # 0-100
    source: str

@dataclass
class RiskAlert:
    """風險警示"""
    level: RiskLevel
    title: str
    description: str
    metric: str
    value: Any

@dataclass
class FinancialHealth:
    """財務健康指標"""
    roe: float
    eps: float
    quarterly_eps: List[Dict]  # 季度 EPS 資料 [{quarter: "2025Q3", eps: 15.36, yoy_change: 10.5}, ...]
    revenue_growth_3y: float
    gross_margin: float
    debt_ratio: float
    current_ratio: float
    quick_ratio: float
    interest_coverage: float
    free_cash_flow: float

@dataclass
class Valuation:
    """估值分析"""
    pe_ratio: float
    pb_ratio: float
    dividend_yield: float
    peg_ratio: float
    ev_ebitda: float

@dataclass
class TechnicalIndicators:
    """技術指標"""
    current_price: float  # 當前價格
    change_pct: float     # 漲跌幅 %
    # MA 均線
    ma5: float
    ma10: float
    ma20: float
    ma60: float
    # MA 均線分析
    ma_arrangement: str    # 均線排列: 多頭排列/空頭排列/糾結
    ma_signal: str         # 均線訊號: 突破MA5/跌破MA10...
    ma_trend: str          # 短中長期趨勢描述
    # 壓力與支撐
    resistance_1: float    # 壓力位1 (近)
    resistance_2: float    # 壓力位2 (遠)
    support_1: float       # 支撐位1 (近)
    support_2: float       # 支撐位2 (遠)
    # 其他技術指標
    rsi_14: float
    macd: float
    macd_signal: str
    kd_k: float
    kd_d: float
    bollinger_width: float
    deviation_20d: float
    deviation_60d: float
    trend: str

@dataclass
class VolumePriceAnalysis:
    """量價關係分析"""
    # 量價趨勢判斷
    trend_direction: str           # bullish, bearish, sideways
    trend_confidence: float        # 0-100 置信度
    
    # 量價確認分析
    volume_price_confirmation: str  # 價漲量增, 價漲量縮, 價跌量增, 價跌量縮
    confirmation_signal: str        # bullish_confirmation, bearish_confirmation, caution, neutral
    confirmation_strength: float    # 0-1 信號強度
    
    # 量價背離
    divergence_detected: bool       # 是否檢測到背離
    divergence_type: str            # bullish_divergence, bearish_divergence, none
    divergence_description: str     # 背離說明
    
    # 成交量指標
    volume_ratio: float             # 量比 (當日成交量 / 5日均量)
    volume_trend: str               # increasing, decreasing, stable
    volume_sma5: float              # 5日成交量均值
    volume_sma20: float             # 20日成交量均值
    
    # 量價技術指標
    obv: float                      # 能量潮 On-Balance Volume
    obv_trend: str                  # OBV趨勢: bullish, bearish, neutral
    vwap: float                     # 成交量加權平均價
    vwap_deviation: float           # 當前價格與VWAP偏離度 (%)
    
    # 關鍵量價訊號
    key_signals: List[str]          # 關鍵量價訊號列表
    
    # 預測
    predicted_direction: str        # up, down, sideways
    prediction_probability: Dict[str, float]  # {up: 0.6, down: 0.2, sideways: 0.2}
    
    # 買賣力道 (專家版新增，移至最後避免語法錯誤)
    buy_pressure_percent: float = 50.0  # 買方力道 %
    sell_pressure_percent: float = 50.0 # 賣方力道 %

@dataclass
class RiskMetrics:
    """風險指標 (專家建議新增)"""
    beta: float                    # 波動率係數 (相對大盤)
    volatility: float              # 歷史波動率 (60日標準差年化)
    margin_usage: float            # 融資使用率 (%)，過高需扣分
    retail_concentration: float    # 散戶持股比例 (%)，反向指標
    short_selling_balance: float   # 借券賣出餘額 (張)
    margin_increase_ratio: float   # 融資增減比例 (%)，正值代表融資增加

@dataclass
class SectorAnalysis:
    """產業地位分析 (專家建議新增)"""
    sector_name: str               # 產業名稱
    sector_trend: str              # 產業趨勢: bullish, bearish, neutral
    relative_strength: float       # 相對強度 RS (個股vs大盤，>1強勢)
    pe_rank_in_sector: float       # 在同產業的PE估值排名 (0-100，越低越便宜)
    sector_avg_pe: float           # 產業平均本益比
    pe_band_position: float        # PE Band 位置 (0-100，目前PE在歷史區間的位置)

@dataclass
class InstitutionalTrading:
    """法人籌碼"""
    foreign_buy: int
    foreign_sell: int
    foreign_net: int
    trust_buy: int
    trust_sell: int
    trust_net: int
    dealer_buy: int
    dealer_sell: int
    dealer_net: int
    total_net: int
    consecutive_days: int
    chip_concentration: float
    # 專家建議新增欄位
    main_force_avg_cost: float = 0  # 主力買均價 (用於判斷是否高於主力成本)
    foreign_short_balance: float = 0  # 外資借券賣出餘額 (假買真空判斷)
    institutional_history: Optional[Dict[str, Dict[str, int]]] = None # 🆕 新增：多周期資料


@dataclass
class DimensionScore:
    """維度評分"""
    name: str
    score: float  # 0-100
    weight: float
    details: List[str]

@dataclass
class ComprehensiveAnalysis:
    """綜合分析結果 (專家版)"""
    stock_code: str
    stock_name: str
    last_updated: str
    overall_score: float
    dimension_scores: List[DimensionScore]
    buy_signals: List[Signal]
    sell_signals: List[Signal]
    risk_alerts: List[RiskAlert]
    financial_health: Optional[FinancialHealth]
    valuation: Optional[Valuation]
    technical_indicators: Optional[TechnicalIndicators]
    institutional_trading: Optional[InstitutionalTrading]
    related_news: List[Dict]
    ai_summary: str
    recommendation: str
    target_price: Optional[float]
    stop_loss: Optional[float]
    # 量價分析
    volume_price_analysis: Optional[VolumePriceAnalysis] = None
    # 專家建議新增模組
    risk_metrics: Optional[RiskMetrics] = None          # 風險指標
    sector_analysis: Optional[SectorAnalysis] = None    # 產業分析
    ai_investment_thesis: str = ""                       # AI 投資邏輯
    ai_risk_warning: str = ""                            # AI 風險預警
    macro_summary: Optional[Dict] = None                 # 國際情勢與總結


# ==================== 分析服務主類別 ====================

class StockComprehensiveAnalyzer:
    """股票綜合分析器"""
    
    def __init__(self):
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.session = None
        self.cache = {}
        self.cache_ttl = 300  # 5分鐘快取
        
    async def _get_session(self):
        if not self.session:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
        return self.session
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    # ==================== 主要分析入口 ====================
    
    async def analyze(self, stock_code: str, quick_mode: bool = False) -> ComprehensiveAnalysis:
        """
        執行完整的股票綜合分析
        
        Args:
            stock_code: 股票代碼
            quick_mode: 是否使用快模式 (跳過 AI 摘要和新聞補充)
            
        Returns:
            ComprehensiveAnalysis: 完整分析結果
        """
        logger.info(f"開始綜合分析股票: {stock_code} (QuickMode: {quick_mode})")
        
        # 檢查快取
        cache_key = f"analysis_{stock_code}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                logger.info(f"使用快取資料: {stock_code}")
                return cached_data
        
        # 並行取得所有資料
        tasks = [
            self._get_stock_price_data(stock_code),
            self._get_financial_data(stock_code),
            self._get_institutional_data(stock_code),
            self._get_stock_news(stock_code) if not quick_mode else asyncio.sleep(0, result=[]),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        price_data = results[0] if not isinstance(results[0], Exception) else {}
        financial_data = results[1] if not isinstance(results[1], Exception) else {}
        institutional_data = results[2] if not isinstance(results[2], Exception) else {}
        news_data = results[3] if not isinstance(results[3], Exception) else []
        
        # 計算各維度分數
        dimension_scores = await self._calculate_dimension_scores(
            price_data, financial_data, institutional_data
        )
        
        # 計算綜合分數
        overall_score = self._calculate_overall_score(dimension_scores)
        
        # 分析買入訊號
        buy_signals = self._analyze_buy_signals(
            price_data, financial_data, institutional_data
        )
        
        # 分析賣出訊號
        sell_signals = self._analyze_sell_signals(
            price_data, financial_data, institutional_data
        )
        
        # 分析風險警示
        risk_alerts = self._analyze_risks(
            price_data, financial_data, institutional_data
        )
        
        # 建構財務健康指標
        financial_health = self._build_financial_health(financial_data)
        
        # 建構估值分析
        valuation = self._build_valuation(financial_data)
        
        # 建構技術指標
        technical_indicators = self._build_technical_indicators(price_data)
        
        # 建構法人籌碼 (傳入 price_data 以進行成本估算回補)
        institutional_trading = self._build_institutional_trading(institutional_data, price_data)
        
        # 建構量價分析
        volume_price_analysis = self._build_volume_price_analysis(price_data)
        
        # 專家建議：建構風險指標
        risk_metrics = self._build_risk_metrics(price_data, institutional_data)
        
        # 專家建議：建構產業分析
        sector_analysis = self._build_sector_analysis(stock_code, financial_data, price_data)
        
        # 生成 AI 摘要
        ai_summary = ""
        ai_investment_thesis = ""
        ai_risk_warning = ""

        if not quick_mode:
            ai_summary = await self._generate_ai_summary(
                stock_code, overall_score, buy_signals, sell_signals, risk_alerts
            )
            
            # 專家建議：生成 AI 投資邏輯和風險預警
            ai_investment_thesis = self._generate_investment_thesis(
                overall_score, dimension_scores, buy_signals, financial_data
            )
            ai_risk_warning = self._generate_risk_warning(
                risk_alerts, risk_metrics, price_data
            )
        else:
            ai_summary = "快速分析模式 (跳過 AI 摘要)"
            ai_investment_thesis = "快速分析模式 (跳過投資邏輯)"
            ai_risk_warning = "快速分析模式 (跳過風險預警)"
        
        # 生成推薦等級
        recommendation = self._generate_recommendation(
            overall_score, len(buy_signals), len(sell_signals), len(risk_alerts)
        )
        
        # 計算目標價和止損價
        target_price, stop_loss = self._calculate_price_targets(price_data, overall_score)
        
        stock_name = await get_stock_name(stock_code)
        
        # 🆕 取得國際情勢總匯
        macro_result = None
        try:
            from app.services.macro_economy_service import macro_service
            macro_result = await macro_service.get_global_macro_status()
        except Exception as me:
            logger.warning(f"取得總經資料失敗: {me}")

        analysis = ComprehensiveAnalysis(
            stock_code=stock_code,
            stock_name=stock_name,
            last_updated=datetime.now().isoformat(),
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            risk_alerts=risk_alerts,
            financial_health=financial_health,
            valuation=valuation,
            technical_indicators=technical_indicators,
            institutional_trading=institutional_trading,
            related_news=news_data,
            ai_summary=ai_summary,
            recommendation=recommendation,
            target_price=target_price,
            stop_loss=stop_loss,
            volume_price_analysis=volume_price_analysis,
            # 專家建議新增
            risk_metrics=risk_metrics,
            sector_analysis=sector_analysis,
            ai_investment_thesis=ai_investment_thesis,
            ai_risk_warning=ai_risk_warning,
            macro_summary=macro_result
        )
        
        # 儲存快取
        self.cache[cache_key] = (datetime.now(), analysis)
        
        logger.info(f"股票 {stock_code} 綜合分析完成，評分: {overall_score}")
        return analysis

    # ==================== 資料取得方法 ====================
    
    async def _get_stock_price_data(self, stock_code: str) -> Dict:
        """取得股票價格和技術面資料"""
        hist = None
        symbol = None
        
        try:
            import yfinance as yf
            
            # 使用 patch_yfinance 取得正確的後綴
            try:
                from app.patch_yfinance import fix_taiwan_symbol, get_stock_market_type
                symbol = fix_taiwan_symbol(stock_code)
                logger.debug(f"使用 patch_yfinance: {stock_code} -> {symbol}")
            except ImportError:
                # 備援：直接使用 .TW
                symbol = f"{stock_code}.TW"
            
            # 靜默 yfinance 警告和錯誤訊息
            import warnings
            import logging as yf_logging
            warnings.filterwarnings('ignore', message='.*possibly delisted.*')
            warnings.filterwarnings('ignore', message='.*No data found.*')
            warnings.filterwarnings('ignore', message='.*Quote not found.*')
            # 暫時降低 yfinance 的日誌級別
            yf_logging.getLogger('yfinance').setLevel(yf_logging.ERROR)
            
            ticker = yf.Ticker(symbol)
            
            # 靜默獲取價格歷史（異步 + timeout 8 秒避免阻塞）
            try:
                import asyncio
                hist = await asyncio.wait_for(
                    asyncio.to_thread(ticker.history, period="3mo"),
                    timeout=8.0
                )
            except (asyncio.TimeoutError, Exception):
                hist = None
            
            # 如果第一次失敗，嘗試另一種格式
            if hist is None or hist.empty:
                alt_symbol = f"{stock_code}.TWO" if ".TW" in symbol and ".TWO" not in symbol else f"{stock_code}.TW"
                ticker = yf.Ticker(alt_symbol)
                try:
                    hist = await asyncio.wait_for(
                        asyncio.to_thread(ticker.history, period="3mo"),
                        timeout=8.0
                    )
                    if hist is not None and not hist.empty:
                        symbol = alt_symbol
                        logger.debug(f"✅ 使用替代後綴: {alt_symbol}")
                except (asyncio.TimeoutError, Exception):
                    hist = None
            
            # 如果 Yahoo 都失敗，嘗試 FinMind API (台灣資料完整)
            if hist is None or hist.empty:
                try:
                    from app.services.finmind_service import get_finmind_history, get_stock_market_type
                    
                    # 取得 FinMind 歷史資料
                    finmind_data = await get_finmind_history(stock_code, days=180)
                    
                    if finmind_data and len(finmind_data) > 0:
                        logger.info(f"✅ 使用 FinMind API 取得 {stock_code} 價格 ({len(finmind_data)} 筆)")
                        
                        # 轉換為 pandas DataFrame 格式
                        import pandas as pd
                        df = pd.DataFrame(finmind_data)
                        df['date'] = pd.to_datetime(df['date'])
                        df.set_index('date', inplace=True)
                        df = df.rename(columns={
                            'open': 'Open',
                            'max': 'High',
                            'min': 'Low',
                            'close': 'Close',
                            'Trading_Volume': 'Volume'
                        })
                        
                        # 確保有足夠資料
                        if len(df) >= 5:
                            hist = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
                            symbol = f"{stock_code} (FinMind)"
                except Exception as e:
                    logger.debug(f"FinMind API 取得 {stock_code} 失敗: {e}")
            
            # 如果 FinMind 也失敗，嘗試富邦 API
            if hist is None or hist.empty:
                try:
                    from app.services.fubon_service import get_realtime_quote
                    fubon_quote = await get_realtime_quote(stock_code)
                    
                    if fubon_quote and fubon_quote.get('price', 0) > 0:
                        # 從富邦 API 獲得基本價格資料
                        logger.info(f"✅ 使用富邦 API 取得 {stock_code} 即時價格")
                        return {
                            "current_price": fubon_quote.get('price', 0),
                            "open": fubon_quote.get('open', 0),
                            "high": fubon_quote.get('high', 0),
                            "low": fubon_quote.get('low', 0),
                            "volume": fubon_quote.get('volume', 0),
                            "vwap": fubon_quote.get('vwap', fubon_quote.get('price', 0)),
                            "source": "fubon",
                            # 技術指標使用預設值 (因為沒有歷史資料)
                            "ma5": fubon_quote.get('price', 0),
                            "ma10": fubon_quote.get('price', 0),
                            "ma20": fubon_quote.get('price', 0),
                            "ma60": fubon_quote.get('price', 0),
                            "ma_arrangement": "資料不足",
                            "ma_signal": "無明顯訊號",
                            "ma_trend": "資料不足",
                            "resistance_1": fubon_quote.get('price', 0) * 1.05,
                            "resistance_2": fubon_quote.get('price', 0) * 1.10,
                            "support_1": fubon_quote.get('price', 0) * 0.95,
                            "support_2": fubon_quote.get('price', 0) * 0.90,
                            "rsi_14": 50,
                            "macd": 0,
                            "macd_signal": "中性",
                            "macd_histogram": 0,
                            "kd_k": 50,
                            "kd_d": 50,
                            "bb_width": 0,
                            "deviation_20d": 0,
                            "deviation_60d": 0,
                            "trend": "盤整",
                            "change_pct": fubon_quote.get('change', 0),
                        }
                except Exception as e:
                    logger.debug(f"富邦 API 也無法取得 {stock_code} 資料: {e}")
            
            if hist is None or hist.empty:
                logger.debug(f"無法取得 {stock_code} 價格資料 (已嘗試 Yahoo .TW/.TWO, FinMind, 富邦)")
                return {}
            
            current_price = hist['Close'].iloc[-1] if not hist.empty else 0
            
            # 計算技術指標
            close = hist['Close']
            high = hist['High']
            low = hist['Low']
            volume = hist['Volume']
            
            import math
            # 輔助函式：處理 NaN 值
            def safe_val(val, fallback=0.0):
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    return fallback
                return val

            # MA 均線
            ma5 = safe_val(close.rolling(5).mean().iloc[-1], current_price) if len(close) >= 5 else current_price
            ma10 = safe_val(close.rolling(10).mean().iloc[-1], current_price) if len(close) >= 10 else current_price
            ma20 = safe_val(close.rolling(20).mean().iloc[-1], current_price) if len(close) >= 20 else current_price
            ma60 = safe_val(close.rolling(60).mean().iloc[-1], current_price) if len(close) >= 60 else current_price
            
            # 前日 MA 值 (用於判斷突破/跌破)
            prev_close = close.iloc[-2] if len(close) >= 2 else current_price
            prev_ma5 = close.rolling(5).mean().iloc[-2] if len(close) >= 6 else ma5
            prev_ma10 = close.rolling(10).mean().iloc[-2] if len(close) >= 11 else ma10
            prev_ma20 = close.rolling(20).mean().iloc[-2] if len(close) >= 21 else ma20
            
            # ========== MA 均線分析 ==========
            
            # 1. 均線排列判斷
            if ma5 > ma10 > ma20 > ma60:
                ma_arrangement = "多頭排列"
            elif ma5 < ma10 < ma20 < ma60:
                ma_arrangement = "空頭排列"
            elif ma5 > ma10 > ma20:
                ma_arrangement = "短多排列"
            elif ma5 < ma10 < ma20:
                ma_arrangement = "短空排列"
            else:
                ma_arrangement = "均線糾結"
            
            # 2. 突破/跌破訊號
            ma_signals = []
            
            # 檢查 MA5 突破/跌破
            if prev_close < prev_ma5 and current_price > ma5:
                ma_signals.append("突破MA5")
            elif prev_close > prev_ma5 and current_price < ma5:
                ma_signals.append("跌破MA5")
            
            # 檢查 MA10 突破/跌破
            if prev_close < prev_ma10 and current_price > ma10:
                ma_signals.append("突破MA10")
            elif prev_close > prev_ma10 and current_price < ma10:
                ma_signals.append("跌破MA10")
            
            # 檢查 MA20 突破/跌破
            if prev_close < prev_ma20 and current_price > ma20:
                ma_signals.append("突破MA20 ⬆️")
            elif prev_close > prev_ma20 and current_price < ma20:
                ma_signals.append("跌破MA20 ⬇️")
            
            # 當前價格相對於均線位置
            if current_price > ma5:
                ma_signals.append("站穩MA5之上")
            else:
                ma_signals.append("在MA5之下")
            
            ma_signal = "、".join(ma_signals) if ma_signals else "無明顯訊號"
            
            # 3. 短中長期趨勢描述
            short_trend = "偏多" if current_price > ma5 else "偏空"
            mid_trend = "偏多" if current_price > ma20 else "偏空"
            long_trend = "偏多" if current_price > ma60 else "偏空"
            ma_trend = f"短期{short_trend}、中期{mid_trend}、長期{long_trend}"
            
            # ========== 壓力與支撐位計算 ==========
            
            # 方法: 結合歷史高低點、均線、整數關卡
            
            # 近期高低點 (20日)
            recent_high = high.tail(20).max()
            recent_low = low.tail(20).min()
            
            # 中期高低點 (60日)
            mid_high = high.tail(60).max() if len(high) >= 60 else recent_high
            mid_low = low.tail(60).min() if len(low) >= 60 else recent_low
            
            # 壓力位計算
            resistance_candidates = []
            
            # 加入均線作為壓力 (如果在價格之上)
            if ma5 > current_price:
                resistance_candidates.append(("MA5", ma5))
            if ma10 > current_price:
                resistance_candidates.append(("MA10", ma10))
            if ma20 > current_price:
                resistance_candidates.append(("MA20", ma20))
            if ma60 > current_price:
                resistance_candidates.append(("MA60", ma60))
            
            # 加入近期高點
            if recent_high > current_price:
                resistance_candidates.append(("近高", recent_high))
            if mid_high > current_price and mid_high != recent_high:
                resistance_candidates.append(("中高", mid_high))
            
            # 整數關卡
            round_up = ((current_price // 10) + 1) * 10
            if round_up > current_price:
                resistance_candidates.append(("整數關卡", round_up))
            
            # 排序並取最近兩個壓力位
            resistance_candidates.sort(key=lambda x: x[1])
            resistance_1 = resistance_candidates[0][1] if len(resistance_candidates) >= 1 else current_price * 1.05
            resistance_2 = resistance_candidates[1][1] if len(resistance_candidates) >= 2 else current_price * 1.10
            
            # 支撐位計算
            support_candidates = []
            
            # 加入均線作為支撐 (如果在價格之下)
            if ma5 < current_price:
                support_candidates.append(("MA5", ma5))
            if ma10 < current_price:
                support_candidates.append(("MA10", ma10))
            if ma20 < current_price:
                support_candidates.append(("MA20", ma20))
            if ma60 < current_price:
                support_candidates.append(("MA60", ma60))
            
            # 加入近期低點
            if recent_low < current_price:
                support_candidates.append(("近低", recent_low))
            if mid_low < current_price and mid_low != recent_low:
                support_candidates.append(("中低", mid_low))
            
            # 整數關卡
            round_down = (current_price // 10) * 10
            if round_down < current_price:
                support_candidates.append(("整數關卡", round_down))
            
            # 排序並取最近兩個支撐位 (從高到低)
            support_candidates.sort(key=lambda x: x[1], reverse=True)
            support_1 = support_candidates[0][1] if len(support_candidates) >= 1 else current_price * 0.95
            support_2 = support_candidates[1][1] if len(support_candidates) >= 2 else current_price * 0.90
            
            # ========== 其他技術指標 ==========
            
            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_14 = rsi.iloc[-1] if not rsi.empty else 50
            
            # MACD
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal_line = macd.ewm(span=9, adjust=False).mean()
            macd_value = macd.iloc[-1] if not macd.empty else 0
            macd_signal_value = signal_line.iloc[-1] if not signal_line.empty else 0
            
            # KD
            low_min = low.rolling(window=9).min()
            high_max = high.rolling(window=9).max()
            rsv = 100 * (close - low_min) / (high_max - low_min)
            k = rsv.ewm(span=3, adjust=False).mean()
            d = k.ewm(span=3, adjust=False).mean()
            kd_k = k.iloc[-1] if not k.empty else 50
            kd_d = d.iloc[-1] if not d.empty else 50
            
            # 布林通道
            bb_middle = close.rolling(20).mean()
            bb_std = close.rolling(20).std()
            bb_upper = bb_middle + (bb_std * 2)
            bb_lower = bb_middle - (bb_std * 2)
            bb_width = ((bb_upper - bb_lower) / bb_middle * 100).iloc[-1] if len(close) >= 20 else 0
            
            # 乖離率
            deviation_20d = ((current_price - ma20) / ma20 * 100) if ma20 else 0
            deviation_60d = ((current_price - ma60) / ma60 * 100) if ma60 else 0
            
            # 趨勢判斷
            if ma5 > ma10 > ma20:
                trend = "多頭"
            elif ma5 < ma10 < ma20:
                trend = "空頭"
            else:
                trend = "盤整"
            
            # 成交量分析
            avg_volume_20 = volume.rolling(20).mean().iloc[-1] if len(volume) >= 20 else volume.mean()
            avg_volume_5 = volume.rolling(5).mean().iloc[-1] if len(volume) >= 5 else volume.mean()
            current_volume = volume.iloc[-1] if not volume.empty else 0
            volume_ratio = current_volume / avg_volume_5 if avg_volume_5 else 1
            
            # ========== 量價分析指標 ==========
            
            # 計算 OBV (On-Balance Volume) 能量潮
            obv_values = []
            obv_current = 0
            close_list = close.tolist()
            volume_list = volume.tolist()
            for i in range(len(close_list)):
                if i == 0:
                    obv_current = volume_list[i]
                else:
                    if close_list[i] > close_list[i-1]:
                        obv_current += volume_list[i]
                    elif close_list[i] < close_list[i-1]:
                        obv_current -= volume_list[i]
                obv_values.append(obv_current)
            
            obv = obv_current
            obv_5d_ago = obv_values[-6] if len(obv_values) >= 6 else obv_values[0]
            obv_trend = "bullish" if obv > obv_5d_ago else ("bearish" if obv < obv_5d_ago else "neutral")
            
            # ===== 計算 VWAP (成交量加權平均價) =====
            # 🔧 修正：優先使用當日即時 VWAP，而非歷史平均
            try:
                from app.services.vwap_tracker import vwap_tracker
                
                # 先嘗試獲取當日即時 VWAP
                realtime_vwap = vwap_tracker.get_vwap(stock_code)
                
                if realtime_vwap > 0:
                    # ✅ 使用當日即時 VWAP
                    vwap = realtime_vwap
                    vwap_deviation = vwap_tracker.get_deviation(stock_code, current_price)
                    logger.debug(f"{stock_code} 使用當日即時 VWAP: {vwap:.2f}, 乖離: {vwap_deviation:.2f}%")
                else:
                    # ⚠️ 沒有 tick 資料，估算當日 VWAP（使用今日開盤後的資料）
                    # 取最近 1 天的資料（而非 6 個月）
                    today_typical = (high.iloc[-1] + low.iloc[-1] + close.iloc[-1]) / 3
                    today_volume = volume.iloc[-1]
                    
                    # 如果有今天的開盤價，用開盤價估算
                    if len(close) >= 1:
                        # 估算當日 VWAP = (開盤 + 最高 + 最低 + 收盤) / 4
                        vwap_est = (high.iloc[-1] + low.iloc[-1] + close.iloc[-1] * 2) / 4
                        vwap = vwap_est
                        vwap_deviation = ((current_price - vwap) / vwap * 100) if vwap else 0
                        logger.debug(f"{stock_code} 估算當日 VWAP: {vwap:.2f}, 乖離: {vwap_deviation:.2f}%")
                    else:
                        vwap = current_price
                        vwap_deviation = 0
                        
            except Exception as e:
                # 回退：使用簡單估算（今日資料）
                logger.warning(f"VWAP 計算異常: {e}")
                if len(close) >= 1:
                    vwap = (high.iloc[-1] + low.iloc[-1] + close.iloc[-1] * 2) / 4
                    vwap_deviation = ((current_price - vwap) / vwap * 100) if vwap else 0
                else:
                    vwap = current_price
                    vwap_deviation = 0
            
            # 量價確認分析
            price_change = (current_price / prev_close - 1) * 100 if prev_close else 0
            prev_volume = volume.iloc[-2] if len(volume) >= 2 else current_volume
            volume_change = ((current_volume - prev_volume) / prev_volume * 100) if prev_volume else 0
            
            # 判斷量價關係
            if price_change > 0 and volume_change > 0:
                volume_price_confirmation = "價漲量增"
                confirmation_signal = "bullish_confirmation"
                confirmation_strength = min(abs(price_change) * abs(volume_change) / 100, 1.0)
            elif price_change > 0 and volume_change <= 0:
                volume_price_confirmation = "價漲量縮"
                confirmation_signal = "caution"
                confirmation_strength = 0.3
            elif price_change < 0 and volume_change > 0:
                volume_price_confirmation = "價跌量增"
                confirmation_signal = "bearish_confirmation"
                confirmation_strength = min(abs(price_change) * abs(volume_change) / 100, 1.0)
            elif price_change < 0 and volume_change <= 0:
                volume_price_confirmation = "價跌量縮"
                confirmation_signal = "bearish_weakness"
                confirmation_strength = 0.4
            else:
                volume_price_confirmation = "中性"
                confirmation_signal = "neutral"
                confirmation_strength = 0.0
            
            # 量價背離檢測 (近20日)
            divergence_detected = False
            divergence_type = "none"
            divergence_description = ""
            
            if len(close) >= 20 and len(obv_values) >= 20:
                # 價格創新高，但 OBV 沒有創新高 -> 看跌背離
                recent_price_high = close.tail(20).max()
                recent_price_high_idx = close.tail(20).idxmax()
                prev_period_high = close.iloc[-40:-20].max() if len(close) >= 40 else close.iloc[:-20].max() if len(close) > 20 else 0
                
                recent_obv = obv_values[-1]
                prev_obv_high = max(obv_values[-40:-20]) if len(obv_values) >= 40 else max(obv_values[:-20]) if len(obv_values) > 20 else obv_values[0]
                
                if recent_price_high > prev_period_high and recent_obv < prev_obv_high:
                    divergence_detected = True
                    divergence_type = "bearish_divergence"
                    divergence_description = "價格創新高但成交量能未跟上，可能反轉下跌"
                
                # 價格創新低，但 OBV 沒有創新低 -> 看漲背離
                recent_price_low = close.tail(20).min()
                prev_period_low = close.iloc[-40:-20].min() if len(close) >= 40 else close.iloc[:-20].min() if len(close) > 20 else float('inf')
                
                prev_obv_low = min(obv_values[-40:-20]) if len(obv_values) >= 40 else min(obv_values[:-20]) if len(obv_values) > 20 else obv_values[0]
                
                if recent_price_low < prev_period_low and recent_obv > prev_obv_low:
                    divergence_detected = True
                    divergence_type = "bullish_divergence"
                    divergence_description = "價格創新低但成交量能未跟破，可能反轉上漲"
            
            # 成交量趨勢
            if avg_volume_5 > avg_volume_20 * 1.2:
                volume_trend = "increasing"
            elif avg_volume_5 < avg_volume_20 * 0.8:
                volume_trend = "decreasing"
            else:
                volume_trend = "stable"
            
            # 量價趨勢預測
            bullish_score = 0
            bearish_score = 0
            
            # 量價確認影響
            if confirmation_signal == "bullish_confirmation":
                bullish_score += 30
            elif confirmation_signal == "bearish_confirmation":
                bearish_score += 30
            elif confirmation_signal == "caution":
                bearish_score += 10
            elif confirmation_signal == "bearish_weakness":
                bullish_score += 10
            
            # OBV 趨勢影響
            if obv_trend == "bullish":
                bullish_score += 20
            elif obv_trend == "bearish":
                bearish_score += 20
            
            # 背離影響
            if divergence_type == "bullish_divergence":
                bullish_score += 25
            elif divergence_type == "bearish_divergence":
                bearish_score += 25
            
            # 技術面趨勢影響
            if trend == "多頭":
                bullish_score += 15
            elif trend == "空頭":
                bearish_score += 15
            
            # VWAP 影響
            if vwap_deviation > 2:
                bearish_score += 5  # 價格高於 VWAP，可能回調
            elif vwap_deviation < -2:
                bullish_score += 5  # 價格低於 VWAP，可能反彈
            
            # 綜合預測
            total_score = bullish_score + bearish_score
            if total_score > 0:
                up_prob = bullish_score / total_score
                down_prob = bearish_score / total_score
            else:
                up_prob = 0.33
                down_prob = 0.33
            sideways_prob = max(0, 1 - up_prob - down_prob)
            
            if bullish_score > bearish_score * 1.5:
                predicted_direction = "up"
                trend_direction = "bullish"
            elif bearish_score > bullish_score * 1.5:
                predicted_direction = "down"
                trend_direction = "bearish"
            else:
                predicted_direction = "sideways"
                trend_direction = "sideways"
            
            trend_confidence = max(bullish_score, bearish_score) / max(total_score, 1) * 100
            
            # 關鍵量價訊號
            key_signals = []
            if volume_ratio > 2:
                key_signals.append("成交量爆發 (量比>2)")
            if volume_ratio > 1.5 and price_change > 2:
                key_signals.append("放量突破")
            if volume_ratio < 0.5:
                key_signals.append("量能萎縮")
            if divergence_detected:
                key_signals.append(f"量價背離 ({divergence_type})")
            if obv_trend == "bullish" and trend == "多頭":
                key_signals.append("OBV確認多頭")
            if obv_trend == "bearish" and trend == "空頭":
                key_signals.append("OBV確認空頭")
            
            # 計算買賣力道 (基於 RSI 與量價預測)
            # 💡 買賣力道 = (RSI * 0.4) + (up_prob * 60)
            buy_pressure = (rsi_14 * 0.4) + (up_prob * 60)
            buy_pressure = max(10, min(90, buy_pressure))
            sell_pressure = 100 - buy_pressure
            
            return {
                "current_price": round(current_price, 2),
                "open": round(hist['Open'].iloc[-1], 2) if not hist.empty else 0,
                "high": round(hist['High'].iloc[-1], 2) if not hist.empty else 0,
                "low": round(hist['Low'].iloc[-1], 2) if not hist.empty else 0,
                "volume": int(current_volume),
                "avg_volume_20": int(avg_volume_20),
                "avg_volume_5": int(avg_volume_5),
                "volume_ratio": round(volume_ratio, 2),
                # MA 均線
                "ma5": round(ma5, 2),
                "ma10": round(ma10, 2),
                "ma20": round(ma20, 2),
                "ma60": round(ma60, 2),
                # MA 分析
                "ma_arrangement": ma_arrangement,
                "ma_signal": ma_signal,
                "ma_trend": ma_trend,
                # 壓力支撐
                "resistance_1": round(resistance_1, 2),
                "resistance_2": round(resistance_2, 2),
                "support_1": round(support_1, 2),
                "support_2": round(support_2, 2),
                # 其他技術指標
                "rsi_14": round(rsi_14, 2),
                "macd": round(macd_value, 4),
                "macd_signal": "多頭強勢" if macd_value > macd_signal_value else "空頭弱勢",
                "macd_histogram": round(macd_value - macd_signal_value, 4),
                "kd_k": round(kd_k, 2),
                "kd_d": round(kd_d, 2),
                "bb_width": round(bb_width, 2),
                "deviation_20d": round(deviation_20d, 2),
                "deviation_60d": round(deviation_60d, 2),
                "trend": trend,
                "prev_close": round(hist['Close'].iloc[-2], 2) if len(hist) >= 2 else current_price,
                "change_pct": round((current_price / hist['Close'].iloc[-2] - 1) * 100, 2) if len(hist) >= 2 else 0,
                # ========== 量價分析 (新增) ==========
                "volume_price_analysis": {
                    "trend_direction": trend_direction,
                    "trend_confidence": round(trend_confidence, 2),
                    "volume_price_confirmation": volume_price_confirmation,
                    "confirmation_signal": confirmation_signal,
                    "confirmation_strength": round(confirmation_strength, 2),
                    "divergence_detected": divergence_detected,
                    "divergence_type": divergence_type,
                    "divergence_description": divergence_description,
                    "volume_ratio": round(volume_ratio, 2),
                    "volume_trend": volume_trend,
                    "volume_sma5": int(avg_volume_5),
                    "volume_sma20": int(avg_volume_20),
                    "obv": obv,
                    "obv_trend": obv_trend,
                    "vwap": round(vwap, 2),
                    "vwap_deviation": round(vwap_deviation, 2),
                    "key_signals": key_signals,
                    "buy_pressure_percent": round(buy_pressure, 1),
                    "sell_pressure_percent": round(sell_pressure, 1),
                    "predicted_direction": predicted_direction,
                    "prediction_probability": {
                        "up": round(up_prob, 2),
                        "down": round(down_prob, 2),
                        "sideways": round(sideways_prob, 2)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"取得股價資料失敗: {e}")
            return {}
    
    async def _get_financial_data(self, stock_code: str) -> Dict:
        """取得財務資料"""
        try:
            import yfinance as yf
            
            # 使用 patch_yfinance 取得正確的後綴
            try:
                from app.patch_yfinance import fix_taiwan_symbol
                symbol = fix_taiwan_symbol(stock_code)
            except ImportError:
                symbol = f"{stock_code}.TW"
            
            import asyncio
            ticker = yf.Ticker(symbol)
            try:
                info = await asyncio.wait_for(
                    asyncio.to_thread(lambda: ticker.info),
                    timeout=8.0
                )
            except (asyncio.TimeoutError, Exception):
                info = {}
            
            if not info or len(info) < 5:
                # 嘗試另一種格式
                alt_symbol = f"{stock_code}.TWO" if ".TW" in symbol and ".TWO" not in symbol else f"{stock_code}.TW"
                ticker = yf.Ticker(alt_symbol)
                try:
                    info = await asyncio.wait_for(
                        asyncio.to_thread(lambda: ticker.info),
                        timeout=8.0
                    )
                except (asyncio.TimeoutError, Exception):
                    info = {}
            
            # 取得資產負債表
            balance_sheet = ticker.balance_sheet
            income_stmt = ticker.income_stmt
            cash_flow = ticker.cashflow
            
            # 計算財務比率
            roe = info.get('returnOnEquity', 0) or 0
            eps = info.get('trailingEps', 0) or 0
            
            # 取得季度 EPS (只顯示當季數據)
            quarterly_eps = []
            try:
                quarterly_income = ticker.quarterly_income_stmt
                if quarterly_income is not None and not quarterly_income.empty:
                    # 優先使用 Diluted EPS
                    eps_row_name = None
                    for row_name in ['Diluted EPS', 'Basic EPS']:
                        if row_name in quarterly_income.index:
                            eps_row_name = row_name
                            break
                    
                    if eps_row_name:
                        # 只取最近4季
                        for col in quarterly_income.columns[:4]:
                            try:
                                val = quarterly_income.loc[eps_row_name, col]
                                if val is not None and not (isinstance(val, float) and (val != val)):  # 排除 NaN
                                    if hasattr(col, 'year'):
                                        year = col.year
                                        quarter = (col.month - 1) // 3 + 1
                                        label = f"{year}Q{quarter}"
                                    else:
                                        label = str(col)
                                    quarterly_eps.append({
                                        "quarter": label,
                                        "eps": round(float(val), 2)
                                    })
                            except Exception:
                                continue
                
                # 🆕 Fallback: 如果 yfinance 沒資料，嘗試 GoodInfo
                if not quarterly_eps:
                    try:
                        from app.services.goodinfo_crawler import goodinfo_crawler
                        goodinfo_eps = await goodinfo_crawler.get_stock_eps_history(stock_code)
                        if goodinfo_eps:
                            for item in goodinfo_eps:
                                quarterly_eps.append({
                                    "quarter": item.get("quarter", "-"),
                                    "eps": item.get("eps", 0),
                                    "roe": item.get("roe", 0)
                                })
                            logger.info(f"✅ Fallback to GoodInfo for {stock_code} EPS success")
                    except Exception as ge:
                        logger.warning(f"GoodInfo Fallback 失敗: {ge}")
                        
            except Exception as qe:
                logger.debug(f"取得季度 EPS 失敗: {qe}")
            
            # 營收成長 (3年)
            revenue_growth = info.get('revenueGrowth', 0) or 0
            
            # 毛利率
            gross_margin = info.get('grossMargins', 0) or 0
            
            # 負債比
            debt_to_equity = info.get('debtToEquity', 0) or 0
            debt_ratio = debt_to_equity / (1 + debt_to_equity) * 100 if debt_to_equity else 0
            
            # 流動比率
            current_ratio = info.get('currentRatio', 0) or 0
            
            # 速動比率
            quick_ratio = info.get('quickRatio', 0) or 0
            
            # PE, PB
            pe_ratio = info.get('trailingPE', 0) or 0
            pb_ratio = info.get('priceToBook', 0) or 0
            
            # 殖利率
            dividend_yield = (info.get('dividendYield', 0) or 0) * 100
            
            # PEG
            peg_ratio = info.get('pegRatio', 0) or 0
            
            # EV/EBITDA
            ev_ebitda = info.get('enterpriseToEbitda', 0) or 0
            
            # 自由現金流
            free_cash_flow = info.get('freeCashflow', 0) or 0
            
            return {
                "roe": round(roe * 100 if roe < 1 else roe, 2),
                "eps": round(eps, 2),
                "quarterly_eps": quarterly_eps,  # 季度 EPS 資料
                "revenue_growth_3y": round(revenue_growth * 100, 2),
                "gross_margin": round(gross_margin * 100 if gross_margin < 1 else gross_margin, 2),
                "debt_ratio": round(debt_ratio, 2),
                "current_ratio": round(current_ratio, 2),
                "quick_ratio": round(quick_ratio, 2),
                "interest_coverage": 0,  # Yahoo 沒有直接提供
                "free_cash_flow": round(free_cash_flow / 1e8, 2) if free_cash_flow else 0,  # 億元
                "pe_ratio": round(pe_ratio, 2),
                "pb_ratio": round(pb_ratio, 2),
                "dividend_yield": round(dividend_yield, 2),
                "peg_ratio": round(peg_ratio, 2),
                "ev_ebitda": round(ev_ebitda, 2),
                "market_cap": info.get('marketCap', 0),
                "sector": info.get('sector', ''),
                "industry": info.get('industry', ''),
            }
            
        except Exception as e:
            logger.error(f"取得財務資料失敗: {e}")
            return {}
    
    async def _get_institutional_data(self, stock_code: str) -> Dict:
        """取得法人籌碼資料 (張)"""
        try:
            from app.services.twse_crawler import twse_crawler
            
            # 取得近 65 天法人買賣超 (支援 1D, 5D, 10D, 60D 計算)
            data = await twse_crawler.get_stock_institutional(stock_code, days=65)
            
            # 🆕 取得主力分點資料 (富邦新店等關鍵券商)
            try:
                from app.services.broker_flow_analyzer import broker_flow_analyzer
                # 以執行緒執行並加超時，避免阻塞主線程與過度延遲
                import asyncio
                broker_summary = await asyncio.wait_for(
                    asyncio.to_thread(broker_flow_analyzer.get_broker_flow_summary, stock_code, 1),
                    timeout=5.0
                )
                main_force_net = broker_summary.get('net_flow_count', 0)
                
                # 取得 MA20 作為成本參考 (如果沒有真實成本資料)
                # 這裡需要從傳入的 indicators 取得，但目前 context 只有 latest data
                # 暫時先從 data 中的 index 0 獲取目前價格作為基準，或者從外部傳入
                main_force_avg_cost = 0 
            except Exception as e:
                logger.warning(f"取得主力分點資料失敗: {e}")
                main_force_net = 0
                main_force_avg_cost = 0

            if not data:
                logger.warning(f"無法取得 {stock_code} 的法人買賣超數據")
                # 即使無法人資料，至少回傳主力分點資料
                return {
                    "foreign_net": 0, "trust_net": 0, "dealer_net": 0, "total_net": 0,
                    "main_force_net": main_force_net,
                    "main_force_avg_cost": main_force_avg_cost,
                    "institutional_history": {
                        "foreign": {"d1": 0, "d5": 0, "d10": 0},
                        "trust": {"d1": 0, "d5": 0, "d10": 0},
                        "dealer": {"d1": 0, "d5": 0, "d10": 0},
                        "total": {"d1": 0, "d5": 0, "d10": 0}
                    }
                }
            
            # 取得 MA20 成本參考 (如果有的話)
            # 在 _get_institutional_data 之前通常會先跑技術分析，但這裡是獨立的
            # 我們可以直接從 history 中推算或使用 current_price
            current_price = data[0].get('close', 0) # 如果有的話
            
            # 解析為多週期 (1D, 5D, 10D)
            history = data # data 已經是最新在前
            
            def sum_net_lots(key, days):
                # 先加總原始股數 (Shares)，再轉為張 (Lots)，避免每一天截斷產生的累積誤差
                total_shares = sum(d.get(key, 0) for d in history[:days])
                return int(total_shares / 1000)

            inst_history = {
                "foreign": {"d1": sum_net_lots('foreign_net', 1), "d5": sum_net_lots('foreign_net', 5), "d10": sum_net_lots('foreign_net', 10), "d20": sum_net_lots('foreign_net', 20)},
                "trust": {"d1": sum_net_lots('investment_net', 1), "d5": sum_net_lots('investment_net', 5), "d10": sum_net_lots('investment_net', 10), "d20": sum_net_lots('investment_net', 20)},
                "dealer": {"d1": sum_net_lots('dealer_net', 1), "d5": sum_net_lots('dealer_net', 5), "d10": sum_net_lots('dealer_net', 10), "d20": sum_net_lots('dealer_net', 20)},
            }
            # 合計
            inst_history["total"] = {
                "d1": int(inst_history["foreign"]["d1"] + inst_history["trust"]["d1"] + inst_history["dealer"]["d1"]),
                "d5": int(inst_history["foreign"]["d5"] + inst_history["trust"]["d5"] + inst_history["dealer"]["d5"]),
                "d10": int(inst_history["foreign"]["d10"] + inst_history["trust"]["d10"] + inst_history["dealer"]["d10"]),
                "d20": int(inst_history["foreign"]["d20"] + inst_history["trust"]["d20"] + inst_history["dealer"]["d20"]),
            }
            
            latest = data[0]
            
            # 🆕 加強型籌碼集中度計算 (以 5日合計 net / 該段期間總成交量)
            # 專業公式: 集中度 = (區間買賣超合計 / 區間總成交量) * 100
            total_5d_net = abs(inst_history["total"]["d5"])
            
            # 試著從 data 抓取成交量 (如果有的話) 或者使用 5000 作為基準回退
            # 1 張 = 1000 股
            avg_vol_5d = 0
            try:
                # 基於歷史資料的平均量 (d.get('volume') 是股數)
                # 注意: data 可能只有法人資料，不一定有成交量，所以需要 check
                vol_list = [d.get('volume', 0) for d in data[:5] if d.get('volume', 0) > 0]
                if vol_list:
                    avg_vol_5d = sum(vol_list) / len(vol_list) / 1000 # 轉為張
            except:
                avg_vol_5d = 0
                
            if avg_vol_5d > 0:
                # 區間總量 = avg * 5
                total_5d_vol = avg_vol_5d * 5
                chip_concentration = round((total_5d_net / total_5d_vol) * 100, 1) if total_5d_vol > 0 else 0
            else:
                # 備援：如果沒成交量資料，使用動態基準
                # 小盤股 (5d net > 1000) vs 大盤股 (5d net > 10000)
                chip_concentration = min(95, round((total_5d_net / 5000) * 15, 1)) if total_5d_net > 0 else 0
            
            # 強制上限 100%
            chip_concentration = min(100.0, chip_concentration)
            
            return {
                "foreign_net": int(latest.get('foreign_net', 0) / 1000),
                "trust_net": int(latest.get('investment_net', 0) / 1000),
                "dealer_net": int(latest.get('dealer_net', 0) / 1000),
                "total_net": int(latest.get('total_net', 0) / 1000),
                "main_force_net": main_force_net,
                "main_force_avg_cost": main_force_avg_cost,
                "chip_concentration": chip_concentration,
                "consecutive_days": latest.get('consecutive_days', 0),
                "institutional_history": inst_history,
                "source": latest.get('source', 'twse')
            }
            
        except Exception as e:
            logger.error(f"取得法人籌碼失敗: {e}")
            return {}
    
    async def _get_stock_news(self, stock_code: str) -> List[Dict]:
        """取得股票相關新聞 - 優先使用有 URL 的來源"""
        stock_name = await get_stock_name(stock_code)
        
        # 1. 優先從新聞分析服務取得有 URL 的新聞
        try:
            from app.services.news_analysis_service import news_analysis_service
            import asyncio
            # 同步爬蟲放執行緒池避免阻塞，並加超時保護
            analysis = await asyncio.wait_for(
                asyncio.to_thread(news_analysis_service.get_all_news_with_analysis),
                timeout=8.0
            )
            all_news = analysis.get('news', {}).get('all', [])
            
            # 過濾與該股票相關的新聞
            stock_related_news = []
            for news in all_news:
                title = news.get('title', '')
                stocks = news.get('stocks', [])
                
                # 檢查是否與該股票相關
                if stock_code in title or stock_name in title or stock_code in stocks:
                    stock_related_news.append({
                        "title": title,
                        "summary": title[:100],
                        "date": news.get('date', ''),
                        "source": news.get('source', '財經新聞'),
                        "url": news.get('url', ''),  # 保留 URL
                        "sentiment": news.get('sentiment', 'neutral'),
                        "impact": "medium"
                    })
            
            if len(stock_related_news) >= 2:
                logger.info(f"從新聞分析服務取得 {stock_code} 相關新聞 {len(stock_related_news)} 則")
                return stock_related_news[:5]
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"新聞分析服務取得失敗: {e}")
        
        # 2. 嘗試 yfinance 新聞（有 URL）
        news = await self._fetch_crawler_news(stock_code, stock_name)
        if news and len(news) >= 2:
            return news
        
        # 3. 最後使用 Perplexity API 補充（可能無 URL）
        # 💡 重要：這裡原本會呼叫 Perplexity，我們現在已經外部控制 quick_mode
        # 如果還是進到這裡且你想更極端優化，可以在此時多一層檢查
        if PERPLEXITY_TOKEN:
            perplexity_news = await self._fetch_perplexity_news(stock_code, stock_name)
            if perplexity_news:
                return perplexity_news
        
        return news or []
    
    async def _fetch_perplexity_news(self, stock_code: str, stock_name: str) -> List[Dict]:
        """從 Perplexity API 取得股票新聞"""
        try:
            session = await self._get_session()
            
            prompt = f"""請搜尋台股 {stock_code} {stock_name} 最近一週的相關新聞和市場分析。

請提供以下格式的 JSON 陣列，每則新聞包含：
- title: 新聞標題
- summary: 50字以內摘要
- date: 發布日期 (YYYY-MM-DD)
- source: 來源網站名稱
- url: 新聞原始連結 (完整 https 網址，如無法取得則填寫空字串)
- sentiment: 情緒 (positive/negative/neutral)
- impact: 對股價影響評估 (high/medium/low)

只回傳 JSON 陣列，不要其他文字。最多5則新聞。"""

            headers = {
                "Authorization": f"Bearer {PERPLEXITY_TOKEN}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": PERPLEXITY_MODEL,
                "messages": [
                    {"role": "system", "content": "你是專業的台股分析師，請用繁體中文回答。只回傳有效的 JSON 格式。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 1000
            }
            
            async with session.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # 解析 JSON
                    content = content.replace("```json", "").replace("```", "").strip()
                    news = json.loads(content)
                    
                    logger.info(f"Perplexity 取得 {stock_code} 新聞 {len(news)} 則")
                    return news
                else:
                    logger.warning(f"Perplexity API 失敗: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Perplexity API 錯誤: {e}")
            return []
    
    async def _fetch_crawler_news(self, stock_code: str, stock_name: str) -> List[Dict]:
        """從多個來源取得股票新聞"""
        news_list = []
        
        # 方法1: yfinance 新聞
        try:
            import yfinance as yf
            import asyncio

            def _fetch_yf_news(code):
                sym = f"{code}.TW"
                n = yf.Ticker(sym).news
                if not n:
                    sym = f"{code}.TWO"
                    n = yf.Ticker(sym).news
                return n or []

            yf_news = await asyncio.wait_for(
                asyncio.to_thread(_fetch_yf_news, stock_code),
                timeout=5.0
            )
            
            if yf_news:
                for item in yf_news[:5]:
                    # 分析標題情緒
                    title = item.get('title', '')
                    sentiment = self._simple_sentiment_analysis(title)
                    
                    # 轉換時間戳
                    timestamp = item.get('providerPublishTime', 0)
                    from datetime import datetime as dt
                    if timestamp:
                        date_str = dt.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                    else:
                        date_str = dt.now().strftime('%Y-%m-%d')
                    
                    news_list.append({
                        "title": title,
                        "summary": item.get('summary', title)[:100] if item.get('summary') else title[:100],
                        "date": date_str,
                        "source": item.get('publisher', 'Yahoo Finance'),
                        "sentiment": sentiment,
                        "impact": "medium",
                        "url": item.get('link', '')
                    })
                
                logger.info(f"yfinance 取得 {stock_code} 新聞 {len(news_list)} 則")
                
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"yfinance 新聞取得失敗: {e}")
        
        # 方法2: 新聞爬蟲
        if len(news_list) < 3:
            try:
                from app.services.news_crawler_service import news_crawler
                
                all_news = await news_crawler.crawl_all_news()
                
                # 過濾相關新聞
                for news in all_news:
                    title = news.get('title', '')
                    if stock_code in title or stock_name in title:
                        sentiment = self._simple_sentiment_analysis(title)
                        from datetime import datetime as dt
                        news_list.append({
                            "title": title,
                            "summary": title[:100],
                            "date": news.get('date', dt.now().strftime('%Y-%m-%d')),
                            "source": news.get('source', '財經新聞'),
                            "url": news.get('url', news.get('link', '')),  # 加入 URL
                            "sentiment": sentiment,
                            "impact": "medium"
                        })
                        
            except Exception as e:
                logger.warning(f"新聞爬蟲失敗: {e}")
        
        # 方法3: 如果仍然沒有新聞，生成參考性新聞
        if len(news_list) == 0:
            news_list = self._generate_reference_news(stock_code, stock_name)
        
        return news_list[:5]
    
    def _simple_sentiment_analysis(self, text: str) -> str:
        """簡單的情緒分析"""
        positive_keywords = [
            '漲', '上漲', '大漲', '飆漲', '突破', '創新高', '利多', '看好',
            '獲利', '成長', '增加', '擴張', '轉虧為盈', '超越預期', '強勢',
            '買超', '加碼', '推薦', '優於預期', '營收成長', '看多'
        ]
        negative_keywords = [
            '跌', '下跌', '大跌', '崩跌', '破底', '創新低', '利空', '看淡',
            '虧損', '衰退', '減少', '縮減', '轉盈為虧', '低於預期', '弱勢',
            '賣超', '減碼', '調降', '下修', '營收衰退', '看空'
        ]
        
        pos_count = sum(1 for kw in positive_keywords if kw in text)
        neg_count = sum(1 for kw in negative_keywords if kw in text)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"
    
    def _generate_reference_news(self, stock_code: str, stock_name: str) -> List[Dict]:
        """生成參考性新聞 (當無法取得真實新聞時)"""
        from datetime import datetime, timedelta
        
        today = datetime.now()
        
        # 根據股票產業生成相關參考新聞
        reference_news = [
            {
                "title": f"{stock_name}({stock_code}) 近期法人動態追蹤",
                "summary": f"分析師持續關注 {stock_name} 營運表現與法人買賣超動態",
                "date": today.strftime('%Y-%m-%d'),
                "source": "市場分析",
                "sentiment": "neutral",
                "impact": "medium"
            },
            {
                "title": f"台股盤勢分析：{stock_code} 技術面觀察",
                "summary": f"觀察 {stock_name} 技術指標與成交量變化，研判後續走勢",
                "date": (today - timedelta(days=1)).strftime('%Y-%m-%d'),
                "source": "技術分析",
                "sentiment": "neutral",
                "impact": "low"
            },
            {
                "title": f"產業動態：{stock_name} 所屬產業近況",
                "summary": f"追蹤 {stock_name} 相關產業供需變化與景氣循環",
                "date": (today - timedelta(days=2)).strftime('%Y-%m-%d'),
                "source": "產業研究",
                "sentiment": "neutral",
                "impact": "medium"
            }
        ]
        
        logger.info(f"生成 {stock_code} 參考性新聞 {len(reference_news)} 則")
        return reference_news


    # ==================== 評分計算方法 ====================
    
    async def _calculate_dimension_scores(
        self, 
        price_data: Dict, 
        financial_data: Dict, 
        institutional_data: Dict
    ) -> List[DimensionScore]:
        """
        計算五維度評分 (專家優化版)
        
        架構調整：
        - 合併籌碼+法人為「資金動能」避免雙重計分
        - 新增「風險控管」維度
        
        綜合評分 = 基本面(30%) + 技術面(25%) + 資金動能(30%) + 市場(10%) + 風險(5%)
        """
        scores = []
        
        # 1. 基本面評分 (權重: 30%) - 成長性 + 估值 + 財務品質
        # 專家優化：引入 PEG、PE Band、同業比較
        fundamental_score, fundamental_details = self._calculate_fundamental_score_v2(
            financial_data, price_data
        )
        scores.append(DimensionScore(
            name="基本面",
            score=fundamental_score,
            weight=0.30,
            details=fundamental_details
        ))
        
        # 2. 技術面評分 (權重: 25%)
        # 專家優化：RSI 鈍化處理、乖離率濾網、爆量異常
        technical_score, technical_details = self._calculate_technical_score_v2(
            price_data, institutional_data
        )
        scores.append(DimensionScore(
            name="技術面",
            score=technical_score,
            weight=0.25,
            details=technical_details
        ))
        
        # 3. 資金動能評分 (權重: 30%) - 合併籌碼+法人，避免雙重計分
        # 專家優化：分流主力(非法人) + 三大法人，加入借券餘額判斷
        capital_score, capital_details = self._calculate_capital_momentum_score(
            institutional_data, price_data
        )
        scores.append(DimensionScore(
            name="資金動能",
            score=capital_score,
            weight=0.30,
            details=capital_details
        ))
        
        # 4. 市場維度評分 (權重: 10%)
        market_score, market_details = self._calculate_market_score()
        scores.append(DimensionScore(
            name="市場",
            score=market_score,
            weight=0.10,
            details=market_details
        ))
        
        # 5. 風險控管評分 (權重: 5%) - 專家建議新增
        # 包含：Beta、波動率、融資使用率、散戶持股
        risk_score, risk_details = self._calculate_risk_score(
            price_data, institutional_data, financial_data
        )
        scores.append(DimensionScore(
            name="風險",
            score=risk_score,
            weight=0.05,
            details=risk_details
        ))
        
        return scores
    
    # ==================== 專家優化版評分函數 ====================
    
    def _calculate_fundamental_score_v2(
        self, financial_data: Dict, price_data: Dict
    ) -> Tuple[float, List[str]]:
        """
        計算基本面評分 (專家優化版 v2)
        
        優化項目：
        1. 引入 PEG (本益成長比) 取代單純 PE 判斷
        2. PE Band 歷史區間比較
        3. 營收 MoM 動能判斷
        4. 景氣循環股陷阱檢測
        """
        score = 50
        details = []
        
        # === 1. 成長性指標 (優化版) ===
        
        # 營收成長 - 加入 MoM 動能判斷
        revenue_growth_yoy = financial_data.get('revenue_growth_3y', 0)
        revenue_growth_mom = financial_data.get('revenue_growth_mom', 0)  # 月增率
        
        if revenue_growth_yoy > 20:
            if revenue_growth_mom >= 0:
                score += 12
                details.append(f"營收YoY強勁({revenue_growth_yoy:.1f}%) + MoM持穩")
            else:
                # 專家建議：YoY增但MoM衰退，成長趨緩
                score += 6
                details.append(f"營收YoY成長但MoM衰退({revenue_growth_mom:.1f}%)，動能趨緩⚠️")
        elif revenue_growth_yoy > 10:
            score += 5
        elif revenue_growth_yoy < 0:
            score -= 5
            details.append(f"營收衰退 ({revenue_growth_yoy:.1f}%)")
        
        # EPS 評分
        eps = financial_data.get('eps', 0)
        if eps > 5:
            score += 10
            details.append(f"EPS 優異 (${eps:.2f})")
        elif eps > 2:
            score += 5
        elif eps < 0:
            score -= 10
            details.append(f"EPS 虧損 ⚠️")
        
        # === 2. 估值指標 (專家優化版) ===
        
        pe = financial_data.get('pe_ratio', 0)
        peg = financial_data.get('peg_ratio', 0)
        pe_band_position = financial_data.get('pe_band_position', 50)  # 0-100，目前PE在歷史區間位置
        sector_avg_pe = financial_data.get('sector_avg_pe', 15)  # 產業平均PE
        
        # 景氣循環股陷阱檢測
        is_cyclical = financial_data.get('is_cyclical', False)  # 航運、面板、鋼鐵等
        
        if is_cyclical:
            # 景氣循環股：PE極低可能是高點陷阱
            if 0 < pe < 5:
                score -= 5
                details.append(f"⚠️ 景氣循環股PE極低({pe:.1f}倍)，小心高點陷阱")
            elif pe > 15:
                # 循環股PE高通常是景氣底部
                score += 5
                details.append(f"循環股PE偏高，可能接近景氣底部")
        else:
            # 非循環股：使用 PEG 判斷
            if peg > 0:
                # PEG < 1 為低估成長股
                if peg < 0.8:
                    score += 12
                    details.append(f"PEG低估({peg:.2f})，具成長價值")
                elif peg < 1.0:
                    score += 8
                    details.append(f"PEG合理({peg:.2f})")
                elif peg > 2.0:
                    score -= 5
                    details.append(f"PEG偏高({peg:.2f})，估值過高")
            else:
                # PEG 無效時，使用 PE Band
                if pe_band_position < 20:
                    score += 10
                    details.append(f"PE處歷史低檔區({pe_band_position:.0f}%)")
                elif pe_band_position > 80:
                    score -= 5
                    details.append(f"PE處歷史高檔區({pe_band_position:.0f}%)⚠️")
        
        # 同產業PE比較
        if sector_avg_pe > 0 and pe > 0:
            pe_vs_sector = (pe / sector_avg_pe - 1) * 100
            if pe_vs_sector < -20:
                score += 5
                details.append(f"PE低於產業均值{abs(pe_vs_sector):.0f}%")
            elif pe_vs_sector > 30:
                score -= 3
                details.append(f"PE高於產業均值{pe_vs_sector:.0f}%")
        
        # 殖利率
        dividend_yield = financial_data.get('dividend_yield', 0)
        if dividend_yield > 5:
            score += 8
            details.append(f"高殖利率 ({dividend_yield:.1f}%)")
        elif dividend_yield > 3:
            score += 4
        
        # === 3. 財務品質 ===
        
        roe = financial_data.get('roe', 0)
        if roe > 15:
            score += 8
            details.append(f"ROE 優異 ({roe:.1f}%)")
        elif roe > 10:
            score += 4
        elif roe < 5:
            score -= 5
        
        debt_ratio = financial_data.get('debt_ratio', 0)
        if debt_ratio < 30:
            score += 4
            details.append(f"負債比低 ({debt_ratio:.1f}%)")
        elif debt_ratio > 70:
            score -= 8
            details.append(f"負債比過高 ({debt_ratio:.1f}%) ⚠️")
        
        return min(max(score, 0), 100), details
    
    def _calculate_technical_score_v2(
        self, price_data: Dict, institutional_data: Dict
    ) -> Tuple[float, List[str]]:
        """
        計算技術面評分 (專家優化版 v2)
        
        優化項目：
        1. RSI 高檔鈍化處理 - 超強勢不扣分
        2. RSI 底背離才給分
        3. 乖離率濾網 - 漲多風險扣分
        4. 爆量異常訊號 - 高檔爆量不漲強烈賣出
        """
        score = 50
        details = []
        
        # === 趨勢判斷 ===
        trend = price_data.get('trend', '盤整')
        if trend == "多頭":
            score += 12
            details.append("均線多頭排列，趨勢向上")
        elif trend == "空頭":
            score -= 12
            details.append("均線空頭排列，趨勢向下 ⚠️")
        else:
            details.append("技術面盤整格局")
        
        # === RSI 專家優化 ===
        rsi = price_data.get('rsi_14', 50)
        macd = price_data.get('macd', 0)
        macd_histogram = price_data.get('macd_histogram', 0)
        rsi_divergence = price_data.get('rsi_divergence', None)  # bullish / bearish / none
        
        if rsi > 80:
            # 高檔鈍化判定：RSI > 80 且 MACD 柱狀體持續放大
            if macd_histogram > 0 and macd > 0:
                # 超強勢狀態，不扣分反而加分
                score += 8
                details.append(f"RSI高檔鈍化({rsi:.0f})，超強勢延續 🔥")
            else:
                # MACD 動能衰退，開始扣分
                score -= 8
                details.append(f"RSI過熱({rsi:.0f})且動能衰退，注意回調")
        elif rsi > 70:
            # 過熱但未鈍化
            if macd_histogram > 0:
                score += 3  # 動能仍強，小幅加分
            else:
                score -= 5
                details.append(f"RSI過熱({rsi:.0f})，短期可能回調")
        elif rsi < 30:
            # 超賣區：專家建議等底背離才給分
            if rsi_divergence == 'bullish':
                score += 12
                details.append(f"RSI超賣({rsi:.0f})+ 底背離，反彈訊號 ✅")
            else:
                # 只是超賣，不急著給分
                score += 3
                details.append(f"RSI超賣({rsi:.0f})，待確認底背離")
        
        # === MACD ===
        if macd > 0:
            score += 8
            if macd_histogram > 0:
                details.append("MACD 零軸上方且動能增強")
            else:
                details.append("MACD 零軸上方")
        elif macd < 0:
            score -= 5
        
        # === 乖離率濾網 (專家建議) ===
        deviation_20d = price_data.get('deviation_20d', 0)
        deviation_60d = price_data.get('deviation_60d', 0)
        
        if abs(deviation_20d) > 20:
            # 乖離過大，即便多頭也要扣分
            if deviation_20d > 20:
                score -= 10
                details.append(f"乖離率過高({deviation_20d:.1f}%)，漲多風險 ⚠️")
            elif deviation_20d < -20:
                score += 5  # 超跌可能反彈
                details.append(f"乖離率過低({deviation_20d:.1f}%)，超跌反彈機會")
        
        # === 成交量異常 (專家建議) ===
        volume_ratio = price_data.get('volume_ratio', 1)
        price_change = price_data.get('change_pct', 0)
        current_price = price_data.get('current_price', 0)
        
        # 爆量長黑或高檔爆量不漲 = 強烈賣出訊號
        if volume_ratio > 2 and price_change < -3:
            score -= 15
            details.append(f"⚠️ 爆量長黑({volume_ratio:.1f}x量, {price_change:.1f}%)，強烈賣出訊號")
        elif volume_ratio > 2 and abs(price_change) < 1 and rsi > 60:
            # 高檔爆量不漲
            score -= 10
            details.append(f"⚠️ 高檔爆量不漲({volume_ratio:.1f}x量)，警戒出貨")
        elif volume_ratio > 1.5 and price_change > 2:
            score += 5
            details.append(f"放量上漲({volume_ratio:.1f}x量, +{price_change:.1f}%)")
        
        # === 法人籌碼 (簡化，主要邏輯在資金動能) ===
        total_net = institutional_data.get('total_net', 0)
        if total_net > 0:
            score += 5
        elif total_net < 0:
            score -= 3
        
        return min(max(score, 0), 100), details
    
    def _calculate_capital_momentum_score(
        self, institutional_data: Dict, price_data: Dict
    ) -> Tuple[float, List[str]]:
        """
        計算資金動能評分 (合併籌碼+法人，避免雙重計分)
        
        專家建議：
        1. 分流：主力(非法人大戶) vs 三大法人
        2. 加入借券餘額判斷假買真空
        3. 主力買均價判斷是否高於成本
        4. 散戶指標作為反向參考
        """
        score = 50
        details = []
        
        # === 三大法人合計 (主要權重) ===
        foreign_net = institutional_data.get('foreign_net', 0)
        trust_net = institutional_data.get('trust_net', 0)
        dealer_net = institutional_data.get('dealer_net', 0)
        total_net = institutional_data.get('total_net', 0)
        consecutive_days = institutional_data.get('consecutive_days', 0)
        
        # 外資 (權重最高)
        if foreign_net > 5000:
            score += 15
            details.append(f"外資大買超 {foreign_net:,} 張")
        elif foreign_net > 1000:
            score += 8
            details.append(f"外資買超 {foreign_net:,} 張")
        elif foreign_net < -5000:
            score -= 15
            details.append(f"外資大賣超 {abs(foreign_net):,} 張 ⚠️")
        elif foreign_net < -1000:
            score -= 8
            details.append(f"外資賣超 {abs(foreign_net):,} 張")
        
        # 專家建議：借券餘額判斷假買真空
        foreign_short_balance = institutional_data.get('foreign_short_balance', 0)
        if foreign_net > 1000 and foreign_short_balance > foreign_net * 0.5:
            # 外資買超但借券賣出餘額暴增，可能是假買真空
            score -= 8
            details.append(f"⚠️ 外資買超但借券餘額高，疑似避險操作")
        
        # 投信 (中型股影響大)
        if trust_net > 500:
            score += 10
            details.append(f"投信買超 {trust_net:,} 張")
        elif trust_net < -500:
            score -= 8
            details.append(f"投信賣超 {abs(trust_net):,} 張")
        
        # 自營商 (短線指標)
        if dealer_net > 500:
            score += 5
        elif dealer_net < -500:
            score -= 3
        
        # === 主力買賣超 (非法人大戶) ===
        main_force_net = institutional_data.get('main_force_net', 0)
        main_force_avg_cost = institutional_data.get('main_force_avg_cost', 0)
        current_price = price_data.get('current_price', 0)
        
        if main_force_net > 1000:
            # 專家建議：檢查目前價格是否高於主力買均價
            if main_force_avg_cost > 0 and current_price > main_force_avg_cost * 1.3:
                # 價格已高於主力成本30%，主力可能隨時倒貨
                score += 8  # 打折給分
                details.append(f"主力買超但價格已高於成本 30%+，注意倒貨風險")
            else:
                score += 15
                details.append(f"主力大幅買超 {main_force_net:,} 張")
        elif main_force_net > 500:
            score += 8
            details.append(f"主力買超 {main_force_net:,} 張")
        elif main_force_net < -500:
            score -= 10
            details.append(f"主力賣超 {abs(main_force_net):,} 張")
        elif main_force_net < -1000:
            score -= 18
            details.append(f"主力大幅賣超 {abs(main_force_net):,} 張 ⚠️")
        
        # === 籌碼集中度 ===
        chip_concentration = institutional_data.get('chip_concentration', 0)
        if chip_concentration > 60:
            score += 10
            details.append(f"籌碼高度集中 ({chip_concentration:.1f}%)")
        elif chip_concentration < 20:
            score -= 8
            details.append(f"籌碼分散 ({chip_concentration:.1f}%)")
        
        # === 連續買賣超天數 ===
        if consecutive_days > 5:
            score += 8
            details.append(f"連續買超 {consecutive_days} 天")
        elif consecutive_days < -5:
            score -= 8
            details.append(f"連續賣超 {abs(consecutive_days)} 天")
        
        # === 散戶反向指標 (專家建議) ===
        margin_increase_ratio = institutional_data.get('margin_increase_ratio', 0)
        if margin_increase_ratio > 10:
            # 融資大增，散戶追漲，反向指標扣分
            score -= 5
            details.append(f"融資增加 {margin_increase_ratio:.1f}%，散戶追漲 (反向指標)")
        elif margin_increase_ratio < -10:
            # 融資減少，可能是洗盤或停損
            score += 3
            details.append(f"融資減少，籌碼沉澱")
        
        return min(max(score, 0), 100), details
    
    def _calculate_risk_score(
        self, price_data: Dict, institutional_data: Dict, financial_data: Dict
    ) -> Tuple[float, List[str]]:
        """
        計算風險控管評分 (專家建議新增)
        
        高分=低風險，低分=高風險
        考量：Beta、波動率、融資使用率、散戶持股
        """
        score = 70  # 預設中等風險
        details = []
        
        # === Beta 值 (風險係數) ===
        beta = price_data.get('beta', 1.0)
        if beta < 0.8:
            score += 10
            details.append(f"Beta低({beta:.2f})，防禦性佳")
        elif beta > 1.5:
            score -= 15
            details.append(f"Beta高({beta:.2f})，波動大風險高 ⚠️")
        elif beta > 1.2:
            score -= 8
            details.append(f"Beta偏高({beta:.2f})")
        
        # === 波動率 ===
        volatility = price_data.get('volatility', 0)  # 年化波動率
        if volatility > 50:
            score -= 12
            details.append(f"波動率極高({volatility:.1f}%) ⚠️")
        elif volatility > 30:
            score -= 5
            details.append(f"波動率偏高({volatility:.1f}%)")
        elif volatility < 15:
            score += 8
            details.append(f"波動率低({volatility:.1f}%)，穩定性佳")
        
        # === 融資使用率 ===
        margin_usage = institutional_data.get('margin_usage', 0)
        if margin_usage > 50:
            score -= 15
            details.append(f"融資使用率過高({margin_usage:.1f}%) ⚠️")
        elif margin_usage > 30:
            score -= 5
            details.append(f"融資使用率偏高({margin_usage:.1f}%)")
        elif margin_usage < 10:
            score += 5
            details.append(f"融資使用率低({margin_usage:.1f}%)")
        
        # === 散戶持股比例 (反向指標) ===
        retail_concentration = institutional_data.get('retail_concentration', 0)
        if retail_concentration > 70:
            score -= 10
            details.append(f"散戶持股比例高({retail_concentration:.1f}%)，籌碼凌亂")
        elif retail_concentration < 30:
            score += 8
            details.append(f"法人/大戶持股為主({100-retail_concentration:.1f}%)")
        
        # === 負債風險 ===
        debt_ratio = financial_data.get('debt_ratio', 0)
        if debt_ratio > 80:
            score -= 10
            details.append(f"負債比過高({debt_ratio:.1f}%)，財務風險")
        
        return min(max(score, 0), 100), details
    
    # 保留舊函數作為備援 (向下相容)
    
    def _calculate_chip_score(self, institutional_data: Dict) -> Tuple[float, List[str]]:
        """計算籌碼面評分（券商買賣超）"""
        score = 50
        details = []
        
        # 主力買賣超
        main_force_net = institutional_data.get('main_force_net', 0)
        if main_force_net > 1000:
            score += 25
            details.append(f"主力大幅買超 {main_force_net:,} 張")
        elif main_force_net > 500:
            score += 15
            details.append(f"主力買超 {main_force_net:,} 張")
        elif main_force_net > 0:
            score += 5
        elif main_force_net < -500:
            score -= 15
            details.append(f"主力賣超 {abs(main_force_net):,} 張")
        elif main_force_net < -1000:
            score -= 25
            details.append(f"主力大幅賣超 {abs(main_force_net):,} 張")
        
        # 籌碼集中度
        chip_concentration = institutional_data.get('chip_concentration', 0)
        if chip_concentration > 60:
            score += 15
            details.append(f"籌碼高度集中 ({chip_concentration:.1f}%)")
        elif chip_concentration > 40:
            score += 5
        elif chip_concentration < 20:
            score -= 10
            details.append(f"籌碼分散 ({chip_concentration:.1f}%)")
        
        # 連續買賣超天數
        consecutive_days = institutional_data.get('consecutive_days', 0)
        if consecutive_days > 5:
            score += 10
            details.append(f"連續買超 {consecutive_days} 天")
        elif consecutive_days < -5:
            score -= 10
            details.append(f"連續賣超 {abs(consecutive_days)} 天")
        
        return min(max(score, 0), 100), details
    
    def _calculate_institution_score(self, institutional_data: Dict) -> Tuple[float, List[str]]:
        """計算法人評分（三大法人）"""
        score = 50
        details = []
        
        # 外資
        foreign_net = institutional_data.get('foreign_net', 0)
        if foreign_net > 5000:
            score += 20
            details.append(f"外資大幅買超 {foreign_net:,} 張")
        elif foreign_net > 1000:
            score += 10
            details.append(f"外資買超 {foreign_net:,} 張")
        elif foreign_net < -1000:
            score -= 10
            details.append(f"外資賣超 {abs(foreign_net):,} 張")
        elif foreign_net < -5000:
            score -= 20
            details.append(f"外資大幅賣超 {abs(foreign_net):,} 張")
        
        # 投信
        trust_net = institutional_data.get('trust_net', 0)
        if trust_net > 500:
            score += 15
            details.append(f"投信買超 {trust_net:,} 張")
        elif trust_net < -500:
            score -= 10
            details.append(f"投信賣超 {abs(trust_net):,} 張")
        
        # 自營商
        dealer_net = institutional_data.get('dealer_net', 0)
        if dealer_net > 500:
            score += 10
        elif dealer_net < -500:
            score -= 5
        
        # 三大法人合計
        total_net = institutional_data.get('total_net', 0)
        if total_net > 10000:
            score += 5
            details.append(f"法人合計買超 {total_net:,} 張")
        
        return min(max(score, 0), 100), details
    
    def _calculate_market_score(self) -> Tuple[float, List[str]]:
        """計算市場維度評分（使用市場分析服務）"""
        score = 50  # 預設中性
        details = []
        
        try:
            from app.services.market_dimension_analyzer import market_dimension_analyzer
            
            # 獲取市場分析結果
            market_result = market_dimension_analyzer.analyze()
            
            # 將 0-10 分數轉換為 0-100
            market_total = market_result.get('total_score', 5.0)
            score = market_total * 10
            
            # 添加詳細說明
            details.append(f"市場狀態: {market_result.get('market_status', '未知')}")
            
            components = market_result.get('components', {})
            
            # 大盤趨勢
            trend = components.get('trend', {})
            trend_score = trend.get('score', 0)
            if trend_score >= 3:
                details.append(f"大盤趨勢強勢 ({trend_score:.1f}/4)")
            elif trend_score >= 2:
                details.append(f"大盤趨勢中性 ({trend_score:.1f}/4)")
            else:
                details.append(f"大盤趨勢偏弱 ({trend_score:.1f}/4)")
            
            # 成交量
            volume = components.get('volume', {})
            volume_score = volume.get('score', 0)
            if volume_score >= 2:
                details.append(f"市場量能充足 ({volume_score:.1f}/3)")
            else:
                details.append(f"市場量能不足 ({volume_score:.1f}/3)")
            
            # 外資期貨
            futures = components.get('futures', {})
            futures_score = futures.get('score', 0)
            if futures_score >= 1.2:
                details.append("外資期貨偏多")
            elif futures_score <= 0.8:
                details.append("外資期貨偏空")
            
            # VIX
            vix = components.get('vix', {})
            vix_info = vix.get('info', {})
            vix_status = vix_info.get('vix_status', '')
            if vix_status:
                details.append(f"VIX恐慌指數: {vix_status}")
            
            logger.info(f"市場維度評分: {score:.1f}/100")
            
        except Exception as e:
            logger.warning(f"計算市場維度評分失敗: {e}")
            details.append("市場數據暫不可用")
        
        return min(max(score, 0), 100), details

    
    def _calculate_growth_score(self, financial_data: Dict) -> Tuple[float, List[str]]:
        """計算成長性評分"""
        score = 50
        details = []
        
        # 營收成長
        revenue_growth = financial_data.get('revenue_growth_3y', 0)
        if revenue_growth > 20:
            score += 25
            details.append(f"營收成長強勁 ({revenue_growth}%)")
        elif revenue_growth > 10:
            score += 15
            details.append(f"營收穩定成長 ({revenue_growth}%)")
        elif revenue_growth > 0:
            score += 5
            details.append(f"營收微幅成長 ({revenue_growth}%)")
        else:
            score -= 15
            details.append(f"營收衰退 ({revenue_growth}%)")
        
        # EPS
        eps = financial_data.get('eps', 0)
        if eps > 5:
            score += 20
            details.append(f"EPS 優異 (${eps})")
        elif eps > 2:
            score += 10
            details.append(f"EPS 良好 (${eps})")
        elif eps > 0:
            score += 0
            details.append(f"EPS 普通 (${eps})")
        else:
            score -= 20
            details.append(f"EPS 虧損 (${eps})")
        
        return min(max(score, 0), 100), details
    
    def _calculate_valuation_score(self, financial_data: Dict) -> Tuple[float, List[str]]:
        """計算估值評分"""
        score = 50
        details = []
        
        # PE 本益比
        pe = financial_data.get('pe_ratio', 0)
        if 0 < pe < 10:
            score += 20
            details.append(f"本益比低估 ({pe}倍)")
        elif 10 <= pe < 15:
            score += 15
            details.append(f"本益比合理 ({pe}倍)")
        elif 15 <= pe < 25:
            score += 5
            details.append(f"本益比偏高 ({pe}倍)")
        elif pe >= 25:
            score -= 10
            details.append(f"本益比過高 ({pe}倍)")
        elif pe < 0:
            score -= 20
            details.append("公司虧損 (負PE)")
        
        # PB 股價淨值比
        pb = financial_data.get('pb_ratio', 0)
        if 0 < pb < 1:
            score += 15
            details.append(f"股價淨值比低於1 ({pb})")
        elif 1 <= pb < 1.5:
            score += 10
            details.append(f"股價淨值比合理 ({pb})")
        elif 1.5 <= pb < 3:
            score += 0
        elif pb >= 3:
            score -= 5
            details.append(f"股價淨值比偏高 ({pb})")
        
        # 殖利率
        dividend_yield = financial_data.get('dividend_yield', 0)
        if dividend_yield > 5:
            score += 15
            details.append(f"殖利率優異 ({dividend_yield}%)")
        elif dividend_yield > 3:
            score += 10
            details.append(f"殖利率良好 ({dividend_yield}%)")
        elif dividend_yield > 0:
            score += 5
        
        return min(max(score, 0), 100), details
    
    def _calculate_financial_quality_score(self, financial_data: Dict) -> Tuple[float, List[str]]:
        """計算財務品質評分"""
        score = 50
        details = []
        
        # ROE
        roe = financial_data.get('roe', 0)
        if roe > 20:
            score += 25
            details.append(f"ROE 優異 ({roe}%)")
        elif roe > 10:
            score += 15
            details.append(f"ROE 良好 ({roe}%)")
        elif roe > 0:
            score += 5
            details.append(f"ROE 普通 ({roe}%)")
        else:
            score -= 15
            details.append(f"ROE 偏低 ({roe}%)")
        
        # 負債比
        debt_ratio = financial_data.get('debt_ratio', 0)
        if debt_ratio < 30:
            score += 15
            details.append(f"負債比低 ({debt_ratio}%)")
        elif debt_ratio < 50:
            score += 5
            details.append(f"負債比適中 ({debt_ratio}%)")
        elif debt_ratio > 70:
            score -= 15
            details.append(f"負債比過高 ({debt_ratio}%)")
        
        # 流動比率
        current_ratio = financial_data.get('current_ratio', 0)
        if current_ratio > 2:
            score += 10
            details.append(f"流動比率優 ({current_ratio})")
        elif current_ratio > 1:
            score += 5
        elif current_ratio > 0:
            score -= 10
            details.append(f"流動比率低於標準 ({current_ratio})")
        
        return min(max(score, 0), 100), details
    
    def _calculate_technical_score(self, price_data: Dict, institutional_data: Dict) -> Tuple[float, List[str]]:
        """計算技術面評分"""
        score = 50
        details = []
        
        # 趨勢
        trend = price_data.get('trend', '盤整')
        if trend == "多頭":
            score += 15
            details.append("技術面多頭排列，趨勢向上")
        elif trend == "空頭":
            score -= 15
            details.append("技術面空頭排列，趨勢向下")
        else:
            details.append("技術面盤整格局")
        
        # MACD
        macd = price_data.get('macd', 0)
        macd_signal = price_data.get('macd_signal', '')
        if macd > 0:
            score += 10
            if "多頭強勢" in macd_signal:
                score += 5
                details.append("MACD 黃金交叉且在零軸之上，多頭動能強")
        else:
            score -= 5
        
        # RSI
        rsi = price_data.get('rsi_14', 50)
        if rsi > 70:
            score -= 10
            details.append(f"RSI 過熱 ({rsi})，短期可能回調")
        elif rsi < 30:
            score += 10
            details.append(f"RSI 超賣 ({rsi})，可能反彈")
        
        # 法人籌碼
        total_net = institutional_data.get('total_net', 0)
        if total_net > 0:
            score += 10
            details.append(f"法人近期買超 {total_net} 張")
        elif total_net < 0:
            score -= 5
            details.append(f"法人近期賣超 {abs(total_net)} 張")
        
        # 成交量
        volume_ratio = price_data.get('volume_ratio', 1)
        if volume_ratio > 2:
            score += 5
            details.append(f"成交量放大 ({volume_ratio}倍)")
        
        return min(max(score, 0), 100), details
    
    def _calculate_overall_score(self, dimension_scores: List[DimensionScore]) -> float:
        """計算加權綜合評分"""
        total_weight = sum(d.weight for d in dimension_scores)
        weighted_score = sum(d.score * d.weight for d in dimension_scores)
        return round(weighted_score / total_weight if total_weight else 50, 1)

    # ==================== 訊號分析方法 ====================
    
    def _analyze_buy_signals(
        self, 
        price_data: Dict, 
        financial_data: Dict, 
        institutional_data: Dict
    ) -> List[Signal]:
        """分析買入訊號"""
        signals = []
        
        # 技術面買入訊號
        if price_data.get('trend') == "多頭":
            signals.append(Signal(
                type=SignalType.BUY,
                name="多頭排列",
                description="技術面多頭排列，趨勢向上",
                confidence=75,
                source="技術分析"
            ))
        
        macd = price_data.get('macd', 0)
        macd_histogram = price_data.get('macd_histogram', 0)
        if macd > 0 and macd_histogram > 0:
            signals.append(Signal(
                type=SignalType.BUY,
                name="MACD 黃金交叉",
                description="MACD 黃金交叉且在零軸之上，多頭動能強",
                confidence=80,
                source="技術分析"
            ))
        
        rsi = price_data.get('rsi_14', 50)
        if rsi < 30:
            signals.append(Signal(
                type=SignalType.BUY,
                name="RSI 超賣",
                description=f"RSI ({rsi}) 進入超賣區，可能反彈",
                confidence=65,
                source="技術分析"
            ))
        
        kd_k = price_data.get('kd_k', 50)
        kd_d = price_data.get('kd_d', 50)
        if kd_k > kd_d and kd_k < 30:
            signals.append(Signal(
                type=SignalType.BUY,
                name="KD 低檔黃金交叉",
                description="KD 在低檔區黃金交叉",
                confidence=70,
                source="技術分析"
            ))
        
        # 籌碼面買入訊號
        total_net = institutional_data.get('total_net', 0)
        consecutive = institutional_data.get('consecutive_days', 0)
        if total_net > 1000 and consecutive >= 3:
            signals.append(Signal(
                type=SignalType.BUY,
                name="法人連續買超",
                description=f"法人連續 {consecutive} 天買超，籌碼集中",
                confidence=75,
                source="籌碼分析"
            ))
        
        # 估值面買入訊號
        pe = financial_data.get('pe_ratio', 0)
        if 0 < pe < 12:
            signals.append(Signal(
                type=SignalType.BUY,
                name="本益比低估",
                description=f"本益比 ({pe}) 低於市場平均，可能被低估",
                confidence=60,
                source="估值分析"
            ))
        
        dividend_yield = financial_data.get('dividend_yield', 0)
        if dividend_yield > 5:
            signals.append(Signal(
                type=SignalType.BUY,
                name="高殖利率",
                description=f"殖利率 ({dividend_yield}%) 具吸引力",
                confidence=65,
                source="股利分析"
            ))
        
        # ========== 量價分析買入訊號 ==========
        vp_data = price_data.get('volume_price_analysis', {})
        
        if vp_data:
            # 價漲量增 - 量價確認
            if vp_data.get('confirmation_signal') == 'bullish_confirmation':
                signals.append(Signal(
                    type=SignalType.BUY,
                    name="量價確認 (價漲量增)",
                    description=f"{vp_data.get('volume_price_confirmation', '價漲量增')}，量價配合良好",
                    confidence=80,
                    source="量價分析"
                ))
            
            # 看漲背離
            if vp_data.get('divergence_type') == 'bullish_divergence':
                signals.append(Signal(
                    type=SignalType.BUY,
                    name="量價看漲背離",
                    description=vp_data.get('divergence_description', '價格創新低但成交量能未跟破，可能反轉上漲'),
                    confidence=75,
                    source="量價分析"
                ))
            
            # OBV 確認多頭
            if vp_data.get('obv_trend') == 'bullish' and price_data.get('trend') == '多頭':
                signals.append(Signal(
                    type=SignalType.BUY,
                    name="OBV 確認多頭",
                    description="能量潮 OBV 趨勢向上，資金持續流入",
                    confidence=70,
                    source="量價分析"
                ))
            
            # 放量突破
            volume_ratio = vp_data.get('volume_ratio', 1)
            change_pct = price_data.get('change_pct', 0)
            if volume_ratio > 1.5 and change_pct > 2:
                signals.append(Signal(
                    type=SignalType.BUY,
                    name="放量突破",
                    description=f"成交量放大至 {volume_ratio:.1f} 倍，價格上漲 {change_pct:.1f}%",
                    confidence=80,
                    source="量價分析"
                ))
            
            # 趨勢預測看漲
            if vp_data.get('predicted_direction') == 'up' and vp_data.get('trend_confidence', 0) > 60:
                prob = vp_data.get('prediction_probability', {})
                signals.append(Signal(
                    type=SignalType.BUY,
                    name="量價趨勢看漲",
                    description=f"量價分析預測上漲，機率 {prob.get('up', 0)*100:.0f}%",
                    confidence=int(vp_data.get('trend_confidence', 50)),
                    source="量價分析"
                ))
        
        return signals
    
    def _analyze_sell_signals(
        self, 
        price_data: Dict, 
        financial_data: Dict, 
        institutional_data: Dict
    ) -> List[Signal]:
        """分析賣出訊號"""
        signals = []
        
        # 技術面賣出訊號
        if price_data.get('trend') == "空頭":
            signals.append(Signal(
                type=SignalType.SELL,
                name="空頭排列",
                description="技術面空頭排列，趨勢向下",
                confidence=75,
                source="技術分析"
            ))
        
        macd = price_data.get('macd', 0)
        macd_histogram = price_data.get('macd_histogram', 0)
        if macd < 0 and macd_histogram < 0:
            signals.append(Signal(
                type=SignalType.SELL,
                name="MACD 死亡交叉",
                description="MACD 死亡交叉且在零軸之下，空頭動能強",
                confidence=80,
                source="技術分析"
            ))
        
        rsi = price_data.get('rsi_14', 50)
        if rsi > 80:
            signals.append(Signal(
                type=SignalType.SELL,
                name="RSI 極度超買",
                description=f"RSI ({rsi}) 極度超買，建議減碼",
                confidence=70,
                source="技術分析"
            ))
        
        kd_k = price_data.get('kd_k', 50)
        kd_d = price_data.get('kd_d', 50)
        if kd_k < kd_d and kd_k > 80:
            signals.append(Signal(
                type=SignalType.SELL,
                name="KD 高檔死亡交叉",
                description="KD 在高檔區死亡交叉",
                confidence=70,
                source="技術分析"
            ))
        
        # 乖離率過高
        deviation_20d = price_data.get('deviation_20d', 0)
        if deviation_20d > 15:
            signals.append(Signal(
                type=SignalType.SELL,
                name="乖離率過高",
                description=f"20日乖離率 ({deviation_20d}%) 過高，注意回調風險",
                confidence=65,
                source="技術分析"
            ))
        
        # 籌碼面賣出訊號
        total_net = institutional_data.get('total_net', 0)
        consecutive = institutional_data.get('consecutive_days', 0)
        if total_net < -1000 and consecutive >= 3:
            signals.append(Signal(
                type=SignalType.SELL,
                name="法人連續賣超",
                description=f"法人連續 {consecutive} 天賣超，籌碼鬆動",
                confidence=75,
                source="籌碼分析"
            ))
        
        # 估值面賣出訊號
        pe = financial_data.get('pe_ratio', 0)
        if pe > 50:
            signals.append(Signal(
                type=SignalType.SELL,
                name="本益比過高",
                description=f"本益比 ({pe}) 過高，估值風險大",
                confidence=65,
                source="估值分析"
            ))
        
        # ========== 量價分析賣出訊號 ==========
        vp_data = price_data.get('volume_price_analysis', {})
        
        if vp_data:
            # 價跌量增 - 空頭確認
            if vp_data.get('confirmation_signal') == 'bearish_confirmation':
                signals.append(Signal(
                    type=SignalType.SELL,
                    name="量價確認 (價跌量增)",
                    description=f"{vp_data.get('volume_price_confirmation', '價跌量增')}，賣壓沉重",
                    confidence=80,
                    source="量價分析"
                ))
            
            # 看跌背離
            if vp_data.get('divergence_type') == 'bearish_divergence':
                signals.append(Signal(
                    type=SignalType.SELL,
                    name="量價看跌背離",
                    description=vp_data.get('divergence_description', '價格創新高但成交量能未跟上，可能反轉下跌'),
                    confidence=75,
                    source="量價分析"
                ))
            
            # OBV 確認空頭
            if vp_data.get('obv_trend') == 'bearish' and price_data.get('trend') == '空頭':
                signals.append(Signal(
                    type=SignalType.SELL,
                    name="OBV 確認空頭",
                    description="能量潮 OBV 趨勢向下，資金持續流出",
                    confidence=70,
                    source="量價分析"
                ))
            
            # 價漲量縮 - 量能不足警示
            if vp_data.get('confirmation_signal') == 'caution':
                signals.append(Signal(
                    type=SignalType.SELL,
                    name="量能不足警示",
                    description=f"{vp_data.get('volume_price_confirmation', '價漲量縮')}，上漲動能不足",
                    confidence=60,
                    source="量價分析"
                ))
            
            # 趨勢預測看跌
            if vp_data.get('predicted_direction') == 'down' and vp_data.get('trend_confidence', 0) > 60:
                prob = vp_data.get('prediction_probability', {})
                signals.append(Signal(
                    type=SignalType.SELL,
                    name="量價趨勢看跌",
                    description=f"量價分析預測下跌，機率 {prob.get('down', 0)*100:.0f}%",
                    confidence=int(vp_data.get('trend_confidence', 50)),
                    source="量價分析"
                ))
            
            # 放量下跌
            volume_ratio = vp_data.get('volume_ratio', 1)
            change_pct = price_data.get('change_pct', 0)
            if volume_ratio > 1.5 and change_pct < -2:
                signals.append(Signal(
                    type=SignalType.SELL,
                    name="放量下跌",
                    description=f"成交量放大至 {volume_ratio:.1f} 倍，價格下跌 {abs(change_pct):.1f}%",
                    confidence=80,
                    source="量價分析"
                ))
        
        return signals
    
    def _analyze_risks(
        self, 
        price_data: Dict, 
        financial_data: Dict, 
        institutional_data: Dict
    ) -> List[RiskAlert]:
        """分析風險警示"""
        alerts = []
        
        # ROE 風險
        roe = financial_data.get('roe', 0)
        if roe < 0:
            alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                title="ROE 偏低",
                description=f"ROE ({roe}%)，獲利能力待改善",
                metric="ROE",
                value=roe
            ))
        elif roe < 5:
            alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                title="ROE 普通",
                description=f"ROE ({roe}%)，獲利能力一般",
                metric="ROE",
                value=roe
            ))
        
        # 營收衰退風險
        revenue_growth = financial_data.get('revenue_growth_3y', 0)
        if revenue_growth < -10:
            alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                title="營收衰退",
                description=f"營收成長率 ({revenue_growth}%)，需關注營運狀況",
                metric="營收成長",
                value=revenue_growth
            ))
        elif revenue_growth < 0:
            alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                title="營收微幅衰退",
                description=f"營收成長率 ({revenue_growth}%)，需持續觀察",
                metric="營收成長",
                value=revenue_growth
            ))
        
        # RSI 風險
        rsi = price_data.get('rsi_14', 50)
        if rsi > 70:
            alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                title="RSI 過熱",
                description=f"RSI ({rsi})，短期可能回調",
                metric="RSI",
                value=rsi
            ))
        
        # 負債比風險
        debt_ratio = financial_data.get('debt_ratio', 0)
        if debt_ratio > 70:
            alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                title="負債比過高",
                description=f"負債比 ({debt_ratio}%)，財務槓桿風險高",
                metric="負債比",
                value=debt_ratio
            ))
        elif debt_ratio > 50:
            alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                title="負債比偏高",
                description=f"負債比 ({debt_ratio}%)，需注意財務風險",
                metric="負債比",
                value=debt_ratio
            ))
        
        # 流動比率風險
        current_ratio = financial_data.get('current_ratio', 0)
        if current_ratio > 0 and current_ratio < 1:
            alerts.append(RiskAlert(
                level=RiskLevel.HIGH,
                title="流動比率過低",
                description=f"流動比率 ({current_ratio})，短期償債能力弱",
                metric="流動比率",
                value=current_ratio
            ))
        
        # 乖離率風險
        deviation_60d = price_data.get('deviation_60d', 0)
        if deviation_60d > 30:
            alerts.append(RiskAlert(
                level=RiskLevel.MEDIUM,
                title="短期漲幅過大",
                description=f"60日乖離率 ({deviation_60d}%)，注意回調風險",
                metric="乖離率",
                value=deviation_60d
            ))
        
        return alerts

    # ==================== 建構資料模型方法 ====================
    
    def _build_financial_health(self, financial_data: Dict) -> Optional[FinancialHealth]:
        """建構財務健康指標"""
        if not financial_data:
            return None
        
        return FinancialHealth(
            roe=financial_data.get('roe', 0),
            eps=financial_data.get('eps', 0),
            quarterly_eps=financial_data.get('quarterly_eps', []),
            revenue_growth_3y=financial_data.get('revenue_growth_3y', 0),
            gross_margin=financial_data.get('gross_margin', 0),
            debt_ratio=financial_data.get('debt_ratio', 0),
            current_ratio=financial_data.get('current_ratio', 0),
            quick_ratio=financial_data.get('quick_ratio', 0),
            interest_coverage=financial_data.get('interest_coverage', 0),
            free_cash_flow=financial_data.get('free_cash_flow', 0)
        )
    
    def _build_valuation(self, financial_data: Dict) -> Optional[Valuation]:
        """建構估值分析"""
        if not financial_data:
            return None
        
        return Valuation(
            pe_ratio=financial_data.get('pe_ratio', 0),
            pb_ratio=financial_data.get('pb_ratio', 0),
            dividend_yield=financial_data.get('dividend_yield', 0),
            peg_ratio=financial_data.get('peg_ratio', 0),
            ev_ebitda=financial_data.get('ev_ebitda', 0)
        )
    
    def _build_technical_indicators(self, price_data: Dict) -> Optional[TechnicalIndicators]:
        """建構技術指標"""
        if not price_data:
            return None
        
        return TechnicalIndicators(
            current_price=price_data.get('current_price', 0),
            change_pct=price_data.get('change_pct', 0),
            # MA 均線
            ma5=price_data.get('ma5', 0),
            ma10=price_data.get('ma10', 0),
            ma20=price_data.get('ma20', 0),
            ma60=price_data.get('ma60', 0),
            # MA 分析
            ma_arrangement=price_data.get('ma_arrangement', ''),
            ma_signal=price_data.get('ma_signal', ''),
            ma_trend=price_data.get('ma_trend', ''),
            # 壓力支撐
            resistance_1=price_data.get('resistance_1', 0),
            resistance_2=price_data.get('resistance_2', 0),
            support_1=price_data.get('support_1', 0),
            support_2=price_data.get('support_2', 0),
            # 其他技術指標
            rsi_14=price_data.get('rsi_14', 50),
            macd=price_data.get('macd', 0),
            macd_signal=price_data.get('macd_signal', ''),
            kd_k=price_data.get('kd_k', 50),
            kd_d=price_data.get('kd_d', 50),
            bollinger_width=price_data.get('bb_width', 0),
            deviation_20d=price_data.get('deviation_20d', 0),
            deviation_60d=price_data.get('deviation_60d', 0),
            trend=price_data.get('trend', '盤整')
        )
    
    def _build_institutional_trading(self, institutional_data: Dict, price_data: Dict) -> Optional[InstitutionalTrading]:
        """建構法人籌碼"""
        if not institutional_data:
            return None
        
        # 專家建議：如果沒有真實成本，使用 MA20 作為主力成本參考
        main_force_avg_cost = institutional_data.get('main_force_avg_cost', 0)
        if main_force_avg_cost == 0:
            main_force_avg_cost = price_data.get('ma20', price_data.get('current_price', 0))

        # 🆕 精確計算籌碼集中度 (使用真實成交量)
        # 5日成交量合計 = avg_volume_5 * 5
        # 5日買賣超合計 = institutional_history.total.d5 (這是張)
        # avg_volume_5 是股數，需要轉為張
        chip_concentration = institutional_data.get('chip_concentration', 0)
        try:
            avg_vol_5 = price_data.get('avg_volume_5', 0)
            if avg_vol_5 > 0:
                inst_hist = institutional_data.get('institutional_history', {})
                total_5d_net = abs(inst_hist.get('total', {}).get('d5', 0))
                # 區間總量 (張)
                total_5d_vol = (avg_vol_5 / 1000) * 5
                if total_5d_vol > 0:
                    chip_concentration = round((total_5d_net / total_5d_vol) * 100, 1)
        except Exception as e:
            logger.warning(f"重新計算集中度失敗: {e}")

        # 強制上限 100.0
        chip_concentration = min(100.0, chip_concentration)

        return InstitutionalTrading(
            foreign_buy=0, foreign_sell=0,
            foreign_net=institutional_data.get('foreign_net', 0),
            trust_buy=0, trust_sell=0,
            trust_net=institutional_data.get('trust_net', 0),
            dealer_buy=0, dealer_sell=0,
            dealer_net=institutional_data.get('dealer_net', 0),
            total_net=institutional_data.get('total_net', 0),
            consecutive_days=institutional_data.get('consecutive_days', 0),
            chip_concentration=chip_concentration,
            main_force_avg_cost=main_force_avg_cost,
            institutional_history=institutional_data.get('institutional_history')
        )

    def _build_volume_price_analysis(self, price_data: Dict) -> Optional[VolumePriceAnalysis]:
        """建構量價關係分析"""
        if not price_data:
            return None
        
        vp_data = price_data.get('volume_price_analysis', {})
        
        if not vp_data:
            # 返回預設值
            return VolumePriceAnalysis(
                trend_direction="sideways",
                trend_confidence=50.0,
                volume_price_confirmation="中性",
                confirmation_signal="neutral",
                confirmation_strength=0.0,
                divergence_detected=False,
                divergence_type="none",
                divergence_description="",
                volume_ratio=1.0,
                volume_trend="stable",
                volume_sma5=0,
                volume_sma20=0,
                obv=0,
                obv_trend="neutral",
                vwap=0,
                vwap_deviation=0,
                key_signals=[],
                buy_pressure_percent=50.0,
                sell_pressure_percent=50.0,
                predicted_direction="sideways",
                prediction_probability={"up": 0.33, "down": 0.33, "sideways": 0.34}
            )
        
        return VolumePriceAnalysis(
            trend_direction=vp_data.get('trend_direction', 'sideways'),
            trend_confidence=vp_data.get('trend_confidence', 50.0),
            volume_price_confirmation=vp_data.get('volume_price_confirmation', '中性'),
            confirmation_signal=vp_data.get('confirmation_signal', 'neutral'),
            confirmation_strength=vp_data.get('confirmation_strength', 0.0),
            divergence_detected=vp_data.get('divergence_detected', False),
            divergence_type=vp_data.get('divergence_type', 'none'),
            divergence_description=vp_data.get('divergence_description', ''),
            volume_ratio=vp_data.get('volume_ratio', 1.0),
            volume_trend=vp_data.get('volume_trend', 'stable'),
            volume_sma5=vp_data.get('volume_sma5', 0),
            volume_sma20=vp_data.get('volume_sma20', 0),
            obv=vp_data.get('obv', 0),
            obv_trend=vp_data.get('obv_trend', 'neutral'),
            vwap=vp_data.get('vwap', 0),
            vwap_deviation=vp_data.get('vwap_deviation', 0),
            key_signals=vp_data.get('key_signals', []),
            buy_pressure_percent=vp_data.get('buy_pressure_percent', 50.0),
            sell_pressure_percent=vp_data.get('sell_pressure_percent', 50.0),
            predicted_direction=vp_data.get('predicted_direction', 'sideways'),
            prediction_probability=vp_data.get('prediction_probability', {"up": 0.33, "down": 0.33, "sideways": 0.34})
        )
    
    def _build_risk_metrics(
        self, price_data: Dict, institutional_data: Dict
    ) -> Optional[RiskMetrics]:
        """
        建構風險指標 (專家建議新增)
        包含：Beta、波動率、融資使用率、散戶持股比例、借券餘額
        """
        if not price_data:
            return None
        
        # 計算 Beta (相對大盤波動)
        beta = price_data.get('beta', 1.0)
        
        # 計算波動率 (年化)
        volatility = price_data.get('volatility', 25.0)
        
        # 融資使用率
        margin_usage = institutional_data.get('margin_usage', 0)
        
        # 散戶持股比例
        retail_concentration = institutional_data.get('retail_concentration', 50)
        
        # 借券賣出餘額
        short_selling_balance = institutional_data.get('foreign_short_balance', 0)
        
        # 融資增減比例
        margin_increase_ratio = institutional_data.get('margin_increase_ratio', 0)
        
        return RiskMetrics(
            beta=beta,
            volatility=volatility,
            margin_usage=margin_usage,
            retail_concentration=retail_concentration,
            short_selling_balance=short_selling_balance,
            margin_increase_ratio=margin_increase_ratio
        )
    
    def _build_sector_analysis(
        self, stock_code: str, financial_data: Dict, price_data: Dict
    ) -> Optional[SectorAnalysis]:
        """
        建構產業分析 (專家建議新增)
        包含：產業趨勢、相對強度、同產業估值排名
        """
        # 產業對照表 (簡化版)
        SECTOR_MAP = {
            # 半導體
            '2330': '半導體', '2454': '半導體', '2303': '半導體', '3711': '半導體',
            '2379': 'IC設計', '3034': 'IC設計', '6533': 'IC設計',
            # 電子代工
            '2317': '電子代工', '2382': '電子代工', '3231': '電子代工',
            # 金融
            '2881': '金融', '2882': '金融', '2891': '金融', '2886': '金融',
            # 傳產
            '2002': '鋼鐵', '2603': '航運', '2609': '航運',
            '3481': '面板', '2409': '面板',
        }
        
        sector_name = SECTOR_MAP.get(stock_code, '其他')
        
        # 產業平均 PE (簡化估計值)
        SECTOR_AVG_PE = {
            '半導體': 20, 'IC設計': 25, '電子代工': 12,
            '金融': 10, '鋼鐵': 8, '航運': 6, '面板': 8,
            '其他': 15
        }
        sector_avg_pe = SECTOR_AVG_PE.get(sector_name, 15)
        
        # 計算相對強度 RS (個股vs大盤)
        # 這裡使用簡化計算，實際應比較漲幅
        current_price = price_data.get('current_price', 0)
        ma20 = price_data.get('ma20', current_price)
        ma60 = price_data.get('ma60', current_price)
        
        # RS = 個股強度 / 大盤強度，這裡使用個股自身動能估算
        if ma60 > 0:
            momentum = (current_price / ma60 - 1) * 100
            relative_strength = 1.0 + momentum / 100  # 簡化計算
        else:
            relative_strength = 1.0
        
        # PE 在產業中的排名位置 (0-100，越低越便宜)
        pe = financial_data.get('pe_ratio', 15)
        if sector_avg_pe > 0 and pe > 0:
            pe_rank_in_sector = min(100, max(0, (pe / sector_avg_pe) * 50))
        else:
            pe_rank_in_sector = 50
        
        # PE Band 位置估算
        pe_band_position = financial_data.get('pe_band_position', 50)
        
        # 產業趨勢判斷 (簡化)
        if sector_name in ['半導體', 'IC設計']:
            sector_trend = 'bullish'
        elif sector_name in ['航運', '面板', '鋼鐵']:
            sector_trend = 'neutral'  # 循環型產業
        else:
            sector_trend = 'neutral'
        
        return SectorAnalysis(
            sector_name=sector_name,
            sector_trend=sector_trend,
            relative_strength=round(relative_strength, 2),
            pe_rank_in_sector=round(pe_rank_in_sector, 1),
            sector_avg_pe=sector_avg_pe,
            pe_band_position=pe_band_position
        )
    
    def _generate_investment_thesis(
        self, 
        overall_score: float, 
        dimension_scores: List[DimensionScore],
        buy_signals: List[Signal],
        financial_data: Dict
    ) -> str:
        """
        生成 AI 投資邏輯 (專家建議新增)
        """
        thesis_parts = []
        
        # 依評分給出核心論點
        if overall_score >= 70:
            thesis_parts.append("【核心論點】綜合評分優異，具備投資價值")
        elif overall_score >= 55:
            thesis_parts.append("【核心論點】評分中性偏多，可選擇性布局")
        else:
            thesis_parts.append("【核心論點】評分偏低，建議觀望或避開")
        
        # 找出最強維度
        if dimension_scores:
            best_dim = max(dimension_scores, key=lambda d: d.score)
            thesis_parts.append(f"【最強面向】{best_dim.name}表現突出({best_dim.score:.0f}分)")
            if best_dim.details:
                thesis_parts.append(f"  - {best_dim.details[0]}")
        
        # 估值論點
        pe = financial_data.get('pe_ratio', 0)
        peg = financial_data.get('peg_ratio', 0)
        if peg > 0 and peg < 1:
            thesis_parts.append(f"【估值優勢】PEG {peg:.2f} 低於1，成長價值兼具")
        elif 0 < pe < 12:
            thesis_parts.append(f"【估值優勢】本益比 {pe:.1f} 偏低，可能被低估")
        
        # 買入訊號
        if len(buy_signals) >= 3:
            thesis_parts.append(f"【技術訊號】出現 {len(buy_signals)} 個買入訊號，動能強勁")
        
        return "\n".join(thesis_parts) if thesis_parts else "投資分析進行中..."
    
    def _generate_risk_warning(
        self, 
        risk_alerts: List[RiskAlert], 
        risk_metrics: Optional[RiskMetrics],
        price_data: Dict
    ) -> str:
        """
        生成 AI 風險預警 (專家建議新增)
        """
        warnings = []
        
        # 高風險警示
        high_risks = [r for r in risk_alerts if r.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]
        if high_risks:
            warnings.append(f"⚠️ 高風險警示 ({len(high_risks)}項)：")
            for risk in high_risks[:3]:
                warnings.append(f"  - {risk.title}")
        
        # Beta 風險
        if risk_metrics and risk_metrics.beta > 1.5:
            warnings.append(f"⚠️ 高 Beta ({risk_metrics.beta:.2f})：盤勢轉弱時跌幅可能放大")
        
        # 波動率風險
        if risk_metrics and risk_metrics.volatility > 40:
            warnings.append(f"⚠️ 高波動率 ({risk_metrics.volatility:.1f}%)：價格劇烈波動風險")
        
        # 融資使用率風險
        if risk_metrics and risk_metrics.margin_usage > 40:
            warnings.append(f"⚠️ 融資使用率高 ({risk_metrics.margin_usage:.1f}%)：籌碼面不穩定")
        
        # 乖離率風險
        deviation = price_data.get('deviation_20d', 0)
        if deviation > 15:
            warnings.append(f"⚠️ 乖離率過高 ({deviation:.1f}%)：短期回調風險")
        
        # 量價異常
        volume_ratio = price_data.get('volume_ratio', 1)
        change_pct = price_data.get('change_pct', 0)
        if volume_ratio > 2 and change_pct < 0:
            warnings.append("⚠️ 爆量下跌：可能出現主力出貨")
        
        if not warnings:
            return "目前無重大風險警示"
        
        return "\n".join(warnings)

    # ==================== 輔助方法 ====================
    
    async def _generate_ai_summary(
        self,
        stock_code: str,
        overall_score: float,
        buy_signals: List[Signal],
        sell_signals: List[Signal],
        risk_alerts: List[RiskAlert]
    ) -> str:
        """生成 AI 摘要 (僅限個股分析，不包含國際政經)"""
        stock_name = await get_stock_name(stock_code)
        
        # 移除原本在摘要開頭的國際政經風向，讓專注於個股結論 (避免混淆 EPS 評分與宏觀局勢)
        base = f"🎯【個股結論 - {stock_name}】\n"
        
        # 基本摘要
        if overall_score >= 70:
            base += f"目前技術與籌碼綜合評分優異 ({overall_score}分)，"
        elif overall_score >= 50:
            base += f"整體表現中性偏安穩 ({overall_score}分)，"
        else:
            base += f"綜合評分偏弱 ({overall_score}分)，"
        
        # 訊號摘要
        if len(buy_signals) > len(sell_signals):
            base += f"盤面出現 {len(buy_signals)} 個買入訊號，技術面偏多。\n"
        elif len(sell_signals) > len(buy_signals):
            base += f"盤面出現 {len(sell_signals)} 個賣出訊號，上檔反壓大，需謹慎操作。\n"
        else:
            base += f"買賣訊號均衡，方向尚不明確，建議觀望。\n"
        
        # 風險提示
        high_risks = [r for r in risk_alerts if r.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]
        if high_risks:
            base += f"⚠️ 注意：系統偵測到 {len(high_risks)} 項高風險警示，請嚴設停損。"
        
        return base
    
    def _generate_recommendation(
        self,
        overall_score: float,
        buy_count: int,
        sell_count: int,
        risk_count: int
    ) -> str:
        """生成推薦等級"""
        if overall_score >= 80 and buy_count >= 3 and sell_count == 0:
            return "強力買進"
        elif overall_score >= 70 and buy_count > sell_count:
            return "買進"
        elif overall_score >= 50 or buy_count == sell_count:
            return "觀望"
        elif overall_score >= 40 and sell_count > buy_count:
            return "減碼"
        else:
            return "賣出"
    
    def _calculate_price_targets(
        self,
        price_data: Dict,
        overall_score: float
    ) -> Tuple[Optional[float], Optional[float]]:
        """計算目標價和止損價"""
        current_price = price_data.get('current_price', 0)
        
        if not current_price:
            return None, None
        
        # 根據評分調整目標幅度
        if overall_score >= 70:
            target_pct = 0.15  # 15% 上漲空間
            stop_pct = 0.05   # 5% 止損
        elif overall_score >= 50:
            target_pct = 0.10
            stop_pct = 0.07
        else:
            target_pct = 0.05
            stop_pct = 0.10
        
        target_price = round(current_price * (1 + target_pct), 2)
        stop_loss = round(current_price * (1 - stop_pct), 2)
        
        return target_price, stop_loss


# ==================== 全域實例 ====================

stock_analyzer = StockComprehensiveAnalyzer()


# ==================== 便捷函數 ====================

async def analyze_stock_comprehensive(stock_code: str, quick_mode: bool = False) -> Dict:
    """綜合分析單一股票"""
    analysis = await stock_analyzer.analyze(stock_code, quick_mode=quick_mode)
    return _analysis_to_dict(analysis)

def _analysis_to_dict(analysis: ComprehensiveAnalysis) -> Dict:
    """將分析結果轉為字典"""
    return {
        "stock_code": analysis.stock_code,
        "stock_name": analysis.stock_name,
        "last_updated": analysis.last_updated,
        "overall_score": analysis.overall_score,
        "dimension_scores": [asdict(d) for d in analysis.dimension_scores],
        "buy_signals": [asdict(s) for s in analysis.buy_signals],
        "sell_signals": [asdict(s) for s in analysis.sell_signals],
        "risk_alerts": [asdict(r) for r in analysis.risk_alerts],
        "financial_health": asdict(analysis.financial_health) if analysis.financial_health else None,
        "valuation": asdict(analysis.valuation) if analysis.valuation else None,
        "technical_indicators": asdict(analysis.technical_indicators) if analysis.technical_indicators else None,
        "institutional_trading": asdict(analysis.institutional_trading) if analysis.institutional_trading else None,
        "volume_price_analysis": asdict(analysis.volume_price_analysis) if analysis.volume_price_analysis else None,
        "related_news": analysis.related_news,
        "ai_summary": analysis.ai_summary,
        "recommendation": analysis.recommendation,
        "target_price": analysis.target_price,
        "stop_loss": analysis.stop_loss,
        "macro_summary": analysis.macro_summary
    }


# ==================== 測試 ====================

if __name__ == "__main__":
    async def test():
        print("=" * 60)
        print("股票綜合分析測試")
        print("=" * 60)
        
        result = await analyze_stock_comprehensive("2330")
        
        print(f"\n📊 {result['stock_name']} ({result['stock_code']})")
        print(f"綜合評分: {result['overall_score']}/100")
        print(f"推薦: {result['recommendation']}")
        
        print("\n📈 維度評分:")
        for d in result['dimension_scores']:
            print(f"  - {d['name']}: {d['score']}分 (權重: {d['weight']*100}%)")
        
        print("\n✅ 買入訊號:")
        for s in result['buy_signals']:
            print(f"  - {s['name']}: {s['description']} (信心度: {s['confidence']}%)")
        
        print("\n⚠️ 賣出訊號:")
        for s in result['sell_signals']:
            print(f"  - {s['name']}: {s['description']} (信心度: {s['confidence']}%)")
        
        print("\n🚨 風險警示:")
        for r in result['risk_alerts']:
            print(f"  - [{r['level']}] {r['title']}: {r['description']}")
        
        # 量價分析
        vp = result.get('volume_price_analysis')
        if vp:
            print("\n📊 量價分析:")
            print(f"  趨勢方向: {vp['trend_direction']} (置信度: {vp['trend_confidence']}%)")
            print(f"  量價確認: {vp['volume_price_confirmation']} ({vp['confirmation_signal']})")
            print(f"  預測方向: {vp['predicted_direction']}")
            print(f"  預測機率: 上漲 {vp['prediction_probability']['up']*100:.0f}% / 下跌 {vp['prediction_probability']['down']*100:.0f}% / 盤整 {vp['prediction_probability']['sideways']*100:.0f}%")
            if vp['divergence_detected']:
                print(f"  ⚠️ 背離訊號: {vp['divergence_type']} - {vp['divergence_description']}")
            print(f"  OBV 趨勢: {vp['obv_trend']}")
            print(f"  VWAP 偏離: {vp['vwap_deviation']:.2f}%")
            if vp['key_signals']:
                print(f"  關鍵訊號: {', '.join(vp['key_signals'])}")
        
        print("\n📝 AI 摘要:")
        print(f"  {result['ai_summary']}")
        
        await stock_analyzer.close()
        print("\n✅ 測試完成!")
    
    asyncio.run(test())

