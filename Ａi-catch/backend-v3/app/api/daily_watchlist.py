"""
AI 每日強勢股觀察名單 (Daily Watchlist System)

自動篩選高成交量、大漲的股票
作為 AI 進場參考依據

篩選條件：
1. 漲幅 >= 5% (或指定範圍)
2. 成交量 > 平均量 1.5 倍
3. 經過多因子檢查
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["Daily Watchlist"])

# 觀察名單儲存路徑
WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "../../data/daily_watchlist.json")
os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)


def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"watchlists": {}}
    return {"watchlists": {}}


def save_watchlist(data):
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@router.post("/scan-strong-stocks")
async def scan_strong_stocks(
    min_gain_pct: float = Query(5.0, description="最小漲幅 %"),
    max_gain_pct: float = Query(10.0, description="最大漲幅 %"),
    min_volume_ratio: float = Query(1.5, description="最小成交量倍數（相對平均量）"),
    limit: int = Query(10, description="最多筆數")
):
    """
    掃描強勢股
    
    找出高成交量、大漲的股票，自動進行多因子檢查
    """
    import yfinance as yf
    import httpx
    
    # 台股完整股票池（大幅擴展）
    stock_pool = [
        # 權值股 / 大型股
        "2330", "2454", "2317", "2308", "3711", "2382", "2303", "2412", "3008", "2345",
        
        # 面板股（漲停股常客！）
        "3481", "2409", "3483", "2374", "6116", "8069",  # 群創、友達、榮創、凌巨、彩晶
        
        # 航運股
        "2603", "2609", "2615", "2618", "2606", "2610", "5608",  # 長榮、陽明、萬海、長榮航
        
        # 鋼鐵股
        "2002", "2006", "2014", "2015", "2017", "2020", "2025",
        
        # 塑化 / 傳產
        "1301", "1303", "1326", "1402", "1101", "1102", "1216", "2207", "2912", "2801",
        
        # 金融股
        "2880", "2881", "2882", "2883", "2884", "2885", "2886", "2887", "2888", "2889",
        "2890", "2891", "2892", "5880", "2834", "2838",
        
        # 半導體 / IC設計
        "2379", "2327", "3034", "3443", "2408", "2474", "6669", "3661", "5274", "3533",
        "6770", "3035", "3037", "2357", "2395", "6285", "3006", "2449", "3711", "6415",
        "6239", "5483", "6531", "3529", "8150", "8086", "6147", "6414",
        
        # 記憶體股（常有大漲）
        "2337", "2344", "2408", "3450", "4967", "8299",  # 旺宏、華邦電、南亞科、聯鈞、十銓、群聯
        
        # PCB / 電路板
        "3037", "2474", "8046", "3149", "3044", "6213", "8213",
        
        # 電子零組件
        "3034", "2327", "3231", "3533", "3545", "6176", "6269", "8210", "3022", "6279",
        
        # AI / 伺服器概念
        "2382", "3017", "5274", "6669", "4938", "2353", "3044", "3708", "6214",
        
        # 車用電子
        "2308", "3231", "6285", "6271", "3611", "6153", "6415", "3558", "4551",
        
        # 被動元件
        "2327", "3036", "6147", "8261",
        
        # 中小型股 / 熱門交易股（常有大漲）
        "3006", "6257", "8039", "6176", "3031", "6531", "3293", "8215", "3707", 
        "8936", "6715", "3450", "6683", "6781", "3653", "8044", "6863", "5388", "6789",
        "8110", "3227", "3680", "4919", "6488", "6451", "3017", "8299", "6643", "6182",
        "3536", "4551", "6477", "6462", "6472", "5347", "3653", "6189", "6138", "6568",
        
        # 生技醫療
        "6446", "4743", "1760", "4147", "6547", "4142", "4126", "4174", "1795", "6652",
        
        # 光電 / LED
        "3030", "6167", "6244", "3380", "3406", "6168",
        
        # 營建 / 資產
        "2520", "2504", "2534", "2524", "5522", "3231",
        
        # 紡織
        "1402", "1434", "1440", "1476", "1477",
        
        # 食品
        "1216", "1227", "2105", "2912", "1210",
        
        # 觀光
        "2702", "2704", "2707", "2731",
        
        # 通訊
        "2412", "3045", "3682", "3704", "6285",
        
        # 其他熱門小型股（經常漲停）
        "8440", "6891", "8358", "3702", "5905", "6658", "3260", "1264", "3089", "6679",
        "8074", "5206", "2636", "8163", "6690", "3025", "4551", "6509", "6592", "6698",
    ]
    
    # 去重
    stock_pool = list(set(stock_pool))
    
    results = []
    errors = []
    
    for symbol in stock_pool:
        try:
            # 嘗試取得股票數據
            ticker = yf.Ticker(f"{symbol}.TW")
            hist = ticker.history(period="1mo", interval="1d")
            
            if hist.empty:
                ticker = yf.Ticker(f"{symbol}.TWO")
                hist = ticker.history(period="1mo", interval="1d")
            
            if hist.empty or len(hist) < 5:
                continue
            
            # 計算指標
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) >= 2 else latest
            
            current_price = float(latest['Close'])
            prev_close = float(prev['Close'])
            change_pct = (current_price - prev_close) / prev_close * 100
            
            volume = int(latest['Volume'])
            avg_volume = float(hist['Volume'].iloc[:-1].mean()) if len(hist) > 1 else volume
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1
            
            # 篩選條件
            if change_pct < min_gain_pct or change_pct > max_gain_pct:
                continue
            if volume_ratio < min_volume_ratio:
                continue
            
            # 額外計算
            ma5 = float(hist['Close'].rolling(5).mean().iloc[-1])
            ma20 = float(hist['Close'].rolling(20).mean().iloc[-1]) if len(hist) >= 20 else ma5
            above_ma5 = current_price > ma5
            above_ma20 = current_price > ma20
            
            # 獲取股票名稱
            stock_name = symbol  # 預設
            try:
                info = ticker.info
                stock_name = info.get('shortName', info.get('longName', symbol))
            except:
                pass
            
            results.append({
                "symbol": symbol,
                "name": stock_name,
                "price": round(current_price, 2),
                "change_pct": round(change_pct, 2),
                "volume": volume,
                "volume_ratio": round(volume_ratio, 2),
                "ma5": round(ma5, 2),
                "ma20": round(ma20, 2),
                "above_ma5": above_ma5,
                "above_ma20": above_ma20,
                "trend": "上升" if above_ma5 and above_ma20 else "整理" if above_ma5 else "下降"
            })
            
        except Exception as e:
            errors.append({"symbol": symbol, "error": str(e)})
            continue
    
    # 按漲幅排序
    results.sort(key=lambda x: x['change_pct'], reverse=True)
    results = results[:limit]
    
    # 對篩選出的股票進行多因子檢查
    checked_results = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for stock in results:
            try:
                resp = await client.get(
                    f"http://localhost:8000/api/entry-check/comprehensive/{stock['symbol']}",
                    params={"entry_price": stock['price'], "signal_source": "daily_scan"}
                )
                if resp.status_code == 200:
                    check_result = resp.json()
                    stock["entry_check"] = {
                        "passed_count": check_result.get("passed_count", 0),
                        "total_checks": check_result.get("total_checks", 6),
                        "confidence": check_result.get("confidence", 0),
                        "should_enter": check_result.get("should_enter", False),
                        "recommendation": check_result.get("recommended_action", ""),
                        "blockers": check_result.get("blockers", []),
                        "warnings": check_result.get("warnings", [])[:3]
                    }
            except Exception as e:
                stock["entry_check"] = {"error": str(e)}
            
            checked_results.append(stock)
    
    # 保存觀察名單
    today = datetime.now().strftime('%Y-%m-%d')
    watchlist_data = load_watchlist()
    watchlist_data["watchlists"][today] = {
        "scan_time": datetime.now().isoformat(),
        "criteria": {
            "min_gain_pct": min_gain_pct,
            "max_gain_pct": max_gain_pct,
            "min_volume_ratio": min_volume_ratio
        },
        "stocks": checked_results
    }
    save_watchlist(watchlist_data)
    
    # 分類結果
    can_enter = [s for s in checked_results if s.get("entry_check", {}).get("should_enter")]
    
    return {
        "success": True,
        "date": today,
        "scan_time": datetime.now().isoformat(),
        "criteria": {
            "min_gain_pct": min_gain_pct,
            "max_gain_pct": max_gain_pct,
            "min_volume_ratio": min_volume_ratio
        },
        "total_scanned": len(stock_pool),
        "total_found": len(checked_results),
        "can_enter_count": len(can_enter),
        "recommended": can_enter[:5],  # 最佳 5 檔
        "watchlist": checked_results,
        "errors_count": len(errors)
    }


@router.get("/today")
async def get_today_watchlist():
    """
    取得今日觀察名單
    """
    today = datetime.now().strftime('%Y-%m-%d')
    data = load_watchlist()
    
    if today not in data.get("watchlists", {}):
        return {
            "date": today,
            "message": "今日尚未掃描，請先執行 /scan-strong-stocks",
            "stocks": []
        }
    
    watchlist = data["watchlists"][today]
    stocks = watchlist.get("stocks", [])
    
    # 找出可進場的
    can_enter = [s for s in stocks if s.get("entry_check", {}).get("should_enter")]
    
    return {
        "date": today,
        "scan_time": watchlist.get("scan_time"),
        "criteria": watchlist.get("criteria"),
        "total": len(stocks),
        "can_enter_count": len(can_enter),
        "recommended": can_enter,
        "all_stocks": stocks
    }


@router.get("/history")
async def get_watchlist_history(days: int = Query(7, description="查詢天數")):
    """
    取得歷史觀察名單
    """
    data = load_watchlist()
    watchlists = data.get("watchlists", {})
    
    # 按日期排序
    sorted_dates = sorted(watchlists.keys(), reverse=True)[:days]
    
    history = []
    for date in sorted_dates:
        wl = watchlists[date]
        stocks = wl.get("stocks", [])
        can_enter = [s for s in stocks if s.get("entry_check", {}).get("should_enter")]
        
        history.append({
            "date": date,
            "total_stocks": len(stocks),
            "can_enter": len(can_enter),
            "top_3": [s["symbol"] for s in stocks[:3]],
            "criteria": wl.get("criteria")
        })
    
    return {
        "days": days,
        "history": history
    }


@router.post("/add-manual")
async def add_to_watchlist(
    symbol: str = Query(..., description="股票代碼"),
    reason: str = Query("", description="加入原因")
):
    """
    手動加入觀察名單
    """
    import yfinance as yf
    import httpx
    
    today = datetime.now().strftime('%Y-%m-%d')
    data = load_watchlist()
    
    if today not in data.get("watchlists", {}):
        data["watchlists"][today] = {
            "scan_time": datetime.now().isoformat(),
            "stocks": []
        }
    
    # 獲取股票資訊
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(period="5d", interval="1d")
        
        if hist.empty:
            ticker = yf.Ticker(f"{symbol}.TWO")
            hist = ticker.history(period="5d", interval="1d")
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"無法取得 {symbol} 的數據")
        
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else latest
        
        current_price = float(latest['Close'])
        change_pct = (current_price - float(prev['Close'])) / float(prev['Close']) * 100
        volume = int(latest['Volume'])
        avg_volume = float(hist['Volume'].mean())
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
        
        stock_info = {
            "symbol": symbol,
            "name": symbol,
            "price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "volume": volume,
            "volume_ratio": round(volume_ratio, 2),
            "manual_add": True,
            "reason": reason,
            "added_at": datetime.now().isoformat()
        }
        
        # 進行多因子檢查
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.get(
                    f"http://localhost:8000/api/entry-check/comprehensive/{symbol}",
                    params={"entry_price": current_price, "signal_source": "manual_add"}
                )
                if resp.status_code == 200:
                    check_result = resp.json()
                    stock_info["entry_check"] = {
                        "passed_count": check_result.get("passed_count", 0),
                        "total_checks": check_result.get("total_checks", 6),
                        "confidence": check_result.get("confidence", 0),
                        "should_enter": check_result.get("should_enter", False),
                        "recommendation": check_result.get("recommended_action", "")
                    }
            except:
                pass
        
        # 檢查是否已存在
        existing = [s for s in data["watchlists"][today]["stocks"] if s["symbol"] == symbol]
        if existing:
            return {"success": False, "message": f"{symbol} 已在今日觀察名單中"}
        
        data["watchlists"][today]["stocks"].append(stock_info)
        save_watchlist(data)
        
        return {
            "success": True,
            "message": f"已將 {symbol} 加入今日觀察名單",
            "stock": stock_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_watchlist_performance():
    """
    觀察名單績效追蹤
    
    追蹤歷史觀察名單的後續表現
    """
    import yfinance as yf
    
    data = load_watchlist()
    watchlists = data.get("watchlists", {})
    
    performance = []
    
    for date, wl in watchlists.items():
        stocks = wl.get("stocks", [])
        
        for stock in stocks[:5]:  # 每天只追蹤前 5 檔
            symbol = stock["symbol"]
            entry_price = stock.get("price", 0)
            
            if not entry_price:
                continue
            
            try:
                ticker = yf.Ticker(f"{symbol}.TW")
                hist = ticker.history(period="5d", interval="1d")
                
                if hist.empty:
                    ticker = yf.Ticker(f"{symbol}.TWO")
                    hist = ticker.history(period="5d", interval="1d")
                
                if hist.empty:
                    continue
                
                current_price = float(hist['Close'].iloc[-1])
                pnl_pct = (current_price - entry_price) / entry_price * 100
                
                performance.append({
                    "date": date,
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "current_price": round(current_price, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "was_recommended": stock.get("entry_check", {}).get("should_enter", False)
                })
            except:
                continue
    
    # 統計
    recommended = [p for p in performance if p["was_recommended"]]
    not_recommended = [p for p in performance if not p["was_recommended"]]
    
    rec_avg_pnl = sum(p["pnl_pct"] for p in recommended) / len(recommended) if recommended else 0
    not_rec_avg_pnl = sum(p["pnl_pct"] for p in not_recommended) / len(not_recommended) if not_recommended else 0
    
    return {
        "total_tracked": len(performance),
        "recommended_count": len(recommended),
        "not_recommended_count": len(not_recommended),
        "recommended_avg_pnl": round(rec_avg_pnl, 2),
        "not_recommended_avg_pnl": round(not_rec_avg_pnl, 2),
        "conclusion": "建議股表現較佳" if rec_avg_pnl > not_rec_avg_pnl else "需要改進選股策略",
        "details": performance[-20:]  # 最近 20 筆
    }


@router.get("/candidates")
async def get_entry_candidates():
    """
    取得可進場候選股
    
    從最近的觀察名單中，找出通過多因子檢查的股票
    """
    today = datetime.now().strftime('%Y-%m-%d')
    data = load_watchlist()
    
    candidates = []
    
    for date in sorted(data.get("watchlists", {}).keys(), reverse=True)[:3]:
        wl = data["watchlists"][date]
        for stock in wl.get("stocks", []):
            entry_check = stock.get("entry_check", {})
            if entry_check.get("should_enter"):
                stock["scan_date"] = date
                candidates.append(stock)
    
    # 去重
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c["symbol"] not in seen:
            seen.add(c["symbol"])
            unique_candidates.append(c)
    
    return {
        "count": len(unique_candidates),
        "candidates": unique_candidates,
        "message": "這些股票通過多因子檢查，可考慮進場" if unique_candidates else "目前沒有適合進場的股票"
    }
