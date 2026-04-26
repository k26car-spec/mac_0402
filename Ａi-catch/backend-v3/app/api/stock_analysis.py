"""
股票綜合分析 API
提供完整的股票分析端點

功能:
1. 綜合分析 API
2. 買入/賣出訊號
3. 風險警示
4. 三大法人籌碼
5. 財務健康指標
6. 股票相關新聞
"""

from fastapi import APIRouter, Query, HTTPException, Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

# ========== API 層快取（避免每次都也完整分析）==========
_ANALYSIS_CACHE: Dict[str, tuple] = {}  # {code: (timestamp, result)}
_ANALYSIS_CACHE_TTL = 300  # 5 分鐘

async def _get_cached_analysis(stock_code: str, force: bool = False) -> Dict:
    """帶快取的綜合分析，超時 15 秒就回空結構"""
    now = datetime.now()
    if not force and stock_code in _ANALYSIS_CACHE:
        ts, data = _ANALYSIS_CACHE[stock_code]
        if (now - ts).total_seconds() < _ANALYSIS_CACHE_TTL:
            return data
    try:
        result = await asyncio.wait_for(
            analyze_stock_comprehensive(stock_code),
            timeout=35.0  # 硬上限 35 秒（允許第一次完成並存快取）
        )
        _ANALYSIS_CACHE[stock_code] = (now, result)
        return result
    except asyncio.TimeoutError:
        logger.warning(f"綜合分析超時 {stock_code}，回空結構")
        # 回傳快取舊資料（即使過期）
        if stock_code in _ANALYSIS_CACHE:
            return _ANALYSIS_CACHE[stock_code][1]
        return {}
    except Exception as e:
        logger.error(f"綜合分析失敗 {stock_code}: {e}")
        if stock_code in _ANALYSIS_CACHE:
            return _ANALYSIS_CACHE[stock_code][1]
        return {}

# 導入綜合分析服務
try:
    from app.services.stock_comprehensive_analyzer import (
        stock_analyzer,
        analyze_stock_comprehensive,
        SignalType,
        RiskLevel
    )
    ANALYZER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"股票分析服務導入失敗: {e}")
    ANALYZER_AVAILABLE = False

# 導入 TWSE 爬蟲
try:
    from app.services.twse_crawler import twse_crawler
    TWSE_AVAILABLE = True
except ImportError:
    TWSE_AVAILABLE = False

# 導入新聞爬蟲
try:
    from app.services.news_crawler_service import news_crawler
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False

# 導入 Wantgoo 爬蟲
try:
    from app.services.wantgoo_crawler import wantgoo_crawler, get_wantgoo_news
    WANTGOO_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Wantgoo 爬蟲導入失敗: {e}")
    WANTGOO_AVAILABLE = False


# ==================== 資料模型 ====================

class DimensionScoreResponse(BaseModel):
    """維度評分回應"""
    name: str
    score: float
    weight: float
    details: List[str]

class SignalResponse(BaseModel):
    """訊號回應"""
    type: str
    name: str
    description: str
    confidence: float
    source: str

class RiskAlertResponse(BaseModel):
    """風險警示回應"""
    level: str
    title: str
    description: str
    metric: str
    value: Any

class FinancialHealthResponse(BaseModel):
    """財務健康回應"""
    roe: float
    eps: float
    revenue_growth_3y: float
    gross_margin: float
    debt_ratio: float
    current_ratio: float
    quick_ratio: float
    interest_coverage: float
    free_cash_flow: float

class ValuationResponse(BaseModel):
    """估值分析回應"""
    pe_ratio: float
    pb_ratio: float
    dividend_yield: float
    peg_ratio: float
    ev_ebitda: float

class TechnicalIndicatorsResponse(BaseModel):
    """技術指標回應"""
    current_price: float = 0  # 當前價格
    change_pct: float = 0     # 漲跌幅 %
    # MA 均線
    ma5: float = 0
    ma10: float = 0
    ma20: float = 0
    ma60: float = 0
    # MA 均線分析
    ma_arrangement: str = ""    # 均線排列
    ma_signal: str = ""         # 突破/跌破訊號
    ma_trend: str = ""          # 短中長期趨勢
    # 壓力與支撐
    resistance_1: float = 0     # 壓力位1
    resistance_2: float = 0     # 壓力位2
    support_1: float = 0        # 支撐位1
    support_2: float = 0        # 支撐位2
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

class InstitutionalTradingResponse(BaseModel):
    """法人籌碼回應"""
    foreign_net: int
    trust_net: int
    dealer_net: int
    total_net: int
    consecutive_days: int
    chip_concentration: float = 0
    main_force_avg_cost: float = 0
    institutional_history: Optional[Dict[str, Dict[str, int]]] = None

class NewsItemResponse(BaseModel):
    """新聞項目回應"""
    title: str
    summary: Optional[str] = ""
    date: str
    source: str
    sentiment: Optional[str] = "neutral"
    impact: Optional[str] = "medium"

class ComprehensiveAnalysisResponse(BaseModel):
    """綜合分析回應"""
    status: str
    stock_code: str
    stock_name: str
    last_updated: str
    overall_score: float
    dimension_scores: List[DimensionScoreResponse]
    buy_signals: List[SignalResponse]
    sell_signals: List[SignalResponse]
    risk_alerts: List[RiskAlertResponse]
    financial_health: Optional[FinancialHealthResponse]
    valuation: Optional[ValuationResponse]
    technical_indicators: Optional[TechnicalIndicatorsResponse]
    institutional_trading: Optional[InstitutionalTradingResponse]
    related_news: List[Dict]
    ai_summary: str
    recommendation: str
    target_price: Optional[float]
    stop_loss: Optional[float]


# ==================== API 端點 ====================

# ==================== 股票名稱查詢 ====================

@router.get(
    "/stock-name/{stock_code}",
    summary="查詢股票名稱",
    description="根據股票代碼查詢中文名稱"
)
async def get_stock_name_api(stock_code: str):
    """
    查詢股票中文名稱
    """
    try:
        from fubon_client import fubon_client
        name = await fubon_client.get_stock_name(stock_code)
        
        # 如果 Fubon 返回的還是代碼，則嘗試 fallback 到舊有邏輯 (但優先度已降)
        if name == stock_code:
            from app.services.stock_comprehensive_analyzer import get_stock_name
            name = get_stock_name(stock_code)
            
        return {
            "code": stock_code,
            "name": name,
            "success": True
        }
    except Exception as e:
        return {
            "code": stock_code,
            "name": stock_code,
            "success": False,
            "error": str(e)
        }


@router.post(
    "/stock-names",
    summary="批次查詢股票名稱",
    description="批次查詢多個股票代碼的中文名稱"
)
async def get_stock_names_batch(stock_codes: List[str]):
    """
    批次查詢股票中文名稱
    """
    try:
        from app.services.stock_comprehensive_analyzer import get_stock_name
        results = {}
        for code in stock_codes:
            results[code] = get_stock_name(code)
        return {
            "success": True,
            "data": results,
            "count": len(results)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {}
        }

@router.get(
    "/comprehensive/{stock_code}",
    summary="取得股票綜合分析",
    description="""
    取得完整的股票綜合分析報告，包含:
    - 四維度評分 (成長性、估值、財務品質、技術面)
    - 買入訊號分析
    - 賣出訊號分析
    - 風險警示
    - 財務健康指標
    - 技術指標
    - 法人籌碼
    - 相關新聞
    - AI 摘要和推薦
    - 異常股票警示 (處置股/注意股)
    - 重要日期事件
    - 法人動向分析
    """
)
async def get_comprehensive_analysis(stock_code: str, force: bool = Query(default=False, description="是否強制刷新 (忽略快取)")):
    """
    取得股票綜合分析（帶快取，不超過 15 秒）
    """
    if not ANALYZER_AVAILABLE:
        raise HTTPException(status_code=503, detail="分析服務暫時不可用")

    result = await _get_cached_analysis(stock_code, force=force)
    if not result:
        raise HTTPException(status_code=500, detail="分析超時或失敗")

    # 加入異常股票警示
    try:
        from app.services.twse_abnormal_api import check_stock_abnormal
        is_abnormal, reasons = check_stock_abnormal(stock_code)
        result['abnormal_warning'] = {'is_abnormal': is_abnormal, 'reasons': reasons}
    except Exception:
        result['abnormal_warning'] = {'is_abnormal': False, 'reasons': []}

    return {"status": "success", **result}


@router.get(
    "/signals/{stock_code}",
    summary="取得買入/賣出訊號",
    description="取得股票的買入和賣出訊號分析"
)
async def get_trading_signals(
    stock_code: str,
    signal_type: Optional[str] = Query(
        default=None,
        description="訊號類型: buy (買入) / sell (賣出) / 不填=全部"
    )
):
    """
    取得交易訊號
    """
    if not ANALYZER_AVAILABLE:
        raise HTTPException(status_code=503, detail="分析服務暫時不可用")
    
    try:
        result = await analyze_stock_comprehensive(stock_code)
        
        response = {
            "status": "success",
            "stock_code": stock_code,
            "stock_name": result['stock_name'],
            "timestamp": datetime.now().isoformat(),
        }
        
        if signal_type == "buy":
            response["signals"] = result['buy_signals']
            response["signal_type"] = "buy"
            response["count"] = len(result['buy_signals'])
        elif signal_type == "sell":
            response["signals"] = result['sell_signals']
            response["signal_type"] = "sell"
            response["count"] = len(result['sell_signals'])
        else:
            response["buy_signals"] = result['buy_signals']
            response["sell_signals"] = result['sell_signals']
            response["buy_count"] = len(result['buy_signals'])
            response["sell_count"] = len(result['sell_signals'])
        
        return response
        
    except Exception as e:
        logger.error(f"取得訊號失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/risks/{stock_code}",
    summary="取得風險警示",
    description="取得股票的風險警示分析"
)
async def get_risk_alerts(
    stock_code: str,
    min_level: Optional[str] = Query(
        default=None,
        description="最低風險等級: low / medium / high / critical"
    )
):
    """
    取得風險警示
    """
    if not ANALYZER_AVAILABLE:
        raise HTTPException(status_code=503, detail="分析服務暫時不可用")
    
    try:
        result = await analyze_stock_comprehensive(stock_code)
        
        alerts = result['risk_alerts']
        
        # 過濾等級
        if min_level:
            level_order = ["low", "medium", "high", "critical"]
            min_index = level_order.index(min_level) if min_level in level_order else 0
            alerts = [a for a in alerts if level_order.index(a['level']) >= min_index]
        
        return {
            "status": "success",
            "stock_code": stock_code,
            "stock_name": result['stock_name'],
            "timestamp": datetime.now().isoformat(),
            "risk_alerts": alerts,
            "count": len(alerts),
            "high_risk_count": len([a for a in alerts if a['level'] in ['high', 'critical']])
        }
        
    except Exception as e:
        logger.error(f"取得風險警示失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/financial-health/{stock_code}",
    summary="取得財務健康指標",
    description="取得股票的財務健康分析"
)
async def get_financial_health(stock_code: str):
    """
    取得財務健康指標
    """
    if not ANALYZER_AVAILABLE:
        raise HTTPException(status_code=503, detail="分析服務暫時不可用")
    
    try:
        result = await analyze_stock_comprehensive(stock_code)
        
        financial = result['financial_health']
        valuation = result['valuation']
        
        # 計算財務健康評分
        dimension_scores = result['dimension_scores']
        financial_score = next(
            (d['score'] for d in dimension_scores if d['name'] == '財務品質'),
            50
        )
        
        return {
            "status": "success",
            "stock_code": stock_code,
            "stock_name": result['stock_name'],
            "timestamp": datetime.now().isoformat(),
            "financial_health": financial,
            "valuation": valuation,
            "financial_quality_score": financial_score,
            "health_summary": _generate_health_summary(financial, valuation)
        }
        
    except Exception as e:
        logger.error(f"取得財務健康失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/institutional/{stock_code}",
    summary="取得三大法人籌碼",
    description="取得股票的三大法人買賣超資料"
)
async def get_institutional_trading(
    stock_code: str,
    days: int = Query(default=5, description="取幾天資料")
):
    """
    取得三大法人籌碼（自動過濾週末/假日資料）
    """
    if not TWSE_AVAILABLE:
        raise HTTPException(status_code=503, detail="TWSE 服務暫時不可用")

    try:
        from datetime import datetime as _dt

        # 取得歷史資料
        history = await twse_crawler.get_stock_institutional(stock_code, days=days + 4)

        # ── 過濾非交易日（週六=5、週日=6）──
        def is_weekday(date_str: str) -> bool:
            try:
                d = _dt.strptime(str(date_str)[:10], "%Y-%m-%d")
                return d.weekday() < 5  # 0=Mon ~ 4=Fri
            except:
                return True  # 解析失敗就保留

        history = [d for d in history if is_weekday(d.get('date', ''))]

        # 只保留最近 days 筆
        history = history[:days]

        # 計算累計 (使用原始股數 Shares 以避免精度損失)
        foreign_shares = 0
        trust_shares = 0
        dealer_shares = 0

        for day in history:
            try:
                foreign_shares += int(str(day.get('foreign_net', '0')).replace(',', ''))
                trust_shares += int(str(day.get('investment_net', '0')).replace(',', ''))
                dealer_shares += int(str(day.get('dealer_net', '0')).replace(',', ''))
            except:
                continue

        # 轉換為張 (Lots) 供摘要呈現
        foreign_net = int(foreign_shares / 1000)
        trust_net = int(trust_shares / 1000)
        dealer_net = int(dealer_shares / 1000)
        total_net = foreign_net + trust_net + dealer_net

        # 格式化 history
        formatted_history = []
        for day in history:
            formatted_history.append({
                "date": day.get('date'),
                "foreign_net": int(day.get('foreign_net', 0) / 1000),
                "investment_net": int(day.get('investment_net', 0) / 1000),
                "dealer_net": int(day.get('dealer_net', 0) / 1000),
                "total_net": int(day.get('total_net', 0) / 1000),
                "foreign_shares": day.get('foreign_net', 0),
                "investment_shares": day.get('investment_net', 0),
                "dealer_shares": day.get('dealer_net', 0)
            })

        # 判斷籌碼趨勢
        if total_net > 1000:
            trend = "籌碼集中 📈"
        elif total_net < -1000:
            trend = "籌碼分散 📉"
        else:
            trend = "籌碼中性"

        # 最後一個有效交易日
        last_trading_date = formatted_history[0]['date'] if formatted_history else None

        return {
            "status": "success",
            "stock_code": stock_code,
            "timestamp": datetime.now().isoformat(),
            "last_trading_date": last_trading_date,
            "note": "資料已過濾非交易日（週末/假日）",
            "days": len(formatted_history),
            "summary": {
                "foreign_net": foreign_net,
                "trust_net": trust_net,
                "dealer_net": dealer_net,
                "total_net": total_net,
                "trend": trend,
                "shares_summary": {
                    "foreign": foreign_shares,
                    "trust": trust_shares,
                    "dealer": dealer_shares
                }
            },
            "history": formatted_history,
            "analysis": {
                "foreign_trend": "買超" if foreign_net > 0 else "賣超",
                "trust_trend": "買超" if trust_net > 0 else "賣超",
                "dealer_trend": "買超" if dealer_net > 0 else "賣超",
            }
        }

    except Exception as e:
        logger.error(f"取得法人籌碼失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.get(
    "/technical/{stock_code}",
    summary="取得技術指標",
    description="取得股票的技術分析指標"
)
async def get_technical_indicators(stock_code: str):
    """
    取得技術指標
    """
    if not ANALYZER_AVAILABLE:
        raise HTTPException(status_code=503, detail="分析服務暫時不可用")
    
    try:
        result = await analyze_stock_comprehensive(stock_code)
        
        technical = result['technical_indicators']
        
        # 計算技術面評分
        dimension_scores = result['dimension_scores']
        technical_score = next(
            (d['score'] for d in dimension_scores if d['name'] == '技術面'),
            50
        )
        
        return {
            "status": "success",
            "stock_code": stock_code,
            "stock_name": result['stock_name'],
            "timestamp": datetime.now().isoformat(),
            "technical_indicators": technical,
            "technical_score": technical_score,
            "trend": technical['trend'] if technical else '盤整',
            "signals": _generate_technical_signals(technical)
        }
        
    except Exception as e:
        logger.error(f"取得技術指標失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/news/{stock_code}",
    summary="取得股票相關新聞",
    description="取得股票相關的最新新聞和市場分析"
)
async def get_stock_news(
    stock_code: str,
    limit: int = Query(default=5, description="新聞數量上限")
):
    """
    取得股票相關新聞
    """
    if not ANALYZER_AVAILABLE:
        raise HTTPException(status_code=503, detail="分析服務暫時不可用")
    
    try:
        result = await analyze_stock_comprehensive(stock_code)
        
        news = result['related_news'][:limit]
        
        # 分析新聞情緒
        positive = len([n for n in news if n.get('sentiment') == 'positive'])
        negative = len([n for n in news if n.get('sentiment') == 'negative'])
        neutral = len(news) - positive - negative
        
        if positive > negative:
            overall_sentiment = "正面"
        elif negative > positive:
            overall_sentiment = "負面"
        else:
            overall_sentiment = "中性"
        
        return {
            "status": "success",
            "stock_code": stock_code,
            "stock_name": result['stock_name'],
            "timestamp": datetime.now().isoformat(),
            "news": news,
            "count": len(news),
            "sentiment_analysis": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "overall": overall_sentiment
            }
        }
        
    except Exception as e:
        logger.error(f"取得新聞失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/news/wantgoo/{stock_code}",
    summary="取得 Wantgoo 個股新聞",
    description="從 wantgoo.com 取得特定股票的最新消息"
)
async def get_wantgoo_stock_news(
    stock_code: str,
    limit: int = Query(default=10, description="新聞數量上限")
):
    """
    取得 Wantgoo 個股新聞
    
    從 https://www.wantgoo.com/stock/{stock_code} 爬取最新消息
    """
    if not WANTGOO_AVAILABLE:
        raise HTTPException(status_code=503, detail="Wantgoo 服務暫時不可用")
    
    try:
        news = await wantgoo_crawler.get_stock_news(stock_code, limit)
        
        # 如果從概覽頁取得的新聞不夠，從新聞頁補充
        if len(news) < limit:
            more_news = await wantgoo_crawler.get_stock_news_page(stock_code, limit - len(news))
            news.extend(more_news)
        
        # 分析新聞情緒
        positive = len([n for n in news if n.get('sentiment') == 'positive'])
        negative = len([n for n in news if n.get('sentiment') == 'negative'])
        neutral = len(news) - positive - negative
        
        if positive > negative:
            overall_sentiment = "正面"
        elif negative > positive:
            overall_sentiment = "負面"
        else:
            overall_sentiment = "中性"
        
        return {
            "status": "success",
            "stock_code": stock_code,
            "source": "wantgoo",
            "timestamp": datetime.now().isoformat(),
            "news": news[:limit],
            "count": len(news),
            "sentiment_analysis": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "overall": overall_sentiment
            }
        }
        
    except Exception as e:
        logger.error(f"取得 Wantgoo 新聞失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/batch",
    summary="批量分析多檔股票",
    description="批量取得多檔股票的綜合分析摘要"
)
async def batch_analysis(
    symbols: str = Query(..., description="股票代碼，逗號分隔 (如: 2330,2454,2317)")
):
    """
    批量分析多檔股票
    """
    if not ANALYZER_AVAILABLE:
        raise HTTPException(status_code=503, detail="分析服務暫時不可用")
    
    try:
        stock_codes = [s.strip() for s in symbols.split(',')][:10]  # 最多10檔
        
        results = []
        for code in stock_codes:
            try:
                result = await analyze_stock_comprehensive(code)
                results.append({
                    "stock_code": code,
                    "stock_name": result['stock_name'],
                    "overall_score": result['overall_score'],
                    "recommendation": result['recommendation'],
                    "buy_signals_count": len(result['buy_signals']),
                    "sell_signals_count": len(result['sell_signals']),
                    "risk_count": len(result['risk_alerts']),
                    "trend": result['technical_indicators']['trend'] if result['technical_indicators'] else '盤整',
                    "target_price": result['target_price'],
                    "stop_loss": result['stop_loss']
                })
            except Exception as e:
                results.append({
                    "stock_code": code,
                    "error": str(e)
                })
        
        # 按評分排序
        valid_results = [r for r in results if 'overall_score' in r]
        valid_results.sort(key=lambda x: x['overall_score'], reverse=True)
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "count": len(results),
            "results": results,
            "top_pick": valid_results[0] if valid_results else None
        }
        
    except Exception as e:
        logger.error(f"批量分析失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/market-overview",
    summary="取得市場綜合概覽",
    description="取得今日市場整體狀況，包含三大法人、熱門股、新聞等"
)
async def get_market_overview():
    """
    取得市場綜合概覽
    """
    try:
        result = {}
        
        # 三大法人
        if TWSE_AVAILABLE:
            institutional = await twse_crawler.get_institutional_trading()
            result["institutional"] = institutional
            
            # 漲跌排行
            gainers = await twse_crawler.get_price_ranking("up")
            losers = await twse_crawler.get_price_ranking("down")
            
            result["top_gainers"] = gainers[:5]
            result["top_losers"] = losers[:5]
        
        # 新聞
        if NEWS_AVAILABLE:
            report = await news_crawler.generate_daily_report()
            result["news_summary"] = {
                "total_news": report.get('total_news', 0),
                "sentiment": report.get('overall_sentiment', {}),
                "hot_stocks": report.get('hot_stocks', {}),
                "themes": report.get('themes', [])
            }
        
        result["status"] = "success"
        result["timestamp"] = datetime.now().isoformat()
        
        return result
        
    except Exception as e:
        logger.error(f"取得市場概覽失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 輔助函數 ====================

def _generate_health_summary(financial: Dict, valuation: Dict) -> str:
    """生成財務健康摘要"""
    if not financial:
        return "無法取得財務資料"
    
    points = []
    
    roe = financial.get('roe', 0)
    if roe > 15:
        points.append(f"ROE 優異 ({roe}%)")
    elif roe < 0:
        points.append(f"ROE 偏低需關注")
    
    debt_ratio = financial.get('debt_ratio', 0)
    if debt_ratio > 50:
        points.append(f"負債比偏高 ({debt_ratio}%)")
    
    current_ratio = financial.get('current_ratio', 0)
    if current_ratio < 1:
        points.append("流動比率低於標準")
    
    if valuation:
        pe = valuation.get('pe_ratio', 0)
        if 0 < pe < 15:
            points.append(f"本益比合理 ({pe}倍)")
        elif pe > 30:
            points.append(f"本益比偏高 ({pe}倍)")
    
    return "。".join(points) if points else "財務狀況正常"


def _generate_technical_signals(technical: Dict) -> List[Dict]:
    """生成技術面訊號"""
    if not technical:
        return []
    
    signals = []
    
    # RSI
    rsi = technical.get('rsi_14', 50)
    if rsi > 70:
        signals.append({"indicator": "RSI", "signal": "超買", "value": rsi})
    elif rsi < 30:
        signals.append({"indicator": "RSI", "signal": "超賣", "value": rsi})
    
    # MACD
    macd = technical.get('macd', 0)
    macd_signal = technical.get('macd_signal', '')
    signals.append({
        "indicator": "MACD",
        "signal": macd_signal,
        "value": macd
    })
    
    # KD
    kd_k = technical.get('kd_k', 50)
    kd_d = technical.get('kd_d', 50)
    if kd_k > kd_d and kd_k < 30:
        signals.append({"indicator": "KD", "signal": "低檔黃金交叉", "value": f"{kd_k}/{kd_d}"})
    elif kd_k < kd_d and kd_k > 70:
        signals.append({"indicator": "KD", "signal": "高檔死亡交叉", "value": f"{kd_k}/{kd_d}"})
    
    # 趨勢
    trend = technical.get('trend', '盤整')
    signals.append({"indicator": "趨勢", "signal": trend, "value": trend})
    
    return signals


# ==================== PDF 報告下載 ====================

@router.get("/report/pdf/{stock_code}")
async def download_pdf_report(stock_code: str):
    """
    下載股票分析 PDF 報告
    
    生成 A4 格式的專業股票分析報告，可直接下載分享給好友
    """
    if not ANALYZER_AVAILABLE:
        raise HTTPException(status_code=503, detail="分析服務不可用")
    
    try:
        # 使用 stock_analyzer 取得 dataclass 物件
        analysis = await stock_analyzer.analyze(stock_code)
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"找不到股票 {stock_code} 的分析資料")
        
        # 轉換為 dict
        ti = analysis.technical_indicators
        fh = analysis.financial_health
        inst = analysis.institutional_trading
        
        analysis_dict = {
            'stock_code': analysis.stock_code,
            'stock_name': analysis.stock_name,
            'overall_score': analysis.overall_score,
            'recommendation': analysis.recommendation,
            'target_price': analysis.target_price,
            'stop_loss': analysis.stop_loss,
            'ai_summary': analysis.ai_summary,
            'technical_indicators': {
                'current_price': ti.current_price if ti else 0,
                'change_pct': ti.change_pct if ti else 0,
                'ma5': ti.ma5 if ti else 0,
                'ma10': ti.ma10 if ti else 0,
                'ma20': ti.ma20 if ti else 0,
                'ma60': ti.ma60 if ti else 0,
                'ma_arrangement': ti.ma_arrangement if ti else '',
                'ma_signal': ti.ma_signal if ti else '',
                'ma_trend': ti.ma_trend if ti else '',
                'resistance_1': ti.resistance_1 if ti else 0,
                'resistance_2': ti.resistance_2 if ti else 0,
                'support_1': ti.support_1 if ti else 0,
                'support_2': ti.support_2 if ti else 0,
                'rsi_14': ti.rsi_14 if ti else 50,
                'macd': ti.macd if ti else 0,
                'trend': ti.trend if ti else '盤整',
            } if ti else {},
            'financial_health': {
                'roe': fh.roe if fh else 0,
                'eps': fh.eps if fh else 0,
                'revenue_growth_3y': fh.revenue_growth_3y if fh else 0,
                'gross_margin': fh.gross_margin if fh else 0,
                'debt_ratio': fh.debt_ratio if fh else 0,
            } if fh else {},
            'institutional_trading': {
                'foreign_net': inst.foreign_net if inst else 0,
                'trust_net': inst.trust_net if inst else 0,
                'dealer_net': inst.dealer_net if inst else 0,
                'total_net': inst.total_net if inst else 0,
            } if inst else {},
        }
        
        # 加入量價分析
        try:
            vpa = analysis.volume_price_analysis
            if vpa:
                analysis_dict['volume_price_analysis'] = {
                    'trend_direction': vpa.trend_direction if hasattr(vpa, 'trend_direction') else '',
                    'trend_confidence': vpa.trend_confidence if hasattr(vpa, 'trend_confidence') else 0,
                    'volume_price_confirmation': vpa.volume_price_confirmation if hasattr(vpa, 'volume_price_confirmation') else '',
                    'confirmation_signal': vpa.confirmation_signal if hasattr(vpa, 'confirmation_signal') else '',
                    'confirmation_strength': vpa.confirmation_strength if hasattr(vpa, 'confirmation_strength') else 0,
                    'divergence_detected': vpa.divergence_detected if hasattr(vpa, 'divergence_detected') else False,
                    'divergence_type': vpa.divergence_type if hasattr(vpa, 'divergence_type') else '',
                    'divergence_description': vpa.divergence_description if hasattr(vpa, 'divergence_description') else '',
                    'volume_ratio': vpa.volume_ratio if hasattr(vpa, 'volume_ratio') else 1,
                    'obv_trend': vpa.obv_trend if hasattr(vpa, 'obv_trend') else '',
                    'predicted_direction': vpa.predicted_direction if hasattr(vpa, 'predicted_direction') else '',
                    'key_signals': vpa.key_signals if hasattr(vpa, 'key_signals') else [],
                }
            else:
                analysis_dict['volume_price_analysis'] = None
        except Exception:
            analysis_dict['volume_price_analysis'] = None
        
        # 取得新聞資料
        try:
            news = await stock_analyzer._get_stock_news(stock_code)
            analysis_dict['related_news'] = news if news else []  # 全部新聞
        except Exception:
            analysis_dict['related_news'] = []
        
        # 加入法人籌碼分析 (NEW)
        try:
            from app.services.taifex_crawler import taifex_crawler
            from app.services.margin_trading_crawler import margin_trading_crawler
            from app.services.twse_crawler import twse_crawler
            import asyncio
            
            # 並行取得籌碼數據
            futures_task = taifex_crawler.get_institutional_summary()
            margin_task = margin_trading_crawler.get_margin_sentiment()
            continuous_task = twse_crawler.get_stock_institutional(stock_code, 30)
            
            futures_data, margin_data, continuous_raw = await asyncio.gather(
                futures_task, margin_task, continuous_task,
                return_exceptions=True
            )
            
            # 期貨選擇權數據
            chip_analysis = {}
            if not isinstance(futures_data, Exception) and futures_data.get('success'):
                analysis_info = futures_data.get('analysis', {})
                chip_analysis['futures'] = {
                    'foreign_futures_net': analysis_info.get('foreign_futures_net', 0),
                    'pc_ratio': analysis_info.get('pc_ratio', 0),
                    'foreign_stance': analysis_info.get('foreign_stance', '中性'),
                    'market_sentiment': analysis_info.get('market_sentiment', '中性'),
                }
            else:
                chip_analysis['futures'] = {
                    'foreign_futures_net': 0,
                    'pc_ratio': 0,
                    'foreign_stance': '資料取得中',
                    'market_sentiment': '資料取得中',
                }
            
            # 融資融券數據
            if not isinstance(margin_data, Exception) and margin_data.get('success'):
                chip_analysis['margin'] = {
                    'retail_sentiment': margin_data.get('retail_sentiment', '中性'),
                    'margin_change_ratio': margin_data.get('margin_change_ratio', 0),
                    'short_change_ratio': margin_data.get('short_change_ratio', 0),
                }
            else:
                chip_analysis['margin'] = {
                    'retail_sentiment': '資料取得中',
                    'margin_change_ratio': 0,
                    'short_change_ratio': 0,
                }
            
            # 計算綜合分數
            foreign_net = chip_analysis['futures']['foreign_futures_net']
            pc_ratio = chip_analysis['futures']['pc_ratio']
            margin_ratio = chip_analysis['margin']['margin_change_ratio'] or 0
            
            futures_score = min(max(foreign_net / 100, -50), 50)
            options_score = (1 - pc_ratio) * 30 if pc_ratio > 0 else 0
            margin_score = margin_ratio * 5
            total_score = futures_score + options_score + margin_score
            
            if total_score > 30:
                overall_stance = "強烈看多"
            elif total_score > 10:
                overall_stance = "偏多"
            elif total_score > -10:
                overall_stance = "中性"
            elif total_score > -30:
                overall_stance = "偏空"
            else:
                overall_stance = "強烈看空"
            
            chip_analysis['summary'] = {
                'overall_stance': overall_stance,
                'total_score': round(total_score, 1),
            }
            
            # 個股法人連續買賣超
            if not isinstance(continuous_raw, Exception) and continuous_raw:
                def calculate_continuous(net_list):
                    if not net_list:
                        return {"direction": None, "days": 0}
                    direction = "buy" if net_list[0] > 0 else "sell" if net_list[0] < 0 else None
                    if direction is None:
                        return {"direction": None, "days": 0}
                    days = 0
                    for net in net_list:
                        if (direction == "buy" and net > 0) or (direction == "sell" and net < 0):
                            days += 1
                        else:
                            break
                    return {"direction": direction, "days": days}
                
                foreign_nets = [d.get('foreign_net', 0) for d in continuous_raw]
                investment_nets = [d.get('investment_net', 0) for d in continuous_raw]
                dealer_nets = [d.get('dealer_net', 0) for d in continuous_raw]
                
                chip_analysis['continuous'] = {
                    'foreign': calculate_continuous(foreign_nets),
                    'investment': calculate_continuous(investment_nets),
                    'dealer': calculate_continuous(dealer_nets),
                }
            else:
                chip_analysis['continuous'] = {}
            
            analysis_dict['chip_analysis'] = chip_analysis
            
        except Exception as e:
            logger.warning(f"取得法人籌碼失敗: {e}")
            analysis_dict['chip_analysis'] = None
        
        # 加入買入/賣出訊號和風險警示
        if analysis.buy_signals:
            analysis_dict['buy_signals'] = [
                {'type': s.type.value, 'name': s.name, 'description': s.description, 'confidence': s.confidence}
                for s in analysis.buy_signals[:3]  # 最多 3 個
            ]
        else:
            analysis_dict['buy_signals'] = []
            
        if analysis.sell_signals:
            analysis_dict['sell_signals'] = [
                {'type': s.type.value, 'name': s.name, 'description': s.description, 'confidence': s.confidence}
                for s in analysis.sell_signals[:3]  # 最多 3 個
            ]
        else:
            analysis_dict['sell_signals'] = []
            
        if analysis.risk_alerts:
            analysis_dict['risk_warnings'] = [
                {'level': w.level.value, 'name': w.title, 'description': w.description}
                for w in analysis.risk_alerts[:2]  # 最多 2 個
            ]
        else:
            analysis_dict['risk_warnings'] = []
        
        # 生成 PDF
        from app.services.pdf_report_service import generate_stock_report_pdf
        pdf_bytes, report_id = generate_stock_report_pdf(analysis_dict)
        
        # 設定檔案名稱
        from datetime import datetime
        from urllib.parse import quote
        filename = f"{stock_code}_{analysis.stock_name}_分析報告_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # 回傳 PDF 檔案
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
                "Content-Type": "application/pdf",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成 PDF 報告失敗: {e}")
        raise HTTPException(status_code=500, detail=f"生成報告失敗: {str(e)}")


@router.get("/report/genz/{stock_code}")
async def download_genz_report(stock_code: str):
    """
    下載 GenZ 風格投資懶人包 PDF 報告
    
    特色：
    - 表情符號表達情緒 (🔥/👍/😐/💩)
    - 口語化翻譯專業術語
    - 給新手的實用建議
    - 簡單易懂的進場/停損建議
    """
    if not ANALYZER_AVAILABLE:
        raise HTTPException(status_code=503, detail="分析服務不可用")
    
    try:
        # 使用 stock_analyzer 取得 dataclass 物件
        analysis = await stock_analyzer.analyze(stock_code)
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"找不到股票 {stock_code} 的分析資料")
        
        # 轉換為 dict
        ti = analysis.technical_indicators
        fh = analysis.financial_health
        inst = analysis.institutional_trading
        
        analysis_dict = {
            'stock_code': analysis.stock_code,
            'stock_name': analysis.stock_name,
            'overall_score': analysis.overall_score,
            'recommendation': analysis.recommendation,
            'target_price': analysis.target_price,
            'stop_loss': analysis.stop_loss,
            'ai_summary': analysis.ai_summary,
            'technical_indicators': {
                'current_price': ti.current_price if ti else 0,
                'change_pct': ti.change_pct if ti else 0,
                'ma_arrangement': ti.ma_arrangement if ti else '',
                'trend': ti.trend if ti else '盤整',
                'rsi_14': ti.rsi_14 if ti else 50,
                'macd': ti.macd if ti else 0,
                'support_1': ti.support_1 if ti else 0,
            } if ti else {},
            'financial_health': {
                'roe': fh.roe if fh else 0,
                'pe_ratio': fh.eps if fh else 0,  # 使用 EPS 暫代
            } if fh else {},
            'institutional_trading': {
                'foreign_net': inst.foreign_net if inst else 0,
                'total_net': inst.total_net if inst else 0,
            } if inst else {},
        }
        
        # 生成 GenZ 風格 PDF
        from app.services.pdf_report_service import generate_genz_report_pdf
        pdf_bytes, report_id = generate_genz_report_pdf(analysis_dict)
        
        # 設定檔案名稱
        from datetime import datetime
        from urllib.parse import quote
        filename = f"{stock_code}_{analysis.stock_name}_懶人包_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # 回傳 PDF 檔案
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
                "Content-Type": "application/pdf",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成 GenZ PDF 報告失敗: {e}")
        raise HTTPException(status_code=500, detail=f"生成報告失敗: {str(e)}")

# ==================== 5分鐘線技術分析監控 (NEW!) ====================

@router.get(
    "/technical/5m/{stock_code}",
    summary="取得股票 5 分鐘線技術分析",
    description="獲取盤中 5 分鐘 K 線數據、MA 均線、RSI、MACD 等指標"
)
async def get_technical_5m_analysis(stock_code: str):
    """
    獲取盤中 5 分鐘線技術分析 (包含 Fubon 優先，YFinance 備援)
    """
    try:
        from fubon_client import fubon_client
        from app.services.technical_analysis_service import tech_analysis_service
        from datetime import datetime
        import asyncio
        
        today = datetime.now().strftime("%Y-%m-%d")
        candles      = []
        today_candles = []

        # ★ 策略：優先用 fubon_client.get_candles()（內建 Fubon即時盤中→5分K + yfinance備援）
        try:
            raw = await fubon_client.get_candles(stock_code, timeframe="5")
            if raw and len(raw) > 0:
                candles = raw
                today_candles = [c for c in candles if c.get('date','').startswith(today)]
                # 統一格式：確保 key 是 date（而非 datetime）
                candles = [{
                    "date":   c.get("date",""),
                    "open":   float(c.get("open", 0)),
                    "high":   float(c.get("high", 0)),
                    "low":    float(c.get("low", 0)),
                    "close":  float(c.get("close", 0)),
                    "volume": float(c.get("volume", 0)),
                } for c in candles]
                logger.info(f"✅ fubon_client.get_candles 5m: {len(candles)} 根, 今日 {len(today_candles)} 根")
        except Exception as e:
            logger.warning(f"fubon_client.get_candles 5m 失敗，改用 yfinance: {e}")
            candles = []

        # ☆ 備援：fubon_client 失敗時直接用 yfinance.download（盡量避免，有延遲）
        if not candles:
            try:
                import yfinance as yf
                from app import patch_yfinance

                yf_symbol = patch_yfinance.fix_taiwan_symbol(stock_code)

                hist_5m = await asyncio.wait_for(
                    asyncio.to_thread(
                        yf.download,
                        yf_symbol,
                        period="5d",
                        interval="5m",
                        progress=False,
                        auto_adjust=True,
                        prepost=False,
                    ),
                    timeout=10.0
                )

                if not hist_5m.empty:
                    if hasattr(hist_5m.columns, 'levels'):
                        hist_5m.columns = hist_5m.columns.get_level_values(0)
                    hist_5m.index = hist_5m.index.tz_convert('Asia/Taipei')
                    for index, row in hist_5m.iterrows():
                        candles.append({
                            "date":   index.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                            "open":   float(row["Open"]),
                            "high":   float(row["High"]),
                            "low":    float(row["Low"]),
                            "close":  float(row["Close"]),
                            "volume": float(row["Volume"])
                        })
                    today_candles = [c for c in candles if c['date'].startswith(today)]
                    logger.info(f"✅ yfinance.download 5m 備援: {len(candles)} 根, 今日 {len(today_candles)} 根")
                else:
                    logger.warning(f"yfinance.download 5m 無資料 ({yf_symbol})")

            except Exception as e:
                logger.warning(f"yfinance 5m 備援也失敗: {e}")
                candles = []
                today_candles = []

        # 2. 如果 yfinance 5m 也失敗，用日線保底（確保 MA 有計算基礎）
        if not candles:
            try:
                import yfinance as yf
                from app import patch_yfinance
                yf_symbol = patch_yfinance.fix_taiwan_symbol(stock_code)
                ticker = yf.Ticker(yf_symbol)

                hist_daily = await asyncio.wait_for(
                    asyncio.to_thread(ticker.history, period="3mo", interval="1d"),
                    timeout=10.0
                )
                if not hist_daily.empty:
                    if hasattr(hist_daily.index, 'tz') and hist_daily.index.tz:
                        hist_daily.index = hist_daily.index.tz_convert('Asia/Taipei')
                    for index, row in hist_daily.iterrows():
                        candles.append({
                            "date": index.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                            "open":   float(row["Open"]),
                            "high":   float(row["High"]),
                            "low":    float(row["Low"]),
                            "close":  float(row["Close"]),
                            "volume": float(row["Volume"])
                        })
                    logger.info(f"✅ yfinance 日線保底成功: {len(candles)} 根 K 棒")
            except Exception as e:
                logger.error(f"日線保底也失敗: {e}")

        if not candles:
            return {
                "success": False,
                "message": "無法獲取 K 線數據 (Fubon & YFinance 皆無回應)",
                "stock_code": stock_code
            }
            
        # 3. 計算技術指標
        analysis = tech_analysis_service.calculate_indicators(candles)
        
        if "error" in analysis:
            return {
                "success": False,
                "message": analysis["error"],
                "stock_code": stock_code
            }
            
        if not analysis:
            return {
                "success": False,
                "message": "無法生成技術分析數據",
                "stock_code": stock_code
            }
            
        # 4. 僅返回「今日」的 K 線給前端繪圖
        #    優先顯示今日 → 今日若真的沒有才 fallback 到最近一個交易日
        if "history" in analysis and analysis["history"]:
            all_candles = analysis["history"]
            if all_candles:
                # 先嘗試過濾出今日資料
                today_filtered = [c for c in all_candles if c['date'].startswith(today)]
                if today_filtered:
                    # ✅ 今日有資料 → 只顯示今日
                    analysis["history"] = today_filtered
                    logger.info(f"📈 顯示今日 {today} K線: {len(today_filtered)} 根")
                else:
                    # ⚠️ 今日真的沒資料 → fallback 到最後一個交易日（昨天）
                    latest_date = all_candles[-1]['date'].split('T')[0]
                    analysis["history"] = [c for c in all_candles if c['date'].startswith(latest_date)]
                    logger.info(f"📅 今日無資料，顯示最近交易日 {latest_date} K線: {len(analysis['history'])} 根")

        # ★ 5. 用 Fubon 即時報價合成「當前進行中的 K 棒」
        #    yfinance 有 15-20 分鐘延遲，用即時報價補上缺口
        try:
            quote = await fubon_client.get_quote(stock_code)
            if quote and quote.get('price') and "history" in analysis:
                live_price  = float(quote['price'])
                live_volume = int(quote.get('volume', 0))

                # 計算「當前 5m K 棒」的起始時間（向下對齊到最近的 5 分鐘）
                now_dt     = datetime.now()
                minute_5   = (now_dt.minute // 5) * 5
                bar_start  = now_dt.replace(minute=minute_5, second=0, microsecond=0)
                bar_date   = bar_start.strftime("%Y-%m-%dT%H:%M:%S+08:00")

                h = analysis["history"]
                if h:
                    last_bar_date    = h[-1].get("date", "")[:16]
                    current_bar_date = bar_date[:16]

                    # 前一根繼承 MA 值，確保 LIVE 棒的 MA 線不中斷
                    prev = h[-1]
                    prev_ma5  = prev.get("MA5",  prev.get("close"))
                    prev_ma10 = prev.get("MA10", prev.get("close"))
                    prev_ma20 = prev.get("MA20", prev.get("close"))

                    if last_bar_date != current_bar_date:
                        # 補上即時 K 棒
                        prev_close = float(prev.get("close", live_price))
                        analysis["history"].append({
                            "date":   bar_date,
                            "open":   prev_close,
                            "high":   max(prev_close, live_price),
                            "low":    min(prev_close, live_price),
                            "close":  live_price,
                            "volume": live_volume,
                            "MA5":    prev_ma5,   # 繼承前一根
                            "MA10":   prev_ma10,
                            "MA20":   prev_ma20,
                            "_live":  True
                        })
                        logger.info(
                            f"📡 補上即時 K 棒 {current_bar_date} "
                            f"O={prev_close} C={live_price}"
                            f"（yfinance 最後根: {last_bar_date}）"
                        )
                    else:
                        # 當前 K 棒時間相同 → 更新最後一根收盤價為即時價
                        h[-1]["close"]  = live_price
                        if live_price > h[-1].get("high", 0):
                            h[-1]["high"] = live_price
                        if live_price < h[-1].get("low", float("inf")):
                            h[-1]["low"]  = live_price
                        h[-1]["_live"] = True
        except Exception as eq_err:
            logger.debug(f"即時 K 棒合成失敗 (非致命): {eq_err}")

        return {
            "success": True,
            "stock_code": stock_code,
            "timeframe": "5m",
            "timestamp": datetime.now().isoformat(),
            "data": analysis
        }
        
    except Exception as e:
        logger.error(f"獲取 5m 技術分析失敗: {e}")
        return {
            "success": False,
            "message": str(e),
            "stock_code": stock_code
        }



# ==================== MA 突破 Telegram 警報 ====================
# 防重複發送：記錄 {stock_code: last_alert_bar_time}
_MA_ALERT_SENT: Dict[str, str] = {}

@router.get(
    "/technical/ma-cross-alert/{stock_code}",
    summary="偵測 K 線同時突破 MA5 & MA10 並推送 Telegram",
)
async def ma_cross_alert(
    stock_code: str,
    h1: float = Query(default=0),
    h2: float = Query(default=0),
    h3: float = Query(default=0),
    vwap: float = Query(default=0),
):
    """前端每 5 秒呼叫；偵測到突破時推 Telegram，同一根 K 棒只發一次"""
    try:
        from fubon_client import fubon_client
        from app.services.notification_manager import notification_manager

        today = datetime.now().strftime("%Y-%m-%d")

        # 查詢股票名稱（供訊息顯示）
        stock_name = ""
        try:
            stock_name = await fubon_client.get_stock_name(stock_code)
        except Exception:
            try:
                from app.services.stock_comprehensive_analyzer import get_stock_name as _gsn
                stock_name = _gsn(stock_code) or ""
            except Exception:
                stock_name = ""
        stock_label = f"{stock_code} {stock_name}".strip()

        # 取今日 5m K 棒
        candles = []
        try:
            raw = await fubon_client.get_candles(stock_code, timeframe="5")
            if raw:
                candles = [{"date": c.get("date",""), "open": float(c.get("open",0)),
                            "high": float(c.get("high",0)), "low": float(c.get("low",0)),
                            "close": float(c.get("close",0)), "volume": float(c.get("volume",0))}
                           for c in raw]
        except Exception:
            pass

        today_candles = [c for c in candles if c["date"].startswith(today)]
        if len(today_candles) < 10:
            return {"triggered": False, "reason": f"今日K棒不足10根（現有{len(today_candles)}根）"}

        # 重算 MA（與前端一致）
        def calc_ma(bars, period):
            return [None if i < period-1
                    else sum(b["close"] for b in bars[i-period+1:i+1]) / period
                    for i, _ in enumerate(bars)]

        ma5_list  = calc_ma(today_candles, 5)
        ma10_list = calc_ma(today_candles, 10)
        n = len(today_candles)
        cur, prev = today_candles[-1], today_candles[-2]
        cur_ma5, cur_ma10 = ma5_list[n-1], ma10_list[n-1]
        prev_ma5, prev_ma10 = ma5_list[n-2], ma10_list[n-2]

        if None in (cur_ma5, cur_ma10, prev_ma5, prev_ma10):
            return {"triggered": False, "reason": "MA值尚未收斂"}

        cur_bar_time = cur["date"][:16]

        # 突破判斷：前根未過 MA5 或 MA10，當根同時超越兩條
        prev_below = prev["close"] <= prev_ma5 or prev["close"] <= prev_ma10
        cur_above  = cur["close"] > cur_ma5 and cur["close"] > cur_ma10
        triggered  = prev_below and cur_above

        already_sent = (_MA_ALERT_SENT.get(stock_code) == cur_bar_time)

        result = {
            "triggered": triggered, "already_sent": already_sent,
            "cur_close": round(cur["close"],2),
            "cur_ma5":   round(cur_ma5,2), "cur_ma10": round(cur_ma10,2),
            "cur_bar_time": cur_bar_time,
        }

        if triggered and not already_sent:
            _MA_ALERT_SENT[stock_code] = cur_bar_time
            above_vwap = vwap > 0 and cur["close"] >= vwap
            above_h3   = h3 > 0 and cur["close"] > h3
            strength   = "🔥 強烈" if (above_vwap and above_h3) else "⚡ 普通"

            if above_vwap:
                action = (f"股價站上 VWAP({vwap:.2f}) + 雙均線突破 → 偏多\n"
                          f"停損參考 MA5 {cur_ma5:.2f} 下方\n"
                          f"目標 H2 {h2:.2f} → H1 {h1:.2f}")
            else:
                action = (f"股價仍在 VWAP({vwap:.2f}) 下方，注意假突破\n"
                          f"等站上 VWAP 確認後再進場")

            msg = (
                f"📈 <b>MA 雙線突破警報</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"🏷 <b>股票</b>：{stock_label}\n"
                f"⏰ <b>時間</b>：{datetime.now().strftime('%H:%M:%S')}（{cur_bar_time[-5:]} K棒）\n"
                f"💰 <b>現價</b>：<b>{cur['close']:.2f}</b>\n\n"
                f"📊 <b>均線狀態</b>\n"
                f"• MA5  {cur_ma5:.2f} ✅ 突破\n"
                f"• MA10 {cur_ma10:.2f} ✅ 突破\n"
                f"• VWAP {vwap:.2f} {'✅ 站上' if above_vwap else '❌ 未過'}\n\n"
            )
            if h1 > 0:
                msg += f"🗼 H1 {h1:.2f}  H2 {h2:.2f}  H3 {h3:.2f}\n\n"
            msg += f"{strength} 突破\n━━━━━━━━━━━━━━\n💡 {action}\n"

            try:
                sent = notification_manager.send_to_channel("telegram", msg)
                result["telegram_sent"] = sent
                logger.info(f"📢 MA突破警報發送: {stock_code} @ {cur_bar_time}")
            except Exception as te:
                result["telegram_error"] = str(te)

        return result

    except Exception as e:
        logger.error(f"MA突破偵測失敗 {stock_code}: {e}")
        return {"triggered": False, "error": str(e)}
