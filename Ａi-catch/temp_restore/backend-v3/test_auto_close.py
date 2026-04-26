#!/usr/bin/env python3
"""
測試自動平倉功能
"""

import asyncio
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.auto_close_monitor import run_auto_close_monitor
import os

# 資料庫連線
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://Mac@localhost/ai_stock_db"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def test_auto_close():
    """測試自動平倉"""
    print("🧪 測試自動平倉功能...")
    print("="*60)
    
    async with AsyncSessionLocal() as db:
        try:
            # 執行自動平倉
            result = await run_auto_close_monitor(db, simulated_only=True)
            
            print(f"\n✅ 測試完成！")
            print(f"\n📊 結果：")
            print(f"   檢查持倉數: {result['checked']}")
            print(f"   平倉數量: {result['closed']}")
            
            if result['details']:
                print(f"\n💰 平倉詳情：")
                for detail in result['details']:
                    print(f"\n   {detail['symbol']} {detail['stock_name']}")
                    print(f"   進場: ${detail['entry_price']:.2f}")
                    print(f"   出場: ${detail['exit_price']:.2f}")
                    print(f"   損益: {detail['profit']:+.0f} ({detail['profit_percent']:+.1f}%)")
                    print(f"   原因: {detail['reason']}")
                    print(f"   狀態: {detail['status']}")
            else:
                print(f"\n   ℹ️  沒有需要平倉的持倉")
            
            print(f"\n{'='*60}\n")
            
        except Exception as e:
            print(f"\n❌ 錯誤: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_auto_close())
