import asyncio
import json
import os
import sys
from datetime import datetime
from decimal import Decimal

# Add current directory to path
sys.path.append(os.getcwd())

from app.database.connection import init_db, AsyncSessionLocal
from app.models.portfolio import Portfolio, TradeRecord

async def restore_data():
    print("🔄 Initializing Database...")
    await init_db()
    
    print("📂 Reading backup files...")
    
    # Paths to restore from
    restore_dir = "temp_restore/backend-v3/data"
    reviews_path = os.path.join(restore_dir, "trade_reviews.json")
    perf_path = os.path.join(restore_dir, "ai_performance.json")
    
    trades_to_restore = []
    
    # 1. Read Trade Reviews
    if os.path.exists(reviews_path):
        with open(reviews_path, 'r') as f:
            data = json.load(f)
            print(f"  Found {len(data.get('reviews', []))} reviews")
            trades_to_restore.extend(data.get('reviews', []))
            
    # 2. Read AI Performance (deduplicate by symbol/date if possible, but for now just add)
    # Note: simple logic, assume reviews covers most
    
    async with AsyncSessionLocal() as db:
        count = 0
        for item in trades_to_restore:
            symbol = item.get("symbol")
            if not symbol: continue
            
            # Parse dates
            entry_date_str = item.get("entry_date")
            entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d") if entry_date_str else datetime.now()
            
            # Create Portfolio (Closed)
            p = Portfolio(
                id=int(datetime.now().timestamp() * 1000) + count, # Unique ID
                symbol=symbol,
                stock_name=item.get("stock_name", symbol),
                entry_date=entry_date,
                entry_price=Decimal(str(item.get("entry_price", 0))),
                entry_quantity=1000,
                analysis_source=item.get("signal_source", "unknown"),
                stop_loss_price=Decimal(str(item.get("stop_loss", 0))),
                target_price=Decimal(str(item.get("target_price", 0))),
                is_simulated=True, # Assuming recovered trades are simulated/historical
                status="closed",
                exit_date=datetime.now(), # Approximate if missing
                exit_price=Decimal(str(item.get("exit_price", 0))),
                realized_profit_percent=Decimal(str(item.get("pnl_percent", 0))),
                notes="Restored from backup"
            )
            
            # Calculate logic profit
            if p.exit_price and p.entry_price:
                 p.realized_profit = (p.exit_price - p.entry_price) * 1000
            
            db.add(p)
            await db.flush()
            
            # Create Buy Record
            t_buy = TradeRecord(
                portfolio_id=p.id,
                symbol=symbol,
                trade_type="buy",
                trade_date=entry_date,
                price=p.entry_price,
                quantity=1000,
                total_amount=p.entry_price * 1000,
                analysis_source=p.analysis_source,
                is_simulated=True,
                notes="Restored Buy"
            )
            db.add(t_buy)
            
            # Create Sell Record
            t_sell = TradeRecord(
                portfolio_id=p.id,
                symbol=symbol,
                trade_type="sell",
                trade_date=datetime.now(),
                price=p.exit_price,
                quantity=1000,
                total_amount=p.exit_price * 1000,
                analysis_source=p.analysis_source,
                is_simulated=True,
                notes="Restored Sell"
            )
            db.add(t_sell)
            
            count += 1
            
        await db.commit()
        print(f"✅ Successfully restored {count} trades to SQLite database!")

if __name__ == "__main__":
    asyncio.run(restore_data())
