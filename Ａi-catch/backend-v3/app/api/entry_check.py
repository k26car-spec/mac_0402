"""
AI 多因子進場檢查系統 (Multi-Factor Entry Check System) - 優化版 V6 (Live Fubon Integration)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, time as dt_time, timedelta
import asyncio
import logging

from app.services.fubon_service import get_realtime_quote
from app.services.live_indicator_service import get_live_indicators, get_projected_volume_ratio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/entry-check", tags=["Multi-Factor Entry Check"])

_api_cache = {}      # 子 API 快取 (10s)

class BatchDetailsRequest(BaseModel):
    symbols: List[str]

def safe_json(obj):
    """將 numpy 類型轉換為原生 Python 類型，並處理 NaN/Inf，確保 JSON 序列化成功"""
    import numpy as np
    import math
    if isinstance(obj, dict):
        return {k: safe_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json(x) for x in obj]
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, (float, np.floating)):
        # ⚠️ 關鍵修正：處理 NaN 和 Inf，避免 JSON 序列化失敗
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return val
    elif isinstance(obj, np.ndarray):
        return safe_json(obj.tolist())
    else:
        return obj

def calculate_confidence_v3(checks: dict, sniper_signals: dict, risk_check: dict) -> dict:
    """v3 嚴格版信心度：一眼定多空、理性避險、精準打擊 (含市場時段戰術)"""
    confidence = 60  # 起始基礎分
    details = []
    
    # 提取數據
    price_change = risk_check.get("change_pct", 0)
    vol_ratio = risk_check.get("volume_ratio", 1.0)
    vwap_control = sniper_signals.get("vwap_control", "NEUTRAL")
    vwap = sniper_signals.get("vwap", 0)
    entry_price = risk_check.get("entry_price", checks.get("support_resistance", {}).get("current_price", 0))
    is_divergence = sniper_signals.get("is_divergence", False)
    is_precision_strike = sniper_signals.get("is_precision_strike", False)
    
    # 計算 VWAP 乖離
    vwap_deviation = round((entry_price - vwap) / vwap * 100, 2) if vwap > 0 else 0

    # 時段判斷
    now = datetime.now()
    is_opening = now.hour == 9 and now.minute <= 15
    is_cooling = (now.hour == 10 and now.minute >= 30) or (now.hour == 11) or (now.hour == 12 and now.minute == 0)
    is_closing = now.hour == 13 and now.minute <= 30

    # --- 🌌 特殊狀態：爆量攻擊 (開盤衝刺) ---
    if is_opening and vol_ratio > 2.0 and vwap_control == "LONG":
        details.append("⚡ 爆量攻擊：開盤多方極強勢")
        return {
            "score": 95, 
            "details": details, 
            "status": "PURPLE_LIGHT",
            "threshold": 70,
            "vwap_deviation": vwap_deviation
        }

    # --- 🛑 理性避險 (紅燈攔截核心) ---
    # 條件 1：價量背離 (無量虛漲)
    # 盤中冷卻期 (10:30-12:00) 強化攔截：若量能降至 0.8 以下
    vol_threshold = 0.8 if not is_cooling else 0.85
    is_volume_divergence = price_change > 2.0 and vol_ratio < vol_threshold
    
    # 條件 2：弱勢誘多
    is_weak_rebound = price_change > 1.5 and vwap_control == "SHORT"
    
    # 條件 3：乖離過大
    is_overextended = vwap_deviation > 5.0
    
    if is_volume_divergence or is_weak_rebound or is_divergence or is_overextended:
        reason = ""
        if is_volume_divergence: reason = "價量背離 (無量虛漲)"
        elif is_weak_rebound: reason = "弱勢誘多 (VWAP之下)"
        elif is_overextended: reason = f"乖離過大 ({vwap_deviation}%)"
        else: reason = "指標背離/高位過熱"
        
        details.append(f"🛑 紅燈攔截：{reason}")
        return {
            "score": 10, 
            "details": details, 
            "status": "RED_LIGHT",
            "threshold": 75,
            "vwap_deviation": vwap_deviation
        }

    # --- 1. 一般權重 ---
    if vwap_control == "SHORT":
        confidence -= 35
        details.append("❌ 處於 VWAP 之下 (空方) -35")
    elif vwap_control == "LONG":
        confidence += 15
        details.append("✅ 處於 VWAP 之上 (多方) +15")
        if vol_ratio > 1.2:
            confidence += 15
            details.append("👤 攻擊量能確認 +15")

    # --- 3. 精準打擊 (綠燈) ---
    if is_precision_strike:
        # 尾盤定價期 (13:00-13:30) 綠燈強化
        if is_closing:
            confidence = 92
            details.append("🎯 尾盤確認：支撐守穩且量增")
        elif vol_ratio > 1.0:
            confidence = 90
            details.append("🎯 綠燈：帶量回測支撐")
        else:
            confidence = 80
            details.append("🎯 支撐回測 (量能待補)")

    # 最終校準
    confidence = min(100, max(0, confidence))
    status = "GREEN_LIGHT" if confidence >= 85 and vol_ratio >= 1.0 else "NEUTRAL"
    if confidence < 60: status = "WAIT_AND_SEE"

    return {
        "score": confidence, 
        "details": details, 
        "status": status, 
        "threshold": 75 if not is_precision_strike else 70,
        "vwap_deviation": vwap_deviation
    }

@router.get("/comprehensive/{symbol}")
async def comprehensive_entry_check(
    symbol: str,
    entry_price: float = Query(..., description="預計進場價"),
    signal_source: str = Query("manual", description="訊號來源"),
    analysis_data: Optional[dict] = None
):
    cache_key = f"comp_{symbol}"
    if not analysis_data and cache_key in _api_cache:
        data, ts = _api_cache[cache_key]
        if (datetime.now() - ts).total_seconds() < 5: # 盤中縮短快取時間
            data["entry_price"] = entry_price
            return data

    result = {
        "symbol": symbol, "name": symbol, "entry_price": entry_price, "timestamp": datetime.now().isoformat(),
        "checks": {}, "passed_count": 0, "total_checks": 6, "warnings": [], "blockers": [],
        "should_enter": False, "confidence": 0, "recommended_action": "", "sniper_signals": {}
    }
    
    from app.services.stock_comprehensive_analyzer import analyze_stock_comprehensive, get_stock_name
    from app.api.smart_entry import get_entry_score
    from app.api.support_resistance import analyze_support_resistance
    from app.api.trade_review import should_trade
    
    result["name"] = get_stock_name(symbol)
    
    try:
        # 並行執行：1. 基礎分析, 2. 即時指標 (VWAP/KD), 3. 其他特化任務
        tasks = [
            analyze_stock_comprehensive(symbol, quick_mode=True) if not analysis_data else asyncio.sleep(0, result=analysis_data),
            get_live_indicators(symbol),
            get_entry_score(symbol),
            should_trade(symbol, signal_source, entry_price),
            analyze_support_resistance(symbol)
        ]
        
        try:
            # 增加超時時間以減少超時錯誤 (從 6 秒調整為 10 秒)
            done_results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=10.0)
            main_analysis, live_indicators, scores_res, lesson_res, sr_res = done_results
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ 分析超時 {symbol} (已等待 10 秒)")
            main_analysis, live_indicators, scores_res, lesson_res, sr_res = analysis_data or {}, {}, {}, {}, {}

        # 確保結果是 dict
        if isinstance(main_analysis, Exception): main_analysis = {}
        if isinstance(live_indicators, Exception): live_indicators = {}
        if isinstance(scores_res, Exception): scores_res = {}
        if isinstance(lesson_res, Exception): lesson_res = {}
        if isinstance(sr_res, Exception): sr_res = {}

        ti_hist = main_analysis.get("technical_indicators") or {}
        inst = main_analysis.get("institutional_trading") or {}
        
        # 1. 整理指標 (優先使用 Live 數據)
        vwap = live_indicators.get("vwap", 0)
        # 如果 Live VWAP 無法計算，回退到主分析器或 SR 分析
        if vwap <= 0:
            if isinstance(sr_res, dict) and sr_res.get("data"):
                vwap = sr_res["data"].get("vwap", 0)
        
        kd_k = live_indicators.get("kd_k", ti_hist.get("kd_k", 50))
        kd_d = live_indicators.get("kd_d", ti_hist.get("kd_d", 50))
        
        # 2. 填充 checks
        # (A) 智慧評分 (ORB)
        score = scores_res.get("score", main_analysis.get("overall_score", 60))
        result["checks"]["smart_score"] = {"score": score, "passed": score >= 65}
        
        # (B) 技術面 (結合 Live 趨勢)
        current_price = live_indicators.get("current_price", entry_price)
        trend = ti_hist.get("trend", "盤整")
        passed_tech = any(w in trend for w in ["上", "強", "多"]) or (vwap > 0 and current_price > vwap)
        result["checks"]["technical"] = {"trend": trend, "passed": passed_tech, "kd_k": kd_k}
        
        # (C) 法人 (依賴歷史)
        total_net = inst.get("total_net", 0)
        result["checks"]["institutional"] = {"total_net": total_net, "passed": total_net > 0}
        
        # (D) 撐壓 (VWAP 控制)
        result["checks"]["support_resistance"] = {"passed": entry_price >= vwap * 0.995 if vwap > 0 else True, "vwap": vwap}
        
        # (E) 教訓
        result["checks"]["lessons"] = {"passed": lesson_res.get("should_trade", True)}
        
        # (F) 風險 (漲幅 & 預估量比)
        change_pct = ti_hist.get("change_pct", 0)
        # 如果 Live 有最新價，重新計算漲幅
        if live_indicators.get("current_price") and ti_hist.get("previous_close"):
            change_pct = round((live_indicators["current_price"] - ti_hist["previous_close"]) / ti_hist["previous_close"] * 100, 2)
            
        # 計算預估量比
        yesterday_vol = ti_hist.get("volume", 0) # ti_hist 的 volume 通常是最近一天的
        # 如果是盤中，ti_hist 拿到的 volume 可能是昨天的，也可能是今天目前累積的，視 analyzer 實現而定
        # 但為了保險，我們從昨日法人或歷史資料找更準確的昨日量
        if "avg_volume_20" in ti_hist:
             # 如果沒有明確的昨日量，用 20 日均量作為基準也是一種參考，但最好是昨日量
             pass
             
        vol_ratio = get_projected_volume_ratio(live_indicators.get("current_volume", 0), yesterday_vol)
        result["checks"]["risk"] = {"change_pct": change_pct, "volume_ratio": vol_ratio, "passed": True}
        
        # 3. Sniper V3 邏輯
        vwap_signal = "NEUTRAL"
        if vwap > 0:
            vwap_signal = "LONG" if entry_price > vwap else "SHORT"
            
        is_divergence = change_pct > 4 and kd_k > 80
        is_precision = abs(entry_price/vwap - 1) < 0.015 and 20 < kd_k < 50 if vwap > 0 else False
        
        # 4. 🔥 增強：整合 三重防線 (Dip Analysis) - 採用富邦原汁原味 API 數據
        try:
            from app.services.dip_analyzer import get_dip_analysis
            from fubon_client import fubon_client
            
            # 獲取歷史 K 線
            hist_df = main_analysis.get("df") 
            
            # --- 專業版指標獲取 ---
            ofi = 0
            bid_ask_ratio = 1.0
            
            # (A) 獲取五檔掛單比
            try:
                orderbook = await fubon_client.get_orderbook(symbol)
                if orderbook:
                    total_bid = orderbook.get("totalBidVolume", 1)
                    total_ask = orderbook.get("totalAskVolume", 1)
                    if total_ask > 0:
                        bid_ask_ratio = total_bid / total_ask
                    logger.debug(f"DipData {symbol}: Bid/Ask Ratio = {bid_ask_ratio:.2f}")
            except Exception as obe:
                logger.debug(f"Failed to get orderbook for dip: {obe}")
                
            # (B) 獲取成交明細計算 OFI (Order Flow Imbalance)
            try:
                trades = []
                # 優先使用 Streamer 快取的最近成交
                if fubon_client.streamer and symbol in fubon_client.streamer.trades:
                    trades = fubon_client.streamer.trades[symbol]
                else:
                    # 否則主動連線抓取一波
                    trades = await fubon_client.get_trades(symbol, count=40)
                
                if trades:
                    buy_vol = sum(t.get('volume', 0) for t in trades if t.get('side') == 'buy')
                    sell_vol = sum(t.get('volume', 0) for t in trades if t.get('side') == 'sell')
                    ofi = buy_vol - sell_vol
                    logger.debug(f"DipData {symbol}: OFI = {ofi:+.0f} (B:{buy_vol}|S:{sell_vol})")
            except Exception as te:
                logger.debug(f"Failed to get trades for dip: {te}")

            # 備援：如果 scores_res 有 ofi 則參考之
            if ofi == 0 and isinstance(scores_res, dict):
                 ofi = scores_res.get("ofi", 0)

            dip_res = await get_dip_analysis(symbol, hist_df, current_price, ofi=ofi, ratio=bid_ask_ratio)
            if dip_res:
                result["checks"]["dip_analysis"] = {
                    "quality": dip_res.quality.value,
                    "score": dip_res.score,
                    "confidence": dip_res.confidence,
                    "reasons": dip_res.reasons,
                    "warnings": dip_res.warnings,
                    "stop_loss_price": dip_res.stop_loss_price,
                    "target_price": dip_res.target_price,
                    "ofi": ofi,
                    "bid_ask_ratio": round(bid_ask_ratio, 2)
                }
        except Exception as e:
            logger.warning(f"Dip analysis failed for {symbol}: {e}")

        result["sniper_signals"] = {
            "vwap_control": vwap_signal, "is_divergence": is_divergence, "is_precision_strike": is_precision,
            "kd_k": kd_k, "vwap": vwap, "status": "NEUTRAL", "kd_d": kd_d
        }

        conf_res = calculate_confidence_v3(result["checks"], result["sniper_signals"], result["checks"]["risk"])
        result["confidence"] = conf_res["score"]
        result["sniper_signals"]["status"] = conf_res["status"]
        
        if conf_res["status"] == "RED_LIGHT":
            result["recommended_action"] = "🛑 理性避險"
            result["should_enter"] = False
        elif conf_res["status"] == "GREEN_LIGHT" or is_precision:
            result["recommended_action"] = "🎯 精準打擊"
            result["should_enter"] = True
        else:
            result["should_enter"] = result["confidence"] >= 75
            result["recommended_action"] = "建議進場" if result["should_enter"] else "觀望"

        _api_cache[cache_key] = (result, datetime.now())
        return safe_json(result)
    except Exception as e:
        logger.error(f"Error in comp check {symbol}: {e}", exc_info=True)
        return safe_json(result)

def safe_json(obj):
    """將 numpy 類型轉換為原生 Python 類型，確保 JSON 序列化成功"""
    import numpy as np
    
    if isinstance(obj, dict):
        return {k: safe_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json(x) for x in obj]
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return safe_json(obj.tolist())
    elif hasattr(obj, 'item') and callable(getattr(obj, 'item')): # 處理其他 numpy 純量
        return obj.item()
    else:
        return obj

@router.get("/quick/{symbol}")
async def quick_entry_check(symbol: str):
    """
    快速檢查 - 優先從富邦抓取最新報價，然後調用綜合分析
    """
    try:
        # 1. 直接抓取富邦即時報價
        quote = await get_realtime_quote(symbol)
        
        # 防呆檢查：確保 quote 不是 None
        if not quote:
            quote = {}
            
        price = quote.get("price", 0)
        
        if price <= 0:
            # 如果連沒價格，可能還沒開盤，回退到普通快速檢查
            from app.services.stock_comprehensive_analyzer import analyze_stock_comprehensive
            main_analysis = await analyze_stock_comprehensive(symbol, quick_mode=True)
            # 防呆：確保 main_analysis 不是 None
            if main_analysis is None:
                main_analysis = {}
            ti = main_analysis.get("technical_indicators") or {}
            price = ti.get("current_price", 0)
            return await comprehensive_entry_check(symbol, price, "quick_fallback", analysis_data=main_analysis)
        
        # 2. 調用綜合分析 (傳入 symbol 和 price)
        # 注意：不傳入 analysis_data，讓 comprehensive_entry_check 自己決定是否要並行抓取
        return await comprehensive_entry_check(symbol, price, "quick_fubon_live")
        
    except Exception as e:
        logger.error(f"Quick check error {symbol}: {e}", exc_info=True)
        from app.services.stock_comprehensive_analyzer import get_stock_name
        return safe_json({"symbol": symbol, "name": get_stock_name(symbol), "recommended_action": "更新中", "sniper_signals": {"status": "NEUTRAL"}})

@router.post("/batch-details")
async def batch_all_details(request: BatchDetailsRequest):
    """超快速批次處理 - 只獲取基本報價，不做複雜分析"""
    symbols = request.symbols[:30]
    
    # 加上快取機制，避免前端 polling 每 3 秒太頻繁造成 Yahoo 封鎖
    from datetime import datetime, timedelta
    cache_key = f"batch_{symbols}"
    if hasattr(router, "_batch_cache"):
        if cache_key in router._batch_cache:
            ts, data = router._batch_cache[cache_key]
            if datetime.now() - ts < timedelta(seconds=10):
                return safe_json({"success": True, "results": data, "cached": True})
    else:
        router._batch_cache = {}

    # 🆕 批次獲取法人籌碼 (從 DB 統一讀取，提高效能)
    from app.services.batch_institutional_service import batch_institutional_service
    # 獲取最近 1 天的法人資料字典 {symbol: total_net}
    inst_data_map = {}
    try:
        # 只取最近一天的，用於即時看板顯示
        inst_records = await batch_institutional_service.get_batch_latest_institutional(symbols)
        for symbol, total_net in inst_records.items():
            inst_data_map[symbol] = total_net
    except Exception as e:
        logger.warning(f"Batch fetch institutional failed: {e}")

    async def get_basic_quote(symbol: str) -> dict:
        """超輕量版：獲取報價並加入資料庫中的法人數據"""
        try:
            from stock_mappings import get_stock_name
            name = get_stock_name(symbol)
        except:
            name = symbol
        
        # 獲取緩存/DB 中的法人數據 (張)
        # 注意：DB 存的是股數，界面通常顯示張數，我們在這裡轉換
        raw_net = inst_data_map.get(symbol, 0)
        total_net_lots = int(raw_net / 1000)
        
        try:
            # 🚀 增加超時時間到 8 秒，因為 Yahoo 備援在大盤關盤或 API 繁忙時可能較慢
            quote = await asyncio.wait_for(get_realtime_quote(symbol), timeout=8.0)
            if quote:
                price = quote.get("price", 0)
                change_pct = quote.get("change_pct", 0)
                volume = quote.get("volume", 0)
                
                # 簡單判斷 status
                status = "NEUTRAL"
                if change_pct > 3:
                    status = "GREEN_LIGHT"
                elif change_pct < -2:
                    status = "RED_LIGHT"
                
                return {
                    "symbol": symbol,
                    "name": name,
                    "entry_price": price,
                    "recommended_action": f"{'漲' if change_pct > 0 else '跌'} {abs(change_pct):.2f}%",
                    "confidence": 60 if status == "NEUTRAL" else (80 if status == "GREEN_LIGHT" else 30),
                    "should_enter": change_pct > 0 and change_pct < 5,
                    "sniper_signals": {
                        "status": status,
                        "vwap": quote.get("vwap", 0),
                        "vwap_deviation": 0
                    },
                    "checks": {
                        "risk": {"change_pct": change_pct, "volume_ratio": 1.0},
                        "institutional": {"total_net": total_net_lots} # ❌ 原本是 0，現在改用真實數據
                    }
                }
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.debug(f"Quote fetch failed for {symbol}: {e}")
        
        # 回退：返回基本結構 (仍包含法人數據)
        return {
            "symbol": symbol,
            "name": name,
            "entry_price": 0,
            "recommended_action": "載入中...",
            "confidence": 50,
            "should_enter": False,
            "sniper_signals": {"status": "NEUTRAL", "vwap": 0, "vwap_deviation": 0},
            "checks": {
                "risk": {"change_pct": 0, "volume_ratio": 1.0},
                "institutional": {"total_net": total_net_lots}
            }
        }
    
    # 全部並行，最多等 20 秒
    try:
        all_results = await asyncio.wait_for(
            asyncio.gather(*[get_basic_quote(s) for s in symbols], return_exceptions=True),
            timeout=20.0
        )
        all_results = [
            r if not isinstance(r, Exception) else {"symbol": symbols[i], "name": symbols[i], "sniper_signals": {"status": "NEUTRAL"}}
            for i, r in enumerate(all_results)
        ]
        
        # 存入快取 (只快取成功結果)
        router._batch_cache[cache_key] = (datetime.now(), all_results)
        all_results = [
            r if not isinstance(r, Exception) else {"symbol": symbols[i], "name": symbols[i], "sniper_signals": {"status": "NEUTRAL"}}
            for i, r in enumerate(all_results)
        ]
    except asyncio.TimeoutError:
        logger.warning("Batch details global timeout")
        try:
            from stock_mappings import get_stock_name
            all_results = [{"symbol": s, "name": get_stock_name(s), "recommended_action": "超時", "sniper_signals": {"status": "NEUTRAL"}} for s in symbols]
        except:
            all_results = [{"symbol": s, "name": s, "recommended_action": "超時", "sniper_signals": {"status": "NEUTRAL"}} for s in symbols]
    
    return safe_json({"success": True, "results": all_results})

@router.get("/batch")
async def batch_entry_check(symbols: str):
    tasks = [quick_entry_check(c.strip()) for c in symbols.split(",") if c.strip()][:10]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return safe_json({"results": [r for r in results if not isinstance(r, Exception)]})
