"""
智能移動停利服務 v2.0
Smart Trailing Stop Service

功能：
1. 追蹤持倉最高價格
2. 階梯式移動停利策略
3. 壓力位預警
4. Email 通知停損變動
5. 持久化最高價/移動停損到資料庫
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.portfolio import Portfolio, TradeRecord
from app.services.trade_execution_report import (
    TradeExecutionReportService,
    create_trailing_activated_event,
    create_trailing_updated_event,
    create_close_event
)

logger = logging.getLogger(__name__)


class TrailingStopConfig:
    """移動停利配置"""
    
    # 階梯式策略
    BREAKEVEN_THRESHOLD = 2.0      # 獲利 2% → 保本停損
    TRAILING_ACTIVATION = 3.0      # 獲利 3% → 啟動 -1% 移動停利
    TIGHT_TRAILING = 5.0           # 獲利 5% → -0.5% 緊縮停利
    
    # 移動距離
    TRAILING_DISTANCE_NORMAL = 1.0  # 標準移動距離 1%
    TRAILING_DISTANCE_TIGHT = 0.5   # 緊縮移動距離 0.5%
    
    # 預警設定
    RESISTANCE_WARNING_ZONE = 0.3   # 接近壓力位 ±0.3%


class SmartTrailingStopService:
    """智能移動停利服務"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.config = TrailingStopConfig()
        self.updates_count = 0
        self.closes_count = 0
    
    async def get_real_time_price(self, symbol: str) -> Optional[float]:
        """獲取即時股價（優先使用富邦 API）"""
        
        # 嘗試富邦 API
        try:
            from app.services.fubon_service import get_realtime_quote
            quote = await get_realtime_quote(symbol)
            if quote and quote.get('price', 0) > 0:
                return float(quote['price'])
        except Exception as e:
            logger.debug(f"富邦報價失敗 {symbol}: {e}")
        
        # 備援：yfinance
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(f"{symbol}.TW")
            hist = ticker.history(period="1d")
            
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            
            ticker = yf.Ticker(f"{symbol}.TWO")
            hist = ticker.history(period="1d")
            
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
                
        except Exception as e:
            logger.warning(f"獲取 {symbol} 價格失敗: {e}")
        
        return None
    
    def calculate_trailing_stop(
        self, 
        entry_price: float, 
        highest_price: float, 
        current_price: float,
        vix: float = 18.0  # 🆕 動態波動度參數
    ) -> Dict[str, Any]:
        """
        [AI 升級] 動態計算階梯式移動停損
        根據 VIX 波動率調整：波動越大，獲利保護越緊縮；波動越小，給予更多上漲空間。
        
        Returns:
            {
                'should_activate': bool,
                'trailing_stop_price': float,
                'trailing_distance': float,
                'level': str,  # 'breakeven' | 'normal' | 'tight'
                'reason': str
            }
        """
        profit_pct = ((current_price - entry_price) / entry_price) * 100
        high_profit_pct = ((highest_price - entry_price) / entry_price) * 100
        
        result = {
            'should_activate': False,
            'trailing_stop_price': None,
            'trailing_distance': 0,
            'level': None,
            'reason': '',
            'profit_pct': round(profit_pct, 2),
            'high_profit_pct': round(high_profit_pct, 2)
        }
        
        # 📈 [AI 動態判斷矩陣] 根據 VIX 動態調整參數
        vix_factor = 1.0
        if vix >= 25:
            vix_factor = 0.5  # 極端波動：所有防守距離縮小一半（快跑）
            reason_prefix = "⚠️ [高波避險]"
        elif vix >= 20:
            vix_factor = 0.7  # 波動加劇：防守距離打 7 折
            reason_prefix = "⚡️ [波動防護]"
        elif vix <= 15:
            vix_factor = 1.3  # 穩定趨勢：放寬 1.3 倍空間給股票跑
            reason_prefix = "✅ [穩健趨勢]"
        else:
            reason_prefix = "📊 [標準移動]"

        dynamic_tight_activation = self.config.TIGHT_TRAILING * (0.8 if vix >= 20 else 1.0)
        dynamic_normal_activation = self.config.TRAILING_ACTIVATION * (0.8 if vix >= 20 else 1.0)
        
        dynamic_tight_distance = self.config.TRAILING_DISTANCE_TIGHT * vix_factor
        dynamic_normal_distance = self.config.TRAILING_DISTANCE_NORMAL * vix_factor
        
        # 獲利 5%+ (或動態值)：緊縮移動停利
        if high_profit_pct >= dynamic_tight_activation:
            trailing_stop = highest_price * (1 - dynamic_tight_distance / 100)
            result.update({
                'should_activate': True,
                'trailing_stop_price': round(trailing_stop, 2),
                'trailing_distance': dynamic_tight_distance,
                'level': 'tight',
                'reason': f'{reason_prefix} 高點獲利 {high_profit_pct:.1f}%，緊縮停利 (-{dynamic_tight_distance:.2f}%)'
            })
        
        # 獲利 3-5% (或動態值)：標準移動停利
        elif high_profit_pct >= dynamic_normal_activation:
            trailing_stop = highest_price * (1 - dynamic_normal_distance / 100)
            result.update({
                'should_activate': True,
                'trailing_stop_price': round(trailing_stop, 2),
                'trailing_distance': dynamic_normal_distance,
                'level': 'normal',
                'reason': f'{reason_prefix} 高點獲利 {high_profit_pct:.1f}%，標準停利 (-{dynamic_normal_distance:.2f}%)'
            })
        
        # 獲利 2-3%：保本停損
        elif high_profit_pct >= self.config.BREAKEVEN_THRESHOLD:
            # 停損設在成本價 + 0.5% (涵蓋手續費)
            breakeven_price = entry_price * 1.005
            result.update({
                'should_activate': True,
                'trailing_stop_price': round(breakeven_price, 2),
                'trailing_distance': 0,
                'level': 'breakeven',
                'reason': f'{reason_prefix} 獲利 {high_profit_pct:.1f}%，啟動保本停損機制'
            })
        
        return result
    
    async def update_position_trailing_stop(
        self, 
        position: Portfolio, 
        current_price: float,
        vix: float = 18.0
    ) -> Optional[Dict[str, Any]]:
        """
        更新單一持倉的移動停利
        
        Returns:
            更新結果，如果有變動返回詳情
        """
        entry_price = float(position.entry_price)
        current_highest = float(position.highest_price or entry_price)
        
        # 更新最高價
        new_highest = max(current_highest, current_price)
        price_updated = new_highest > current_highest
        
        # 計算新的移動停損
        trailing_result = self.calculate_trailing_stop(
            entry_price=entry_price,
            highest_price=new_highest,
            current_price=current_price,
            vix=vix  # 傳遞 AI 獲取的波動度參數
        )
        
        update_result = None
        
        # 更新最高價
        if price_updated:
            position.highest_price = Decimal(str(new_highest))
            position.trailing_last_update = datetime.now()
        
        # 檢查是否需要更新移動停損
        if trailing_result['should_activate']:
            new_stop = trailing_result['trailing_stop_price']
            old_stop = float(position.trailing_stop_price or 0)
            was_activated = position.trailing_activated
            
            # 只有當新停損更高時才更新（停損只能上調，不能下調）
            if new_stop > old_stop:
                position.trailing_stop_price = Decimal(str(new_stop))
                position.trailing_activated = True
                position.trailing_last_update = datetime.now()
                
                update_result = {
                    'symbol': position.symbol,
                    'stock_name': position.stock_name,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'highest_price': new_highest,
                    'old_stop': old_stop,
                    'new_stop': new_stop,
                    'level': trailing_result['level'],
                    'reason': trailing_result['reason'],
                    'newly_activated': not was_activated,
                    'is_simulated': position.is_simulated
                }
                
                self.updates_count += 1
                
                # 🆕 記錄交易事件
                try:
                    if not was_activated:
                        # 首次啟動移動停利
                        create_trailing_activated_event(
                            position=position,
                            db=self.db,
                            current_price=current_price,
                            profit_pct=trailing_result['profit_pct'],
                            new_stop=new_stop
                        )
                    else:
                        # 更新移動停利
                        create_trailing_updated_event(
                            position=position,
                            db=self.db,
                            current_price=current_price,
                            new_stop=new_stop
                        )
                except Exception as e:
                    logger.warning(f"記錄交易事件失敗: {e}")
                
                # 發送 Email 通知（新啟動或大幅上調時）
                if not was_activated or (new_stop - old_stop) / entry_price > 0.01:
                    await self._send_trailing_update_email(update_result)
        
        return update_result
    
    async def check_trailing_stop_trigger(
        self, 
        position: Portfolio, 
        current_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        檢查是否觸發移動停損
        
        Returns:
            如果觸發，返回平倉詳情
        """
        if not position.trailing_activated or not position.trailing_stop_price:
            return None
        
        trailing_stop = float(position.trailing_stop_price)
        
        if current_price <= trailing_stop:
            # 觸發移動停損！
            entry_price = float(position.entry_price)
            quantity = int(position.entry_quantity)
            profit = (current_price - entry_price) * quantity
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            total_amount = current_price * quantity
            
            close_result = {
                'symbol': position.symbol,
                'stock_name': position.stock_name,
                'entry_price': entry_price,
                'exit_price': current_price,
                'trailing_stop': trailing_stop,
                'highest_price': float(position.highest_price or entry_price),
                'profit': profit,
                'profit_pct': round(profit_pct, 2),
                'reason': f'移動停損觸發（停損價 ${trailing_stop:.2f}）',
                'is_simulated': position.is_simulated
            }
            
            # 執行平倉 - 更新 portfolio
            position.exit_date = datetime.now()
            position.exit_price = Decimal(str(current_price))
            position.exit_reason = f"移動停損觸發 - 高點 ${float(position.highest_price):.2f} 回落"
            position.realized_profit = Decimal(str(profit))
            position.realized_profit_percent = Decimal(str(round(profit_pct, 2)))
            position.status = "trailing_stopped"
            
            self.closes_count += 1
            
            # ✅ 建立 TradeRecord（出場紀錄），確保交易歷史有記錄
            try:
                trade_record = TradeRecord(
                    portfolio_id=position.id,
                    symbol=position.symbol,
                    stock_name=position.stock_name,
                    trade_type="sell",
                    trade_date=datetime.now(),
                    price=Decimal(str(current_price)),
                    quantity=quantity,
                    total_amount=Decimal(str(total_amount)),
                    analysis_source="smart_trailing_stop",
                    analysis_confidence=Decimal("0.90"),
                    profit=Decimal(str(round(profit, 2))),
                    profit_percent=Decimal(str(round(profit_pct, 2))),
                    is_simulated=position.is_simulated,
                    notes=f"移動停損自動平倉 | 進場 ${entry_price:.2f} | 高點 ${float(position.highest_price or entry_price):.2f} | 停損 ${trailing_stop:.2f}"
                )
                self.db.add(trade_record)
                logger.info(f"✅ 已建立 TradeRecord: {position.symbol} sell @ {current_price:.2f} 損益 {profit_pct:+.2f}%")
            except Exception as e:
                logger.error(f"❌ 建立 TradeRecord 失敗 {position.symbol}: {e}")
            
            # 🆕 記錄平倉事件
            try:
                create_close_event(
                    position=position,
                    db=self.db,
                    exit_price=current_price,
                    exit_reason="跌破移動停損",
                    profit_pct=profit_pct
                )
            except Exception as e:
                logger.warning(f"記錄平倉事件失敗: {e}")
            
            # 🆕 發送完整交易執行報告 Email
            try:
                report_service = TradeExecutionReportService(self.db)
                await report_service.send_execution_report_email(position)
            except Exception as e:
                logger.warning(f"發送執行報告失敗: {e}")
            
            # 發送平倉 Email (備用通知)
            await self._send_trailing_close_email(close_result)
            
            logger.info(
                f"🛑 移動停損觸發: {position.symbol} | "
                f"進場 ${entry_price:.2f} → 出場 ${current_price:.2f} | "
                f"高點 ${float(position.highest_price):.2f} | "
                f"損益 {profit_pct:+.2f}%"
            )
            
            return close_result
        
        return None
    
    async def monitor_all_positions(self, simulated_only: bool = True) -> Dict[str, Any]:
        """
        監控所有持倉的移動停利
        
        Returns:
            監控結果統計
        """
        logger.info("🔍 開始智能移動停利監控...")
        
        # 查詢所有持有中的持倉
        query = select(Portfolio).where(Portfolio.status == "open")
        
        if simulated_only:
            query = query.where(Portfolio.is_simulated == True)
        
        result = await self.db.execute(query)
        positions = result.scalars().all()
        
        if not positions:
            return {
                "checked": 0,
                "updated": 0,
                "closed": 0,
                "details": []
            }
        
        logger.info(f"📊 監控 {len(positions)} 個持倉 (智能移動停利 AI 判斷中...)")
        
        # [AI 升級] 每輪監控只抓取一次當前整體市場 VIX
        def _get_current_vix():
            try:
                import yfinance as yf
                v = yf.Ticker('^VIX').history(period='1d')
                if not v.empty:
                    return float(v['Close'].iloc[-1])
            except Exception:
                pass
            return 18.0
        
        import asyncio
        current_vix = await asyncio.to_thread(_get_current_vix)
        logger.info(f"🛡️ AI 實時市場恐慌觀測: VIX = {current_vix:.2f}")

        update_details = []
        close_details = []
        
        for position in positions:
            try:
                current_price = await self.get_real_time_price(position.symbol)
                
                if current_price is None:
                    logger.warning(f"⚠️ {position.symbol} 無法獲取價格")
                    continue
                
                # 1. 更新當前價格和損益
                profit_info = position.calculate_profit(Decimal(str(current_price)))
                position.current_price = Decimal(str(current_price))
                position.unrealized_profit = Decimal(str(profit_info["profit"]))
                position.unrealized_profit_percent = Decimal(str(profit_info["percent"]))
                
                # 2. 檢查是否觸發移動停損
                close_result = await self.check_trailing_stop_trigger(position, current_price)
                if close_result:
                    close_details.append(close_result)
                    continue
                
                # 3. 更新移動停損 (注入 VIX)
                update_result = await self.update_position_trailing_stop(position, current_price, vix=current_vix)
                if update_result:
                    update_details.append(update_result)
                    
            except Exception as e:
                logger.error(f"❌ 處理 {position.symbol} 失敗: {e}")
                continue
        
        # 提交變更
        await self.db.commit()
        
        return {
            "checked": len(positions),
            "updated": len(update_details),
            "closed": len(close_details),
            "update_details": update_details,
            "close_details": close_details,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _send_trailing_update_email(self, update_result: Dict) -> bool:
        """發送移動停利更新通知"""
        try:
            from app.services.trade_email_notifier import trade_notifier
            
            subject = (
                f"{'🎮' if update_result['is_simulated'] else '📈'} "
                f"移動停利更新: {update_result['symbol']} → ${update_result['new_stop']:.2f}"
            )
            
            level_emoji = {
                'breakeven': '🔒 保本',
                'normal': '📊 標準',
                'tight': '🎯 緊縮'
            }.get(update_result['level'], '📈')
            
            body = f"""
            <h2>{level_emoji} 移動停利已更新</h2>
            <table style="border-collapse: collapse; width: 100%;">
                <tr><td style="padding: 8px; border: 1px solid #ddd;">股票代碼</td><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{update_result['symbol']}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;">股票名稱</td><td style="padding: 8px; border: 1px solid #ddd;">{update_result['stock_name']}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;">進場價格</td><td style="padding: 8px; border: 1px solid #ddd;">${update_result['entry_price']:.2f}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;">當前價格</td><td style="padding: 8px; border: 1px solid #ddd;">${update_result['current_price']:.2f}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;">最高價格</td><td style="padding: 8px; border: 1px solid #ddd; color: green;">${update_result['highest_price']:.2f}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;">舊停損價</td><td style="padding: 8px; border: 1px solid #ddd;">${update_result['old_stop']:.2f}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">新停損價</td><td style="padding: 8px; border: 1px solid #ddd; color: red; font-weight: bold;">${update_result['new_stop']:.2f}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;">策略</td><td style="padding: 8px; border: 1px solid #ddd;">{update_result['reason']}</td></tr>
            </table>
            <p style="color: gray; font-size: 12px; margin-top: 20px;">
                {'🎮 模擬交易' if update_result['is_simulated'] else '💰 實盤交易'} | 
                更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
            """
            
            # 整合多管道通知 (Telegram)
            from app.services.notification_manager import notification_manager
            tg_msg = f"""
{level_emoji} <b>移動停利已更新</b>
代碼：{update_result['symbol']} {update_result.get('stock_name', '')}
現價：${update_result['current_price']:.2f}
最高：${update_result['highest_price']:.2f}
舊停損：${update_result['old_stop']:.2f}
<b>新停損：${update_result['new_stop']:.2f}</b>
說明：{update_result['reason']}
"""
            notification_manager.send_to_all(tg_msg)
            
            return trade_notifier._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"發送移動停利更新通知失敗: {e}")
            return False
    
    async def _send_trailing_close_email(self, close_result: Dict) -> bool:
        """發送移動停損觸發通知"""
        try:
            from app.services.trade_email_notifier import trade_notifier
            
            profit_color = 'green' if close_result['profit'] > 0 else 'red'
            
            subject = (
                f"{'🎮' if close_result['is_simulated'] else '🛑'} "
                f"移動停損觸發: {close_result['symbol']} | "
                f"損益 {close_result['profit_pct']:+.2f}%"
            )
            
            body = f"""
            <h2>🛑 移動停損觸發 - 已平倉</h2>
            <table style="border-collapse: collapse; width: 100%;">
                <tr><td style="padding: 8px; border: 1px solid #ddd;">股票代碼</td><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{close_result['symbol']}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;">股票名稱</td><td style="padding: 8px; border: 1px solid #ddd;">{close_result['stock_name']}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;">進場價格</td><td style="padding: 8px; border: 1px solid #ddd;">${close_result['entry_price']:.2f}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;">持倉最高價</td><td style="padding: 8px; border: 1px solid #ddd; color: green;">${close_result['highest_price']:.2f}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;">觸發停損價</td><td style="padding: 8px; border: 1px solid #ddd; color: orange;">${close_result['trailing_stop']:.2f}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">出場價格</td><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">${close_result['exit_price']:.2f}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">損益</td><td style="padding: 8px; border: 1px solid #ddd; color: {profit_color}; font-weight: bold;">${close_result['profit']:+,.0f} ({close_result['profit_pct']:+.2f}%)</td></tr>
            </table>
            <p style="margin-top: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px;">
                💡 <strong>說明</strong>: 價格從最高點 ${close_result['highest_price']:.2f} 回落超過移動停損距離，
                系統自動執行平倉保護利潤。
            </p>
            <p style="color: gray; font-size: 12px; margin-top: 10px;">
                {'🎮 模擬交易' if close_result['is_simulated'] else '💰 實盤交易'} | 
                平倉時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
            """
            
            # 整合多管道通知 (Telegram)
            from app.services.notification_manager import notification_manager
            tg_msg = f"""
🛑 <b>移動停損觸發 - 已平倉</b>
代碼：{close_result['symbol']} {close_result.get('stock_name', '')}
出場價：${close_result['exit_price']:.2f} (觸發停損 ${close_result['trailing_stop']:.2f})
損益：<b>{close_result['profit_pct']:+.2f}%</b> (${close_result['profit']:+,.0f})
最高：${close_result['highest_price']:.2f}
說明：價格從最高點回落超過移動停損距離，系統自動執行平倉保護利潤。
"""
            notification_manager.send_to_all(tg_msg)
            
            return trade_notifier._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"發送移動停損觸發通知失敗: {e}")
            return False


async def run_smart_trailing_stop(db: AsyncSession, simulated_only: bool = True) -> Dict[str, Any]:
    """執行智能移動停利監控（便捷函數）"""
    service = SmartTrailingStopService(db)
    return await service.monitor_all_positions(simulated_only=simulated_only)
