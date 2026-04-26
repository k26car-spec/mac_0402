"""
自動平倉監控服務
Auto Close Monitor Service

功能：
1. 監控所有持倉（包括模擬交易）
2. 達到目標價時自動平倉
3. 達到停損價時自動平倉
4. 記錄平倉原因和詳細信息
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.portfolio import Portfolio, TradeRecord

logger = logging.getLogger(__name__)


class AutoCloseMonitor:
    """自動平倉監控器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.closed_count = 0
        self.checked_count = 0
    
    async def get_real_time_price(self, symbol: str) -> Optional[float]:
        """
        獲取即時股價 (優化版：使用富邦真實 API)
        """
        try:
            from project_root.fubon_client import fubon_client
        except:
            # 確保專案根目錄在 sys.path
            import sys
            sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')
            from fubon_client import fubon_client
            
        try:
            quote = await fubon_client.get_quote(symbol)
            if quote and quote.get('close'):
                return float(quote['close'])
            return None
        except Exception as e:
            logger.error(f"❌ 透過 Fubon 獲取 {symbol} 價格失敗: {e}")
            return None
    
    async def check_and_close_position(self, position: Portfolio) -> Optional[Dict[str, Any]]:
        """
        檢查單一持倉是否需要平倉
        
        平倉條件：
        1. 達到目標價（嚴格達標）
        2. 觸及停損價
        
        Returns:
            如果平倉成功，返回平倉詳情；否則返回 None
        """
        # 獲取即時價格
        current_price = await self.get_real_time_price(position.symbol)
        
        if current_price is None:
            logger.warning(f"⚠️ {position.symbol} 無法獲取價格，跳過檢查")
            return None
        
        current_price_decimal = Decimal(str(current_price))
        
        # 更新當前價格和未實現損益
        profit_info = position.calculate_profit(current_price_decimal)
        position.current_price = current_price_decimal
        position.unrealized_profit = Decimal(str(profit_info["profit"]))
        position.unrealized_profit_percent = Decimal(str(profit_info["percent"]))
        
        # 檢查是否需要平倉
        should_close = False
        close_reason = ""
        status = "closed"
        
        # 1. 檢查目標價（嚴格達標）
        if position.target_price and current_price_decimal >= position.target_price:
            should_close = True
            close_reason = f"達到目標價 ${float(position.target_price):.2f}"
            status = "target_hit"
            logger.info(f"🎯 {position.symbol} 達到目標價: ${current_price:.2f} >= ${float(position.target_price):.2f}")
        
        # 2. 檢查停損價
        elif position.stop_loss_price and current_price_decimal <= position.stop_loss_price:
            should_close = True
            close_reason = f"觸及停損價 ${float(position.stop_loss_price):.2f}"
            status = "stopped"
            logger.info(f"🛑 {position.symbol} 觸及停損: ${current_price:.2f} <= ${float(position.stop_loss_price):.2f}")
        
        if not should_close:
            return None
        
        # 執行平倉
        exit_date = datetime.utcnow()
        
        # 更新持倉狀態
        position.exit_date = exit_date
        position.exit_price = current_price_decimal
        position.exit_reason = f"自動平倉 - {close_reason}"
        position.realized_profit = Decimal(str(profit_info["profit"]))
        position.realized_profit_percent = Decimal(str(profit_info["percent"]))
        position.status = status
        
        # 創建賣出交易記錄
        trade = TradeRecord(
            portfolio_id=position.id,
            symbol=position.symbol,
            stock_name=position.stock_name,
            trade_type="sell",
            trade_date=exit_date,
            price=current_price_decimal,
            quantity=position.entry_quantity,
            total_amount=current_price_decimal * position.entry_quantity,
            analysis_source=position.analysis_source,
            analysis_confidence=position.analysis_confidence,
            profit=Decimal(str(profit_info["profit"])),
            profit_percent=Decimal(str(profit_info["percent"])),
            is_simulated=position.is_simulated,
            notes=f"自動平倉 - {close_reason}"
        )
        
        self.db.add(trade)
        self.closed_count += 1
        
        # 🆕 資本回流 (如果是模擬交易，將資金加回 available_capital)
        if position.is_simulated:
            try:
                import json, os
                CAPITAL_FILE = '/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/data/capital_config.json'
                if os.path.exists(CAPITAL_FILE):
                    with open(CAPITAL_FILE, 'r') as f:
                        cap_data = json.load(f)
                    recover_amount = float(current_price_decimal * position.entry_quantity)
                    cap_data["available_capital"] = float(cap_data.get("available_capital", 0)) + recover_amount
                    with open(CAPITAL_FILE, 'w') as f:
                        json.dump(cap_data, f)
                    logger.info(f"💰 [資本回流] 已將 {recover_amount:.0f} 元加回可用餘額。")
            except Exception as e:
                logger.error(f"❌ 資本回流更新失敗: {e}")
        
        # 發送平倉 Email 通知
        try:
            from app.services.trade_email_notifier import trade_notifier
            await trade_notifier.send_close_notification(
                symbol=position.symbol,
                stock_name=position.stock_name or position.symbol,
                entry_price=float(position.entry_price),
                exit_price=current_price,
                quantity=int(position.entry_quantity),
                profit=profit_info["profit"],
                profit_percent=profit_info["percent"],
                reason=close_reason,
                status=status,
                is_simulated=position.is_simulated
            )
        except Exception as e:
            logger.error(f"發送平倉通知失敗: {e}")
        
        return {
            "symbol": position.symbol,
            "stock_name": position.stock_name,
            "entry_price": float(position.entry_price),
            "exit_price": current_price,
            "profit": profit_info["profit"],
            "profit_percent": profit_info["percent"],
            "reason": close_reason,
            "status": status,
            "is_simulated": position.is_simulated
        }
    
    async def monitor_all_positions(self, simulated_only: bool = True) -> Dict[str, Any]:
        """
        監控所有持倉並自動平倉
        
        Args:
            simulated_only: 是否只監控模擬交易（預設 True）
        
        Returns:
            監控結果統計
        """
        logger.info("🔍 開始自動平倉監控...")
        
        # 查詢所有持有中的持倉
        query = select(Portfolio).where(Portfolio.status == "open")
        
        if simulated_only:
            query = query.where(Portfolio.is_simulated == True)
        
        result = await self.db.execute(query)
        positions = result.scalars().all()
        
        if not positions:
            logger.info("✅ 沒有需要監控的持倉")
            return {
                "checked": 0,
                "closed": 0,
                "details": []
            }
        
        logger.info(f"📊 找到 {len(positions)} 個持倉需要檢查")
        
        closed_details = []
        
        for position in positions:
            self.checked_count += 1
            
            try:
                result = await self.check_and_close_position(position)
                
                if result:
                    closed_details.append(result)
                    logger.info(
                        f"✅ 自動平倉: {result['symbol']} {result['stock_name']} | "
                        f"進場: ${result['entry_price']:.2f} → 出場: ${result['exit_price']:.2f} | "
                        f"損益: {result['profit']:+.0f} ({result['profit_percent']:+.1f}%) | "
                        f"原因: {result['reason']}"
                    )
            
            except Exception as e:
                logger.error(f"❌ 檢查 {position.symbol} 時發生錯誤: {e}")
                continue
        
        # 提交所有變更
        if closed_details:
            await self.db.commit()
            logger.info(f"💾 已提交 {len(closed_details)} 筆平倉記錄")
        
        return {
            "checked": self.checked_count,
            "closed": self.closed_count,
            "details": closed_details,
            "timestamp": datetime.now().isoformat()
        }


async def run_auto_close_monitor(db: AsyncSession, simulated_only: bool = True) -> Dict[str, Any]:
    """
    執行自動平倉監控（便捷函數）
    
    Args:
        db: 資料庫 session
        simulated_only: 是否只監控模擬交易
    
    Returns:
        監控結果
    """
    monitor = AutoCloseMonitor(db)
    return await monitor.monitor_all_positions(simulated_only=simulated_only)
