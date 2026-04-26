"""
Portfolio API Routes
持有股票與交易紀錄 API
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, desc
from pydantic import BaseModel, Field

from app.database.connection import get_db
from app.models.portfolio import Portfolio, TradeRecord, AnalysisAccuracy
from app.services.auto_close_monitor import run_auto_close_monitor

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

# ============== Capital Management ==============
import json
CAPITAL_FILE = os.path.join(os.path.dirname(__file__), "../../data/capital_config.json")

def get_capital_config():
    if not os.path.exists(CAPITAL_FILE):
        return {"total_capital": 0.0, "available_capital": 0.0}
    try:
        with open(CAPITAL_FILE, "r") as f:
            return json.load(f)
    except:
        return {"total_capital": 0.0, "available_capital": 0.0}

def save_capital_config(data):
    os.makedirs(os.path.dirname(CAPITAL_FILE), exist_ok=True)
    with open(CAPITAL_FILE, "w") as f:
        json.dump(data, f)



# ============== Pydantic Models ==============

class PortfolioCreate(BaseModel):
    """創建持有股票"""
    symbol: str
    stock_name: Optional[str] = None
    entry_date: datetime
    entry_price: float
    entry_quantity: int = 1000
    analysis_source: str
    analysis_confidence: Optional[float] = None
    analysis_details: Optional[dict] = None
    stop_loss_price: Optional[float] = None
    stop_loss_amount: Optional[float] = None
    target_price: Optional[float] = None
    is_simulated: bool = False
    notes: Optional[str] = None


class PortfolioUpdate(BaseModel):
    """更新持有股票"""
    current_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    target_price: Optional[float] = None
    notes: Optional[str] = None


class PortfolioClose(BaseModel):
    """結束持有（賣出）"""
    exit_date: datetime
    exit_price: float
    exit_reason: Optional[str] = None
    notes: Optional[str] = None


class PortfolioResponse(BaseModel):
    """持有股票回應"""
    id: int
    symbol: str
    stock_name: Optional[str]
    entry_date: datetime
    entry_price: float
    entry_quantity: int
    analysis_source: str
    analysis_confidence: Optional[float]
    analysis_details: Optional[dict]
    stop_loss_price: Optional[float]
    stop_loss_amount: Optional[float]
    target_price: Optional[float]
    current_price: Optional[float]
    unrealized_profit: Optional[float]
    unrealized_profit_percent: Optional[float]
    exit_date: Optional[datetime]
    exit_price: Optional[float]
    exit_reason: Optional[str]
    realized_profit: Optional[float]
    realized_profit_percent: Optional[float]
    status: str
    is_simulated: bool
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TradeRecordResponse(BaseModel):
    """交易紀錄回應"""
    id: int
    portfolio_id: Optional[int]
    symbol: str
    stock_name: Optional[str]
    trade_type: str
    trade_date: datetime
    price: float
    quantity: int
    total_amount: float
    analysis_source: str
    analysis_confidence: Optional[float]
    profit: Optional[float]
    profit_percent: Optional[float]
    is_simulated: bool
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AccuracyResponse(BaseModel):
    """準確性分析回應"""
    analysis_source: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    net_profit: float
    avg_profit_percent: Optional[float]
    avg_loss_percent: Optional[float]


class SimulationRequest(BaseModel):
    """AI 模擬交易請求"""
    symbol: str
    analysis_source: str
    entry_price: float
    entry_date: datetime
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    simulation_days: int = 30  # 模擬天數


class CapitalUpdate(BaseModel):
    """儲值/提款請求"""
    amount: float


# ============== Capital Endpoints ==============

@router.get("/capital")
async def get_capital():
    return get_capital_config()

@router.post("/capital/deposit")
async def deposit_capital(data: CapitalUpdate):
    cap = get_capital_config()
    cap["total_capital"] += data.amount
    cap["available_capital"] += data.amount
    save_capital_config(cap)
    return cap

@router.post("/capital/withdraw")
async def withdraw_capital(data: CapitalUpdate):
    cap = get_capital_config()
    # 允許扣除，即使造成負數（彈性運作），或可加檢查
    if cap["available_capital"] < data.amount:
         # 這裡可以警告但不強迫阻擋，或者強迫阻擋
         pass
    
    cap["total_capital"] -= data.amount
    cap["available_capital"] -= data.amount
    save_capital_config(cap)
    return cap


@router.get("/capital-status")
async def get_capital_status(db: AsyncSession = Depends(get_db)):
    cap = get_capital_config()
    total_capital = float(cap.get("total_capital", 0.0))
    
    # 計算模擬交易的已實現與未實現
    all_sim_result = await db.execute(select(Portfolio).where(Portfolio.is_simulated == True))
    all_sims = all_sim_result.scalars().all()
    
    open_sims = [p for p in all_sims if p.status == "open"]
    closed_sims = [p for p in all_sims if p.status != "open"]
    
    realized_profit = sum(float(p.realized_profit or 0) for p in closed_sims)
    unrealized_profit = sum(float(p.unrealized_profit or 0) for p in open_sims)
    open_cost = sum(float(p.entry_price * p.entry_quantity) for p in open_sims)
    
    current_equity = total_capital + realized_profit + unrealized_profit
    available_capital = total_capital + realized_profit - open_cost
    
    return {
        "configured_capital": total_capital,
        "realized_profit": realized_profit,
        "unrealized_profit": unrealized_profit,
        "current_equity": current_equity,
        "open_cost": open_cost,
        "available_capital": max(0.0, available_capital)
    }


# ============== Portfolio Summary Endpoint ==============

@router.get("/summary")
async def get_portfolio_summary(db: AsyncSession = Depends(get_db)):
    """
    取得 Portfolio 整體統計摘要
    供 AI 績效追蹤儀表板使用
    """
    # 查詢所有持倉
    all_result = await db.execute(select(Portfolio).order_by(desc(Portfolio.created_at)))
    all_positions = all_result.scalars().all()

    open_positions = [p for p in all_positions if p.status == "open"]
    closed_positions = [p for p in all_positions if p.status != "open"]

    # 未實現損益（持倉中）
    total_unrealized = sum(float(p.unrealized_profit or 0) for p in open_positions)

    # 已實現損益（已結束）
    total_realized = sum(float(p.realized_profit or 0) for p in closed_positions)

    # 勝率統計（依已結倉計算）
    wins = sum(1 for p in closed_positions if (p.realized_profit or 0) > 0)
    losses = sum(1 for p in closed_positions if (p.realized_profit or 0) <= 0)
    win_rate = round((wins / len(closed_positions) * 100), 2) if closed_positions else 0.0

    # 按來源分組統計（持倉中）
    source_breakdown: dict = {}
    for pos in open_positions:
        src = pos.analysis_source or "未知"
        if src not in source_breakdown:
            source_breakdown[src] = {"count": 0, "unrealized": 0.0}
        source_breakdown[src]["count"] += 1
        source_breakdown[src]["unrealized"] += float(pos.unrealized_profit or 0)

    return {
        "open_positions_count": len(open_positions),
        "closed_positions_count": len(closed_positions),
        "total_unrealized_profit": round(total_unrealized, 2),
        "total_realized_profit": round(total_realized, 2),
        "total_profit": round(total_unrealized + total_realized, 2),
        "win_rate": win_rate,
        "wins": wins,
        "losses": losses,
        "source_breakdown": source_breakdown,
    }


# ============== Portfolio Endpoints ==============

@router.get("/positions", response_model=List[PortfolioResponse])
async def get_positions(
    status: Optional[str] = Query(None, description="篩選狀態: open, closed, stopped, target_hit"),
    source: Optional[str] = Query(None, description="篩選分析來源"),
    simulated: Optional[bool] = Query(None, description="篩選是否為模擬"),
    db: AsyncSession = Depends(get_db)
):
    """取得持有股票列表"""
    query = select(Portfolio).order_by(desc(Portfolio.created_at))
    
    if status:
        query = query.where(Portfolio.status == status)
    if source:
        query = query.where(Portfolio.analysis_source == source)
    if simulated is not None:
        query = query.where(Portfolio.is_simulated == simulated)
    
    result = await db.execute(query)
    positions = result.scalars().all()
    
    return positions


@router.post("/positions/update-prices")
async def update_positions_prices(db: AsyncSession = Depends(get_db)):
    """
    即時更新所有持有中股票的現價和未實現損益
    優先使用 Fubon API，退而使用 yfinance（背景執行避免阻塞）
    """
    import asyncio
    import logging
    logger = logging.getLogger(__name__)

    # ① 先取得所有持倉代碼（快速 SELECT，立即釋放 session）
    result = await db.execute(
        select(Portfolio.symbol, Portfolio.id, Portfolio.entry_price, Portfolio.entry_quantity)
        .where(Portfolio.status == "open")
    )
    rows = result.all()

    if not rows:
        return {"message": "沒有持有中的股票", "updated": 0}

    symbols = list(set(r.symbol for r in rows))
    logger.info(f"🔄 更新 {len(symbols)} 檔股票的即時價格...")

    # ② 取得價格（先嘗試 Fubon API，再 yfinance）
    price_map: dict = {}

    # 2a. Fubon API（非阻塞，快取 5 秒）
    try:
        from fastapi import Request
        from fubon_client import fubon_client
        tasks = [fubon_client.get_quote(sym) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for sym, res in zip(symbols, results):
            if isinstance(res, dict) and res.get("price", 0) > 0:
                price_map[sym] = float(res["price"])
    except Exception as e:
        logger.debug(f"Fubon 批量報價: {e}")

    # 2b. yfinance 補足缺少的（改為背景執行避免阻塞事件循環）
    missing = [s for s in symbols if s not in price_map]
    if missing:
        def _fetch_yfinance(syms: list) -> dict:
            import yfinance as yf
            result = {}
            tw_syms = [f"{s}.TW" for s in syms]
            try:
                data = yf.download(tw_syms, period="1d", progress=False, threads=False, timeout=10)
                if not data.empty:
                    for s in syms:
                        try:
                            col = f"{s}.TW"
                            if len(tw_syms) == 1:
                                close = data["Close"].iloc[-1]
                            else:
                                close = data["Close"][col].iloc[-1] if col in data["Close"].columns else None
                            if close and float(close) > 0:
                                result[s] = float(close)
                        except Exception:
                            pass
            except Exception:
                pass
            # TWO fallback
            for s in syms:
                if s not in result:
                    try:
                        hist = yf.Ticker(f"{s}.TWO").history(period="1d")
                        if not hist.empty:
                            result[s] = float(hist.iloc[-1]["Close"])
                    except Exception:
                        pass
            return result

        try:
            extra = await asyncio.wait_for(
                asyncio.to_thread(_fetch_yfinance, missing),
                timeout=20.0
            )
            price_map.update(extra)
        except asyncio.TimeoutError:
            logger.warning("⏱️ yfinance 更新超時，使用部分結果")
        except Exception as e:
            logger.error(f"yfinance 更新失敗: {e}")

    logger.info(f"📊 取得 {len(price_map)}/{len(symbols)} 檔股票價格")

    if not price_map:
        return {"message": "未能取得任何價格", "updated": 0}

    # ③ 逐一更新資料庫（分批 commit，避免大事務鎖表）
    updated_count = 0
    updated_list = []

    for r in rows:
        if r.symbol not in price_map:
            continue
        try:
            pos_result = await db.execute(
                select(Portfolio).where(Portfolio.id == r.id)
            )
            position = pos_result.scalar_one_or_none()
            if not position:
                continue

            current_price = Decimal(str(price_map[r.symbol]))
            profit_info = position.calculate_profit(current_price)

            position.current_price = current_price
            position.unrealized_profit = Decimal(str(profit_info["profit"]))
            position.unrealized_profit_percent = Decimal(str(profit_info["percent"]))
            position.updated_at = datetime.utcnow()

            await db.commit()  # ✅ 逐筆 commit，避免長事務鎖死

            updated_count += 1
            updated_list.append({
                "symbol": r.symbol,
                "entry_price": float(r.entry_price),
                "current_price": float(current_price),
                "unrealized_profit": float(profit_info["profit"]),
                "unrealized_profit_percent": float(profit_info["percent"])
            })
        except Exception as e:
            await db.rollback()
            logger.error(f"更新 {r.symbol} 失敗: {e}")

    return {
        "message": f"已更新 {updated_count} 檔股票的即時價格",
        "updated": updated_count,
        "total_positions": len(rows),
        "timestamp": datetime.now().isoformat(),
        "positions": updated_list
    }




@router.get("/positions/open", response_model=List[PortfolioResponse])
async def get_open_positions(db: AsyncSession = Depends(get_db)):
    """取得所有持有中的股票"""
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.status == "open")
        .order_by(desc(Portfolio.entry_date))
    )
    return result.scalars().all()


@router.get("/positions/{portfolio_id}", response_model=PortfolioResponse)
async def get_position(portfolio_id: int, db: AsyncSession = Depends(get_db)):
    """取得單一持有紀錄"""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    position = result.scalar_one_or_none()
    
    if not position:
        raise HTTPException(status_code=404, detail="持有紀錄不存在")
    
    return position


@router.post("/positions", response_model=PortfolioResponse)
async def create_position(
    data: PortfolioCreate,
    db: AsyncSession = Depends(get_db)
):
    """新增持有股票"""
    # 🔧 使用富邦 API 獲取繁體中文股票名稱（禁用股票名稱表）
    try:
        from fubon_client import fubon_client
        stock_name_zh = await fubon_client.get_stock_name(data.symbol)
        # 如果富邦 API 返回代碼（未取得名稱），使用後備方案
        if stock_name_zh == data.symbol:
            import logging
            logging.getLogger(__name__).warning(f"富邦 API 未返回股票名稱，使用傳入值: {data.stock_name}")
            stock_name_zh = data.stock_name or data.symbol
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"獲取股票名稱失敗: {e}，使用傳入值")
        stock_name_zh = data.stock_name or data.symbol
    
    position = Portfolio(
        symbol=data.symbol,
        stock_name=stock_name_zh,  # 使用富邦 API 獲取的繁體名稱
        entry_date=data.entry_date,
        entry_price=Decimal(str(data.entry_price)),
        entry_quantity=data.entry_quantity,
        analysis_source=data.analysis_source,
        analysis_confidence=Decimal(str(data.analysis_confidence)) if data.analysis_confidence else None,
        analysis_details=data.analysis_details,
        stop_loss_price=Decimal(str(data.stop_loss_price)) if data.stop_loss_price else None,
        stop_loss_amount=Decimal(str(data.stop_loss_amount)) if data.stop_loss_amount else None,
        target_price=Decimal(str(data.target_price)) if data.target_price else None,
        is_simulated=data.is_simulated,
        notes=data.notes,
        status="open"
    )
    
    db.add(position)
    await db.flush()
    
    # 同時創建買入紀錄
    trade = TradeRecord(
        portfolio_id=position.id,
        symbol=data.symbol,
        stock_name=stock_name_zh,  # 使用富邦 API 獲取的繁體名稱
        trade_type="buy",
        trade_date=data.entry_date,
        price=Decimal(str(data.entry_price)),
        quantity=data.entry_quantity,
        total_amount=Decimal(str(data.entry_price * data.entry_quantity)),
        analysis_source=data.analysis_source,
        analysis_confidence=Decimal(str(data.analysis_confidence)) if data.analysis_confidence else None,
        analysis_details=data.analysis_details,
        is_simulated=data.is_simulated,
        notes=data.notes
    )
    
    db.add(trade)
    await db.commit()
    await db.refresh(position)
    
    # 發送買進 Email 通知
    try:
        from app.services.trade_email_notifier import trade_notifier
        await trade_notifier.send_buy_notification(
            symbol=data.symbol,
            stock_name=stock_name_zh,  # 使用富邦 API 獲取的繁體名稱
            entry_price=data.entry_price,
            quantity=data.entry_quantity,
            stop_loss=data.stop_loss_price,
            target_price=data.target_price,
            analysis_source=data.analysis_source,
            is_simulated=data.is_simulated
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"發送買進通知失敗: {e}")
    
    return position



@router.patch("/positions/{portfolio_id}", response_model=PortfolioResponse)
async def update_position(
    portfolio_id: int,
    data: PortfolioUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新持有股票資訊"""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    position = result.scalar_one_or_none()
    
    if not position:
        raise HTTPException(status_code=404, detail="持有紀錄不存在")
    
    if data.current_price is not None:
        position.current_price = Decimal(str(data.current_price))
        # 計算未實現損益
        profit_info = position.calculate_profit(Decimal(str(data.current_price)))
        position.unrealized_profit = Decimal(str(profit_info["profit"]))
        position.unrealized_profit_percent = Decimal(str(profit_info["percent"]))
    
    if data.stop_loss_price is not None:
        position.stop_loss_price = Decimal(str(data.stop_loss_price))
    
    if data.target_price is not None:
        position.target_price = Decimal(str(data.target_price))
    
    if data.notes is not None:
        position.notes = data.notes
    
    await db.commit()
    await db.refresh(position)
    
    return position


@router.post("/positions/{portfolio_id}/close", response_model=PortfolioResponse)
async def close_position(
    portfolio_id: int,
    data: PortfolioClose,
    db: AsyncSession = Depends(get_db)
):
    """結束持有（賣出）"""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    position = result.scalar_one_or_none()
    
    if not position:
        raise HTTPException(status_code=404, detail="持有紀錄不存在")
    
    if position.status != "open":
        raise HTTPException(status_code=400, detail="該持有紀錄已結束")
    
    # 計算實現損益
    exit_price = Decimal(str(data.exit_price))
    profit_info = position.calculate_profit(exit_price)
    
    # 判斷結束原因
    status = "closed"
    if position.stop_loss_price and exit_price <= position.stop_loss_price:
        status = "stopped"
    elif position.target_price and exit_price >= position.target_price:
        status = "target_hit"
    
    # 更新持有紀錄
    position.exit_date = data.exit_date
    position.exit_price = exit_price
    position.exit_reason = data.exit_reason
    position.realized_profit = Decimal(str(profit_info["profit"]))
    position.realized_profit_percent = Decimal(str(profit_info["percent"]))
    position.status = status
    
    if data.notes:
        position.notes = (position.notes or "") + "\n" + data.notes
    
    # 創建賣出紀錄
    trade = TradeRecord(
        portfolio_id=position.id,
        symbol=position.symbol,
        stock_name=position.stock_name,
        trade_type="sell",
        trade_date=data.exit_date,
        price=exit_price,
        quantity=position.entry_quantity,
        total_amount=exit_price * position.entry_quantity,
        analysis_source=position.analysis_source,
        analysis_confidence=position.analysis_confidence,
        profit=Decimal(str(profit_info["profit"])),
        profit_percent=Decimal(str(profit_info["percent"])),
        is_simulated=position.is_simulated,
        notes=data.exit_reason
    )
    
    db.add(trade)
    await db.commit()
    await db.refresh(position)
    
    # 發送平倉 Email 通知
    try:
        from app.services.trade_email_notifier import trade_notifier
        await trade_notifier.send_close_notification(
            symbol=position.symbol,
            stock_name=position.stock_name or position.symbol,
            entry_price=float(position.entry_price),
            exit_price=float(exit_price),
            quantity=int(position.entry_quantity),
            profit=profit_info["profit"],
            profit_percent=profit_info["percent"],
            reason=data.exit_reason or "手動平倉",
            status=status,
            is_simulated=position.is_simulated
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"發送平倉通知失敗: {e}")
    
    return position


@router.delete("/positions/{portfolio_id}")
async def delete_position(portfolio_id: int, db: AsyncSession = Depends(get_db)):
    """刪除持有紀錄"""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    position = result.scalar_one_or_none()
    
    if not position:
        raise HTTPException(status_code=404, detail="持有紀錄不存在")
    
    # 刪除相關交易紀錄
    await db.execute(
        delete(TradeRecord).where(TradeRecord.portfolio_id == portfolio_id)
    )
    
    await db.delete(position)
    await db.commit()
    
    return {"message": "持有紀錄已刪除"}


# ============== Trade Records Endpoints ==============

@router.get("/trades", response_model=List[TradeRecordResponse])
async def get_trades(
    symbol: Optional[str] = None,
    source: Optional[str] = None,
    trade_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db)
):
    """取得交易紀錄"""
    query = select(TradeRecord).order_by(desc(TradeRecord.trade_date))
    
    if symbol:
        query = query.where(TradeRecord.symbol == symbol)
    if source:
        query = query.where(TradeRecord.analysis_source == source)
    if trade_type:
        query = query.where(TradeRecord.trade_type == trade_type)
    if start_date:
        query = query.where(TradeRecord.trade_date >= start_date)
    if end_date:
        query = query.where(TradeRecord.trade_date <= end_date)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


# ============== Accuracy Analysis ==============

@router.get("/accuracy", response_model=List[AccuracyResponse])
async def get_accuracy_by_source(
    days: int = Query(30, description="統計天數"),
    db: AsyncSession = Depends(get_db)
):
    """取得各分析來源的準確性統計"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # 查詢已結束的持有紀錄
    result = await db.execute(
        select(Portfolio)
        .where(
            and_(
                Portfolio.status != "open",
                Portfolio.exit_date >= start_date
            )
        )
    )
    positions = result.scalars().all()
    
    # 按來源分組統計
    source_stats = {}
    for pos in positions:
        source = pos.analysis_source
        if source not in source_stats:
            source_stats[source] = {
                "total": 0,
                "wins": 0,
                "losses": 0,
                "total_profit": Decimal("0"),
                "profit_percents": [],
                "loss_percents": []
            }
        
        stats = source_stats[source]
        stats["total"] += 1
        
        if pos.realized_profit and pos.realized_profit > 0:
            stats["wins"] += 1
            stats["total_profit"] += pos.realized_profit
            if pos.realized_profit_percent:
                stats["profit_percents"].append(float(pos.realized_profit_percent))
        else:
            stats["losses"] += 1
            if pos.realized_profit:
                stats["total_profit"] += pos.realized_profit
            if pos.realized_profit_percent:
                stats["loss_percents"].append(float(pos.realized_profit_percent))
    
    # 計算準確率
    accuracy_list = []
    for source, stats in source_stats.items():
        win_rate = (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0
        avg_profit = sum(stats["profit_percents"]) / len(stats["profit_percents"]) if stats["profit_percents"] else None
        avg_loss = sum(stats["loss_percents"]) / len(stats["loss_percents"]) if stats["loss_percents"] else None
        
        accuracy_list.append(AccuracyResponse(
            analysis_source=source,
            total_trades=stats["total"],
            winning_trades=stats["wins"],
            losing_trades=stats["losses"],
            win_rate=round(win_rate, 2),
            net_profit=float(stats["total_profit"]),
            avg_profit_percent=round(avg_profit, 2) if avg_profit is not None else None,
            avg_loss_percent=round(avg_loss, 2) if avg_loss is not None else None
        ))
    
    # 按勝率排序
    accuracy_list.sort(key=lambda x: x.win_rate, reverse=True)
    
    return accuracy_list


@router.get("/daily-report")
async def get_daily_report(
    db: AsyncSession = Depends(get_db)
):
    """
    取得每日報表與投資組合總覽
    高效版本：只回傳必要的今日明細與歷史匯總數據
    """
    today = datetime.utcnow().date()
    # 注意：資料庫如果是 UTC 時間，這裡需要處理時區問題，假設資料庫存的是 UTC
    # 但為了簡化，這裡均以天為單位切分
    today_start = datetime.combine(today, datetime.min.time())
    
    # 1. 持有中倉位 (Holdings) - 完整列表
    open_result = await db.execute(
        select(Portfolio)
        .where(Portfolio.status == "open")
        .order_by(desc(Portfolio.entry_date))
    )
    holdings = open_result.scalars().all()
    
    # 2. 今日已平倉 (Today's Closed) - 完整列表
    # 包含 target_hit, stopped, closed
    today_closed_result = await db.execute(
        select(Portfolio)
        .where(
            and_(
                Portfolio.status != "open",
                Portfolio.exit_date >= today_start
            )
        )
        .order_by(desc(Portfolio.exit_date))
    )
    today_closed = today_closed_result.scalars().all()
    
    # 3. 歷史已平倉 (Previous Closed) - 僅聚合統計 (高效)
    # 計算今日之前的總損益與筆數
    prev_stats_result = await db.execute(
        select(
            func.sum(Portfolio.realized_profit),
            func.count(Portfolio.id)
        ).where(
            and_(
                Portfolio.status != "open",
                Portfolio.exit_date < today_start
            )
        )
    )
    prev_total_profit, prev_count = prev_stats_result.one()
    
    # 處理 None
    prev_total_profit = float(prev_total_profit or 0)
    prev_count = int(prev_count or 0)
    
    # 4. 計算統計數據
    today_profit = sum(float(p.realized_profit or 0) for p in today_closed)
    today_count = len(today_closed)
    
    # 持有中未實現損益
    unrealized_profit = sum(float(p.unrealized_profit or 0) for p in holdings)
    
    return {
        "summary": {
            "today_realized": round(today_profit, 0),
            "today_count": today_count,
            "previous_realized": round(prev_total_profit, 0),
            "previous_count": prev_count,
            "total_realized": round(today_profit + prev_total_profit, 0),
            "total_count": today_count + prev_count,
            "unrealized_profit": round(unrealized_profit, 0),
            "holdings_count": len(holdings)
        },
        "holdings": holdings,
        "today_closed": today_closed
    }


# ============== AI Simulation ==============

@router.post("/simulate")
async def simulate_trade(
    data: SimulationRequest,
    db: AsyncSession = Depends(get_db)
):
    """基於分析數據進行 AI 模擬交易"""
    from app.services.portfolio_simulator import simulate_trade_outcome
    
    try:
        result = await simulate_trade_outcome(
            symbol=data.symbol,
            analysis_source=data.analysis_source,
            entry_price=data.entry_price,
            entry_date=data.entry_date,
            target_price=data.target_price,
            stop_loss_price=data.stop_loss_price,
            simulation_days=data.simulation_days
        )
        
        # 如果模擬成功，創建模擬持有紀錄
        if result.get("success"):
            position = Portfolio(
                symbol=data.symbol,
                entry_date=data.entry_date,
                entry_price=Decimal(str(data.entry_price)),
                entry_quantity=1000,
                analysis_source=data.analysis_source,
                target_price=Decimal(str(data.target_price)) if data.target_price else None,
                stop_loss_price=Decimal(str(data.stop_loss_price)) if data.stop_loss_price else None,
                is_simulated=True,
                status="open" if not result.get("closed") else result.get("status", "closed"),
                notes=f"AI 模擬交易\n{result.get('summary', '')}"
            )
            
            if result.get("closed"):
                position.exit_date = result.get("exit_date")
                position.exit_price = Decimal(str(result.get("exit_price", 0)))
                position.realized_profit = Decimal(str(result.get("profit", 0)))
                position.realized_profit_percent = Decimal(str(result.get("profit_percent", 0)))
            else:
                position.current_price = Decimal(str(result.get("current_price", data.entry_price)))
                profit_info = position.calculate_profit(position.current_price)
                position.unrealized_profit = Decimal(str(profit_info["profit"]))
                position.unrealized_profit_percent = Decimal(str(profit_info["percent"]))
            
            db.add(position)
            await db.commit()
            await db.refresh(position)
            
            result["portfolio_id"] = position.id
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模擬交易失敗: {str(e)}")


@router.post("/auto-simulate")
async def auto_simulate_from_analysis(
    source: str = Query(..., description="分析來源: main_force, big_order, lstm_prediction 等"),
    days: int = Query(7, description="查詢最近幾天的分析"),
    db: AsyncSession = Depends(get_db)
):
    """
    自動從分析數據中提取信號並進行模擬交易
    用於檢驗分析準確性
    """
    from app.services.portfolio_simulator import auto_simulate_from_signals
    
    try:
        results = await auto_simulate_from_signals(
            db=db,
            source=source,
            days_back=days
        )
        
        return {
            "message": f"已模擬 {len(results)} 筆交易",
            "simulations": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"自動模擬失敗: {str(e)}")


# ============== 自動平倉監控 ==============

@router.post("/auto-close")
async def auto_close_positions(
    simulated_only: bool = Query(True, description="是否只監控模擬交易"),
    db: AsyncSession = Depends(get_db)
):
    """
    自動平倉監控
    
    檢查所有持倉，達到目標價或停損價時自動平倉
    
    平倉條件：
    1. 達到目標價（嚴格達標）- 標記為 target_hit
    2. 觸及停損價 - 標記為 stopped
    
    Args:
        simulated_only: 是否只監控模擬交易（預設 True）
    
    Returns:
        監控結果統計
    """
    try:
        result = await run_auto_close_monitor(db, simulated_only=simulated_only)
        
        return {
            "success": True,
            "message": f"監控完成：檢查 {result['checked']} 個持倉，平倉 {result['closed']} 個",
            "checked_count": result["checked"],
            "closed_count": result["closed"],
            "closed_details": result["details"],
            "timestamp": result["timestamp"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"自動平倉監控失敗: {str(e)}")


@router.get("/auto-close/status")
async def get_auto_close_status(
    simulated_only: bool = Query(True, description="是否只查看模擬交易"),
    db: AsyncSession = Depends(get_db)
):
    """
    查看需要監控的持倉狀態
    
    返回所有持有中的持倉，以及是否接近目標價/停損價
    """
    try:
        # 查詢所有持有中的持倉
        query = select(Portfolio).where(Portfolio.status == "open")
        
        if simulated_only:
            query = query.where(Portfolio.is_simulated == True)
        
        result = await db.execute(query)
        positions = result.scalars().all()
        
        status_list = []
        
        for pos in positions:
            # 計算距離目標價/停損價的百分比
            current_price = float(pos.current_price) if pos.current_price else float(pos.entry_price)
            
            target_distance = None
            stop_distance = None
            
            if pos.target_price:
                target_distance = (float(pos.target_price) - current_price) / current_price * 100
            
            if pos.stop_loss_price:
                stop_distance = (current_price - float(pos.stop_loss_price)) / current_price * 100
            
            status_list.append({
                "symbol": pos.symbol,
                "stock_name": pos.stock_name,
                "current_price": current_price,
                "entry_price": float(pos.entry_price),
                "target_price": float(pos.target_price) if pos.target_price else None,
                "stop_loss_price": float(pos.stop_loss_price) if pos.stop_loss_price else None,
                "target_distance_percent": round(target_distance, 2) if target_distance is not None else None,
                "stop_distance_percent": round(stop_distance, 2) if stop_distance is not None else None,
                "unrealized_profit": float(pos.unrealized_profit) if pos.unrealized_profit else 0,
                "unrealized_profit_percent": float(pos.unrealized_profit_percent) if pos.unrealized_profit_percent else 0,
                "is_simulated": pos.is_simulated,
                "will_close_on_target": pos.target_price and current_price >= float(pos.target_price),
                "will_close_on_stop": pos.stop_loss_price and current_price <= float(pos.stop_loss_price)
            })
        
        return {
            "success": True,
            "total_positions": len(status_list),
            "positions": status_list,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢狀態失敗: {str(e)}")


@router.get("/auto-close/scheduler-status")
async def get_auto_close_scheduler_status():
    """
    查詢自動平倉排程器狀態
    
    返回排程器運行狀態、最後檢查時間、統計數據等
    """
    try:
        from app.services.auto_close_scheduler import auto_close_scheduler
        return {
            "success": True,
            **auto_close_scheduler.get_status()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "is_running": False
        }


@router.post("/auto-close/scheduler-start")
async def start_auto_close_scheduler():
    """
    手動啟動自動平倉排程器
    """
    try:
        from app.services.auto_close_scheduler import auto_close_scheduler
        import asyncio
        
        if auto_close_scheduler.is_running:
            return {"success": False, "message": "排程器已經在運行中"}
        
        asyncio.create_task(auto_close_scheduler.start_scheduler())
        return {"success": True, "message": "自動平倉排程器已啟動"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-close/scheduler-stop")
async def stop_auto_close_scheduler():
    """
    手動停止自動平倉排程器
    """
    try:
        from app.services.auto_close_scheduler import auto_close_scheduler
        auto_close_scheduler.stop_scheduler()
        return {"success": True, "message": "自動平倉排程器已停止"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== 智能模擬交易器 ==============

@router.get("/smart-trader/status")
async def get_smart_trader_status():
    """
    查詢智能模擬交易器狀態
    """
    try:
        from app.services.smart_simulation_trader import smart_trader
        return {
            "success": True,
            **smart_trader.get_status()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "is_running": False
        }


@router.post("/smart-trader/start")
async def start_smart_trader():
    """
    啟動智能模擬交易器
    
    功能：
    - 自動監控高信心度 AI 信號並建倉
    - ORB（開盤區間突破）自動下單
    - 移動停利自動調整
    """
    try:
        from app.services.smart_simulation_trader import smart_trader
        import asyncio
        
        if smart_trader.is_running:
            return {"success": False, "message": "智能交易器已經在運行中"}
        
        asyncio.create_task(smart_trader.start_smart_trading())
        return {
            "success": True,
            "message": "智能模擬交易器已啟動",
            "features": [
                "自動監控高信心度 AI 信號",
                "ORB 開盤區間突破自動下單",
                "移動停利自動調整",
                "加碼/減碼機會偵測"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-trader/stop")
async def stop_smart_trader():
    """
    停止智能模擬交易器
    """
    try:
        from app.services.smart_simulation_trader import smart_trader
        smart_trader.stop_smart_trading()
        return {"success": True, "message": "智能模擬交易器已停止"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-trader/process-now")
async def process_signals_now():
    """
    立即處理信號（手動觸發）
    """
    try:
        from app.services.smart_simulation_trader import smart_trader
        result = await smart_trader.process_signals()
        return {
            "success": True,
            "message": f"處理完成：找到 {result['signals_found']} 個信號，開倉 {result['positions_opened']} 個",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/smart-trader/scale-opportunities")
async def get_scale_opportunities():
    """
    獲取加碼/減碼機會
    """
    try:
        from app.services.smart_simulation_trader import smart_trader
        opportunities = await smart_trader.check_scale_opportunities()
        return {
            "success": True,
            "scale_in_opportunities": opportunities["scale_in"],
            "scale_out_opportunities": opportunities["scale_out"],
            "total_opportunities": len(opportunities["scale_in"]) + len(opportunities["scale_out"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-trader/update-trailing-stops")
async def update_trailing_stops_now():
    """
    立即更新移動停利
    """
    try:
        from app.services.smart_simulation_trader import smart_trader
        updates = await smart_trader.update_trailing_stops()
        return {
            "success": True,
            "message": f"更新了 {len(updates)} 個移動停利",
            "updates": updates
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== 智能移動停利 v2.0 ==============

@router.post("/smart-trailing-stop/monitor")
async def run_smart_trailing_stop_monitor(
    simulated_only: bool = Query(True, description="是否只監控模擬交易"),
    db: AsyncSession = Depends(get_db)
):
    """
    執行智能移動停利監控
    
    功能：
    1. 追蹤持倉最高價
    2. 階梯式移動停利（保本 → 標準 → 緊縮）
    3. 自動平倉保護利潤
    4. Email 通知
    """
    try:
        from app.services.smart_trailing_stop import run_smart_trailing_stop
        result = await run_smart_trailing_stop(db, simulated_only=simulated_only)
        
        return {
            "success": True,
            "message": f"監控完成：更新 {result['updated']} 個停損，平倉 {result['closed']} 個",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/smart-trailing-stop/status")
async def get_smart_trailing_stop_status(
    simulated_only: bool = Query(True, description="是否只查看模擬交易"),
    db: AsyncSession = Depends(get_db)
):
    """
    查看智能移動停利狀態
    
    返回所有持倉的移動停利情況
    """
    try:
        from sqlalchemy import select
        from app.models.portfolio import Portfolio
        
        query = select(Portfolio).where(Portfolio.status == "open")
        if simulated_only:
            query = query.where(Portfolio.is_simulated == True)
        
        result = await db.execute(query)
        positions = result.scalars().all()
        
        status_list = []
        for pos in positions:
            entry_price = float(pos.entry_price)
            current_price = float(pos.current_price or entry_price)
            highest_price = float(pos.highest_price or entry_price)
            trailing_stop = float(pos.trailing_stop_price) if pos.trailing_stop_price else None
            
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            high_profit_pct = ((highest_price - entry_price) / entry_price) * 100
            
            status_list.append({
                "symbol": pos.symbol,
                "stock_name": pos.stock_name,
                "entry_price": entry_price,
                "current_price": current_price,
                "highest_price": highest_price,
                "profit_pct": round(profit_pct, 2),
                "high_profit_pct": round(high_profit_pct, 2),
                "original_stop_loss": float(pos.stop_loss_price) if pos.stop_loss_price else None,
                "trailing_stop_price": trailing_stop,
                "trailing_activated": pos.trailing_activated,
                "trailing_last_update": pos.trailing_last_update.isoformat() if pos.trailing_last_update else None,
                "is_simulated": pos.is_simulated,
                "trailing_level": (
                    "緊縮(-0.5%)" if high_profit_pct >= 5 else
                    "標準(-1%)" if high_profit_pct >= 3 else
                    "保本" if high_profit_pct >= 2 else
                    "未啟動"
                )
            })
        
        return {
            "success": True,
            "total_positions": len(status_list),
            "trailing_activated_count": len([s for s in status_list if s["trailing_activated"]]),
            "positions": status_list,
            "config": {
                "breakeven_threshold": "2%",
                "normal_trailing": "3%+ → -1%",
                "tight_trailing": "5%+ → -0.5%"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== 交易執行報告 ==============

@router.get("/execution-report/{position_id}")
async def get_execution_report(
    position_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    取得交易執行報告
    
    返回詳細的交易事件時間線和損益摘要
    """
    try:
        from app.services.trade_execution_report import TradeExecutionReportService
        from sqlalchemy import select
        from app.models.portfolio import Portfolio
        
        result = await db.execute(select(Portfolio).where(Portfolio.id == position_id))
        position = result.scalar_one_or_none()
        
        if not position:
            raise HTTPException(status_code=404, detail=f"找不到持倉 ID: {position_id}")
        
        report_service = TradeExecutionReportService(db)
        report = report_service.generate_execution_report(position)
        
        return {
            "success": True,
            **report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execution-report/{position_id}/send-email")
async def send_execution_report_email(
    position_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    手動發送交易執行報告 Email
    """
    try:
        from app.services.trade_execution_report import TradeExecutionReportService
        from sqlalchemy import select
        from app.models.portfolio import Portfolio
        
        result = await db.execute(select(Portfolio).where(Portfolio.id == position_id))
        position = result.scalar_one_or_none()
        
        if not position:
            raise HTTPException(status_code=404, detail=f"找不到持倉 ID: {position_id}")
        
        report_service = TradeExecutionReportService(db)
        success = await report_service.send_execution_report_email(position)
        
        if success:
            return {"success": True, "message": "交易執行報告已發送"}
        else:
            return {"success": False, "message": "發送失敗，請檢查 Email 設定"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== 每日交易報告郵件 ==============


logger = logging.getLogger(__name__)

async def send_daily_trade_report_email(trades: list, positions: list, summary: dict) -> bool:
    """發送每日交易報告郵件"""
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('EMAIL_USERNAME', '')
        sender_password = os.getenv('EMAIL_PASSWORD', '')
        recipients_str = os.getenv('EMAIL_RECIPIENTS', '')
        recipients = [r.strip() for r in recipients_str.split(',') if r.strip()]
        
        if not sender_email or not sender_password or not recipients:
            logger.warning("Email 設定不完整，跳過發送")
            return False
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 構建郵件內容
        subject = f"📊 每日交易報告 - {today} ({len(trades)} 筆交易)"
        
        # 組建交易表格 HTML
        trades_html = ""
        for trade in trades:
            profit_color = "#dc2626" if (trade.get('profit', 0) or 0) >= 0 else "#16a34a"
            profit_sign = "+" if (trade.get('profit', 0) or 0) >= 0 else ""
            trades_html += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 12px 8px; font-weight: bold;">{trade.get('symbol', '')} {trade.get('stock_name', '')}</td>
                <td style="padding: 12px 8px; text-align: center;">{trade.get('trade_type', '')}</td>
                <td style="padding: 12px 8px; text-align: right;">${trade.get('price', 0):.2f}</td>
                <td style="padding: 12px 8px; text-align: right;">{trade.get('quantity', 0)}</td>
                <td style="padding: 12px 8px; text-align: right; color: {profit_color}; font-weight: bold;">
                    {profit_sign}${trade.get('profit', 0) or 0:.0f}
                </td>
            </tr>
            """
        
        # 持倉狀態 HTML
        positions_html = ""
        for pos in positions[:5]:  # 最多顯示 5 筆
            profit = pos.get('unrealized_profit', 0) or 0
            profit_color = "#dc2626" if profit >= 0 else "#16a34a"
            profit_sign = "+" if profit >= 0 else ""
            positions_html += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 8px;">{pos.get('symbol', '')} {pos.get('stock_name', '')}</td>
                <td style="padding: 8px; text-align: right;">${pos.get('entry_price', 0):.2f}</td>
                <td style="padding: 8px; text-align: right;">${pos.get('current_price', 0):.2f}</td>
                <td style="padding: 8px; text-align: right; color: {profit_color}; font-weight: bold;">
                    {profit_sign}${profit:.0f}
                </td>
            </tr>
            """
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; padding: 24px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">📊 每日交易報告</h1>
                    <p style="margin: 8px 0 0; opacity: 0.9;">{today}</p>
                </div>
                
                <!-- Summary -->
                <div style="padding: 20px;">
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;">
                        <div style="background: #f3f4f6; padding: 16px; border-radius: 12px; text-align: center;">
                            <div style="font-size: 24px; font-weight: bold; color: #2563eb;">{summary.get('total_trades', 0)}</div>
                            <div style="font-size: 12px; color: #6b7280;">今日交易</div>
                        </div>
                        <div style="background: #dcfce7; padding: 16px; border-radius: 12px; text-align: center;">
                            <div style="font-size: 24px; font-weight: bold; color: #16a34a;">{summary.get('buy_trades', 0)}</div>
                            <div style="font-size: 12px; color: #6b7280;">買進</div>
                        </div>
                        <div style="background: #fee2e2; padding: 16px; border-radius: 12px; text-align: center;">
                            <div style="font-size: 24px; font-weight: bold; color: #dc2626;">{summary.get('sell_trades', 0)}</div>
                            <div style="font-size: 12px; color: #6b7280;">賣出</div>
                        </div>
                    </div>
                    
                    <!-- 今日交易 -->
                    <h3 style="margin: 20px 0 12px; color: #374151; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px;">📈 今日交易明細</h3>
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <thead>
                            <tr style="background: #f9fafb;">
                                <th style="padding: 12px 8px; text-align: left;">股票</th>
                                <th style="padding: 12px 8px; text-align: center;">類型</th>
                                <th style="padding: 12px 8px; text-align: right;">價格</th>
                                <th style="padding: 12px 8px; text-align: right;">數量</th>
                                <th style="padding: 12px 8px; text-align: right;">損益</th>
                            </tr>
                        </thead>
                        <tbody>
                            {trades_html if trades_html else '<tr><td colspan="5" style="text-align: center; padding: 20px; color: #9ca3af;">今日無交易</td></tr>'}
                        </tbody>
                    </table>
                    
                    <!-- 目前持倉 -->
                    <h3 style="margin: 24px 0 12px; color: #374151; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px;">💼 目前持倉 ({summary.get('open_positions', 0)} 筆)</h3>
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <thead>
                            <tr style="background: #f9fafb;">
                                <th style="padding: 8px; text-align: left;">股票</th>
                                <th style="padding: 8px; text-align: right;">進場價</th>
                                <th style="padding: 8px; text-align: right;">現價</th>
                                <th style="padding: 8px; text-align: right;">損益</th>
                            </tr>
                        </thead>
                        <tbody>
                            {positions_html if positions_html else '<tr><td colspan="4" style="text-align: center; padding: 16px; color: #9ca3af;">無持倉</td></tr>'}
                        </tbody>
                    </table>
                </div>
                
                <!-- Footer -->
                <div style="padding: 16px 24px; background: #f9fafb; text-align: center; color: #9ca3af; font-size: 12px;">
                    AI 主力監控平台 v3.0 | 此為自動發送報告
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        logger.info(f"✅ 每日交易報告已發送: {len(trades)} 筆交易")
        return True
        
    except Exception as e:
        logger.error(f"❌ 發送每日交易報告失敗: {e}")
        return False


@router.post("/daily-report/send")
async def send_daily_trade_report(
    db: AsyncSession = Depends(get_db)
):
    """
    發送今日交易報告郵件
    如果今日有交易記錄，發送郵件通知
    """
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # 查詢今日交易
    trades_query = select(TradeRecord).where(
        and_(
            TradeRecord.trade_date >= today_start,
            TradeRecord.trade_date <= today_end
        )
    ).order_by(desc(TradeRecord.trade_date))
    
    result = await db.execute(trades_query)
    trades = result.scalars().all()
    
    # 查詢持倉狀態
    positions_query = select(Portfolio).where(Portfolio.status == 'open')
    result = await db.execute(positions_query)
    positions = result.scalars().all()
    
    # 統計數據
    buy_trades = len([t for t in trades if t.trade_type == 'BUY'])
    sell_trades = len([t for t in trades if t.trade_type == 'SELL'])
    
    summary = {
        'total_trades': len(trades),
        'buy_trades': buy_trades,
        'sell_trades': sell_trades,
        'open_positions': len(positions)
    }
    
    # 如果沒有交易，返回但不發郵件
    if len(trades) == 0:
        return {
            "success": False,
            "message": "今日無交易記錄，不發送郵件",
            "summary": summary
        }
    
    # 轉換為字典
    trades_list = [
        {
            'symbol': t.symbol,
            'stock_name': t.stock_name,
            'trade_type': t.trade_type,
            'price': float(t.price),
            'quantity': t.quantity,
            'profit': float(t.profit) if t.profit else 0
        }
        for t in trades
    ]
    
    positions_list = [
        {
            'symbol': p.symbol,
            'stock_name': p.stock_name,
            'entry_price': float(p.entry_price),
            'current_price': float(p.current_price) if p.current_price else float(p.entry_price),
            'unrealized_profit': float(p.unrealized_profit) if p.unrealized_profit else 0
        }
        for p in positions
    ]
    
    # 發送郵件
    email_sent = await send_daily_trade_report_email(trades_list, positions_list, summary)
    
    return {
        "success": email_sent,
        "message": "每日交易報告已發送" if email_sent else "郵件發送失敗",
        "summary": summary,
        "trades_count": len(trades_list)
    }


@router.get("/daily-report/preview")
async def preview_daily_trade_report(
    db: AsyncSession = Depends(get_db)
):
    """
    預覽今日交易報告（不發送郵件）
    """
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # 查詢今日交易
    trades_query = select(TradeRecord).where(
        and_(
            TradeRecord.trade_date >= today_start,
            TradeRecord.trade_date <= today_end
        )
    ).order_by(desc(TradeRecord.trade_date))
    
    result = await db.execute(trades_query)
    trades = result.scalars().all()
    
    # 查詢持倉狀態
    positions_query = select(Portfolio).where(Portfolio.status == 'open')
    result = await db.execute(positions_query)
    positions = result.scalars().all()
    
    return {
        "date": str(today),
        "trades": [
            {
                "symbol": t.symbol,
                "stock_name": t.stock_name,
                "trade_type": t.trade_type,
                "price": float(t.price),
                "quantity": t.quantity,
                "profit": float(t.profit) if t.profit else 0,
                "trade_date": t.trade_date.isoformat()
            }
            for t in trades
        ],
        "positions": [
            {
                "symbol": p.symbol,
                "stock_name": p.stock_name,
                "entry_price": float(p.entry_price),
                "current_price": float(p.current_price) if p.current_price else float(p.entry_price),
                "unrealized_profit": float(p.unrealized_profit) if p.unrealized_profit else 0
            }
            for p in positions
        ],
        "summary": {
            "total_trades": len(trades),
            "buy_trades": len([t for t in trades if t.trade_type == 'BUY']),
            "sell_trades": len([t for t in trades if t.trade_type == 'SELL']),
            "open_positions": len(positions)
        }
    }
