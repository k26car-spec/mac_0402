#!/usr/bin/env python3
"""
自動平倉定時任務
Auto Close Scheduler

功能：
1. 每分鐘檢查一次所有模擬交易持倉
2. 達到目標價或停損價時自動平倉
3. 記錄平倉日誌

使用方式：
    python auto_close_scheduler.py

或使用 crontab 每分鐘執行：
    * * * * * cd /path/to/backend-v3 && python auto_close_scheduler.py >> logs/auto_close.log 2>&1
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.auto_close_monitor import run_auto_close_monitor


# 資料庫連線設定
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://Mac@localhost/ai_stock_db"
)

# 創建異步引擎
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def run_auto_close():
    """執行自動平倉監控"""
    print(f"\n{'='*60}")
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 開始自動平倉監控")
    print(f"{'='*60}")
    
    async with AsyncSessionLocal() as db:
        try:
            result = await run_auto_close_monitor(db, simulated_only=True)
            
            print(f"\n📊 監控結果：")
            print(f"   ✓ 檢查持倉數: {result['checked']}")
            print(f"   ✓ 平倉數量: {result['closed']}")
            
            if result['details']:
                print(f"\n💰 平倉詳情：")
                for detail in result['details']:
                    profit_sign = '+' if detail['profit'] >= 0 else ''
                    profit_color = '🔴' if detail['profit'] >= 0 else '🟢'
                    
                    print(f"\n   {profit_color} {detail['symbol']} {detail['stock_name']}")
                    print(f"      進場: ${detail['entry_price']:.2f}")
                    print(f"      出場: ${detail['exit_price']:.2f}")
                    print(f"      損益: {profit_sign}{detail['profit']:.0f} ({profit_sign}{detail['profit_percent']:.1f}%)")
                    print(f"      原因: {detail['reason']}")
                    print(f"      狀態: {detail['status']}")
            else:
                print(f"\n   ℹ️  沒有需要平倉的持倉")
            
            print(f"\n{'='*60}")
            print(f"✅ 監控完成")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            print(f"\n❌ 錯誤: {e}")
            import traceback
            traceback.print_exc()
            return None


async def main():
    """主函數"""
    try:
        result = await run_auto_close()
        
        # 如果有平倉，返回 0；否則返回 1（方便 crontab 判斷）
        if result and result['closed'] > 0:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  使用者中斷")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
