"""
LSTM 強化特徵建構器 v2
======================
整合系統所有可用數據源，為 LSTM 提供更豐富的輸入特徵

特徵分類（共 35 個）：
  A. 技術指標    (9)  ← 原本的
  B. 量價關係    (8)  ← 新增（量增價漲、量縮價跌等）
  C. VWAP 系列  (4)  ← 整合 vwap_tracker
  D. KD / 動能  (5)  ← 整合 feature_engineering
  E. 相對強弱    (5)  ← vs 大盤、vs 同類股
  F. 支撐壓力    (4)  ← 整合 support_resistance_analyzer

使用方式：
    from lstm_feature_builder import build_features_full
    X, feature_names = build_features_full(symbol, df_ohlcv, df_twii)
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import patch_yfinance  # 🆕 導入修補模組
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')


# ─── A. 技術指標（原有 9 個）────────────────────────────
TECH_COLS = ['Close', 'Volume', 'MA5', 'MA10', 'MA20',
             'Volume_MA5', 'RSI', 'Volatility', 'MACD']


def _build_tech(df: pd.DataFrame) -> pd.DataFrame:
    """計算基礎技術指標"""
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
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD']       = ema12 - ema26
    return df


# ─── B. 量價關係（8 個新特徵）────────────────────────────
def _build_volume_price(df: pd.DataFrame) -> pd.DataFrame:
    """
    量價關係特徵（最重要的交易信號之一）

    price_up_vol_up   (1=是)  價漲量增 → 健康上漲
    price_up_vol_down (1=是)  價漲量縮 → 可能假突破
    price_down_vol_up (1=是)  價跌量增 → 恐慌出貨
    price_down_vol_dn (1=是)  價跌量縮 → 縮量整理
    vol_ratio_5       float   當日量 / 5日均量（量能倍數）
    vol_ratio_20      float   當日量 / 20日均量
    vol_trend_3d      float   3日量能趨勢（正=放量, 負=縮量）
    price_vol_score   float   綜合量價健康分數 (-3 ~ +3)
    """
    df = df.copy()

    price_chg  = df['Close'].pct_change()
    vol_chg    = df['Volume'].pct_change()
    vol_ma5    = df['Volume'].rolling(5).mean()
    vol_ma20   = df['Volume'].rolling(20).mean()

    df['price_up_vol_up']   = ((price_chg > 0) & (vol_chg > 0)).astype(int)
    df['price_up_vol_down'] = ((price_chg > 0) & (vol_chg < 0)).astype(int)
    df['price_dn_vol_up']   = ((price_chg < 0) & (vol_chg > 0)).astype(int)
    df['price_dn_vol_down'] = ((price_chg < 0) & (vol_chg < 0)).astype(int)

    # 量能倍數（相對均量）
    df['vol_ratio_5']  = df['Volume'] / (vol_ma5  + 1)
    df['vol_ratio_20'] = df['Volume'] / (vol_ma20 + 1)

    # 3日量能趨勢（線性迴歸斜率方向）
    vols = df['Volume'].rolling(3)
    df['vol_trend_3d'] = vols.apply(
        lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == 3 else 0,
        raw=True
    ) / (df['Volume'].rolling(3).mean() + 1)  # 標準化

    # 量價健康分數：量增價漲+3, 量增價跌-3, 量縮價漲+1, 量縮價跌-1
    def vp_score(row):
        pc = row['price_chg']; vc = row['vol_chg']
        if pd.isna(pc) or pd.isna(vc): return 0
        if pc > 0 and vc > 0.2:   return 3   # 爆量上漲
        if pc > 0 and vc > 0:     return 2   # 放量上漲
        if pc > 0 and vc < 0:     return 1   # 縮量上漲（弱）
        if pc < 0 and vc > 0.2:   return -3  # 爆量下跌（恐慌）
        if pc < 0 and vc > 0:     return -2  # 放量下跌
        if pc < 0 and vc < 0:     return -1  # 縮量下跌（止跌）
        return 0

    df['price_chg'] = price_chg
    df['vol_chg']   = vol_chg
    df['price_vol_score'] = df.apply(vp_score, axis=1)
    df = df.drop(columns=['price_chg', 'vol_chg'])

    return df


VOL_PRICE_COLS = ['price_up_vol_up', 'price_up_vol_down', 'price_dn_vol_up',
                  'price_dn_vol_down', 'vol_ratio_5', 'vol_ratio_20',
                  'vol_trend_3d', 'price_vol_score']


# ─── C. VWAP 系列（4 個特徵）────────────────────────────
def _build_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    VWAP 相關特徵（日內由 OHLCV 近似計算）

    日線上的 VWAP 近似 = 典型價格加權動態均線
    vwap_approx      float  VWAP 近似值
    vwap_deviation   float  現價距 VWAP 乖離率(%)
    above_vwap       int    (1=在 VWAP 上方)
    vwap_trend_5d    float  5日 VWAP 斜率 (正=上升趨勢)
    """
    df = df.copy()
    # 典型價格 × 成交量 / 成交量
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    df['vwap_approx'] = (typical * df['Volume']).rolling(5).sum() / (df['Volume'].rolling(5).sum() + 1)
    df['vwap_deviation'] = (df['Close'] - df['vwap_approx']) / (df['vwap_approx'] + 1e-9) * 100
    df['above_vwap']     = (df['Close'] > df['vwap_approx']).astype(int)
    # VWAP 5日趨勢
    df['vwap_trend_5d'] = df['vwap_approx'].pct_change(5) * 100
    return df


VWAP_COLS = ['vwap_deviation', 'above_vwap', 'vwap_trend_5d', 'vol_ratio_5']


# ─── D. KD 動能指標（5 個特徵）──────────────────────────
def _build_kd(df: pd.DataFrame, period: int = 9) -> pd.DataFrame:
    """
    KD 隨機指標 + 動能特徵

    kd_k             float  KD K 值
    kd_d             float  KD D 值
    kd_diff          float  K - D（黃金交叉 = 正, 死亡交叉 = 負）
    kd_overbought    int    K > 80
    kd_oversold      int    K < 20
    """
    df = df.copy()
    low_min  = df['Low'].rolling(period).min()
    high_max = df['High'].rolling(period).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min + 1e-9) * 100

    df['kd_k'] = rsv.ewm(com=2, adjust=False).mean()
    df['kd_d'] = df['kd_k'].ewm(com=2, adjust=False).mean()
    df['kd_diff']       = df['kd_k'] - df['kd_d']
    df['kd_overbought'] = (df['kd_k'] > 80).astype(int)
    df['kd_oversold']   = (df['kd_k'] < 20).astype(int)
    return df


KD_COLS = ['kd_k', 'kd_d', 'kd_diff', 'kd_overbought', 'kd_oversold']


# ─── E. 相對強弱（5 個特徵）────────────────────────────
def _build_relative_strength(df: pd.DataFrame, df_bench: pd.DataFrame) -> pd.DataFrame:
    """
    相對大盤強弱（Alpha 系列）

    rs_1d            float  個股 1日報酬 - 大盤 1日報酬
    rs_5d            float  個股 5日報酬 - 大盤 5日報酬
    rs_20d           float  個股 20日報酬 - 大盤 20日報酬
    outperform_5d    int    5日是否跑贏大盤（1=是）
    rs_trend         float  RS 趨勢（rs_5d 斜率方向）
    """
    df = df.copy()

    stock_ret1  = df['Close'].pct_change(1)
    stock_ret5  = df['Close'].pct_change(5)
    stock_ret20 = df['Close'].pct_change(20)

    # 對齊大盤
    bench = df_bench['Close'].reindex(df.index, method='ffill')
    bench_ret1  = bench.pct_change(1)
    bench_ret5  = bench.pct_change(5)
    bench_ret20 = bench.pct_change(20)

    df['rs_1d']         = (stock_ret1  - bench_ret1)  * 100
    df['rs_5d']         = (stock_ret5  - bench_ret5)  * 100
    df['rs_20d']        = (stock_ret20 - bench_ret20) * 100
    df['outperform_5d'] = (df['rs_5d'] > 0).astype(int)
    df['rs_trend']      = df['rs_5d'].diff(3)  # RS 是否在改善

    return df


RS_COLS = ['rs_1d', 'rs_5d', 'rs_20d', 'outperform_5d', 'rs_trend']


# ─── F. 支撐壓力距離（4 個特徵）────────────────────────
def _build_support_resistance(df: pd.DataFrame) -> pd.DataFrame:
    """
    支撐壓力距離（簡化計算）

    dist_to_52w_high    float  距 52 週高點距離(%)
    dist_to_52w_low     float  距 52 週低點距離(%)
    near_resistance     int    距近期高點 < 3% (0=遠, 1=近)
    near_support        int    距近期低點 < 3% (0=遠, 1=近)
    """
    df = df.copy()
    w52_high = df['High'].rolling(252, min_periods=60).max()
    w52_low  = df['Low'].rolling(252, min_periods=60).min()
    recent_high = df['High'].rolling(20).max()
    recent_low  = df['Low'].rolling(20).min()

    df['dist_52w_high']    = (df['Close'] / (w52_high + 1e-9) - 1) * 100  # 負值 = 距高點有距離
    df['dist_52w_low']     = (df['Close'] / (w52_low  + 1e-9) - 1) * 100  # 正值 = 比低點高多少
    df['near_resistance']  = (abs(df['Close'] / (recent_high + 1e-9) - 1) < 0.03).astype(int)
    df['near_support']     = (abs(df['Close'] / (recent_low  + 1e-9) - 1) < 0.03).astype(int)

    return df


SR_COLS = ['dist_52w_high', 'dist_52w_low', 'near_resistance', 'near_support']


# ─── 主要建構函數 ─────────────────────────────────────────
ALL_FEATURE_COLS = TECH_COLS + VOL_PRICE_COLS + VWAP_COLS + KD_COLS + RS_COLS + SR_COLS

# 去重（VWAP_COLS 裡的 vol_ratio_5 與 VOL_PRICE_COLS 重复）
ALL_FEATURE_COLS = list(dict.fromkeys(ALL_FEATURE_COLS))


def build_features_full(df_ohlcv: pd.DataFrame,
                        df_bench: pd.DataFrame = None) -> tuple[pd.DataFrame, list]:
    """
    完整特徵建構入口

    Args:
        df_ohlcv  : yfinance 格式的 OHLCV DataFrame（index=日期）
        df_bench  : 大盤指數 DataFrame（index=日期, 需有 'Close' 欄）
                    若為 None 則相對強弱特徵填 0

    Returns:
        (df_features, feature_cols)
        df_features : 含所有特徵的 DataFrame（已去除 NaN 行）
        feature_cols: 實際使用的特徵欄名稱清單
    """
    df = df_ohlcv.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)

    # A. 技術指標
    df = _build_tech(df)

    # B. 量價關係
    df = _build_volume_price(df)

    # C. VWAP
    df = _build_vwap(df)

    # D. KD
    df = _build_kd(df)

    # E. 相對強弱
    if df_bench is not None:
        bench = df_bench.copy()
        bench.index = pd.to_datetime(bench.index).tz_localize(None)
        df = _build_relative_strength(df, bench)
    else:
        for col in RS_COLS:
            df[col] = 0.0

    # F. 支撐壓力
    # 需要 High/Low 欄位
    if 'High' in df.columns and 'Low' in df.columns:
        df = _build_support_resistance(df)
    else:
        for col in SR_COLS:
            df[col] = 0.0

    # 取出有效欄位
    feature_cols = [c for c in ALL_FEATURE_COLS if c in df.columns]
    df_feat = df[feature_cols].copy()
    df_feat = df_feat.replace([np.inf, -np.inf], np.nan)
    df_feat = df_feat.dropna()

    return df_feat, feature_cols


# ── 標籤基準線設定 ──────────────────────────────────────────
def make_sequences_v2(
    df_ohlcv: pd.DataFrame,
    df_bench: pd.DataFrame,
    seq_len: int = 20,
    pred_days: int = 5,
    alpha_threshold: float = 0.005,   # 比率格式（0.005 = 跑贏大盤 0.5%）
):
    """
    建立 LSTM 訓練序列（使用完整特徵集）

    標籤定義（熊市強化版）：
      y = 1  當第 t+pred_days 天的超額報酬 >= alpha_threshold

      公式: alpha = stock_ret - bench_ret  【比率格式，非百分比】
      標籤: 1 當 alpha >= alpha_threshold，0 否則

      預設 alpha_threshold = 0.005（跑贏大盤 0.5%）
      與使用者公式完全一致：
        (close_t1 / close_t0) > (index_t1 / index_t0) + 0.005

      常用設定：
        只看跑贏 (alpha > 0)        → alpha_threshold=0.0
        跑贏大盤 0.5% (default)     → alpha_threshold=0.005
        跑贏大盤 1%  (積極篩選)       → alpha_threshold=0.01

    Returns:
        X, y, class_weights, scaler, feature_cols, alpha_threshold
    """
    from sklearn.utils.class_weight import compute_class_weight

    # 建構特徵
    df_feat, feature_cols = build_features_full(df_ohlcv, df_bench)

    # 統一去除時區（yfinance 可能附帶 Asia/Taipei）
    def strip_tz(s: pd.Series) -> pd.Series:
        idx = pd.to_datetime(s.index)
        if idx.tz is not None:
            idx = idx.tz_localize(None)
        s = s.copy()
        s.index = idx
        return s

    # 計算 alpha（相對大盤超額報酬）
    bench_raw   = strip_tz(df_bench['Close'])
    stock_raw   = strip_tz(df_ohlcv['Close'])
    bench       = bench_raw.reindex(df_feat.index, method='ffill')
    stock_close = stock_raw.reindex(df_feat.index, method='ffill')

    # 對齊後計算 alpha（比率格式，非百分比）
    # 對應使用者公式: (close_t1/close_t0) > (index_t1/index_t0) + 0.005
    stock_ret = stock_close.pct_change(pred_days).shift(-pred_days)
    bench_ret = bench.pct_change(pred_days).shift(-pred_days)
    alpha     = stock_ret - bench_ret   # 比率格式，不乘 100

    df_feat = df_feat.copy()
    df_feat['alpha'] = alpha
    df_feat = df_feat.dropna(subset=['alpha'])

    if len(df_feat) < seq_len + pred_days + 10:
        raise ValueError(f"樣本不足：{len(df_feat)} < {seq_len + pred_days + 10}")

    # 歸一化
    scaler = MinMaxScaler()
    df_feat[feature_cols] = scaler.fit_transform(df_feat[feature_cols].fillna(0))

    # 建立序列
    # 標籤定義【熊市強化版】：
    #   y = 1  當 alpha >= alpha_threshold（跨贏大盤 alpha_threshold%）
    #   y = 0  否則——包含跨贏小於閾値及跌幅小於大盤
    X, y = [], []
    for i in range(len(df_feat) - seq_len - pred_days):
        X.append(df_feat[feature_cols].iloc[i:i+seq_len].values)
        a = df_feat['alpha'].iloc[i + seq_len]
        y.append(1 if a >= alpha_threshold else 0)

    X = np.array(X)
    y = np.array(y, dtype=np.int32)

    # 類別加權（當閾値提高，1 的比例會降低，自動加大 1 的權重）
    uniq = np.unique(y)
    if len(uniq) < 2:
        class_weights = {0: 1.0, 1: 1.0}
    else:
        cw = compute_class_weight('balanced', classes=uniq, y=y)
        class_weights = {int(c): float(w) for c, w in zip(uniq, cw)}

    # 印出標籤分布，方便展示閾値影響
    pos = int(y.sum())
    import logging
    logging.getLogger(__name__).debug(
        f"[Label] alpha_threshold={alpha_threshold} ({alpha_threshold*100:.1f}%) | "
        f"標籤1={pos}({pos/len(y)*100:.1f}%) 標籤0={len(y)-pos}"
    )

    return X, y, class_weights, scaler, feature_cols, alpha_threshold


# ─── 快速測試 ─────────────────────────────────────────────
if __name__ == '__main__':
    import yfinance as yf, sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else '2337'
    print(f"\n🔬 特徵建構測試：{symbol}")
    print("=" * 55)

    df = yf.Ticker(symbol).history(period="2y")
    bench = yf.Ticker("^TWII").history(period="2y")

    df_feat, cols = build_features_full(df, bench)

    print(f"✅ 有效樣本: {len(df_feat)} 筆")
    print(f"✅ 特徵數量: {len(cols)} 個")
    print(f"\n特徵清單:")
    groups = [
        ("A. 技術指標", TECH_COLS),
        ("B. 量價關係", VOL_PRICE_COLS),
        ("C. VWAP",    VWAP_COLS),
        ("D. KD動能",  KD_COLS),
        ("E. 相對強弱", RS_COLS),
        ("F. 支撐壓力", SR_COLS),
    ]
    for gname, gcols in groups:
        valid = [c for c in gcols if c in cols]
        print(f"  {gname} ({len(valid)}): {valid}")

    print(f"\n最近 3 筆特徵樣本:")
    print(df_feat[cols].tail(3).T.to_string())

    # 建立訓練序列測試
    print(f"\n⚙️  建立訓練序列測試...")
    X, y, cw, scaler, feat_cols, alpha_thr = make_sequences_v2(df, bench)
    pos = y.sum()
    print(f"✅ X shape: {X.shape}")
    print(f"   跑贏={pos}({pos/len(y)*100:.1f}%), 跑輸={len(y)-pos}({(len(y)-pos)/len(y)*100:.1f}%)")
    print(f"   類別加權: {cw}")
    print(f"   alpha_threshold: {alpha_thr}")

