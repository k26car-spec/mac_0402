#!/usr/bin/env python3
"""
修復持倉股票名稱 - 將英文名稱改為繁體中文
使用富邦 API 獲取正確的股票名稱
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend-v3'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.portfolio import Portfolio, TradeRecord
from fubon_client import fubon_client
import logging
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 數據庫連接（從環境變數或使用默認值）
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://Mac@localhost/ai_stock_db")
logger.info(f"🔗 使用數據庫: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

async def fix_stock_names():
    """修復所有持倉的股票名稱"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. 獲取所有持倉
        result = await session.execute(select(Portfolio))
        positions = result.scalars().all()
        
        logger.info(f"📊 找到 {len(positions)} 筆持倉記錄")
        
        updated_count = 0
        for pos in positions:
            # 檢查是否為英文名稱或需要更新
            if not pos.stock_name or pos.stock_name == pos.symbol or pos.stock_name.isascii():
                try:
                    # 使用富邦 API 獲取繁體中文名稱
                    stock_name_zh = await fubon_client.get_stock_name(pos.symbol)
                    
                    if stock_name_zh and stock_name_zh != pos.symbol:
                        old_name = pos.stock_name
                        pos.stock_name = stock_name_zh
                        updated_count += 1
                        logger.info(f"✅ {pos.symbol}: {old_name} → {stock_name_zh}")
                    else:
                        logger.warning(f"⚠️  {pos.symbol}: 富邦 API 未返回名稱")
                except Exception as e:
                    logger.error(f"❌ {pos.symbol}: 獲取名稱失敗 - {e}")
        
        # 2. 更新交易記錄
        trade_result = await session.execute(select(TradeRecord))
        trades = trade_result.scalars().all()
        
        logger.info(f"📊 找到 {len(trades)} 筆交易記錄")
        
        trade_updated = 0
        for trade in trades:
            if not trade.stock_name or trade.stock_name == trade.symbol or trade.stock_name.isascii():
                try:
                    stock_name_zh = await fubon_client.get_stock_name(trade.symbol)
                    
                    if stock_name_zh and stock_name_zh != trade.symbol:
                        old_name = trade.stock_name
                        trade.stock_name = stock_name_zh
                        trade_updated += 1
                        logger.info(f"✅ 交易 {trade.id} ({trade.symbol}): {old_name} → {stock_name_zh}")
                except Exception as e:
                    logger.error(f"❌ 交易 {trade.id}: 獲取名稱失敗 - {e}")
        
        # 提交修改
        await session.commit()
        
        logger.info(f"\n🎉 修復完成！")
        logger.info(f"   持倉更新: {updated_count} 筆")
        logger.info(f"   交易更新: {trade_updated} 筆")

if __name__ == "__main__":
    asyncio.run(fix_stock_names())
