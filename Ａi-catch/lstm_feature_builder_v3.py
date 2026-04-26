"""
LSTM 特徵建構器 v3 - 趨勢股四大類核心指標升級版
=================================================
v2 vs v3 新增特徵：

【第1類：技術面 - 多頭排列偵測】
  + MA60         (季線，趨勢股必備)
  + ma_bull_align  多頭排列分數 (0~4：MA5>10>20>60 各加1分)
  + ma_spread_5_20  MA5 距 MA20 乖離率 (衡量多頭強度)
  + ma_all_up      全部均線向上 (1=是)
  + macd_above_zero MACD DIF/MACD 均在 0 軸上
  + macd_hist       MACD柱狀體（DIF - Signal 線）
  + macd_hist_exp   柱狀體連續 3 日擴大（上漲動能強化）
  + rsi_passivation RSI 高檔鈍化：RSI > 70 時的等級 (1=70-80, 2=80+)
  + rsi_trend_zone  RSI 所在區間（多頭: 50+, 強勢: 60+, 鈍化: 70+）

【第2類：籌碼面代理指標】（法人資料難取歷史，用量價代理）
  + chip_proxy_buy   法人買超代理：大成交量 + 收盤在高點 (視為法人接貨)
  + chip_proxy_sell  法人賣超代理：大成交量 + 收盤在低點
  + big_vol_days     近5日是否有大量日（>2倍均量）
  + accumulation     多日籌碼累積分數 (OBV 方向 10日趨勢)
  + obv_trend        OBV 10日趨勢方向 (+/-1)

【第3類：市場相對強度升級】
  + rs_60d           60日超額報酬（相對大盤）
  + rs_rank          相對強度排名代理（自身歷史分位）
  + rsi_above_50_streak  RSI 連續在 50 以上的天數（趨勢股特徵）
  + beat_market_streak   連續跑贏大盤天數

【第4類：產業族群共振代理】（無即時產業資料，用相關ETF + 同期比較）
  + sector_soc_align  SOC相關性：與半導體 ETF (0050/006208) 的 5日相關
  + momentum_20      20日動量（趨勢強度指標）
  + momentum_60      60日動量
  + ath_proximity    距歷史最高點距離（趨勢股通常在高點附近）

使用：
    from lstm_feature_builder_v3 import build_features_v3, make_sequences_v3
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import warnings
warnings.filterwarnings('ignore')


# ─── 繼承 v2 全部特徵 ────────────────────────────────────
from lstm_feature_builder import (
    _build_tech, _build_volume_price, _build_vwap,
    _build_kd, _build_relative_strength, _build_support_resistance,
    ALL_FEATURE_COLS as V2_FEATURE_COLS
)

# ══════════════════════════════════════════════════════════
# 第1類：技術面升級 - 多頭排列 + MACD 完整版
# ══════════════════════════════════════════════════════════

def _build_trend_tech(df: pd.DataFrame) -> pd.DataFrame:
    """
    趨勢股核心技術指標（v3 新增）

    多頭排列（Bullish Alignment）：
      判斷 MA5 > MA10 > MA20 > MA60 且全部向上
    MACD 完整版：
      DIF（EMA12-EMA26）、Signal（EMA9）、Histogram
      + 是否在 0 軸上、柱體是否擴大
    RSI 鈍化偵測：
      趨勢股 RSI > 70 不是賣點，是強勢特徵
    """
    df = df.copy()

    # ── MA60（季線） ─────────────────────────────────────
    df['MA60'] = df['Close'].rolling(60).mean()

    # ── 多頭排列分數（0~4） ──────────────────────────────
    # 每條件成立加 1 分：MA5>MA10, MA10>MA20, MA20>MA60, MA5>MA60
    ma5  = df['Close'].rolling(5).mean()
    ma10 = df['Close'].rolling(10).mean()
    ma20 = df['Close'].rolling(20).mean()
    ma60 = df['MA60']

    df['ma_bull_align'] = (
        (ma5  > ma10).astype(int) +
        (ma10 > ma20).astype(int) +
        (ma20 > ma60).astype(int) +
        (ma5  > ma60).astype(int)
    ).astype(float)

    # ── MA 乖離率與趨勢 ──────────────────────────────────
    df['ma_spread_5_20'] = (ma5 - ma20) / (ma20 + 1e-9) * 100   # 正值=多頭
    df['ma_all_up'] = (
        (ma5.diff()  > 0) &
        (ma10.diff() > 0) &
        (ma20.diff() > 0) &
        (ma60.diff() > 0)
    ).astype(float)

    # ── MACD 完整版 ──────────────────────────────────────
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    dif   = ema12 - ema26
    signal = dif.ewm(span=9, adjust=False).mean()
    hist  = dif - signal   # 柱狀體

    df['macd_dif']        = dif
    df['macd_signal']     = signal
    df['macd_hist']       = hist
    df['macd_above_zero'] = ((dif > 0) & (signal > 0)).astype(float)  # 兩者都在 0 軸上
    # 柱狀體連續 3 天擴大（正向擴大 or 縮小）
    hist_diff = hist.diff()
    df['macd_hist_exp'] = (
        (hist_diff > 0) & (hist_diff.shift(1) > 0) & (hist_diff.shift(2) > 0) & (hist > 0)
    ).astype(float)   # 1 = 連續 3 天柱體擴大且在 0 軸上方

    # ── RSI 高檔鈍化偵測 ─────────────────────────────────
    delta = df['Close'].diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi   = 100 - 100 / (1 + gain / (loss + 1e-9))

    df['rsi_passivation'] = np.where(rsi >= 80, 2.0,
                            np.where(rsi >= 70, 1.0, 0.0))   # 2=極強鈍化，1=輕鈍化

    df['rsi_trend_zone']  = np.where(rsi >= 70, 3.0,           # 高檔鈍化區
                            np.where(rsi >= 60, 2.0,           # 多頭強勢區
                            np.where(rsi >= 50, 1.0,           # 多頭基礎區
                                                0.0)))          # 弱勢區

    # RSI 連續在 50 以上的天數（趨勢股特徵）
    above50 = (rsi >= 50).astype(int)
    streak = []
    count = 0
    for v in above50:
        if v == 1:
            count += 1
        else:
            count = 0
        streak.append(count)
    df['rsi_above_50_streak'] = np.array(streak, dtype=float)

    return df


TREND_TECH_COLS = [
    'ma_bull_align', 'ma_spread_5_20', 'ma_all_up', 'MA60',
    'macd_hist', 'macd_above_zero', 'macd_hist_exp',
    'rsi_passivation', 'rsi_trend_zone', 'rsi_above_50_streak'
]


# ══════════════════════════════════════════════════════════
# 第2類：籌碼面代理指標（法人買超代理）
# ══════════════════════════════════════════════════════════

def _build_chip_proxy(df: pd.DataFrame) -> pd.DataFrame:
    """
    法人籌碼代理特徵（因歷史法人資料難取得，用量價行為代理）

    法人買超行為特徵（學術研究依據）：
      - 大量 + 收盤在高點 = 機構悄悄買入（不願拉尾盤）
      - 連續多日收在 VWAP 以上 = 法人布局
      - OBV 趨勢上升 = 籌碼累積
    """
    df = df.copy()

    vol_ma20 = df['Volume'].rolling(20).mean()

    # 收盤在當日區間的位置 (0~1，1=收最高，0=收最低)
    high_low_range = df['High'] - df['Low'] + 1e-9
    close_pos = (df['Close'] - df['Low']) / high_low_range  # 0~1

    # 法人買超代理：大量 + 收盤在上半段 (> 60%)
    df['chip_proxy_buy']  = (
        (df['Volume'] > vol_ma20 * 1.5) & (close_pos > 0.6)
    ).astype(float)

    # 法人賣超代理：大量 + 收盤在下半段 (< 40%)
    df['chip_proxy_sell'] = (
        (df['Volume'] > vol_ma20 * 1.5) & (close_pos < 0.4)
    ).astype(float)

    # 5日內是否有大量日（爆量 > 2倍均量）
    df['big_vol_days'] = (df['Volume'] > vol_ma20 * 2.0).rolling(5).sum()

    # OBV (On-Balance Volume) 計算
    obv = []
    prev_obv = 0
    prev_close = None
    for _, row in df.iterrows():
        if prev_close is None:
            obv.append(0.0)
        elif row['Close'] > prev_close:
            prev_obv += row['Volume']
            obv.append(float(prev_obv))
        elif row['Close'] < prev_close:
            prev_obv -= row['Volume']
            obv.append(float(prev_obv))
        else:
            obv.append(float(prev_obv))
        prev_close = row['Close']

    df['obv'] = obv

    # OBV 10日趨勢方向
    obv_s = pd.Series(df['obv'].values, index=df.index)
    obv_ma = obv_s.rolling(10).mean()
    df['obv_trend']   = np.where(obv_s > obv_ma, 1.0, -1.0)

    # 籌碼累積分數：OBV 是否連續上升（正值=積累 負值=出貨）
    obv_diff = obv_s.diff()
    df['accumulation'] = (
        obv_diff.rolling(5).apply(lambda x: np.sign(x).sum(), raw=True)
    ) / 5.0   # -1 到 +1 之間，正值= 籌碼集中

    return df


CHIP_COLS = [
    'chip_proxy_buy', 'chip_proxy_sell', 'big_vol_days',
    'obv_trend', 'accumulation'
]


# ══════════════════════════════════════════════════════════
# 第3類：市場相對強度升級版
# ══════════════════════════════════════════════════════════

def _build_relative_strength_v3(df: pd.DataFrame, df_bench: pd.DataFrame) -> pd.DataFrame:
    """
    升級版相對強度指標（加入 60 日、連勝天數）

    rs_60d          60日超額報酬（相對大盤，中期趨勢）
    rs_rank         個股自身 RS 的歷史分位（0~1，越高越強）
    beat_market_streak  連續跑贏大盤天數（趨勢股特徵）
    momentum_20     20日動量（趨勢強度）
    momentum_60     60日動量（波段趨勢強度）
    ath_proximity   距 ATH 距離（趨勢股特徵：在高點附近）
    """
    df = df.copy()

    bench = df_bench['Close'].reindex(df.index, method='ffill')
    stock_ret1 = df['Close'].pct_change(1)
    bench_ret1 = bench.pct_change(1)

    # 60日超額報酬
    stock_ret60 = df['Close'].pct_change(60)
    bench_ret60 = bench.pct_change(60)
    df['rs_60d'] = (stock_ret60 - bench_ret60) * 100

    # RS 歷史分位（越高代表越強）
    rs_1d = (stock_ret1 - bench_ret1) * 100
    df['rs_rank'] = rs_1d.rolling(60).rank(pct=True)   # 0~1

    # 連續跑贏大盤天數
    beat = (stock_ret1 > bench_ret1).astype(int)
    streak = []
    count = 0
    for v in beat:
        if v == 1:
            count += 1
        else:
            count = 0
        streak.append(count)
    df['beat_market_streak'] = np.array(streak, dtype=float)

    # 動量指標（趨勢強度代理）
    df['momentum_20'] = df['Close'].pct_change(20) * 100
    df['momentum_60'] = df['Close'].pct_change(60) * 100

    # 距 ATH 距離（趨勢股特徵：股價在年高點 95% 以上）
    ath = df['High'].rolling(252, min_periods=60).max()
    df['ath_proximity'] = (df['Close'] / (ath + 1e-9)) * 100   # 100=在 ATH

    return df


RS_V3_COLS = [
    'rs_60d', 'rs_rank', 'beat_market_streak',
    'momentum_20', 'momentum_60', 'ath_proximity'
]


# ══════════════════════════════════════════════════════════
# 第4類：產業族群 & 基本面代理
# ══════════════════════════════════════════════════════════

# 台股重要產業 ETF / 代理股
INDUSTRY_MAP = {
    'CPO':      ['4967', '3491', '6176', '4966'],
    'PCB':      ['2383', '3037', '6669', '2367'],
    'ABF':      ['3037', '3006', '2369', '6749'],
    'HBM':      ['4256', '6531', '3443', '8046'],
    'Satellite': ['3706', '5222', '6595', '4743'],
    'Semi':     ['2330', '2454', '2303', '2308'],
    'AI':       ['2330', '2454', '3711', '2379'],
}

# 反查：股票在哪些產業
def get_stock_industries(symbol: str) -> list:
    """回傳該股票所屬的產業清單"""
    result = []
    for ind, stocks in INDUSTRY_MAP.items():
        if str(symbol) in stocks:
            result.append(ind)
    return result


def _build_sector_proxy(df: pd.DataFrame, df_bench: pd.DataFrame,
                        sector_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    產業族群共振代理特徵

    當沒有同業資料時，改用：
      - 自身動量 vs 大盤的相對動量
      - 股價在布林帶的位置（突破上帶=族群帶動特徵）
    """
    df = df.copy()

    # 布林帶（Bollinger Bands）
    bb_ma = df['Close'].rolling(20).mean()
    bb_std = df['Close'].rolling(20).std()
    bb_upper = bb_ma + 2 * bb_std
    bb_lower = bb_ma - 2 * bb_std

    # 股價在布林帶的位置（0~1，>0.8 代表接近上帶 = 強勢突破）
    bb_range = (bb_upper - bb_lower + 1e-9)
    df['bb_position'] = (df['Close'] - bb_lower) / bb_range   # 0~1

    # 布林帶突破（股價突破上帶）
    df['bb_breakout'] = (df['Close'] > bb_upper).astype(float)

    # 動量加速度（20日動量的 5日變化率 = 是否加速上漲）
    mom20 = df['Close'].pct_change(20) * 100
    df['momentum_accel'] = mom20.diff(5)   # 正值 = 動量加速（族群帶動特徵）

    # 相對大盤動量差距（自身 20日動量 - 大盤 20日動量）
    bench = df_bench['Close'].reindex(df.index, method='ffill')
    bench_mom20 = bench.pct_change(20) * 100
    df['sector_outmom'] = mom20 - bench_mom20   # 正值=跑贏大盤動量

    # 同業共振代理（若有傳入同業資料）
    if sector_df is not None:
        sector_ret = sector_df['Close'].reindex(df.index, method='ffill').pct_change(5) * 100
        stock_ret5 = df['Close'].pct_change(5) * 100
        # 5日相關性（是否與同業同步上漲）
        corr = []
        for i in range(len(df)):
            if i < 20:
                corr.append(0.5)
            else:
                s1 = stock_ret5.iloc[max(0,i-20):i].values
                s2 = sector_ret.iloc[max(0,i-20):i].values
                if len(s1) > 5 and np.std(s1) > 0 and np.std(s2) > 0:
                    corr.append(float(np.corrcoef(s1, s2)[0, 1]))
                else:
                    corr.append(0.5)
        df['sector_corr'] = corr
    else:
        df['sector_corr'] = 0.5   # 無法計算時填入中性值

    return df


SECTOR_COLS = [
    'bb_position', 'bb_breakout', 'momentum_accel',
    'sector_outmom', 'sector_corr'
]


# ══════════════════════════════════════════════════════════
# 完整特徵清單（v2 + v3 新增）
# ══════════════════════════════════════════════════════════

V3_EXTRA_COLS = TREND_TECH_COLS + CHIP_COLS + RS_V3_COLS + SECTOR_COLS

# 去重合併
ALL_FEATURE_COLS_V3 = list(dict.fromkeys(V2_FEATURE_COLS + V3_EXTRA_COLS))

print(f"📊 v3 特徵總數: {len(ALL_FEATURE_COLS_V3)} 個 "
      f"(v2={len(V2_FEATURE_COLS)} + v3新增={len(V3_EXTRA_COLS)})")


# ══════════════════════════════════════════════════════════
# 主建構函數
# ══════════════════════════════════════════════════════════

def build_features_v3(df_ohlcv: pd.DataFrame,
                      df_bench: pd.DataFrame = None,
                      sector_df: pd.DataFrame = None) -> tuple:
    """
    完整特徵建構入口 v3

    Args:
        df_ohlcv  : yfinance 格式 OHLCV DataFrame
        df_bench  : 大盤指數（^TWII）
        sector_df : 同業代表股（可選，用於族群共振）

    Returns:
        (df_features, feature_cols)
    """
    df = df_ohlcv.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)

    # ── v2 基礎特徵 ─────────────────────────────────────
    df = _build_tech(df)
    df = _build_volume_price(df)
    df = _build_vwap(df)
    df = _build_kd(df)

    if df_bench is not None:
        bench = df_bench.copy()
        bench.index = pd.to_datetime(bench.index).tz_localize(None)
        df = _build_relative_strength(df, bench)
    else:
        from lstm_feature_builder import RS_COLS
        for col in RS_COLS:
            df[col] = 0.0

    if 'High' in df.columns and 'Low' in df.columns:
        df = _build_support_resistance(df)
    else:
        from lstm_feature_builder import SR_COLS
        for col in SR_COLS:
            df[col] = 0.0

    # ── v3 新增特徵 ─────────────────────────────────────
    # 第1類：趨勢技術指標
    df = _build_trend_tech(df)

    # 第2類：籌碼面代理
    df = _build_chip_proxy(df)

    # 第3類：相對強度升級
    if df_bench is not None:
        bench_clean = df_bench.copy()
        bench_clean.index = pd.to_datetime(bench_clean.index).tz_localize(None)
        df = _build_relative_strength_v3(df, bench_clean)
    else:
        for col in RS_V3_COLS:
            df[col] = 0.0

    # 第4類：產業族群代理
    bench_for_sector = None
    if df_bench is not None:
        bench_for_sector = df_bench.copy()
        bench_for_sector.index = pd.to_datetime(bench_for_sector.index).tz_localize(None)
    df = _build_sector_proxy(df, bench_for_sector if bench_for_sector is not None else df, sector_df)

    # ── 整理輸出 ─────────────────────────────────────────
    feature_cols = [c for c in ALL_FEATURE_COLS_V3 if c in df.columns]
    df_feat = df[feature_cols].copy()
    df_feat = df_feat.replace([np.inf, -np.inf], np.nan)
    df_feat = df_feat.dropna()

    return df_feat, feature_cols


def make_sequences_v3(df_ohlcv: pd.DataFrame,
                      df_bench: pd.DataFrame,
                      seq_len: int = 20,
                      pred_days: int = 5,
                      alpha_threshold: float = 0.005,
                      sector_df: pd.DataFrame = None):
    """
    建立 LSTM 訓練序列（v3 完整特徵集）

    標籤定義（趨勢股版）：
      y = 1 當未來 pred_days 天的超額報酬 >= alpha_threshold
          即個股跑贏大盤 0.5%（預設）

    Returns:
        X, y, class_weights, scaler, feature_cols, alpha_threshold
    """
    from sklearn.utils.class_weight import compute_class_weight

    # 建構特徵
    df_feat, feature_cols = build_features_v3(df_ohlcv, df_bench, sector_df)

    # 去除時區
    def strip_tz(s):
        idx = pd.to_datetime(s.index)
        if idx.tz is not None:
            idx = idx.tz_localize(None)
        s = s.copy()
        s.index = idx
        return s

    # 計算 alpha 標籤
    bench_raw   = strip_tz(df_bench['Close'])
    stock_raw   = strip_tz(df_ohlcv['Close'])
    bench       = bench_raw.reindex(df_feat.index, method='ffill')
    stock_close = stock_raw.reindex(df_feat.index, method='ffill')

    stock_ret = stock_close.pct_change(pred_days).shift(-pred_days)
    bench_ret = bench.pct_change(pred_days).shift(-pred_days)
    alpha     = stock_ret - bench_ret   # 比率格式

    df_feat = df_feat.copy()
    df_feat['alpha'] = alpha
    df_feat = df_feat.dropna(subset=['alpha'])

    if len(df_feat) < seq_len + pred_days + 10:
        raise ValueError(f"樣本不足：{len(df_feat)} < {seq_len + pred_days + 10}")

    # 歸一化（先建立全特徵 scaler，RF 篩選後再重建精簡 scaler）
    scaler = MinMaxScaler()
    df_feat[feature_cols] = scaler.fit_transform(df_feat[feature_cols].fillna(0))

    # 建立序列
    X, y = [], []
    for i in range(len(df_feat) - seq_len - pred_days):
        X.append(df_feat[feature_cols].iloc[i:i+seq_len].values)
        a = df_feat['alpha'].iloc[i + seq_len]
        y.append(1 if a >= alpha_threshold else 0)

    X = np.array(X)
    y = np.array(y, dtype=np.int32)

    # 類別加權
    uniq = np.unique(y)
    if len(uniq) < 2:
        class_weights = {0: 1.0, 1: 1.0}
    else:
        cw = compute_class_weight('balanced', classes=uniq, y=y)
        class_weights = {int(c): float(w) for c, w in zip(uniq, cw)}

    pos = int(y.sum())
    print(f"   [v3] 標籤: 跑贏={pos}({pos/len(y)*100:.1f}%) 跑輸={len(y)-pos}")

    return X, y, class_weights, scaler, feature_cols, alpha_threshold


# ──────────────────────────────────────────────────────────
# 快速測試
# ──────────────────────────────────────────────────────────
if __name__ == '__main__':
    import yfinance as yf, sys

    symbol = sys.argv[1] if len(sys.argv) > 1 else '2337'
    print(f"\n🔬 v3 特徵建構測試：{symbol}")
    print("=" * 60)

    df = yf.Ticker(f"{symbol}.TW").history(period="2y")
    bench = yf.Ticker("^TWII").history(period="2y")

    df_feat, cols = build_features_v3(df, bench)

    print(f"✅ 有效樣本: {len(df_feat)} 筆")
    print(f"✅ 特徵數量: {len(cols)} 個")

    groups = [
        ("A. 技術指標(原)",  ['Close','Volume','MA5','MA10','MA20','Volume_MA5','RSI','Volatility','MACD']),
        ("B. 量價關係",      ['price_up_vol_up','price_up_vol_down','vol_ratio_5','vol_ratio_20','price_vol_score']),
        ("C. KD動能",        ['kd_k','kd_d','kd_diff','kd_overbought','kd_oversold']),
        ("D. 相對強弱(原)",  ['rs_1d','rs_5d','rs_20d','outperform_5d','rs_trend']),
        ("E. 支撐壓力",      ['dist_52w_high','dist_52w_low','near_resistance','near_support']),
        ("★ 第1類(多頭排列)", TREND_TECH_COLS),
        ("★ 第2類(籌碼代理)", CHIP_COLS),
        ("★ 第3類(RS升級)",   RS_V3_COLS),
        ("★ 第4類(族群共振)", SECTOR_COLS),
    ]
    print()
    for gname, gcols in groups:
        valid = [c for c in gcols if c in cols]
        print(f"  {gname:26s} ({len(valid)}): {valid}")

    print(f"\n{'─'*60}")
    print("📋 最近 1 筆特徵值（趨勢指標）：")
    trend_cols = [c for c in TREND_TECH_COLS + CHIP_COLS + RS_V3_COLS + SECTOR_COLS if c in df_feat.columns]
    print(df_feat[trend_cols].tail(1).T.to_string())

    # 建立訓練序列測試
    print(f"\n⚙️  訓練序列建構測試...")
    X, y, cw, scaler, feat_cols, alpha_thr = make_sequences_v3(df, bench)
    pos = y.sum()
    print(f"✅ X shape: {X.shape}")
    print(f"   跑贏={pos}({pos/len(y)*100:.1f}%),  跑輸={len(y)-pos}({(len(y)-pos)/len(y)*100:.1f}%)")
    print(f"   類別加權: {cw}")
