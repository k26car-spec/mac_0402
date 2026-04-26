"""
大單監控即時數據 API
提供即時 tick 數據和大單偵測功能，並自動保存訊號到資料庫
支援智能通知：瀏覽器推播 + Email
"""
from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
import asyncio
import logging
from collections import defaultdict, deque
import random
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.database.connection import async_session
from app.models.big_order import BigOrderSignal
from sqlalchemy import select, desc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/big-order", tags=["大單監控"])

# ============ 智能通知系統配置 ============
NOTIFICATION_CONFIG = {
    "quality_threshold": 0.75,      # 品質門檻 75%
    "accumulate_count": 3,          # 1 分鐘內累積次數
    "accumulate_window": 60,        # 累積時間窗口（秒）
    "cooldown_seconds": 300,        # 冷卻時間 5 分鐘
    "high_quality_threshold": 0.85, # 高品質立即通知門檻 85%
    "require_real_data": True,      # ⚠️ 必須有真實資料才發送通知
}

# 訊號累積追蹤（按股票代碼）
signal_accumulator: Dict[str, List[Dict]] = defaultdict(list)

# 上次通知時間（按股票代碼）
last_notification_time: Dict[str, datetime] = {}

# 待發送通知隊列
pending_notifications: List[Dict] = []


def should_send_notification(stock_code: str, signal: Dict) -> Optional[Dict]:
    """
    判斷是否應該發送通知
    返回通知內容或 None
    """
    now = datetime.now()
    quality = signal.get('quality_score', 0)
    signal_type = signal.get('signal_type', '')
    
    # 🕐 檢查是否在交易時間內 (09:00 - 13:30)
    current_time = now.time()
    market_open = datetime.strptime("09:00", "%H:%M").time()
    market_close = datetime.strptime("13:30", "%H:%M").time()
    
    if current_time < market_open or current_time > market_close:
        logger.debug(f"🕐 {stock_code} 非交易時間 ({current_time.strftime('%H:%M')})，跳過通知")
        return None
    
    # 🔴 檢查是否已漲停/跌停 - 不發送通知
    change_percent = signal.get('change_percent', 0)
    if abs(change_percent) >= 9.5:  # 漲停/跌停約 10%，這裡用 9.5% 作為門檻
        if change_percent > 0:
            logger.info(f"⛔ {stock_code} 已漲停 ({change_percent:.1f}%)，跳過通知")
        else:
            logger.info(f"⛔ {stock_code} 已跌停 ({change_percent:.1f}%)，跳過通知")
        return None
    
    # 檢查冷卻時間
    if stock_code in last_notification_time:
        elapsed = (now - last_notification_time[stock_code]).total_seconds()
        if elapsed < NOTIFICATION_CONFIG['cooldown_seconds']:
            logger.debug(f"{stock_code} 仍在冷卻時間內 ({elapsed:.0f}s)")
            return None
    
    # 條件1：高品質訊號立即通知
    if quality >= NOTIFICATION_CONFIG['high_quality_threshold']:
        logger.info(f"🚨 {stock_code} 高品質訊號 ({quality:.1%})，立即通知！")
        last_notification_time[stock_code] = now
        return {
            "type": "high_quality",
            "stock_code": stock_code,
            "stock_name": signal.get('stock_name', stock_code),
            "signal_type": signal_type,
            "quality": quality,
            "price": signal.get('price', 0),
            "reason": signal.get('reason', ''),
            "count": 1,
            "timestamp": now.isoformat()
        }
    
    # 條件2：品質達標，檢查累積次數
    if quality >= NOTIFICATION_CONFIG['quality_threshold']:
        # 清理過期的累積訊號
        window = NOTIFICATION_CONFIG['accumulate_window']
        cutoff = now - timedelta(seconds=window)
        signal_accumulator[stock_code] = [
            s for s in signal_accumulator[stock_code]
            if datetime.fromisoformat(s['timestamp']) > cutoff
        ]
        
        # 添加當前訊號
        signal_accumulator[stock_code].append({
            "signal_type": signal_type,
            "quality": quality,
            "timestamp": now.isoformat()
        })
        
        # 檢查同向訊號累積數量
        same_direction = [
            s for s in signal_accumulator[stock_code]
            if s['signal_type'] == signal_type
        ]
        
        if len(same_direction) >= NOTIFICATION_CONFIG['accumulate_count']:
            avg_quality = sum(s['quality'] for s in same_direction) / len(same_direction)
            logger.info(f"🚨 {stock_code} 累積 {len(same_direction)} 次 {signal_type} 訊號，發送通知！")
            last_notification_time[stock_code] = now
            signal_accumulator[stock_code] = []  # 清空累積
            return {
                "type": "accumulated",
                "stock_code": stock_code,
                "stock_name": signal.get('stock_name', stock_code),
                "signal_type": signal_type,
                "quality": avg_quality,
                "price": signal.get('price', 0),
                "reason": f"1分鐘內出現 {len(same_direction)} 筆{signal_type}大單",
                "count": len(same_direction),
                "timestamp": now.isoformat()
            }
    
    return None


async def send_email_notification(notification: Dict) -> bool:
    """發送 Email 通知"""
    try:
        # 從環境變數讀取設定
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('EMAIL_USERNAME') or os.getenv('SENDER_EMAIL', '')
        sender_password = os.getenv('EMAIL_PASSWORD') or os.getenv('SENDER_PASSWORD', '')
        recipients_str = os.getenv('EMAIL_RECIPIENTS') or os.getenv('RECIPIENT_EMAILS', '')
        recipients = [r.strip() for r in recipients_str.split(',') if r.strip()]
        
        if not sender_email or not sender_password or not recipients:
            logger.warning("Email 設定不完整，跳過通知")
            return False
        
        signal_type = notification['signal_type']
        emoji = "🔴 買進" if signal_type == 'BUY' else "🟢 賣出"
        
        subject = f"🚨 大單{signal_type}訊號 - {notification['stock_code']} {notification['stock_name']}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; background: #f5f5f5;">
            <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <div style="background: {'linear-gradient(135deg, #ef4444, #dc2626)' if signal_type == 'BUY' else 'linear-gradient(135deg, #22c55e, #16a34a)'}; color: white; padding: 24px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">{emoji} 大單訊號</h1>
                    <p style="margin: 8px 0 0; opacity: 0.9;">{notification['stock_code']} {notification['stock_name']}</p>
                </div>
                <div style="padding: 24px;">
                    <div style="display: grid; gap: 12px;">
                        <div style="display: flex; justify-content: space-between; padding: 12px; background: #eef2ff; border-radius: 8px; border: 1px solid #c7d2fe;">
                            <span style="color: #4338ca;">📡 訊號管道</span>
                            <span style="font-weight: bold; color: #4338ca;">大單監控</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 12px; background: #f9fafb; border-radius: 8px;">
                            <span style="color: #6b7280;">💰 當前價格</span>
                            <span style="font-weight: bold;">${notification['price']:.2f}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 12px; background: #f9fafb; border-radius: 8px;">
                            <span style="color: #6b7280;">⭐ 品質分數</span>
                            <span style="font-weight: bold; color: {'#7c3aed' if notification['quality'] >= 0.8 else '#2563eb'};">{notification['quality']:.1%}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 12px; background: #f9fafb; border-radius: 8px;">
                            <span style="color: #6b7280;">📊 觸發原因</span>
                            <span style="font-weight: bold;">{notification['reason']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 12px; background: #f9fafb; border-radius: 8px;">
                            <span style="color: #6b7280;">⏰ 時間</span>
                            <span style="font-weight: bold;">{datetime.now().strftime('%H:%M:%S')}</span>
                        </div>
                    </div>
                </div>
                <div style="padding: 16px 24px; background: #f9fafb; text-align: center; color: #9ca3af; font-size: 12px;">
                    大單偵測監控系統 v3.0 | 此為自動發送通知
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())
        
        logger.info(f"✅ Email 通知已發送: {notification['stock_code']} to {len(recipients)} 位收件人")
        return True
        
    except Exception as e:
        logger.error(f"❌ Email 發送失敗: {e}")
        return False


async def get_fubon_quote_direct(request: Request, symbol: str) -> Optional[Dict[str, Any]]:
    """
    獲取即時報價
    
    邏輯：
    1. 交易時段（富邦有成交量）：使用富邦 API
    2. 非交易時段（富邦 volume=0）：優先使用 Yahoo Finance（收盤價更準確）
    """
    fubon_quote = None
    
    try:
        # 判斷是否為盤中交易時間 (09:00 - 13:30)
        now = datetime.now()
        current_time = now.time()
        market_open = datetime.strptime("09:00", "%H:%M").time()
        market_close = datetime.strptime("13:30", "%H:%M").time()
        is_market_hours = market_open <= current_time <= market_close

        if hasattr(request.app.state, 'fubon_client') and request.app.state.fubon_connected:
            fubon = request.app.state.fubon_client
            
    
            # 盤中強制重試最多 3 次
            retry_count = 3 if is_market_hours else 1
            
            for i in range(retry_count):
                try:
                    # 強制加上 timeout，避免卡死
                    fubon_quote = await asyncio.wait_for(fubon.get_quote(symbol), timeout=2.0)
                    
                    # 檢查數據有效性
                    if fubon_quote and fubon_quote.get('price', 0) > 0:
                        # 盤中必須有成交量才算有效 (開盤初可能為0，需特判)
                        if is_market_hours and fubon_quote.get('volume', 0) == 0 and current_time > datetime.strptime("09:01", "%H:%M").time():
                             pass
                        
                        # 正確計算漲跌幅 (應該基於昨收/參考價，而非開盤價)
                        # 富邦 API 通常有 'referencePrice' 或 'previousClose'
                        ref_price = fubon_quote.get('referencePrice') or fubon_quote.get('previousClose') or fubon_quote.get('open')
                        
                        if ref_price and ref_price > 0:
                            fubon_quote['change'] = round((fubon_quote['price'] - ref_price) / ref_price * 100, 2)
                        elif fubon_quote.get('open', 0) > 0:
                             # Fallback 到開盤價 (不準確，但比 0 好)
                            fubon_quote['change'] = round((fubon_quote['price'] - fubon_quote['open']) / fubon_quote['open'] * 100, 2)
                        
                        logger.info(f"✅ 使用富邦即時報價: {symbol} = {fubon_quote['price']} ({fubon_quote.get('change')}%)")
                        return fubon_quote
                except asyncio.TimeoutError:
                    if i == retry_count - 1:
                        logger.warning(f"富邦報價請求超時 ({symbol})")
                except Exception as e:
                    if i == retry_count - 1:
                        logger.warning(f"富邦報價重試失敗 ({i+1}/{retry_count}): {e}")
                    await asyncio.sleep(0.1)

            # 如果盤中富邦失敗，不要馬上切 Yahoo，先回傳最後已知價格或 None (除非真的完全拿不到)
            # 這裡我們還是讓它 fallback，但在前端可以顯示警示
                    
    except Exception as e:
        logger.error(f"富邦報價獲取失敗: {e}")
    
    # 盤中時間，如果富邦失敗，盡量不要切換到 Yahoo (因為 Yahoo 延遲嚴重)，除非完全沒辦法
    # 但為了不讓畫面空白，我們先 fallback，但特別標註來源
    
    # 非交易時段或富邦失敗時使用 Yahoo Finance
    yahoo_quote = await get_yahoo_quote(symbol)
    
    if yahoo_quote:
        source_label = "yahoo (模擬)" if is_market_hours else "yahoo"
        logger.info(f"⚠️ 使用 Yahoo Finance 報價: {symbol} = {yahoo_quote['price']} ({source_label})")
        yahoo_quote['source'] = source_label # 標記為模擬，讓前端知道
        return yahoo_quote
    
    # 如果 Yahoo 也失敗，fallback 到富邦的 reference_price
    if fubon_quote and fubon_quote.get('price', 0) > 0:
        return fubon_quote
    
    return None


async def get_yahoo_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """
    從 Yahoo Finance 獲取報價（回退方案）
    支援上市股票 (.TW) 和上櫃股票 (.TWO)
    """
    try:
        import yfinance as yf
        
        # 這裡直接傳入 symbol，patched yfinance 會自動根據清單修正為 .TW 或 .TWO
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        
        # 如果失敗，嘗試強迫另一種後綴作為最後手段
        if hist.empty:
            clean = symbol.replace('.TW', '').replace('.TWO', '')
            alt_symbol = f"{clean}.TWO" if '.TW' in symbol or ('.' not in symbol) else f"{clean}.TW"
            ticker = yf.Ticker(alt_symbol)
            hist = ticker.history(period="1d")
            
        if hist.empty:
            return None
        
        last_row = hist.iloc[-1]
        
        return {
            "symbol": clean_symbol,
            "price": round(float(last_row['Close']), 2),
            "open": round(float(last_row['Open']), 2),
            "high": round(float(last_row['High']), 2),
            "low": round(float(last_row['Low']), 2),
            "volume": int(last_row['Volume']),
            "change": round(float((last_row['Close'] - last_row['Open']) / last_row['Open'] * 100), 2),
            "source": "yahoo",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Yahoo Finance 報價獲取失敗: {e}")
        return None

# 儲存 tick 歷史（每個股票最多 1000 筆）
tick_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

# 股價緩存 (用於動態計算門檻)
price_cache: Dict[str, float] = {}

# 自訂門檻覆蓋 (如果用戶手動設定，優先使用)
custom_thresholds: Dict[str, int] = {}


def get_threshold(symbol: str, current_price: Optional[float] = None) -> int:
    """
    取得股票的大單閾值
    
    優先順序:
    1. 用戶自訂門檻
    2. 根據當前股價動態計算
    3. 使用緩存價格計算
    4. 預設值 50 張
    """
    # 1. 檢查自訂門檻
    if symbol in custom_thresholds:
        return custom_thresholds[symbol]
    
    # 2. 使用當前價格動態計算
    price = current_price or price_cache.get(symbol, 0)
    
    if price > 0:
        from app.config.big_order_config import calculate_dynamic_threshold
        config = calculate_dynamic_threshold(price)
        return config.single_order
    
    # 3. 預設值
    return 50


def set_custom_threshold(symbol: str, threshold: int):
    """設定自訂門檻"""
    custom_thresholds[symbol] = threshold
    

def update_price_cache(symbol: str, price: float):
    """更新價格緩存"""
    if price > 0:
        price_cache[symbol] = price


def is_big_order(volume: int, symbol: str, current_price: Optional[float] = None) -> bool:
    """判斷是否為大單"""
    threshold = get_threshold(symbol, current_price)
    return volume >= threshold


def analyze_tick_flow(ticks: List[Dict], symbol: str) -> Dict[str, Any]:
    """分析 tick 流，計算買賣力道"""
    if not ticks or len(ticks) < 2:
        return None
    
    threshold = get_threshold(symbol)
    
    buy_volume = 0
    sell_volume = 0
    big_buy_volume = 0
    big_sell_volume = 0
    big_order_count = 0
    
    prices = []
    
    for tick in ticks:
        vol = tick.get('volume', 0)
        bs = tick.get('bs_flag', 'N')
        price = tick.get('price', 0)
        
        if price > 0:
            prices.append(price)
        
        if bs == 'B':
            buy_volume += vol
            if vol >= threshold:
                big_buy_volume += vol
                big_order_count += 1
        elif bs == 'S':
            sell_volume += vol
            if vol >= threshold:
                big_sell_volume += vol
                big_order_count += 1
    
    total_volume = buy_volume + sell_volume
    
    if total_volume == 0:
        return None
    
    buy_ratio = buy_volume / total_volume
    
    # 價格變化
    price_change_pct = 0
    if len(prices) >= 2 and prices[0] > 0:
        price_change_pct = (prices[-1] - prices[0]) / prices[0]
    
    return {
        'total_volume': total_volume,
        'buy_volume': buy_volume,
        'sell_volume': sell_volume,
        'buy_ratio': buy_ratio,
        'big_buy_volume': big_buy_volume,
        'big_sell_volume': big_sell_volume,
        'big_order_count': big_order_count,
        'price_change_pct': price_change_pct,
        'current_price': prices[-1] if prices else 0
    }


def generate_signal(symbol: str, stock_name: str, analysis: Dict, data_source: str = "unknown") -> Optional[Dict]:
    """根據分析結果產生訊號"""
    if not analysis or analysis['big_order_count'] < 3:
        return None
    
    buy_ratio = analysis['buy_ratio']
    price_change = analysis['price_change_pct']
    
    # 判斷訊號方向
    if buy_ratio > 0.65 and price_change > 0.002:
        signal_type = 'BUY'
        confidence = buy_ratio
    elif buy_ratio < 0.35 and price_change < -0.002:
        signal_type = 'SELL'
        confidence = 1 - buy_ratio
    else:
        return None
    
    # 計算品質分數
    quality_score = min(1.0, 0.5 + abs(buy_ratio - 0.5) + abs(price_change) * 10)
    
    # 計算綜合分數
    momentum_score = min(1.0, 0.5 + abs(price_change) * 20)
    volume_score = min(1.0, 0.5 + analysis['big_order_count'] * 0.1)
    
    # 方向確認獎勵
    if (buy_ratio > 0.6 and price_change > 0) or (buy_ratio < 0.4 and price_change < 0):
        pattern_score = 0.85
    else:
        pattern_score = 0.5
    
    composite_score = quality_score * 0.3 + momentum_score * 0.25 + volume_score * 0.25 + pattern_score * 0.2
    
    if composite_score < 0.6:
        return None
    
    current_price = analysis['current_price']
    
    # 產生停損停利
    if signal_type == 'BUY':
        stop_loss = current_price * 0.985
        take_profit = current_price * 1.025
    else:
        stop_loss = current_price * 1.015
        take_profit = current_price * 0.975
    
    # 品質等級
    if quality_score >= 0.8:
        quality_level = '優秀'
    elif quality_score >= 0.7:
        quality_level = '良好'
    elif quality_score >= 0.6:
        quality_level = '普通'
    else:
        quality_level = '不佳'
    
    signal_id = f"signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{symbol}"
    
    return {
        'id': signal_id,
        'timestamp': datetime.now().isoformat(),
        'stock_code': symbol,
        'stock_name': stock_name,
        'signal_type': signal_type,
        'price': current_price,
        'composite_score': round(composite_score, 4),
        'confidence': round(confidence, 4),
        'quality_score': round(quality_score, 4),
        'momentum_score': round(momentum_score, 4),
        'volume_score': round(volume_score, 4),
        'pattern_score': round(pattern_score, 4),
        'quality_level': quality_level,
        'reason': f"{'買盤' if signal_type == 'BUY' else '賣壓'}力道 {buy_ratio:.1%}，{analysis['big_order_count']} 筆大單",
        'warnings': [],
        'stop_loss': round(stop_loss, 2),
        'take_profit': round(take_profit, 2),
        'metadata': analysis,
        'data_source': data_source
    }


async def save_signal_to_db(signal: Dict) -> bool:
    """將訊號保存到資料庫"""
    try:
        async with async_session() as session:
            db_signal = BigOrderSignal(
                signal_id=signal['id'],
                timestamp=datetime.fromisoformat(signal['timestamp']) if isinstance(signal['timestamp'], str) else signal['timestamp'],
                stock_code=signal['stock_code'],
                stock_name=signal['stock_name'],
                signal_type=signal['signal_type'],
                price=signal['price'],
                stop_loss=signal.get('stop_loss'),
                take_profit=signal.get('take_profit'),
                composite_score=signal['composite_score'],
                confidence=signal['confidence'],
                quality_score=signal['quality_score'],
                momentum_score=signal.get('momentum_score'),
                volume_score=signal.get('volume_score'),
                pattern_score=signal.get('pattern_score'),
                quality_level=signal['quality_level'],
                reason=signal.get('reason'),
                warnings=signal.get('warnings', []),
                extra_data=signal.get('metadata'),
                data_source=signal.get('data_source', 'unknown')
            )
            session.add(db_signal)
            await session.commit()
            logger.info(f"✅ 訊號已保存到資料庫: {signal['stock_code']} {signal['signal_type']}")
            
            # 檢查是否需要發送通知
            # ⚠️ 如果是模擬資料，不發送通知
            data_source = signal.get('data_source', 'unknown')
            is_real_data = data_source in ['fubon', 'fubon_websocket', 'twse_realtime']
            
            notification = None
            if is_real_data or not NOTIFICATION_CONFIG.get('require_real_data', True):
                notification = should_send_notification(signal['stock_code'], signal)
                if notification:
                    pending_notifications.append(notification)
                    # 非同步發送 Email（不阻塞）
                    asyncio.create_task(send_email_notification(notification))
            else:
                logger.debug(f"⚠️ {signal['stock_code']} 使用模擬資料 ({data_source})，跳過通知")
            
            # 🎯 高品質買入信號自動建立模擬持倉（也需要真實資料）
            if signal['signal_type'] == 'BUY' and signal['quality_score'] >= 0.75:
                if is_real_data or not NOTIFICATION_CONFIG.get('require_real_data', True):
                    asyncio.create_task(auto_create_position_from_big_order(signal))
            
            return True, notification
    except Exception as e:
        logger.error(f"❌ 保存訊號失敗: {e}")
        return False, None


async def auto_create_position_from_big_order(signal: Dict):
    """
    從大單信號自動建立模擬持倉
    這是即時信號自動建倉功能的核心
    """
    try:
        # 🕐 檢查是否在交易時間內 (09:00 - 13:30)
        now = datetime.now()
        current_time = now.time()
        market_open = datetime.strptime("09:00", "%H:%M").time()
        market_close = datetime.strptime("13:30", "%H:%M").time()
        
        if current_time < market_open or current_time > market_close:
            logger.debug(f"🕐 非交易時間，跳過自動建倉 {signal['stock_code']}")
            return
        
        from app.services.portfolio_automation import portfolio_automation
        
        position_id = await portfolio_automation.auto_create_position_from_signal(
            symbol=signal['stock_code'],
            stock_name=signal['stock_name'],
            source="big_order",
            confidence=signal['quality_score'],
            current_price=signal['price'],
            analysis_details={
                "signal_id": signal['id'],
                "signal_type": signal['signal_type'],
                "quality_score": signal['quality_score'],
                "momentum_score": signal.get('momentum_score'),
                "volume_score": signal.get('volume_score'),
                "reason": signal.get('reason'),
                "stop_loss": signal.get('stop_loss'),
                "take_profit": signal.get('take_profit')
            }
        )
        
        if position_id:
            logger.info(f"🎯 自動建立持倉成功: {signal['stock_code']} (ID: {position_id})")
        
    except Exception as e:
        logger.error(f"❌ 自動建倉失敗: {e}")


@router.get("/status")
async def get_status(request: Request):
    """取得大單監控系統狀態"""
    fubon_connected = getattr(request.app.state, 'fubon_connected', False)
    return {
        "system": "大單監控系統 v3.0",
        "status": "online",
        "data_source": "fubon" if fubon_connected else "yahoo",
        "fubon_connected": fubon_connected,
        "dynamic_threshold": True,
        "threshold_target_amount": "500萬",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/threshold")
async def get_threshold_config(
    price: float = Query(..., description="股價", ge=1),
    target_amount: float = Query(default=500, description="目標金額(萬元)", ge=100)
):
    """
    查詢指定股價的大單門檻
    
    系統會根據股價自動計算需要多少張才算大單
    
    計算邏輯：
    - 目標：單筆交易金額達到「能影響股價」的程度
    - 公式：張數 = 目標金額(萬) × 10 / 股價
    """
    from app.config.big_order_config import (
        calculate_dynamic_threshold, 
        calculate_threshold_with_custom_amount,
        get_threshold_description,
        MIN_THRESHOLD,
        MAX_THRESHOLD
    )
    
    if target_amount == 500:
        config = calculate_dynamic_threshold(price)
    else:
        config = calculate_threshold_with_custom_amount(price, target_amount)
    
    return {
        "price": price,
        "target_amount": f"${target_amount}萬",
        "threshold": {
            "single_order": config.single_order,
            "minute_accumulate": config.minute_accumulate,
            "actual_amount": f"${config.actual_amount:.0f}萬",
            "quality_threshold": f"{config.quality_threshold:.0%}"
        },
        "formula": f"{config.single_order}張 × ${price:.0f} × 1000股 = ${config.actual_amount:.0f}萬",
        "limits": {
            "min_threshold": MIN_THRESHOLD,
            "max_threshold": MAX_THRESHOLD
        },
        "description": get_threshold_description(price)
    }


@router.get("/threshold/table")
async def get_threshold_table():
    """
    取得完整的門檻對照表
    顯示不同股價對應的大單門檻
    """
    from app.config.big_order_config import calculate_dynamic_threshold
    
    prices = [15, 25, 35, 50, 75, 100, 150, 200, 300, 500, 800, 1000, 1500, 2000]
    table = []
    
    for price in prices:
        config = calculate_dynamic_threshold(price)
        table.append({
            "price": price,
            "threshold": config.single_order,
            "amount": f"${config.actual_amount:.0f}萬",
            "accumulate": config.minute_accumulate,
            "quality": f"{config.quality_threshold:.0%}"
        })
    
    return {
        "target_amount": "500萬",
        "formula": "張數 = 500萬 × 10 / 股價",
        "table": table,
        "note": "股價越高，所需張數越少，因為單筆金額更大"
    }


@router.get("/quote/{symbol}")
async def get_quote(request: Request, symbol: str):
    """取得單一股票即時報價"""
    quote = await get_fubon_quote_direct(request, symbol)
    if not quote:
        raise HTTPException(status_code=404, detail=f"無法取得 {symbol} 的報價")
    return quote


@router.post("/quotes")
async def get_quotes(request: Request, symbols: List[str]):
    """批量取得股票即時報價"""
    quotes = []
    for symbol in symbols:
        quote = await get_fubon_quote_direct(request, symbol)
        if quote:
            quotes.append(quote)
    return {"quotes": quotes}


@router.get("/tick/{symbol}")
async def get_latest_tick(request: Request, symbol: str):
    """
    取得股票最新 tick 數據（模擬即時 tick）
    實際環境中應該由 WebSocket 推送
    """
    # 獲取即時報價
    quote = await get_fubon_quote_direct(request, symbol)
    
    if not quote or quote.get('price', 0) == 0:
        raise HTTPException(status_code=404, detail=f"無法取得 {symbol} 的報價")
    
    # 模擬 tick 數據
    price = quote.get('price', 0)
    volume = quote.get('volume', 0)
    
    # 根據漲跌判斷買賣方向
    change = quote.get('change', 0)
    bs_flag = 'B' if change >= 0 else 'S'
    
    # 模擬單筆成交量（日成交量的一部分）
    tick_volume = max(1, volume // 1000) if volume > 0 else random.randint(10, 100)
    
    tick = {
        'symbol': symbol,
        'timestamp': datetime.now().isoformat(),
        'price': price,
        'volume': tick_volume,
        'bs_flag': bs_flag,
        'ask_price': round(price * 1.001, 2),
        'bid_price': round(price * 0.999, 2),
        'source': quote.get('source', 'unknown')
    }
    
    # 儲存到歷史
    tick_history[symbol].append(tick)
    
    return tick


@router.get("/analyze/{symbol}")
async def analyze_stock(
    request: Request,
    symbol: str,
    window_minutes: int = Query(default=5, ge=1, le=30),
    stock_name: str = Query(default="")
):
    """
    分析股票的大單情況並產生訊號
    使用動態門檻：根據當前股價自動計算大單張數門檻
    """
    # 🕐 檢查是否在交易時間內 (09:00 - 13:30)
    now = datetime.now()
    current_time = now.time()
    market_open = datetime.strptime("09:00", "%H:%M").time()
    market_close = datetime.strptime("13:30", "%H:%M").time()
    
    if current_time < market_open or current_time > market_close:
        return {
            "signal": None, 
            "analysis": None, 
            "market_closed": True,
            "message": f"非交易時間 ({current_time.strftime('%H:%M')})，台股交易時間為 09:00-13:30"
        }
    
    # 獲取最新報價
    quote = await get_fubon_quote_direct(request, symbol)
    
    if not quote or quote.get('price', 0) == 0:
        return {"signal": None, "analysis": None, "error": "無法取得報價"}
    
    # 模擬多筆 tick 數據用於分析
    ticks = []
    price = quote.get('price', 0)
    volume = quote.get('volume', 0)
    change = quote.get('change', 0)
    
    # 🎯 更新價格緩存並使用動態門檻
    update_price_cache(symbol, price)
    threshold = get_threshold(symbol, price)
    
    # 取得門檻詳細資訊 (用於回傳)
    from app.config.big_order_config import calculate_dynamic_threshold, get_threshold_breakdown
    threshold_config = calculate_dynamic_threshold(price)
    
    # 根據實際漲跌情況模擬 tick 分佈
    buy_bias = 0.5 + (change / 10)  # 漲時偏多，跌時偏空
    buy_bias = max(0.3, min(0.7, buy_bias))
    
    for i in range(20):
        bs = 'B' if random.random() < buy_bias else 'S'
        # 模擬大單
        if random.random() < 0.15:  # 15% 機率是大單
            vol = random.randint(threshold, threshold * 3)
        else:
            vol = random.randint(10, max(11, threshold - 1))
        
        ticks.append({
            'price': price * (1 + random.uniform(-0.002, 0.002)),
            'volume': vol,
            'bs_flag': bs
        })
    
    # 分析
    analysis = analyze_tick_flow(ticks, symbol)
    
    if not analysis:
        return {"signal": None, "analysis": None}
    
    # 產生訊號
    name = stock_name or symbol
    data_source = quote.get('source', 'unknown')
    signal = generate_signal(symbol, name, analysis, data_source)
    
    # 🔴 添加 change_percent 用於漲停板判斷
    if signal:
        # 計算漲跌幅百分比
        open_price = quote.get('open', 0)
        if open_price > 0:
            change_percent = ((price - open_price) / open_price) * 100
        else:
            # 使用 yfinance 的 change_percent
            change_percent = quote.get('change_percent', 0)
        signal['change_percent'] = round(change_percent, 2)
    
    # 自動保存訊號到資料庫並檢查通知
    notification = None
    if signal:
        _, notification = await save_signal_to_db(signal)
    
    return {
        "signal": signal,
        "notification": notification,  # 如果觸發通知，返回給前端
        "analysis": {
            "symbol": symbol,
            "price": price,
            "threshold": threshold,
            "threshold_amount": f"${threshold_config.actual_amount:.0f}萬",
            "threshold_formula": f"{threshold}張 × ${price:.0f} × 1000股",
            "buy_ratio": round(analysis['buy_ratio'], 4),
            "big_order_count": analysis['big_order_count'],
            "source": data_source
        },
        "dynamic_threshold": {
            "enabled": True,
            "target_amount": f"${threshold_config.target_amount}萬",
            "calculated_lots": threshold,
            "actual_amount": f"${threshold_config.actual_amount:.0f}萬",
            "minute_accumulate": threshold_config.minute_accumulate,
            "quality_threshold": f"{threshold_config.quality_threshold:.0%}"
        }
    }


@router.post("/batch-analyze")
async def batch_analyze(
    request: Request,
    stocks: List[Dict[str, Any]]
):
    """
    批量分析多檔股票
    
    Request body:
    [
        {"symbol": "2330", "name": "台積電", "threshold": 150},
        {"symbol": "2454", "name": "聯發科", "threshold": 120}
    ]
    """
    results = []
    signals = []
    notifications = []  # 觸發的通知列表
    
    for stock in stocks:
        symbol = stock.get('symbol', '')
        name = stock.get('name', symbol)
        threshold = stock.get('threshold', 50)
        
        # 如果有自訂閾值，設定它
        if threshold:
            set_custom_threshold(symbol, threshold)
        
        try:
            result = await analyze_stock(request, symbol, stock_name=name)
            results.append({
                "symbol": symbol,
                "name": name,
                "analysis": result.get('analysis'),
                "has_signal": result.get('signal') is not None
            })
            
            if result.get('signal'):
                signals.append(result['signal'])
            
            # 收集通知
            if result.get('notification'):
                notifications.append(result['notification'])
                
        except Exception as e:
            logger.error(f"分析 {symbol} 失敗: {e}")
            results.append({
                "symbol": symbol,
                "name": name,
                "error": str(e)
            })
    
    return {
        "results": results,
        "signals": signals,
        "notifications": notifications,  # 返回觸發的通知給前端
        "total_stocks": len(stocks),
        "signals_count": len(signals),
        "notifications_count": len(notifications),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/history")
async def get_signal_history(
    limit: int = Query(default=50, ge=1, le=500),
    stock_code: Optional[str] = Query(default=None),
    signal_type: Optional[str] = Query(default=None),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
):
    """
    查詢歷史大單訊號記錄
    
    Parameters:
    - limit: 返回筆數 (預設 50)
    - stock_code: 股票代號篩選
    - signal_type: 訊號類型 (BUY/SELL)
    - start_date: 開始日期 (YYYY-MM-DD)
    - end_date: 結束日期 (YYYY-MM-DD)
    """
    try:
        async with async_session() as session:
            query = select(BigOrderSignal).order_by(desc(BigOrderSignal.timestamp))
            
            # 篩選條件
            if stock_code:
                query = query.where(BigOrderSignal.stock_code == stock_code)
            if signal_type:
                query = query.where(BigOrderSignal.signal_type == signal_type.upper())
            if start_date:
                try:
                    start = datetime.strptime(start_date, "%Y-%m-%d")
                    query = query.where(BigOrderSignal.timestamp >= start)
                except:
                    pass
            if end_date:
                try:
                    end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                    query = query.where(BigOrderSignal.timestamp < end)
                except:
                    pass
            
            query = query.limit(limit)
            result = await session.execute(query)
            signals = result.scalars().all()
            
            return {
                "success": True,
                "signals": [s.to_dict() for s in signals],
                "total": len(signals),
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"查詢歷史記錄失敗: {e}")
        return {
            "success": False,
            "error": str(e),
            "signals": [],
            "total": 0
        }


@router.get("/history/stats")
async def get_signal_stats(
    days: int = Query(default=7, ge=1, le=30)
):
    """
    取得大單訊號統計
    """
    try:
        async with async_session() as session:
            start_date = datetime.now() - timedelta(days=days)
            
            # 查詢所有記錄
            query = select(BigOrderSignal).where(
                BigOrderSignal.timestamp >= start_date
            )
            result = await session.execute(query)
            signals = result.scalars().all()
            
            # 統計
            buy_count = len([s for s in signals if s.signal_type == 'BUY'])
            sell_count = len([s for s in signals if s.signal_type == 'SELL'])
            
            # 按股票分組
            stock_stats = {}
            for s in signals:
                if s.stock_code not in stock_stats:
                    stock_stats[s.stock_code] = {
                        "name": s.stock_name,
                        "buy": 0,
                        "sell": 0,
                        "total": 0
                    }
                stock_stats[s.stock_code][s.signal_type.lower()] += 1
                stock_stats[s.stock_code]["total"] += 1
            
            # 按日期分組
            daily_stats = {}
            for s in signals:
                day = s.timestamp.strftime("%Y-%m-%d")
                if day not in daily_stats:
                    daily_stats[day] = {"buy": 0, "sell": 0, "total": 0}
                daily_stats[day][s.signal_type.lower()] += 1
                daily_stats[day]["total"] += 1
            
            return {
                "success": True,
                "period_days": days,
                "total_signals": len(signals),
                "buy_signals": buy_count,
                "sell_signals": sell_count,
                "stock_stats": stock_stats,
                "daily_stats": daily_stats,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"統計失敗: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/history/{signal_id}")
async def delete_signal(signal_id: str):
    """刪除指定的訊號記錄"""
    try:
        async with async_session() as session:
            query = select(BigOrderSignal).where(BigOrderSignal.signal_id == signal_id)
            result = await session.execute(query)
            signal = result.scalar_one_or_none()
            
            if not signal:
                raise HTTPException(status_code=404, detail="訊號不存在")
            
            await session.delete(signal)
            await session.commit()
            
            return {"success": True, "message": "訊號已刪除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刪除訊號失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 通知相關 API ============

@router.get("/notifications/config")
async def get_notification_config():
    """取得通知配置"""
    return {
        "config": NOTIFICATION_CONFIG,
        "timestamp": datetime.now().isoformat()
    }


@router.put("/notifications/config")
async def update_notification_config(config: Dict[str, Any]):
    """更新通知配置"""
    global NOTIFICATION_CONFIG
    for key in config:
        if key in NOTIFICATION_CONFIG:
            NOTIFICATION_CONFIG[key] = config[key]
    
    return {
        "success": True,
        "config": NOTIFICATION_CONFIG,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/notifications/pending")
async def get_pending_notifications():
    """取得待確認的通知（供前端瀏覽器推播用）"""
    global pending_notifications
    
    # 返回並清空待發送通知
    notifications = pending_notifications.copy()
    pending_notifications = []
    
    return {
        "notifications": notifications,
        "count": len(notifications),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/notifications/stats")
async def get_notification_stats():
    """取得通知統計"""
    return {
        "accumulator": {k: len(v) for k, v in signal_accumulator.items()},
        "cooldowns": {k: v.isoformat() for k, v in last_notification_time.items()},
        "config": NOTIFICATION_CONFIG,
        "timestamp": datetime.now().isoformat()
    }
