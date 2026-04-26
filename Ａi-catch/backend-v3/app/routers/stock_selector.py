"""
選股決策引擎 API 路由
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import asyncio
import logging

from ..services.integrated_stock_selector import (
    integrated_selector,
    analyze_single_stock,
    analyze_multiple_stocks,
    get_top_recommendations
)
from ..services.broker_flow_analyzer import (
    broker_flow_analyzer,
    get_fubon_xindan_flow,
    get_fubon_xindan_top_stocks
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stock-selector", tags=["選股決策引擎"])


class StockAnalysisRequest(BaseModel):
    """股票分析請求"""
    stock_codes: List[str]
    include_ai: bool = True


class BrokerFlowRequest(BaseModel):
    """券商進出查詢請求"""
    stock_code: str
    days: int = 5


@router.get("/analyze/{stock_code}")
async def analyze_stock_endpoint(stock_code: str):
    """
    分析單一股票
    
    Args:
        stock_code: 股票代碼
        
    Returns:
        完整分析結果
    """
    try:
        logger.info(f"API: 分析股票 {stock_code}")
        
        result = await analyze_single_stock(stock_code)
        
        if result.get('metadata', {}).get('error'):
            raise HTTPException(status_code=500, detail="分析失敗")
        
        return {
            'success': True,
            'data': result
        }
        
    except Exception as e:
        logger.error(f"API錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/batch")
async def batch_analyze_stocks_endpoint(request: StockAnalysisRequest):
    """
    批量分析股票（快速模式）
    
    基於券商買超數據快速生成評分，並使用 yfinance 獲取現價計算目標價
    
    Args:
        request: 包含股票代碼列表的請求
        
    Returns:
        分析結果列表
    """
    try:
        import yfinance as yf
        logger.info(f"API: 快速批量分析 {len(request.stock_codes)} 檔股票")
        
        # 使用快速評分模式 - 基於券商數據
        results = []
        
        # 獲取券商數據作為評分基礎
        from ..services.advanced_broker_crawler import advanced_broker_crawler
        
        broker_df = advanced_broker_crawler.get_broker_flow_by_date(
            broker_code='9600',
            sub_broker_code='9661'  # 富邦新店
        )
        
        # 建立股票代碼到券商數據的映射
        broker_map = {}
        if broker_df is not None and not broker_df.empty:
            for idx, row in broker_df.iterrows():
                try:
                    stock_code_val = row['stock_code'] if 'stock_code' in broker_df.columns else ''
                    stock_name_val = row['stock_name'] if 'stock_name' in broker_df.columns else ''
                    buy_count_val = row['buy_count'] if 'buy_count' in broker_df.columns else 0
                    sell_count_val = row['sell_count'] if 'sell_count' in broker_df.columns else 0
                    net_count_val = row['net_count'] if 'net_count' in broker_df.columns else 0
                    
                    broker_map[str(stock_code_val)] = {
                        'stock_name': str(stock_name_val),
                        'buy_count': int(buy_count_val) if buy_count_val else 0,
                        'sell_count': int(sell_count_val) if sell_count_val else 0,
                        'net_count': int(net_count_val) if net_count_val else 0
                    }
                except Exception as e:
                    logger.warning(f"處理券商數據行失敗: {e}")
                    continue
        
        # 批量獲取股票名稱（使用現有API）
        stock_names = {}
        try:
            from ..main import STOCK_NAMES
            if isinstance(STOCK_NAMES, dict):
                stock_names = STOCK_NAMES
            logger.info(f"已載入 {len(stock_names)} 個股票名稱")
        except Exception as e:
            logger.warning(f"載入股票名稱失敗: {e}")
            stock_names = {}
        
        import pandas as pd
        
        # 嘗試獲取現價（使用 yfinance）
        stock_prices = {}
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            # 逐個獲取股價（更可靠）
            async def fetch_single_price(code: str) -> tuple:
                def get_price():
                    try:
                        ticker = yf.Ticker(f"{code}.TW")
                        hist = ticker.history(period="5d")
                        if not hist.empty:
                            return float(hist['Close'].iloc[-1])
                    except:
                        pass
                    return 0.0
                
                try:
                    price = await asyncio.wait_for(
                        loop.run_in_executor(None, get_price),
                        timeout=3.0
                    )
                    return (code, price)
                except:
                    return (code, 0.0)
            
            # 並行獲取所有股價（限制並發數為 3）
            semaphore = asyncio.Semaphore(3)
            async def fetch_with_limit(code):
                async with semaphore:
                    return await fetch_single_price(code)
            
            tasks = [fetch_with_limit(code) for code in request.stock_codes]
            price_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in price_results:
                if isinstance(result, tuple) and len(result) == 2:
                    code, price = result
                    if price > 0:
                        stock_prices[code] = price
                        logger.info(f"股票 {code} 現價: {price}")
            
            logger.info(f"成功獲取 {len(stock_prices)}/{len(request.stock_codes)} 檔股票價格")
            
        except Exception as e:
            logger.warning(f"獲取股價失敗: {e}")
        
        for stock_code in request.stock_codes:
            code_str = str(stock_code)
            
            # 安全獲取券商數據
            broker_data = {}
            if isinstance(broker_map, dict):
                broker_data = broker_map.get(code_str, {})
            
            # 獲取股票名稱：優先用券商數據，其次用內建名稱庫
            stock_name = ''
            if isinstance(broker_data, dict):
                stock_name = broker_data.get('stock_name', '')
            if not stock_name and isinstance(stock_names, dict):
                stock_name = stock_names.get(code_str, code_str)
            if not stock_name:
                stock_name = code_str
            
            # 獲取現價
            current_price = 0
            if isinstance(stock_prices, dict):
                current_price = stock_prices.get(code_str, 0)
            
            # 基於券商數據計算評分
            net_count = 0
            buy_count = 0
            if isinstance(broker_data, dict):
                net_count = broker_data.get('net_count', 0) or 0
                buy_count = broker_data.get('buy_count', 0) or 0
            
            # 評分邏輯：淨買超越多分數越高
            base_score = 50
            
            # 淨流入評分 (0-30分)
            if net_count > 100000:
                net_score = 30
            elif net_count > 50000:
                net_score = 25
            elif net_count > 10000:
                net_score = 20
            elif net_count > 5000:
                net_score = 15
            elif net_count > 1000:
                net_score = 10
            elif net_count > 0:
                net_score = 5
            else:
                net_score = 0
            
            # 買進量評分 (0-20分)
            if buy_count > 100000:
                buy_score = 20
            elif buy_count > 50000:
                buy_score = 15
            elif buy_count > 10000:
                buy_score = 10
            else:
                buy_score = 5
            
            total_score = min(100, base_score + net_score + buy_score)
            
            # 評級與目標價/停損價計算
            if total_score >= 85:
                grade = 'A+'
                action = '強力買入'
                target_pct = 0.10  # +10%
                stop_pct = 0.05   # -5%
            elif total_score >= 75:
                grade = 'A'
                action = '買入'
                target_pct = 0.08  # +8%
                stop_pct = 0.05   # -5%
            elif total_score >= 65:
                grade = 'B+'
                action = '偏多'
                target_pct = 0.06  # +6%
                stop_pct = 0.04   # -4%
            elif total_score >= 55:
                grade = 'B'
                action = '持有'
                target_pct = 0.05  # +5%
                stop_pct = 0.04   # -4%
            else:
                grade = 'C'
                action = '觀望'
                target_pct = 0.03  # +3%
                stop_pct = 0.03   # -3%
            
            # 計算目標價和停損價
            if current_price > 0:
                target_price = round(current_price * (1 + target_pct), 2)
                stop_loss = round(current_price * (1 - stop_pct), 2)
            else:
                target_price = 0
                stop_loss = 0
            
            results.append({
                '股票代碼': code_str,
                '股票名稱': stock_name,
                '現價': current_price,
                '綜合評分': total_score,
                '評級': grade,
                '建議動作': action,
                '目標價': target_price,
                '停損價': stop_loss,
                '建議倉位(%)': round(total_score / 10, 1),
                '風險等級': 'medium' if total_score >= 60 else 'high',
                '基本面分數': 50,  # 快速模式使用預設值
                '技術面分數': 50,
                '籌碼面分數': min(100, net_score + buy_score + 40),
                '淨買超': net_count,
                '買進張數': buy_count
            })
        
        # 按評分排序
        results.sort(key=lambda x: x['綜合評分'], reverse=True)
        
        logger.info(f"✅ 快速分析完成，共 {len(results)} 檔股票")
        
        return {
            'success': True,
            'data': results,
            'count': len(results),
            'mode': 'fast'  # 標記為快速模式
        }
        
    except Exception as e:
        import traceback
        logger.error(f"API錯誤: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/batch/full")
async def batch_analyze_stocks_full_endpoint(request: StockAnalysisRequest):
    """
    批量分析股票（完整模式）
    
    使用 StockComprehensiveAnalyzer 進行完整的五維度分析：
    - 基本面 (30%): ROE、EPS、營收成長、毛利率
    - 技術面 (25%): MA、RSI、MACD、KD
    - 籌碼面 (25%): 券商買賣超
    - 法人 (10%): 三大法人買賣超
    - 市場 (10%): 趨勢、成交量
    
    注意：此模式可能需要 15-30 秒完成
    
    Args:
        request: 包含股票代碼列表的請求
        
    Returns:
        完整分析結果列表
    """
    try:
        from ..services.stock_comprehensive_analyzer import StockComprehensiveAnalyzer
        import asyncio
        
        logger.info(f"API: 完整批量分析 {len(request.stock_codes)} 檔股票")
        
        analyzer = StockComprehensiveAnalyzer()
        results = []
        
        # 限制並發數避免過載
        semaphore = asyncio.Semaphore(2)
        
        async def analyze_single(code: str):
            async with semaphore:
                try:
                    # 每個股票最多 30 秒
                    analysis = await asyncio.wait_for(
                        analyzer.analyze(code),
                        timeout=30.0
                    )
                    
                    # 轉換為標準格式
                    # 處理相關新聞
                    news_count = len(analysis.related_news) if analysis.related_news else 0
                    top_news = analysis.related_news[:3] if analysis.related_news else []
                    news_titles = [n.get('title', '')[:50] for n in top_news]
                    
                    return {
                        '股票代碼': analysis.stock_code,
                        '股票名稱': analysis.stock_name,
                        '現價': analysis.technical_indicators.current_price if analysis.technical_indicators else 0,
                        '綜合評分': analysis.overall_score,
                        '評級': _get_grade(analysis.overall_score),
                        '建議動作': analysis.recommendation,
                        '目標價': analysis.target_price or 0,
                        '停損價': analysis.stop_loss or 0,
                        '建議倉位(%)': round(analysis.overall_score / 10, 1),
                        '風險等級': _get_risk_level(analysis.risk_alerts),
                        # 五維度評分
                        '基本面分數': _get_dimension_score(analysis.dimension_scores, '基本面'),
                        '技術面分數': _get_dimension_score(analysis.dimension_scores, '技術面'),
                        '籌碼面分數': _get_dimension_score(analysis.dimension_scores, '籌碼面'),
                        '法人分數': _get_dimension_score(analysis.dimension_scores, '法人'),
                        '市場分數': _get_dimension_score(analysis.dimension_scores, '市場'),
                        '法人動向': _get_institutional_summary(analysis.institutional_trading),
                        '買入訊號數': len(analysis.buy_signals),
                        '賣出訊號數': len(analysis.sell_signals),
                        '風險警示數': len(analysis.risk_alerts),
                        '相關新聞數': news_count,
                        '新聞標題': news_titles,
                        'AI摘要': analysis.ai_summary[:200] if analysis.ai_summary else '',
                        '分析模式': 'full'
                    }
                except asyncio.TimeoutError:
                    logger.warning(f"股票 {code} 分析超時")
                    return {
                        '股票代碼': code,
                        '股票名稱': code,
                        '綜合評分': 0,
                        '評級': 'N/A',
                        '建議動作': '分析超時',
                        '分析模式': 'timeout'
                    }
                except Exception as e:
                    logger.warning(f"股票 {code} 分析失敗: {e}")
                    return {
                        '股票代碼': code,
                        '股票名稱': code,
                        '綜合評分': 0,
                        '評級': 'N/A',
                        '建議動作': '分析失敗',
                        '分析模式': 'error'
                    }
        
        # 並行分析所有股票
        tasks = [analyze_single(code) for code in request.stock_codes]
        results = await asyncio.gather(*tasks)
        
        # 關閉分析器
        await analyzer.close()
        
        # 按評分排序（過濾掉失敗的）
        valid_results = [r for r in results if r.get('綜合評分', 0) > 0]
        valid_results.sort(key=lambda x: x['綜合評分'], reverse=True)
        
        # 失敗的放最後
        failed_results = [r for r in results if r.get('綜合評分', 0) <= 0]
        
        all_results = valid_results + failed_results
        
        # 獲取產業新聞摘要
        news_summary = {}
        try:
            from ..services.news_analysis_service import news_analysis_service
            news_data = news_analysis_service.get_all_news_with_analysis()
            if news_data:
                news_summary = {
                    '熱門產業': news_data.get('hotIndustries', [])[:5],
                    '熱門關鍵字': news_data.get('hotKeywords', [])[:10],
                    '市場情緒': news_data.get('sentimentAnalysis', {}),
                    '可操作建議': news_data.get('actionableInsights', [])[:3],
                    '分析摘要': news_data.get('smartSummary', '')[:300]
                }
        except Exception as e:
            logger.warning(f"獲取產業新聞失敗: {e}")
        
        # 獲取市場維度分析
        market_analysis = {}
        try:
            from ..services.market_dimension_analyzer import market_dimension_analyzer
            market_result = market_dimension_analyzer.analyze()
            market_analysis = {
                '市場評分': market_result.get('total_score', 5),
                '市場狀態': market_result.get('market_status', ''),
                '操作建議': market_result.get('action_recommendation', ''),
                '風險等級': market_result.get('risk_level', 'medium'),
                '大盤趨勢': market_result.get('components', {}).get('trend', {}).get('score', 0),
                '成交量': market_result.get('components', {}).get('volume', {}).get('score', 0),
                '外資期貨': market_result.get('components', {}).get('futures', {}).get('score', 0),
                'VIX指數': market_result.get('components', {}).get('vix', {}).get('score', 0)
            }
        except Exception as e:
            logger.warning(f"獲取市場維度分析失敗: {e}")
        
        logger.info(f"✅ 完整分析完成，成功 {len(valid_results)}/{len(request.stock_codes)} 檔")
        
        return {
            'success': True,
            'data': all_results,
            'count': len(all_results),
            'success_count': len(valid_results),
            'mode': 'full',
            'news_summary': news_summary,  # 產業新聞摘要
            'market_analysis': market_analysis  # 市場維度分析
        }
        
    except Exception as e:
        import traceback
        logger.error(f"完整分析 API 錯誤: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_grade(score: float) -> str:
    """根據分數獲取評級"""
    if score >= 85:
        return 'A+'
    elif score >= 75:
        return 'A'
    elif score >= 65:
        return 'B+'
    elif score >= 55:
        return 'B'
    elif score >= 45:
        return 'C+'
    else:
        return 'C'


def _get_dimension_score(dimension_scores, name: str) -> float:
    """從維度分數列表中獲取指定維度的分數"""
    if not dimension_scores:
        return 50
    for dim in dimension_scores:
        if hasattr(dim, 'name') and dim.name == name:
            return dim.score if hasattr(dim, 'score') else 50
    return 50


def _get_risk_level(risk_alerts) -> str:
    """根據風險警示判斷風險等級"""
    if not risk_alerts:
        return 'low'
    if len(risk_alerts) >= 3:
        return 'high'
    elif len(risk_alerts) >= 1:
        return 'medium'
    return 'low'


def _get_institutional_summary(institutional_trading) -> str:
    """生成法人動向摘要"""
    if not institutional_trading:
        return '無資料'
    
    try:
        total_net = institutional_trading.total_net if hasattr(institutional_trading, 'total_net') else 0
        if total_net > 1000:
            return f'法人買超 {total_net:,} 張'
        elif total_net < -1000:
            return f'法人賣超 {abs(total_net):,} 張'
        else:
            return '法人持平'
    except:
        return '無資料'

@router.get("/recommendations")
async def get_recommendations_endpoint(
    stock_codes: List[str] = Query(..., description="股票代碼列表"),
    top_n: int = Query(10, description="前N名")
):
    """
    獲取推薦股票
    
    Args:
        stock_codes: 股票代碼列表
        top_n: 前N名
        
    Returns:
        推薦股票列表
    """
    try:
        logger.info(f"API: 獲取前 {top_n} 名推薦")
        
        df = await get_top_recommendations(stock_codes, top_n)
        
        if df.empty:
            return {
                'success': True,
                'data': [],
                'count': 0
            }
        
        results = df.to_dict('records')
        
        return {
            'success': True,
            'data': results,
            'count': len(results),
            'top_n': top_n
        }
        
    except Exception as e:
        logger.error(f"API錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/broker-flow/{stock_code}")
async def get_broker_flow_endpoint(
    stock_code: str,
    days: int = Query(5, description="分析天數")
):
    """
    獲取券商進出資料
    
    Args:
        stock_code: 股票代碼
        days: 分析天數
        
    Returns:
        券商進出分析
    """
    try:
        logger.info(f"API: 查詢 {stock_code} 券商進出 ({days}天)")
        
        result = get_fubon_xindan_flow(stock_code, days)
        
        return {
            'success': True,
            'data': result
        }
        
    except Exception as e:
        logger.error(f"API錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/broker-flow/fubon-xindan/top-stocks")
async def get_fubon_xindan_top_endpoint(
    top_n: int = Query(20, description="前N名"),
    sub_broker_code: str = Query("9661", description="分點代碼 (9661=新店, 9600=總公司, 9604=陽明, 9624=竹北, 9647=新竹, 9654=永和)")
):
    """
    獲取富邦券商分點買超前N名股票
    
    【已修復】現已支援正確的「富邦-新店」分點代碼 9661
    
    可用的分點代碼：
    - 9661: 新店 (預設)
    - 9600: 總公司
    - 9604: 陽明
    - 9624: 竹北
    - 9647: 新竹
    - 9654: 永和
    
    Args:
        top_n: 前N名
        sub_broker_code: 分點代碼
        
    Returns:
        買超股票列表
    """
    try:
        logger.info(f"API: 查詢富邦分點 {sub_broker_code} 買超前 {top_n} 名")
        
        # 使用修復後的 advanced_broker_crawler
        from ..services.advanced_broker_crawler import advanced_broker_crawler
        
        results = advanced_broker_crawler.get_top_stocks_by_broker(
            broker_code='9600',
            sub_broker_code=sub_broker_code,
            top_n=top_n,
            min_net_count=0  # 獲取所有數據
        )
        
        # 分點名稱映射
        branch_names = {
            '9661': '新店',       # 富邦新店
            '9600': '總公司',
            '9604': '陽明',
            '9624': '竹北',
            '9647': '新竹',
            '9654': '永和',
            '0039003600310052': '南員林'
        }
        branch_name = branch_names.get(sub_broker_code, sub_broker_code)

        
        return {
            'success': True,
            'data': results,
            'count': len(results),
            'broker': f'富邦-{branch_name}',
            'sub_broker_code': sub_broker_code
        }
        
    except Exception as e:
        logger.error(f"API錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/fubon-html")
async def debug_fubon_html_endpoint(
    broker_code: str = Query("9600", description="券商代碼"),
    sub_broker_code: str = Query("9600", description="分點代碼")
):
    """
    調試端點：直接測試富邦網站連接
    
    用於診斷富邦券商數據抓取問題
    """
    import requests
    import re
    
    try:
        url = "https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm"
        params = {'a': broker_code, 'b': sub_broker_code}
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.encoding = 'big5'
        
        html_content = response.text
        
        # 統計信息
        stock_count = len(re.findall(r"GenLink2stk\('AS(\d{4})','([^']+)'\)", html_content))
        has_error = "券商分點代碼有誤" in html_content
        
        # 可用分點列表
        available_branches = {
            "新店": "9661",          # 富邦新店
            "總公司": "9600",
            "陽明": "9604",
            "竹北": "9624",
            "新竹": "9647",
            "永和": "9654",
            "南員林": "0039003600310052"
        }
        
        return {
            "success": not has_error,
            "status_code": response.status_code,
            "content_length": len(html_content),
            "stock_count": stock_count,
            "has_error": has_error,
            "error_message": "券商分點代碼有誤" if has_error else None,
            "url": str(response.url),
            "params_used": params,
            "available_branches": available_branches,
            "html_preview": html_content[:1500] if not has_error else html_content
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/broker-flow/all-brokers/{stock_code}")
async def get_all_brokers_flow_endpoint(stock_code: str):
    """
    獲取所有關鍵券商對特定股票的進出
    
    Args:
        stock_code: 股票代碼
        
    Returns:
        所有券商進出資料
    """
    try:
        logger.info(f"API: 查詢 {stock_code} 所有券商進出")
        
        result = broker_flow_analyzer.get_broker_flow_summary(stock_code, days=5)
        
        return {
            'success': True,
            'data': result
        }
        
    except Exception as e:
        logger.error(f"API錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/report")
async def export_report_endpoint(
    stock_codes: List[str] = Query(..., description="股票代碼列表"),
    format: str = Query('csv', description="匯出格式 (csv/excel)")
):
    """
    匯出分析報告
    
    Args:
        stock_codes: 股票代碼列表
        format: 匯出格式
        
    Returns:
        檔案路徑
    """
    try:
        logger.info(f"API: 匯出報告 ({format})")
        
        df = await analyze_multiple_stocks(stock_codes)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="無資料可匯出")
        
        filepath = integrated_selector.export_report(df, format=format)
        
        if not filepath:
            raise HTTPException(status_code=500, detail="匯出失敗")
        
        return {
            'success': True,
            'filepath': filepath,
            'format': format,
            'count': len(df)
        }
        
    except Exception as e:
        logger.error(f"API錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康檢查"""
    return {
        'status': 'healthy',
        'service': '選股決策引擎',
        'version': '1.0.0'
    }


@router.get("/market-dimension")
async def get_market_dimension_analysis():
    """
    市場維度分析 API
    
    分析當前市場環境，包含：
    - 大盤趨勢 (4分/40%): 均線排列、漲跌幅、關鍵位置
    - 成交量 (3分/30%): 價量配合、量能強度、量能趨勢
    - 外資期貨 (2分/20%): 淨部位、變化趨勢、一致性
    - VIX指數 (1分/10%): 恐慌程度、變化趨勢
    
    Returns:
        市場維度分析結果 (0-10分)
    """
    try:
        from ..services.market_dimension_analyzer import market_dimension_analyzer
        
        logger.info("API: 執行市場維度分析")
        
        result = market_dimension_analyzer.analyze()
        
        logger.info(f"✅ 市場維度分析完成: {result['total_score']}/10")
        
        return {
            'success': True,
            'data': result
        }
        
    except Exception as e:
        import traceback
        logger.error(f"市場維度分析錯誤: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
