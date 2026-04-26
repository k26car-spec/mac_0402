"""
AI 交易檢討與學習系統 (Trade Review & Learning System)

分析每筆虧損交易，找出問題並記錄改進措施
自動調整進場條件，避免重複犯錯
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trade-review", tags=["Trade Review & Learning"])

# 儲存路徑
REVIEW_FILE = os.path.join(os.path.dirname(__file__), "../../data/trade_reviews.json")
LESSONS_FILE = os.path.join(os.path.dirname(__file__), "../../data/trading_lessons.json")

os.makedirs(os.path.dirname(REVIEW_FILE), exist_ok=True)


def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 預設的交易教訓
DEFAULT_LESSONS = {
    "entry_rules": {
        "min_smart_score": 65,
        "min_bullish_factors": 3,
        "require_trend_confirmation": True,
        "require_volume_confirmation": True,
        "avoid_gap_up_chase": True,
        "max_entry_vs_ma5_percent": 5,  # 不買超過 MA5 5% 以上的股票
    },
    "stop_loss_rules": {
        "max_loss_percent": 5,
        "use_atr_stop": True,
        "atr_multiplier": 1.5,
        "check_gap_risk": True,  # 檢查跳空風險
    },
    "signal_weights": {
        "大單分析": 0.8,  # 降低權重，因為多次失敗
        "ORB突破": 1.0,
        "法人買超": 1.0,
        "技術突破": 0.9,
        "主力進場": 0.9,
    },
    "blacklist": [],  # 避免交易的股票
    "lessons_learned": []
}


def get_lessons():
    data = load_json(LESSONS_FILE)
    if not data:
        data = DEFAULT_LESSONS
        save_json(LESSONS_FILE, data)
    return data


def update_lessons(lessons):
    save_json(LESSONS_FILE, lessons)


@router.post("/analyze/{symbol}")
async def analyze_failed_trade(
    symbol: str,
    entry_price: float = Query(..., description="進場價"),
    exit_price: float = Query(..., description="出場價"),
    stop_loss: float = Query(..., description="設定的停損價"),
    target_price: float = Query(..., description="目標價"),
    signal_source: str = Query(..., description="訊號來源"),
    entry_date: str = Query(..., description="進場日期 YYYY-MM-DD"),
    notes: str = Query("", description="備註")
):
    """
    分析一筆虧損交易，找出問題並記錄教訓
    """
    import yfinance as yf
    
    # 計算損益
    pnl_pct = (exit_price - entry_price) / entry_price * 100
    is_loss = pnl_pct < 0
    stop_missed = exit_price < stop_loss  # 實際出場價低於停損價
    
    # 獲取歷史數據進行分析
    analysis = {
        "symbol": symbol,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "stop_loss": stop_loss,
        "target_price": target_price,
        "signal_source": signal_source,
        "entry_date": entry_date,
        "pnl_percent": round(pnl_pct, 2),
        "is_loss": is_loss,
        "stop_missed": stop_missed,
        "problems": [],
        "recommendations": [],
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(period="1mo", interval="1d")
        
        if hist.empty:
            ticker = yf.Ticker(f"{symbol}.TWO")
            hist = ticker.history(period="1mo", interval="1d")
        
        if not hist.empty:
            # 分析進場時的技術狀態
            
            # 1. 檢查是否追高
            ma5 = hist['Close'].rolling(5).mean()
            ma20 = hist['Close'].rolling(20).mean()
            
            # 找進場日的數據
            entry_idx = None
            for i, idx in enumerate(hist.index):
                if idx.strftime('%Y-%m-%d') == entry_date:
                    entry_idx = i
                    break
            
            if entry_idx is not None and entry_idx > 0:
                entry_ma5 = ma5.iloc[entry_idx] if entry_idx < len(ma5) else None
                entry_ma20 = ma20.iloc[entry_idx] if entry_idx < len(ma20) else None
                
                # 問題 1: 追高買入
                if entry_ma5 and entry_price > float(entry_ma5) * 1.05:
                    analysis["problems"].append({
                        "type": "追高買入",
                        "detail": f"進場價 ${entry_price} 高於 MA5 ${float(entry_ma5):.2f} 超過 5%",
                        "severity": "高"
                    })
                    analysis["recommendations"].append("避免買入已大幅偏離 MA5 的股票")
                
                # 問題 2: 趨勢向下
                if entry_ma5 and entry_ma20 and float(entry_ma5) < float(entry_ma20):
                    analysis["problems"].append({
                        "type": "逆勢買入",
                        "detail": "進場時 MA5 < MA20，處於下降趨勢",
                        "severity": "高"
                    })
                    analysis["recommendations"].append("只在 MA5 > MA20 的上升趨勢中買入")
                
                # 問題 3: 連續下跌中買入
                prev_days = hist['Close'].iloc[max(0, entry_idx-3):entry_idx]
                if len(prev_days) >= 2:
                    consecutive_down = all(prev_days.diff().dropna() < 0)
                    if consecutive_down:
                        analysis["problems"].append({
                            "type": "接飛刀",
                            "detail": "進場前連續下跌，可能在接飛刀",
                            "severity": "中"
                        })
                        analysis["recommendations"].append("避免在連續下跌中買入，等待止跌訊號")
            
            # 問題 4: 跳空風險
            if stop_missed:
                # 檢查是否有跳空
                gaps = []
                for i in range(1, len(hist)):
                    gap_pct = (hist['Open'].iloc[i] - hist['Close'].iloc[i-1]) / hist['Close'].iloc[i-1] * 100
                    if abs(gap_pct) > 2:
                        gaps.append({
                            "date": hist.index[i].strftime('%Y-%m-%d'),
                            "gap_pct": round(gap_pct, 2)
                        })
                
                if gaps:
                    analysis["problems"].append({
                        "type": "跳空停損失效",
                        "detail": f"股票有跳空下跌風險，停損無法在預設價位觸發",
                        "severity": "高"
                    })
                    analysis["recommendations"].append("對高波動股票使用更寬的停損，或減少倉位")
    
    except Exception as e:
        logger.error(f"分析失敗: {e}")
    
    # 問題 5: 單一訊號
    analysis["problems"].append({
        "type": "單一訊號進場",
        "detail": f"僅依賴「{signal_source}」訊號，缺乏多因子確認",
        "severity": "中"
    })
    analysis["recommendations"].append("至少需要 3 個正向因子才能進場")
    
    # 問題 6: 風險報酬比
    risk = entry_price - stop_loss
    reward = target_price - entry_price
    rr_ratio = reward / risk if risk > 0 else 0
    if rr_ratio < 2:
        analysis["problems"].append({
            "type": "風險報酬比不佳",
            "detail": f"風報比只有 1:{rr_ratio:.1f}，建議至少 1:2",
            "severity": "低"
        })
        analysis["recommendations"].append("選擇風險報酬比至少 1:2 的交易機會")
    
    # 保存檢討記錄
    reviews = load_json(REVIEW_FILE)
    if "reviews" not in reviews:
        reviews["reviews"] = []
    reviews["reviews"].append(analysis)
    save_json(REVIEW_FILE, reviews)
    
    # 更新交易教訓
    lessons = get_lessons()
    
    # 降低失敗訊號來源的權重
    if signal_source in lessons["signal_weights"]:
        current_weight = lessons["signal_weights"][signal_source]
        new_weight = max(0.5, current_weight - 0.1)  # 每次失敗降低 0.1，最低 0.5
        lessons["signal_weights"][signal_source] = new_weight
        analysis["weight_adjusted"] = {
            "source": signal_source,
            "old_weight": current_weight,
            "new_weight": new_weight
        }
    
    # 記錄新教訓
    lesson_summary = f"{symbol}: {', '.join([p['type'] for p in analysis['problems']])}"
    if lesson_summary not in lessons["lessons_learned"]:
        lessons["lessons_learned"].append({
            "date": datetime.now().strftime('%Y-%m-%d'),
            "symbol": symbol,
            "loss_pct": round(pnl_pct, 2),
            "problems": [p['type'] for p in analysis['problems']],
            "key_lesson": analysis["recommendations"][0] if analysis["recommendations"] else ""
        })
    
    update_lessons(lessons)
    
    return {
        "success": True,
        "analysis": analysis,
        "lessons_updated": True,
        "message": f"已分析 {symbol} 的交易並更新交易教訓"
    }


@router.get("/lessons")
async def get_trading_lessons():
    """
    取得目前的交易教訓與規則
    """
    lessons = get_lessons()
    
    return {
        "entry_rules": lessons.get("entry_rules", {}),
        "stop_loss_rules": lessons.get("stop_loss_rules", {}),
        "signal_weights": lessons.get("signal_weights", {}),
        "lessons_learned": lessons.get("lessons_learned", [])[-10:],  # 最近 10 條
        "total_lessons": len(lessons.get("lessons_learned", []))
    }


@router.get("/should-trade/{symbol}")
async def should_trade(
    symbol: str,
    signal_source: str = Query(..., description="訊號來源"),
    entry_price: float = Query(..., description="預計進場價")
):
    """
    根據學習到的教訓，判斷是否應該進行這筆交易
    """
    import yfinance as yf
    
    lessons = get_lessons()
    warnings = []
    score = 100  # 滿分 100，根據問題扣分
    
    # 1. 檢查訊號來源權重
    signal_weight = lessons.get("signal_weights", {}).get(signal_source, 1.0)
    if signal_weight < 0.8:
        warnings.append(f"⚠️ 「{signal_source}」訊號歷史表現不佳 (權重 {signal_weight})")
        score -= 20
    
    # 2. 檢查是否在黑名單
    if symbol in lessons.get("blacklist", []):
        warnings.append(f"❌ {symbol} 在黑名單中，建議避免交易")
        score -= 50
    
    # 3. 檢查技術面
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(period="1mo", interval="1d")
        
        if hist.empty:
            ticker = yf.Ticker(f"{symbol}.TWO")
            hist = ticker.history(period="1mo", interval="1d")
        
        if not hist.empty:
            current_price = float(hist['Close'].iloc[-1])
            ma5 = float(hist['Close'].rolling(5).mean().iloc[-1])
            ma20 = float(hist['Close'].rolling(20).mean().iloc[-1])
            
            # 檢查追高
            entry_rules = lessons.get("entry_rules", {})
            max_vs_ma5 = entry_rules.get("max_entry_vs_ma5_percent", 5)
            
            if entry_price > ma5 * (1 + max_vs_ma5/100):
                warnings.append(f"⚠️ 進場價偏高：超過 MA5 {max_vs_ma5}%")
                score -= 15
            
            # 檢查趨勢
            if entry_rules.get("require_trend_confirmation", True):
                if ma5 < ma20:
                    warnings.append("⚠️ 趨勢向下：MA5 < MA20")
                    score -= 20
            
            # 連續下跌
            recent_returns = hist['Close'].pct_change().iloc[-3:]
            if all(recent_returns.dropna() < 0):
                warnings.append("⚠️ 最近 3 天連續下跌")
                score -= 15
            
            # 高波動風險
            volatility = float(hist['Close'].pct_change().std() * 100)
            if volatility > 4:
                warnings.append(f"⚠️ 高波動風險 (日波動 {volatility:.1f}%)")
                score -= 10
    
    except Exception as e:
        warnings.append(f"⚠️ 無法獲取技術數據: {str(e)}")
        score -= 10
    
    # 決定建議
    if score >= 80:
        recommendation = "✅ 可以交易"
        should_trade = True
    elif score >= 60:
        recommendation = "⚠️ 謹慎交易，注意風險"
        should_trade = True
    else:
        recommendation = "❌ 不建議交易"
        should_trade = False
    
    return {
        "symbol": symbol,
        "signal_source": signal_source,
        "entry_price": entry_price,
        "score": score,
        "should_trade": should_trade,
        "recommendation": recommendation,
        "warnings": warnings,
        "signal_weight": signal_weight
    }


@router.get("/history")
async def get_review_history(limit: int = Query(10, description="筆數")):
    """
    取得歷史檢討記錄
    """
    reviews = load_json(REVIEW_FILE)
    all_reviews = reviews.get("reviews", [])
    
    return {
        "total": len(all_reviews),
        "reviews": all_reviews[-limit:]
    }


@router.post("/reset-lessons")
async def reset_lessons():
    """
    重置交易教訓（測試用）
    """
    save_json(LESSONS_FILE, DEFAULT_LESSONS)
    return {"success": True, "message": "已重置交易教訓"}


@router.post("/review-all-stopped")
async def review_all_stopped_trades():
    """
    批量檢討所有停損交易
    
    自動從 Portfolio 讀取所有停損交易，
    跳過已檢討過的，對未檢討的進行分析
    """
    import yfinance as yf
    import httpx
    
    # 獲取已檢討的交易
    reviews = load_json(REVIEW_FILE)
    reviewed_trades = set()
    for r in reviews.get("reviews", []):
        # 用 symbol + entry_date 作為 key
        key = f"{r['symbol']}_{r['entry_date']}"
        reviewed_trades.add(key)
    
    # 從 Portfolio API 獲取所有停損交易
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://localhost:8000/api/portfolio/positions?status=stopped")
            stopped_positions = resp.json()
        except Exception as e:
            logger.error(f"獲取停損交易失敗: {e}")
            return {"success": False, "error": str(e)}
    
    # 篩選未檢討的交易
    to_review = []
    already_reviewed = []
    
    for pos in stopped_positions:
        entry_date = pos['entry_date'].split('T')[0] if 'T' in pos['entry_date'] else pos['entry_date']
        key = f"{pos['symbol']}_{entry_date}"
        
        if key in reviewed_trades:
            already_reviewed.append({
                "id": pos['id'],
                "symbol": pos['symbol'],
                "stock_name": pos.get('stock_name'),
                "status": "已檢討"
            })
        else:
            to_review.append(pos)
    
    # 對未檢討的交易進行分析
    results = []
    lessons = get_lessons()
    
    for pos in to_review:
        symbol = pos['symbol']
        entry_price = float(pos['entry_price'])
        exit_price = float(pos['exit_price']) if pos['exit_price'] else entry_price
        stop_loss = float(pos['stop_loss_price']) if pos['stop_loss_price'] else entry_price * 0.95
        target_price = float(pos['target_price']) if pos['target_price'] else entry_price * 1.1
        signal_source = pos.get('analysis_source', 'unknown')
        entry_date = pos['entry_date'].split('T')[0] if 'T' in pos['entry_date'] else pos['entry_date']
        
        # 計算損益
        pnl_pct = (exit_price - entry_price) / entry_price * 100
        stop_missed = exit_price < stop_loss
        
        analysis = {
            "portfolio_id": pos['id'],
            "symbol": symbol,
            "stock_name": pos.get('stock_name'),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "signal_source": signal_source,
            "entry_date": entry_date,
            "pnl_percent": round(pnl_pct, 2),
            "is_loss": pnl_pct < 0,
            "stop_missed": stop_missed,
            "problems": [],
            "recommendations": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # 分析問題
        try:
            ticker = yf.Ticker(f"{symbol}.TW")
            hist = ticker.history(period="2mo", interval="1d")
            
            if hist.empty:
                ticker = yf.Ticker(f"{symbol}.TWO")
                hist = ticker.history(period="2mo", interval="1d")
            
            if not hist.empty:
                ma5 = hist['Close'].rolling(5).mean()
                ma20 = hist['Close'].rolling(20).mean()
                
                # 找進場日
                entry_idx = None
                for i, idx in enumerate(hist.index):
                    if idx.strftime('%Y-%m-%d') == entry_date:
                        entry_idx = i
                        break
                
                if entry_idx is not None and entry_idx > 0:
                    entry_ma5 = ma5.iloc[entry_idx] if entry_idx < len(ma5) and ma5.iloc[entry_idx] is not None else None
                    entry_ma20 = ma20.iloc[entry_idx] if entry_idx < len(ma20) and ma20.iloc[entry_idx] is not None else None
                    
                    # 追高
                    if entry_ma5 is not None and entry_price > float(entry_ma5) * 1.05:
                        analysis["problems"].append({
                            "type": "追高買入",
                            "detail": f"進場價 ${entry_price:.2f} 高於 MA5 ${float(entry_ma5):.2f} 超過 5%",
                            "severity": "高"
                        })
                        analysis["recommendations"].append("避免買入已大幅偏離 MA5 的股票")
                    
                    # 逆勢
                    if entry_ma5 is not None and entry_ma20 is not None:
                        if float(entry_ma5) < float(entry_ma20):
                            analysis["problems"].append({
                                "type": "逆勢買入",
                                "detail": "進場時 MA5 < MA20，處於下降趨勢",
                                "severity": "高"
                            })
                            analysis["recommendations"].append("只在 MA5 > MA20 的上升趨勢中買入")
                
                # 跳空停損
                if stop_missed:
                    analysis["problems"].append({
                        "type": "跳空停損失效",
                        "detail": f"實際出場價 ${exit_price:.2f} 低於停損價 ${stop_loss:.2f}",
                        "severity": "高"
                    })
                    analysis["recommendations"].append("對高波動股票使用更寬的停損，或減少倉位")
        
        except Exception as e:
            logger.error(f"分析 {symbol} 失敗: {e}")
        
        # 單一訊號
        analysis["problems"].append({
            "type": "單一訊號進場",
            "detail": f"僅依賴「{signal_source}」訊號，缺乏多因子確認",
            "severity": "中"
        })
        analysis["recommendations"].append("至少需要 3 個正向因子才能進場")
        
        # 風險報酬比
        risk = entry_price - stop_loss
        reward = target_price - entry_price
        rr_ratio = reward / risk if risk > 0 else 0
        if rr_ratio < 2:
            analysis["problems"].append({
                "type": "風險報酬比不佳",
                "detail": f"風報比只有 1:{rr_ratio:.1f}，建議至少 1:2",
                "severity": "低"
            })
            analysis["recommendations"].append("選擇風險報酬比至少 1:2 的交易機會")
        
        # 保存檢討
        if "reviews" not in reviews:
            reviews["reviews"] = []
        reviews["reviews"].append(analysis)
        
        # 更新訊號權重
        # 將 analysis_source 映射到 signal_weights 的 key
        source_mapping = {
            "big_order": "大單分析",
            "main_force": "主力進場",
            "lstm_prediction": "LSTM預測",
            "orb": "ORB突破",
            "institutional": "法人買超"
        }
        mapped_source = source_mapping.get(signal_source, signal_source)
        
        if mapped_source in lessons["signal_weights"]:
            old_weight = lessons["signal_weights"][mapped_source]
            new_weight = max(0.3, old_weight - 0.05)  # 每次失敗降低 0.05
            lessons["signal_weights"][mapped_source] = new_weight
            analysis["weight_adjusted"] = {
                "source": mapped_source,
                "old_weight": round(old_weight, 2),
                "new_weight": round(new_weight, 2)
            }
        else:
            # 新訊號來源，從 1.0 開始
            lessons["signal_weights"][mapped_source] = 0.9
            analysis["weight_adjusted"] = {
                "source": mapped_source,
                "old_weight": 1.0,
                "new_weight": 0.9
            }
        
        # 記錄教訓
        lessons["lessons_learned"].append({
            "date": datetime.now().strftime('%Y-%m-%d'),
            "symbol": symbol,
            "stock_name": pos.get('stock_name'),
            "loss_pct": round(pnl_pct, 2),
            "problems": [p['type'] for p in analysis['problems']],
            "key_lesson": analysis["recommendations"][0] if analysis["recommendations"] else ""
        })
        
        results.append(analysis)
    
    # 保存
    save_json(REVIEW_FILE, reviews)
    update_lessons(lessons)
    
    # 計算統計
    problem_counts = {}
    for r in results:
        for p in r['problems']:
            ptype = p['type']
            problem_counts[ptype] = problem_counts.get(ptype, 0) + 1
    
    return {
        "success": True,
        "total_stopped": len(stopped_positions),
        "already_reviewed": len(already_reviewed),
        "newly_reviewed": len(results),
        "problem_summary": problem_counts,
        "signal_weights": lessons["signal_weights"],
        "results": results,
        "already_reviewed_list": already_reviewed
    }


@router.get("/reviewed-ids")
async def get_reviewed_ids():
    """
    取得已檢討的交易 ID 列表
    """
    reviews = load_json(REVIEW_FILE)
    reviewed = []
    for r in reviews.get("reviews", []):
        reviewed.append({
            "symbol": r.get('symbol'),
            "entry_date": r.get('entry_date'),
            "portfolio_id": r.get('portfolio_id'),
            "pnl_percent": r.get('pnl_percent'),
            "problems_count": len(r.get('problems', []))
        })
    return {
        "count": len(reviewed),
        "reviewed": reviewed
    }


@router.get("/problem-statistics")
async def get_problem_statistics():
    """
    取得問題類型統計，找出最常見的錯誤
    """
    reviews = load_json(REVIEW_FILE)
    all_reviews = reviews.get("reviews", [])
    
    problem_counts = {}
    total_loss = 0
    
    for r in all_reviews:
        if r.get('pnl_percent', 0) < 0:
            total_loss += abs(r['pnl_percent'])
        for p in r.get('problems', []):
            ptype = p['type']
            if ptype not in problem_counts:
                problem_counts[ptype] = {"count": 0, "severity": {}}
            problem_counts[ptype]["count"] += 1
            sev = p.get('severity', '中')
            problem_counts[ptype]["severity"][sev] = problem_counts[ptype]["severity"].get(sev, 0) + 1
    
    # 排序
    sorted_problems = sorted(problem_counts.items(), key=lambda x: x[1]['count'], reverse=True)
    
    return {
        "total_reviews": len(all_reviews),
        "total_loss_pct": round(total_loss, 2),
        "avg_loss_pct": round(total_loss / len(all_reviews), 2) if all_reviews else 0,
        "problems": [{"type": k, **v} for k, v in sorted_problems],
        "top_problem": sorted_problems[0][0] if sorted_problems else None,
        "focus_area": f"需重點改進：{sorted_problems[0][0]}" if sorted_problems else "無數據"
    }

