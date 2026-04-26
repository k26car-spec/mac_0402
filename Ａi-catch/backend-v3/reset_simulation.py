
import asyncio
from sqlalchemy import delete
from app.database.connection import AsyncSessionLocal
from app.models.portfolio import Portfolio, TradeRecord, AnalysisAccuracy

async def reset_simulation():
    async with AsyncSessionLocal() as db:
        print("🧹 開始清理所有模擬交易數據，準備明日實戰測試...")
        
        # 1. 刪除模擬交易記錄
        result = await db.execute(delete(TradeRecord).where(TradeRecord.is_simulated == True))
        print(f"  - 已刪除 {result.rowcount} 筆交易記錄")
        
        # 2. 刪除模擬持倉
        result = await db.execute(delete(Portfolio).where(Portfolio.is_simulated == True))
        print(f"  - 已刪除 {result.rowcount} 筆模擬持倉")
        
        # 3. (可選) 清空分析準確度統計 (讓勝率從零開始計算)
        # 如果您希望保留過去的統計，請註解掉這行
        # result = await db.execute(delete(AnalysisAccuracy))
        # print(f"  - 已重置分析準確度統計")
        
        await db.commit()
        print("✅ 系統已歸零重置完成！")
        print("📅 系統將於明日 (交易日) 09:00 自動啟動盤中模擬交易。")

if __name__ == "__main__":
    asyncio.run(reset_simulation())
