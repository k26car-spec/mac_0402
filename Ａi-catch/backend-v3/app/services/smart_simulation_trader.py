"""
智能模擬下單系統 v3.3 - 黃金時程表版
Smart Simulation Trading System

🔥 v3.3 升級重點：
1. 五階段黃金時程表
2. 禁止新倉時間 (13:00 後)
3. 強制平倉機制 (13:00-13:25)
4. 垃圾時間過濾 (11:30-12:30)
5. 定錨期等待 (09:00-09:05)

時程表：
- 08:45-09:00: 盤前試撮 (禁止下單)
- 09:00-09:05: 定錨期 (觀察不動作)
- 09:05-10:30: 黃金進攻期 (權重 100%)
- 10:30-11:30: 早盤續航 (權重 75%)
- 11:30-12:30: 垃圾時間 (權重 25%)
- 12:30-13:00: 尾盤衝刺 (權重 50%)
- 13:00-13:25: 結算逃命 (禁止新倉, 強制平倉)
- 13:25-13:30: 收盤集合競價 (只出不進)
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.models.portfolio import Portfolio, TradeRecord

logger = logging.getLogger(__name__)


# ============ 時段定義 ============
class TradingPhase:
    """交易時段枚舉"""
    PRE_MARKET = "pre_market"           # 盤前試撮 08:45-09:00
    ANCHOR = "anchor"                    # 定錨期 09:00-09:05
    GOLDEN_ATTACK = "golden_attack"      # 黃金進攻期 09:05-10:30
    MORNING_EXTEND = "morning_extend"    # 早盤續航 10:30-11:30
    GARBAGE_TIME = "garbage_time"        # 垃圾時間 11:30-12:30
    AFTERNOON_SPRINT = "afternoon_sprint"  # 尾盤衝刺 12:30-13:00
    CLOSING_ESCAPE = "closing_escape"    # 結算逃命 13:00-13:25
    FINAL_AUCTION = "final_auction"      # 收盤集合競價 13:25-13:30
    MARKET_CLOSED = "market_closed"      # 收盤


PHASE_CONFIG = {
    TradingPhase.PRE_MARKET: {
        "name": "盤前試撮", "weight": 0, "allow_new_position": False, 
        "force_close": False, "color": "gray", "emoji": "⏳"
    },
    TradingPhase.ANCHOR: {
        "name": "定錨期", "weight": 0, "allow_new_position": False,
        "force_close": False, "color": "blue", "emoji": "⚓"
    },
    TradingPhase.GOLDEN_ATTACK: {
        "name": "黃金進攻期", "weight": 100, "allow_new_position": True,
        "force_close": False, "color": "gold", "emoji": "🚀"
    },
    TradingPhase.MORNING_EXTEND: {
        "name": "早盤續航", "weight": 75, "allow_new_position": True,
        "force_close": False, "color": "green", "emoji": "📈"
    },
    TradingPhase.GARBAGE_TIME: {
        "name": "垃圾時間", "weight": 25, "allow_new_position": False,
        "force_close": False, "color": "orange", "emoji": "💤"
    },
    TradingPhase.AFTERNOON_SPRINT: {
        "name": "尾盤衝刺", "weight": 50, "allow_new_position": True,
        "force_close": False, "color": "purple", "emoji": "⚡"
    },
    TradingPhase.CLOSING_ESCAPE: {
        "name": "結算逃命", "weight": 0, "allow_new_position": False,
        "force_close": True, "color": "red", "emoji": "🚨"
    },
    TradingPhase.FINAL_AUCTION: {
        "name": "收盤集合競價", "weight": 0, "allow_new_position": False,
        "force_close": True, "color": "darkred", "emoji": "🔔"
    },
    TradingPhase.MARKET_CLOSED: {
        "name": "已收盤", "weight": 0, "allow_new_position": False,
        "force_close": False, "color": "gray", "emoji": "💤"
    },
}


class SmartForceCloseManager:
    """
    智能強制平倉管理器 v2.0
    
    三階段漸進式平倉，避免一刀切虧損：
    - 階段 1 (13:15-13:20)：選擇性平倉（虧損 > 1% 才平）
    - 階段 2 (13:20-13:25)：漸進平倉（虧損或小獲利平）
    - 階段 3 (13:25-13:30)：全部平倉
    """
    
    def __init__(self):
        self.phase1_start = time(13, 15)   # 選擇性平倉開始
        self.phase2_start = time(13, 20)   # 漸進平倉開始
        self.phase3_start = time(13, 25)   # 全部平倉開始
        self.market_close = time(13, 30)   # 收盤
    
    def should_force_close(self, position: Dict, current_time: time = None) -> Dict:
        """
        判斷是否應該強制平倉
        
        Args:
            position: 持倉資料，包含 entry_time, pnl_pct
            current_time: 當前時間（None 則使用系統時間）
        
        Returns:
            Dict with keys: should_close, reason, urgency
        """
        if current_time is None:
            current_time = datetime.now().time()
        
        entry_time = position.get('entry_time')
        pnl_pct = position.get('pnl_pct', 0)
        
        # 計算持倉時間（分鐘）
        if isinstance(entry_time, datetime):
            hold_minutes = (datetime.now() - entry_time).total_seconds() / 60
        else:
            hold_minutes = 120  # 預設 2 小時
        
        # === 階段 1：13:15-13:20（選擇性平倉）===
        if self.phase1_start <= current_time < self.phase2_start:
            
            # 虧損 > 1% → 立即平倉
            if pnl_pct < -1:
                return {
                    'should_close': True,
                    'reason': f'虧損 {pnl_pct:.2f}%，提早止損',
                    'urgency': 'HIGH'
                }
            
            # 持倉時間 < 1 小時 → 繼續持有
            elif hold_minutes < 60:
                return {
                    'should_close': False,
                    'reason': f'持倉僅 {hold_minutes:.0f} 分鐘，給時間發展',
                    'next_check': 5
                }
            
            # 小虧或平盤 → 繼續持有
            elif -1 <= pnl_pct <= 0:
                return {
                    'should_close': False,
                    'reason': f'小虧 {pnl_pct:.2f}%，等待反彈',
                    'next_check': 3
                }
            
            # 獲利 → 保留
            else:
                return {
                    'should_close': False,
                    'reason': f'獲利 {pnl_pct:+.2f}%，繼續持有',
                    'next_check': 5
                }
        
        # === 階段 2：13:20-13:25（漸進平倉）===
        elif self.phase2_start <= current_time < self.phase3_start:
            
            # 虧損 → 平倉
            if pnl_pct < 0:
                return {
                    'should_close': True,
                    'reason': f'收盤前平倉（{pnl_pct:.2f}%）',
                    'urgency': 'MEDIUM'
                }
            
            # 小獲利（< 0.5%）→ 平倉
            elif 0 <= pnl_pct < 0.5:
                return {
                    'should_close': True,
                    'reason': f'小獲利鎖利（+{pnl_pct:.2f}%）',
                    'urgency': 'LOW'
                }
            
            # 較大獲利（>= 0.5%）→ 保留到 13:25
            else:
                return {
                    'should_close': False,
                    'reason': f'獲利 +{pnl_pct:.2f}%，保留到 13:25',
                    'next_check': 2
                }
        
        # === 階段 3：13:25-13:30（全部平倉）===
        elif self.phase3_start <= current_time <= self.market_close:
            return {
                'should_close': True,
                'reason': '收盤前 5 分鐘，強制平倉',
                'urgency': 'CRITICAL'
            }
        
        # 非平倉時段
        else:
            return {
                'should_close': False,
                'reason': '非平倉時段',
                'urgency': None
            }
    
    def get_order_type(self, urgency: str) -> str:
        """根據緊急程度決定下單方式"""
        if urgency == 'CRITICAL':
            return 'MARKET'           # 市價單，確保成交
        elif urgency == 'HIGH':
            return 'LIMIT_AGGRESSIVE'  # 限價單，稍微不利但快
        else:
            return 'LIMIT_PATIENT'     # 限價單，等待更好價格
    
    def get_status(self) -> Dict:
        """獲取當前平倉管理器狀態"""
        current_time = datetime.now().time()
        
        if current_time < self.phase1_start:
            phase = "正常交易"
            phase_num = 0
        elif current_time < self.phase2_start:
            phase = "選擇性平倉"
            phase_num = 1
        elif current_time < self.phase3_start:
            phase = "漸進平倉"
            phase_num = 2
        elif current_time <= self.market_close:
            phase = "全部平倉"
            phase_num = 3
        else:
            phase = "已收盤"
            phase_num = 4
        
        return {
            'current_time': current_time.strftime('%H:%M:%S'),
            'phase': phase,
            'phase_num': phase_num,
            'phase1_start': self.phase1_start.strftime('%H:%M'),
            'phase2_start': self.phase2_start.strftime('%H:%M'),
            'phase3_start': self.phase3_start.strftime('%H:%M')
        }


# 智能平倉管理器單例
smart_close_manager = SmartForceCloseManager()


class SmartSimulationTrader:
    """智能模擬交易器 v3.3 - 黃金時程表版"""
    
    def __init__(self):
        self.is_running = False
        self.check_interval = 60  # 每分鐘檢查
        
        # ============ v3.4 黃金時程表 (09:03 開始進攻) ============
        self.phase_times = {
            TradingPhase.PRE_MARKET: (time(8, 45), time(9, 0)),
            TradingPhase.ANCHOR: (time(9, 0), time(9, 3)),      # 🆕 縮短為 3 分鐘
            TradingPhase.GOLDEN_ATTACK: (time(9, 3), time(10, 30)),  # 🆕 09:03 開始
            TradingPhase.MORNING_EXTEND: (time(10, 30), time(11, 30)),
            TradingPhase.GARBAGE_TIME: (time(11, 30), time(12, 30)),
            TradingPhase.AFTERNOON_SPRINT: (time(12, 30), time(13, 0)),
            TradingPhase.CLOSING_ESCAPE: (time(13, 0), time(13, 25)),
            TradingPhase.FINAL_AUCTION: (time(13, 25), time(13, 30)),
        }
        
        # 信號門檻設定
        self.min_confidence = 75  # 最低信心度
        self.min_smart_score = 70  # 最低智慧評分

        # 🔴 停用來源設定（設定後該來源將不執行模擬下單）
        self.disabled_sources = {
            "breakout_chase",   # 突破追擊型：勝率不穩，等改良後再開啟
            "early_entry",      # 早盤偵測型：27.7% 勝率，暫停
            "orb_breakout",     # ORB 突破型：42.9% 勝率，暫停
        }
        # ↑ 若要重新開啟某策略，把它從 set 裡移除即可
        if self.disabled_sources:
            logger.info(f"⛔ 已停用模擬下單來源: {self.disabled_sources}")
        
        # 🆕 移動停損設定 (當沖版本)
        self.trailing_stop_activation = 3  # 獲利 3% 時啟動移動停利
        self.trailing_stop_distance = 1    # 移動停利距離 1%
        
        # 🆕 高點回落警告
        self.pullback_warning_pct = 1  # 從高點回落 1% 發出警告
        
        # 加碼設定
        self.scale_in_threshold = -3  # 虧損 3% 時考慮加碼
        self.max_scale_in_times = 2  # 最多加碼 2 次
        
        # 🆕 減碼設定 (當沖版本 - 分批停利)
        self.scale_out_threshold = 2  # 獲利 2% 時部分減碼 (原5%)
        self.scale_out_ratio = 0.33   # 減碼 33% (分三批出)
        
        # 統計
        self.signals_checked = 0
        self.positions_opened = 0
        self.trailing_stops_triggered = 0
        self.forced_closes = 0
        
        # 已處理的信號（避免重複）
        self.processed_signals: set = set()
    
    def get_current_phase(self) -> Tuple[str, Dict]:
        """
        獲取當前交易時段
        
        Returns:
            Tuple[phase_key, phase_config]
        """
        now = datetime.now()
        
        # 休市或週末不交易
        from app.utils.twse_calendar import twse_calendar
        if not twse_calendar.is_trading_day(now):
            return TradingPhase.MARKET_CLOSED, PHASE_CONFIG[TradingPhase.MARKET_CLOSED]
        
        current_time = now.time()
        
        # 根據時間判斷階段
        for phase, (start, end) in self.phase_times.items():
            if start <= current_time < end:
                return phase, PHASE_CONFIG[phase]
        
        # 收盤後
        if current_time >= time(13, 30):
            return TradingPhase.MARKET_CLOSED, PHASE_CONFIG[TradingPhase.MARKET_CLOSED]
        
        # 開盤前
        return TradingPhase.MARKET_CLOSED, PHASE_CONFIG[TradingPhase.MARKET_CLOSED]
    
    def is_trading_hours(self) -> bool:
        """檢查是否在交易時間"""
        from app.utils.twse_calendar import twse_calendar
        return twse_calendar.is_market_open()
    
    def can_open_position(self) -> Tuple[bool, str]:
        """
        檢查是否可以開新倉
        
        v3.4: 加入單日虧損上限檢查
        
        Returns:
            Tuple[can_open, reason]
        """
        phase, config = self.get_current_phase()
        
        # 1. 檢查時段
        if not config["allow_new_position"]:
            return False, f"【{config['emoji']} {config['name']}】禁止新倉"
        
        # 2. 檢查風控（單日虧損上限）
        try:
            from app.services.daily_loss_monitor import daily_loss_monitor
            can_trade, risk_reason = daily_loss_monitor.can_open_position()
            if not can_trade:
                return False, f"【🛡️ 風控】{risk_reason}"
        except Exception:
            pass  # 風控模組未載入時不阻擋
        
        return True, f"【{config['emoji']} {config['name']}】允許建倉 (權重 {config['weight']}%)"
    
    def should_force_close(self) -> Tuple[bool, str]:
        """
        檢查是否應該強制平倉
        
        Returns:
            Tuple[should_close, reason]
        """
        phase, config = self.get_current_phase()
        
        if config["force_close"]:
            return True, f"【{config['emoji']} {config['name']}】強制平倉！只出不進！"
        
        return False, ""
    
    def get_position_weight(self) -> float:
        """獲取當前時段的建倉權重 (0-100)"""
        phase, config = self.get_current_phase()
        return config["weight"] / 100.0
    
    def is_orb_time(self) -> bool:
        """檢查是否在 ORB 時段（09:05-10:30 黃金進攻期）"""
        phase, _ = self.get_current_phase()
        return phase == TradingPhase.GOLDEN_ATTACK
    
    async def fetch_high_confidence_signals(self) -> List[Dict]:
        """
        獲取高信心度的 AI 信號
        整合多個信號來源
        """
        signals = []
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                # 1. 獲取主力偵測信號
                try:
                    resp = await client.get("http://localhost:8000/api/analysis/mainforce/batch")
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("results", []):
                            if item.get("confidence", 0) >= self.min_confidence:
                                signals.append({
                                    "symbol": item["symbol"],
                                    "source": "main_force",
                                    "confidence": item["confidence"],
                                    "signal_type": item.get("signal", "unknown"),
                                    "price": item.get("current_price"),
                                    "reason": item.get("reason", "主力進場信號")
                                })
                except Exception as e:
                    logger.debug(f"主力偵測信號獲取失敗: {e}")
                
                # 2. 獲取智慧評分信號
                try:
                    resp = await client.get("http://localhost:8000/api/smart-entry/top-picks?min_score=70&limit=10")
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("picks", []):
                            if item.get("smart_score", 0) >= self.min_smart_score:
                                signals.append({
                                    "symbol": item["symbol"],
                                    "source": "smart_entry",
                                    "confidence": item["smart_score"],
                                    "signal_type": "buy",
                                    "price": item.get("current_price"),
                                    "reason": f"智慧評分 {item['smart_score']} 分"
                                })
                except Exception as e:
                    logger.debug(f"智慧評分信號獲取失敗: {e}")
                
                # 3. 獲取每日強勢股
                try:
                    resp = await client.get("http://localhost:8000/api/watchlist/today")
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("recommended_entries", []):
                            signals.append({
                                "symbol": item["symbol"],
                                "source": "daily_watchlist",
                                "confidence": item.get("confidence", 75),
                                "signal_type": "buy",
                                "price": item.get("scan_price"),
                                "reason": f"強勢股建議進場"
                            })
                except Exception as e:
                    logger.debug(f"每日強勢股信號獲取失敗: {e}")
        
        except Exception as e:
            logger.error(f"獲取信號失敗: {e}")
        
        return signals
    
    async def fetch_orb_signals(self) -> List[Dict]:
        """
        獲取 ORB（開盤區間突破）信號
        在開盤後 15-30 分鐘執行
        """
        signals = []
        
        try:
            import yfinance as yf
            
            # 使用可配置的監控清單
            watchlist = getattr(self, 'orb_watchlist', None)
            if not watchlist:
                watchlist = ["2330", "2317", "2454", "2881", "2882", "3008", "2412"]
            
            for symbol in watchlist:
                try:
                    ticker = yf.Ticker(f"{symbol}.TW")
                    hist = ticker.history(period="1d", interval="1m")
                    
                    if hist.empty or len(hist) < 15:
                        continue
                    
                    # 計算開盤區間（前 15 分鐘）
                    orb_data = hist.head(15)
                    orb_high = float(orb_data['High'].max())
                    orb_low = float(orb_data['Low'].min())
                    current_price = float(hist['Close'].iloc[-1])
                    
                    # 判斷突破
                    if current_price > orb_high * 1.002:  # 突破高點 0.2%
                        range_size = orb_high - orb_low
                        signals.append({
                            "symbol": symbol,
                            "source": "orb_breakout",
                            "confidence": 80,
                            "signal_type": "long",
                            "price": current_price,
                            "orb_high": orb_high,
                            "orb_low": orb_low,
                            "stop_loss": orb_high - range_size * 0.3,  # 停損在區間內
                            "target": current_price + range_size * 1.5,  # 目標 1.5R
                            "reason": f"ORB 突破高點 ${orb_high:.2f}"
                        })
                    elif current_price < orb_low * 0.998:  # 跌破低點 0.2%
                        range_size = orb_high - orb_low
                        signals.append({
                            "symbol": symbol,
                            "source": "orb_breakout",
                            "confidence": 75,
                            "signal_type": "avoid",  # 目前只做多，跌破標記避開
                            "price": current_price,
                            "orb_high": orb_high,
                            "orb_low": orb_low,
                            "reason": f"ORB 跌破低點 ${orb_low:.2f}，建議避開"
                        })
                
                except Exception as e:
                    logger.debug(f"獲取 {symbol} ORB 數據失敗: {e}")
        
        except Exception as e:
            logger.error(f"ORB 信號獲取失敗: {e}")
        
        return signals
    
    async def fetch_breakout_signals(self) -> List[Dict]:
        """
        獲取「突破追擊型」信號
        
        偵測條件：
        1. 漲幅 > 5%
        2. 價格在高檔區 (接近今日最高)
        3. 跳空突破
        """
        signals = []
        
        try:
            # 使用監控清單
            watchlist = getattr(self, 'orb_watchlist', None)
            if not watchlist:
                return signals
            
            from app.services.fubon_service import get_realtime_quote
            
            for symbol in watchlist[:15]:  # 最多檢查 15 檔
                try:
                    quote = await get_realtime_quote(symbol)
                    
                    if not quote or quote.get('price', 0) <= 0:
                        continue
                    
                    price = quote.get('price', 0)
                    change_pct = quote.get('change', 0)
                    high = quote.get('high', price)
                    prev_close = quote.get('previousClose', 0) or quote.get('prev_close', 0)
                    
                    breakout_score = 0
                    reasons = []
                    
                    # 條件1: 強勢上漲 (> 5%)
                    if change_pct >= 5:
                        breakout_score += 30
                        reasons.append(f"強勢 +{change_pct:.1f}%")
                        
                        if change_pct >= 9:
                            breakout_score += 25
                            reasons.append("🚀接近漲停")
                    
                    # 條件2: 價格在高檔區
                    if high > 0 and price >= high * 0.995:
                        breakout_score += 20
                        reasons.append("高檔強勢")
                    
                    # 條件3: 突破後續強
                    if prev_close > 0 and price > prev_close * 1.03:
                        breakout_score += 15
                        reasons.append("突破前收")
                    
                    # 信心度 >= 50 才觸發做多
                    if breakout_score >= 50:
                        stop_loss_long = round(price * 0.97, 2)
                        limit_up = prev_close * 1.10 if prev_close > 0 else price * 1.05
                        target_long = round(min(limit_up, price * 1.08), 2)
                        
                        signals.append({
                            "symbol": symbol,
                            "source": "breakout_chase",
                            "confidence": min(breakout_score + 20, 95),
                            "signal_type": "long",
                            "price": price,
                            "stop_loss": stop_loss_long,
                            "target": target_long,
                            "reason": f"【突破追擊】" + " + ".join(reasons)
                        })
                        logger.info(f"🚀 發現突破訊號: {symbol} @ ${price:.1f} (+{change_pct:.1f}%)")

                    # --- [新增] 做空訊號偵測 ---
                    collapse_score = 0
                    short_reasons = []
                    if change_pct <= -4:
                        collapse_score += 40
                        short_reasons.append(f"弱勢 {change_pct:.1f}%")
                    
                    if prev_close > 0 and price < prev_close * 0.95:
                        collapse_score += 20
                        short_reasons.append("破前收跌幅大")

                    if collapse_score >= 50:
                         stop_loss_short = round(price * 1.03, 2)
                         limit_down = prev_close * 0.90 if prev_close > 0 else price * 0.95
                         target_short = round(max(limit_down, price * 0.92), 2)
                         signals.append({
                            "symbol": symbol,
                            "source": "breakout_chase",
                            "confidence": min(collapse_score + 10, 90),
                            "signal_type": "short",
                            "price": price,
                            "stop_loss": stop_loss_short,
                            "target": target_short,
                            "reason": f"【弱勢崩潰】" + " + ".join(short_reasons)
                        })
                         logger.info(f"📉 發現放空訊號: {symbol} @ ${price:.1f} ({change_pct:.1f}%)")
                
                except Exception as e:
                    logger.debug(f"突破分析 {symbol} 失敗: {e}")
                
                await asyncio.sleep(0.5)  # 避免 API 過載
        
        except Exception as e:
            logger.error(f"突破信號獲取失敗: {e}")
        
        return signals
    
    async def open_simulation_position(
        self,
        symbol: str,
        price: float,
        source: str,
        confidence: float,
        reason: str,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        is_short: bool = False,
        kelly_multiplier: float = 0.1,  # 🆕 傳入 Kelly 建議
        tier: str = "Standard"          # 🆕 傳入標的分層
    ) -> Optional[Dict]:
        """
        開立模擬持倉
        """
        # [v5.5 升級] 🛡️ 實戰滑價懲罰 (Slippage Simulation)
        # 固定增加 0.1% 作為追價成本，確保模擬績效不虛標
        # 如果是做多 (is_short=False)，進場價加 0.1%；做空反之。
        original_price = float(price)
        price = original_price * (1.001 if not is_short else 0.999)
        logger.info(f"⚖️ [滑價修正] {symbol} 原價 {original_price} -> 實戰成交價 {price:.2f}")

        async with AsyncSessionLocal() as db:
            try:
                # 🆕 [v3.5 升級] 使用 Kelly 大腦建議決定張數
                quantity_lots = max(1, int(kelly_multiplier * 10.0))
                
                # 根據分層微調張數 (A 級多 1 張，C 級固定 1 張)
                if tier == "Tier A (優質)":
                    quantity_lots += 1
                    logger.info(f"💎 {symbol} 屬於 Tier A，加碼 1 張 (總計 {quantity_lots} 張)")
                elif tier == "Tier C (弱勢)":
                    quantity_lots = 1
                    logger.info(f"⚠️ {symbol} 屬於 Tier C，強制縮減至 1 張")
                
                # 限制單筆最大上限 5 張，避免極端數據導致爆倉
                quantity_lots = min(5, quantity_lots)
                
                try:
                    from app.api.portfolio import get_capital_config
                    cap = get_capital_config()
                    total_capital = float(cap.get("total_capital", 0.0))
                    
                    if total_capital > 0:
                        all_sims = await db.execute(select(Portfolio).where(Portfolio.is_simulated == True))
                        sim_positions = all_sims.scalars().all()
                        
                        realized_pnl = sum(float(p.realized_profit or 0) for p in sim_positions if p.status != "open")
                        open_cost = sum(float(p.entry_price * p.entry_quantity) for p in sim_positions if p.status == "open")
                        available_cap = total_capital + realized_pnl - open_cost
                        
                        # 檢查目前該股票已持有張數，避免無限攤平 (上限設為 5 張)
                        symbol_open_lots = sum(int(p.entry_quantity / 1000) for p in sim_positions if p.symbol == symbol and p.status == "open")
                        if symbol_open_lots >= 5:
                            logger.info(f"⚠️ {symbol} 已持有 {symbol_open_lots} 張，達模擬上限，跳過")
                            return None

                        # 如果已有反向持倉，先跳過（簡化模型，不支持對沖）
                        existing_opposite = [p for p in sim_positions if p.symbol == symbol and p.status == "open" and p.is_short != is_short]
                        if existing_opposite:
                            logger.info(f"⚠️ {symbol} 已有反向持倉，暫不支持對沖，跳過")
                            return None
                        
                        # 如果資金不足，嘗試降載 (降張數)
                        while quantity_lots > 0:
                            needed_cap = price * 1000 * quantity_lots
                            if available_cap >= needed_cap:
                                break
                            quantity_lots -= 1
                        
                        if quantity_lots <= 0:
                            logger.warning(f"🏦 資金不足擋單: {symbol} 連 1 張都買不起 (剩餘 {available_cap:.0f})")
                            return None
                        
                except Exception as e:
                    logger.debug(f"資金水位檢查失敗，默認 1 張: {e}")
                    quantity_lots = 1

                # [新增] 🚨 均線過濾器 (做多擋空頭，做空擋多頭)
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(f"{symbol}.TW")
                    hist = ticker.history(period="1mo")
                    if len(hist) >= 20:
                        ma5 = hist['Close'].tail(5).mean()
                        ma20 = hist['Close'].tail(20).mean()
                        current_close = float(hist['Close'].iloc[-1])
                        
                        if not is_short:
                            # 做多擋單：處於空頭排列
                            if current_close < ma20 and ma5 < ma20:
                                logger.warning(f"🛡️ 風控擋單(做多): {symbol} 處於均線空頭排列，不進場")
                                return None
                        else:
                            # 做空擋單：處於多頭強勢排列
                            if current_close > ma20 and ma5 > ma20:
                                logger.warning(f"🛡️ 風控擋單(做空): {symbol} 處於均線多頭排列，不放空")
                                return None
                except Exception as e:
                    logger.debug(f"均線過濾器檢查失敗，暫不阻擋: {e}")

                # 計算停損和目標 (做空邏輯反向)
                if stop_loss is None:
                    stop_loss = price * 1.05 if is_short else price * 0.95
                if target is None:
                    target = price * 0.90 if is_short else price * 1.10
                
                # 🆕 取得繁體中文股票名稱
                try:
                    from app.services.trade_email_notifier import get_tw_stock_name
                    stock_name = await get_tw_stock_name(symbol)
                except:
                    stock_name = symbol
                
                final_quantity = quantity_lots * 1000

                # 建立持倉
                position = Portfolio(
                    symbol=symbol,
                    stock_name=stock_name,
                    entry_date=datetime.now(),
                    entry_price=Decimal(str(price)),
                    entry_quantity=final_quantity,
                    analysis_source=source,
                    analysis_confidence=Decimal(str(confidence)),
                    stop_loss_price=Decimal(str(stop_loss)),
                    target_price=Decimal(str(target)),
                    is_simulated=True,
                    is_short=is_short,
                    notes=f"智能模擬下單({quantity_lots}張{'做空' if is_short else '做多'}) - {reason}",
                    status="open"
                )
                
                db.add(position)
                await db.flush()
                
                # 建立買入記錄
                trade = TradeRecord(
                    portfolio_id=position.id,
                    symbol=symbol,
                    trade_type="buy",
                    trade_date=datetime.now(),
                    price=Decimal(str(price)),
                    quantity=final_quantity,
                    total_amount=Decimal(str(price * final_quantity)),
                    analysis_source=source,
                    analysis_confidence=Decimal(str(confidence)),
                    is_simulated=True,
                    notes=f"智能模擬下單({quantity_lots}張) - {reason}"
                )
                
                db.add(trade)
                await db.commit()
                
                self.positions_opened += 1
                
                # 發送通知
                try:
                    from app.services.trade_email_notifier import trade_notifier
                    await trade_notifier.send_buy_notification(
                        symbol=symbol,
                        stock_name=stock_name or symbol,
                        entry_price=price,
                        quantity=final_quantity,
                        stop_loss=stop_loss,
                        target_price=target,
                        analysis_source=source,
                        is_simulated=True
                    )
                except Exception as e:
                    logger.debug(f"發送通知失敗: {e}")
                
                direction_str = "做空" if is_short else "做多"
                logger.info(f"✅ 智能模擬建倉: {symbol} @ ${price:.2f} ({quantity_lots}張 {direction_str}) | 停損: ${stop_loss:.2f} | 信心度: {confidence*100:.0f}%")
                
                return {
                    "symbol": symbol,
                    "price": price,
                    "stop_loss": stop_loss,
                    "target": target,
                    "source": source,
                    "reason": reason
                }
                
            except Exception as e:
                logger.error(f"建立模擬持倉失敗: {e}")
                await db.rollback()
                return None
    
    async def update_trailing_stops(self) -> List[Dict]:
        """
        更新移動停利
        當價格上漲時，自動調整停損價
        """
        updates = []
        
        async with AsyncSessionLocal() as db:
            try:
                # 獲取所有模擬持倉
                result = await db.execute(
                    select(Portfolio).where(
                        Portfolio.status == "open",
                        Portfolio.is_simulated == True
                    )
                )
                positions = result.scalars().all()
                
                for pos in positions:
                    try:
                        # 獲取當前價格
                        import yfinance as yf
                        ticker = yf.Ticker(f"{pos.symbol}.TW")
                        hist = ticker.history(period="1d")
                        
                        if hist.empty:
                            continue
                        
                        current_price = float(hist['Close'].iloc[-1])
                        entry_price = float(pos.entry_price)
                        current_stop = float(pos.stop_loss_price) if pos.stop_loss_price else (entry_price * 1.05 if pos.is_short else entry_price * 0.95)
                        
                        # 計算當前獲利百分比 (做多做空邏輯反向)
                        if pos.is_short:
                            profit_pct = (entry_price - current_price) / entry_price * 100
                        else:
                            profit_pct = (current_price - entry_price) / entry_price * 100
                        
                        # 檢查是否啟動移動停利
                        if profit_pct >= self.trailing_stop_activation:
                            # 計算新的移動停利價
                            if pos.is_short:
                                # 做空：價格跌，停損下移
                                new_stop = current_price * (1 + self.trailing_stop_distance / 100)
                                should_update = new_stop < current_stop
                            else:
                                # 做多：價格漲，停損上移
                                new_stop = current_price * (1 - self.trailing_stop_distance / 100)
                                should_update = new_stop > current_stop
                            
                            if should_update:
                                pos.stop_loss_price = Decimal(str(new_stop))
                                pos.notes = (pos.notes or "") + f"\n[移動停利] {datetime.now().strftime('%H:%M')} 停損調整至 ${new_stop:.2f}"
                                
                                updates.append({
                                    "symbol": pos.symbol,
                                    "old_stop": current_stop,
                                    "new_stop": new_stop,
                                    "profit_pct": profit_pct
                                })
                                
                                direction_str = "做空下移" if pos.is_short else "做多上移"
                                logger.info(f"📈 移動停利({direction_str}): {pos.symbol} 停損 ${current_stop:.2f} → ${new_stop:.2f} (獲利 {profit_pct:.1f}%)")
                                self.trailing_stops_triggered += 1
                    
                    except Exception as e:
                        logger.debug(f"更新 {pos.symbol} 移動停利失敗: {e}")
                
                if updates:
                    await db.commit()
                
            except Exception as e:
                logger.error(f"更新移動停利失敗: {e}")
        
        return updates
    
    async def check_scale_opportunities(self) -> Dict[str, List]:
        """
        檢查加碼/減碼機會
        """
        opportunities = {
            "scale_in": [],  # 加碼機會
            "scale_out": []  # 減碼機會
        }
        
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(Portfolio).where(
                        Portfolio.status == "open",
                        Portfolio.is_simulated == True
                    )
                )
                positions = result.scalars().all()
                
                for pos in positions:
                    if pos.unrealized_profit_percent is None:
                        continue
                    
                    profit_pct = float(pos.unrealized_profit_percent)
                    
                    # 檢查加碼機會（虧損一定程度後考慮加碼攤平）
                    if profit_pct <= self.scale_in_threshold:
                        # 檢查加碼次數
                        scale_in_count = (pos.notes or "").count("[加碼]")
                        if scale_in_count < self.max_scale_in_times:
                            opportunities["scale_in"].append({
                                "symbol": pos.symbol,
                                "position_id": pos.id,
                                "current_loss_pct": profit_pct,
                                "scale_in_count": scale_in_count,
                                "suggestion": f"虧損 {abs(profit_pct):.1f}%，可考慮加碼攤平"
                            })
                    
                    # 檢查減碼機會（獲利一定程度後部分獲利了結）
                    elif profit_pct >= self.scale_out_threshold:
                        if "[減碼]" not in (pos.notes or ""):
                            opportunities["scale_out"].append({
                                "symbol": pos.symbol,
                                "position_id": pos.id,
                                "current_profit_pct": profit_pct,
                                "suggestion": f"獲利 {profit_pct:.1f}%，可考慮減碼 {self.scale_out_ratio*100:.0f}%"
                            })
            
            except Exception as e:
                logger.error(f"檢查加碼/減碼機會失敗: {e}")
        
        return opportunities
    
    async def process_signals(self) -> Dict[str, Any]:
        """
        處理所有信號並執行交易
        
        v3.3 升級：
        - 根據黃金時程表判斷是否允許建倉
        - 在結算逃命期強制平倉
        - 根據時段權重調整建倉優先級
        """
        phase, config = self.get_current_phase()
        
        result = {
            "phase": phase,
            "phase_name": config["name"],
            "phase_emoji": config["emoji"],
            "signals_found": 0,
            "positions_opened": 0,
            "positions_closed": 0,
            "trailing_updates": 0,
            "details": [],
            "warnings": []
        }
        
        if not self.is_trading_hours():
            return result
        
        # ============ 強制平倉檢查 (13:00-13:30) ============
        should_close, close_reason = self.should_force_close()
        if should_close:
            closed_count = await self.force_close_all_positions(close_reason)
            result["positions_closed"] = closed_count
            result["warnings"].append(f"🚨 {close_reason} - 已平倉 {closed_count} 筆")
            logger.warning(f"🚨 強制平倉: {close_reason} - 已平倉 {closed_count} 筆")
            
            # 結算期間只做平倉，不建新倉
            return result
        
        # ============ 檢查是否可以建倉 ============
        can_open, open_reason = self.can_open_position()
        
        if not can_open:
            result["warnings"].append(f"⚠️ {open_reason}")
            logger.info(f"⏸️ {open_reason}")
            
            # 即使不能建倉，仍然更新移動停利
            trailing_updates = await self.update_trailing_stops()
            result["trailing_updates"] = len(trailing_updates)
            return result
        
        # ============ 獲取建倉權重 ============
        weight = self.get_position_weight()
        
        # 🆕 0. 優先使用早盤進場偵測器 (09:10-10:30 黃金時段)
        if "early_entry" not in self.disabled_sources:
            try:
                from app.services.early_entry_detector import early_entry_detector
                now_time = datetime.now().time()

                # 在 09:10-10:30 期間，優先使用早盤偵測器
                if time(9, 10) <= now_time <= time(10, 30):
                    early_signals = await early_entry_detector.scan_all_signals()
                    if early_signals:
                        logger.info(f"🎯 早盤偵測器發現 {len(early_signals)} 個進場信號")
                        for signal in early_signals:
                            signal["signal_type"] = "long"
                            logger.info(f"  📍 {signal['symbol']}: {signal['reason']}")

                        result["signals_found"] = len(early_signals)
                        result["details"].append({"early_entry_signals": len(early_signals)})

                        for signal in early_signals:
                            opened = await self.open_simulation_position(
                                symbol=signal["symbol"],
                                price=signal.get("price", 0),
                                source="early_entry",
                                confidence=signal.get("confidence", 80),
                                reason=signal.get("reason", "早盤進場信號"),
                                stop_loss=signal.get("stop_loss"),
                                target=signal.get("target")
                            )
                            if opened:
                                result["positions_opened"] += 1
                                result["details"].append(opened)

                        trailing_updates = await self.update_trailing_stops()
                        result["trailing_updates"] = len(trailing_updates)
                        return result
            except Exception as e:
                logger.debug(f"早盤偵測器執行失敗: {e}")
        else:
            logger.debug("⛔ early_entry 已停用，跳過早盤偵測器")
        
        # 1. 獲取高信心度信號
        signals = await self.fetch_high_confidence_signals()

        # 2. 如果在 ORB 時段（黃金進攻期），加入 ORB 信號
        if self.is_orb_time() and "orb_breakout" not in self.disabled_sources:
            orb_signals = await self.fetch_orb_signals()
            signals.extend([s for s in orb_signals if s.get("signal_type") != "avoid"])
        elif "orb_breakout" in self.disabled_sources:
            logger.debug("⛔ orb_breakout 已停用，跳過 ORB 信號")

        # 3. 加入突破追擊信號
        if "breakout_chase" not in self.disabled_sources:
            breakout_signals = await self.fetch_breakout_signals()
            signals.extend(breakout_signals)
        else:
            logger.debug("⛔ breakout_chase 已停用，跳過突破追擊信號")
        
        result["signals_found"] = len(signals)
        self.signals_checked += len(signals)
        
        # 3. 根據權重過濾信號（低權重時段需要更高信心度）
        min_confidence_adjusted = int(self.min_confidence + (1 - weight) * 15)
        filtered_signals = [
            s for s in signals 
            if s.get("confidence", 0) >= min_confidence_adjusted
        ]
        
        if weight < 1.0:
            logger.info(f"📊 時段權重 {weight*100:.0f}%，信心度門檻調整為 {min_confidence_adjusted}%")
        
        # 4. 過濾已處理的信號
        new_signals = []
        for signal in filtered_signals:
            signal_key = f"{signal['symbol']}_{signal['source']}_{datetime.now().strftime('%Y%m%d')}"
            if signal_key not in self.processed_signals:
                new_signals.append(signal)
                self.processed_signals.add(signal_key)
        
        # 5. 執行交易
        for signal in new_signals:
            if signal.get("signal_type") in ["buy", "long"]:
                opened = await self.open_simulation_position(
                    symbol=signal["symbol"],
                    price=signal.get("price", 0),
                    source=signal["source"],
                    confidence=signal.get("confidence", 75),
                    reason=f"[{config['emoji']} {config['name']}] {signal.get('reason', '信號觸發')}",
                    stop_loss=signal.get("stop_loss"),
                    target=signal.get("target"),
                    kelly_multiplier=signal.get("kelly_multiplier", 0.1),
                    tier=signal.get("tier", "Standard")
                )
                if opened:
                    result["positions_opened"] += 1
                    result["details"].append(opened)
        
        # 6. 更新移動停利
        trailing_updates = await self.update_trailing_stops()
        result["trailing_updates"] = len(trailing_updates)
        
        return result
    
    async def force_close_all_positions(self, reason: str) -> int:
        """
        強制平倉所有模擬持倉
        
        Returns:
            平倉數量
        """
        closed_count = 0
        exempt_count = 0  # 🆕 豁免數量
        
        # 🆕 漲停豁免參數
        MOMENTUM_EXEMPT_THRESHOLD = 5.0  # 漲幅 > 5% 豁免強制平倉
        HIGH_POSITION_THRESHOLD = 0.97   # 價格在高點的 97% 以上視為高檔區
        
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(Portfolio).where(
                        Portfolio.status == "open",
                        Portfolio.is_simulated == True
                    )
                )
                positions = result.scalars().all()
                
                for pos in positions:
                    try:
                        # 獲取當前價格
                        import yfinance as yf
                        ticker = yf.Ticker(f"{pos.symbol}.TW")
                        hist = ticker.history(period="1d")
                        
                        if hist.empty:
                            continue
                        
                        current_price = float(hist['Close'].iloc[-1])
                        entry_price = float(pos.entry_price)
                        today_high = float(hist['High'].max())
                        today_open = float(hist['Open'].iloc[0])
                        
                        # 計算損益
                        profit = (current_price - entry_price) * float(pos.entry_quantity)
                        profit_pct = (current_price - entry_price) / entry_price * 100
                        
                        # 計算今日漲幅（相對開盤價）
                        today_change_pct = (current_price - today_open) / today_open * 100 if today_open > 0 else 0
                        
                        # 🆕 使用智能平倉管理器判斷
                        close_decision = smart_close_manager.should_force_close({
                            'entry_time': pos.entry_date,
                            'pnl_pct': profit_pct
                        })
                        
                        # 🆕 檢查是否符合漲停豁免條件（覆蓋智能平倉判斷）
                        is_momentum_strong = today_change_pct >= MOMENTUM_EXEMPT_THRESHOLD
                        is_at_high = current_price >= today_high * HIGH_POSITION_THRESHOLD if today_high > 0 else False
                        should_exempt = (is_momentum_strong and is_at_high) or profit_pct >= 5.0
                        
                        # 🆕 智能平倉決策：結合管理器判斷和豁免條件
                        if should_exempt:
                            # 漲停/強勢股豁免
                            exempt_count += 1
                            exempt_reason = []
                            if is_momentum_strong:
                                exempt_reason.append(f"今日漲幅 {today_change_pct:.1f}%")
                            if is_at_high:
                                exempt_reason.append("價格在高檔區")
                            if profit_pct >= 5.0:
                                exempt_reason.append(f"獲利 {profit_pct:.1f}%")
                            
                            logger.info(
                                f"🛡️ 漲停豁免: {pos.symbol} @ ${current_price:.2f} | "
                                f"{', '.join(exempt_reason)} | 繼續持有！"
                            )
                            
                            # 更新備註但不平倉
                            pos.notes = (pos.notes or "") + f"\n[漲停豁免] {datetime.now().strftime('%H:%M')} {', '.join(exempt_reason)}"
                            pos.current_price = Decimal(str(current_price))
                            pos.unrealized_profit = Decimal(str(profit))
                            pos.unrealized_profit_percent = Decimal(str(profit_pct))
                            continue  # 跳過平倉
                        
                        # 🆕 智能平倉管理器說不該平倉（例如小虧等待反彈）
                        if not close_decision.get('should_close', True):
                            logger.info(
                                f"⏸️ 暫緩平倉: {pos.symbol} @ ${current_price:.2f} | "
                                f"原因: {close_decision.get('reason', '')} | {profit_pct:+.2f}%"
                            )
                            pos.notes = (pos.notes or "") + f"\n[暫緩平倉] {datetime.now().strftime('%H:%M')} {close_decision.get('reason', '')}"
                            pos.current_price = Decimal(str(current_price))
                            pos.unrealized_profit = Decimal(str(profit))
                            pos.unrealized_profit_percent = Decimal(str(profit_pct))
                            continue  # 跳過平倉
                        
                        # 執行強制平倉
                        pos.status = "forced_close"
                        pos.exit_date = datetime.now()
                        pos.exit_price = Decimal(str(current_price))
                        pos.exit_reason = reason
                        pos.realized_profit = Decimal(str(profit))
                        pos.realized_profit_percent = Decimal(str(profit_pct))
                        pos.notes = (pos.notes or "") + f"\n[強制平倉] {datetime.now().strftime('%H:%M')} {reason}"
                        
                        closed_count += 1
                        self.forced_closes += 1
                        
                        logger.info(
                            f"🚨 強制平倉: {pos.symbol} @ ${current_price:.2f} | "
                            f"損益: ${profit:+.0f} ({profit_pct:+.1f}%)"
                        )
                        
                    except Exception as e:
                        logger.error(f"強制平倉 {pos.symbol} 失敗: {e}")
                
                if closed_count > 0 or exempt_count > 0:
                    await db.commit()
                    if exempt_count > 0:
                        logger.info(f"🛡️ 本次平倉: {closed_count} 筆，漲停豁免: {exempt_count} 筆")
                    
            except Exception as e:
                logger.error(f"強制平倉失敗: {e}")
        
        return closed_count
    
    async def start_smart_trading(self):
        """
        啟動智能交易監控 (v3.4 漲停豁免版)
        """
        if self.is_running:
            logger.warning("智能交易器已經在運行中")
            return
        
        self.is_running = True
        logger.info("🤖 智能模擬交易器 v3.4 已啟動 (漲停豁免版)")
        logger.info("   ⏰ 黃金時程表:")
        logger.info("      ⏳ 08:45-09:00  盤前試撮 (禁止下單)")
        logger.info("      ⚓ 09:00-09:05  定錨期 (觀察不動作)")
        logger.info("      🚀 09:05-10:30  黃金進攻期 (權重 100%)")
        logger.info("      📈 10:30-11:30  早盤續航 (權重 75%)")
        logger.info("      💤 11:30-12:30  垃圾時間 (禁止建倉)")
        logger.info("      ⚡ 12:30-13:00  尾盤衝刺 (權重 50%)")
        logger.info("      🚨 13:00-13:25  結算逃命 (強制平倉!)")
        logger.info("      🔔 13:25-13:30  收盤集合競價")
        logger.info("   🆕 漲停豁免機制:")
        logger.info("      🛡️ 漲幅 > 5% + 價格在高檔區 → 不平倉")
        logger.info("      🛡️ 獲利 > 5% → 不平倉")
        logger.info(f"   🎯 最低信心度: {self.min_confidence}%")
        logger.info(f"   📈 移動停利: 獲利 {self.trailing_stop_activation}% 啟動，距離 {self.trailing_stop_distance}%")
        
        while self.is_running:
            try:
                if self.is_trading_hours():
                    result = await self.process_signals()
                    
                    if result["positions_opened"] > 0 or result["trailing_updates"] > 0:
                        logger.info(
                            f"🔄 智能交易: 找到 {result['signals_found']} 個信號, "
                            f"開倉 {result['positions_opened']}, "
                            f"移動停利 {result['trailing_updates']}"
                        )
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"智能交易錯誤: {e}")
                await asyncio.sleep(self.check_interval)
        
        self.is_running = False
        logger.info("🔴 智能模擬交易器已停止")
    
    def stop_smart_trading(self):
        """停止智能交易"""
        self.is_running = False
    
    def get_status(self) -> Dict[str, Any]:
        """獲取狀態 (v3.3 黃金時程表版)"""
        phase, config = self.get_current_phase()
        can_open, open_reason = self.can_open_position()
        should_close, close_reason = self.should_force_close()
        
        return {
            "version": "v3.3",
            "is_running": self.is_running,
            "is_trading_hours": self.is_trading_hours(),
            "is_orb_time": self.is_orb_time(),
            
            # v3.3 黃金時程表
            "current_phase": {
                "key": phase,
                "name": config["name"],
                "emoji": config["emoji"],
                "color": config["color"],
                "weight": config["weight"],
                "allow_new_position": config["allow_new_position"],
                "force_close": config["force_close"]
            },
            "can_open_position": can_open,
            "open_position_reason": open_reason,
            "should_force_close": should_close,
            "force_close_reason": close_reason,
            
            # 統計
            "signals_checked": self.signals_checked,
            "positions_opened": self.positions_opened,
            "trailing_stops_triggered": self.trailing_stops_triggered,
            "forced_closes": self.forced_closes,
            
            # 設定
            "settings": {
                "min_confidence": self.min_confidence,
                "min_smart_score": self.min_smart_score,
                "trailing_stop_activation": self.trailing_stop_activation,
                "trailing_stop_distance": self.trailing_stop_distance,
                "scale_in_threshold": self.scale_in_threshold,
                "scale_out_threshold": self.scale_out_threshold
            },
            
            # 時程表
            "golden_schedule": {
                "pre_market": "08:45-09:00",
                "anchor": "09:00-09:05",
                "golden_attack": "09:05-10:30",
                "morning_extend": "10:30-11:30",
                "garbage_time": "11:30-12:30",
                "afternoon_sprint": "12:30-13:00",
                "closing_escape": "13:00-13:25",
                "final_auction": "13:25-13:30"
            },
            
            "current_time": datetime.now().isoformat()
        }


# 全域實例
smart_trader = SmartSimulationTrader()

