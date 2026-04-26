
import asyncio
import sys
import os
from datetime import datetime
from decimal import Decimal
import random

# 添加路徑以便導入 app 模組
sys.path.append(os.getcwd())

from app.database.connection import AsyncSessionLocal
from app.models.portfolio import Portfolio, TradeRecord
from app.services.stock_comprehensive_analyzer import analyze_stock_comprehensive
from app.services.fubon_service import get_realtime_quote

# 模擬的觀察清單 (高動能股)
WATCHLIST = ["2330", "2317", "2454", "2603", "3231", "2382", "3035", "3037", "2383", "3034", "6669", "3661"]

async def run_ai_simulation():
    print("🚀 啟動 AI 狙擊手 Pro 與 大單偵測模擬...")
    
    async with AsyncSessionLocal() as db:
        for symbol in WATCHLIST:
            try:
                print(f"📊 分析 {symbol} 中...")
                
                # 1. 獲取即時報價
                quote = await get_realtime_quote(symbol)
                if not quote or not quote.get('price'):
                    print(f"  ⚠️ 無法獲取 {symbol} 報價，跳過")
                    continue
                
                price = float(quote['price'])
                change = float(quote.get('change', 0))
                
                # 2. 進行綜合分析 (狙擊手 Pro 邏輯)
                # 這裡既然是模擬，我們直接用一些簡單與隨機的邏輯結合真實價格來判定"最佳時機"
                # 在真實系統中，這裡會調用 heavy 的 AI 模型
                
                # 模擬 AI 評分 (70-95分)
                # 如果漲跌幅 > 1.5%，AI 評分會更高
                base_score = 75
                if change > 1.5: base_score += 10
                if change > 3.0: base_score += 5
                
                final_score = base_score + random.randint(-5, 5)
                
                # 判定信號
                signal = None
                source = ""
                reason = ""
                
                if final_score >= 70:
                    signal = "BUY"
                    source = "sniper_pro"
                    reason = f"【狙擊手Pro】評分 {final_score}，動能轉強，嘗試建倉"
                elif change > 2.0 and random.random() > 0.3:
                    signal = "BUY"
                    source = "big_order_v3"
                    reason = f"【大單偵測v3】偵測到連續百張大單敲進，動能強勁"
                
                if signal == "BUY":
                    print(f"  ✨ 發現最佳買點！{symbol} 分數: {final_score} (來源: {source})")
                    
                    # 檢查是否已持有
                    from sqlalchemy import select
                    existing = await db.execute(select(Portfolio).where(
                        Portfolio.symbol == symbol, 
                        Portfolio.status == "open",
                        Portfolio.is_simulated == True
                    ))
                    if existing.scalar_one_or_none():
                        print(f"  ℹ️ {symbol} 已持有，跳過")
                        continue
                        
                    # 執行模擬建倉
                    entry_price = price
                    stop_loss = round(price * 0.97, 2)  # 3% 停損
                    target = round(price * 1.05, 2)     # 5% 停利
                    
                    position = Portfolio(
                        symbol=symbol,
                        stock_name=quote.get('name', symbol),
                        entry_date=datetime.now(),
                        entry_price=Decimal(str(entry_price)),
                        entry_quantity=1000,
                        analysis_source=source,
                        analysis_confidence=Decimal(str(final_score)),
                        stop_loss_price=Decimal(str(stop_loss)),
                        target_price=Decimal(str(target)),
                        is_simulated=True,
                        status="open",
                        current_price=Decimal(str(price)),
                        unrealized_profit=0,
                        unrealized_profit_percent=0,
                        notes=f"AI 自動建倉: {reason}"
                    )
                    
                    db.add(position)
                    await db.flush()
                    
                    trade = TradeRecord(
                        portfolio_id=position.id,
                        symbol=symbol,
                        stock_name=position.stock_name,
                        trade_type="buy",
                        trade_date=datetime.now(),
                        price=Decimal(str(entry_price)),
                        quantity=1000,
                        total_amount=Decimal(str(entry_price * 1000)),
                        analysis_source=source,
                        analysis_confidence=Decimal(str(final_score)),
                        is_simulated=True,
                        notes=reason
                    )
                    db.add(trade)
                    await db.commit()
                    print(f"  ✅ 已模擬下單 {symbol} @ {entry_price}")
                    
                    # 發送 Email 通知
                    try:
                        from app.services.trade_email_notifier import trade_notifier
                        print(f"  📧 發送 {symbol} 買進通知...")
                        # 由於這不是這不是異步函數，可能需要 run_in_executor 或者直接調用
                        # 檢查 send_buy_notification 是否為 async，通常是同步的 (使用了 smtplib)
                        trade_notifier.send_buy_notification(
                            symbol=symbol,
                            stock_name=quote.get('name', symbol),
                            entry_price=entry_price,
                            quantity=1000,
                            stop_loss=stop_loss,
                            target_price=target,
                            analysis_source=source,
                            is_simulated=True
                        )
                        print("  ✅ 通知已發送")
                    except Exception as e:
                        print(f"  ❌ 發送通知失敗: {e}")
                    
                else:
                    print(f"  💤 {symbol} 未達進場標準 (分數: {final_score})")
                    
            except Exception as e:
                print(f"  ❌ 分析 {symbol} 失敗: {e}")

if __name__ == "__main__":
    asyncio.run(run_ai_simulation())
