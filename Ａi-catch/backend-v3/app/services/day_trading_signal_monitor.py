"""
當沖自動進出場訊號監控器
Day Trading Auto Signal Monitor

功能：
1. 自動監控 ORB watchlist 中的股票
2. 根據 VWAP/OFI/量價 條件判斷進出場時機
3. 自動發送 Email 通知

進場條件 (做多)：
- 價格接近支撐位 (±1%)
- 大戶資金流 > 0 (OFI 買進)
- 量價確認為利多
- VWAP 偏離度在合理範圍

出場條件：
- 價格跌破支撐位 (停損)
- 價格達到壓力位 (停利)
- 大戶資金流轉負
"""

import asyncio
import logging
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SignalType(Enum):
    ENTRY_LONG = "進場做多"
    EXIT_LONG = "出場(平多)"
    ENTRY_SHORT = "進場做空"
    EXIT_SHORT = "出場(平空)"
    STOP_LOSS = "停損"
    TAKE_PROFIT = "停利"


@dataclass
class TradingSignal:
    symbol: str
    stock_name: str
    signal_type: SignalType
    price: float
    reason: str
    confidence: int  # 0-100
    timestamp: datetime
    
    # 進場相關
    support: float = 0
    resistance: float = 0
    vwap: float = 0
    ofi: float = 0
    
    # 停損停利
    stop_loss: float = 0
    take_profit: float = 0


def judge_trend(price: float, vwap: float, ofi: float, volume_price: str, change_pct: float) -> dict:
    """
    改進的趨勢判斷函數
    結合價格、VWAP、OFI、量價確認進行多維度判斷
    
    Returns:
        dict: {
            'trend': str,           # 趨勢描述
            'strength': int,        # 強度 1-5
            'safe_to_long': bool,   # 是否適合做多
            'safe_to_short': bool,  # 是否適合做空
            'warning': str          # 警告訊息
        }
    """
    trend = "中性"
    strength = 3
    safe_to_long = False
    safe_to_short = False
    warning = ""
    
    # 價格相對於 VWAP 的位置
    above_vwap = price > vwap if vwap > 0 else True
    
    # 🔴 判斷邏輯：OFI 是關鍵
    if above_vwap:
        # 價格在 VWAP 上方
        if ofi > 1000:  # OFI > +10萬
            trend = "💪 強多方控盤"
            strength = 5
            safe_to_long = True
        elif ofi > 0:
            trend = "📈 多方控盤"
            strength = 4
            safe_to_long = True
        elif ofi > -500:  # OFI 略微負
            trend = "⚠️ 多方偏弱"
            strength = 3
            warning = "資金流出中，注意反轉"
        else:  # OFI < -500
            trend = "🚨 假多頭，主力出貨"
            strength = 2
            safe_to_short = True
            warning = "價格在 VWAP 上方但主力在拋售！"
    else:
        # 價格在 VWAP 下方
        if ofi < -1000:  # OFI < -10萬
            trend = "💀 空方主導"
            strength = 1
            safe_to_short = True
        elif ofi < 0:
            trend = "📉 空方控盤"
            strength = 2
            safe_to_short = True
        elif ofi > 500:  # OFI 正向
            trend = "🔄 可能反彈"
            strength = 3
            warning = "價格低於 VWAP 但資金流入"
            safe_to_long = True  # 逆勢做多機會
        else:
            trend = "😐 弱勢盤整"
            strength = 2
    
    # 🟢 量價確認加成
    if '價跌量增' in volume_price:
        # 價跌量增 = 出貨訊號，降級所有做多判斷
        safe_to_long = False
        safe_to_short = True
        warning = "🚨 價跌量增 (出貨訊號)"
        strength = min(strength, 2)
    elif '價漲量增' in volume_price:
        # 價漲量增 = 健康上漲
        if safe_to_long:
            strength = min(strength + 1, 5)
    elif '價漲量縮' in volume_price:
        # 價漲量縮 = 上漲動能不足
        warning = warning or "上漲動能不足"
    
    return {
        'trend': trend,
        'strength': strength,
        'safe_to_long': safe_to_long,
        'safe_to_short': safe_to_short,
        'warning': warning
    }


class DayTradingSignalMonitor:
    """當沖自動訊號監控器"""
    
    def __init__(self):
        self.is_running = False
        self.monitored_stocks: Dict[str, Dict] = {}  # symbol -> last signal info
        self.signal_cooldown: Dict[str, datetime] = {}  # symbol -> last signal time
        self.cooldown_seconds = 300  # 5 分鐘冷卻
        
        # 🆕 風控設定
        self.min_rr_ratio = 1.5  # 最低風險報酬比
        self.opening_wait_minutes = 20  # 開盤等待 20 分鐘 (09:20 才能進場)
        
        # 🆕 時段停損設定 (ATR 倍數)
        self.stop_loss_multipliers = {
            'opening': 2.0,    # 09:00-09:30 開盤波動期
            'golden': 1.5,     # 09:30-11:00 黃金時段
            'normal': 1.3,     # 11:00+ 其他時段
        }
        
        # Email 設定
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = os.getenv('EMAIL_USERNAME') or os.getenv('SENDER_EMAIL', '')
        self.sender_password = os.getenv('EMAIL_PASSWORD') or os.getenv('SENDER_PASSWORD', '')
        self.recipients = self._get_recipients()
        
        logger.info("🎯 當沖自動訊號監控器已初始化 (R/R >= 1.5, 09:20 後進場)")
    
    def _get_recipients(self) -> List[str]:
        recipients_str = os.getenv('EMAIL_RECIPIENTS') or os.getenv('RECIPIENT_EMAILS', '')
        return [r.strip() for r in recipients_str.split(',') if r.strip()]
    
    async def _track_rejected_signal(
        self,
        symbol: str,
        stock_name: str,
        price: float,
        vwap: float,
        vwap_deviation: float,
        kd_k: float,
        ofi: float,
        rejection_reasons: List[str],
        risk_score: int
    ):
        """啟動被拒絕訊號的事後追蹤"""
        try:
            from app.services.signal_tracker import signal_tracker
            from app.services.rejected_signal import RejectedSignal
            from datetime import datetime
            
            # 計算虛擬停損停利
            stop_loss = price * 0.97  # -3%
            take_profit = price * 1.05  # +5%
            
            signal = RejectedSignal(
                signal_id=f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                stock_code=symbol,
                stock_name=stock_name,
                reject_time=datetime.now(),
                price_at_reject=price,
                vwap=vwap,
                vwap_deviation=vwap_deviation,
                kd_k=kd_k,
                kd_d=0,
                ofi=ofi,
                volume_trend="",
                price_trend="",
                rejection_reasons=rejection_reasons,
                risk_score=risk_score,
                virtual_entry_price=price,
                virtual_stop_loss=stop_loss,
                virtual_take_profit=take_profit
            )
            
            signal_tracker.add_rejected_signal(signal)
            
        except Exception as e:
            logger.error(f"追蹤拒絕訊號失敗: {e}")
    
    async def start(self):
        """啟動監控"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("🚀 當沖自動訊號監控器已啟動")
        asyncio.create_task(self._monitor_loop())
    
    async def stop(self):
        """停止監控"""
        self.is_running = False
        logger.info("🛑 當沖自動訊號監控器已停止")
    
    async def _monitor_loop(self):
        """主監控循環"""
        while self.is_running:
            try:
                now = datetime.now()
                current_time = now.time()
                
                # 🆕 改進的時間控制
                market_open = datetime.strptime("09:00", "%H:%M").time()
                safe_open = datetime.strptime("09:20", "%H:%M").time()  # 安全進場時間
                new_entry_close = datetime.strptime("11:30", "%H:%M").time()  # 停止新進場
                market_close = datetime.strptime("13:30", "%H:%M").time()
                
                from app.utils.twse_calendar import twse_calendar
                if not twse_calendar.is_trading_day(now):
                    logger.debug("休市或週末，跳過監控")
                elif current_time < market_open:
                    logger.debug("尚未開盤")
                elif current_time < safe_open:
                    logger.debug(f"⏰ 開盤波動期 ({current_time.strftime('%H:%M')})，等待 09:20 再進場")
                elif current_time > new_entry_close:
                    logger.debug(f"🚫 {current_time.strftime('%H:%M')} 後不發新進場訊號")
                elif current_time <= market_close:
                    # ✅ 大盤環境閘門：VIX 過高或大盤重跌時，停止發進場訊號
                    market_ok = await self._check_market_conditions()
                    if market_ok:
                        await self._check_all_stocks()
                
                # 每 30 秒檢查一次
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                await asyncio.sleep(10)

    async def _check_market_conditions(self) -> bool:
        """
        大盤環境閘門：
        - VIX > 25 → 恐慌市場，停止當沖做多訊號
        - 加權指數跌幅 > 1.5% → 系統性下跌，停止進場
        Return True = 市場安全，可以發訊號；False = 停止發訊號
        """
        try:
            import yfinance as yf
            import asyncio

            def _fetch():
                try:
                    vix = yf.Ticker('^VIX').history(period='1d')
                    twii = yf.Ticker('^TWII').history(period='2d')
                    vix_val = float(vix['Close'].iloc[-1]) if len(vix) > 0 else 18.0
                    if len(twii) >= 2:
                        twii_chg = (twii['Close'].iloc[-1] - twii['Close'].iloc[-2]) / twii['Close'].iloc[-2] * 100
                    else:
                        twii_chg = 0.0
                    return vix_val, twii_chg
                except:
                    return 18.0, 0.0

            vix_val, twii_chg = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=8.0)

            if vix_val > 25:
                logger.warning(f"🚨 [市場閘門] VIX={vix_val:.1f} > 25，市場恐慌，停止發當沖進場訊號")
                return False

            if twii_chg < -1.5:
                logger.warning(f"🚨 [市場閘門] 加權指數跌 {twii_chg:.1f}%，系統性下跌，停止發當沖進場訊號")
                return False

            logger.debug(f"✅ [市場閘門] VIX={vix_val:.1f}, 加權={twii_chg:+.1f}%，市場環境正常")
            return True

        except Exception as e:
            logger.warning(f"市場閘門檢查失敗，預設允許: {e}")
            return True  # 若無法取得資料，不阻擋（避免影響正常運作）


    async def _check_all_stocks(self):
        """檢查所有監控中的股票"""
        try:
            # 取得 ORB watchlist
            from app.services.smart_simulation_trader import smart_trader
            watchlist = getattr(smart_trader, 'orb_watchlist', [])
            
            if not watchlist:
                return
            
            for symbol in watchlist[:10]:  # 最多同時監控 10 檔
                try:
                    signal = await self._analyze_stock(symbol)
                    if signal:
                        await self._process_signal(signal)
                except Exception as e:
                    logger.debug(f"分析 {symbol} 時發生錯誤: {e}")
                
                await asyncio.sleep(1)  # 避免 API 過載
                
        except Exception as e:
            logger.error(f"檢查股票時發生錯誤: {e}")
    
    
    async def _analyze_stock(self, symbol: str) -> Optional[TradingSignal]:
        """分析單一股票，判斷是否產生訊號"""
        try:
            # 取得報價
            from app.services.fubon_service import get_realtime_quote
            quote = await get_realtime_quote(symbol)
            
            if not quote or quote.get('price', 0) <= 0:
                return None
            
            price = quote.get('price', 0)
            
            # 取得綜合分析
            from app.services.stock_comprehensive_analyzer import analyze_stock_comprehensive
            analysis = await analyze_stock_comprehensive(symbol)
            
            if not analysis:
                return None
            
            # 取得關鍵指標
            vpa = analysis.get('volume_price_analysis', {})
            inst = analysis.get('institutional_trading', {})
            
            vwap = vpa.get('vwap', 0)
            vwap_deviation = vpa.get('vwap_deviation', 0)
            confirmation = vpa.get('confirmation_signal', '')
            volume_price_text = vpa.get('volume_price_confirmation', '')
            
            # 🆕 使用即時 VWAP 追蹤器取得正確的當日 VWAP 乖離
            try:
                from app.services.vwap_tracker import vwap_tracker
                
                # 取得即時計算的 VWAP 偏離（如果有 tick 資料的話）
                realtime_deviation = vwap_tracker.get_deviation(symbol, price)
                
                if realtime_deviation != 0:
                    # 使用即時追蹤器的值
                    if abs(realtime_deviation - vwap_deviation) > 5:
                        logger.info(f"⚠️ {symbol} VWAP偏離校正: API={vwap_deviation:.1f}% -> 即時={realtime_deviation:.1f}%")
                    vwap_deviation = realtime_deviation
                    vwap = vwap_tracker.get_vwap(symbol)
                elif vwap > 0 and price > 0:
                    # 沒有 tick 資料，用 API VWAP 重新計算偏離
                    calc_deviation = ((price - vwap) / vwap) * 100
                    if abs(calc_deviation - vwap_deviation) > 5:
                        logger.info(f"⚠️ {symbol} VWAP偏離校正: API={vwap_deviation:.1f}% -> 計算={calc_deviation:.1f}%")
                        vwap_deviation = calc_deviation
            except Exception as e:
                logger.debug(f"VWAP 追蹤器錯誤: {e}")
            
            # 計算 OFI (大戶資金流)
            foreign_net = inst.get('foreign_net', 0) or 0
            trust_net = inst.get('trust_net', 0) or 0
            ofi = (foreign_net + trust_net) / 100
            
            # 🆕 取得成交量數據
            volume = quote.get('volume', 0)
            prev_volume = vpa.get('avg_volume', volume)  # 平均成交量
            volume_ratio = volume / prev_volume if prev_volume > 0 else 1.0
            
            # 取得 KD 值
            tech_data = analysis.get('technical_indicators', {})
            kd_k = tech_data.get('kd_k', 50)
            kd_d = tech_data.get('kd_d', 50)
            
            # ========================================
            # 🚨 第一層：致命訊號否決機制 (FATAL SIGNAL VETO)
            # 任何一個致命訊號都直接否決
            # ========================================
            fatal_signals = []
            
            # 致命訊號 1：VWAP 乖離過大 (> 30% 絕對禁止)
            if vwap_deviation >= 30:
                fatal_signals.append(f"🚨 VWAP 乖離極大 (+{vwap_deviation:.1f}%)")
            
            # 致命訊號 2：KD 極度超買 (K > 90)
            if kd_k > 90:
                fatal_signals.append(f"🚨 KD 極度超買 (K:{kd_k:.0f})")
            
            # 致命訊號 3：大戶大量拋售 (OFI < -50)
            if ofi < -50:
                fatal_signals.append(f"🚨 大戶大量拋售 (OFI:{ofi:.1f})")
            
            # 致命訊號 4：價跌量增 (出貨訊號)
            change_pct = quote.get('change', 0)
            is_price_down = change_pct < -0.5
            is_volume_up = volume_ratio > 1.2
            if is_price_down and is_volume_up:
                fatal_signals.append("🚨 價跌量增 (出貨訊號)")
            
            # 如果有致命訊號，直接返回 None
            if fatal_signals:
                logger.warning(f"🚫 {symbol} 致命訊號: {', '.join(fatal_signals)} - 禁止進場")
                # 🆕 啟動事後追蹤
                await self._track_rejected_signal(
                    symbol=symbol,
                    stock_name=stock_name if 'stock_name' in dir() else symbol,
                    price=price,
                    vwap=vwap,
                    vwap_deviation=vwap_deviation,
                    kd_k=kd_k,
                    ofi=ofi,
                    rejection_reasons=fatal_signals,
                    risk_score=9  # 致命訊號 = 最高風險
                )
                return None
            
            # ========================================
            # ⚠️ 第二層：組合風險評估 (累計風險分數)
            # 單一不致命，但多個累積就危險
            # ========================================
            risk_score = 0
            risk_reasons = []
            
            # 風險 1：VWAP 乖離 (分級)
            if vwap_deviation >= 20:
                risk_score += 3
                risk_reasons.append(f"VWAP 乖離高 (+{vwap_deviation:.1f}%)")
            elif vwap_deviation >= 15:
                risk_score += 2
                risk_reasons.append(f"VWAP 乖離中 (+{vwap_deviation:.1f}%)")
            elif vwap_deviation >= 10:
                risk_score += 1
            
            # 風險 2：KD 超買 (分級)
            if kd_k > 85:
                risk_score += 2
                risk_reasons.append(f"KD 超買 (K:{kd_k:.0f})")
            elif kd_k > 80:
                risk_score += 1
            
            # 風險 3：OFI 分級
            if ofi < -10:
                risk_score += 3
                risk_reasons.append(f"大戶賣出 (OFI:{ofi:.1f})")
            elif ofi < 0:
                risk_score += 2
                risk_reasons.append(f"大戶小幅賣出 (OFI:{ofi:.1f})")
            elif ofi < 5:
                risk_score += 1  # OFI 接近 0，不確定性高
            
            # 風險 4：高位量縮 (警訊)
            if change_pct > 2 and volume_ratio < 0.8:
                risk_score += 1
                risk_reasons.append("高位量縮，動能不足")
            
            # 風險 5：價格低於支撐
            support_level = tech_data.get('support_1', 0)
            if support_level > 0 and price < support_level:
                risk_score += 2
                risk_reasons.append(f"跌破支撐 ({price:.1f} < {support_level:.1f})")
            
            # 組合風險檢查：風險分數 >= 7 不建議進場
            if risk_score >= 7:
                logger.warning(f"⚠️ {symbol} 組合風險過高 ({risk_score}/9): {', '.join(risk_reasons)} - 不建議進場")
                # 🆕 啟動事後追蹤
                await self._track_rejected_signal(
                    symbol=symbol,
                    stock_name=stock_name,
                    price=price,
                    vwap=vwap,
                    vwap_deviation=vwap_deviation,
                    kd_k=kd_k,
                    ofi=ofi,
                    rejection_reasons=risk_reasons,
                    risk_score=risk_score
                )
                return None
            
            # 風險分數 >= 5 記錄警告但允許繼續評估
            if risk_score >= 5:
                logger.info(f"⚠️ {symbol} 中等風險 ({risk_score}/9): {', '.join(risk_reasons)}")
            
            # ========================================
            
            # 取得支撐壓力
            tech = analysis.get('technical_indicators', {})
            support = tech.get('support_1', 0) or quote.get('low', 0)
            resistance = tech.get('resistance_1', 0) or quote.get('high', 0)
            
            # 🆕 計算 ATR (平均真實波幅) 用於設定合理停損停利
            today_high = quote.get('high', price)
            today_low = quote.get('low', price)
            atr = max(today_high - today_low, price * 0.02)  # 至少 2%
            
            # 🆕 根據時段計算動態停損距離
            current_time = datetime.now().time()
            if current_time < datetime.strptime("09:30", "%H:%M").time():
                stop_multiplier = self.stop_loss_multipliers['opening']  # 2.0
            elif current_time < datetime.strptime("11:00", "%H:%M").time():
                stop_multiplier = self.stop_loss_multipliers['golden']  # 1.5
            else:
                stop_multiplier = self.stop_loss_multipliers['normal']  # 1.3
            
            stop_distance = atr * stop_multiplier
            target_distance = stop_distance * 2.0  # 🆕 目標距離 = 停損距離 × 2 (R/R = 2.0)
            
            # 🆕 優先使用繁體中文名稱
            from app.services.market_scanner import STOCK_NAMES_TW
            stock_name = STOCK_NAMES_TW.get(symbol) or analysis.get('stock_name', symbol)
            
            # ========================================
            # 🆕 改進的趨勢判斷 (使用 judge_trend 函數)
            # ========================================
            trend_result = judge_trend(
                price=price,
                vwap=vwap,
                ofi=ofi,
                volume_price=volume_price_text,
                change_pct=change_pct
            )
            
            # 如果趨勢判斷不適合做多，直接返回
            if not trend_result['safe_to_long']:
                if trend_result['warning']:
                    logger.info(f"⚠️ {symbol} 趨勢不適合做多: {trend_result['trend']} - {trend_result['warning']}")
                return None
            
            # ========================================
            # ===== 判斷進場條件 (做多) =====
            # 🆕 新權重: OFI 40%, 量價 30%, 技術 20%, VWAP 10%
            # ========================================
            entry_reasons = []
            entry_reasons.append(f"趨勢: {trend_result['trend']}")
            entry_confidence = 0

            # ✅ LSTM 閘門：若 LSTM 預測下跌，直接封鎖進場
            try:
                import httpx
                async with httpx.AsyncClient(timeout=4.0) as hc:
                    resp = await hc.get(f"http://127.0.0.1:8000/api/lstm/predict/{symbol}")
                    if resp.status_code == 200:
                        lstm_data = resp.json()
                        lstm_dir = lstm_data.get('prediction', {}).get('direction', 'neutral')
                        lstm_conf = lstm_data.get('prediction', {}).get('confidence', 50)
                        if lstm_dir == 'down' and lstm_conf >= 60:
                            logger.warning(f"🤖 [LSTM閘門] {symbol} LSTM預測下跌（信心{lstm_conf}%），封鎖進場訊號")
                            return None
                        elif lstm_dir == 'up' and lstm_conf >= 60:
                            entry_reasons.append(f"🤖 LSTM預測上漲({lstm_conf}%)")
                            entry_confidence += 10  # LSTM 確認加分
            except Exception:
                pass  # LSTM 服務不可用時不影響正常判斷


            # 從分析結果取得技術指標
            tech = analysis.get('technical_indicators', {})
            ma5 = tech.get('ma5', 0)
            ma10 = tech.get('ma10', 0)
            ma20 = tech.get('ma20', 0)
            kd_k = tech.get('kd_k', 50)
            kd_d = tech.get('kd_d', 50)
            rsi = tech.get('rsi_14', 50)
            
            # ========================================
            # 🆕 新權重計算 (總分 100)
            # OFI: 40%  量價: 30%  技術: 20%  VWAP: 10%
            # ========================================
            
            # 🔴 條件1: OFI 資金流 (權重 40%)
            if ofi > 1000:  # OFI > 10萬 (強力買進)
                entry_reasons.append(f"💰 大戶強力買進 (OFI: {ofi:,.0f})")
                entry_confidence += 40
            elif ofi > 500:  # OFI > 5萬 (買進中)
                entry_reasons.append(f"📈 大戶買進中 (OFI: {ofi:,.0f})")
                entry_confidence += 30
            elif ofi > 0:  # OFI > 0 (小幅買進)
                entry_reasons.append(f"大戶小幅買進 (OFI: {ofi:,.0f})")
                entry_confidence += 15
            elif ofi < -500:  # OFI < -5萬 (賣出) - 扣分！
                entry_confidence -= 20
            
            # 🟢 條件2: 量價確認 (權重 30%)
            if confirmation in ['bullish_confirmation', 'bullish_divergence']:
                if '價漲量增' in volume_price_text or 'bullish' in confirmation:
                    entry_reasons.append(f"✅ 量價健康 (價漲量增)")
                    entry_confidence += 30
                else:
                    entry_reasons.append(f"量價確認: {volume_price_text}")
                    entry_confidence += 20
            elif '量縮' in volume_price_text and change_pct >= 0:
                entry_reasons.append(f"賣壓枯竭: {volume_price_text}")
                entry_confidence += 15
            
            # 🔵 條件3: 技術指標 (權重 20%)
            tech_score = 0
            # 均線多頭排列
            if ma5 > 0 and ma10 > 0 and ma20 > 0:
                if price > ma5 > ma10 > ma20:
                    entry_reasons.append(f"📈 均線多頭排列")
                    tech_score += 10
                elif price > ma5 > ma10:
                    tech_score += 5
            
            # KD 向上
            if kd_k > kd_d and kd_k > 20 and kd_k < 80:
                entry_reasons.append(f"📊 KD 向上 (K:{kd_k:.0f})")
                tech_score += 10
            
            entry_confidence += min(tech_score, 20)  # 最多 20 分
            
            # 🟡 條件4: VWAP 偏離度 (權重 10%)
            if vwap > 0:
                if 0 <= vwap_deviation <= 2:  # 合理乖離
                    entry_reasons.append(f"VWAP 偏離健康 (+{vwap_deviation:.1f}%)")
                    entry_confidence += 10
                elif -2 <= vwap_deviation < 0:  # 略低於 VWAP
                    entry_confidence += 5
            
            # ===== 策略1: 支撐反彈型 =====
            # 進場訊號：信心度 >= 60%
            if entry_confidence >= 60:
                # 🆕 計算停損停利
                stop_loss = round(price - stop_distance, 2)
                take_profit = round(price + target_distance, 2)
                
                # 🆕 計算風險報酬比
                risk = price - stop_loss
                reward = take_profit - price
                rr_ratio = reward / risk if risk > 0 else 0
                
                # 🆕 風險報酬比檢查
                if rr_ratio < self.min_rr_ratio:
                    logger.info(f"⚠️ {symbol} R/R={rr_ratio:.2f} < {self.min_rr_ratio}，不發訊號")
                    return None
                
                entry_reasons.append(f"R/R={rr_ratio:.1f}")
                
                return TradingSignal(
                    symbol=symbol,
                    stock_name=stock_name,
                    signal_type=SignalType.ENTRY_LONG,
                    price=price,
                    reason=f"【支撐反彈】" + " + ".join(entry_reasons),
                    confidence=min(entry_confidence, 100),
                    timestamp=datetime.now(),
                    support=support,
                    resistance=resistance,
                    vwap=vwap,
                    ofi=ofi,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            
            # ===== 策略2: 突破追擊型 (捕捉強勢股/漲停股) =====
            # 🆕 突破型也必須檢查資金流！
            breakout_reasons = []
            breakout_confidence = 0
            
            # 取得量比和更多數據
            volume = quote.get('volume', 0)
            prev_close = quote.get('previousClose', 0) or quote.get('prev_close', 0)
            open_price = quote.get('open', 0)
            high_price = quote.get('high', 0)
            change_pct = quote.get('change', 0)
            
            # 計算漲停價 (約 10%)
            limit_up = prev_close * 1.10 if prev_close > 0 else 0
            
            # 🚨 突破型的致命訊號檢查
            # 1. OFI 必須為正 (大戶在買，不能追沒有資金支持的)
            if ofi < 0:
                logger.info(f"⚠️ {symbol} 突破追擊取消: OFI={ofi:.1f} < 0 (大戶未買進)")
                # 不設定 breakout_confidence，讓突破策略不觸發
            
            # 2. VWAP 偏離不能過高 (> 20% 太危險，追高被套)
            elif vwap_deviation > 20:
                logger.info(f"⚠️ {symbol} 突破追擊取消: VWAP偏離 +{vwap_deviation:.1f}% > 20% (追高風險)")
            
            else:
                # 條件B1: 強勢上漲 (> 5%)
                if change_pct >= 5:
                    breakout_reasons.append(f"強勢上漲 +{change_pct:.1f}%")
                    breakout_confidence += 30
                    
                    # 接近或達到漲停
                    if change_pct >= 9:
                        breakout_reasons.append("🚀 接近漲停!")
                        breakout_confidence += 20
                
                # 條件B2: 價格在高檔區 (接近今日最高)
                if high_price > 0 and price >= high_price * 0.995:
                    breakout_reasons.append(f"價格在高檔區 (今高 {high_price:.1f})")
                    breakout_confidence += 15
                
                # 條件B3: 突破開盤價 (跳空後續強)
                if open_price > 0 and prev_close > 0:
                    gap = (open_price - prev_close) / prev_close * 100
                    if gap >= 3 and price > open_price:
                        breakout_reasons.append(f"跳空突破 ({gap:.1f}%)")
                        breakout_confidence += 20
                
                # 條件B4: 外盤力道強 (VWAP 偏離度適中 3-15%)
                if vwap > 0 and 3 <= vwap_deviation <= 15:
                    breakout_reasons.append(f"買盤強勢 (偏離VWAP +{vwap_deviation:.1f}%)")
                    breakout_confidence += 15
                
                # 條件B5: 大戶積極買進 (OFI > 5)
                if ofi > 5:
                    breakout_reasons.append(f"大戶積極買進 (OFI: {ofi:.1f})")
                    breakout_confidence += 20
            
            # 突破追擊進場：信心度 >= 65%
            if breakout_confidence >= 65:
                # 突破型停損較嚴格（買高賣更高，快進快出）
                stop_loss = round(price * 0.97, 2)  # 3% 停損
                take_profit = round(limit_up if limit_up > price else price * 1.05, 2)  # 目標漲停或 5%
                
                return TradingSignal(
                    symbol=symbol,
                    stock_name=stock_name,
                    signal_type=SignalType.ENTRY_LONG,
                    price=price,
                    reason=f"【突破追擊】" + " + ".join(breakout_reasons),
                    confidence=min(breakout_confidence, 100),
                    timestamp=datetime.now(),
                    support=stop_loss,  # 用止損價當支撐
                    resistance=take_profit,  # 用目標價當壓力
                    vwap=vwap,
                    ofi=ofi,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            
            # ===== 判斷出場條件 =====
            last_signal = self.monitored_stocks.get(symbol)
            if last_signal and last_signal.get('signal_type') == SignalType.ENTRY_LONG:
                exit_reasons = []
                exit_type = None
                
                # 停損: 跌破支撐位
                entry_support = last_signal.get('support', support)
                if price < entry_support * 0.99:
                    exit_reasons.append(f"跌破支撐位 {entry_support:.1f}")
                    exit_type = SignalType.STOP_LOSS
                
                # 停利: 達到壓力位
                entry_resistance = last_signal.get('resistance', resistance)
                if price >= entry_resistance * 0.99:
                    exit_reasons.append(f"達到壓力位 {entry_resistance:.1f}")
                    exit_type = SignalType.TAKE_PROFIT
                
                # 大戶開始賣出
                if ofi < -10:
                    exit_reasons.append(f"大戶開始賣出 (OFI: {ofi:.1f})")
                    exit_type = SignalType.EXIT_LONG
                
                # 🆕 高點回落警告 (從當日高點回落 1%)
                entry_price = last_signal.get('price', price)
                day_high = quote.get('high', price)
                if day_high > entry_price and price < day_high * 0.99:
                    pullback_pct = (day_high - price) / day_high * 100
                    if pullback_pct >= 1.0:  # 回落 1%
                        exit_reasons.append(f"⚠️ 高點回落 {pullback_pct:.1f}% (高 {day_high:.1f} → 現 {price:.1f})")
                        if not exit_type:  # 如果還沒有其他出場原因
                            exit_type = SignalType.EXIT_LONG
                
                if exit_type:
                    return TradingSignal(
                        symbol=symbol,
                        stock_name=stock_name,
                        signal_type=exit_type,
                        price=price,
                        reason=" + ".join(exit_reasons),
                        confidence=85,
                        timestamp=datetime.now(),
                        support=support,
                        resistance=resistance,
                        vwap=vwap,
                        ofi=ofi
                    )
            
            return None
            
        except Exception as e:
            logger.debug(f"分析 {symbol} 失敗: {e}")
            return None
    
    async def _process_signal(self, signal: TradingSignal):
        """處理訊號：檢查冷卻時間並發送通知"""
        # 檢查冷卻時間
        last_signal_time = self.signal_cooldown.get(signal.symbol)
        if last_signal_time:
            elapsed = (datetime.now() - last_signal_time).total_seconds()
            if elapsed < self.cooldown_seconds:
                logger.debug(f"{signal.symbol} 在冷卻時間內，跳過 ({elapsed:.0f}s)")
                return
        
        # 🆕 記錄到 ML 訓練資料庫
        try:
            from app.services.ml_signal_tracker import ml_signal_tracker
            
            features = {
                'vwap': signal.vwap,
                'vwap_deviation': 0,  # TODO: 從分析數據中取得
                'ofi': signal.ofi,
                'support': signal.support,
                'resistance': signal.resistance,
                'volume_price_signal': signal.reason,
                'market_phase': self._get_current_phase()
            }
            
            await ml_signal_tracker.record_signal(
                stock_code=signal.symbol,
                stock_name=signal.stock_name,
                signal_type=signal.signal_type.name,
                entry_price=signal.price,
                features=features,
                signal_source="day_trading_auto",
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                confidence=signal.confidence
            )
            logger.info(f"📊 訊號已記錄到 ML 資料庫: {signal.symbol}")
        except Exception as e:
            logger.debug(f"ML 記錄失敗 (可能資料庫未設定): {e}")
        
        # 發送通知
        success = await self._send_notification(signal)
        
        if success:
            # 更新冷卻時間
            self.signal_cooldown[signal.symbol] = datetime.now()
            
            # 儲存訊號狀態
            self.monitored_stocks[signal.symbol] = {
                'signal_type': signal.signal_type,
                'price': signal.price,
                'support': signal.support,
                'resistance': signal.resistance,
                'timestamp': signal.timestamp
            }
            
            logger.info(f"✅ 已發送 {signal.symbol} {signal.signal_type.value} 訊號")
    
    def _get_current_phase(self) -> str:
        """取得目前交易階段"""
        now = datetime.now()
        hour, minute = now.hour, now.minute
        time_val = hour * 60 + minute
        
        if time_val < 9 * 60:
            return "pre_market"
        elif time_val < 9 * 60 + 5:
            return "anchor"
        elif time_val < 10 * 60 + 30:
            return "golden_attack"
        elif time_val < 11 * 60 + 30:
            return "morning_extend"
        elif time_val < 12 * 60 + 30:
            return "garbage_time"
        elif time_val < 13 * 60:
            return "afternoon_sprint"
        elif time_val < 13 * 60 + 25:
            return "closing_escape"
        else:
            return "final_auction"
    
    async def _send_notification(self, signal: TradingSignal) -> bool:
        """發送 Email 通知"""
        if not self.sender_email or not self.sender_password or not self.recipients:
            logger.warning("Email 設定不完整，跳過通知")
            return False
        
        try:
            # 決定顏色和 emoji
            if signal.signal_type in [SignalType.ENTRY_LONG, SignalType.TAKE_PROFIT]:
                bg_color = "linear-gradient(135deg, #ef4444, #dc2626)"
                emoji = "🔴"
                action = "買進" if signal.signal_type == SignalType.ENTRY_LONG else "停利"
            else:
                bg_color = "linear-gradient(135deg, #22c55e, #16a34a)"
                emoji = "🟢"
                action = "賣出" if signal.signal_type == SignalType.EXIT_LONG else "停損"
            
            subject = f"🎯 當沖{action}訊號 - {signal.symbol} {signal.stock_name} @ ${signal.price:.2f}"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"></head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; background: #f5f5f5;">
                <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                    <div style="background: {bg_color}; color: white; padding: 24px; text-align: center;">
                        <h1 style="margin: 0; font-size: 28px;">{emoji} {signal.signal_type.value}</h1>
                        <p style="margin: 8px 0 0; font-size: 20px; font-weight: bold;">{signal.symbol} {signal.stock_name}</p>
                    </div>
                    <div style="padding: 24px;">
                        <div style="display: grid; gap: 12px;">
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #fef3c7; border-radius: 8px; border: 1px solid #fcd34d;">
                                <span style="color: #92400e;">📡 訊號管道</span>
                                <span style="font-weight: bold; color: #92400e;">當沖監控 (自動)</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #f9fafb; border-radius: 8px;">
                                <span style="color: #6b7280;">💰 當前價格</span>
                                <span style="font-weight: bold; font-size: 18px;">${signal.price:.2f}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #f9fafb; border-radius: 8px;">
                                <span style="color: #6b7280;">⭐ 信心度</span>
                                <span style="font-weight: bold; color: #7c3aed;">{signal.confidence}%</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #f9fafb; border-radius: 8px;">
                                <span style="color: #6b7280;">📊 觸發原因</span>
                                <span style="font-weight: bold;">{signal.reason}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #f9fafb; border-radius: 8px;">
                                <span style="color: #6b7280;">📈 VWAP</span>
                                <span style="font-weight: bold;">${signal.vwap:.2f}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #f9fafb; border-radius: 8px;">
                                <span style="color: #6b7280;">💹 大戶資金流</span>
                                <span style="font-weight: bold; color: {'#dc2626' if signal.ofi > 0 else '#16a34a'};">{signal.ofi:.1f}</span>
                            </div>
                            {'<div style="display: flex; justify-content: space-between; padding: 14px; background: #fef2f2; border-radius: 8px; border: 1px solid #fecaca;"><span style="color: #dc2626;">🛡️ 建議停損</span><span style="font-weight: bold; color: #dc2626;">${:.2f}</span></div>'.format(signal.stop_loss) if signal.stop_loss > 0 else ''}
                            {'<div style="display: flex; justify-content: space-between; padding: 14px; background: #f0fdf4; border-radius: 8px; border: 1px solid #bbf7d0;"><span style="color: #16a34a;">🎯 建議停利</span><span style="font-weight: bold; color: #16a34a;">${:.2f}</span></div>'.format(signal.take_profit) if signal.take_profit > 0 else ''}
                            <div style="display: flex; justify-content: space-between; padding: 14px; background: #f9fafb; border-radius: 8px;">
                                <span style="color: #6b7280;">⏰ 時間</span>
                                <span style="font-weight: bold;">{signal.timestamp.strftime('%H:%M:%S')}</span>
                            </div>
                        </div>
                        
                        <!-- 🆕 快速操作按鈕 -->
                        <div style="margin-top: 20px; text-align: center;">
                            {'<a href="http://TWAAMHQ32.local:8000/api/quick-trade/open/' + signal.symbol + '?price=' + str(signal.price) + '&stop_loss=' + str(signal.stop_loss) + '&take_profit=' + str(signal.take_profit) + '" style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #dc2626, #b91c1c); color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 5px;">📈 快速建倉</a>' if signal.signal_type == SignalType.ENTRY_LONG else '<a href="http://TWAAMHQ32.local:8000/api/quick-trade/close/' + signal.symbol + '" style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #16a34a, #15803d); color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 5px;">💰 快速平倉</a>'}
                        </div>
                        <p style="margin-top: 10px; text-align: center; color: #9ca3af; font-size: 11px;">
                            ⚠️ 點擊連結將自動執行交易，請確認後再點擊
                        </p>
                    </div>
                    <div style="padding: 16px 24px; background: #f9fafb; text-align: center; color: #9ca3af; font-size: 12px;">
                        當沖狙擊手 Pro v3.0 | 自動訊號監控系統
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipients)
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipients, msg.as_string())
            
            logger.info(f"✅ 當沖訊號郵件已發送: {signal.symbol} {signal.signal_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 發送郵件失敗: {e}")
            return False


# 全域單例
day_trading_monitor = DayTradingSignalMonitor()
