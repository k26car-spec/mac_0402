"""
AI 交易績效追蹤系統 (AI Trading Performance Tracker)

記錄 AI 的每次交易決策，追蹤準確性
讓用戶可以驗證 AI 的預測能力
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-performance", tags=["AI Performance Tracker"])

# 儲存路徑
PERFORMANCE_FILE = os.path.join(os.path.dirname(__file__), "../../data/ai_performance.json")

# 確保數據目錄存在
os.makedirs(os.path.dirname(PERFORMANCE_FILE), exist_ok=True)


class TradeDecision(BaseModel):
    """AI 交易決策記錄"""
    stock_code: str
    stock_name: Optional[str] = None
    decision: str  # BUY, SELL, HOLD
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    smart_score: float  # 進場時的智慧評分
    factors: dict  # 評分因子
    reason: str  # 進場理由


def load_performance_data():
    """載入績效數據"""
    if os.path.exists(PERFORMANCE_FILE):
        try:
            with open(PERFORMANCE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"trades": [], "stats": {}}
    return {"trades": [], "stats": {}}


def save_performance_data(data):
    """儲存績效數據"""
    with open(PERFORMANCE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@router.post("/record-decision")
async def record_ai_decision(decision: TradeDecision):
    """
    記錄 AI 的交易決策
    
    當 AI 做出買入/賣出決策時，記錄下來供日後追蹤
    """
    data = load_performance_data()
    
    trade_record = {
        "id": len(data["trades"]) + 1,
        "stock_code": decision.stock_code,
        "stock_name": decision.stock_name,
        "decision": decision.decision,
        "entry_price": decision.entry_price,
        "stop_loss": decision.stop_loss,
        "take_profit": decision.take_profit,
        "smart_score": decision.smart_score,
        "factors": decision.factors,
        "reason": decision.reason,
        "decision_time": datetime.now().isoformat(),
        "status": "OPEN",  # OPEN, CLOSED_WIN, CLOSED_LOSS, CLOSED_EVEN
        "exit_price": None,
        "exit_time": None,
        "pnl": None,
        "pnl_pct": None
    }
    
    data["trades"].append(trade_record)
    save_performance_data(data)
    
    return {
        "success": True,
        "message": "已記錄 AI 交易決策",
        "trade_id": trade_record["id"],
        "decision": decision.decision,
        "stock_code": decision.stock_code,
        "entry_price": decision.entry_price,
        "smart_score": decision.smart_score
    }


@router.post("/update-result/{trade_id}")
async def update_trade_result(
    trade_id: int,
    exit_price: float = Query(..., description="出場價格"),
    exit_reason: str = Query(default="", description="出場原因")
):
    """
    更新交易結果
    
    當交易結束時，記錄實際結果
    """
    data = load_performance_data()
    
    # 找到交易記錄
    trade = None
    for t in data["trades"]:
        if t["id"] == trade_id:
            trade = t
            break
    
    if not trade:
        raise HTTPException(status_code=404, detail=f"找不到交易 ID: {trade_id}")
    
    if trade["status"] != "OPEN":
        raise HTTPException(status_code=400, detail="此交易已結束")
    
    # 計算盈虧
    entry_price = trade["entry_price"]
    is_buy = trade["decision"] == "BUY"
    
    if is_buy:
        pnl = exit_price - entry_price
        pnl_pct = (pnl / entry_price) * 100
    else:
        pnl = entry_price - exit_price
        pnl_pct = (pnl / entry_price) * 100
    
    # 判斷結果
    if pnl > 0:
        status = "CLOSED_WIN"
    elif pnl < 0:
        status = "CLOSED_LOSS"
    else:
        status = "CLOSED_EVEN"
    
    # 更新記錄
    trade["exit_price"] = exit_price
    trade["exit_time"] = datetime.now().isoformat()
    trade["pnl"] = round(pnl, 2)
    trade["pnl_pct"] = round(pnl_pct, 2)
    trade["status"] = status
    trade["exit_reason"] = exit_reason
    
    save_performance_data(data)
    
    return {
        "success": True,
        "trade_id": trade_id,
        "stock_code": trade["stock_code"],
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl": trade["pnl"],
        "pnl_pct": trade["pnl_pct"],
        "result": "獲利" if status == "CLOSED_WIN" else "虧損" if status == "CLOSED_LOSS" else "打平"
    }


@router.get("/stats")
async def get_performance_stats():
    """
    取得 AI 交易績效統計
    
    計算準確率、獲利率等關鍵指標
    """
    data = load_performance_data()
    trades = data["trades"]
    
    # 過濾已結束的交易
    closed_trades = [t for t in trades if t["status"] != "OPEN"]
    open_trades = [t for t in trades if t["status"] == "OPEN"]
    
    if not closed_trades:
        return {
            "total_trades": len(trades),
            "open_trades": len(open_trades),
            "closed_trades": 0,
            "message": "尚無已結束的交易可供統計"
        }
    
    # 計算統計
    wins = len([t for t in closed_trades if t["status"] == "CLOSED_WIN"])
    losses = len([t for t in closed_trades if t["status"] == "CLOSED_LOSS"])
    evens = len([t for t in closed_trades if t["status"] == "CLOSED_EVEN"])
    
    win_rate = (wins / len(closed_trades)) * 100 if closed_trades else 0
    
    total_pnl = sum(t.get("pnl", 0) or 0 for t in closed_trades)
    total_pnl_pct = sum(t.get("pnl_pct", 0) or 0 for t in closed_trades)
    avg_pnl_pct = total_pnl_pct / len(closed_trades) if closed_trades else 0
    
    # 按智慧評分分組統計
    high_score_trades = [t for t in closed_trades if t.get("smart_score", 0) >= 65]
    low_score_trades = [t for t in closed_trades if t.get("smart_score", 0) < 65]
    
    high_score_wins = len([t for t in high_score_trades if t["status"] == "CLOSED_WIN"])
    high_score_win_rate = (high_score_wins / len(high_score_trades) * 100) if high_score_trades else 0
    
    low_score_wins = len([t for t in low_score_trades if t["status"] == "CLOSED_WIN"])
    low_score_win_rate = (low_score_wins / len(low_score_trades) * 100) if low_score_trades else 0
    
    return {
        "summary": {
            "total_trades": len(trades),
            "open_trades": len(open_trades),
            "closed_trades": len(closed_trades),
            "wins": wins,
            "losses": losses,
            "evens": evens,
            "win_rate": round(win_rate, 1),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "avg_pnl_pct": round(avg_pnl_pct, 2)
        },
        "by_score": {
            "high_score_trades": len(high_score_trades),
            "high_score_win_rate": round(high_score_win_rate, 1),
            "low_score_trades": len(low_score_trades),
            "low_score_win_rate": round(low_score_win_rate, 1),
            "score_matters": high_score_win_rate > low_score_win_rate
        },
        "insight": _generate_insight(win_rate, high_score_win_rate, low_score_win_rate, avg_pnl_pct),
        "timestamp": datetime.now().isoformat()
    }


def _generate_insight(win_rate, high_score_win_rate, low_score_win_rate, avg_pnl_pct):
    """生成績效洞察"""
    insights = []
    
    if win_rate >= 60:
        insights.append(f"✅ AI 勝率 {win_rate:.1f}% 表現良好")
    elif win_rate >= 50:
        insights.append(f"⚠️ AI 勝率 {win_rate:.1f}% 尚可，仍有改進空間")
    else:
        insights.append(f"❌ AI 勝率 {win_rate:.1f}% 偏低，需要調整策略")
    
    if high_score_win_rate > low_score_win_rate + 10:
        insights.append(f"📊 高評分交易勝率 ({high_score_win_rate:.1f}%) 明顯優於低評分 ({low_score_win_rate:.1f}%)，建議只做高評分交易")
    
    if avg_pnl_pct > 0:
        insights.append(f"💰 平均每筆獲利 {avg_pnl_pct:.2f}%")
    else:
        insights.append(f"💸 平均每筆虧損 {abs(avg_pnl_pct):.2f}%，需控制停損")
    
    return insights


@router.get("/trades")
async def get_all_trades(
    status: Optional[str] = Query(None, description="狀態: OPEN, CLOSED_WIN, CLOSED_LOSS"),
    limit: int = Query(20, description="筆數限制")
):
    """
    取得所有交易記錄
    """
    data = load_performance_data()
    trades = data["trades"]
    
    if status:
        trades = [t for t in trades if t["status"] == status]
    
    # 按時間倒序
    trades = sorted(trades, key=lambda x: x.get("decision_time", ""), reverse=True)
    
    return {
        "count": len(trades),
        "trades": trades[:limit]
    }


@router.get("/open-trades")
async def get_open_trades():
    """
    取得目前持倉的交易
    """
    data = load_performance_data()
    open_trades = [t for t in data["trades"] if t["status"] == "OPEN"]
    
    # 取得即時價格並計算未實現盈虧
    import yfinance as yf
    
    for trade in open_trades:
        try:
            ticker = yf.Ticker(f"{trade['stock_code']}.TW")
            hist = ticker.history(period="1d")
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                entry = trade["entry_price"]
                
                if trade["decision"] == "BUY":
                    unrealized_pnl = current_price - entry
                    unrealized_pnl_pct = (unrealized_pnl / entry) * 100
                else:
                    unrealized_pnl = entry - current_price
                    unrealized_pnl_pct = (unrealized_pnl / entry) * 100
                
                trade["current_price"] = round(current_price, 2)
                trade["unrealized_pnl"] = round(unrealized_pnl, 2)
                trade["unrealized_pnl_pct"] = round(unrealized_pnl_pct, 2)
        except:
            pass
    
    return {
        "count": len(open_trades),
        "trades": open_trades
    }


@router.delete("/clear-all")
async def clear_all_trades():
    """
    清除所有交易記錄（測試用）
    """
    save_performance_data({"trades": [], "stats": {}})
    return {"success": True, "message": "已清除所有交易記錄"}


@router.get("/accuracy-report")
async def get_accuracy_report():
    """
    生成詳細的準確性報告
    """
    data = load_performance_data()
    trades = data["trades"]
    closed = [t for t in trades if t["status"] != "OPEN"]
    
    if not closed:
        return {"message": "尚無已結束交易，無法生成報告"}
    
    # 按月統計
    monthly_stats = {}
    for t in closed:
        month = t.get("decision_time", "")[:7]  # YYYY-MM
        if month not in monthly_stats:
            monthly_stats[month] = {"wins": 0, "losses": 0, "total_pnl_pct": 0}
        
        if t["status"] == "CLOSED_WIN":
            monthly_stats[month]["wins"] += 1
        elif t["status"] == "CLOSED_LOSS":
            monthly_stats[month]["losses"] += 1
        monthly_stats[month]["total_pnl_pct"] += t.get("pnl_pct", 0) or 0
    
    # 按因子分析
    factor_analysis = {}
    for t in closed:
        for factor, detail in t.get("factors", {}).items():
            if factor not in factor_analysis:
                factor_analysis[factor] = {"high_score_wins": 0, "high_score_total": 0, 
                                           "low_score_wins": 0, "low_score_total": 0}
            
            score = detail.get("score", 50)
            is_win = t["status"] == "CLOSED_WIN"
            
            if score >= 60:
                factor_analysis[factor]["high_score_total"] += 1
                if is_win:
                    factor_analysis[factor]["high_score_wins"] += 1
            else:
                factor_analysis[factor]["low_score_total"] += 1
                if is_win:
                    factor_analysis[factor]["low_score_wins"] += 1
    
    # 計算各因子的預測能力
    factor_effectiveness = {}
    for factor, stats in factor_analysis.items():
        high_rate = (stats["high_score_wins"] / stats["high_score_total"] * 100) if stats["high_score_total"] > 0 else 0
        low_rate = (stats["low_score_wins"] / stats["low_score_total"] * 100) if stats["low_score_total"] > 0 else 0
        factor_effectiveness[factor] = {
            "high_score_win_rate": round(high_rate, 1),
            "low_score_win_rate": round(low_rate, 1),
            "predictive_power": round(high_rate - low_rate, 1),
            "is_effective": high_rate > low_rate
        }
    
    return {
        "total_closed_trades": len(closed),
        "overall_win_rate": round(len([t for t in closed if t["status"] == "CLOSED_WIN"]) / len(closed) * 100, 1),
        "monthly_stats": monthly_stats,
        "factor_effectiveness": factor_effectiveness,
        "most_effective_factor": max(factor_effectiveness.items(), key=lambda x: x[1]["predictive_power"])[0] if factor_effectiveness else None,
        "generated_at": datetime.now().isoformat()
    }
