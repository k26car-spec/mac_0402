"""
早盤進場偵測器 v1.0 - Early Entry Detector
專門在 09:10-10:00 黃金時段偵測最佳買點

🎯 設計理念：
像用戶在 10:05 以 70.7 買到旺宏，最終漲到 76.6 (+8.3%)
系統要能在這個時段捕捉到類似的機會

📊 進場策略：
1. 開盤拉回買 (Pullback from Open)
   - 開盤後先漲後拉回到 VWAP 附近
   - 在支撐區形成止跌轉強信號

2. ORB 突破買 (Opening Range Breakout)
   - 突破前 15 分鐘高點
   - 成交量放大確認

3. 首次回測買 (First Pullback)
   - 開盤強勢後的首次回測
   - 回測到前高支撐區

4. 量價背離買 (Volume Divergence)
   - 價格未破新低但量能萎縮
   - 空頭力竭，多頭準備進攻

時間表：
- 09:00-09:10: 觀察期（收集數據）
- 09:10-09:30: 早期進場窗口（開盤拉回買）
- 09:30-10:00: 主要進場窗口（ORB 突破 + 回測買）
- 10:00-10:30: 延伸進場窗口（趨勢確認後加倉）
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
import json
import os

logger = logging.getLogger(__name__)


class EntrySignalType:
    """進場信號類型"""
    PULLBACK_FROM_OPEN = "pullback_from_open"      # 開盤拉回買
    ORB_BREAKOUT = "orb_breakout"                  # ORB 突破
    FIRST_PULLBACK = "first_pullback"              # 首次回測
    VOLUME_DIVERGENCE = "volume_divergence"        # 量價背離
    VWAP_BOUNCE = "vwap_bounce"                    # VWAP 反彈
    MOMENTUM_SURGE = "momentum_surge"              # 動能爆發


class EarlyEntryDetector:
    """早盤進場偵測器"""
    
    def __init__(self):
        # 時間窗口設定
        self.observation_start = time(9, 0)
        self.observation_end = time(9, 10)
        self.early_window_start = time(9, 10)
        self.early_window_end = time(9, 30)
        self.main_window_start = time(9, 30)
        self.main_window_end = time(10, 0)
        self.extended_window_end = time(10, 30)
        
        # 信號門檻
        self.min_orb_breakout_pct = 0.3      # ORB 突破門檻 0.3%
        self.pullback_depth_min = 0.5        # 最小拉回深度 0.5%
        self.pullback_depth_max = 2.0        # 最大拉回深度 2%
        self.volume_surge_ratio = 1.5        # 成交量放大倍數
        self.vwap_tolerance = 0.5            # VWAP 容差 0.5%
        
        # 風控參數
        self.default_stop_loss_pct = 2.0     # 預設停損 2%
        self.default_target_pct = 5.0        # 預設目標 5%
        self.risk_reward_min = 1.5           # 最小風報比
        
        # 股票盤中數據緩存
        self.intraday_data: Dict[str, Dict] = {}
        
        # 已發出的信號（避免重複）
        self.signals_sent: Dict[str, str] = {}  # symbol -> signal_type
        
        # 載入 ORB 監控清單
        self.watchlist = self._load_orb_watchlist()
    
    def _load_orb_watchlist(self) -> List[str]:
        """載入 ORB 監控清單"""
        try:
            orb_file = os.path.join(
                os.path.dirname(__file__), 
                '../../../data/orb_watchlist.json'
            )
            if os.path.exists(orb_file):
                with open(orb_file, 'r') as f:
                    data = json.load(f)
                    return data.get('watchlist', [])
        except Exception as e:
            logger.warning(f"載入 ORB 監控清單失敗: {e}")
        
        # 預設清單
        return ["2330", "2317", "2454", "2337", "2344", "3034", "2881", "2882"]
    
    def get_current_window(self) -> Tuple[str, bool]:
        """
        獲取當前時間窗口
        
        Returns:
            (window_name, can_enter)
        """
        now = datetime.now().time()
        
        if now < self.observation_start:
            return "market_closed", False
        elif now < self.observation_end:
            return "observation", False  # 觀察期，不進場
        elif now < self.early_window_end:
            return "early_window", True  # 早期進場窗口
        elif now < self.main_window_end:
            return "main_window", True   # 主要進場窗口
        elif now < self.extended_window_end:
            return "extended_window", True  # 延伸進場窗口
        else:
            return "after_golden_hour", True  # 黃金時段後
        
    async def collect_intraday_data(self, symbol: str) -> Optional[Dict]:
        """
        收集股票盤中數據
        使用 Fubon API 或 yfinance
        """
        try:
            data = {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "open": 0,
                "high": 0,
                "low": 0,
                "current": 0,
                "prev_close": 0,
                "volume": 0,
                "orb_high": 0,
                "orb_low": 0,
                "vwap": 0,
                "change_pct": 0,
                "price_history": [],  # 分鐘K線
            }
            
            # 嘗試使用 Fubon 即時報價
            try:
                from app.services.fubon_service import get_realtime_quote
                quote = await get_realtime_quote(symbol)
                if quote and quote.get('price', 0) > 0:
                    data["current"] = quote.get('price', 0)
                    data["open"] = quote.get('open', 0) or data["current"]
                    data["high"] = quote.get('high', 0) or data["current"]
                    data["low"] = quote.get('low', 0) or data["current"]
                    data["prev_close"] = quote.get('previousClose', 0) or quote.get('prev_close', 0)
                    data["volume"] = quote.get('volume', 0)
                    data["change_pct"] = quote.get('change', 0)
                    
                    # 計算 VWAP (簡化版：使用 (H+L+C)/3 * Volume)
                    if data["high"] > 0 and data["low"] > 0:
                        typical_price = (data["high"] + data["low"] + data["current"]) / 3
                        data["vwap"] = typical_price  # 簡化 VWAP
                    
                    logger.debug(f"📊 {symbol} Fubon 報價: ${data['current']:.2f} ({data['change_pct']:+.2f}%)")
            except Exception as e:
                logger.debug(f"Fubon 報價失敗 {symbol}: {e}")
            
            # 如果 Fubon 沒有數據，使用 yfinance
            if data["current"] <= 0:
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(f"{symbol}.TW")
                    hist = ticker.history(period="1d", interval="1m")
                    
                    if not hist.empty:
                        data["current"] = float(hist['Close'].iloc[-1])
                        data["open"] = float(hist['Open'].iloc[0])
                        data["high"] = float(hist['High'].max())
                        data["low"] = float(hist['Low'].min())
                        data["volume"] = int(hist['Volume'].sum())
                        
                        # 計算 ORB (前 10-15 分鐘)
                        orb_minutes = min(15, len(hist))
                        orb_data = hist.head(orb_minutes)
                        data["orb_high"] = float(orb_data['High'].max())
                        data["orb_low"] = float(orb_data['Low'].min())
                        
                        # 保存分鐘K線
                        data["price_history"] = [
                            {
                                "time": idx.strftime("%H:%M"),
                                "open": float(row['Open']),
                                "high": float(row['High']),
                                "low": float(row['Low']),
                                "close": float(row['Close']),
                                "volume": int(row['Volume'])
                            }
                            for idx, row in hist.iterrows()
                        ]
                        
                        # 計算 VWAP
                        if len(hist) > 0:
                            typical_prices = (hist['High'] + hist['Low'] + hist['Close']) / 3
                            cumulative_tp_vol = (typical_prices * hist['Volume']).cumsum()
                            cumulative_vol = hist['Volume'].cumsum()
                            if cumulative_vol.iloc[-1] > 0:
                                data["vwap"] = float(cumulative_tp_vol.iloc[-1] / cumulative_vol.iloc[-1])
                        
                        # 計算漲跌幅
                        info = ticker.info
                        data["prev_close"] = info.get('previousClose', 0) or data["open"]
                        if data["prev_close"] > 0:
                            data["change_pct"] = (data["current"] - data["prev_close"]) / data["prev_close"] * 100
                        
                        logger.debug(f"📊 {symbol} yfinance: ${data['current']:.2f} ({data['change_pct']:+.2f}%)")
                        
                except Exception as e:
                    logger.debug(f"yfinance 數據失敗 {symbol}: {e}")
            
            # 緩存數據
            if data["current"] > 0:
                self.intraday_data[symbol] = data
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"收集 {symbol} 盤中數據失敗: {e}")
            return None
    
    def detect_pullback_from_open(self, data: Dict) -> Optional[Dict]:
        """
        偵測「開盤拉回買」信號
        
        條件：
        1. 開盤後先漲（開盤價 < 最高價）
        2. 當前價格從高點拉回 0.5%-2%
        3. 當前價格接近 VWAP 或開盤價支撐
        4. 尚未跌破開盤價
        """
        try:
            current = data.get("current", 0)
            open_price = data.get("open", 0)
            high = data.get("high", 0)
            low = data.get("low", 0)
            vwap = data.get("vwap", 0)
            
            if current <= 0 or open_price <= 0 or high <= 0:
                return None
            
            # 條件1: 開盤後有上漲（高點 > 開盤價 0.5%）
            if high < open_price * 1.005:
                return None
            
            # 條件2: 從高點拉回
            pullback_pct = (high - current) / high * 100
            if pullback_pct < self.pullback_depth_min or pullback_pct > self.pullback_depth_max:
                return None
            
            # 條件3: 當前價格接近 VWAP 或開盤價（在 0.5% 範圍內）
            near_vwap = vwap > 0 and abs(current - vwap) / vwap * 100 < self.vwap_tolerance
            near_open = abs(current - open_price) / open_price * 100 < self.vwap_tolerance
            
            if not (near_vwap or near_open):
                return None
            
            # 條件4: 未跌破開盤價超過 0.5%
            if current < open_price * 0.995:
                return None
            
            # 計算停損和目標
            stop_loss = round(min(low, open_price * 0.98), 2)
            target = round(high * 1.02, 2)  # 突破前高後再加 2%
            
            # 計算風報比
            risk = current - stop_loss
            reward = target - current
            rr_ratio = reward / risk if risk > 0 else 0
            
            if rr_ratio < self.risk_reward_min:
                return None
            
            # 計算信心度
            confidence = 70
            if near_vwap:
                confidence += 10
            if pullback_pct < 1.0:
                confidence += 5
            if rr_ratio > 2.0:
                confidence += 5
            
            return {
                "symbol": data["symbol"],
                "signal_type": EntrySignalType.PULLBACK_FROM_OPEN,
                "source": "early_entry",
                "confidence": min(confidence, 95),
                "price": current,
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": round(rr_ratio, 2),
                "reason": f"🔄 開盤拉回買 | 高點 ${high:.1f} 拉回 {pullback_pct:.1f}% | R/R {rr_ratio:.1f}",
                "details": {
                    "open": open_price,
                    "high": high,
                    "pullback_pct": pullback_pct,
                    "vwap": vwap,
                    "near_vwap": near_vwap
                }
            }
            
        except Exception as e:
            logger.debug(f"偵測開盤拉回買失敗: {e}")
            return None
    
    def detect_orb_breakout(self, data: Dict) -> Optional[Dict]:
        """
        偵測「ORB 突破」信號
        
        條件：
        1. 突破前 15 分鐘高點
        2. 突破幅度 > 0.3%
        3. 最好有成交量放大
        """
        try:
            current = data.get("current", 0)
            orb_high = data.get("orb_high", 0)
            orb_low = data.get("orb_low", 0)
            
            if current <= 0 or orb_high <= 0:
                return None
            
            # 如果 orb_high 沒有設定，使用前 15 分鐘的 high
            if orb_high == 0:
                price_history = data.get("price_history", [])
                if len(price_history) >= 10:
                    orb_high = max(p.get("high", 0) for p in price_history[:15])
                    orb_low = min(p.get("low", 999999) for p in price_history[:15])
                else:
                    return None
            
            # 條件1: 突破 ORB 高點
            breakout_pct = (current - orb_high) / orb_high * 100
            if breakout_pct < self.min_orb_breakout_pct:
                return None
            
            # 計算區間大小
            range_size = orb_high - orb_low
            if range_size <= 0:
                return None
            
            # 計算停損和目標
            stop_loss = round(orb_high - range_size * 0.3, 2)  # 停損在區間內 30%
            target = round(current + range_size * 2, 2)  # 目標 2R
            
            # 計算風報比
            risk = current - stop_loss
            reward = target - current
            rr_ratio = reward / risk if risk > 0 else 0
            
            # 計算信心度
            confidence = 80
            if breakout_pct > 0.5:
                confidence += 5
            if rr_ratio > 2.0:
                confidence += 5
            
            return {
                "symbol": data["symbol"],
                "signal_type": EntrySignalType.ORB_BREAKOUT,
                "source": "early_entry",
                "confidence": min(confidence, 95),
                "price": current,
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": round(rr_ratio, 2),
                "reason": f"📈 ORB 突破 | 突破 ${orb_high:.1f} (+{breakout_pct:.1f}%) | R/R {rr_ratio:.1f}",
                "details": {
                    "orb_high": orb_high,
                    "orb_low": orb_low,
                    "range_size": range_size,
                    "breakout_pct": breakout_pct
                }
            }
            
        except Exception as e:
            logger.debug(f"偵測 ORB 突破失敗: {e}")
            return None
    
    def detect_momentum_surge(self, data: Dict) -> Optional[Dict]:
        """
        偵測「動能爆發」信號
        
        條件：
        1. 漲幅 > 3%
        2. 價格在高檔區（接近今日最高）
        3. 有持續上漲動能
        """
        try:
            current = data.get("current", 0)
            high = data.get("high", 0)
            prev_close = data.get("prev_close", 0)
            change_pct = data.get("change_pct", 0)
            
            if current <= 0 or prev_close <= 0:
                return None
            
            # 條件1: 漲幅 > 3%
            if change_pct < 3.0:
                return None
            
            # 條件2: 價格在高檔區（距離今日最高 < 0.5%）
            if high > 0 and current < high * 0.995:
                return None
            
            # 計算停損和目標
            stop_loss = round(current * 0.97, 2)  # 停損 3%
            
            # 目標：往漲停方向設定
            limit_up = prev_close * 1.10
            target = round(min(limit_up * 0.98, current * 1.05), 2)
            
            # 計算風報比
            risk = current - stop_loss
            reward = target - current
            rr_ratio = reward / risk if risk > 0 else 0
            
            # 計算信心度
            confidence = 75
            if change_pct > 5:
                confidence += 10
            if change_pct > 7:
                confidence += 5
            if rr_ratio > 1.5:
                confidence += 5
            
            return {
                "symbol": data["symbol"],
                "signal_type": EntrySignalType.MOMENTUM_SURGE,
                "source": "early_entry",
                "confidence": min(confidence, 95),
                "price": current,
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": round(rr_ratio, 2),
                "reason": f"🚀 動能爆發 | +{change_pct:.1f}% 強勢攻擊 | R/R {rr_ratio:.1f}",
                "details": {
                    "change_pct": change_pct,
                    "prev_close": prev_close,
                    "limit_up": limit_up
                }
            }
            
        except Exception as e:
            logger.debug(f"偵測動能爆發失敗: {e}")
            return None
    
    def detect_vwap_bounce(self, data: Dict) -> Optional[Dict]:
        """
        偵測「VWAP 反彈」信號
        
        條件：
        1. 價格曾跌破 VWAP
        2. 現在回升到 VWAP 上方
        3. 整體趨勢仍為上漲（漲幅 > 0）
        """
        try:
            current = data.get("current", 0)
            vwap = data.get("vwap", 0)
            low = data.get("low", 0)
            change_pct = data.get("change_pct", 0)
            
            if current <= 0 or vwap <= 0:
                return None
            
            # 條件1: 今天曾跌破 VWAP（低點 < VWAP）
            if low >= vwap:
                return None
            
            # 條件2: 現在回升到 VWAP 上方
            above_vwap_pct = (current - vwap) / vwap * 100
            if above_vwap_pct < 0.1 or above_vwap_pct > 1.0:
                return None  # 要在 VWAP 上方 0.1%-1% 範圍
            
            # 條件3: 整體仍為上漲趨勢
            if change_pct < 0:
                return None
            
            # 計算停損和目標
            stop_loss = round(vwap * 0.99, 2)  # VWAP 下方 1%
            target = round(current * 1.03, 2)  # 目標 3%
            
            # 計算風報比
            risk = current - stop_loss
            reward = target - current
            rr_ratio = reward / risk if risk > 0 else 0
            
            if rr_ratio < self.risk_reward_min:
                return None
            
            confidence = 75
            if change_pct > 1:
                confidence += 5
            if rr_ratio > 2:
                confidence += 5
            
            return {
                "symbol": data["symbol"],
                "signal_type": EntrySignalType.VWAP_BOUNCE,
                "source": "early_entry",
                "confidence": min(confidence, 90),
                "price": current,
                "stop_loss": stop_loss,
                "target": target,
                "risk_reward": round(rr_ratio, 2),
                "reason": f"📊 VWAP 反彈 | VWAP ${vwap:.1f} 上方 {above_vwap_pct:.1f}% | R/R {rr_ratio:.1f}",
                "details": {
                    "vwap": vwap,
                    "low": low,
                    "above_vwap_pct": above_vwap_pct
                }
            }
            
        except Exception as e:
            logger.debug(f"偵測 VWAP 反彈失敗: {e}")
            return None
    
    async def scan_all_signals(self) -> List[Dict]:
        """
        掃描所有監控股票的進場信號
        """
        signals = []
        window, can_enter = self.get_current_window()
        
        if not can_enter:
            logger.info(f"⏳ 當前時間窗口: {window}，暫不進場")
            return signals
        
        logger.info(f"🔍 早盤掃描 | 時間窗口: {window} | 監控 {len(self.watchlist)} 檔股票")
        
        for symbol in self.watchlist:
            try:
                # 收集盤中數據
                data = await self.collect_intraday_data(symbol)
                if not data:
                    continue
                
                # 檢查是否已發出過信號（每天每檔只發一種信號）
                signal_key = f"{symbol}_{datetime.now().strftime('%Y%m%d')}"
                if signal_key in self.signals_sent:
                    continue
                
                # 依序偵測各種進場信號
                signal = None
                
                # 1. 開盤拉回買（早期窗口優先）
                if window == "early_window":
                    signal = self.detect_pullback_from_open(data)
                
                # 2. ORB 突破（主要窗口）
                if not signal and window in ["main_window", "extended_window"]:
                    signal = self.detect_orb_breakout(data)
                
                # 3. 動能爆發（任何窗口都可以）
                if not signal:
                    signal = self.detect_momentum_surge(data)
                
                # 4. VWAP 反彈（主要窗口）
                if not signal and window in ["main_window", "extended_window"]:
                    signal = self.detect_vwap_bounce(data)
                
                if signal:
                    signals.append(signal)
                    self.signals_sent[signal_key] = signal["signal_type"]
                    logger.info(f"🎯 發現信號: {symbol} | {signal['reason']}")
                
                # 避免 API 過載
                await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.debug(f"掃描 {symbol} 失敗: {e}")
        
        logger.info(f"✅ 早盤掃描完成 | 發現 {len(signals)} 個信號")
        return signals
    
    async def get_entry_recommendation(self, symbol: str) -> Optional[Dict]:
        """
        獲取單一股票的進場建議
        """
        data = await self.collect_intraday_data(symbol)
        if not data:
            return None
        
        # 嘗試所有偵測策略
        for detector in [
            self.detect_pullback_from_open,
            self.detect_orb_breakout,
            self.detect_momentum_surge,
            self.detect_vwap_bounce
        ]:
            signal = detector(data)
            if signal:
                return signal
        
        return None
    
    def reset_daily(self):
        """重置每日數據"""
        self.signals_sent.clear()
        self.intraday_data.clear()
        logger.info("🔄 早盤偵測器已重置")


# 單例
early_entry_detector = EarlyEntryDetector()
