"""
📌 增強版低點買進 (Buy on Dip) 分析模組 v3.0
=====================================
核心邏輯提供：USER
整合實作：Antigravity AI
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DipQuality(Enum):
    """低點品質分級"""
    DANGEROUS = "接刀風險"           # 繼續破底，不宜進場
    TESTING = "支撐測試中"           # 在支撐附近，觀察中
    CONFIRMED = "止跌確認"           # 出現止跌訊號，可考慮
    STRONG_BUY = "強力反彈訊號"      # 多重確認，積極買點

@dataclass
class DipSignal:
    """低點訊號結果"""
    quality: DipQuality
    confidence: int
    score: float
    reasons: List[str]
    warnings: List[str]
    entry_type: str
    stop_loss_price: float
    target_price: float

class EnhancedDipAnalyzer:
    """增強版低點分析器"""
    
    def __init__(self):
        self.weights = {
            "price_support": 0.20,
            "volume_shrink": 0.10,
            "rsi_reversal": 0.10,
            "kd_golden": 0.10,
            "macd_divergence": 0.10,
            "bollinger_bounce": 0.10,
            "money_flow": 0.30  # 提高資金流權重，增加敏感度
        }
        # 🆕 訊號平滑與滯後機制
        self.state_history: Dict[str, List[float]] = {}  # 儲存個股近期分數
        self.last_quality: Dict[str, DipQuality] = {}    # 儲存個股上次狀態
        self.smoothing_window = 3  # 平滑窗口大小
    
    def analyze(
        self,
        symbol: str,  # 🆕 增加 symbol 參數用於追蹤狀態
        df: pd.DataFrame,
        current_price: float,
        ofi: float = 0,
        bid_ask_ratio: float = 1.0,
        ma5: float = 0,
        ma20: float = 0
    ) -> DipSignal:
        """綜合分析低點品質"""
        if df is None or df.empty or len(df) < 20:
            return None

        total_score = 0.0
        reasons = []
        warnings = []
        
        # 取得均線
        if ma5 == 0: ma5 = df['Close'].rolling(5).mean().iloc[-1]
        if ma20 == 0: ma20 = df['Close'].rolling(20).mean().iloc[-1]
        
        # 1. 價格支撐分析
        s, r, w = self._check_price_support(current_price, df, ma5)
        total_score += s * self.weights["price_support"]
        if r: reasons.append(r)
        if w: warnings.append(w)
        
        # 2. 成交量萎縮（賣壓減輕）
        s, r, w = self._check_volume_shrink(df)
        total_score += s * self.weights["volume_shrink"]
        if r: reasons.append(r)
        if w: warnings.append(w)
        
        # 3. RSI 反轉
        s, r = self._check_rsi_reversal(df)
        total_score += s * self.weights["rsi_reversal"]
        if r: reasons.append(r)
        
        # 4. KD 黃金交叉
        s, r = self._check_kd_golden_cross(df)
        total_score += s * self.weights["kd_golden"]
        if r: reasons.append(r)
        
        # 5. MACD 背離/向好
        s, r = self._check_macd_divergence(df)
        total_score += s * self.weights["macd_divergence"]
        if r: reasons.append(r)
        
        # 6. 布林下軌反彈
        s, r = self._check_bollinger_bounce(df, current_price)
        total_score += s * self.weights["bollinger_bounce"]
        if r: reasons.append(r)
        
        # 7. 資金流向
        s, r, w = self._check_money_flow(ofi, bid_ask_ratio)
        total_score += s * self.weights["money_flow"]
        if r: reasons.append(r)
        if w: warnings.append(w)

        # 8. 🆕 價格慣性 (下影線支撐)
        s, r = self._check_price_inertia(df)
        total_score += s * 0.10 # 額外加成因子
        if r: reasons.append(r)
        
        # 🆕 執行平滑處理 (Smoothing)
        if symbol not in self.state_history:
            self.state_history[symbol] = []
        self.state_history[symbol].append(total_score)
        if len(self.state_history[symbol]) > self.smoothing_window:
            self.state_history[symbol].pop(0)
        
        # 使用平均分數，減少瞬時跳動
        smoothed_score = sum(self.state_history[symbol]) / len(self.state_history[symbol])
        
        # 🆕 執行滯後處理 (Hysteresis)
        prev_quality = self.last_quality.get(symbol, DipQuality.TESTING)
        quality, entry_type = self._determine_quality_v2(smoothed_score, warnings, prev_quality)
        self.last_quality[symbol] = quality
        
        confidence = self._calculate_confidence(smoothed_score, quality, len(warnings))
        stop_loss = self._calculate_stop_loss(current_price, df)
        target = self._calculate_target(current_price, df, quality)
        
        return DipSignal(
            quality=quality,
            confidence=confidence,
            score=round(smoothed_score, 2),
            reasons=reasons,
            warnings=warnings,
            entry_type=entry_type,
            stop_loss_price=stop_loss,
            target_price=target
        )

    def _check_price_support(self, price, df, ma5):
        recent_low = df['Low'].tail(15).min()
        deviation = abs(price - ma5) / ma5 * 100
        if price < recent_low * 0.99:
            return 20, "", "⚠️ 價格破底，下行趨勢中"
        elif price >= recent_low * 1.002:
            return 85, f"✅ 守住支撐 ${recent_low:.1f}", ""
        return 50, "", "⚠️ 測試支撐中"

    def _check_volume_shrink(self, df):
        v_ma5 = df['Volume'].tail(5).mean()
        curr_v = df['Volume'].iloc[-1]
        v_ratio = curr_v / v_ma5
        
        # 🆕 進階邏輯：偵測「換手量」後「窒息量」的概念
        # 檢查過去 10 個交易日內是否曾出現過 2 倍以上的近期最大量（疑似底部換手）
        recent_volumes = df['Volume'].tail(15)
        max_v_recent = recent_volumes.iloc[:-2].max()
        avg_v_recent = recent_volumes.iloc[:-2].mean()
        
        has_washout_volume = max_v_recent > avg_v_recent * 2.2
        
        # 窒息量判定
        is_exhausted = v_ratio < 0.5
        
        if has_washout_volume and is_exhausted:
            return 100, "🔥 底部換手完成！爆量後出現窒息量，籌碼極度穩定", ""
        elif is_exhausted:
            return 90, f"✅ 極致量縮 ({v_ratio*100:.0f}%) 賣壓完全枯竭", ""
        elif v_ratio < 0.75:
            return 75, "✅ 出現凹洞量，籌碼沉澱中", ""
        elif v_ratio > 1.5:
            # 如果是帶量下跌
            if df['Close'].iloc[-1] < df['Open'].iloc[-1]:
                return 10, "", "🚨 放量下殺，恐慌性賣壓尚未止盡"
            else:
                return 60, "⚡ 帶量上攻（中繼訊號）", ""
        
        return 50, "", ""

    def _check_rsi_reversal(self, df):
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        curr_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        # 🆕 偵測技術背離 (Divergence)
        # 尋找過去 10 天的股價最低點與對應 RSI
        recent_prices = df['Close'].tail(15)
        recent_rsi = rsi.tail(15)
        
        prev_low_idx = recent_prices.iloc[:-2].idxmin()
        prev_low_price = recent_prices.loc[prev_low_idx]
        prev_low_rsi = recent_rsi.loc[prev_low_idx]
        
        curr_price = df['Close'].iloc[-1]
        
        # 背離條件：股價破底 (或接近底) 但 RSI 顯著提升
        if curr_price <= prev_low_price * 1.01 and curr_rsi > prev_low_rsi + 5:
            return 100, f"🔥 RSI 牛市背離！股價破底但 RSI 轉強 ({curr_rsi:.1f} vs {prev_low_rsi:.1f})"
            
        if curr_rsi < 30 and curr_rsi > prev_rsi:
            return 95, f"✅ RSI 超賣打勾 ({curr_rsi:.1f})"
        elif curr_rsi < 40:
            return 70, "✅ RSI 進入低檔區"
        return 50, ""

    def _check_kd_golden_cross(self, df):
        low_9 = df['Low'].rolling(9).min()
        high_9 = df['High'].rolling(9).max()
        rsv = (df['Close'] - low_9) / (high_9 - low_9) * 100
        k = rsv.ewm(com=2).mean()
        d = k.ewm(com=2).mean()
        k_val = k.iloc[-1]
        d_val = d.iloc[-1]
        if k_val > d_val and k.iloc[-2] <= d.iloc[-2] and k_val < 30:
            return 95, "✅ KD 低檔黃金交叉"
        elif k_val > d_val and k_val < 40:
            return 75, "✅ KD 多方交叉"
        return 50, ""

    def _check_macd_divergence(self, df):
        exp12 = df['Close'].ewm(span=12).mean()
        exp26 = df['Close'].ewm(span=26).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9).mean()
        hist = macd - signal
        
        curr_hist = hist.iloc[-1]
        prev_hist = hist.iloc[-2]
        
        # 偵測 MACD 柱狀背離
        recent_prices = df['Close'].tail(10)
        recent_hist = hist.tail(10)
        
        prev_low_price = recent_prices.iloc[:-2].min()
        curr_price = df['Close'].iloc[-1]
        
        if curr_price < prev_low_price and curr_hist > prev_hist:
            return 95, "🔥 MACD 牛市背離！柱狀圖縮減且股價創新低"
            
        if curr_hist > prev_hist:
            return 80, "✅ MACD 柱狀收斂"
        return 50, ""

    def _check_bollinger_bounce(self, df, price):
        ma20 = df['Close'].rolling(20).mean()
        std20 = df['Close'].rolling(20).std()
        lower = ma20 - (std20 * 2)
        l_val = lower.iloc[-1]
        if price < l_val * 1.01:
            return 90, "✅ 觸及布林下軌支撐"
        return 60, ""

    def _check_price_inertia(self, df):
        """偵測價格慣性：如連續下影線"""
        last_3 = df.tail(3)
        shadows = []
        
        for i in range(3):
            o, c, l = last_3['Open'].iloc[i], last_3['Close'].iloc[i], last_3['Low'].iloc[i]
            body_bottom = min(o, c)
            lower_shadow = body_bottom - l
            body_size = abs(o - c)
            # 下影線比例（相對於實體）
            shadow_ratio = lower_shadow / body_size if body_size > 0 else 2.0
            shadows.append(shadow_ratio)

        # 判定 A：連續三天下影線
        if all(s > 0.8 for s in shadows):
            return 100, "🔥 強烈價格慣性：連續三天收下影線，買盤積極打底"
        
        # 判定 B：今日有強力長下影線
        if shadows[-1] > 1.5:
            return 85, "✅ 出現長下影線，低檔承接力強"
            
        return 50, ""

    def _check_money_flow(self, ofi, ratio):
        score = 60
        res, warn = "", ""
        
        # 強化 OFI 判定
        if ofi > 100:
            score = 95
            res = f"✅ 大單強力流入 (OFI:{ofi:+.0f})"
        elif ofi > 0:
            score = 80
            res = f"✅ 資金小幅流入 (OFI:{ofi:+.0f})"
        elif ofi < -800:
            score = 0
            warn = f"🚨 大戶集體倒貨 (OFI:{ofi:+.0f})"
        elif ofi < -200:
            score = 20
            warn = f"⚠️ 大戶持續拋售 (OFI:{ofi:+.0f})"
        
        # 掛單比（買/賣力道）
        if ratio > 1.5:
            score = min(100, score + 15)
            res += " | 買盤支撐強"
        elif ratio < 0.6:
            score = max(0, score - 20)
            warn += " | 賣壓掛單重"
            
        return score, res, warn

    def _determine_quality_v2(self, score, warnings, prev_quality):
        """
        帶有滯後機制的判定邏輯 (V2)
        防止在門檻點來回跳動
        """
        has_heavy_sell = any("🚨" in w for w in warnings)
        if has_heavy_sell or len(warnings) >= 3 or score < 30:
            return DipQuality.DANGEROUS, "wait"
            
        # 滯後門檻 (Hysteresis Thresholds)
        # 如果上次是 CONFIRMED (65)，要掉回 TESTING 需要低於 55
        # 如果上次是 TESTING (40)，要升到 CONFIRMED 需要高於 70
        
        if prev_quality == DipQuality.STRONG_BUY:
            if score >= 75: return DipQuality.STRONG_BUY, "aggressive"
            if score >= 60: return DipQuality.CONFIRMED, "conservative"
        elif prev_quality == DipQuality.CONFIRMED:
            if score >= 85: return DipQuality.STRONG_BUY, "aggressive"
            if score >= 55: return DipQuality.CONFIRMED, "conservative"
        elif prev_quality == DipQuality.TESTING:
            if score >= 85: return DipQuality.STRONG_BUY, "aggressive"
            if score >= 70: return DipQuality.CONFIRMED, "conservative"
            if score >= 35: return DipQuality.TESTING, "wait"
        else: # prev is DANGEROUS
            if score >= 75: return DipQuality.CONFIRMED, "conservative"
            if score >= 50: return DipQuality.TESTING, "wait"
            
        return DipQuality.DANGEROUS, "wait"

    def _determine_quality(self, score, warnings):
        # 舊版邏輯 (保留以防萬一或單次呼叫)
        has_heavy_sell = any("🚨" in w for w in warnings)
        
        if has_heavy_sell or len(warnings) >= 2 or score < 40:
            return DipQuality.DANGEROUS, "wait"
        if score >= 85:
            return DipQuality.STRONG_BUY, "aggressive"
        if score >= 65:
            return DipQuality.CONFIRMED, "conservative"
        return DipQuality.TESTING, "wait"

    def _calculate_confidence(self, score, quality, w_count):
        conf = int(score * 0.9) - (w_count * 15)
        if quality == DipQuality.STRONG_BUY: conf += 10
        return max(0, min(100, conf))

    def _calculate_stop_loss(self, price, df):
        return round(df['Low'].tail(10).min() * 0.985, 2)

    def _calculate_target(self, price, df, quality):
        mult = 1.06 if quality == DipQuality.STRONG_BUY else 1.03
        return round(price * mult, 2)

# 全局實例
dip_analyzer = EnhancedDipAnalyzer()

async def get_dip_analysis(symbol, df, price, ofi=0, ratio=1.0):
    """便捷調用介面"""
    return dip_analyzer.analyze(symbol, df, price, ofi, ratio)
