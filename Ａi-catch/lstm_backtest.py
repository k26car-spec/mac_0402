"""
LSTM 回測驗證系統 v2
====================
功能：
  - 支援 --threshold auto（從 lstm_whitelist.json 自動讀取各股閾值）
  - 支援 v5 34 特徵（lstm_feature_builder）
  - 向下相容舊版 9 特徵模型
  - 回測期間：1m / 3m / 6m / 1y
  - 輸出：準確率、精確率、召回率、F1、平均超額報酬

執行：
    python3 lstm_backtest.py                          # 白名單 + auto 閾值 + 3m
    python3 lstm_backtest.py --threshold auto --period 3m
    python3 lstm_backtest.py --threshold 0.5 --period 6m --stocks all
    python3 lstm_backtest.py --stocks 2337,2344
"""

import sys, os, json, pickle, warnings, argparse
import numpy as np
import pandas as pd
import yfinance as yf
import patch_yfinance  # 🆕 導入修補模組
from datetime import datetime
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import MinMaxScaler
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tensorflow as tf
from tensorflow.keras.models import load_model

MODEL_DIR    = "models/lstm_smart_entry"
WL_PATH      = "lstm_whitelist.json"
SEQ_LEN_NEW  = 20   # v5 序列長度
SEQ_LEN_OLD  = 60   # 舊版序列長度

print("=" * 65)
print("📊 LSTM 回測驗證系統 v2")
print("=" * 65)


# ─── 工具函數 ─────────────────────────────────────────────

def load_whitelist() -> dict:
    """載入白名單，返回 {symbol: {threshold, precision, recall, ...}}"""
    try:
        with open(WL_PATH) as f:
            wl = json.load(f)
        return {k: v for k, v in wl.items() if not k.startswith('_')}
    except:
        return {}


def load_model_safe(symbol: str):
    """安全載入模型"""
    path = os.path.join(MODEL_DIR, f"{symbol}_model.h5")
    if not os.path.exists(path):
        return None
    try:
        return load_model(path, compile=False)
    except Exception as e:
        print(f"   ❌ 模型載入失敗 {symbol}: {e}")
        return None


def strip_tz(idx):
    """移除 DatetimeIndex 的時區"""
    if hasattr(idx, 'tz') and idx.tz is not None:
        return idx.tz_localize(None)
    return idx


# ─── v5 回測（使用 lstm_feature_builder）────────────────

def backtest_v5(symbol: str, period: str, threshold: float,
                df_bench: pd.DataFrame) -> dict | None:
    """v5/v6 統一回測（自動偵測版本，支援 v2=34特徵 / v3=60特徵）"""
    try:
        period_map = {'1m': '4mo', '3m': '8mo', '6m': '14mo', '1y': '2y'}
        hist_period = period_map.get(period, '8mo')

        df = yf.Ticker(symbol).history(period=hist_period)
        if df.empty or len(df) < 100:
            return None

        # 載入 scaler + feature_cols
        scaler_path = os.path.join(MODEL_DIR, f"{symbol}_scaler_v5.pkl")
        if not os.path.exists(scaler_path):
            return None
        with open(scaler_path, 'rb') as f:
            saved = pickle.load(f)
        scaler       = saved['scaler']
        feature_cols = saved['feature_cols']    # RF 篩選後的特徵清單
        scaler_dim   = getattr(scaler, 'n_features_in_', len(feature_cols))
        model_ver    = saved.get('version', 'v5')    # 'v5' or 'v6'

        # 載入模型
        model = load_model_safe(symbol)
        if model is None:
            return None

        # ─── 依版本選擇特徵建構器 ───────────────────────────
        if model_ver == 'v6':
            # v6 模型：使用 v3 建構器（60個特徵）
            from lstm_feature_builder_v3 import build_features_v3, ALL_FEATURE_COLS_V3 as ALL_COLS_V3
            df_feat, all_cols = build_features_v3(df, df_bench)
            ALL_FEATURE_COLS  = ALL_COLS_V3
        else:
            # v5 模型（或更舊）：使用 v2 建構器（34個特徵）
            from lstm_feature_builder import build_features_full, ALL_FEATURE_COLS
            df_feat, all_cols = build_features_full(df, df_bench)

        if len(df_feat) < SEQ_LEN_NEW + 10:
            return None

        # 計算 alpha 標籤
        bench_s = df_bench['Close'].copy()
        bench_s.index = strip_tz(pd.to_datetime(bench_s.index))
        stock_s = df['Close'].copy()
        stock_s.index = strip_tz(pd.to_datetime(stock_s.index))
        bench_a = bench_s.reindex(df_feat.index, method='ffill')
        stock_a = stock_s.reindex(df_feat.index, method='ffill')
        stock_ret = stock_a.pct_change(5).shift(-5)
        bench_ret = bench_a.pct_change(5).shift(-5)
        alpha = (stock_ret - bench_ret) * 100

        df_feat = df_feat.copy()
        df_feat['alpha'] = alpha
        df_feat = df_feat.dropna(subset=['alpha'])

        if len(df_feat) < SEQ_LEN_NEW + 10:
            return None

        # ─── 自動偵測 scaler 維度，決定如何 transform ───
        # Case A：新模型（scaler 已只 fit feature_cols 個特徵）→ 直接傳 feature_cols
        # Case B：舊模型（scaler fit 全 34 欄，feature_cols 是 RF 篩選的 12 個）→
        #         先傳全部欄 transform，再取對應欄的 index

        if scaler_dim == len(feature_cols):
            # Case A：維度一致，直接 transform
            X_raw = df_feat[feature_cols].fillna(0).values
            X_scaled = scaler.transform(X_raw)
        else:
            # Case B：舊模型，scaler 是 34 維，需先取全欄 transform 再切片
            # 確認 ALL_FEATURE_COLS 可用
            full_cols = [c for c in ALL_FEATURE_COLS if c in df_feat.columns]
            if scaler_dim != len(full_cols):
                # 若還是對不上，就用 fit_transform 重新標準化（僅用 12 欄）
                fallback_scaler = MinMaxScaler()
                X_raw = df_feat[feature_cols].fillna(0).values
                X_scaled = fallback_scaler.fit_transform(X_raw)
                print(f"   ℹ️  {symbol}: 使用 fallback scaler（dim mismatch: "
                      f"scaler={scaler_dim} vs full_cols={len(full_cols)} vs feat={len(feature_cols)}）")
            else:
                X_full = df_feat[full_cols].fillna(0).values
                X_transformed = scaler.transform(X_full)   # (N, 34)
                # 取出 feature_cols 在 full_cols 中的 index
                col_idx = [full_cols.index(c) for c in feature_cols if c in full_cols]
                X_scaled = X_transformed[:, col_idx]       # (N, 12)
                print(f"   ℹ️  {symbol}: 舊模型相容模式（scaler={scaler_dim}→切出{len(col_idx)}欄）")

        X, y = [], []
        for i in range(len(df_feat) - SEQ_LEN_NEW):
            X.append(X_scaled[i:i + SEQ_LEN_NEW])
            y.append(1 if df_feat['alpha'].iloc[i + SEQ_LEN_NEW] > 0 else 0)

        X, y = np.array(X), np.array(y)

        # 只取最近回測期對應的樣本
        period_days = {'1m': 20, '3m': 60, '6m': 120, '1y': 252}
        n = min(period_days.get(period, 60), len(X))
        X_test, y_test = X[-n:], y[-n:]

        preds = model.predict(X_test, verbose=0).flatten()

        # ─── 自適應閾值：若模型輸出集中在低值（舊模型退化），自動調整 ───
        n_above = (preds > threshold).sum()
        threshold_mode = 'fixed'
        effective_thr = threshold
        if n_above == 0:
            # 所有預測值都低於閾值 → 用 60th 分位數做自適應閾值
            adaptive_thr = float(np.percentile(preds, 60))
            print(f"   ⚡ {symbol}: 固定閾值 {threshold:.2f} 無效（preds max={preds.max():.3f}），"
                  f"改用自適應閾值={adaptive_thr:.3f}")
            effective_thr = adaptive_thr
            threshold_mode = 'adaptive'

        pred_b = (preds > effective_thr).astype(int)

        # 計算平均超額報酬
        alpha_vals = df_feat['alpha'].values[-n:]
        traded_alpha = alpha_vals[pred_b == 1]
        avg_alpha = float(np.mean(traded_alpha)) if len(traded_alpha) > 0 else 0.0

        return {
            'symbol':         symbol,
            'version':        'v5',
            'threshold':      effective_thr,
            'threshold_mode': threshold_mode,
            'samples':        len(y_test),
            'accuracy':     float(accuracy_score(y_test, pred_b)),
            'precision':    float(precision_score(y_test, pred_b, zero_division=0)),
            'recall':       float(recall_score(y_test, pred_b, zero_division=0)),
            'f1':           float(f1_score(y_test, pred_b, zero_division=0)),
            'pos_preds':    int(pred_b.sum()),
            'actual_pos':   int(y_test.sum()),
            'avg_alpha':    round(avg_alpha, 3),
        }

    except Exception as e:
        print(f"   ⚠️  v5 回測失敗 {symbol}: {e}")
        return None


# ─── 舊版 v4 回測（9 特徵）──────────────────────────────

def _build_features_old(df: pd.DataFrame) -> pd.DataFrame:
    """舊版 9 特徵計算"""
    df = df.copy()
    df['MA5']        = df['Close'].rolling(5).mean()
    df['MA10']       = df['Close'].rolling(10).mean()
    df['MA20']       = df['Close'].rolling(20).mean()
    df['Volume_MA5'] = df['Volume'].rolling(5).mean()
    delta = df['Close'].diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI']        = 100 - 100 / (1 + gain / (loss + 1e-9))
    df['Volatility'] = df['Close'].rolling(20).std()
    df['MACD']       = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
    return df


def backtest_v4(symbol: str, period: str, threshold: float,
                df_bench: pd.DataFrame) -> dict | None:
    """舊版 v4 回測（9 特徵）"""
    try:
        period_map = {'1m': '4mo', '3m': '8mo', '6m': '14mo', '1y': '2y'}
        df = yf.Ticker(symbol).history(period=period_map.get(period, '8mo'))
        if df.empty or len(df) < SEQ_LEN_OLD + 20:
            return None

        model = load_model_safe(symbol)
        if model is None:
            return None

        df = _build_features_old(df)
        feat_cols = ['Close', 'Volume', 'MA5', 'MA10', 'MA20',
                     'Volume_MA5', 'RSI', 'Volatility', 'MACD']

        # 大盤對齊
        bench_s = df_bench['Close'].copy()
        bench_s.index = strip_tz(pd.to_datetime(bench_s.index))
        stock_s = df['Close'].copy()
        stock_s.index = strip_tz(pd.to_datetime(stock_s.index))
        df.index = strip_tz(pd.to_datetime(df.index))
        bench_a = bench_s.reindex(df.index, method='ffill')

        # 標籤（未來 5 天超額報酬）
        stock_ret = stock_s.pct_change(5).shift(-5)
        bench_ret = bench_a.pct_change(5).shift(-5)
        df['alpha'] = (stock_ret - bench_ret) * 100
        df = df.dropna()

        scaler = MinMaxScaler()
        df[feat_cols] = scaler.fit_transform(df[feat_cols].fillna(0))

        X, y, alpha_vals = [], [], []
        for i in range(len(df) - SEQ_LEN_OLD):
            X.append(df[feat_cols].iloc[i:i + SEQ_LEN_OLD].values)
            y.append(1 if df['alpha'].iloc[i + SEQ_LEN_OLD] > 0 else 0)
            alpha_vals.append(df['alpha'].iloc[i + SEQ_LEN_OLD])

        X, y, alpha_vals = np.array(X), np.array(y), np.array(alpha_vals)

        period_days = {'1m': 20, '3m': 60, '6m': 120, '1y': 252}
        n = min(period_days.get(period, 60), len(X))
        X_t, y_t, alpha_t = X[-n:], y[-n:], alpha_vals[-n:]

        preds = model.predict(X_t, verbose=0).flatten()
        pred_b = (preds > threshold).astype(int)
        traded = alpha_t[pred_b == 1]
        avg_alpha = float(np.mean(traded)) if len(traded) > 0 else 0.0

        return {
            'symbol':    symbol,
            'version':   'v4',
            'threshold': threshold,
            'samples':   len(y_t),
            'accuracy':  float(accuracy_score(y_t, pred_b)),
            'precision': float(precision_score(y_t, pred_b, zero_division=0)),
            'recall':    float(recall_score(y_t, pred_b, zero_division=0)),
            'f1':        float(f1_score(y_t, pred_b, zero_division=0)),
            'pos_preds': int(pred_b.sum()),
            'actual_pos': int(y_t.sum()),
            'avg_alpha': round(avg_alpha, 3),
        }

    except Exception as e:
        print(f"   ⚠️  v4 回測失敗 {symbol}: {e}")
        return None


# ─── 主回測函數 ──────────────────────────────────────────

def run_backtest(stock_list: list, period: str,
                 threshold_arg: str, whitelist: dict) -> list:
    """
    執行回測

    threshold_arg: 'auto' 表示從白名單讀取，否則轉 float
    """
    use_auto = (threshold_arg == 'auto')
    fixed_thr = 0.5 if use_auto else float(threshold_arg)

    print(f"\n🔍 開始回測...")
    print(f"   股票: {len(stock_list)} 支  期間: {period}  閾值: {'各股自動' if use_auto else fixed_thr}")

    # 預載大盤
    bench_df = yf.Ticker("^TWII").history(period="3y")
    bench_df.index = strip_tz(pd.to_datetime(bench_df.index))

    results = []
    for i, sym in enumerate(stock_list, 1):
        print(f"\n  [{i}/{len(stock_list)}] {sym}", end="  ", flush=True)

        # 決定閾值
        if use_auto and sym in whitelist:
            thr = whitelist[sym].get('threshold', 0.5)
        else:
            thr = fixed_thr

        # 優先 v5，退回 v4
        scaler_v5 = os.path.join(MODEL_DIR, f"{sym}_scaler_v5.pkl")
        if os.path.exists(scaler_v5):
            r = backtest_v5(sym, period, thr, bench_df)
        else:
            r = backtest_v4(sym, period, thr, bench_df)

        if r:
            results.append(r)
            in_wl = '✅白名單' if sym in whitelist else '  '
            print(f"P={r['precision']*100:.1f}%  R={r['recall']*100:.1f}%  "
                  f"F1={r['f1']*100:.1f}%  alpha={r['avg_alpha']:+.2f}%  "
                  f"thr={thr:.3f}  {in_wl}")
        else:
            print("❌ 回測失敗")

    return results


# ─── 摘要分析 ───────────────────────────────────────────

def print_summary(results: list, whitelist: dict):
    if not results:
        print("\n❌ 無任何回測結果")
        return

    wl_stocks = [r for r in results if r['symbol'] in whitelist]
    other     = [r for r in results if r['symbol'] not in whitelist]

    print(f"\n\n{'═'*65}")
    print("📊 回測摘要")
    print(f"{'═'*65}")

    def _print_group(group, title):
        if not group: return
        avg_p   = np.mean([r['precision'] for r in group]) * 100
        avg_r   = np.mean([r['recall']    for r in group]) * 100
        avg_f1  = np.mean([r['f1']        for r in group]) * 100
        avg_a   = np.mean([r['avg_alpha'] for r in group])
        pos_pct = np.mean([r['pos_preds'] / max(r['samples'], 1) for r in group]) * 100
        print(f"\n{title} ({len(group)} 支):")
        print(f"  精確率 avg: {avg_p:.1f}%  召回率 avg: {avg_r:.1f}%  F1 avg: {avg_f1:.1f}%")
        print(f"  超額報酬 avg: {avg_a:+.2f}%  買進比例 avg: {pos_pct:.1f}%")
        print()
        for r in sorted(group, key=lambda x: -x['precision']):
            sym  = r['symbol']
            flag = '⭐' if r['precision'] >= 0.65 else ('✅' if r['precision'] >= 0.55 else '⚠️')
            print(f"  {flag} {sym} [{r['version']}]  "
                  f"P={r['precision']*100:.1f}%  R={r['recall']*100:.1f}%  "
                  f"F1={r['f1']*100:.1f}%  alpha={r['avg_alpha']:+.2f}%  "
                  f"+={r['pos_preds']}/{r['samples']}  thr={r['threshold']:.3f}")

    _print_group(wl_stocks, "✅ 白名單股票")
    _print_group(other,     "📋 其他股票")

    print(f"\n{'─'*65}")
    print("💡 大盤超額報酬說明：alpha > 0 = 跑贏大盤，< 0 = 跑輸大盤")
    print(f"{'═'*65}")

    return {
        'total': len(results),
        'whitelist': len(wl_stocks),
        'avg_precision': float(np.mean([r['precision'] for r in results])),
        'avg_alpha': float(np.mean([r['avg_alpha'] for r in results])),
    }


def convert_types(obj):
    """遞迴轉換 numpy 型別"""
    if isinstance(obj, dict):
        return {k: convert_types(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_types(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    return obj


# ─── 主程式 ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='LSTM 回測驗證 v2')
    parser.add_argument('--period', type=str, default='3m',
                        help='回測期間: 1m / 3m / 6m / 1y（預設 3m）')
    parser.add_argument('--stocks', type=str, default='whitelist',
                        help='股票清單: whitelist / all / 逗號分隔代碼（預設 whitelist）')
    parser.add_argument('--threshold', type=str, default='auto',
                        help='閾值: auto（白名單自動）/ 0.5（固定值）')
    args = parser.parse_args()

    print(f"\n⚙️  參數: period={args.period}  threshold={args.threshold}  stocks={args.stocks}")

    whitelist = load_whitelist()
    print(f"📋 白名單: {list(whitelist.keys())}")

    # 決定股票清單
    if args.stocks == 'whitelist':
        if not whitelist:
            print("⚠️  白名單為空，請先執行 python3 train_lstm_v5.py")
            return
        stock_list = sorted(whitelist.keys())
    elif args.stocks == 'all':
        h5s = [f.replace('_model.h5', '')
               for f in os.listdir(MODEL_DIR) if f.endswith('_model.h5')]
        stock_list = sorted(h5s)
    else:
        stock_list = [s.strip() for s in args.stocks.split(',')]

    print(f"📌 回測股票: {stock_list}\n")

    # 執行回測
    results = run_backtest(stock_list, args.period, args.threshold, whitelist)

    # 摘要
    summary = print_summary(results, whitelist)

    # 儲存
    if results:
        out = {
            'backtest_date': datetime.now().isoformat(),
            'period':        args.period,
            'threshold':     args.threshold,
            'summary':       summary,
            'results':       results
        }
        fname = f"lstm_backtest_{args.period}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(convert_types(out), f, indent=2, ensure_ascii=False)
        print(f"\n📄 報告已儲存: {fname}")

    print(f"\n✅ 回測完成！")


if __name__ == '__main__':
    main()
