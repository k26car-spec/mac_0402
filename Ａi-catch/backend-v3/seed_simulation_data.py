
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import random
from app.database.connection import AsyncSessionLocal
from app.models.portfolio import Portfolio, TradeRecord

async def seed_data():
    async with AsyncSessionLocal() as db:
        print("開始生成模擬交易訓練數據...")
        
        # 1. 2330 台積電 (持倉中，小賺) - 現價約 1810
        # 2. 2317 鴻海 (持倉中，小賺) - 現價約 224.5
        # 3. 2454 聯發科 (持倉中，平盤) - 現價約 1790
        # 4. 2603 長榮 (已獲利平倉) - 假設進場 175, 出場 185
        
        sim_data = [
            {
                "symbol": "2330", "name": "台積電", "status": "open",
                "entry_price": 1780, "current_price": 1810, "qty": 1000,
                "days_ago": 3, "hold_days": 0, "source": "main_force",
                "reason": "主力連續買超，均線多頭排列",
                "profit": 30000, "percent": 1.68
            },
            {
                "symbol": "2317", "name": "鴻海", "status": "open",
                "entry_price": 220, "current_price": 224.5, "qty": 2000,
                "days_ago": 1, "hold_days": 0, "source": "orb_breakout",
                "reason": "開盤帶量突破壓力區",
                "profit": 9000, "percent": 2.04
            },
            {
                "symbol": "2454", "name": "聯發科", "status": "open",
                "entry_price": 1785, "current_price": 1790, "qty": 1000,
                "days_ago": 0, "hold_days": 0, "source": "smart_entry",
                "reason": "回測支撐有守，嘗試進場",
                "profit": 5000, "percent": 0.28
            },
            {
                "symbol": "2603", "name": "長榮", "status": "target_hit",
                "entry_price": 175, "exit_price": 188, "qty": 1000,
                "days_ago": 5, "hold_days": 3, "source": "big_order",
                "reason": "達標獲利了結",
                "profit": 13000, "percent": 7.42
            }
        ]

        for item in sim_data:
            entry_date = datetime.now() - timedelta(days=item["days_ago"])
            
            # 構建 Portfolio
            p = Portfolio(
                symbol=item["symbol"],
                stock_name=item["name"],
                entry_date=entry_date,
                entry_price=Decimal(str(item["entry_price"])),
                entry_quantity=item["qty"],
                analysis_source=item["source"],
                analysis_confidence=Decimal("85.5"),
                is_simulated=True,
                status=item["status"],
                notes=f"AI 訓練: {item['reason']}",
                target_price=Decimal(str(item["entry_price"] * 1.1)),
                stop_loss_price=Decimal(str(item["entry_price"] * 0.95))
            )
            
            if item["status"] == "open":
                p.current_price = Decimal(str(item["current_price"]))
                p.unrealized_profit = Decimal(str(item["profit"]))
                p.unrealized_profit_percent = Decimal(str(item["percent"]))
            else:
                p.exit_date = entry_date + timedelta(days=item["hold_days"])
                p.exit_price = Decimal(str(item["exit_price"]))
                p.realized_profit = Decimal(str(item["profit"]))
                p.realized_profit_percent = Decimal(str(item["percent"]))
                p.exit_reason = item["reason"]

            db.add(p)
            await db.flush()

            # 構建買入記錄
            t_buy = TradeRecord(
                portfolio_id=p.id,
                symbol=item["symbol"],
                stock_name=item["name"],
                trade_type="buy",
                trade_date=entry_date,
                price=Decimal(str(item["entry_price"])),
                quantity=item["qty"],
                total_amount=Decimal(str(item["entry_price"] * item["qty"])),
                analysis_source=item["source"],
                is_simulated=True,
                notes=f"買進: {item['reason']}"
            )
            db.add(t_buy)

            # 如果已平倉，構建賣出記錄
            if item["status"] != "open":
                t_sell = TradeRecord(
                    portfolio_id=p.id,
                    symbol=item["symbol"],
                    stock_name=item["name"],
                    trade_type="sell",
                    trade_date=p.exit_date,
                    price=Decimal(str(item["exit_price"])),
                    quantity=item["qty"],
                    total_amount=Decimal(str(item["exit_price"] * item["qty"])),
                    analysis_source=item["source"],
                    profit=Decimal(str(item["profit"])),
                    profit_percent=Decimal(str(item["percent"])),
                    is_simulated=True,
                    notes=f"賣出: {item['reason']}"
                )
                db.add(t_sell)

        await db.commit()
        print(f"✅ 成功生成 {len(sim_data)} 筆模擬交易數據")

if __name__ == "__main__":
    try:
        asyncio.run(seed_data())
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
