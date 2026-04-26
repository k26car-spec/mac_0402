"""
交易 Email 通知服務
Trade Email Notification Service

功能：
1. 買進通知 - 新建倉位時發送
2. 平倉通知 - 平倉時發送（達標/停損）
3. 整合到自動平倉系統
"""

import os
import smtplib
import logging
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


# 繁體中文股票名稱字典
STOCK_NAMES_TW = {
    # 半導體
    "2330": "台積電", "2454": "聯發科", "3711": "日月光投控", "2303": "聯電", "3034": "聯詠",
    "6770": "力積電", "3661": "世芯-KY", "2379": "瑞昱", "2344": "華邦電", "2337": "旺宏",
    # PCB / 電子
    "2317": "鴻海", "3037": "欣興", "2313": "華通", "2314": "台揚", "8046": "南電",
    "3706": "神達", "2327": "國巨", "6153": "嘉聯益", "2368": "金像電", "2367": "燿華",
    # 金融
    "2881": "富邦金", "2882": "國泰金", "2891": "中信金", "2884": "玉山金", "2886": "兆豐金",
    "2887": "台新金", "2892": "第一金", "2801": "彰銀", "5880": "合庫金", "2834": "臺企銀",
    # 傳產
    "1301": "台塑", "1303": "南亞", "1326": "台化", "1101": "台泥", "1216": "統一",
    "2912": "統一超", "1605": "華新", "2002": "中鋼", "2207": "和泰車", "9910": "豐泰",
    # 其他
    "3231": "緯創", "2382": "廣達", "3008": "大立光", "2412": "中華電", "3481": "群創",
    "2609": "陽明", "2618": "長榮航", "2377": "微星", "2301": "光寶科", "2408": "南亞科",
    # 中小型股
    "5498": "凱崴", "8074": "鉅橡", "3163": "波若威", "6257": "矽格", "1815": "富喬",
    "8422": "可寧衛", "3265": "台星科", "3363": "上詮", "8155": "博智", "6282": "康舒",
    "5521": "工信", "2312": "金寶", "3443": "創意", "6285": "啟碁", "3529": "力旺",
    "6239": "力成", "3189": "景碩", "2449": "京元電子", "3653": "健策", "6452": "康友-KY",
    # 🆕 新增
    "8039": "台虹", "3030": "德律", "1802": "台玻", "1504": "東元", "2308": "台達電"
}


async def get_tw_stock_name(symbol: str, fallback: str = None) -> str:
    """取得繁體中文股票名稱 — 只用富邦 API，不使用對應表"""

    # 1. 優先用富邦 fubon_client（最準確）
    try:
        from fubon_client import fubon_client
        name = await fubon_client.get_stock_name(symbol)
        if name and name != symbol and not name.isupper():  # 排除全英大寫（如 CAREER）
            return name
    except Exception as e:
        logger.debug(f"富邦 client 名稱查詢失敗 {symbol}: {e}")

    # 2. 備援：內部 API（也是用富邦）
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"http://localhost:8000/api/stock-analysis/stock-name/{symbol}")
            if resp.status_code == 200:
                data = resp.json()
                name = data.get('name', '')
                if name and name != symbol and not name.isupper():
                    return name
    except Exception as e:
        logger.debug(f"內部 API 名稱查詢失敗 {symbol}: {e}")

    # 3. 最後 fallback
    return fallback or symbol



class TradeEmailNotifier:
    """交易 Email 通知器"""
    
    def __init__(self):
        # 使用現有的 Email 設定
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.sender_email = 'k26car@gmail.com'
        self.sender_password = 'zrgogmielnvpykrv'  # Gmail 應用程式密碼
        self.recipients = ['k26car@gmail.com', 'neimou1225@gmail.com']
    
    def is_configured(self) -> bool:
        """檢查 Email 是否已設定"""
        return bool(self.sender_email and self.sender_password and self.recipients)
    
    def _send_email(self, subject: str, html_content: str) -> bool:
        """發送 Email"""
        if not self.is_configured():
            logger.warning("⚠️ Email 設定不完整，跳過發送")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipients)
            
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipients, msg.as_string())
            
            logger.info(f"✅ Email 發送成功: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email 發送失敗: {e}")
            return False
    
    async def send_buy_notification(
        self,
        symbol: str,
        stock_name: str,
        entry_price: float,
        quantity: int,
        stop_loss: Optional[float],
        target_price: Optional[float],
        analysis_source: str,
        is_simulated: bool = False
    ) -> bool:
        """
        發送買進通知
        
        Args:
            symbol: 股票代碼
            stock_name: 股票名稱
            entry_price: 進場價
            quantity: 數量
            stop_loss: 停損價
            target_price: 目標價
            analysis_source: 訊號來源
            is_simulated: 是否為模擬交易
        """
        # 🆕 確保使用繁體中文名稱 (使用 await)
        stock_name = await get_tw_stock_name(symbol, stock_name)
        
        trade_type = "🎮 模擬" if is_simulated else "💰 真實"
        total_cost = entry_price * quantity
        
        # 計算預期獲利/虧損
        expected_profit = ""
        if target_price:
            profit = (target_price - entry_price) * quantity
            profit_pct = (target_price - entry_price) / entry_price * 100
            expected_profit = f"<p>🎯 預期獲利: <span style='color: #dc2626;'>+${profit:,.0f} (+{profit_pct:.1f}%)</span></p>"
        
        expected_loss = ""
        if stop_loss:
            loss = (stop_loss - entry_price) * quantity
            loss_pct = (stop_loss - entry_price) / entry_price * 100
            expected_loss = f"<p>🛡️ 最大虧損: <span style='color: #16a34a;'>${loss:,.0f} ({loss_pct:.1f}%)</span></p>"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f8fafc; margin: 0; padding: 20px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #dc2626, #b91c1c); color: white; padding: 24px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header .type {{ opacity: 0.9; font-size: 14px; margin-top: 8px; }}
                .content {{ padding: 24px; }}
                .stock-info {{ background: #fef2f2; border-radius: 12px; padding: 16px; margin-bottom: 20px; text-align: center; }}
                .stock-code {{ font-size: 32px; font-weight: bold; color: #dc2626; }}
                .stock-name {{ color: #666; margin-top: 4px; }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #f1f5f9; }}
                .detail-label {{ color: #64748b; }}
                .detail-value {{ font-weight: 600; color: #1e293b; }}
                .footer {{ padding: 16px 24px; background: #f8fafc; text-align: center; color: #94a3b8; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔔 買進通知</h1>
                    <div class="type">{trade_type}交易</div>
                </div>
                <div class="content">
                    <div class="stock-info">
                        <div class="stock-code">{symbol}</div>
                        <div class="stock-name">{stock_name or symbol}</div>
                    </div>
                    
                    <div class="detail-row">
                        <span class="detail-label">進場價格</span>
                        <span class="detail-value">${entry_price:,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">買進數量</span>
                        <span class="detail-value">{quantity:,} 股</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">投資成本</span>
                        <span class="detail-value">${total_cost:,.0f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">停損價</span>
                        <span class="detail-value">${stop_loss:,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">目標價</span>
                        <span class="detail-value">${target_price:,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">訊號來源</span>
                        <span class="detail-value">{analysis_source}</span>
                    </div>
                    
                    {expected_profit}
                    {expected_loss}
                </div>
                <div class="footer">
                    AI Stock Intelligence | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """
        
        subject = f"{'🎮' if is_simulated else '🔔'} 買進通知: {symbol} @ ${entry_price:.2f}"
        
        # 整合多管道通知 (Telegram)
        try:
            from app.services.notification_manager import notification_manager
            stop_loss_str = f"${stop_loss:,.2f}" if stop_loss else "無"
            target_str = f"${target_price:,.2f}" if target_price else "無"
            tg_msg = f"""
{'🎮' if is_simulated else '🔔'} <b>買進通知</b>
股票代碼：{symbol} {stock_name or symbol}
進場價格：${entry_price:,.2f}
買進數量：{quantity:,} 股
投資成本：${total_cost:,.0f}
停損價：{stop_loss_str}
目標價：{target_str}
訊號來源：{analysis_source}
"""
            notification_manager.send_to_all(tg_msg)
        except Exception as e:
            logger.error(f"Telegram 發送失敗: {e}")
            
        return self._send_email(subject, html)
    
    async def send_close_notification(
        self,
        symbol: str,
        stock_name: str,
        entry_price: float,
        exit_price: float,
        quantity: int,
        profit: float,
        profit_percent: float,
        reason: str,
        status: str,
        is_simulated: bool = False
    ) -> bool:
        """
        發送平倉通知
        
        Args:
            symbol: 股票代碼
            stock_name: 股票名稱
            entry_price: 進場價
            exit_price: 出場價
            quantity: 數量
            profit: 損益金額
            profit_percent: 損益百分比
            reason: 平倉原因
            status: 狀態 (target_hit / stopped / closed)
            is_simulated: 是否為模擬交易
        """
        # 🆕 確保使用繁體中文名稱 (使用 await)
        stock_name = await get_tw_stock_name(symbol, stock_name)
        
        trade_type = "🎮 模擬" if is_simulated else "💰 真實"
        is_profit = profit >= 0
        
        # 根據狀態決定顏色
        if status == 'target_hit':
            header_gradient = "linear-gradient(135deg, #dc2626, #b91c1c)"
            emoji = "🎯"
            status_text = "達標獲利"
        elif status == 'stopped':
            header_gradient = "linear-gradient(135deg, #16a34a, #15803d)"
            emoji = "🛑"
            status_text = "停損出場"
        else:
            header_gradient = "linear-gradient(135deg, #6b7280, #4b5563)"
            emoji = "📋"
            status_text = "手動平倉"
        
        profit_color = "#dc2626" if is_profit else "#16a34a"
        profit_sign = "+" if is_profit else ""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f8fafc; margin: 0; padding: 20px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: {header_gradient}; color: white; padding: 24px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header .type {{ opacity: 0.9; font-size: 14px; margin-top: 8px; }}
                .content {{ padding: 24px; }}
                .stock-info {{ border-radius: 12px; padding: 20px; margin-bottom: 20px; text-align: center; background: {'#fef2f2' if is_profit else '#f0fdf4'}; }}
                .stock-code {{ font-size: 28px; font-weight: bold; color: #333; }}
                .stock-name {{ color: #666; margin-top: 4px; }}
                .profit-box {{ background: linear-gradient(135deg, {profit_color}, {profit_color}dd); color: white; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; }}
                .profit-amount {{ font-size: 36px; font-weight: bold; }}
                .profit-percent {{ font-size: 18px; opacity: 0.9; margin-top: 4px; }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #f1f5f9; }}
                .detail-label {{ color: #64748b; }}
                .detail-value {{ font-weight: 600; color: #1e293b; }}
                .reason-box {{ background: #f8fafc; border-radius: 8px; padding: 12px; margin-top: 16px; text-align: center; color: #64748b; }}
                .footer {{ padding: 16px 24px; background: #f8fafc; text-align: center; color: #94a3b8; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{emoji} {status_text}</h1>
                    <div class="type">{trade_type}交易</div>
                </div>
                <div class="content">
                    <div class="stock-info">
                        <div class="stock-code">{symbol}</div>
                        <div class="stock-name">{stock_name or symbol}</div>
                    </div>
                    
                    <div class="profit-box">
                        <div class="profit-amount">{profit_sign}${abs(profit):,.0f}</div>
                        <div class="profit-percent">{profit_sign}{profit_percent:.1f}%</div>
                    </div>
                    
                    <div class="detail-row">
                        <span class="detail-label">進場價格</span>
                        <span class="detail-value">${entry_price:,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">出場價格</span>
                        <span class="detail-value">${exit_price:,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">交易數量</span>
                        <span class="detail-value">{quantity:,} 股</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">持倉成本</span>
                        <span class="detail-value">${entry_price * quantity:,.0f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">賣出金額</span>
                        <span class="detail-value">${exit_price * quantity:,.0f}</span>
                    </div>
                    
                    <div class="reason-box">
                        📌 {reason}
                    </div>
                </div>
                <div class="footer">
                    AI Stock Intelligence | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """
        
        emoji_subject = "🎯" if status == 'target_hit' else "🛑" if status == 'stopped' else "📋"
        subject = f"{emoji_subject} 平倉通知: {symbol} {profit_sign}${abs(profit):,.0f} ({profit_sign}{profit_percent:.1f}%)"
        
        # 整合多管道通知 (Telegram)
        try:
            from app.services.notification_manager import notification_manager
            tg_msg = f"""
{emoji_subject} <b>{status_text} - 已平倉</b>
股票代碼：{symbol} {stock_name or symbol}
進場價格：${entry_price:,.2f}
出場價格：${exit_price:,.2f}
交易數量：{quantity:,} 股
損益：<b>{profit_sign}{profit_percent:.1f}%</b> ({profit_sign}${abs(profit):,.0f})
說明：{reason}
"""
            notification_manager.send_to_all(tg_msg)
        except Exception as e:
            logger.error(f"Telegram 發送失敗: {e}")
            
        return self._send_email(subject, html)
    
    async def send_batch_notification(
        self,
        trades: List[Dict[str, Any]],
        title: str = "交易彙整報告"
    ) -> bool:
        """
        發送批量交易通知
        
        Args:
            trades: 交易列表
            title: 報告標題
        """
        if not trades:
            return False
        
        total_profit = sum(t.get('profit', 0) for t in trades)
        wins = sum(1 for t in trades if t.get('profit', 0) > 0)
        losses = sum(1 for t in trades if t.get('profit', 0) < 0)
        
        rows_html = ""
        for t in trades:
            profit = t.get('profit', 0)
            profit_pct = t.get('profit_percent', 0)
            is_profit = profit >= 0
            profit_color = "#dc2626" if is_profit else "#16a34a"
            sign = "+" if is_profit else ""
            
            status = t.get('status', 'closed')
            if status == 'target_hit':
                status_badge = '<span style="background:#dcfce7;color:#16a34a;padding:2px 8px;border-radius:12px;font-size:11px;">達標</span>'
            elif status == 'stopped':
                status_badge = '<span style="background:#fef2f2;color:#dc2626;padding:2px 8px;border-radius:12px;font-size:11px;">停損</span>'
            else:
                status_badge = '<span style="background:#f1f5f9;color:#64748b;padding:2px 8px;border-radius:12px;font-size:11px;">平倉</span>'
            
            rows_html += f"""
            <tr>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;font-weight:600;">{t.get('symbol', '-')}</td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;">{t.get('stock_name', '-')}</td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;text-align:right;">${t.get('entry_price', 0):.2f}</td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;text-align:right;">${t.get('exit_price', 0):.2f}</td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;text-align:right;color:{profit_color};font-weight:600;">
                    {sign}${abs(profit):,.0f}<br><span style="font-size:11px;">({sign}{profit_pct:.1f}%)</span>
                </td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;text-align:center;">{status_badge}</td>
            </tr>
            """
        
        total_color = "#dc2626" if total_profit >= 0 else "#16a34a"
        total_sign = "+" if total_profit >= 0 else ""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f8fafc; margin: 0; padding: 20px; }}
                .container {{ max-width: 700px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 24px; text-align: center; }}
                .summary {{ display: flex; justify-content: space-around; padding: 20px; background: #f8fafc; }}
                .summary-item {{ text-align: center; }}
                .summary-value {{ font-size: 24px; font-weight: bold; }}
                .summary-label {{ font-size: 12px; color: #64748b; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ background: #f1f5f9; padding: 12px; text-align: left; font-size: 12px; color: #64748b; text-transform: uppercase; }}
                .footer {{ padding: 16px 24px; background: #f8fafc; text-align: center; color: #94a3b8; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 {title}</h1>
                    <div style="opacity:0.9;">{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
                </div>
                <div class="summary">
                    <div class="summary-item">
                        <div class="summary-value">{len(trades)}</div>
                        <div class="summary-label">交易筆數</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value" style="color:#dc2626;">{wins}</div>
                        <div class="summary-label">獲利筆數</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value" style="color:#16a34a;">{losses}</div>
                        <div class="summary-label">虧損筆數</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value" style="color:{total_color};">{total_sign}${abs(total_profit):,.0f}</div>
                        <div class="summary-label">總損益</div>
                    </div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>代碼</th>
                            <th>名稱</th>
                            <th style="text-align:right;">進場</th>
                            <th style="text-align:right;">出場</th>
                            <th style="text-align:right;">損益</th>
                            <th style="text-align:center;">狀態</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
                <div class="footer">
                    AI Stock Intelligence | 自動交易報告
                </div>
            </div>
        </body>
        </html>
        """
        
        subject = f"📊 {title}: {len(trades)} 筆交易, 總損益 {total_sign}${abs(total_profit):,.0f}"
        return self._send_email(subject, html)


# 全域通知器實例
trade_notifier = TradeEmailNotifier()
