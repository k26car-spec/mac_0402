"""
Portfolio Automation Service
自動化持有股票管理服務

功能：
1. 開市自動模擬 - 每天 9:00 執行
2. 收盤後自動更新 - 每天 13:30 執行
3. 即時信號自動建倉 - 偵測到高信心度信號時自動建立模擬持倉
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import yfinance as yf

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, update, and_

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 資料庫連接
DATABASE_URL = "postgresql+asyncpg://Mac@localhost/ai_stock_db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class PortfolioAutomation:
    """持有股票自動化管理"""
    
    # 高信心度門檻
    HIGH_CONFIDENCE_THRESHOLD = 0.75
    
    # 預設停損/目標設定
    DEFAULT_STOP_LOSS_PERCENT = 0.05  # 5%
    DEFAULT_TARGET_PERCENT = 0.08     # 8%
    
    def __init__(self):
        self.is_running = False
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """取得股票當前價格"""
        try:
            yf_symbol = symbol if ".TW" in symbol else f"{symbol}.TW"
            ticker = yf.Ticker(yf_symbol)
            
            # 取得最新報價
            info = ticker.info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            
            if not price:
                # 嘗試從歷史數據取得
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
            
            return float(price) if price else None
            
        except Exception as e:
            logger.warning(f"取得 {symbol} 價格失敗: {e}")
            # 嘗試上櫃股票
            try:
                yf_symbol = f"{symbol.replace('.TW', '')}.TWO"
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(period="1d")
                if not hist.empty:
                    return float(hist["Close"].iloc[-1])
            except:
                pass
            return None
    
    async def update_open_positions(self):
        """
        更新所有持有中持倉的當前價格和損益
        建議在收盤後執行 (13:30)
        """
        logger.info("🔄 開始更新持有中持倉的價格...")
        
        async with async_session() as session:
            from app.models.portfolio import Portfolio
            
            # 查詢所有持有中的持倉
            result = await session.execute(
                select(Portfolio).where(Portfolio.status == "open")
            )
            positions = result.scalars().all()
            
            updated_count = 0
            
            for pos in positions:
                try:
                    current_price = await self.get_current_price(pos.symbol)
                    
                    if current_price:
                        # 計算損益
                        profit = (current_price - float(pos.entry_price)) * pos.entry_quantity
                        profit_percent = ((current_price - float(pos.entry_price)) / float(pos.entry_price)) * 100
                        
                        # 更新持倉
                        pos.current_price = Decimal(str(current_price))
                        pos.unrealized_profit = Decimal(str(round(profit, 2)))
                        pos.unrealized_profit_percent = Decimal(str(round(profit_percent, 2)))
                        
                        updated_count += 1
                        logger.info(f"   ✅ {pos.symbol}: ${current_price:.2f} ({profit_percent:+.2f}%)")
                        
                        # 檢查是否觸及停損或目標
                        await self._check_auto_close(session, pos, current_price)
                        
                except Exception as e:
                    logger.error(f"   ❌ 更新 {pos.symbol} 失敗: {e}")
            
            await session.commit()
            logger.info(f"✅ 已更新 {updated_count}/{len(positions)} 個持倉")
            
            return {"updated": updated_count, "total": len(positions)}
    
    async def _check_auto_close(self, session: AsyncSession, position, current_price: float):
        """檢查是否應該自動結束持倉"""
        from app.models.portfolio import Portfolio, TradeRecord
        
        # 檢查停損
        if position.stop_loss_price and current_price <= float(position.stop_loss_price):
            await self._close_position(
                session, position, current_price, "stopped", "自動停損"
            )
            return
        
        # 檢查目標價
        if position.target_price and current_price >= float(position.target_price):
            await self._close_position(
                session, position, current_price, "target_hit", "達到目標價"
            )
            return
    
    async def _close_position(
        self, 
        session: AsyncSession, 
        position, 
        exit_price: float, 
        status: str, 
        reason: str
    ):
        """結束持倉"""
        from app.models.portfolio import TradeRecord
        
        profit = (exit_price - float(position.entry_price)) * position.entry_quantity
        profit_percent = ((exit_price - float(position.entry_price)) / float(position.entry_price)) * 100
        
        position.exit_date = datetime.now()
        position.exit_price = Decimal(str(exit_price))
        position.exit_reason = reason
        position.realized_profit = Decimal(str(round(profit, 2)))
        position.realized_profit_percent = Decimal(str(round(profit_percent, 2)))
        position.status = status
        
        # 創建賣出紀錄
        trade = TradeRecord(
            portfolio_id=position.id,
            symbol=position.symbol,
            stock_name=position.stock_name,
            trade_type="sell",
            trade_date=datetime.now(),
            price=Decimal(str(exit_price)),
            quantity=position.entry_quantity,
            total_amount=Decimal(str(exit_price * position.entry_quantity)),
            analysis_source=position.analysis_source,
            profit=Decimal(str(round(profit, 2))),
            profit_percent=Decimal(str(round(profit_percent, 2))),
            is_simulated=position.is_simulated,
            notes=reason
        )
        
        session.add(trade)
        
        logger.info(f"   📤 {position.symbol} {reason}: ${exit_price:.2f} ({profit_percent:+.2f}%)")
    
    async def run_morning_simulation(self):
        """
        開市自動模擬
        每天 9:00 執行，檢驗前幾天的分析信號準確性
        """
        logger.info("🌅 開始執行開市自動模擬...")
        
        from app.services.portfolio_simulator import auto_simulate_from_signals
        
        async with async_session() as session:
            results = []
            
            # 模擬各來源的信號
            for source in ["main_force", "lstm_prediction", "expert_signal"]:
                try:
                    logger.info(f"   🔍 模擬 {source} 信號...")
                    source_results = await auto_simulate_from_signals(
                        db=session,
                        source=source,
                        days_back=3  # 過去3天的信號
                    )
                    results.extend(source_results)
                    logger.info(f"      ✅ {source}: {len(source_results)} 筆模擬")
                except Exception as e:
                    logger.error(f"      ❌ {source} 模擬失敗: {e}")
            
            logger.info(f"✅ 開市模擬完成，共 {len(results)} 筆")
            
            return {"simulated": len(results), "results": results}
    
    async def auto_create_position_from_signal(
        self,
        symbol: str,
        stock_name: Optional[str],
        source: str,
        confidence: float,
        current_price: float,
        analysis_details: Optional[Dict] = None
    ) -> Optional[int]:
        """
        即時信號自動建倉
        當偵測到高信心度信號時自動建立模擬持倉
        
        Returns:
            position_id 如果成功建立，否則 None
        """
        # 檢查信心度門檻
        if confidence < self.HIGH_CONFIDENCE_THRESHOLD:
            return None
        
        logger.info(f"🎯 偵測到高信心度信號: {symbol} ({source}, {confidence:.2%})")
        
        async with async_session() as session:
            from app.models.portfolio import Portfolio, TradeRecord
            
            # 檢查是否已經有該股票的持倉
            existing = await session.execute(
                select(Portfolio).where(
                    and_(
                        Portfolio.symbol == symbol,
                        Portfolio.status == "open",
                        Portfolio.analysis_source == source
                    )
                )
            )
            if existing.scalar_one_or_none():
                logger.info(f"   ⏭️ {symbol} 已有持倉，跳過")
                return None
            
            # 計算停損和目標價
            stop_loss = current_price * (1 - self.DEFAULT_STOP_LOSS_PERCENT)
            target_price = current_price * (1 + self.DEFAULT_TARGET_PERCENT)
            
            # 建立持倉
            position = Portfolio(
                symbol=symbol,
                stock_name=stock_name,
                entry_date=datetime.now(),
                entry_price=Decimal(str(current_price)),
                entry_quantity=1000,
                analysis_source=source,
                analysis_confidence=Decimal(str(confidence)),
                analysis_details=analysis_details,
                stop_loss_price=Decimal(str(round(stop_loss, 2))),
                target_price=Decimal(str(round(target_price, 2))),
                current_price=Decimal(str(current_price)),
                unrealized_profit=Decimal("0"),
                unrealized_profit_percent=Decimal("0"),
                status="open",
                is_simulated=True,
                notes=f"自動建倉 - 信心度 {confidence:.2%}"
            )
            
            session.add(position)
            await session.flush()
            
            # 建立買入紀錄
            trade = TradeRecord(
                portfolio_id=position.id,
                symbol=symbol,
                stock_name=stock_name,
                trade_type="buy",
                trade_date=datetime.now(),
                price=Decimal(str(current_price)),
                quantity=1000,
                total_amount=Decimal(str(current_price * 1000)),
                analysis_source=source,
                analysis_confidence=Decimal(str(confidence)),
                analysis_details=analysis_details,
                is_simulated=True,
                notes=f"自動建倉 - 信心度 {confidence:.2%}"
            )
            
            session.add(trade)
            await session.commit()
            
            logger.info(f"   ✅ 自動建立 {symbol} 持倉: 進場 ${current_price:.2f}, 停損 ${stop_loss:.2f}, 目標 ${target_price:.2f}")
            
            return position.id
    
    async def calculate_all_accuracy(self) -> Dict[str, Any]:
        """計算所有分析來源的準確性"""
        from app.services.portfolio_simulator import calculate_source_accuracy
        
        async with async_session() as session:
            accuracy_results = {}
            
            for source in ["main_force", "lstm_prediction", "expert_signal", "big_order", "premarket"]:
                try:
                    result = await calculate_source_accuracy(session, source, days=30)
                    accuracy_results[source] = result
                except Exception as e:
                    logger.error(f"計算 {source} 準確性失敗: {e}")
            
            return accuracy_results


# 全局實例
portfolio_automation = PortfolioAutomation()


async def run_morning_tasks():
    """每天開市 (9:00) 執行的任務"""
    logger.info("=" * 50)
    logger.info("🌅 執行開市任務...")
    logger.info("=" * 50)
    
    await portfolio_automation.run_morning_simulation()
    
    logger.info("=" * 50)
    logger.info("✅ 開市任務完成")
    logger.info("=" * 50)


async def run_afternoon_tasks():
    """每天收盤 (13:30) 執行的任務"""
    logger.info("=" * 50)
    logger.info("🌇 執行收盤任務...")
    logger.info("=" * 50)
    
    # 更新所有持倉價格
    await portfolio_automation.update_open_positions()
    
    # 計算準確性
    accuracy = await portfolio_automation.calculate_all_accuracy()
    
    logger.info("\n📊 準確性統計:")
    for source, stats in accuracy.items():
        if stats.get("total_trades", 0) > 0:
            logger.info(f"   {source}: 勝率 {stats.get('win_rate', 0):.1f}%, 淨損益 ${stats.get('net_profit', 0):.2f}")
    
    logger.info("=" * 50)
    logger.info("✅ 收盤任務完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        task = sys.argv[1]
        
        if task == "morning":
            asyncio.run(run_morning_tasks())
        elif task == "afternoon":
            asyncio.run(run_afternoon_tasks())
        elif task == "update":
            asyncio.run(portfolio_automation.update_open_positions())
        elif task == "simulate":
            asyncio.run(portfolio_automation.run_morning_simulation())
        else:
            print(f"未知任務: {task}")
            print("可用任務: morning, afternoon, update, simulate")
    else:
        print("用法: python portfolio_automation.py [morning|afternoon|update|simulate]")
