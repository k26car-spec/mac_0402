"""
lstm_feature_builder_v4.py
特徵建構模組 v4 — 使用滾動標準化，廢棄外部 scaler.pkl
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


# ──────────────────────────────────────────
# 1. 特徵計算
# ──────────────────────────────────────────

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    輸入：包含 Open / High / Low / Close / Volume 的日線 DataFrame
    輸出：附加 15 個特徵欄位的 DataFrame（原始尺度，尚未 normalize）
    """
    df = df.copy()
    close  = df["Close"]
    volume = df["Volume"]

    # --- 趨勢 ---
    df["MA5"]  = close.rolling(5).mean()
    df["MA10"] = close.rolling(10).mean()
    df["MA20"] = close.rolling(20).mean()
    df["MA60"] = close.rolling(60).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26

    # --- 動能 ---
    df["momentum_20"]   = close / close.shift(20) - 1
    df["momentum_60"]   = close / close.shift(60) - 1
    df["momentum_accel"] = df["momentum_20"] - df["momentum_20"].shift(5)

    # 相對強度（對自身 20/60 日基準）
    df["rs_20d"]  = close / close.rolling(20).mean() - 1
    df["rs_trend"] = df["rs_20d"] - df["rs_20d"].shift(10)

    # --- 籌碼 ---
    df["Volume_MA5"] = volume.rolling(5).mean()

    # --- 風險/位階 ---
    df["Volatility"]   = close.pct_change().rolling(20).std()
    df["dist_52w_low"] = close / close.rolling(252).min() - 1

    # KD（隨機指標）
    low14  = df["Low"].rolling(14).min()
    high14 = df["High"].rolling(14).max()
    rsv    = (close - low14) / (high14 - low14 + 1e-8) * 100
    k      = rsv.ewm(com=2, adjust=False).mean()
    d      = k.ewm(com=2, adjust=False).mean()
    df["kd_diff"] = k - d

    return df


FEATURE_COLS = [
    "Close", "MA5", "MA10", "MA20", "MA60", "MACD",
    "momentum_20", "momentum_60", "momentum_accel",
    "rs_20d", "rs_trend", "Volume_MA5",
    "Volatility", "dist_52w_low", "kd_diff",
]


# ──────────────────────────────────────────
# 2. 滾動標準化（核心升級點）
# ──────────────────────────────────────────

def normalize_features(
    df: pd.DataFrame,
    feature_cols: list = FEATURE_COLS,
    window: int = 60,
    min_periods: int = 20,
) -> pd.DataFrame:
    """
    用 rolling window 對每個特徵做 z-score 標準化。

    優點：
    - 自帶時序適應性，不需要外部 scaler.pkl
    - 無未來洩漏（只用過去 window 天的統計量）
    - 各股票特徵尺度統一，值域約 -3 ~ +3

    注意：
    - 必須在訓練 / 推論前重新計算（不可重用舊 scaler）
    - 前 min_periods 行會產生 NaN，需在後續步驟 dropna
    """
    df_out = df.copy()
    for col in feature_cols:
        if col not in df_out.columns:
            continue
        roll_mean = df_out[col].rolling(window, min_periods=min_periods).mean()
        roll_std  = df_out[col].rolling(window, min_periods=min_periods).std()
        df_out[col] = (df_out[col] - roll_mean) / (roll_std + 1e-8)
    return df_out


# ──────────────────────────────────────────
# 3. 標籤建構
# ──────────────────────────────────────────

def create_label(
    prices: pd.Series,
    horizon: int = 5,
    cost_rate: float = 0.003,
    cost_multiplier: float = 1.5,
) -> pd.Series:
    """
    標籤：未來 horizon 天報酬 > cost_rate × cost_multiplier 才為 1。

    預設：手續費 0.3%，門檻 = 0.45%，避免「微漲但賺不過手續費」的假陽性。
    最後 horizon 行因無未來資料，標籤為 NaN（訓練時需 dropna）。
    """
    future_return = prices.shift(-horizon) / prices - 1
    threshold = cost_rate * cost_multiplier
    label = (future_return > threshold).astype(float)
    label.iloc[-horizon:] = np.nan   # 最後幾行沒有未來，設為 NaN
    return label


# ──────────────────────────────────────────
# 4. 序列切割（供 DataLoader 使用）
# ──────────────────────────────────────────

def make_sequences(
    df: pd.DataFrame,
    label: pd.Series,
    seq_len: int = 40,
    feature_cols: list = FEATURE_COLS,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    將已 normalize 的 DataFrame 切成 (X, y) 序列對。

    X shape: (N, seq_len, n_features)
    y shape: (N,)

    只保留 X 和 y 都不含 NaN 的樣本。
    """
    df_clean = df[feature_cols].copy()
    df_clean["__label__"] = label.values

    # 去掉任何含 NaN 的行
    df_clean = df_clean.dropna()

    X_list, y_list = [], []
    arr = df_clean[feature_cols].values
    lbl = df_clean["__label__"].values

    for i in range(seq_len, len(arr)):
        X_list.append(arr[i - seq_len : i])
        y_list.append(lbl[i])

    if not X_list:
        return np.empty((0, seq_len, len(feature_cols))), np.empty(0)

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.float32)


# ──────────────────────────────────────────
# 5. 完整 pipeline（一站式呼叫）
# ──────────────────────────────────────────

def build_dataset(
    df_raw: pd.DataFrame,
    seq_len: int = 40,
    horizon: int = 5,
    norm_window: int = 60,
    cost_rate: float = 0.003,
    feature_cols: list = FEATURE_COLS,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    從原始日線資料到 (X, y) 的完整流程：
    build_features → normalize_features → create_label → make_sequences
    """
    df = build_features(df_raw)
    df = normalize_features(df, feature_cols=feature_cols, window=norm_window)
    label = create_label(df_raw["Close"], horizon=horizon, cost_rate=cost_rate)
    X, y = make_sequences(df, label, seq_len=seq_len, feature_cols=feature_cols)
    return X, y


# ──────────────────────────────────────────
# 快速自測
# ──────────────────────────────────────────

if __name__ == "__main__":
    dates  = pd.date_range("2020-01-01", periods=400, freq="B")
    np.random.seed(42)
    price  = 100 * np.cumprod(1 + np.random.randn(400) * 0.01)
    volume = np.random.randint(1000, 5000, 400).astype(float)

    dummy = pd.DataFrame({
        "Open":   price * 0.99,
        "High":   price * 1.01,
        "Low":    price * 0.98,
        "Close":  price,
        "Volume": volume,
    }, index=dates)

    X, y = build_dataset(dummy)
    print(f"X shape : {X.shape}")        # 期望 (N, 40, 15)
    print(f"y shape : {y.shape}")        # 期望 (N,)
    print(f"X range : [{X.min():.2f}, {X.max():.2f}]")  # 期望約 -4 ~ +4
    print(f"y balance: {y.mean():.2%}")  # 期望約 50% ± 隨機
