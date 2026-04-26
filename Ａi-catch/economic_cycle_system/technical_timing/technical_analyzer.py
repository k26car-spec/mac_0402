"""
技術面與線型時機模組 v2.0
運用五年區間高低點、技術指標、價格型態判斷進出場時機

系統名稱：循環驅動多因子投資系統
模組4：技術面與線型時機模組
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import os
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from scipy import stats

warnings.filterwarnings('ignore')


@dataclass
class TechnicalSignal:
    """技術信號數據類"""
    ticker: str
    date: str
    signal_type: str  # buy, sell, hold, strong_buy, strong_sell
    strength: float  # 0-1
    price: float
    indicators: Dict[str, float]
    reasons: List[str]
    confidence: float  # 0-1
    
    def to_dict(self):
        return asdict(self)


class TechnicalAnalyzer:
    """
    技術面與線型時機分析器
    運用多種技術指標和價格型態判斷交易時機
    """
    
    def __init__(self, lookback_years: int = 5, market: str = "TW"):
        """
        初始化分析器
        
        Parameters:
        -----------
        lookback_years : int
            回看年數，用於計算歷史區間
        market : str
            市場: TW(台灣), US(美國)
        """
        self.lookback_years = lookback_years
        self.market = market
        self.price_data = {}
        self.technical_data = {}
        self.signals = {}
        self.support_resistance = {}
        self.last_update = None
        
        # 價格位置評分標準
        self.position_scoring = {
            "bottom_10": {"score": 90, "action": "strong_buy", "desc": "五年低點附近"},
            "10_25": {"score": 70, "action": "buy", "desc": "相對低檔"},
            "25_50": {"score": 50, "action": "hold", "desc": "中間區域"},
            "50_75": {"score": 30, "action": "caution", "desc": "相對高檔"},
            "75_90": {"score": 10, "action": "sell", "desc": "五年高點附近"},
            "top_10": {"score": 0, "action": "strong_sell", "desc": "歷史高點"}
        }
        
        # 交易信號定義
        self.signal_levels = {
            "strong_buy": (80, 100, "強烈買進"),
            "buy": (60, 80, "買進"),
            "hold": (40, 60, "持有觀望"),
            "sell": (20, 40, "賣出"),
            "strong_sell": (0, 20, "強烈賣出")
        }
    
    def fetch_price_data(self, ticker: str, period: str = "5y") -> pd.DataFrame:
        """獲取股價數據 (同時支援上市.TW和上櫃.TWO)"""
        try:
            print(f"  獲取 {ticker} 股價數據...", end="")
            
            # 準備要嘗試的後綴
            if ".TW" in ticker or ".TWO" in ticker:
                suffixes = [ticker]  # 已經有後綴
            else:
                suffixes = [f"{ticker}.TW", f"{ticker}.TWO"]  # 嘗試上市和上櫃
            
            hist = pd.DataFrame()
            
            for yf_ticker in suffixes:
                try:
                    stock = yf.Ticker(yf_ticker)
                    hist = stock.history(period=period, interval="1d")
                    
                    if not hist.empty and len(hist) >= 50:
                        print(f" 獲取 {len(hist)} 筆 ({yf_ticker})")
                        hist = self._calculate_indicators(hist)
                        self.price_data[ticker] = hist
                        return hist
                except:
                    continue
            
            # 都失敗時使用模擬數據
            print(" 使用模擬數據")
            return self._generate_mock_data(ticker, period)
            
        except Exception as e:
            print(f" 錯誤: {e}")
            return self._generate_mock_data(ticker, period)
    
    def _generate_mock_data(self, ticker: str, period: str) -> pd.DataFrame:
        """生成模擬數據"""
        period_days = {"1y": 252, "2y": 504, "5y": 1260}.get(period, 504)
        
        np.random.seed(hash(ticker) % 10000)
        dates = pd.date_range(end=datetime.now(), periods=period_days, freq='B')
        
        # 根據代號設定基礎價格
        if ticker in ["2330", "TSMC"]:
            base = 550
            drift = 0.0008
        elif ticker in ["2454", "2317"]:
            base = 200
            drift = 0.0006
        else:
            base = np.random.uniform(50, 300)
            drift = np.random.uniform(-0.0002, 0.0006)
        
        returns = np.random.normal(drift, 0.018, period_days)
        prices = base * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame(index=dates)
        df['Open'] = prices * np.random.uniform(0.99, 1.01, period_days)
        df['High'] = prices * np.random.uniform(1.01, 1.03, period_days)
        df['Low'] = prices * np.random.uniform(0.97, 0.99, period_days)
        df['Close'] = prices
        df['Volume'] = np.random.randint(5000000, 50000000, period_days)
        
        df['High'] = df[['Open', 'High', 'Close']].max(axis=1) * 1.005
        df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1) * 0.995
        
        df = self._calculate_indicators(df)
        self.price_data[ticker] = df
        return df
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算技術指標"""
        # 移動平均線
        df['SMA_5'] = df['Close'].rolling(5).mean()
        df['SMA_10'] = df['Close'].rolling(10).mean()
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['SMA_60'] = df['Close'].rolling(60).mean()
        df['SMA_120'] = df['Close'].rolling(120).mean()
        df['SMA_200'] = df['Close'].rolling(200).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # KD
        low_min = df['Low'].rolling(9).min()
        high_max = df['High'].rolling(9).max()
        df['RSV'] = (df['Close'] - low_min) / (high_max - low_min) * 100
        df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
        df['D'] = df['K'].ewm(com=2, adjust=False).mean()
        
        # 布林通道
        df['BB_Mid'] = df['Close'].rolling(20).mean()
        df['BB_Std'] = df['Close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Mid'] + 2 * df['BB_Std']
        df['BB_Lower'] = df['BB_Mid'] - 2 * df['BB_Std']
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Mid'] * 100
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower']) * 100
        
        # 成交量
        df['Vol_MA20'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_MA20']
        
        # 波動率
        df['Returns'] = df['Close'].pct_change()
        df['Volatility'] = df['Returns'].rolling(20).std() * np.sqrt(252) * 100
        
        # ATR
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['ATR_Pct'] = df['ATR'] / df['Close'] * 100
        
        return df
    
    def analyze_price_position(self, ticker: str) -> Dict:
        """分析五年區間價格位置"""
        if ticker not in self.price_data:
            self.fetch_price_data(ticker, f"{self.lookback_years}y")
        
        df = self.price_data[ticker]
        
        five_year_high = df['High'].max()
        five_year_low = df['Low'].min()
        current_price = df['Close'].iloc[-1]
        
        if five_year_high > five_year_low:
            position_pct = (current_price - five_year_low) / (five_year_high - five_year_low) * 100
        else:
            position_pct = 50
        
        # 判斷區域
        if position_pct <= 10:
            zone = "bottom_10"
        elif position_pct <= 25:
            zone = "10_25"
        elif position_pct <= 50:
            zone = "25_50"
        elif position_pct <= 75:
            zone = "50_75"
        elif position_pct <= 90:
            zone = "75_90"
        else:
            zone = "top_10"
        
        zone_info = self.position_scoring[zone]
        
        # 近一年區間
        recent = df.tail(252)
        recent_high = recent['High'].max()
        recent_low = recent['Low'].min()
        recent_position = (current_price - recent_low) / (recent_high - recent_low) * 100 if recent_high > recent_low else 50
        
        return {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "five_year_high": round(five_year_high, 2),
            "five_year_low": round(five_year_low, 2),
            "position_percentage": round(position_pct, 1),
            "position_zone": zone,
            "position_score": zone_info["score"],
            "position_action": zone_info["action"],
            "position_description": zone_info["desc"],
            "recent_high": round(recent_high, 2),
            "recent_low": round(recent_low, 2),
            "recent_position": round(recent_position, 1),
            "distance_to_high_pct": round((five_year_high - current_price) / current_price * 100, 1),
            "distance_to_low_pct": round((current_price - five_year_low) / current_price * 100, 1)
        }
    
    def detect_support_resistance(self, ticker: str, window: int = 20) -> Dict:
        """檢測支撐阻力位"""
        if ticker not in self.price_data:
            self.fetch_price_data(ticker)
        
        df = self.price_data[ticker]
        
        if len(df) < window * 2:
            return {"error": "數據不足"}
        
        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values
        current_price = closes[-1]
        
        # 找局部極值
        support_levels = []
        resistance_levels = []
        
        for i in range(window, len(df) - window):
            # 支撐
            if lows[i] == np.min(lows[i-window:i+window+1]):
                strength = self._calc_level_strength(df, lows[i], "support")
                if strength > 0.3:
                    support_levels.append({"price": round(lows[i], 2), "strength": round(strength, 2)})
            
            # 阻力
            if highs[i] == np.max(highs[i-window:i+window+1]):
                strength = self._calc_level_strength(df, highs[i], "resistance")
                if strength > 0.3:
                    resistance_levels.append({"price": round(highs[i], 2), "strength": round(strength, 2)})
        
        # 合併相近價位
        support_levels = self._merge_levels(support_levels)
        resistance_levels = self._merge_levels(resistance_levels)
        
        # 找最近的支撐阻力
        supports_below = [s for s in support_levels if s["price"] < current_price]
        resists_above = [r for r in resistance_levels if r["price"] > current_price]
        
        nearest_support = max(supports_below, key=lambda x: x["price"]) if supports_below else None
        nearest_resist = min(resists_above, key=lambda x: x["price"]) if resists_above else None
        
        result = {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "support_levels": sorted(support_levels, key=lambda x: x["strength"], reverse=True)[:5] if support_levels else [],
            "resistance_levels": sorted(resistance_levels, key=lambda x: x["strength"], reverse=True)[:5] if resistance_levels else [],
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resist,
            "support_distance_pct": round((current_price - nearest_support["price"]) / current_price * 100, 1) if nearest_support else None,
            "resistance_distance_pct": round((nearest_resist["price"] - current_price) / current_price * 100, 1) if nearest_resist else None
        }
        
        self.support_resistance[ticker] = result
        return result
    
    def _calc_level_strength(self, df: pd.DataFrame, level: float, level_type: str) -> float:
        """計算支撐阻力強度"""
        touches = 0
        for _, row in df.iterrows():
            if abs(row['Close'] - level) / level < 0.015:
                touches += 1
        return min(1.0, touches / 8)
    
    def _merge_levels(self, levels: List[Dict], threshold: float = 0.02) -> List[Dict]:
        """合併相近價位"""
        if not levels:
            return []
        
        levels = sorted(levels, key=lambda x: x["price"])
        merged = [levels[0]]
        
        for level in levels[1:]:
            if abs(level["price"] - merged[-1]["price"]) / merged[-1]["price"] <= threshold:
                merged[-1]["strength"] = max(merged[-1]["strength"], level["strength"])
            else:
                merged.append(level)
        
        return merged
    
    def analyze_technical_indicators(self, ticker: str) -> Dict:
        """分析所有技術指標"""
        if ticker not in self.price_data:
            self.fetch_price_data(ticker)
        
        df = self.price_data[ticker]
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 均線分析
        ma_analysis = self._analyze_ma(df, latest, prev)
        
        # 震盪指標
        oscillator_analysis = self._analyze_oscillators(df, latest, prev)
        
        # 成交量
        volume_analysis = self._analyze_volume(df, latest)
        
        # 趨勢
        trend_analysis = self._analyze_trend(df)
        
        # 綜合評分
        summary = self._generate_summary(ma_analysis, oscillator_analysis, volume_analysis, trend_analysis)
        
        result = {
            "ticker": ticker,
            "date": df.index[-1].strftime("%Y-%m-%d"),
            "price": round(latest['Close'], 2),
            "moving_averages": ma_analysis,
            "oscillators": oscillator_analysis,
            "volume": volume_analysis,
            "trend": trend_analysis,
            "summary": summary
        }
        
        self.technical_data[ticker] = result
        return result
    
    def _analyze_ma(self, df: pd.DataFrame, latest, prev) -> Dict:
        """均線分析"""
        price = latest['Close']
        sma20 = latest['SMA_20']
        sma60 = latest['SMA_60']
        sma120 = latest.get('SMA_120', sma60)
        
        # 均線排列
        if price > sma20 > sma60:
            alignment = "bullish"
        elif price < sma20 < sma60:
            alignment = "bearish"
        else:
            alignment = "mixed"
        
        # 交叉
        golden_cross = prev['SMA_20'] <= prev['SMA_60'] and latest['SMA_20'] > latest['SMA_60']
        death_cross = prev['SMA_20'] >= prev['SMA_60'] and latest['SMA_20'] < latest['SMA_60']
        
        return {
            "sma_20": round(sma20, 2),
            "sma_60": round(sma60, 2),
            "sma_120": round(sma120, 2),
            "price_vs_sma20_pct": round((price - sma20) / sma20 * 100, 1),
            "price_vs_sma60_pct": round((price - sma60) / sma60 * 100, 1),
            "alignment": alignment,
            "golden_cross": golden_cross,
            "death_cross": death_cross,
            "sma20_slope": round((latest['SMA_20'] - df['SMA_20'].iloc[-5]) / df['SMA_20'].iloc[-5] * 100, 2)
        }
    
    def _analyze_oscillators(self, df: pd.DataFrame, latest, prev) -> Dict:
        """震盪指標分析"""
        rsi = latest['RSI']
        k = latest['K']
        d = latest['D']
        macd = latest['MACD']
        macd_signal = latest['MACD_Signal']
        bb_pos = latest['BB_Position']
        
        # RSI信號
        rsi_signal = "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"
        
        # KD信號
        kd_signal = "overbought" if k > 80 and d > 80 else "oversold" if k < 20 and d < 20 else "neutral"
        kd_cross = "golden" if k > d and prev['K'] <= prev['D'] else "death" if k < d and prev['K'] >= prev['D'] else "none"
        
        # MACD信號
        macd_cross = "bullish" if macd > macd_signal and prev['MACD'] <= prev['MACD_Signal'] else \
                     "bearish" if macd < macd_signal and prev['MACD'] >= prev['MACD_Signal'] else "none"
        
        # 布林信號
        bb_signal = "upper" if bb_pos > 80 else "lower" if bb_pos < 20 else "middle"
        
        return {
            "rsi": round(rsi, 1),
            "rsi_signal": rsi_signal,
            "k": round(k, 1),
            "d": round(d, 1),
            "kd_signal": kd_signal,
            "kd_cross": kd_cross,
            "macd": round(macd, 4),
            "macd_signal_line": round(macd_signal, 4),
            "macd_hist": round(latest['MACD_Hist'], 4),
            "macd_cross": macd_cross,
            "bb_position": round(bb_pos, 1),
            "bb_signal": bb_signal,
            "bb_width": round(latest['BB_Width'], 1)
        }
    
    def _analyze_volume(self, df: pd.DataFrame, latest) -> Dict:
        """成交量分析"""
        vol_ratio = latest['Vol_Ratio']
        vol_signal = "spike" if vol_ratio > 2 else "high" if vol_ratio > 1.5 else "low" if vol_ratio < 0.5 else "normal"
        
        # 價量背離
        price_chg = (latest['Close'] - df['Close'].iloc[-5]) / df['Close'].iloc[-5] * 100
        vol_chg = (latest['Volume'] - df['Volume'].iloc[-5]) / df['Volume'].iloc[-5] * 100
        
        if price_chg > 2 and vol_chg < -20:
            divergence = "bearish"
        elif price_chg < -2 and vol_chg > 20:
            divergence = "bullish"
        else:
            divergence = "none"
        
        return {
            "volume": int(latest['Volume']),
            "vol_ma20": int(latest['Vol_MA20']),
            "vol_ratio": round(vol_ratio, 2),
            "vol_signal": vol_signal,
            "price_change_5d": round(price_chg, 1),
            "volume_change_5d": round(vol_chg, 1),
            "divergence": divergence
        }
    
    def _analyze_trend(self, df: pd.DataFrame) -> Dict:
        """趨勢分析"""
        prices = df['Close'].tail(20).values
        x = np.arange(len(prices))
        
        slope, _, r_value, _, _ = stats.linregress(x, prices)
        strength = abs(r_value)
        
        if slope > 0:
            direction = "up"
        elif slope < 0:
            direction = "down"
        else:
            direction = "sideways"
        
        volatility = df['Volatility'].iloc[-1]
        avg_vol = df['Volatility'].tail(60).mean()
        vol_ratio = volatility / avg_vol if avg_vol > 0 else 1
        
        return {
            "direction": direction,
            "slope_pct": round(slope / prices[0] * 100, 2),
            "strength": round(strength, 3),
            "r_squared": round(r_value ** 2, 3),
            "volatility": round(volatility, 1),
            "volatility_ratio": round(vol_ratio, 2),
            "atr_pct": round(df['ATR_Pct'].iloc[-1], 2)
        }
    
    def _generate_summary(self, ma: Dict, osc: Dict, vol: Dict, trend: Dict) -> Dict:
        """生成綜合摘要"""
        bullish = 0
        bearish = 0
        
        # 均線
        if ma["alignment"] == "bullish":
            bullish += 1
        elif ma["alignment"] == "bearish":
            bearish += 1
        
        if ma["golden_cross"]:
            bullish += 1
        if ma["death_cross"]:
            bearish += 1
        
        # RSI
        if osc["rsi_signal"] == "oversold":
            bullish += 1
        elif osc["rsi_signal"] == "overbought":
            bearish += 1
        
        # KD
        if osc["kd_cross"] == "golden":
            bullish += 1
        elif osc["kd_cross"] == "death":
            bearish += 1
        
        # MACD
        if osc["macd_cross"] == "bullish":
            bullish += 1
        elif osc["macd_cross"] == "bearish":
            bearish += 1
        
        # 布林
        if osc["bb_signal"] == "lower":
            bullish += 1
        elif osc["bb_signal"] == "upper":
            bearish += 1
        
        # 成交量
        if vol["divergence"] == "bullish":
            bullish += 1
        elif vol["divergence"] == "bearish":
            bearish += 1
        
        # 趨勢
        if trend["direction"] == "up" and trend["strength"] > 0.5:
            bullish += 1
        elif trend["direction"] == "down" and trend["strength"] > 0.5:
            bearish += 1
        
        total = bullish + bearish + 1
        bull_ratio = bullish / total
        bear_ratio = bearish / total
        
        if bull_ratio > 0.6:
            signal = "bullish"
            strength = bull_ratio
        elif bear_ratio > 0.6:
            signal = "bearish"
            strength = bear_ratio
        else:
            signal = "neutral"
            strength = max(bull_ratio, bear_ratio)
        
        return {
            "bullish_count": bullish,
            "bearish_count": bearish,
            "bull_ratio": round(bull_ratio, 2),
            "bear_ratio": round(bear_ratio, 2),
            "overall_signal": signal,
            "signal_strength": round(strength, 3),
            "confidence": round(min(0.95, strength * 1.2), 3)
        }
    
    def generate_trading_signals(self, ticker: str) -> List[TechnicalSignal]:
        """生成交易信號"""
        position = self.analyze_price_position(ticker)
        tech = self.analyze_technical_indicators(ticker)
        sr = self.detect_support_resistance(ticker)
        
        signals = []
        current_price = position["current_price"]
        
        # 價格位置信號
        pos_score = position["position_score"]
        if pos_score >= 80:
            sig_type = "strong_buy"
            strength = 0.9
        elif pos_score >= 60:
            sig_type = "buy"
            strength = 0.7
        elif pos_score <= 10:
            sig_type = "strong_sell"
            strength = 0.9
        elif pos_score <= 30:
            sig_type = "sell"
            strength = 0.7
        else:
            sig_type = "hold"
            strength = 0.5
        
        signals.append(TechnicalSignal(
            ticker=ticker,
            date=datetime.now().strftime("%Y-%m-%d"),
            signal_type=sig_type,
            strength=strength,
            price=current_price,
            indicators={"position_pct": position["position_percentage"]},
            reasons=[f"五年區間位置: {position['position_percentage']:.1f}% ({position['position_description']})"],
            confidence=strength * 0.9
        ))
        
        # 技術指標信號
        summary = tech["summary"]
        if summary["overall_signal"] == "bullish":
            sig_type = "buy" if summary["signal_strength"] < 0.8 else "strong_buy"
            reasons = []
            if tech["moving_averages"]["golden_cross"]:
                reasons.append("均線黃金交叉")
            if tech["oscillators"]["rsi_signal"] == "oversold":
                reasons.append(f"RSI超賣({tech['oscillators']['rsi']:.0f})")
            if tech["oscillators"]["macd_cross"] == "bullish":
                reasons.append("MACD黃金交叉")
            
            signals.append(TechnicalSignal(
                ticker=ticker,
                date=datetime.now().strftime("%Y-%m-%d"),
                signal_type=sig_type,
                strength=summary["signal_strength"],
                price=current_price,
                indicators={"bull_ratio": summary["bull_ratio"]},
                reasons=reasons if reasons else ["技術指標偏多"],
                confidence=summary["confidence"]
            ))
        
        elif summary["overall_signal"] == "bearish":
            sig_type = "sell" if summary["signal_strength"] < 0.8 else "strong_sell"
            reasons = []
            if tech["moving_averages"]["death_cross"]:
                reasons.append("均線死亡交叉")
            if tech["oscillators"]["rsi_signal"] == "overbought":
                reasons.append(f"RSI超買({tech['oscillators']['rsi']:.0f})")
            if tech["oscillators"]["macd_cross"] == "bearish":
                reasons.append("MACD死亡交叉")
            
            signals.append(TechnicalSignal(
                ticker=ticker,
                date=datetime.now().strftime("%Y-%m-%d"),
                signal_type=sig_type,
                strength=summary["signal_strength"],
                price=current_price,
                indicators={"bear_ratio": summary["bear_ratio"]},
                reasons=reasons if reasons else ["技術指標偏空"],
                confidence=summary["confidence"]
            ))
        
        # 支撐阻力信號
        if sr.get("nearest_support") and sr.get("support_distance_pct"):
            if sr["support_distance_pct"] <= 3:
                signals.append(TechnicalSignal(
                    ticker=ticker,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    signal_type="buy",
                    strength=sr["nearest_support"]["strength"],
                    price=current_price,
                    indicators={"support": sr["nearest_support"]["price"]},
                    reasons=[f"接近支撐位 {sr['nearest_support']['price']} (距離 {sr['support_distance_pct']:.1f}%)"],
                    confidence=sr["nearest_support"]["strength"] * 0.8
                ))
        
        if sr.get("nearest_resistance") and sr.get("resistance_distance_pct"):
            if sr["resistance_distance_pct"] <= 3:
                signals.append(TechnicalSignal(
                    ticker=ticker,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    signal_type="sell",
                    strength=sr["nearest_resistance"]["strength"],
                    price=current_price,
                    indicators={"resistance": sr["nearest_resistance"]["price"]},
                    reasons=[f"接近阻力位 {sr['nearest_resistance']['price']} (距離 {sr['resistance_distance_pct']:.1f}%)"],
                    confidence=sr["nearest_resistance"]["strength"] * 0.8
                ))
        
        # 整合信號
        buy_strength = sum(s.strength * s.confidence for s in signals if s.signal_type in ["buy", "strong_buy"])
        sell_strength = sum(s.strength * s.confidence for s in signals if s.signal_type in ["sell", "strong_sell"])
        
        total = buy_strength + sell_strength + 0.1
        
        if buy_strength / total > 0.6:
            final_type = "strong_buy" if buy_strength / total > 0.8 else "buy"
            final_strength = buy_strength / total
        elif sell_strength / total > 0.6:
            final_type = "strong_sell" if sell_strength / total > 0.8 else "sell"
            final_strength = sell_strength / total
        else:
            final_type = "hold"
            final_strength = max(buy_strength, sell_strength) / total
        
        all_reasons = []
        for s in signals:
            all_reasons.extend(s.reasons)
        
        final_signal = TechnicalSignal(
            ticker=ticker,
            date=datetime.now().strftime("%Y-%m-%d"),
            signal_type=final_type,
            strength=round(final_strength, 3),
            price=current_price,
            indicators={"buy_strength": round(buy_strength, 3), "sell_strength": round(sell_strength, 3)},
            reasons=all_reasons[:3],
            confidence=round(min(0.95, final_strength * 1.1), 3)
        )
        
        signals.append(final_signal)
        self.signals[ticker] = signals
        
        return signals
    
    def generate_trading_plan(self, ticker: str) -> Dict:
        """生成交易計劃"""
        signals = self.generate_trading_signals(ticker)
        position = self.analyze_price_position(ticker)
        tech = self.analyze_technical_indicators(ticker)
        sr = self.detect_support_resistance(ticker)
        
        final = signals[-1]
        current_price = position["current_price"]
        
        # 停損
        if sr.get("nearest_support"):
            stop_loss = round(sr["nearest_support"]["price"] * 0.98, 2)
            stop_type = "支撐下方"
        else:
            stop_loss = round(current_price * 0.92, 2)
            stop_type = "固定8%"
        
        stop_loss_pct = round((current_price - stop_loss) / current_price * 100, 1)
        
        # 獲利目標
        if sr.get("nearest_resistance"):
            take_profit = round(sr["nearest_resistance"]["price"], 2)
            tp_type = "阻力位"
        else:
            take_profit = round(current_price * 1.15, 2)
            tp_type = "固定15%"
        
        take_profit_pct = round((take_profit - current_price) / current_price * 100, 1)
        
        # 風險報酬比
        risk = current_price - stop_loss
        reward = take_profit - current_price
        rr_ratio = round(reward / risk, 2) if risk > 0 else 1
        
        # 建議動作
        action_map = {
            "strong_buy": {"action": "積極買入", "urgency": "高", "allocation": "30%"},
            "buy": {"action": "買入", "urgency": "中", "allocation": "20%"},
            "hold": {"action": "持有觀望", "urgency": "低", "allocation": "維持"},
            "sell": {"action": "賣出", "urgency": "中", "allocation": "-20%"},
            "strong_sell": {"action": "強力賣出", "urgency": "高", "allocation": "清倉"}
        }
        
        rec = action_map.get(final.signal_type, action_map["hold"])
        
        return {
            "ticker": ticker,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_price": current_price,
            "final_signal": final.signal_type,
            "signal_strength": final.strength,
            "confidence": final.confidence,
            "reasons": final.reasons,
            
            "position_analysis": {
                "zone": position["position_zone"],
                "score": position["position_score"],
                "description": position["position_description"]
            },
            
            "recommendation": rec,
            
            "risk_management": {
                "stop_loss": stop_loss,
                "stop_loss_pct": stop_loss_pct,
                "stop_type": stop_type,
                "take_profit": take_profit,
                "take_profit_pct": take_profit_pct,
                "take_profit_type": tp_type,
                "risk_reward_ratio": rr_ratio
            },
            
            "key_levels": {
                "support": sr["nearest_support"]["price"] if sr.get("nearest_support") else None,
                "resistance": sr["nearest_resistance"]["price"] if sr.get("nearest_resistance") else None,
                "sma_20": tech["moving_averages"]["sma_20"],
                "sma_60": tech["moving_averages"]["sma_60"]
            },
            
            "indicators_summary": {
                "rsi": tech["oscillators"]["rsi"],
                "kd": f"K:{tech['oscillators']['k']:.0f}/D:{tech['oscillators']['d']:.0f}",
                "macd": tech["oscillators"]["macd_cross"],
                "trend": tech["trend"]["direction"],
                "volatility": tech["trend"]["volatility"]
            }
        }
    
    def generate_report(self, ticker: str) -> str:
        """生成分析報告"""
        plan = self.generate_trading_plan(ticker)
        position = self.analyze_price_position(ticker)
        tech = self.analyze_technical_indicators(ticker)
        
        report = f"""
{'='*80}
📈 技術面與線型時機分析報告
{'='*80}

股票代號: {ticker}
分析時間: {plan['analysis_date']}
當前價格: {plan['current_price']}

{'─'*80}
🎯 【交易信號】
{'─'*80}

最終信號: {plan['final_signal'].upper()}
信號強度: {plan['signal_strength']:.1%}
信心度: {plan['confidence']:.1%}

主要理由:
"""
        for reason in plan['reasons']:
            report += f"  • {reason}\n"
        
        report += f"""
{'─'*80}
📊 【價格位置分析】
{'─'*80}

五年區間: {position['five_year_low']:.2f} - {position['five_year_high']:.2f}
當前位置: {position['position_percentage']:.1f}% ({position['position_description']})
評分: {position['position_score']}/100

距離高點: {position['distance_to_high_pct']:.1f}%
距離低點: {position['distance_to_low_pct']:.1f}%

{'─'*80}
📉 【技術指標】
{'─'*80}

均線分析:
  20日均線: {tech['moving_averages']['sma_20']:.2f} (價格 {tech['moving_averages']['price_vs_sma20_pct']:+.1f}%)
  60日均線: {tech['moving_averages']['sma_60']:.2f} (價格 {tech['moving_averages']['price_vs_sma60_pct']:+.1f}%)
  排列: {tech['moving_averages']['alignment']}

震盪指標:
  RSI: {tech['oscillators']['rsi']:.1f} ({tech['oscillators']['rsi_signal']})
  KD: K={tech['oscillators']['k']:.0f} D={tech['oscillators']['d']:.0f} ({tech['oscillators']['kd_signal']})
  MACD: {tech['oscillators']['macd']:.4f} ({tech['oscillators']['macd_cross']})
  布林位置: {tech['oscillators']['bb_position']:.1f}% ({tech['oscillators']['bb_signal']})

趨勢:
  方向: {tech['trend']['direction']}
  強度: {tech['trend']['strength']:.2f}
  波動率: {tech['trend']['volatility']:.1f}%

綜合:
  多方信號: {tech['summary']['bullish_count']}
  空方信號: {tech['summary']['bearish_count']}
  整體: {tech['summary']['overall_signal']}

{'─'*80}
💡 【交易建議】
{'─'*80}

建議動作: {plan['recommendation']['action']}
緊急程度: {plan['recommendation']['urgency']}
建議倉位: {plan['recommendation']['allocation']}

風險管理:
  停損價位: {plan['risk_management']['stop_loss']:.2f} (-{plan['risk_management']['stop_loss_pct']:.1f}%)
  獲利目標: {plan['risk_management']['take_profit']:.2f} (+{plan['risk_management']['take_profit_pct']:.1f}%)
  風險報酬比: 1:{plan['risk_management']['risk_reward_ratio']:.1f}

關鍵價位:
  支撐位: {plan['key_levels']['support'] or 'N/A'}
  阻力位: {plan['key_levels']['resistance'] or 'N/A'}

{'='*80}
"""
        return report
    
    def save_report(self, ticker: str, directory: str = "reports"):
        """保存報告"""
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(directory, f"{ticker}_technical_report_{datetime.now().strftime('%Y%m%d')}.txt")
        
        report = self.generate_report(ticker)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📄 報告已保存: {filename}")
        return filename
    
    def batch_analyze(self, tickers: List[str]) -> List[Dict]:
        """批量分析"""
        print(f"\n📈 批量技術分析 ({len(tickers)} 檔)")
        print("=" * 60)
        
        results = []
        for ticker in tickers:
            try:
                plan = self.generate_trading_plan(ticker)
                
                signal_emoji = {
                    "strong_buy": "🔥", "buy": "📈", "hold": "➡️",
                    "sell": "📉", "strong_sell": "⚠️"
                }.get(plan["final_signal"], "➡️")
                
                print(f"  {ticker}: {signal_emoji} {plan['recommendation']['action']} "
                      f"(強度: {plan['signal_strength']:.1%})")
                
                results.append(plan)
            except Exception as e:
                print(f"  {ticker}: ❌ 錯誤 - {e}")
        
        # 按信號強度排序
        results.sort(key=lambda x: x["signal_strength"], reverse=True)
        
        self.last_update = datetime.now()
        print("\n" + "=" * 60)
        print("✅ 分析完成!")
        
        return results
    
    def to_dict(self) -> Dict:
        """API 格式"""
        return {
            "market": self.market,
            "analysis_count": len(self.technical_data),
            "signals": {k: [s.to_dict() for s in v] for k, v in self.signals.items()},
            "last_update": self.last_update.isoformat() if self.last_update else None
        }


def main():
    """主程式"""
    print("=" * 80)
    print("📈 技術面與線型時機分析系統 v2.0")
    print("=" * 80)
    
    # 預設股票
    tickers = ["2330", "2454", "2317", "2308", "2382", "3231", "6669", "3017"]
    
    analyzer = TechnicalAnalyzer(market="TW")
    
    # 批量分析
    results = analyzer.batch_analyze(tickers)
    
    # 顯示買入信號
    buy_signals = [r for r in results if r["final_signal"] in ["buy", "strong_buy"]]
    if buy_signals:
        print("\n🔥 買入信號:")
        for r in buy_signals[:5]:
            print(f"  {r['ticker']}: {r['recommendation']['action']} | "
                  f"價格 {r['current_price']} | 停損 {r['risk_management']['stop_loss']}")
    
    # 顯示賣出信號
    sell_signals = [r for r in results if r["final_signal"] in ["sell", "strong_sell"]]
    if sell_signals:
        print("\n⚠️ 賣出信號:")
        for r in sell_signals[:5]:
            print(f"  {r['ticker']}: {r['recommendation']['action']}")
    
    # 生成詳細報告（取第一檔）
    if results:
        print("\n" + "=" * 80)
        report = analyzer.generate_report(results[0]["ticker"])
        print(report)
        
        analyzer.save_report(results[0]["ticker"], "technical_timing/reports")
    
    return analyzer


if __name__ == "__main__":
    main()
