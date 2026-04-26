"""
監控清單分析 API
為主控台的監控清單提供完整的技術分析和信心度評分
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/watchlist-analysis", response_model=Dict[str, Any])
async def get_watchlist_analysis():
    """
    獲取監控清單的完整分析
    包含信心度、技術指標、進場/停損/目標價
    ✅ 使用富邦API真實數據
    """
    try:
        # 從主控台獲取監控清單
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get('http://127.0.0.1:8082/api/stocks', timeout=5.0)
                watchlist_data = response.json()
            stock_codes = [stock['code'].replace('.TW', '') for stock in watchlist_data.get('stocks', [])]
        except Exception as e:
            logger.warning(f"無法從主控台獲取監控清單: {e}")
            # 使用預設監控清單
            stock_codes = ["2330", "2317", "2454"]
        
        logger.info(f"📊 分析監控清單: {stock_codes}")
        
        # 導入富邦API服務
        try:
            from app.services.real_data_service import fubon_service
            use_fubon = True
            logger.info("✅ 富邦API服務已載入")
        except ImportError as e:
            logger.warning(f"⚠️ 富邦API服務載入失敗: {e}")
            use_fubon = False
        
        # 為每支股票生成分析
        analyzed_stocks = []
        
        if use_fubon:
            # 嘗試使用富邦API獲取真實數據
            try:
                # 初始化富邦連接
                logger.info("=" * 60)
                logger.info("🔍 開始初始化富邦API")
                logger.info(f"fubon_service._initialized = {fubon_service._initialized}")
                
                success = await fubon_service.initialize()
                
                logger.info(f"🔍 初始化結果: success={success}")
                logger.info(f"🔍 初始化後 _initialized={fubon_service._initialized}")
                logger.info(f"🔍 client存在: {fubon_service.client is not None}")
                if fubon_service.client:
                    logger.info(f"🔍 client連接狀態: {fubon_service.client.is_connected}")
                logger.info("=" * 60)
                
                if success:
                    logger.info("🎯 使用富邦API獲取真實數據")
                    success_count = 0
                    
                    for idx, stock_code in enumerate(stock_codes[:20]):
                        try:
                            logger.info(f"📊 [{idx+1}/{min(20, len(stock_codes))}] 獲取 {stock_code} 數據...")
                            
                            # 獲取真實技術指標
                            indicators = await fubon_service.get_technical_indicators(stock_code)
                            
                            logger.info(f"📊 {stock_code} 指標結果: {indicators is not None}")
                            
                            if indicators:
                                price = indicators.get('current_price', 0)
                                logger.info(f"✅ {stock_code} 成功！價格={price}")
                                
                                # 基於真實數據生成分析
                                analysis = await generate_real_stock_analysis(stock_code, indicators, idx)
                                analyzed_stocks.append(analysis)
                                success_count += 1
                                
                                # 避免請求過快
                                await asyncio.sleep(0.3)
                            else:
                                # 單支股票失敗，用模擬數據
                                logger.warning(f"⚠️ {stock_code} 無法獲取真實數據，使用模擬")
                                analysis = generate_mock_stock_analysis(stock_code, idx)
                                analyzed_stocks.append(analysis)
                        except Exception as e:
                            logger.error(f"❌ 處理 {stock_code} 錯誤: {e}", exc_info=True)
                            analysis = generate_mock_stock_analysis(stock_code, idx)
                            analyzed_stocks.append(analysis)
                    
                    logger.info(f"🎯 富邦API完成: {success_count}/{len(stock_codes[:20])} 支成功")
                else:
                    logger.warning("⚠️ 富邦API連接失敗，使用模擬數據")
                    for idx, stock_code in enumerate(stock_codes[:20]):
                        analysis = generate_mock_stock_analysis(stock_code, idx)
                        analyzed_stocks.append(analysis)
            except Exception as e:
                logger.error(f"❌ 富邦API錯誤: {e}，使用模擬數據", exc_info=True)
                for idx, stock_code in enumerate(stock_codes[:20]):
                    analysis = generate_mock_stock_analysis(stock_code, idx)
                    analyzed_stocks.append(analysis)
        else:
            # 富邦服務未載入，使用模擬數據
            logger.warning("⚠️ 使用模擬數據（富邦服務未載入）")
            for idx, stock_code in enumerate(stock_codes[:20]):
                analysis = generate_mock_stock_analysis(stock_code, idx)
                analyzed_stocks.append(analysis)
        
        # 按信心度排序
        analyzed_stocks.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 重新設定排名
        for idx, stock in enumerate(analyzed_stocks):
            stock['rank'] = idx + 1
        
        return {
            "analysis_time": datetime.now().isoformat(),
            "total_stocks": len(analyzed_stocks),
            "analyzed_stocks": analyzed_stocks,
            "source": "Fubon API Real-Time" if use_fubon and analyzed_stocks else "Simulated Data"
        }
        
    except Exception as e:
        logger.error(f"監控清單分析錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析錯誤: {str(e)}")


async def generate_real_stock_analysis(stock_code: str, indicators: Dict[str, Any], index: int) -> Dict[str, Any]:
    """基於富邦API真實數據生成股票分析"""
    
    # 股票名稱對應
    stock_names = {
        "2330": "台積電", "2317": "鴻海", "2454": "聯發科",
        "2881": "富邦金", "2882": "國泰金", "2412": "中華電",
        "2308": "台達電", "8046": "南電", "1802": "台玻",
        "2313": "華通", "2331": "精英", "8110": "華東",
        "8021": "尖點", "3706": "神達", "5521": "工信",
        "2449": "京元電", "3363": "上詮", "2379": "瑞昱",
        "3661": "世芯-KY", "2382": "廣達", "6446": "藥華藥"
    }
    
    stock_name = stock_names.get(stock_code, stock_code)
    
    # 從指標獲取真實數據
    current_price = indicators.get('current_price', 100.0)
    ma5 = indicators.get('ma5', 0)
    ma10 = indicators.get('ma10', 0)
    ma20 = indicators.get('ma20', 0)
    ma60 = indicators.get('ma60', 0)
    rsi = indicators.get('rsi', 50)
    macd = indicators.get('macd', 0)
    macd_signal = indicators.get('macd_signal', 0)
    volume_ratio = indicators.get('volume_ratio', 1.0)
    
    # 基於真實技術指標計算信心度和評分
    score = 0
    reasons = []
    
    # 1. 量能分析 (30分)
    if volume_ratio > 2.0:
        score += 30
        reasons.append("✅ 量能爆發，成交量超過平均2倍以上")
    elif volume_ratio > 1.5:
        score += 20
        reasons.append("✅ 量能放大，主力進場跡象明顯")
    elif volume_ratio > 1.2:
        score += 10
        reasons.append("⚠️ 量能溫和增加")
    
    # 2. 均線多頭排列 (25分)
    if ma5 > ma10 > ma20 > ma60:
        score += 25
        reasons.append("✅ 均線完美多頭排列")
    elif ma5 > ma10 > ma20:
        score += 15
        reasons.append("✅ 短中期均線多頭")
    elif ma5 > ma20:
        score += 10
        reasons.append("⚠️ 短期均線走強")
    
    # 3. 突破關鍵價位 (20分)
    if current_price > ma20 and current_price > ma60:
        score += 20
        reasons.append(f"✅ 突破季線和年線 (MA20: {ma20:.1f}, MA60: {ma60:.1f})")
    elif current_price > ma20:
        score += 10
        reasons.append(f"✅ 站上季線 (MA20: {ma20:.1f})")
    
    # 4. RSI強勢區 (15分)
    if 50 < rsi < 70:
        score += 15
        reasons.append(f"✅ RSI強勢區 ({rsi:.1f})")
    elif 40 < rsi < 80:
        score += 10
        reasons.append(f"⚠️ RSI中性偏強 ({rsi:.1f})")
    elif rsi > 70:
        score += 5
        reasons.append(f"⚠️ RSI過熱 ({rsi:.1f})，注意回檔")
    
    # 5. MACD多頭 (10分)
    if macd > macd_signal and macd > 0:
        score += 10
        reasons.append("✅ MACD黃金交叉且在零軸上")
    elif macd > macd_signal:
        score += 5
        reasons.append("⚠️ MACD轉強中")
    
    # 計算信心度 (0-1)
    confidence = min(0.95, max(0.50, score / 100))
    
    # 如果沒有明確理由，添加基礎說明
    if not reasons:
        reasons.append("⚠️ 技術面中性，等待明確訊號")
    
    # 計算進場/目標/停損價
    entry_price = current_price
    
    # 根據技術強度調整目標價
    if score >= 80:
        target_price = current_price * 1.08  # +8%
        stop_loss = current_price * 0.97     # -3%
    elif score >= 60:
        target_price = current_price * 1.05  # +5%
        stop_loss = current_price * 0.98     # -2%
    else:
        target_price = current_price * 1.03  # +3%
        stop_loss = current_price * 0.99     # -1%
    
    # 建議倉位
    if confidence >= 0.85:
        position_size = "建議倉位 30-40%"
    elif confidence >= 0.75:
        position_size = "建議倉位 20-30%"
    else:
        position_size = "建議倉位 10-20%"
    
    # 操作策略
    if score >= 80:
        strategy = "強勢突破，順勢追單，嚴守停損"
    elif score >= 60:
        strategy = "技術面轉強，回檔進場，順勢操作"
    else:
        strategy = "觀望為主，等待更明確訊號"
    
    return {
        "rank": index + 1,
        "stock_id": stock_code,
        "stock_name": stock_name,
        "total_score": score,
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "entry_price": round(entry_price, 2),
        "target_price": round(target_price, 2),
        "stop_loss": round(stop_loss, 2),
        "current_price": round(current_price, 2),
        "position_size": position_size,
        "strategy": strategy,
        "data_source": "✅ Fubon API Real-Time"
    }


def generate_mock_stock_analysis(stock_code: str, index: int) -> Dict[str, Any]:
    """為單支股票生成模擬分析（fallback）"""
    
    # 股票名稱對應
    stock_names = {
        "2330": "台積電", "2317": "鴻海", "2454": "聯發科",
        "2881": "富邦金", "2882": "國泰金", "2412": "中華電",
        "2308": "台達電", "8046": "南電", "1802": "台玻",
        "2313": "華通", "2331": "精英", "8110": "華東",
        "8021": "尖點", "3706": "神達", "5521": "工信",
        "2449": "京元電", "3363": "上詮", "2379": "瑞昱",
        "3661": "世芯-KY", "2382": "廣達", "6446": "藥華藥"
    }
    
    stock_name = stock_names.get(stock_code, stock_code)
    
    # 更接近真實的股價（2025-12-16 參考價格）
    base_prices = {
        "2330": 1035.0,   # 台積電
        "2317": 110.0,    # 鴻海
        "2454": 1275.0,   # 聯發科
        "2881": 89.5,     # 富邦金
        "2882": 68.0,     # 國泰金
        "2412": 125.0,    # 中華電
        "2308": 358.0,    # 台達電
        "8046": 380.0,    # 南電
        "1802": 23.5,     # 台玻
        "2313": 43.0,     # 華通
        "2331": 32.0,     # 精英
        "8110": 115.0,    # 華東
        "8021": 75.0,     # 尖點
        "3706": 138.0,    # 神達
        "5521": 88.0,     # 工信
        "2449": 105.0,    # 京元電
        "3363": 72.0,     # 上詮
        "2379": 485.0,    # 瑞昱
        "3661": 1950.0,   # 世芯-KY
        "2382": 298.0,    # 廣達
        "6446": 780.0     # 藥華藥
    }
    
    current_price = base_prices.get(stock_code, 100.0)
    
    # 計算模擬信心度（基於index，實際應基於真實技術指標）
    confidence_base = 0.85 - (index * 0.05)
    confidence = max(0.60, min(0.95, confidence_base))
    
    # 計算總分
    total_score = int(confidence * 100)
    
    # 生成原因
    reasons = []
    if confidence >= 0.85:
        reasons = [
            "✅ 量能放大，主力進場跡象明顯",
            "✅ 突破關鍵技術位",
            "✅ 法人持續買超"
        ]
    elif confidence >= 0.75:
        reasons = [
            "✅ 技術面轉強",
            "✅ 均線多頭排列"
        ]
    else:
        reasons = [
            "⚠️ 盤整中，等待突破"
        ]
    
    # 計算進場/目標/停損價
    entry_price = current_price
    target_price = current_price * 1.05  # +5%
    stop_loss = current_price * 0.98     # -2%
    
    return {
        "rank": index + 1,
        "stock_id": stock_code,
        "stock_name": stock_name,
        "total_score": total_score,
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "entry_price": round(entry_price, 2),
        "target_price": round(target_price, 2),
        "stop_loss": round(stop_loss, 2),
        "current_price": round(current_price, 2),
        "position_size": "建議倉位 20-30%",
        "strategy": "順勢操作，嚴守紀律",
        "data_source": "⚠️ Simulated Data (Fallback)"
    }
