"""
LSTM 訓練 v4 - 整合法人籌碼特徵
=====================================
核心改進：
  1. 特徵集從 9 個技術指標 → 9 技術 + 13 法人籌碼 = 22 個特徵
  2. 法人特徵：外資/投信/自營商買賣超、累積、動能、籌碼一致性
  3. 訓練標籤：未來 5 天是否跑贏大盤（Alpha > 0）
  4. 輕量模型架構（避免過擬合小樣本）
  5. 使用 2 年以上歷史法人數據

執行：
    python3 train_lstm_v4.py --stocks 2881,2317    # 指定股票
    python3 train_lstm_v4.py                        # 訓練所有問題模型
    python3 train_lstm_v4.py --all                  # 訓練全部 50 支
"""

import numpy as np
import pandas as pd
import json
import os
import argparse
import warnings
warnings.filterwarnings('ignore')
import logging

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import MinMaxScaler
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import yfinance as yf
from datetime import datetime, timedelta

logging.basicConfig(level=logging.WARNING)  # 靜默 TF 日誌

print("=" * 70)
print("🔧 LSTM v4 - 技術指標 + 法人籌碼特徵")
print("=" * 70)
print(f"TensorFlow {tf.__version__}")

# ─── 導入法人爬取器 ─────────────────────────────────────
try:
    from chip_feature_fetcher import ChipFeatureFetcher
    CHIP_FETCHER = ChipFeatureFetcher()
    print("✅ 法人籌碼爬取器已載入")
except ImportError:
    print("⚠️  chip_feature_fetcher 未找到，退回純技術指標模式")
    CHIP_FETCHER = None

# ─── 配置 ────────────────────────────────────────────────
MODEL_DIR   = "models/lstm_smart_entry"
SEQ_LEN     = 20      # 回看 20 天（法人數據較少，縮短序列）
PRED_DAYS   = 5       # 預測未來 5 天
EPOCHS      = 300
BATCH_SIZE  = 16
LR          = 0.0003

# 全技術特徵欄位
TECH_COLS = ['Close','Volume','MA5','MA10','MA20',
             'Volume_MA5','RSI','Volatility','MACD']

# 法人特徵欄位（與 chip_feature_fetcher 輸出一致）
CHIP_COLS = [
    'foreign_net', 'trust_net', 'dealer_net', 'inst_net_total',
    'foreign_cum5', 'foreign_cum10', 'inst_total_cum5', 'inst_total_cum10',
    'foreign_momentum', 'inst_consensus',
    'margin_balance', 'margin_chg_5d', 'margin_ratio'
]

# 問題模型清單（回測確認的 36 支）
PROBLEM_STOCKS = [
    '8422','2317','2881','6285','1802','2371','6282','1301',
    '3706','3034','2454','2382','2002','6257','5521','3189',
    '2303','2412','1326','2314','6153','2609','3037','2313',
    '3008','1303','2379','8150','2408','2618','3231',
    '2449','2344','6770','2367','2337'   # 無腦看多的也要重訓
]

os.makedirs(MODEL_DIR, exist_ok=True)


# ─── 技術指標計算 ─────────────────────────────────────────
def build_tech_features(df: pd.DataFrame) -> pd.DataFrame:
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


# ─── 數據整合 ──────────────────────────────────────────────
def fetch_combined_data(symbol: str) -> pd.DataFrame | None:
    """
    整合技術指標 + 法人籌碼 + 大盤基準
    自動降級：若法人數據不足，退回純技術指標
    """
    # 1. 技術指標數據（yfinance）
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        df_tech = ticker.history(period="3y")
        if df_tech.empty or len(df_tech) < 120:
            return None
        df_tech = build_tech_features(df_tech)
        df_tech.index = df_tech.index.tz_localize(None)  # 去時區

        # 大盤基準
        bench = yf.Ticker("^TWII")
        bench_df = bench.history(period="3y")[['Close']].rename(columns={'Close': 'Bench'})
        bench_df.index = bench_df.index.tz_localize(None)
        df_tech = df_tech.join(bench_df, how='left')
        df_tech['Bench'] = df_tech['Bench'].ffill()
        df_tech = df_tech.dropna(subset=TECH_COLS + ['Bench'])
    except Exception as e:
        print(f"   ⚠️ 技術數據獲取失敗: {e}")
        return None

    # 2. 法人籌碼數據（TWSE）
    chip_df = None
    if CHIP_FETCHER is not None:
        try:
            start_date = (datetime.now() - timedelta(days=3*365)).strftime('%Y-%m-%d')
            chip_df = CHIP_FETCHER.get_chip_features(symbol, start=start_date)
            if not chip_df.empty and len(chip_df) >= 20:
                print(f"   ✅ 法人數據: {len(chip_df)} 筆")
            else:
                print(f"   ⚠️ 法人數據不足（{len(chip_df) if chip_df is not None else 0} 筆），退回純技術模式")
                chip_df = None
        except Exception as e:
            print(f"   ⚠️ 法人數據爬取失敗: {e}")
            chip_df = None

    # 3. 合併
    if chip_df is not None:
        # 用 left join - 保留所有技術日期，法人缺值填 0
        df_tech.index = pd.to_datetime(df_tech.index).normalize()
        chip_df.index = pd.to_datetime(chip_df.index).normalize()
        df_combined = df_tech.join(chip_df, how='left')
        # 法人欄位：缺值填 0（表示當天無特殊籌碼動作）
        for col in CHIP_COLS:
            if col in df_combined.columns:
                df_combined[col] = df_combined[col].fillna(0)
        feature_cols = TECH_COLS + [c for c in CHIP_COLS if c in df_combined.columns]
        valid_chip = df_combined[chip_df.columns[0]].ne(0).sum()
        print(f"   📊 合併後: {len(df_combined)} 天 | {len(feature_cols)} 個特徵 | 法人有效日: {valid_chip}")
    else:
        df_combined = df_tech
        feature_cols = TECH_COLS
        print(f"   📊 純技術: {len(df_combined)} 天 | {len(feature_cols)} 個特徵")

    df_combined.__feature_cols__ = feature_cols  # 附加特徵清單
    return df_combined


# ─── 建立訓練序列 ───────────────────────────────────────────
def make_sequences(df: pd.DataFrame, feature_cols: list):
    """
    標籤：未來 5 天是否跑贏大盤（Alpha > 0）
    """
    df = df.copy()
    stock_ret = (df['Close'].shift(-PRED_DAYS) / df['Close'] - 1)
    bench_ret = (df['Bench'].shift(-PRED_DAYS) / df['Bench'] - 1)
    df['alpha'] = (stock_ret - bench_ret) * 100
    df = df.dropna(subset=['alpha'])

    # 歸一化特徵
    scaler = MinMaxScaler()
    available = [c for c in feature_cols if c in df.columns]
    df[available] = scaler.fit_transform(df[available].fillna(0))

    X, y = [], []
    for i in range(len(df) - SEQ_LEN - PRED_DAYS):
        X.append(df[available].iloc[i:i+SEQ_LEN].values)
        y.append(1 if df['alpha'].iloc[i + SEQ_LEN] > 0 else 0)

    X = np.array(X)
    y = np.array(y, dtype=np.int32)

    # 類別加權（確保有兩個類別）
    unique_classes = np.unique(y)
    if len(unique_classes) < 2:
        class_weights = {0: 1.0, 1: 1.0}  # 只有單一類別，不加權
    else:
        cw = compute_class_weight('balanced', classes=unique_classes, y=y)
        class_weights = {int(c): float(w) for c, w in zip(unique_classes, cw)}

    return X, y, class_weights, scaler, len(available)


# ─── 模型架構 ─────────────────────────────────────────────
def build_model(seq_len: int, n_features: int) -> tf.keras.Model:
    """
    輕量 LSTM 分類器
    - 2 層 LSTM（48 + 24 units）
    - Sigmoid 輸出（看漲機率）
    """
    model = Sequential([
        LSTM(48, return_sequences=True,
             input_shape=(seq_len, n_features),
             dropout=0.15, recurrent_dropout=0.05),
        BatchNormalization(),

        LSTM(24, return_sequences=False,
             dropout=0.15, recurrent_dropout=0.05),
        BatchNormalization(),
        Dropout(0.15),

        Dense(12, activation='relu'),
        Dropout(0.1),
        Dense(1, activation='sigmoid')
    ])
    model.compile(
        optimizer=Adam(learning_rate=LR),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model


# ─── 訓練單一股票 ──────────────────────────────────────────
def train_one(symbol: str) -> dict:
    print(f"\n{'─'*55}")
    print(f"🔄 [{symbol}] 開始訓練")
    print(f"{'─'*55}")

    # 1. 數據
    df = fetch_combined_data(symbol)
    if df is None:
        return {'symbol': symbol, 'status': 'data_error'}

    feature_cols = getattr(df, '__feature_cols__', TECH_COLS)

    # 2. 序列
    X, y, class_weights, scaler, n_feat = make_sequences(df, feature_cols)
    pos = y.sum()
    neg = len(y) - pos
    print(f"   📦 樣本: {len(X)}, 跑贏={pos}({pos/len(y)*100:.0f}%), 跑輸={neg}({neg/len(y)*100:.0f}%)")
    print(f"   ⚖️  類別加權: {class_weights}")

    if len(X) < 50:
        return {'symbol': symbol, 'status': 'insufficient_data', 'samples': len(X)}

    # 3. 分割（80% 訓練 / 20% 測試）
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # 4. 模型
    model = build_model(SEQ_LEN, n_feat)
    print(f"   🏗️  模型參數數: {model.count_params():,}")

    # 5. 訓練
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=40,
                      restore_best_weights=True, verbose=0),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5,
                          patience=12, min_lr=1e-6, verbose=0)
    ]
    print(f"   🚀 訓練中（最多 {EPOCHS} epochs）...")
    history = model.fit(
        X_train, y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_split=0.2,
        class_weight=class_weights,
        callbacks=callbacks,
        verbose=0
    )

    ep = len(history.history['loss'])
    final_loss     = history.history['loss'][-1]
    final_val_loss = history.history['val_loss'][-1]
    print(f"   ✓ {ep} epochs | train_loss={final_loss:.4f} | val_loss={final_val_loss:.4f}")

    # 6. 評估
    preds = model.predict(X_test, verbose=0).flatten()
    pred_b = (preds > 0.5).astype(int)
    acc  = float(accuracy_score(y_test, pred_b))
    prec = float(precision_score(y_test, pred_b, zero_division=0))
    rec  = float(recall_score(y_test, pred_b, zero_division=0))
    f1   = float(f1_score(y_test, pred_b, zero_division=0))
    pos_preds = int(pred_b.sum())

    print(f"   📊 評估: 準確率={acc*100:.1f}% | 精確率={prec*100:.1f}% | 召回率={rec*100:.1f}% | +預測={pos_preds}/{len(pred_b)}")

    # 7. 判斷合格性（不是全買也不是全不買，且精確率 > 隨機水準）
    is_valid = bool(pos_preds > 0 and pos_preds < len(pred_b) and prec > 0.45)
    mode = "法人+技術" if len(feature_cols) > len(TECH_COLS) else "純技術"
    print(f"   {'✅ 合格' if is_valid else '⚠️  偏差'} | 模式: {mode}")

    # 8. 儲存
    model_path = os.path.join(MODEL_DIR, f"{symbol}_model.h5")
    model.save(model_path)
    print(f"   💾 儲存: {model_path}")

    return {
        'symbol':       symbol,
        'status':       'ok' if is_valid else 'biased',
        'mode':         mode,
        'features':     len(feature_cols),
        'epochs':       ep,
        'samples':      len(X),
        'accuracy':     round(acc, 4),
        'precision':    round(prec, 4),
        'recall':       round(rec, 4),
        'f1':           round(f1, 4),
        'pos_preds':    pos_preds,
        'total_test':   len(pred_b),
        'is_valid':     is_valid
    }


# ─── 主程式 ───────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='LSTM v4 - 法人籌碼特徵')
    parser.add_argument('--stocks', type=str, default='',
                        help='指定股票（逗號分隔）')
    parser.add_argument('--all', action='store_true',
                        help='重訓全部 50 支')
    args = parser.parse_args()

    if args.all:
        stock_list = sorted([f.replace('_model.h5','') for f in
                             os.listdir(MODEL_DIR) if f.endswith('.h5')])
        print(f"\n📋 全部重訓: {len(stock_list)} 支")
    elif args.stocks:
        stock_list = [s.strip() for s in args.stocks.split(',')]
        print(f"\n📋 指定股票: {stock_list}")
    else:
        stock_list = PROBLEM_STOCKS
        print(f"\n📋 問題模型重訓: {len(stock_list)} 支")

    print(f"\n⚙️  配置: SEQ_LEN={SEQ_LEN}, EPOCHS={EPOCHS}, LR={LR}")
    print(f"   技術特徵: {len(TECH_COLS)} 個 | 法人特徵: {len(CHIP_COLS)} 個（若可用）")

    results = []
    total = len(stock_list)
    start_t = datetime.now()

    for i, sym in enumerate(stock_list, 1):
        elapsed = (datetime.now() - start_t).seconds
        eta_per = elapsed / i if i > 1 else 180
        remaining = int(eta_per * (total - i))
        print(f"\n[{i}/{total}] ETA 約 {remaining//60}分{remaining%60}秒")
        result = train_one(sym)
        results.append(result)

    # 統計
    print(f"\n\n{'='*70}")
    print("📊 訓練結果統計")
    print(f"{'='*70}")

    ok  = [r for r in results if r.get('is_valid')]
    bad = [r for r in results if not r.get('is_valid') and r.get('status') not in ('data_error','insufficient_data')]
    err = [r for r in results if r.get('status') in ('data_error','insufficient_data')]

    print(f"\n✅ 合格 ({len(ok)} 支):")
    for r in ok:
        print(f"   {r['symbol']} [{r['mode']}] 準確率={r['accuracy']*100:.1f}% P={r['precision']*100:.1f}% R={r['recall']*100:.1f}% +預測={r['pos_preds']}/{r['total_test']}")

    print(f"\n⚠️  偏差 ({len(bad)} 支):")
    for r in bad:
        print(f"   {r['symbol']}: +預測={r.get('pos_preds',0)}/{r.get('total_test',0)}")

    print(f"\n❌ 錯誤 ({len(err)} 支):")
    for r in err:
        print(f"   {r['symbol']}: {r.get('status','')}")

    # 儲存報告
    elapsed_total = (datetime.now() - start_t).seconds
    report = {
        'train_date': datetime.now().isoformat(),
        'method': 'LSTM_v4_tech+chip',
        'total': len(results),
        'ok': len(ok),
        'elapsed_sec': elapsed_total,
        'results': results
    }
    out_file = f"train_v4_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n⏱️  總耗時: {elapsed_total//60} 分 {elapsed_total%60} 秒")
    print(f"📄 報告: {out_file}")
    print(f"\n{'='*70}")
    print(f"✅ 完成! 合格率: {len(ok)}/{len(results)} ({len(ok)/max(len(results),1)*100:.0f}%)")
    print(f"{'='*70}")
    print(f"\n👉 下一步驗證:")
    print(f"   python3 lstm_backtest.py --threshold 0.5 --period 6m")


if __name__ == '__main__':
    main()
