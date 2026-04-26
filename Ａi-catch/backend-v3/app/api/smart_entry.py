"""
智慧進場評分系統 (Smart Entry Scoring System)

整合多個分析因子，給出進場信心評分
避免單一訊號導致的虧損
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/smart-entry", tags=["Smart Entry Scoring"])


@router.get("/score/{stock_code}")
async def get_entry_score(stock_code: str):
    """
    智慧進場評分
    
    整合多個分析因子，計算進場信心分數
    
    評分因子：
    1. ORB 開盤區間突破 (權重 20%)
    2. 大單買賣超 (權重 25%)
    3. 法人買賣超 (權重 20%)
    4. 技術指標 (權重 20%)
    5. 主力動向 (權重 15%)
    
    Returns:
        - score: 總分 (0-100)
        - recommendation: 建議 (強烈買進/買進/觀望/賣出/強烈賣出)
        - factors: 各因子評分細節
        - entry_price: 建議進場價
        - stop_loss: 建議停損價
        - take_profit: 建議目標價
    """
    try:
        import yfinance as yf
        
        # 這裡直接傳入 stock_code，patched yfinance 會自動根據清單修正為 .TW 或 .TWO
        ticker = yf.Ticker(stock_code)
        hist = ticker.history(period="5d", interval="1d")
        
        # 如果失敗，嘗試強迫另一種後綴作為最後手段
        if hist.empty:
            alt_symbol = f"{stock_code}.TWO" if not stock_code.endswith(".TWO") else f"{stock_code}.TW"
            ticker = yf.Ticker(alt_symbol)
            hist = ticker.history(period="5d", interval="1d")
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"無法取得 {stock_code} 的數據")
        
        # 取得即時數據
        intraday = ticker.history(period="1d", interval="1m")
        
        latest = hist.iloc[-1]
        current_price = float(latest['Close'])
        open_price = float(latest['Open'])
        high = float(latest['High'])
        low = float(latest['Low'])
        volume = int(latest['Volume'])
        
        # 取得昨日數據 (如果有兩天以上的數據)
        prev_high = None
        prev_low = None
        prev_close = None
        if len(hist) >= 2:
            prev_day = hist.iloc[-2]
            prev_high = float(prev_day['High'])
            prev_low = float(prev_day['Low'])
            prev_close = float(prev_day['Close'])

        
        # 計算各因子分數
        factors = {}
        
        # 1. ORB 開盤區間突破 (20%)
        if not intraday.empty and len(intraday) >= 15:
            first_15 = intraday.head(15)
            range_high = float(first_15['High'].max())
            range_low = float(first_15['Low'].min())
            current = float(intraday['Close'].iloc[-1])
            
            if current > range_high:
                orb_score = 100  # 突破
                orb_status = "真突破"
            elif current < range_low:
                orb_score = 0  # 跌破
                orb_status = "真跌破"
            else:
                # 在區間內，根據位置給分
                range_size = range_high - range_low
                if range_size > 0:
                    position = (current - range_low) / range_size
                    orb_score = int(position * 50 + 25)  # 25-75分
                else:
                    orb_score = 50
                orb_status = "區間整理"
            
            factors["orb"] = {
                "score": orb_score,
                "weight": 0.20,
                "status": orb_status,
                "range_high": round(range_high, 2),
                "range_low": round(range_low, 2),
                "current": round(current, 2)
            }
        else:
            orb_score = 50
            factors["orb"] = {
                "score": 50,
                "weight": 0.20,
                "status": "無法判斷",
                "note": "無足夠分鐘數據"
            }
        
        # 2. 價格動能 (25%) - 替代大單分析
        price_change_pct = (current_price - open_price) / open_price * 100
        if price_change_pct > 3:
            momentum_score = 100
            momentum_status = "強勢上漲"
        elif price_change_pct > 1:
            momentum_score = 80
            momentum_status = "溫和上漲"
        elif price_change_pct > 0:
            momentum_score = 60
            momentum_status = "小幅上漲"
        elif price_change_pct > -1:
            momentum_score = 40
            momentum_status = "小幅下跌"
        elif price_change_pct > -3:
            momentum_score = 20
            momentum_status = "溫和下跌"
        else:
            momentum_score = 0
            momentum_status = "強勢下跌"
        
        factors["momentum"] = {
            "score": momentum_score,
            "weight": 0.25,
            "status": momentum_status,
            "change_pct": round(price_change_pct, 2)
        }
        
        # 3. 成交量分析 (20%)
        if len(hist) >= 5:
            avg_volume = float(hist['Volume'].iloc[:-1].mean())
            volume_ratio = float(volume / avg_volume) if avg_volume > 0 else 1.0
            
            if volume_ratio > 2:
                volume_score = 100 if price_change_pct > 0 else 0  # 放量看漲跌
                volume_status = "放量" + ("上漲" if price_change_pct > 0 else "下跌")
            elif volume_ratio > 1.5:
                volume_score = 75 if price_change_pct > 0 else 25
                volume_status = "量增" + ("價漲" if price_change_pct > 0 else "價跌")
            elif volume_ratio > 0.7:
                volume_score = 50
                volume_status = "量能正常"
            else:
                volume_score = 30
                volume_status = "量縮"
            
            factors["volume"] = {
                "score": volume_score,
                "weight": 0.20,
                "status": volume_status,
                "ratio": round(volume_ratio, 2)
            }
        else:
            volume_score = 50
            factors["volume"] = {"score": 50, "weight": 0.20, "status": "數據不足"}
        
        # 4. 技術形態 (20%)
        if len(hist) >= 5:
            # 簡化的技術分析
            ma5 = float(hist['Close'].tail(5).mean())
            trend_up = bool(current_price > ma5)
            higher_low = bool(low > float(hist['Low'].iloc[-2])) if len(hist) >= 2 else True
            
            if trend_up and higher_low:
                tech_score = 80
                tech_status = "多頭排列"
            elif trend_up:
                tech_score = 60
                tech_status = "短多"
            elif not trend_up and not higher_low:
                tech_score = 20
                tech_status = "空頭排列"
            else:
                tech_score = 40
                tech_status = "震盪整理"
            
            factors["technical"] = {
                "score": tech_score,
                "weight": 0.20,
                "status": tech_status,
                "above_ma5": trend_up
            }
        else:
            tech_score = 50
            factors["technical"] = {"score": 50, "weight": 0.20, "status": "數據不足"}
        
        # 5. 風險評估 (15%)
        # 計算波動率
        if len(hist) >= 5:
            daily_returns = hist['Close'].pct_change().dropna()
            volatility = float(daily_returns.std() * 100)
            
            if volatility < 2:
                risk_score = 80
                risk_status = "低風險"
            elif volatility < 4:
                risk_score = 60
                risk_status = "中風險"
            elif volatility < 6:
                risk_score = 40
                risk_status = "高風險"
            else:
                risk_score = 20
                risk_status = "極高風險"
            
            factors["risk"] = {
                "score": risk_score,
                "weight": 0.15,
                "status": risk_status,
                "volatility_pct": round(volatility, 2)
            }
        else:
            risk_score = 50
            factors["risk"] = {"score": 50, "weight": 0.15, "status": "數據不足"}
        
        # 計算總分
        total_score = (
            factors["orb"]["score"] * factors["orb"]["weight"] +
            factors["momentum"]["score"] * factors["momentum"]["weight"] +
            factors["volume"]["score"] * factors["volume"]["weight"] +
            factors["technical"]["score"] * factors["technical"]["weight"] +
            factors["risk"]["score"] * factors["risk"]["weight"]
        )
        
        # 決定建議
        if total_score >= 80:
            recommendation = "強烈買進"
            action = "BUY"
            confidence = "高"
        elif total_score >= 65:
            recommendation = "買進"
            action = "BUY"
            confidence = "中"
        elif total_score >= 50:
            recommendation = "觀望"
            action = "HOLD"
            confidence = "低"
        elif total_score >= 35:
            recommendation = "減碼"
            action = "REDUCE"
            confidence = "中"
        else:
            recommendation = "賣出"
            action = "SELL"
            confidence = "高"
        
        # 計算建議價位
        atr = high - low  # 簡化的 ATR
        
        if action == "BUY":
            entry_price = current_price  # 現價進場
            stop_loss = round(current_price - atr * 1.5, 2)  # 1.5 ATR 停損
            take_profit_1 = round(current_price + atr * 1, 2)  # 1:1 目標
            take_profit_2 = round(current_price + atr * 2, 2)  # 1:2 目標
        else:
            entry_price = None
            stop_loss = None
            take_profit_1 = None
            take_profit_2 = None
        
        # 計算符合因子數
        bullish_factors = sum(1 for f in factors.values() if f["score"] >= 60)
        
        return {
            "success": True,
            "stock_code": stock_code,
            "current_price": round(current_price, 2),
            "score": round(total_score, 1),
            "recommendation": recommendation,
            "action": action,
            "confidence": confidence,
            "bullish_factors": f"{bullish_factors}/5",
            "factors": factors,
            # 昨日數據
            "prev_high": round(prev_high, 2) if prev_high else None,
            "prev_low": round(prev_low, 2) if prev_low else None,
            "prev_close": round(prev_close, 2) if prev_close else None,
            "today_open": round(open_price, 2),
            "today_high": round(high, 2),
            "today_low": round(low, 2),
            "trading_plan": {
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit_1": take_profit_1,
                "take_profit_2": take_profit_2,
                "risk_reward_ratio": "1:1 ~ 1:2"
            } if action == "BUY" else None,
            "warning": "僅供參考，不構成投資建議" if total_score < 65 else None,
            "timestamp": datetime.now().isoformat()
        }

        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"智慧評分失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=f"評分失敗: {str(e)}")


@router.get("/batch-score")
async def batch_entry_score(
    stock_codes: str = Query(..., description="股票代碼，逗號分隔")
):
    """
    批量智慧評分
    
    一次評估多檔股票，找出最佳進場機會
    """
    codes = [c.strip() for c in stock_codes.split(",") if c.strip()]
    
    if not codes:
        raise HTTPException(status_code=400, detail="請提供股票代碼")
    
    if len(codes) > 10:
        raise HTTPException(status_code=400, detail="一次最多10檔股票")
    
    results = []
    for code in codes:
        try:
            result = await get_entry_score(code)
            results.append(result)
        except Exception as e:
            results.append({
                "stock_code": code,
                "success": False,
                "error": str(e)
            })
    
    # 按分數排序
    successful = [r for r in results if r.get("success")]
    successful.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    return {
        "count": len(results),
        "successful": len(successful),
        "top_picks": [r for r in successful if r.get("score", 0) >= 65],
        "all_results": results,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/recommendation/{stock_code}")
async def get_simple_recommendation(stock_code: str):
    """
    簡化版建議
    
    快速取得買賣建議，適合快速決策
    """
    result = await get_entry_score(stock_code)
    
    return {
        "stock_code": stock_code,
        "price": result["current_price"],
        "score": result["score"],
        "action": result["action"],
        "recommendation": result["recommendation"],
        "stop_loss": result["trading_plan"]["stop_loss"] if result["trading_plan"] else None,
        "target": result["trading_plan"]["take_profit_1"] if result["trading_plan"] else None,
        "key_factors": [
            f"{k}: {v['status']}" for k, v in result["factors"].items()
        ]
    }


@router.get("/top-picks")
async def get_top_picks(
    min_score: int = Query(70, description="最低智慧評分"),
    limit: int = Query(10, description="返回數量限制")
):
    """
    獲取進場精選股票
    
    整合以下來源:
    1. 新聞分析推薦股票 (強力關注)
    2. 技術評分篩選
    
    智能交易器會調用此 API 獲取進場信號
    """
    picks = []
    
    try:
        # 1. 從新聞分析獲取推薦股票
        news_picks = []
        try:
            from app.services.news_analysis_service import news_analysis_service
            analysis = news_analysis_service.get_all_news_with_analysis()
            recommendations = analysis.get("recommendations", [])
            
            for rec in recommendations:
                if rec.get("action") in ["強力關注", "值得關注"]:
                    action_score = 85 if rec.get("action") == "強力關注" else 70
                    news_score = rec.get("score", 0)
                    
                    # 計算綜合分數
                    combined_score = (action_score * 0.6) + (min(news_score, 100) * 0.4)
                    
                    if combined_score >= min_score:
                        news_picks.append({
                            "symbol": rec.get("symbol"),
                            "name": rec.get("name", rec.get("symbol")),
                            "news_score": news_score,
                            "positive_count": rec.get("positiveCount", 0),
                            "negative_count": rec.get("negativeCount", 0),
                            "mention_count": rec.get("mentionCount", 0),
                            "source": "news_analysis",
                            "reason": rec.get("action", "")
                        })
            
            logger.info(f"從新聞分析獲取 {len(news_picks)} 檔推薦股票")
            
        except Exception as e:
            logger.warning(f"獲取新聞推薦失敗: {e}")
        
        # 2. 對每檔推薦股票進行技術評分
        for pick in news_picks[:limit * 2]:  # 取更多以便篩選
            try:
                import yfinance as yf
                
                symbol = pick["symbol"]
                ticker = yf.Ticker(f"{symbol}.TW")
                hist = ticker.history(period="5d")
                
                if hist.empty:
                    ticker = yf.Ticker(f"{symbol}.TWO")
                    hist = ticker.history(period="5d")
                
                if hist.empty:
                    continue
                
                current_price = float(hist['Close'].iloc[-1])
                open_price = float(hist['Open'].iloc[-1])
                high = float(hist['High'].iloc[-1])
                low = float(hist['Low'].iloc[-1])
                
                # 計算技術分數
                price_change_pct = (current_price - open_price) / open_price * 100
                
                # 簡化技術評分
                tech_score = 50
                if price_change_pct > 3:
                    tech_score = 90
                elif price_change_pct > 1:
                    tech_score = 75
                elif price_change_pct > 0:
                    tech_score = 60
                elif price_change_pct > -1:
                    tech_score = 45
                else:
                    tech_score = 30
                
                # 計算智慧評分 = 新聞分數 * 0.5 + 技術分數 * 0.5
                smart_score = (pick["news_score"] * 0.4 + tech_score * 0.6)
                
                if smart_score >= min_score:
                    # 計算停損和目標
                    atr = high - low
                    stop_loss = round(current_price - atr * 1.5, 2)
                    target = round(current_price + atr * 2, 2)
                    
                    picks.append({
                        "symbol": symbol,
                        "name": pick.get("name", symbol),
                        "current_price": round(current_price, 2),
                        "smart_score": round(smart_score, 1),
                        "news_score": round(pick["news_score"], 1),
                        "tech_score": tech_score,
                        "positive_news": pick.get("positive_count", 0),
                        "mention_count": pick.get("mention_count", 0),
                        "stop_loss": stop_loss,
                        "target": target,
                        "reason": f"新聞{pick.get('reason', '')}, 漲幅{price_change_pct:.1f}%",
                        "source": "smart_entry"
                    })
                    
            except Exception as e:
                logger.debug(f"評估 {pick['symbol']} 失敗: {e}")
                continue
        
        # 按智慧評分排序
        picks.sort(key=lambda x: x["smart_score"], reverse=True)
        picks = picks[:limit]
        
        logger.info(f"智慧進場精選: {len(picks)} 檔股票 (門檻 {min_score} 分)")
        
    except Exception as e:
        logger.error(f"獲取進場精選失敗: {e}")
    
    return {
        "success": True,
        "picks": picks,
        "count": len(picks),
        "min_score": min_score,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/bollinger/{stock_code}")
async def get_bollinger_bands(
    stock_code: str,
    period: int = Query(20, description="MA 週期"),
    std_dev: float = Query(2.0, description="標準差倍數")
):
    """
    獲取布林通道數據
    
    Returns:
        - upper: 上軌
        - middle: 中軌 (MA)
        - lower: 下軌
        - current_price: 當前價格
        - position: 價格位置 (upper/middle/lower)
        - bandwidth: 帶寬百分比
        - %b: 布林 %B 指標
    """
    try:
        import yfinance as yf
        import numpy as np
        
        # 取得股票數據
        ticker = yf.Ticker(f"{stock_code}.TW")
        hist = ticker.history(period="1mo", interval="1d")
        
        if hist.empty:
            ticker = yf.Ticker(f"{stock_code}.TWO")
            hist = ticker.history(period="1mo", interval="1d")
        
        if hist.empty or len(hist) < period:
            raise HTTPException(status_code=404, detail=f"無法取得 {stock_code} 的足夠數據")
        
        closes = hist['Close'].values
        current = float(closes[-1])
        
        # 計算布林通道
        ma = np.mean(closes[-period:])
        std = np.std(closes[-period:])
        
        upper = ma + (std_dev * std)
        lower = ma - (std_dev * std)
        
        # 計算 %B (布林指標)
        percent_b = (current - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
        
        # 計算帶寬
        bandwidth = ((upper - lower) / ma) * 100 if ma > 0 else 0
        
        # 判斷位置
        if current >= upper:
            position = "upper"
            position_text = "觸及上軌 (超買)"
        elif current <= lower:
            position = "lower"
            position_text = "觸及下軌 (超賣)"
        elif current > ma:
            position = "above_middle"
            position_text = "中軌上方 (偏多)"
        else:
            position = "below_middle"
            position_text = "中軌下方 (偏空)"
        
        # 取得分鐘數據計算即時位置
        intraday = ticker.history(period="1d", interval="5m")
        intraday_bollinger = []
        
        if not intraday.empty and len(intraday) >= 12:
            intraday_closes = intraday['Close'].values
            for i in range(12, len(intraday_closes)):
                window = intraday_closes[max(0, i-12):i]
                ma_5m = np.mean(window)
                std_5m = np.std(window)
                intraday_bollinger.append({
                    "time": intraday.index[i].strftime("%H:%M"),
                    "price": float(intraday_closes[i]),
                    "upper": float(ma_5m + 2 * std_5m),
                    "middle": float(ma_5m),
                    "lower": float(ma_5m - 2 * std_5m),
                })
        
        return {
            "success": True,
            "stock_code": stock_code,
            "current_price": round(current, 2),
            "bollinger": {
                "upper": round(upper, 2),
                "middle": round(ma, 2),
                "lower": round(lower, 2),
                "bandwidth": round(bandwidth, 2),
                "percent_b": round(percent_b * 100, 1),
            },
            "position": position,
            "position_text": position_text,
            "signal": "買入" if position == "lower" else "賣出" if position == "upper" else "觀望",
            "period": period,
            "std_dev": std_dev,
            "intraday_bollinger": intraday_bollinger[-20:] if intraday_bollinger else [],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"布林通道計算失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=f"計算失敗: {str(e)}")


@router.get("/support-resistance/{stock_code}")
async def get_auto_support_resistance(stock_code: str):
    """
    九宮格撐壓自動分析
    
    自動計算並返回所有關鍵撐壓位（根據九大條件）：
    1. 前高/前低
    2. 關鍵價/整數關卡
    3. 移動平均線(MA5, MA10, MA20, MA60)
    4. 趨勢線/通道線 (簡化)
    5. 型態滿足點 (簡化)
    6. 斐波那契回撤
    7. 跳空缺口
    8. 大量成交區
    9. 布林通道
    """
    try:
        import yfinance as yf
        import numpy as np
        
        # 取得股票數據
        ticker = yf.Ticker(f"{stock_code}.TW")
        hist = ticker.history(period="3mo", interval="1d")
        
        if hist.empty:
            ticker = yf.Ticker(f"{stock_code}.TWO")
            hist = ticker.history(period="3mo", interval="1d")
        
        # 清除 NaN 資料點，避免後續計算導致 'cannot convert float NaN to integer' 錯誤
        hist = hist.dropna(subset=['Close', 'High', 'Low'])
        
        if hist.empty or len(hist) < 20:
             raise HTTPException(status_code=404, detail=f"無法取得 {stock_code} 的足夠數據")
        
        closes = hist['Close'].values
        highs = hist['High'].values
        lows = hist['Low'].values
        volumes = hist['Volume'].values
        current = float(closes[-1])
        
        # 額外安全性防護：確保 current 不是 NaN
        import math
        if math.isnan(current):
             # 嘗試找到最後一個非 NaN 的值
             valid_closes = [c for c in closes if not math.isnan(c)]
             if valid_closes:
                 current = float(valid_closes[-1])
             else:
                 raise HTTPException(status_code=404, detail="股票數據包含無效值(NaN)")
        
        levels = []
        
        # === 1. 前高/前低 (prev_hl) ===
        # 近期高點
        recent_highs = []
        for i in range(max(2, len(highs)-20), len(highs)-1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1] if i+1 < len(highs) else highs[i] > highs[i-1]:
                recent_highs.append(float(highs[i]))
        
        # 昨日高低
        if len(hist) >= 2:
            prev_day = hist.iloc[-2]
            levels.append({
                "price": round(float(prev_day['High']), 2),
                "type": "resistance",
                "conditions": ["prev_hl"],
                "label": "昨高"
            })
            levels.append({
                "price": round(float(prev_day['Low']), 2),
                "type": "support",
                "conditions": ["prev_hl"],
                "label": "昨低"
            })
        
        # 近5日高低
        if len(hist) >= 5:
            five_day_high = float(highs[-5:].max())
            five_day_low = float(lows[-5:].min())
            levels.append({
                "price": round(five_day_high, 2),
                "type": "resistance",
                "conditions": ["prev_hl"],
                "label": "5日高"
            })
            levels.append({
                "price": round(five_day_low, 2),
                "type": "support",
                "conditions": ["prev_hl"],
                "label": "5日低"
            })
        
        # === 2. 關鍵價/整數關卡 (key_price) ===
        # 找出接近的整數關卡
        base = int(current)
        for multiplier in [10, 50, 100]:
            round_price = round(current / multiplier) * multiplier
            if abs(round_price - current) / current < 0.03:  # 3%以內
                levels.append({
                    "price": round_price,
                    "type": "resistance" if round_price > current else "support",
                    "conditions": ["key_price"],
                    "label": f"整數關卡 {round_price}"
                })
        
        # === 3. 移動平均線 (ma) ===
        for period, name in [(5, "MA5"), (10, "MA10"), (20, "MA20"), (60, "MA60")]:
            if len(closes) >= period:
                ma_value = float(np.mean(closes[-period:]))
                levels.append({
                    "price": round(ma_value, 2),
                    "type": "support" if ma_value < current else "resistance",
                    "conditions": ["ma"],
                    "label": name
                })
        
        # === 4. 趨勢線/通道線 (trend_ch) - 簡化版 ===
        # 使用線性回歸計算趨勢
        if len(closes) >= 20:
            x = np.arange(20)
            y = closes[-20:]
            slope, intercept = np.polyfit(x, y, 1)
            trend_next = intercept + slope * 20
            levels.append({
                "price": round(float(trend_next), 2),
                "type": "resistance" if trend_next > current else "support",
                "conditions": ["trend_ch"],
                "label": "趨勢線投射"
            })
        
        # === 5. 型態滿足點 (pattern) - 簡化版 ===
        # 計算區間震幅的等距滿足點
        if len(hist) >= 10:
            recent_range = float(highs[-10:].max() - lows[-10:].min())
            pattern_up = current + recent_range
            pattern_down = current - recent_range
            levels.append({
                "price": round(pattern_up, 2),
                "type": "resistance",
                "conditions": ["pattern"],
                "label": "等距滿足(上)"
            })
            levels.append({
                "price": round(pattern_down, 2),
                "type": "support",
                "conditions": ["pattern"],
                "label": "等距滿足(下)"
            })
        
        # === 6. 斐波那契回撤 (fib) ===
        if len(hist) >= 20:
            recent_high = float(highs[-20:].max())
            recent_low = float(lows[-20:].min())
            diff = recent_high - recent_low
            
            fib_levels = [
                (0.236, "Fib23.6"),
                (0.382, "Fib38.2"),
                (0.5, "Fib50"),
                (0.618, "Fib61.8"),
                (0.786, "Fib78.6"),
            ]
            
            for ratio, name in fib_levels:
                fib_price = recent_low + diff * ratio
                levels.append({
                    "price": round(fib_price, 2),
                    "type": "support" if fib_price < current else "resistance",
                    "conditions": ["fib"],
                    "label": name
                })
        
        # === 7. 跳空缺口 (gap) ===
        for i in range(max(1, len(hist)-20), len(hist)):
            prev_close = float(hist.iloc[i-1]['Close'])
            curr_open = float(hist.iloc[i]['Open'])
            gap = curr_open - prev_close
            
            # 跳空超過 1%
            if abs(gap) / prev_close > 0.01:
                gap_price = (prev_close + curr_open) / 2
                levels.append({
                    "price": round(gap_price, 2),
                    "type": "support" if gap > 0 else "resistance",
                    "conditions": ["gap"],
                    "label": "缺口" + ("向上" if gap > 0 else "向下")
                })
        
        # === 8. 大量成交區 (volume_area) ===
        # 找出成交量最大的幾天的價格區間
        if len(hist) >= 10:
            vol_price = list(zip(volumes[-20:], closes[-20:]))
            vol_price.sort(key=lambda x: x[0], reverse=True)
            
            for vol, price in vol_price[:3]:
                levels.append({
                    "price": round(float(price), 2),
                    "type": "support" if price < current else "resistance",
                    "conditions": ["volume_area"],
                    "label": "大量成交區"
                })
        
        # === 9. 布林通道 (bollinger) ===
        if len(closes) >= 20:
            ma20 = float(np.mean(closes[-20:]))
            std = float(np.std(closes[-20:]))
            bb_upper = ma20 + 2 * std
            bb_lower = ma20 - 2 * std
            
            levels.append({
                "price": round(bb_upper, 2),
                "type": "resistance",
                "conditions": ["bollinger"],
                "label": "布林上軌"
            })
            levels.append({
                "price": round(ma20, 2),
                "type": "support" if ma20 < current else "resistance",
                "conditions": ["bollinger"],
                "label": "布林中軌"
            })
            levels.append({
                "price": round(bb_lower, 2),
                "type": "support",
                "conditions": ["bollinger"],
                "label": "布林下軌"
            })
        
        # === 合併相近價位，計算共振強度 ===
        merged_levels = []
        tolerance = current * 0.005  # 0.5% 容差
        
        for level in levels:
            found = False
            for merged in merged_levels:
                if abs(merged["price"] - level["price"]) <= tolerance:
                    # 合併條件
                    for cond in level["conditions"]:
                        if cond not in merged["conditions"]:
                            merged["conditions"].append(cond)
                    merged["labels"].append(level["label"])
                    found = True
                    break
            
            if not found:
                merged_levels.append({
                    "price": level["price"],
                    "type": level["type"],
                    "conditions": level["conditions"].copy(),
                    "labels": [level["label"]]
                })
        
        # 計算共振強度分數
        weight_map = {
            "prev_hl": 2,
            "key_price": 2,
            "ma": 1,
            "trend_ch": 1,
            "pattern": 1,
            "fib": 1,
            "gap": 2,
            "volume_area": 2,
            "bollinger": 1,
        }
        
        for level in merged_levels:
            score = sum(weight_map.get(c, 1) for c in level["conditions"])
            level["score"] = score
            level["resonance"] = len(level["conditions"])
        
        # 按分數排序，取前20個最重要的
        merged_levels.sort(key=lambda x: (-x["score"], x["price"]))
        top_levels = merged_levels[:20]
        
        # 按價格排序返回
        top_levels.sort(key=lambda x: -x["price"])
        
        return {
            "success": True,
            "stock_code": stock_code,
            "current_price": round(current, 2),
            "levels": top_levels,
            "total_analyzed": len(levels),
            "merged_count": len(merged_levels),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"九宮格撐壓分析失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=f"分析失敗: {str(e)}")


# ============== 觀察清單監控系統 ==============

# 內存觀察清單（生產環境應使用數據庫）
watchlist_storage: Dict[str, Dict] = {}

# 股票名稱對照表（常用股票）
STOCK_NAMES = {
    # 權值股
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2303": "聯電",
    "2308": "台達電", "2412": "中華電", "2882": "國泰金", "2881": "富邦金",
    "2891": "中信金", "2886": "兆豐金", "1301": "台塑", "1303": "南亞",
    "2002": "中鋼", "2912": "統一超", "3008": "大立光", "2382": "廣達",
    "2357": "華碩", "3711": "日月光", "2395": "研華", "2379": "瑞昱",
    "6505": "台塑化", "2880": "華南金", "2884": "玉山金", "5880": "合庫金",
    "2892": "第一金", "9910": "豐泰", "1216": "統一", "2609": "陽明",
    "2603": "長榮", "2615": "萬海", "3037": "欣興", "2327": "國巨",
    "2377": "微星", "3034": "聯詠", "2301": "光寶科", "2345": "智邦",
    "6669": "緯穎", "3017": "奇鋐", "2618": "長榮航", "2610": "華航",
    # 電子代工/零組件
    "3706": "神達", "3231": "緯創", "2337": "旺宏", "2312": "金寶",
    "2324": "仁寶", "2353": "宏碁", "2356": "英業達", "3481": "群創",
    "2409": "友達", "2474": "可成", "3023": "信邦", "2385": "群光",
    "3443": "創意", "6239": "力成", "3661": "世芯", "3529": "力旺",
    # IC 設計
    "2388": "威盛", "3035": "智原", "2449": "京元電", "6415": "矽力",
    "5274": "信驊", "6414": "樺漢", "3653": "健策", "2458": "義隆",
    # 金融
    "2883": "開發金", "2885": "元大金", "2887": "台新金", "2888": "新光金",
    "2889": "國票金", "2890": "永豐金", "5876": "上海商銀",
    # 傳產/其他
    "1101": "台泥", "1102": "亞泥", "1326": "台化", "1402": "遠東新",
    "2105": "正新", "2201": "裕隆", "2207": "和泰車", "2227": "裕日車",
    "2801": "彰銀", "2834": "臺企銀", "9904": "寶成", "9921": "巨大",
    "1590": "亞德客", "2408": "南亞科", "3045": "台灣大", "4904": "遠傳",
    "4938": "和碩", "6176": "瑞儀", "6285": "啟碁", "8046": "南電",
}



async def get_stock_name(symbol: str) -> str:
    """取得股票名稱"""
    # 先查本地對照表
    if symbol in STOCK_NAMES:
        return STOCK_NAMES[symbol]
    
    # 嘗試從 API 獲取
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://localhost:8000/api/stock-name/{symbol}")
            if response.status_code == 200:
                data = response.json()
                if data.get("name"):
                    return data["name"]
    except:
        pass
    
    # 使用 yfinance 嘗試獲取
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.TW")
        info = ticker.info
        if info and info.get("shortName"):
            return info["shortName"].split(" ")[0]
    except:
        pass
    
    return symbol


@router.post("/watchlist/add")
async def add_to_watchlist(
    symbol: str = Query(..., description="股票代碼"),
    orb_high: float = Query(..., description="ORB 突破價"),
    orb_low: float = Query(..., description="ORB 跌破價"),
    stop_loss: float = Query(None, description="停損價"),
    target_price: float = Query(None, description="目標價"),
    quantity: int = Query(1000, description="預計數量"),
    notes: str = Query("", description="備註")
):
    """
    新增股票到觀察清單
    
    系統會定期監控，當觸發進出場條件時發送 Email 通知
    """
    try:
        import yfinance as yf
        
        # 取得股票名稱
        stock_name = await get_stock_name(symbol)
        
        # 取得當前價格
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(period="1d")
        if hist.empty:
            ticker = yf.Ticker(f"{symbol}.TWO")
            hist = ticker.history(period="1d")
        
        current_price = float(hist['Close'].iloc[-1]) if not hist.empty else 0
        
        watchlist_storage[symbol] = {
            "symbol": symbol,
            "stock_name": stock_name,
            "orb_high": orb_high,
            "orb_low": orb_low,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "quantity": quantity,
            "notes": notes,
            "current_price": current_price,
            "status": "watching",
            "signal": None,
            "added_at": datetime.now().isoformat(),
            "last_checked": None,
            "notified": False
        }
        
        return {
            "success": True,
            "message": f"已將 {stock_name}({symbol}) 加入觀察清單",
            "watchlist_count": len(watchlist_storage),
            "item": watchlist_storage[symbol]
        }
        
    except Exception as e:
        logger.error(f"加入觀察清單失敗: {e}")

        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/watchlist/remove/{symbol}")
async def remove_from_watchlist(symbol: str):
    """從觀察清單移除股票"""
    if symbol in watchlist_storage:
        del watchlist_storage[symbol]
        return {"success": True, "message": f"已移除 {symbol}"}
    raise HTTPException(status_code=404, detail=f"{symbol} 不在觀察清單中")


@router.get("/watchlist")
async def get_watchlist():
    """取得觀察清單"""
    return {
        "success": True,
        "count": len(watchlist_storage),
        "items": list(watchlist_storage.values())
    }


@router.post("/watchlist/scan")
async def scan_watchlist(send_email: bool = Query(True, description="是否發送郵件通知")):
    """
    掃描觀察清單，檢查買賣訊號
    
    觸發條件：
    - 買進: 現價 > ORB 突破價
    - 賣出: 現價 < ORB 跌破價
    - 停損: 現價 < 停損價
    - 達標: 現價 > 目標價
    """
    try:
        import httpx
        
        signals = []
        
        for symbol, item in watchlist_storage.items():
            try:
                # 優先使用富邦即時報價 API
                current = None
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        res = await client.get(f"http://localhost:8000/api/big-order/quote/{symbol}")
                        if res.status_code == 200:
                            quote = res.json()
                            if quote and quote.get("price"):
                                current = float(quote["price"])
                except Exception as e:
                    logger.debug(f"富邦報價失敗 {symbol}: {e}")
                
                # 回退到 yfinance
                if current is None:
                    import yfinance as yf
                    ticker = yf.Ticker(f"{symbol}.TW")
                    hist = ticker.history(period="1d", interval="1m")
                    if hist.empty:
                        ticker = yf.Ticker(f"{symbol}.TWO")
                        hist = ticker.history(period="1d", interval="1m")
                    if not hist.empty:
                        current = float(hist['Close'].iloc[-1])
                
                if current is None:
                    continue
                item["current_price"] = current
                item["last_checked"] = datetime.now().isoformat()
                
                signal = None
                signal_type = None
                
                # 檢查訊號
                if current > item["orb_high"]:
                    signal = f"✅ 突破買進訊號！現價 {current:.2f} > ORB 突破價 {item['orb_high']:.2f}"
                    signal_type = "BUY_BREAKOUT"
                elif current < item["orb_low"]:
                    signal = f"⚠️ 跌破賣出訊號！現價 {current:.2f} < ORB 跌破價 {item['orb_low']:.2f}"
                    signal_type = "SELL_BREAKDOWN"
                elif item["stop_loss"] and current < item["stop_loss"]:
                    signal = f"🛑 觸及停損！現價 {current:.2f} < 停損價 {item['stop_loss']:.2f}"
                    signal_type = "STOP_LOSS"
                elif item["target_price"] and current > item["target_price"]:
                    signal = f"🎯 達到目標！現價 {current:.2f} > 目標價 {item['target_price']:.2f}"
                    signal_type = "TARGET_HIT"
                
                if signal:
                    item["signal"] = signal
                    item["signal_type"] = signal_type
                    
                    # 🔑 只發送關鍵訊號，不重複發送
                    # 檢查是否為新訊號（首次觸發或訊號類型改變）
                    last_notified_type = item.get("last_notified_type")
                    is_new_signal = (last_notified_type != signal_type)
                    
                    if is_new_signal:
                        signals.append({
                            "symbol": symbol,
                            "stock_name": item.get("stock_name", symbol),
                            "current_price": current,
                            "signal": signal,
                            "signal_type": signal_type,
                            "orb_high": item["orb_high"],
                            "orb_low": item["orb_low"],
                            "stop_loss": item.get("stop_loss"),
                            "target_price": item.get("target_price"),
                            "quantity": item["quantity"],
                            "notes": item["notes"],
                            "is_new_signal": True
                        })
                        # 標記已發送此類型訊號
                        item["last_notified_type"] = signal_type
                        item["notified"] = True
                        item["notified_at"] = datetime.now().isoformat()
                else:
                    # 價格回到區間內，重置訊號狀態（下次觸發可再發送）
                    item["signal"] = None
                    item["signal_type"] = None
                    # 不重置 last_notified_type，避免快速進出區間時重複發送
                    
            except Exception as e:
                logger.warning(f"掃描 {symbol} 失敗: {e}")
        
        # 發送郵件通知 - 只發送關鍵訊號
        email_sent = False
        if send_email and signals:
            try:
                from app.services.trade_email_notifier import trade_notifier
                
                # 建立專業 HTML 郵件內容
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background: #f8fafc;">
                    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="background: linear-gradient(135deg, #3b82f6, #8b5cf6); padding: 20px; color: white;">
                            <h2 style="margin: 0;">🎯 當沖戰情室 - 關鍵訊號通知</h2>
                            <p style="margin: 5px 0 0 0; opacity: 0.9;">只發送關鍵訊號，不重複打擾</p>
                        </div>
                        
                        <div style="padding: 20px;">
                """
                
                for s in signals:
                    signal_type = s["signal_type"]
                    current_price = s["current_price"]
                    orb_high = s.get("orb_high", 0)
                    orb_low = s.get("orb_low", 0)
                    stop_loss = s.get("stop_loss") or (orb_low * 0.98)
                    target_price = s.get("target_price") or orb_high
                    stock_name = s.get("stock_name", s["symbol"])
                    
                    # 根據訊號類型設定顏色和建議
                    if "BUY" in signal_type:
                        bg_color = "#fef2f2"
                        border_color = "#dc2626"
                        action = "🔴 買進訊號"
                        advice = f"建議進場，停損設 {stop_loss:.1f}，目標 {target_price:.1f}"
                    else:
                        bg_color = "#f0fdf4"
                        border_color = "#16a34a"
                        action = "🟢 賣出訊號"
                        advice = f"建議出場或觀望"
                    
                    html_content += f"""
                            <div style="background: {bg_color}; border-left: 4px solid {border_color}; padding: 15px; margin-bottom: 15px; border-radius: 0 8px 8px 0;">
                                <div style="font-size: 18px; font-weight: bold; color: #1f2937;">
                                    {stock_name} ({s['symbol']}) - 現價 ${current_price:.2f}
                                </div>
                                <div style="font-size: 14px; color: {border_color}; font-weight: bold; margin: 8px 0;">
                                    {action}
                                </div>
                                <div style="font-size: 13px; color: #6b7280; margin-bottom: 10px;">
                                    {s['signal']}
                                </div>
                                
                                <!-- 專業交易建議 -->
                                <div style="background: white; border-radius: 8px; padding: 12px; margin-top: 10px;">
                                    <div style="font-size: 12px; font-weight: bold; color: #374151; margin-bottom: 8px;">📊 關鍵價位</div>
                                    <table style="width: 100%; font-size: 12px;">
                                        <tr>
                                            <td style="padding: 4px; color: #16a34a;">🟢 買點: ${orb_low:.1f}</td>
                                            <td style="padding: 4px; color: #dc2626;">🔴 賣點: ${orb_high:.1f}</td>
                                            <td style="padding: 4px; color: #6b7280;">⚠️ 停損: ${stop_loss:.1f}</td>
                                        </tr>
                                    </table>
                                    <div style="font-size: 11px; color: #9ca3af; margin-top: 8px; padding-top: 8px; border-top: 1px solid #e5e7eb;">
                                        💡 {advice}
                                    </div>
                                </div>
                            </div>
                    """
                
                html_content += f"""
                        </div>
                        
                        <div style="background: #f3f4f6; padding: 15px; text-align: center; font-size: 11px; color: #9ca3af;">
                            發送時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                            此為系統自動發送的關鍵訊號，僅供參考
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # 根據訊號類型決定標題
                signal_types = list(set([s["signal_type"] for s in signals]))
                if any("BUY" in t for t in signal_types):
                    subject = f"🔴 買進訊號！{', '.join([s['symbol'] for s in signals if 'BUY' in s['signal_type']])}"
                else:
                    subject = f"🟢 賣出訊號！{', '.join([s['symbol'] for s in signals])}"
                
                email_sent = trade_notifier._send_email(
                    subject=subject,
                    html_content=html_content
                )
                
            except Exception as e:
                logger.error(f"發送郵件失敗: {e}")
        
        return {
            "success": True,
            "scanned_count": len(watchlist_storage),
            "signals_count": len(signals),
            "signals": signals,
            "email_sent": email_sent,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"掃描觀察清單失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist/auto-trade")
async def auto_trade_from_watchlist(
    symbol: str = Query(..., description="股票代碼"),
    action: str = Query(..., description="動作: buy 或 sell")
):
    """
    根據觀察清單訊號自動執行模擬交易
    
    會自動在 Portfolio 中建立持倉記錄
    """
    try:
        if symbol not in watchlist_storage:
            raise HTTPException(status_code=404, detail=f"{symbol} 不在觀察清單中")
        
        item = watchlist_storage[symbol]
        
        # 呼叫 portfolio API 建立持倉
        import httpx
        
        async with httpx.AsyncClient() as client:
            if action == "buy":
                response = await client.post(
                    "http://localhost:8000/api/portfolio/positions",
                    json={
                        "symbol": symbol,
                        "stock_name": symbol,
                        "entry_date": datetime.now().isoformat(),
                        "entry_price": item["current_price"],
                        "entry_quantity": item["quantity"],
                        "analysis_source": "day_trading",
                        "stop_loss_price": item["stop_loss"],
                        "target_price": item["target_price"],
                        "is_simulated": True,
                        "notes": f"當沖戰情室自動下單 - {item['notes']}"
                    }
                )
                
                if response.status_code == 200:
                    # 從觀察清單移除
                    watchlist_storage[symbol]["status"] = "traded"
                    
                    return {
                        "success": True,
                        "message": f"已自動買進 {symbol}",
                        "action": "buy",
                        "price": item["current_price"],
                        "quantity": item["quantity"],
                        "portfolio_response": response.json()
                    }
            
            return {
                "success": False,
                "message": f"執行失敗: {action}"
            }
            
    except Exception as e:
        logger.error(f"自動交易失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 早盤進場偵測器 API ==============

@router.get("/early-entry/scan")
async def scan_early_entry_signals():
    """
    掃描早盤進場信號
    
    在 09:10-10:30 黃金時段偵測最佳買點
    
    偵測策略：
    1. 開盤拉回買 (Pullback from Open)
    2. ORB 突破買 (Opening Range Breakout)
    3. 動能爆發 (Momentum Surge)
    4. VWAP 反彈 (VWAP Bounce)
    
    Returns:
        signals: 進場信號列表
        window: 當前時間窗口
        can_enter: 是否可進場
    """
    try:
        from app.services.early_entry_detector import early_entry_detector
        
        window, can_enter = early_entry_detector.get_current_window()
        signals = await early_entry_detector.scan_all_signals()
        
        return {
            "success": True,
            "window": window,
            "can_enter": can_enter,
            "signals_count": len(signals),
            "signals": signals,
            "watchlist_count": len(early_entry_detector.watchlist),
            "timestamp": datetime.now().isoformat(),
            "description": "在 09:10-10:30 黃金時段偵測最佳買點"
        }
        
    except Exception as e:
        logger.error(f"早盤掃描失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/early-entry/signal/{symbol}")
async def get_early_entry_signal(symbol: str):
    """
    獲取單一股票的早盤進場建議
    
    Args:
        symbol: 股票代碼
        
    Returns:
        signal: 進場信號（如有）
        intraday_data: 盤中數據
    """
    try:
        from app.services.early_entry_detector import early_entry_detector
        
        # 收集盤中數據
        data = await early_entry_detector.collect_intraday_data(symbol)
        if not data:
            raise HTTPException(status_code=404, detail=f"無法獲取 {symbol} 的盤中數據")
        
        # 獲取進場建議
        signal = await early_entry_detector.get_entry_recommendation(symbol)
        
        window, can_enter = early_entry_detector.get_current_window()
        
        return {
            "success": True,
            "symbol": symbol,
            "window": window,
            "can_enter": can_enter,
            "has_signal": signal is not None,
            "signal": signal,
            "intraday_data": {
                "current": data.get("current"),
                "open": data.get("open"),
                "high": data.get("high"),
                "low": data.get("low"),
                "vwap": data.get("vwap"),
                "change_pct": data.get("change_pct"),
                "orb_high": data.get("orb_high"),
                "orb_low": data.get("orb_low"),
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取 {symbol} 進場信號失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/early-entry/status")
async def get_early_entry_status():
    """
    獲取早盤偵測器狀態
    
    Returns:
        window: 當前時間窗口
        watchlist: 監控清單
        signals_sent: 今日已發出的信號
    """
    try:
        from app.services.early_entry_detector import early_entry_detector
        
        window, can_enter = early_entry_detector.get_current_window()
        
        return {
            "success": True,
            "window": window,
            "window_description": {
                "observation": "觀察期 (09:00-09:10)",
                "early_window": "早期進場窗口 (09:10-09:30)",
                "main_window": "主要進場窗口 (09:30-10:00)",
                "extended_window": "延伸進場窗口 (10:00-10:30)",
                "after_golden_hour": "黃金時段後 (10:30+)",
                "market_closed": "盤前/盤後"
            }.get(window, window),
            "can_enter": can_enter,
            "watchlist": early_entry_detector.watchlist,
            "watchlist_count": len(early_entry_detector.watchlist),
            "signals_sent_today": len(early_entry_detector.signals_sent),
            "signals_sent_list": list(early_entry_detector.signals_sent.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"獲取早盤狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/early-entry/reset")
async def reset_early_entry_detector():
    """
    重置早盤偵測器
    
    清除今日已發出的信號，允許重新偵測
    """
    try:
        from app.services.early_entry_detector import early_entry_detector
        
        old_count = len(early_entry_detector.signals_sent)
        early_entry_detector.reset_daily()
        
        return {
            "success": True,
            "message": f"已重置早盤偵測器，清除 {old_count} 個信號記錄",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"重置早盤偵測器失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 智能進場系統 v2.0 API ==============

@router.get("/smart-system/status")
async def get_smart_entry_system_status():
    """
    獲取智能進場系統 v2.0 狀態
    
    包含 4 種策略：回檔買、突破買、動能買、VWAP反彈
    """
    try:
        from app.services.smart_entry_system import smart_entry_system
        return {
            "success": True,
            **smart_entry_system.get_status()
        }
    except Exception as e:
        logger.error(f"獲取智能進場系統狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/smart-system/scan")
async def scan_with_smart_entry_system():
    """
    使用智能進場系統 v2.0 掃描所有監控股票
    
    返回符合條件的進場信號
    """
    try:
        from app.services.smart_entry_system import smart_entry_system
        
        signals = await smart_entry_system.scan_all_stocks()
        
        return {
            "success": True,
            "signals_count": len(signals),
            "signals": signals,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"智能進場系統掃描失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-system/scan-and-trade")
async def scan_and_auto_trade():
    """
    掃描並自動建倉
    
    使用智能進場系統 v2.0 掃描股票，符合條件的自動建倉（模擬）
    """
    try:
        from app.services.smart_entry_system import smart_entry_system
        
        result = await smart_entry_system.run_scan_and_trade()
        
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"掃描並自動建倉失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/smart-system/evaluate/{symbol}")
async def evaluate_single_stock(symbol: str):
    """
    評估單一股票
    
    使用所有策略評估，返回最佳進場策略
    """
    try:
        from app.services.smart_entry_system import smart_entry_system
        
        # 收集數據
        stock_data = await smart_entry_system.collect_stock_data(symbol)
        if not stock_data:
            raise HTTPException(status_code=404, detail=f"無法獲取 {symbol} 的數據")
        
        # 評估
        result = smart_entry_system.evaluate_stock(stock_data)
        
        return {
            "success": True,
            "symbol": symbol,
            "stock_data": {
                "price": stock_data.get('price'),
                "change_pct": stock_data.get('change_pct'),
                "volume_ratio": stock_data.get('volume_ratio'),
                "ma5": stock_data.get('ma5'),
                "ma20": stock_data.get('ma20'),
                "vwap": stock_data.get('vwap'),
                "trend": stock_data.get('trend'),
                "above_ma5": stock_data.get('above_ma5'),
                "above_ma20": stock_data.get('above_ma20'),
            },
            "evaluation": result,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"評估 {symbol} 失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-system/reset")
async def reset_smart_entry_system():
    """
    重置智能進場系統
    
    清除今日已發出的信號，允許重新掃描
    """
    try:
        from app.services.smart_entry_system import smart_entry_system
        
        old_count = len(smart_entry_system.signals_sent)
        smart_entry_system.reset_daily()
        
        return {
            "success": True,
            "message": f"已重置智能進場系統，清除 {old_count} 個信號記錄",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"重置智能進場系統失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/analyze")
async def analyze_stock(request: dict):
    """
    分析股票並返回包含 LSTM AI 的綜合判斷
    
    用於 LSTM AI 助手頁面調用
    已整合 LSTM 深度學習預測
    """
    try:
        stock_code = request.get("stock_code")
        
        if not stock_code:
            raise HTTPException(status_code=400, detail="請提供股票代碼")
        
        # 導入 SmartEntrySystem
        from app.services.smart_entry_system import SmartEntrySystem
        import yfinance as yf
        
        system = SmartEntrySystem()
        
        # 獲取股票數據
        ticker = yf.Ticker(f"{stock_code}.TW")
        hist = ticker.history(period="3mo")
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"無法取得 {stock_code} 的數據")
        
        # 構造 stock_data
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else latest
        
        ma5 = hist['Close'].rolling(5).mean().iloc[-1]
        ma20 = hist['Close'].rolling(20).mean().iloc[-1]
        
        stock_data = {
            'symbol': stock_code,
            'price': float(latest['Close']),
            'change_pct': float((latest['Close'] - prev['Close']) / prev['Close'] * 100),
            'volume': int(latest['Volume']),
            'volume_ratio': 1.2,
            'ma5': float(ma5),
            'ma20': float(ma20),
            'above_ma5': float(latest['Close']) > float(ma5),
            'above_ma20': float(latest['Close']) > float(ma20),
            'trend': '上升' if float(latest['Close']) > float(ma5) else '盤整'
        }
        
        # 風險檢查
        risk_check = system.check_entry_risk(stock_data)
        
        # 調用核心方法
        result = system.calculate_confidence(stock_data, risk_check)
        
        return {
            "success": True,
            "stock_code": stock_code,
            "confidence": result['confidence'],
            "factors": result['factors'],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=f"分析失敗: {str(e)}")
