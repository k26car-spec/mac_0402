"""
交易執行報告服務
Trade Execution Report Service

功能：
1. 追蹤交易過程中的所有事件
2. 生成詳細執行報告
3. 平倉時自動發送 Email 報告
"""

import logging
import smtplib
import os
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class TradeEvent:
    """交易事件類型"""
    OPEN = "open"                      # 開倉
    TRAILING_ACTIVATED = "trailing_activated"  # 移動停利啟動
    TRAILING_UPDATED = "trailing_updated"      # 移動停利更新
    HIGH_UPDATED = "high_updated"      # 最高價更新
    TRAILING_TRIGGERED = "trailing_triggered"  # 移動停損觸發
    STOP_LOSS = "stop_loss"            # 固定停損觸發
    TARGET_HIT = "target_hit"          # 目標達成
    MANUAL_CLOSE = "manual_close"      # 手動平倉


class TradeExecutionReportService:
    """交易執行報告服務"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def add_trade_event(
        self, 
        position: Portfolio, 
        event_type: str, 
        price: float,
        description: str,
        details: Optional[Dict] = None
    ) -> Dict:
        """
        新增交易事件
        
        Args:
            position: Portfolio 持倉物件
            event_type: 事件類型
            price: 當時價格
            description: 事件說明
            details: 額外詳情
        
        Returns:
            新增的事件物件
        """
        # 初始化事件列表
        if position.trade_events is None:
            position.trade_events = {"events": []}
        elif "events" not in position.trade_events:
            position.trade_events = {"events": []}
        
        event = {
            "time": datetime.now().strftime("%H:%M"),
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "price": price,
            "description": description,
            "details": details or {}
        }
        
        # 建立新的字典來觸發 SQLAlchemy 變更偵測
        new_events = dict(position.trade_events)
        new_events["events"] = list(new_events.get("events", [])) + [event]
        position.trade_events = new_events
        
        logger.info(f"📝 {position.symbol} 新增事件: {event_type} - {description}")
        return event
    
    def generate_execution_report(self, position: Portfolio) -> Dict:
        """
        生成交易執行報告
        
        Returns:
            {
                "symbol": str,
                "stock_name": str,
                "entry_date": str,
                "exit_date": str,
                "events": [...],
                "summary": {...},
                "html_table": str
            }
        """
        events = []
        if position.trade_events and "events" in position.trade_events:
            events = position.trade_events["events"]
        
        # 計算損益
        entry_price = float(position.entry_price)
        exit_price = float(position.exit_price) if position.exit_price else float(position.current_price or entry_price)
        quantity = position.entry_quantity
        
        profit = (exit_price - entry_price) * quantity
        profit_pct = ((exit_price - entry_price) / entry_price) * 100
        
        # 生成 HTML 表格
        html_table = self._generate_html_table(events)
        
        report = {
            "symbol": position.symbol,
            "stock_name": position.stock_name or position.symbol,
            "entry_date": position.entry_date.strftime("%Y-%m-%d") if position.entry_date else "",
            "entry_datetime": position.entry_date.strftime("%m/%d %H:%M") if position.entry_date else "",
            "entry_datetime_full": position.entry_date.strftime("%Y-%m-%d %H:%M:%S") if position.entry_date else "",
            "exit_date": position.exit_date.strftime("%Y-%m-%d %H:%M") if position.exit_date else "",
            "exit_datetime": position.exit_date.strftime("%m/%d %H:%M") if position.exit_date else "",
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "events": events,
            "summary": {
                "profit": profit,
                "profit_pct": round(profit_pct, 2),
                "total_events": len(events),
                "highest_price": float(position.highest_price) if position.highest_price else entry_price,
                "trailing_activated": position.trailing_activated,
                "exit_reason": position.exit_reason or "未知",
                "analysis_source": position.analysis_source or "",
                "quantity": int(position.entry_quantity),
                "stop_loss_price": float(position.stop_loss_price) if position.stop_loss_price else None,
                "target_price": float(position.target_price) if position.target_price else None,
                "hold_duration": self._calc_hold_duration(position),
            },
            "html_table": html_table
        }
        
        return report
    
    def _generate_html_table(self, events: List[Dict]) -> str:
        """生成 HTML 事件表格"""
        if not events:
            return "<p>無交易事件記錄</p>"
        
        # 事件類型中文對照
        event_type_names = {
            TradeEvent.OPEN: "開倉",
            TradeEvent.TRAILING_ACTIVATED: "啟動移動停利",
            TradeEvent.TRAILING_UPDATED: "更新高點",
            TradeEvent.HIGH_UPDATED: "更新最高價",
            TradeEvent.TRAILING_TRIGGERED: "觸發平倉",
            TradeEvent.STOP_LOSS: "停損平倉",
            TradeEvent.TARGET_HIT: "目標達成",
            TradeEvent.MANUAL_CLOSE: "手動平倉"
        }
        
        rows = []
        for event in events:
            event_type = event.get("type", "unknown")
            action = event_type_names.get(event_type, event_type)
            time = event.get("time", "")
            price = event.get("price", 0)
            description = event.get("description", "")
            
            rows.append(f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{time}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${price:.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{action}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{description}</td>
            </tr>
            """)
        
        table = f"""
        <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
            <thead>
                <tr style="background-color: #f5f5f5;">
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">時間</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">價格</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">動作</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">說明</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
        
        return table
    
    def _calc_hold_duration(self, position: Portfolio) -> str:
        """計算持倉時長"""
        try:
            start = position.entry_date
            end = position.exit_date or datetime.now()
            delta = end - start
            total_min = int(delta.total_seconds() / 60)
            if total_min < 60:
                return f"{total_min} 分鐘"
            elif total_min < 1440:
                h, m = divmod(total_min, 60)
                return f"{h} 小時 {m} 分鐘"
            else:
                days = delta.days
                h = (total_min % 1440) // 60
                return f"{days} 天 {h} 小時"
        except Exception:
            return ""

    async def send_execution_report_email(self, position: Portfolio) -> bool:
        """
        發送交易執行報告 Email
        
        Returns:
            是否發送成功
        """
        try:
            report = self.generate_execution_report(position)
            
            # Email 設定 (支援兩種環境變數命名)
            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            sender_email = os.getenv("EMAIL_USERNAME") or os.getenv("SMTP_USER", "")
            sender_password = os.getenv("EMAIL_PASSWORD") or os.getenv("SMTP_PASSWORD", "")
            recipients_str = os.getenv("EMAIL_RECIPIENTS") or os.getenv("NOTIFICATION_EMAIL", sender_email)
            recipient_email = recipients_str.split(",")[0].strip() if recipients_str else sender_email
            
            if not sender_email or not sender_password:
                logger.warning("⚠️ Email 設定不完整，跳過發送")
                return False
            
            # 判斷獲利或虧損 (台灣股市: 紅色=漲/獲利, 綠色=跌/虧損)
            profit = report["summary"]["profit"]
            profit_pct = report["summary"]["profit_pct"]
            
            if profit >= 0:
                emoji = "🎉"
                profit_color = "#dc3545"  # 紅色 = 獲利
                result_text = "獲利"
            else:
                emoji = "📉"
                profit_color = "#28a745"  # 綠色 = 虧損
                result_text = "虧損"
            
            # 建立郵件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"{emoji} 交易報告 | {report['entry_date']} {report['symbol']} {report['stock_name']} {result_text} {profit_pct:+.1f}%"
            msg["From"] = sender_email
            msg["To"] = recipient_email
            
            # HTML 內容
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: 'Microsoft JhengHei', Arial, sans-serif; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .header {{ text-align: center; padding-bottom: 20px; border-bottom: 2px solid #eee; }}
                    .title {{ font-size: 24px; color: #333; margin: 0; }}
                    .subtitle {{ color: #666; margin-top: 5px; }}
                    .summary {{ display: flex; justify-content: space-around; padding: 20px 0; background: #f9f9f9; border-radius: 8px; margin: 20px 0; }}
                    .summary-item {{ text-align: center; }}
                    .summary-label {{ font-size: 12px; color: #666; }}
                    .summary-value {{ font-size: 20px; font-weight: bold; color: #333; }}
                    .profit {{ color: {profit_color}; font-size: 28px; }}
                    .section-title {{ font-size: 16px; font-weight: bold; color: #333; margin: 20px 0 10px 0; border-left: 4px solid #007bff; padding-left: 10px; }}
                    .footer {{ text-align: center; padding-top: 20px; color: #999; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 class="title">{emoji} {report['symbol']} {report['stock_name']}</h1>
                        <p class="subtitle">
                            進場: <strong>{report['entry_datetime_full']}</strong>
                            &nbsp;|&nbsp;
                            出場: <strong>{report['exit_date']}</strong>
                            &nbsp;|&nbsp;
                            報告時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}
                        </p>
                    </div>
                    
                    <div style="text-align: center; padding: 20px;">
                        <div class="summary-label">最終損益</div>
                        <div class="profit">{profit_pct:+.1f}%</div>
                        <div style="color: {profit_color}; font-size: 18px;">${profit:+,.0f}</div>
                    </div>
                    
                    <table style="width: 100%; margin: 20px 0;">
                        <tr>
                            <td style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
                                <div style="font-size: 12px; color: #666;">進場價</div>
                                <div style="font-size: 18px; font-weight: bold;">${report['entry_price']:.2f}</div>
                            </td>
                            <td style="text-align: center; padding: 10px;">→</td>
                            <td style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
                                <div style="font-size: 12px; color: #666;">出場價</div>
                                <div style="font-size: 18px; font-weight: bold;">${report['exit_price']:.2f}</div>
                            </td>
                            <td style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
                                <div style="font-size: 12px; color: #666;">最高價</div>
                                <div style="font-size: 18px; font-weight: bold;">${report['summary']['highest_price']:.2f}</div>
                            </td>
                        </tr>
                    </table>
                    
                    <div class="section-title">📋 執行情況</div>
                    {report['html_table']}
                    
                    <div style="background: #e7f3ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
                        <div style="font-weight: bold; color: #0056b3;">📊 交易摘要</div>
                        <div style="margin-top: 10px; color: #333;">
                            <div>• 進場時間: {report['entry_datetime_full']}</div>
                            <div>• 出場時間: {report['exit_date']}</div>
                            <div>• 持倉時長: {report['summary']['hold_duration']}</div>
                            <div>• 買進股數: {report['summary']['quantity']:,} 股</div>
                            <div>• 分析來源: {report['summary']['analysis_source'] or '手動'}</div>
                            <div>• 移動停利: {'✅ 已啟動' if report['summary']['trailing_activated'] else '❌ 未啟動'}</div>
                            <div>• 出場原因: {report['summary']['exit_reason']}</div>
                            <div>• 事件數量: {report['summary']['total_events']} 筆</div>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p>AI Stock Intelligence Platform - 智能交易系統</p>
                        <p>此報告由系統自動生成</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, "html", "utf-8"))
            
            # 發送郵件
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())
            
            logger.info(f"✅ 交易執行報告已發送: {report['symbol']} {report['stock_name']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 發送交易執行報告失敗: {e}")
            return False


# 便捷函數
def create_open_event(position: Portfolio, db: AsyncSession) -> Dict:
    """建立開倉事件"""
    service = TradeExecutionReportService(db)
    stop_loss_text = f"停損 ${float(position.stop_loss_price):.2f}" if position.stop_loss_price else ""
    return service.add_trade_event(
        position=position,
        event_type=TradeEvent.OPEN,
        price=float(position.entry_price),
        description=stop_loss_text,
        details={
            "stop_loss": float(position.stop_loss_price) if position.stop_loss_price else None,
            "target": float(position.target_price) if position.target_price else None
        }
    )


def create_trailing_activated_event(
    position: Portfolio, 
    db: AsyncSession,
    current_price: float,
    profit_pct: float,
    new_stop: float
) -> Dict:
    """建立移動停利啟動事件"""
    service = TradeExecutionReportService(db)
    return service.add_trade_event(
        position=position,
        event_type=TradeEvent.TRAILING_ACTIVATED,
        price=current_price,
        description=f"獲利{profit_pct:.1f}%，停損→${new_stop:.2f}",
        details={"profit_pct": profit_pct, "new_stop": new_stop}
    )


def create_trailing_updated_event(
    position: Portfolio,
    db: AsyncSession,
    current_price: float,
    new_stop: float
) -> Dict:
    """建立移動停利更新事件"""
    service = TradeExecutionReportService(db)
    return service.add_trade_event(
        position=position,
        event_type=TradeEvent.TRAILING_UPDATED,
        price=current_price,
        description=f"停損→${new_stop:.2f}",
        details={"new_stop": new_stop}
    )


def create_close_event(
    position: Portfolio,
    db: AsyncSession,
    exit_price: float,
    exit_reason: str,
    profit_pct: float
) -> Dict:
    """建立平倉事件"""
    service = TradeExecutionReportService(db)
    event_type = TradeEvent.TRAILING_TRIGGERED
    
    if "停損" in exit_reason:
        event_type = TradeEvent.STOP_LOSS
    elif "目標" in exit_reason or "達標" in exit_reason:
        event_type = TradeEvent.TARGET_HIT
    elif "手動" in exit_reason:
        event_type = TradeEvent.MANUAL_CLOSE
    elif "移動" in exit_reason:
        event_type = TradeEvent.TRAILING_TRIGGERED
    
    description = f"{exit_reason}，鎖定{profit_pct:+.1f}%利潤" if profit_pct > 0 else f"{exit_reason}，虧損{profit_pct:.1f}%"
    
    return service.add_trade_event(
        position=position,
        event_type=event_type,
        price=exit_price,
        description=description,
        details={"profit_pct": profit_pct, "exit_reason": exit_reason}
    )
