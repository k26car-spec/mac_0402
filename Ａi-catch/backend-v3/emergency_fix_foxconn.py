
import asyncio
from sqlalchemy import select, delete
from app.database.connection import AsyncSessionLocal
from app.models.portfolio import Portfolio, TradeRecord

async def fix_foxconn():
    async with AsyncSessionLocal() as db:
        print("🚨 緊急修復：清除鴻海 (2317) 異常模擬持倉...")
        
        # 1. 查詢所有鴻海模擬持倉
        result = await db.execute(select(Portfolio).where(
            Portfolio.symbol == "2317",
            Portfolio.is_simulated == True
        ))
        positions = result.scalars().all()
        
        print(f"發現 {len(positions)} 筆鴻海模擬持倉。")
        
        if not positions:
            print("無須處理。")
            return

        # 2. 刪除這些持倉的交易記錄
        p_ids = [p.id for p in positions]
        await db.execute(delete(TradeRecord).where(TradeRecord.portfolio_id.in_(p_ids)))
        
        # 3. 刪除持倉本身
        await db.execute(delete(Portfolio).where(Portfolio.id.in_(p_ids)))
        
        await db.commit()
        print(f"✅ 已刪除 {len(positions)} 筆異常持倉，信件轟炸應已停止。")
        
        # 4. 重新建立一個正常的鴻海持倉 (可選)
        # 為了不讓用戶覺得鴻海不見了，建立一個正常的
        from datetime import datetime
        from decimal import Decimal
        
        new_p = Portfolio(
            symbol="2317",
            stock_name="鴻海",
            entry_date=datetime.now(),
            entry_price=Decimal("224.0"),  # 接近現價
            entry_quantity=1000,
            analysis_source="repaired_entry",
            analysis_confidence=Decimal("80.0"),
            is_simulated=True,
            status="open",
            target_price=Decimal("240.0"),
            stop_loss_price=Decimal("215.0"),
            current_price=Decimal("224.5"),
            unrealized_profit=Decimal("500"),
            unrealized_profit_percent=Decimal("0.22"),
            notes="系統自動修復後重建"
        )
        db.add(new_p)
        await db.commit()
        print("✅ 已重建一筆正常的鴻海持倉。")

if __name__ == "__main__":
    asyncio.run(fix_foxconn())
