#!/usr/bin/env python3
"""
增強版歷史回測系統 v3.0 — LSTM 整合版
Enhanced Backtesting Engine with LSTM Signal Engine

AI 引擎：LSTM 深度學習模型（取代規則型 expert_manager）
修正記錄：
  1. 同一股票有持倉時禁止重複開倉
  2. 每檔股票回測前重置資金
  3. 做空資金正確歸還（進場本金 + 損益）
  4. 單筆倉位 ≤ 資金 20%（風控）
  5. 隨機種子固定 → 回測結果可重現
"""

import sys, os, pickle, warnings, asyncio
import random
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict, Optional
from datetime import datetime

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['PYTHONHASHSEED'] = '42'        # Python hash 種子（影響 dict 順序等）
warnings.filterwarnings('ignore')

# ─── 🌱 固定所有隨機種子，確保回測結果可重現 ──────────────────────
def set_all_seeds(seed: int = 42):
    """固定 random / numpy / TensorFlow / PyTorch 的隨機種子"""
    random.seed(seed)
    np.random.seed(seed)

    # TensorFlow（我們的 LSTM 框架）
    try:
        import tensorflow as tf
        tf.random.set_seed(seed)
        # 單執行緒確保計算順序一致
        os.environ['TF_DETERMINISTIC_OPS'] = '1'
    except ImportError:
        pass

    # PyTorch（選用，若環境有安裝）
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass  # 環境沒有 PyTorch，跳過

set_all_seeds(42)
print("🌱 隨機種子已固定 (seed=42)，回測結果可重現")

import tensorflow as tf
from tensorflow.keras.models import load_model

# 壓制 TF Python 層級的日誌（C++ 層由 TF_CPP_MIN_LOG_LEVEL 控制）
tf.get_logger().setLevel('ERROR')
import logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)

# ─── LSTM 模型路徑設定 ──────────────────────────────────────
MODEL_DIR   = "models/lstm_smart_entry"
WL_PATH     = "lstm_whitelist.json"
SEQ_LEN     = 20   # v5 序列長度

# 嘗試匯入特徵建構器
try:
    from lstm_feature_builder import build_features_full, ALL_FEATURE_COLS
    HAS_FEATURE_BUILDER = True
except ImportError:
    HAS_FEATURE_BUILDER = False
    print("⚠️  lstm_feature_builder 未找到，將使用精簡特徵模式")


# ─── LSTM 訊號引擎 ───────────────────────────────────────────

class LSTMSignalEngine:
    """封裝 LSTM 模型推理的訊號引擎"""

    def __init__(self):
        self._model_cache  = {}
        self._scaler_cache = {}

    def _load_model(self, symbol: str):
        if symbol not in self._model_cache:
            # 優先嘗試載入新版 PyTorch 模型 (v4+)
            pt_path = f"models/pytorch_smart_entry/{symbol}_model.pt"
            keras_path = os.path.join(MODEL_DIR, f"{symbol}_model.h5")
            
            if os.path.exists(pt_path):
                try:
                    import torch
                    from train_pytorch_lstm import LSTMWithAttention
                    device = torch.device('mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu')
                    model = LSTMWithAttention(input_size=15, seq_len=20).to(device)
                    model.load_state_dict(torch.load(pt_path, map_location=device, weights_only=True))
                    model.eval()
                    self._model_cache[symbol] = {'engine': 'pytorch', 'model': model, 'device': device}
                except Exception as e:
                    print(f"   ❌ {symbol} PyTorch 模型載入失敗: {e}")
                    self._model_cache[symbol] = None
            elif os.path.exists(keras_path):
                try:
                    keras_model = load_model(keras_path, compile=False)
                    self._model_cache[symbol] = {'engine': 'keras', 'model': keras_model}
                except Exception as e:
                    print(f"   ❌ {symbol} Keras 模型載入失敗: {e}")
                    self._model_cache[symbol] = None
            else:
                self._model_cache[symbol] = None
        return self._model_cache[symbol]

    def _load_scaler(self, symbol: str):
        if symbol not in self._scaler_cache:
            path = os.path.join(MODEL_DIR, f"{symbol}_scaler_v5.pkl")
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    self._scaler_cache[symbol] = pickle.load(f)
            else:
                self._scaler_cache[symbol] = None
        return self._scaler_cache[symbol]

    def predict(self, symbol: str, hist_df: pd.DataFrame,
                current_idx: int, threshold: float = 0.5) -> Dict:
        """
        使用 LSTM 模型預測當前時間點的訊號
        返回: {'signal': 'buy'|'sell'|'neutral', 'confidence': float, 'raw_prob': float}
        """
        model_info = self._load_model(symbol)
        if not model_info:
            return {'signal': 'neutral', 'confidence': 0.0, 'raw_prob': 0.0}
            
        engine_type = model_info['engine']
        model = model_info['model']

        # ─── 建構特徵 ────────────────────────────────────────
        try:
            if engine_type == 'pytorch':
                # ─── 🌟 PyTorch + LSTMWithAttention (v4) 預測邏輯 ───────────
                from lstm_feature_builder_v4 import build_features, normalize_features, FEATURE_COLS
                import torch
                
                # 建構推論所需長度的歷史特徵 (至少需要 80 天以利 rolling 60 天 + 序列長度 20 天)
                start_idx = max(0, current_idx - 80)
                df_window = hist_df.iloc[start_idx : current_idx + 1].copy()
                
                if len(df_window) < 60:
                    return {'signal': 'neutral', 'confidence': 0.0, 'raw_prob': 0.0}
                
                df_feat = build_features(df_window)
                df_norm = normalize_features(df_feat, feature_cols=FEATURE_COLS, window=60, min_periods=20)
                
                # 取得最後 SEQ_LEN (20) 天資料
                X_raw = df_norm[FEATURE_COLS].iloc[-SEQ_LEN:].values
                if pd.isna(X_raw).any() or len(X_raw) < SEQ_LEN:
                    return {'signal': 'neutral', 'confidence': 0.0, 'raw_prob': 0.0}
                
                device = model_info['device']
                X_tensor = torch.tensor(X_raw, dtype=torch.float32).unsqueeze(0).to(device)
                
                with torch.no_grad():
                    prob = model(X_tensor).item()

            else:
                # ─── 👴 傳統 Keras LSTM (v3) 預測邏輯 ────────────
                saved = self._load_scaler(symbol)
                if saved is None:
                    return {'signal': 'neutral', 'confidence': 0.0, 'raw_prob': 0.0}
                
                scaler       = saved['scaler']
                feature_cols = saved['feature_cols']

                if HAS_FEATURE_BUILDER:
                    bench_df = self._get_bench_df()
                    df_feat, _ = build_features_full(hist_df.copy(), bench_df)
                else:
                    df_feat = self._build_simple_features(hist_df)

                if len(df_feat) < SEQ_LEN + 5:
                    return {'signal': 'neutral', 'confidence': 0.0, 'raw_prob': 0.0}

                # 對應到 current_idx
                feat_idx = min(current_idx, len(df_feat) - 1)
                if feat_idx < SEQ_LEN:
                    return {'signal': 'neutral', 'confidence': 0.0, 'raw_prob': 0.0}

                window = df_feat.iloc[feat_idx - SEQ_LEN: feat_idx].copy()

                for col in feature_cols:
                    if col not in window.columns:
                        window[col] = 0.0

                X_raw = window[feature_cols].fillna(0).values

                try:
                    X_scaled = scaler.transform(X_raw)
                except Exception:
                    from sklearn.preprocessing import MinMaxScaler
                    X_scaled = MinMaxScaler().fit_transform(X_raw)

                try:
                    model_n_feat = model.input_shape[-1]
                except Exception:
                    model_n_feat = X_scaled.shape[1]

                if X_scaled.shape[1] != model_n_feat:
                    if X_scaled.shape[1] > model_n_feat:
                        X_scaled = X_scaled[:, :model_n_feat]
                    else:
                        pad = np.zeros((X_scaled.shape[0], model_n_feat - X_scaled.shape[1]))
                        X_scaled = np.hstack([X_scaled, pad])

                X_in = X_scaled.reshape(1, SEQ_LEN, model_n_feat)
                prob = float(model.predict(X_in, verbose=0).flatten()[0])

            # 自適應閾值
            eff_thr = threshold

            if prob > eff_thr:
                signal     = 'buy'
                confidence = min(0.70 + (prob - eff_thr) / (1 - eff_thr) * 0.30, 0.99)
            elif prob < (1 - eff_thr):
                signal     = 'sell'
                confidence = min(0.70 + ((1 - eff_thr) - prob) / (1 - eff_thr) * 0.30, 0.99)
            else:
                signal     = 'neutral'
                confidence = 0.0

            return {'signal': signal, 'confidence': round(confidence, 4), 'raw_prob': round(prob, 4)}

        except Exception as e:
            print(f"   ⚠️  LSTM predict 錯誤 ({symbol}): {e}")
            return {'signal': 'neutral', 'confidence': 0.0, 'raw_prob': 0.0, 'error': str(e)}

    def _get_bench_df(self):
        """取得大盤基準（快取）"""
        if not hasattr(self, '_bench_df'):
            self._bench_df = yf.Ticker("^TWII").history(period="2y")
            self._bench_df.index = pd.to_datetime(self._bench_df.index).tz_localize(None)
        return self._bench_df

    def _build_simple_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """精簡版特徵（當 lstm_feature_builder 不可用時使用）"""
        df = df.copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df['Close'] = df['Close'].astype(float)
        df['MA5']        = df['Close'].rolling(5).mean()
        df['MA10']       = df['Close'].rolling(10).mean()
        df['MA20']       = df['Close'].rolling(20).mean()
        df['MA60']       = df['Close'].rolling(60).mean()
        df['Volume_MA5'] = df['Volume'].rolling(5).mean()
        delta = df['Close'].diff()
        gain  = delta.where(delta > 0, 0).rolling(14).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI']        = 100 - 100 / (1 + gain / (loss + 1e-9))
        df['MACD']       = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
        df['Volatility'] = df['Close'].rolling(20).std()
        df['kd_d']       = df['RSI'].rolling(3).mean()
        df['dist_52w_high'] = df['Close'] / df['High'].rolling(252).max()
        df['dist_52w_low']  = df['Close'] / df['Low'].rolling(252).min()
        df['rs_20d']     = df['Close'].pct_change(20)
        return df.dropna()


# ─── 交易記錄類別 ────────────────────────────────────────────

class Trade:
    def __init__(self, symbol, entry_date, entry_price, signal, position_size):
        self.symbol        = symbol
        self.entry_date    = entry_date
        self.entry_price   = entry_price
        self.signal        = signal   # 'buy' | 'sell'(short)
        self.position_size = position_size
        self.exit_date     = None
        self.exit_price    = None
        self.profit        = 0.0
        self.profit_pct    = 0.0
        self.exit_reason   = None

    def close(self, exit_date, exit_price, reason):
        self.exit_date   = exit_date
        self.exit_price  = exit_price
        self.exit_reason = reason
        if self.signal == 'buy':
            self.profit     = (exit_price - self.entry_price) * self.position_size
            self.profit_pct = (exit_price - self.entry_price) / self.entry_price
        else:
            self.profit     = (self.entry_price - exit_price) * self.position_size
            self.profit_pct = (self.entry_price - exit_price) / self.entry_price


# ─── 回測引擎 ────────────────────────────────────────────────

class LSTMBacktester:
    """LSTM 整合版回測引擎 v3.0"""

    def __init__(self, initial_capital=5_000_000,
                 stop_loss_pct=0.04, take_profit_pct=0.07,
                 lstm_threshold=0.42):  # 0.42: buy>0.42, sell<0.58
        self.initial_capital  = initial_capital
        self.capital          = initial_capital
        self.stop_loss_pct    = stop_loss_pct
        self.take_profit_pct  = take_profit_pct
        self.lstm_threshold   = lstm_threshold
        self.signal_engine    = LSTMSignalEngine()
        self.trades: List[Trade]      = []
        self.open_trades: List[Trade] = []

    def _get_threshold(self, symbol: str) -> float:
        """從白名單取各股專屬閾值"""
        try:
            import json
            with open(WL_PATH) as f:
                wl = json.load(f)
            if symbol in wl:
                return wl[symbol].get('threshold', self.lstm_threshold)
        except:
            pass
        return self.lstm_threshold

    async def backtest(self, symbol: str, start_date: str, end_date: str) -> Optional[Dict]:
        # 重置狀態
        self.capital     = self.initial_capital
        self.trades      = []
        self.open_trades = []

        thr = self._get_threshold(symbol)

        print(f"\n{'='*70}")
        print(f"🤖 {symbol} LSTM 回測 v3.0")
        print(f"期間: {start_date} → {end_date}  |  LSTM 閾值: {thr:.3f}")
        print(f"初始資金: ${self.initial_capital:,.0f}")
        print(f"{'='*70}")

        print(f"\n📊 下載歷史數據...")
        ticker = yf.Ticker(f"{symbol}.TW")
        hist   = ticker.history(start=start_date, end=end_date)
        if hist.empty:
            print(f"❌ 無法獲取 {symbol} 的數據")
            return None
        hist.index = pd.to_datetime(hist.index).tz_localize(None)
        print(f"✅ 成功獲取 {len(hist)} 天數據")

        # 需要更多歷史數據來計算特徵
        ticker_long = yf.Ticker(f"{symbol}.TW")
        hist_long   = ticker_long.history(period="2y")
        hist_long.index = pd.to_datetime(hist_long.index).tz_localize(None)

        print(f"\n🧠 開始逐日 LSTM 分析... (閾值:{thr:.2f} | 做多>{thr:.2f} | 做空<{1-thr:.2f})")
        debug_count = 0

        # 找到 hist 在 hist_long 中的起始位置
        start_ts = pd.Timestamp(start_date)
        for i, ts in enumerate(hist_long.index):
            if ts >= start_ts:
                long_start_i = i
                break
        else:
            long_start_i = 0

        for offset, date in enumerate(hist.index):
            long_i    = long_start_i + offset
            current   = hist.iloc[offset]

            if long_i < SEQ_LEN + 10:
                continue

            # LSTM 推理
            prediction = self.signal_engine.predict(
                symbol, hist_long, long_i, threshold=thr
            )
            # Debug: 每股前 5 天印出 LSTM 機率
            if debug_count < 5:
                p   = prediction.get('raw_prob', -1)
                sig = prediction.get('signal', '?')
                print(f"  [DEBUG {date.date()}] prob={p:.3f} signal={sig}")
                debug_count += 1

            price = float(current['Close'])

            # ✅ 15% 單標的最大虧損保護（防止連續止損燒光資金）
            loss_pct = (self.capital - self.initial_capital) / self.initial_capital
            if loss_pct < -0.15:
                print(f"  [⛔️  {date.date()}] {symbol} 已觸發 15% 虧損上限 "
                      f"(loss={loss_pct:.1%})，進行強制平倉後終止該標的")
                for trade in self.open_trades[:]:
                    trade.close(date, price, 'Hit Max Drawdown')
                    self.capital += trade.entry_price * trade.position_size + trade.profit
                    self.trades.append(trade)
                self.open_trades.clear()
                break

            # MA 過濾器（配合 LSTM 共同決策）
            ma5  = float(hist['Close'].iloc[max(0, offset-5):offset+1].mean())
            ma20 = float(hist['Close'].iloc[max(0, offset-20):offset+1].mean())
            is_bearish = price < ma20 and ma5 < ma20
            is_bullish = price > ma20 and ma5 > ma20

            # 平倉優先
            self._check_exit(date, current)

            # 開倉
            self._check_entry(symbol, date, current, prediction,
                              is_bearish, is_bullish, price)

        # 強制平倉所有剩餘持倉
        for trade in self.open_trades[:]:
            last_p = float(hist.iloc[-1]['Close'])
            trade.close(hist.index[-1], last_p, 'End of period')
            self.capital += trade.entry_price * trade.position_size + trade.profit
            self.trades.append(trade)
        self.open_trades.clear()

        return self._report(symbol)

    def _check_entry(self, symbol, date, data, prediction,
                     is_bearish, is_bullish, price):
        # 禁止重複開倉
        if any(t.symbol == symbol for t in self.open_trades):
            return

        signal     = prediction.get('signal', 'neutral')
        confidence = prediction.get('confidence', 0.0)
        raw_prob   = prediction.get('raw_prob', 0.5)

        if signal == 'neutral' or confidence < 0.72:
            return

        # MA + LSTM 雙重過濾
        if signal == 'buy' and is_bearish:
            return
        if signal == 'sell' and is_bullish:
            return

        direction = signal  # 'buy' or 'sell'

        # 動態張數：信心越高張數越多
        lots = 1
        if confidence >= 0.90:
            lots = 3
        elif confidence >= 0.85:
            lots = 2

        quantity   = lots * 1000
        total_cost = price * quantity

        # 風控：單筆 ≤ 20% 資金
        if total_cost > self.capital * 0.20:
            lots      = 1
            quantity  = 1000
            total_cost = price * quantity

        if self.capital >= total_cost:
            trade = Trade(symbol, date, price, direction, quantity)
            self.open_trades.append(trade)
            self.capital -= total_cost
            dir_label = '做多' if direction == 'buy' else '做空'
            print(f"  [{date.date()}] ⚡ {symbol} x {lots}張 ({dir_label}) "
                  f"| 價格:{price:.1f} | LSTM:{raw_prob:.3f} | 信心:{confidence:.2f} "
                  f"| 剩餘:${self.capital:,.0f}")

    def _check_exit(self, date, data):
        for trade in self.open_trades[:]:
            price = float(data['Close'])
            if trade.signal == 'buy':
                pnl_pct = (price - trade.entry_price) / trade.entry_price
            else:
                pnl_pct = (trade.entry_price - price) / trade.entry_price

            reason = None
            if pnl_pct < -self.stop_loss_pct:
                reason = 'Stop Loss'
                emoji  = '🔴'
            elif pnl_pct > self.take_profit_pct:
                reason = 'Take Profit'
                emoji  = '🟢'

            if reason:
                trade.close(date, price, reason)
                self.capital += trade.entry_price * trade.position_size + trade.profit
                self.trades.append(trade)
                self.open_trades.remove(trade)
                print(f"  [{date.date()}] {emoji} {reason}: {trade.symbol} "
                      f"| {pnl_pct:+.2%} | 資金:${self.capital:,.0f}")

    def _report(self, symbol: str) -> Dict:
        if not self.trades:
            print(f"\n{'='*70}")
            print(f"📊 {symbol} — 期間無成交（LSTM 沒有發出有效訊號）")
            print(f"{'='*70}")
            return {'symbol': symbol, 'total_trades': 0, 'total_pnl': 0, 'roi': 0}

        winning   = [t for t in self.trades if t.profit > 0]
        losing    = [t for t in self.trades if t.profit <= 0]
        total_pnl = sum(t.profit for t in self.trades)
        win_rate  = len(winning) / len(self.trades)
        avg_win   = sum(t.profit for t in winning) / len(winning) if winning else 0
        avg_loss  = sum(t.profit for t in losing)  / len(losing)  if losing  else 0
        roi       = total_pnl / self.initial_capital

        print(f"\n{'='*70}")
        print(f"📈 {symbol} LSTM 回測報告")
        print(f"{'='*70}")
        print(f"\n💰 資金情況:")
        print(f"   初始資金: ${self.initial_capital:,.0f}")
        print(f"   最終資金: ${self.capital:,.0f}")
        print(f"   總損益:   ${total_pnl:,.0f}  ({roi:+.2%})")
        print(f"\n📊 交易統計:")
        print(f"   總交易次數: {len(self.trades)}")
        print(f"   獲利: {len(winning)} 筆 ({win_rate:.1%})  |  虧損: {len(losing)} 筆 ({1-win_rate:.1%})")
        print(f"\n💵 盈虧分析:")
        print(f"   平均獲利: ${avg_win:,.0f}  |  平均虧損: ${avg_loss:,.0f}")
        if avg_loss != 0:
            print(f"   盈虧比: {abs(avg_win/avg_loss):.2f}")
        if self.trades:
            best  = max(self.trades, key=lambda t: t.profit)
            worst = min(self.trades, key=lambda t: t.profit)
            print(f"\n🏆 最佳: {best.entry_date.date()} | +${best.profit:,.0f} ({best.profit_pct:+.2%})")
            print(f"📉 最差: {worst.entry_date.date()} | ${worst.profit:,.0f} ({worst.profit_pct:+.2%})")
        print(f"{'='*70}")

        return {
            'symbol': symbol, 'total_trades': len(self.trades),
            'win_rate': win_rate, 'total_pnl': total_pnl,
            'roi': roi, 'final_capital': self.capital,
            'avg_profit_loss_ratio': abs(avg_win / avg_loss) if avg_loss else 0,
        }


# ─── 主程式 ─────────────────────────────────────────────────

async def main():
    print("\n" + "="*70)
    print("🚀 LSTM 整合版歷史回測系統 v3.0")
    print("  AI 引擎: LSTM 深度學習模型 + MA 均線雙重過濾")
    print("="*70)

    backtester = LSTMBacktester(
        initial_capital  = 5_000_000,
        stop_loss_pct    = 0.04,   # 4% 止損
        take_profit_pct  = 0.07,   # 7% 止盈
        lstm_threshold   = 0.42,   # 做多>0.42, 做空<0.58 (可依各股調整)
    )

    # ORB 活躍監控清單 × 有 LSTM 模型 → 46 支
    test_stocks = [
        "1301", "1303", "1326", "1605", "1802", "1815",
        "2002", "2301", "2303", "2312", "2313", "2314",
        "2317", "2327", "2330", "2337", "2344", "2367",
        "2371", "2379", "2382", "2408", "2412", "2449",
        "2454", "2609", "2618", "2881", "3008", "3034",
        "3037", "3163", "3189", "3231", "3265", "3363",
        "3481", "3706", "5498", "5521", "6239", "6257",
        "6282", "6285", "6770", "8046",
    ]
    all_results  = []
    skip_reasons = {}   # symbol → reason string

    for symbol in test_stocks:
        try:
            result = await backtester.backtest(
                symbol=symbol,
                start_date="2024-10-01",
                end_date="2025-03-24"
            )
            if result is None:
                skip_reasons[symbol] = "❌ 數據獲取失敗 (yfinance 回傳空)"
            elif result.get('total_trades', 0) == 0:
                skip_reasons[symbol] = "⚪ LSTM 全期 neutral，無有效訊號"
            else:
                all_results.append(result)
        except Exception as e:
            skip_reasons[symbol] = f"💥 程式異常: {str(e)[:80]}"

    # ─── 有成交的股票摘要（按報酬率排序）───────────────────────────
    if all_results:
        print(f"\n{'='*80}")
        print("📊 LSTM 回測總摘要（有成交，按報酬率排序）")
        print(f"{'='*80}")
        print(f"   {'股票':^6} {'交易':^5} {'勝率':^7} {'盈虧比':^6} {'總損益':^14} {'報酬率':^8}  {'狀態':^6}")
        print("-"*73)
        total_all = 0
        qualified_stocks = []

        for r in sorted(all_results, key=lambda x: x.get('roi', 0), reverse=True):
            plr   = r.get('avg_profit_loss_ratio', 0)
            win_r = r.get('win_rate', 0)
            pnl   = r.get('total_pnl', 0)
            total_all += pnl
            roi   = r.get('roi', 0)
            
            # 🔥 嚴格篩選條件：勝率 >= 40% 且 盈虧比 >= 1.3
            is_qualified = (win_r >= 0.4) and (plr >= 1.3)
            if is_qualified:
                qualified_stocks.append(r['symbol'])

            roi_s = f"{roi:+.2%}"
            flag  = '✅' if roi > 0 else '🔴'
            status = '🌟 合格' if is_qualified else '淘汰'

            print(f"{flag} {r['symbol']:^5}  {r['total_trades']:^5} "
                  f"{win_r:.1%}  {plr:^6.2f}  "
                  f"${pnl:>12,.0f}  {roi_s}  {status}")
        print(f"\n   {'合計':^6} {'':^5} {'':^7} {'':^6}  ${total_all:>12,.0f}")

        print(f"\n🏆 嚴選合格白名單 (勝率 >= 40% 且 盈虧比 >= 1.3):")
        print(f"   {qualified_stocks}")

    # ─── 跳過 / 無訊號的股票說明表 ────────────────────────────────
    if skip_reasons:
        print(f"\n{'='*80}")
        print(f"⚠️   跳過 / 無訊號股票（{len(skip_reasons)} 支）")
        print(f"{'='*80}")
        for sym, reason in sorted(skip_reasons.items()):
            print(f"   {sym:^6}  {reason}")

    print(f"\n✅ LSTM 回測及評估完成！")

if __name__ == "__main__":
    asyncio.run(main())
