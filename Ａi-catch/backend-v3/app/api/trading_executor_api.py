import os
import json
from fastapi import APIRouter
from pydantic import BaseModel
from app.database.connection import get_db, async_session
from app.models.portfolio import Portfolio
from sqlalchemy import select, desc

router = APIRouter()
VIRTUAL_DB_PATH = '/Users/Mac/Documents/ETF/AI/Ａi-catch/virtual_portfolio.json'

@router.get("/status")
async def get_trading_status():
    """獲取實盤執行官的當前狀態與持倉管理同步數據"""
    
    # 1. 讀取基礎配置
    try:
        import sys
        sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')
        from trading_executor import SIMULATION_MODE, TARGET_STOCKS
        mode = "Simulation (紙盤)" if SIMULATION_MODE else "Real Money (真倉)"
    except Exception:
        mode = "Unknown"
        TARGET_STOCKS = []

    # 2. 獲取本金配置
    total_capital = 0.0
    available_capital = 0.0
    cap_file = '/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/data/capital_config.json'
    if os.path.exists(cap_file):
        try:
            with open(cap_file, 'r') as f:
                cap_data = json.load(f)
                total_capital = float(cap_data.get("total_capital", 0))
                available_capital = float(cap_data.get("available_capital", 0))
        except: pass

    # 3. 核心：從資料庫同步持倉管理數據
    db_positions = []
    try:
        async with async_session() as db:
            # 查詢所有由 LSTM 或 AI 模擬產生的持倉
            stmt = select(Portfolio).where(
                Portfolio.analysis_source.in_(["lstm_prediction", "ai_simulation", "expert_signal"]),
                Portfolio.status == "open"
            ).order_by(desc(Portfolio.entry_date))
            
            result = await db.execute(stmt)
            positions_objs = result.scalars().all()
            
            for p in positions_objs:
                db_positions.append({
                    "symbol": p.symbol,
                    "stock_name": p.stock_name,
                    "quantity": p.entry_quantity,
                    "entry_price": float(p.entry_price),
                    "current_price": float(p.current_price) if p.current_price else None,
                    "stop_loss": float(p.stop_loss_price) if p.stop_loss_price else None,
                    "target": float(p.target_price) if p.target_price else None,
                    "pnl_percent": float(p.unrealized_profit_percent) if p.unrealized_profit_percent else 0.0,
                    "entry_date": p.entry_date.isoformat() if p.entry_date else None,
                })
    except Exception as e:
        print(f"資料庫讀取失敗: {e}")
        # 如果 DB 失敗，回退到 JSON 檔案
        if os.path.exists(VIRTUAL_DB_PATH):
            with open(VIRTUAL_DB_PATH, 'r') as f:
                json_data = json.load(f)
                for sym, v in json_data.items():
                    db_positions.append({
                        "symbol": sym, 
                        "quantity": v.get('shares', 0),
                        "entry_price": v.get('cost', 0),
                        "entry_date": v.get('buy_time')
                    })

    current_holding_cost = sum(p['quantity'] * p['entry_price'] for p in db_positions)
    equity = available_capital + current_holding_cost

    return {
        "success": True,
        "mode": mode,
        "target_stocks": TARGET_STOCKS,
        "financials": {
            "total_capital": total_capital,
            "available_capital": available_capital,
            "equity": equity,
            "win_rate": 0.0, 
            "current_holding_cost": current_holding_cost,
            "total_positions": len(db_positions),
            "unrealized_pnl": sum(p['quantity'] * (p['current_price'] - p['entry_price']) for p in db_positions if p.get('current_price')),
        },
        "portfolio": db_positions # 返回統一格式的 Array
    }

@router.post("/scan")
async def trigger_scan():
    """手動觸發一次完整的交易掃描循環"""
    try:
        import sys
        sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')
        from trading_executor import TradingExecutor
        
        executor = TradingExecutor()
        await executor.initialize()
        await executor.run_scan_cycle()
        
        return {"success": True, "message": "掃描循環觸發完成，請查看終端機日誌。"}
    except Exception as e:
        return {"success": False, "error": str(e)}
