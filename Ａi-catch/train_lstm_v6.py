"""
LSTM 訓練 v6 - 趨勢股四大類完整特徵
======================================
相比 v5 的核心改進：

1. 使用 lstm_feature_builder_v3：
   - 第1類：多頭排列分數、MA60、MACD柱體擴張、RSI高檔鈍化
   - 第2類：法人買超代理（OBV趨勢、籌碼累積）
   - 第3類：60日相對強度、連勝天數、動量加速
   - 第4類：布林帶突破、族群共振代理、動量加速度

2. 產業分組訓練（CPO/PCB/ABF/HBM/衛星）
   可指定產業批次訓練白名單內的股票

3. 特徵數：v2=34 → v3=55+ 個，RF 篩選至 Top 15

執行：
    python3 train_lstm_v6.py --stocks 2337,2344
    python3 train_lstm_v6.py --industry CPO
    python3 train_lstm_v6.py --all
    python3 train_lstm_v6.py --whitelist   # 重訓白名單
"""

import numpy as np
import pandas as pd
import json, os, argparse, warnings, pickle
warnings.filterwarnings('ignore')
import logging
logging.basicConfig(level=logging.WARNING)

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import yfinance as yf
from datetime import datetime

# ── v3 特徵建構器 ─────────────────────────────────────────
from lstm_feature_builder_v3 import (
    build_features_v3, make_sequences_v3,
    ALL_FEATURE_COLS_V3, INDUSTRY_MAP, get_stock_industries,
    TREND_TECH_COLS, CHIP_COLS, RS_V3_COLS, SECTOR_COLS
)

# ─── RF 特徵重要性篩選 ─────────────────────────────────────
def get_refined_features(df, labels, top_n=15):
    if df.empty or len(df) < 10:
        return df.columns.tolist()
    try:
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(df, labels)
        importances = pd.Series(model.feature_importances_, index=df.columns)
        top_n = min(top_n, len(df.columns))
        top_features = importances.nlargest(top_n).index.tolist()
        print(f"  🚀 [AI 診斷] 最重要 {top_n} 個特徵：")
        for i, feat in enumerate(top_features):
            category = _get_feature_category(feat)
            print(f"    {i+1:>2}. {feat:<30} {importances[feat]:.4f}  {category}")
        return top_features
    except Exception as e:
        print(f"  ⚠️ 特徵篩選失敗: {e}")
        return df.columns.tolist()

def _get_feature_category(feat):
    """識別特徵屬於哪一類"""
    if feat in TREND_TECH_COLS: return '⭐[1類:多頭排列]'
    if feat in CHIP_COLS:       return '🔥[2類:籌碼代理]'
    if feat in RS_V3_COLS:      return '📈[3類:RS升級]'
    if feat in SECTOR_COLS:     return '🎯[4類:族群共振]'
    return '  [基礎特徵]'


# ─── 配置 ─────────────────────────────────────────────────
MODEL_DIR  = "models/lstm_smart_entry"
SEQ_LEN    = 20
PRED_DAYS  = 5
EPOCHS     = 300
BATCH_SIZE = 16
LR         = 0.0003

RF_SELECTION    = True
TOP_N_FEATURES  = 15     # v3：55個特徵 → RF篩選15個（比v5的12多3個）
MIN_SAMPLES_RF  = 80
ALPHA_THRESHOLD = 0.005

# 合格門檻（與 v5.1 一致）
PRECISION_THRESHOLD = 0.55
RECALL_THRESHOLD    = 0.25
HIGH_PREC_THRESHOLD = 0.70

os.makedirs(MODEL_DIR, exist_ok=True)

print("=" * 65)
print(f"🔧 LSTM v6 - 趨勢股四大類完整特徵 (Top {TOP_N_FEATURES})")
print("=" * 65)
print(f"TensorFlow {tf.__version__}")
print(f"v3 全特徵數: {len(ALL_FEATURE_COLS_V3)} 個")
print(f"  ★第1類(多頭排列): {TREND_TECH_COLS}")
print(f"  ★第2類(籌碼代理): {CHIP_COLS}")
print(f"  ★第3類(RS升級)  : {RS_V3_COLS}")
print(f"  ★第4類(族群共振): {SECTOR_COLS}")
print()


# ─── 模型架構 ─────────────────────────────────────────────
def build_model(n_features):
    model = Sequential([
        LSTM(64, return_sequences=True,
             input_shape=(SEQ_LEN, n_features),
             dropout=0.2, recurrent_dropout=0.05),
        BatchNormalization(),
        LSTM(32, return_sequences=False,
             dropout=0.2, recurrent_dropout=0.05),
        BatchNormalization(),
        Dropout(0.2),
        Dense(16, activation='relu'),
        Dropout(0.15),
        Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer=Adam(learning_rate=LR),
                  loss='binary_crossentropy', metrics=['accuracy'])
    return model


# ─── RF 特徵篩選並重建序列 ────────────────────────────────
def _select_and_rebuild(X_full, y_all, feature_cols, top_n=TOP_N_FEATURES):
    X_last  = X_full[:, -1, :]
    df_last = pd.DataFrame(X_last, columns=feature_cols)
    selected_cols = get_refined_features(df_last, pd.Series(y_all), top_n=top_n)
    col_idx = [feature_cols.index(c) for c in selected_cols]
    X_refined = X_full[:, :, col_idx]
    return X_refined, selected_cols


# ─── 訓練單一股票 ─────────────────────────────────────────
def train_one(symbol: str, use_rf: bool = True) -> dict:
    print(f"\n{'─'*55}")
    print(f"🔄 [{symbol}] 開始訓練（v6 四大類特徵）")
    industries = get_stock_industries(symbol)
    if industries:
        print(f"   📌 產業分類: {industries}")
    print(f"{'─'*55}")

    # 1. 取得歷史數據
    try:
        df_stock = yf.Ticker(f"{symbol}.TW").history(period="3y")
        df_bench = yf.Ticker("^TWII").history(period="3y")
        if df_stock.empty or len(df_stock) < 150:
            print(f"   ❌ 數據不足")
            return {'symbol': symbol, 'status': 'data_error'}
    except Exception as e:
        print(f"   ❌ 數據獲取失敗: {e}")
        return {'symbol': symbol, 'status': 'data_error'}

    # 2. 建構 v3 序列
    try:
        X, y, class_weights, scaler_full, all_feature_cols, alpha_thr = make_sequences_v3(
            df_stock, df_bench,
            seq_len=SEQ_LEN,
            pred_days=PRED_DAYS,
            alpha_threshold=ALPHA_THRESHOLD,
        )
    except ValueError as e:
        print(f"   ❌ 序列建構失敗: {e}")
        return {'symbol': symbol, 'status': 'insufficient_data'}

    pos = int(y.sum())
    neg = len(y) - pos
    n_feat_orig = len(all_feature_cols)
    feature_cols = list(all_feature_cols)
    print(f"   📦 樣本: {len(X)} | 原始特徵: {n_feat_orig} | "
          f"標籤1={pos}({pos/len(y)*100:.0f}%) 標籤0={neg}")

    if len(X) < 50:
        return {'symbol': symbol, 'status': 'insufficient_data', 'samples': len(X)}

    # 2.5 RF 特徵篩選（v3 特徵 → Top 15）
    if use_rf and len(X) >= MIN_SAMPLES_RF:
        X, feature_cols = _select_and_rebuild(X, y, all_feature_cols, top_n=TOP_N_FEATURES)
        n_feat = len(feature_cols)
        print(f"   🎯 RF 篩選後保留 {n_feat} 個核心特徵")

        # ✅ 重新 fit 精簡版 scaler（只對篩選後特徵）
        from sklearn.preprocessing import MinMaxScaler as _MS
        _df_f, _ = build_features_v3(df_stock, df_bench)
        _df_f = _df_f.replace([float('inf'), float('-inf')], float('nan')).dropna()
        scaler = _MS()
        scaler.fit(_df_f[feature_cols].fillna(0).values)
        print(f"   ✅ 精簡 scaler fit 完成（{n_feat} 個特徵）")
    else:
        scaler = scaler_full
        n_feat = n_feat_orig
        if use_rf:
            print(f"   ⚠️  樣本不足，跳過 RF 篩選（使用全 {n_feat} 個特徵）")

    # 3. 分割
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # 4. 建模
    model = build_model(n_feat)
    print(f"   🏗️  參數數: {model.count_params():,}")

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
    print(f"   ✓ {ep} epochs | "
          f"loss={history.history['loss'][-1]:.4f} | "
          f"val_loss={history.history['val_loss'][-1]:.4f}")

    # 6. 評估
    preds_raw = model.predict(X_test, verbose=0).flatten()

    best_thr, best_f1 = 0.5, 0.0
    for thr in np.arange(0.35, 0.76, 0.05):
        pb = (preds_raw > thr).astype(int)
        n_pos = pb.sum()
        if n_pos == 0 or n_pos == len(pb):
            continue
        prec_t = precision_score(y_test, pb, zero_division=0)
        rec_t  = recall_score(y_test, pb, zero_division=0)
        if rec_t >= 0.90:
            continue
        f = f1_score(y_test, pb, zero_division=0)
        if f > best_f1:
            best_f1, best_thr = f, thr

    if best_f1 == 0.0:
        for thr in np.arange(0.55, 0.85, 0.05):
            pb = (preds_raw > thr).astype(int)
            if pb.sum() > 0:
                best_thr = thr
                break

    pred_b  = (preds_raw > best_thr).astype(int)
    acc     = float(accuracy_score(y_test, pred_b))
    prec    = float(precision_score(y_test, pred_b, zero_division=0))
    rec     = float(recall_score(y_test, pred_b, zero_division=0))
    f1_val  = float(f1_score(y_test, pred_b, zero_division=0))
    pos_pred = int(pred_b.sum())

    print(f"   📊 最佳閾值={best_thr:.2f} | 準確率={acc*100:.1f}% | "
          f"精確率={prec*100:.1f}% | 召回率={rec*100:.1f}% | +預測={pos_pred}/{len(pred_b)}")

    # 7. 合格判斷
    all_buy    = (pos_pred == len(pred_b))
    no_predict = (pos_pred == 0)
    standard_ok = (not all_buy and not no_predict and
                   prec > PRECISION_THRESHOLD and
                   rec  > RECALL_THRESHOLD and
                   rec  < 0.90)
    high_prec_ok = (not all_buy and not no_predict and
                    prec >= HIGH_PREC_THRESHOLD and
                    rec  >= 0.20 and rec < 0.90)
    is_valid = bool(standard_ok or high_prec_ok)

    if not is_valid:
        reasons = []
        if all_buy:    reasons.append('全買偏差')
        if no_predict: reasons.append('無預測')
        if prec <= PRECISION_THRESHOLD: reasons.append(f'P={prec*100:.1f}%<{PRECISION_THRESHOLD*100:.0f}%')
        if rec  <= RECALL_THRESHOLD:    reasons.append(f'R={rec*100:.1f}%<{RECALL_THRESHOLD*100:.0f}%')
        if rec  >= 0.90:                reasons.append(f'召回率過高R={rec*100:.1f}%')
        reason_str = ' | '.join(reasons)
    else:
        reason_str = '高精確率特例' if (high_prec_ok and not standard_ok) else '標準'

    quality = 'ok' if is_valid else ('all_buy' if all_buy else 'low_quality')
    print(f"   {'✅ 合格' if is_valid else ('🔴 全買偏差' if all_buy else '⚠️  未達標')}  "
          f"[{quality}]  [{reason_str}]")

    # 8. 儲存
    model_path  = os.path.join(MODEL_DIR, f"{symbol}_model.h5")
    scaler_path = os.path.join(MODEL_DIR, f"{symbol}_scaler_v5.pkl")   # 保持相同路徑供 backtest 使用
    model.save(model_path)
    with open(scaler_path, 'wb') as f:
        pickle.dump({
            'scaler':         scaler,
            'feature_cols':   feature_cols,
            'n_features':     n_feat,
            'rf_selected':    use_rf and n_feat < n_feat_orig,
            'scaler_n_feats': n_feat,
            'version':        'v6',                   # 標記版本
        }, f)
    print(f"   💾 模型: {model_path}  (v6, {n_feat}特徵)")

    return {
        'symbol':          symbol,
        'status':          'ok' if is_valid else 'low_quality',
        'version':         'v6',
        'industries':      industries,
        'alpha_threshold': alpha_thr,
        'n_features':      n_feat,
        'n_features_orig': n_feat_orig,
        'feature_cols':    feature_cols,
        'threshold':       round(best_thr, 4),
        'accuracy':        round(acc, 4),
        'precision':       round(prec, 4),
        'recall':          round(rec, 4),
        'f1':              round(f1_val, 4),
        'pos_preds':       pos_pred,
        'total_test':      len(pred_b),
        'samples':         len(X),
        'epochs':          ep,
        'is_valid':        is_valid
    }


# ─── 更新白名單 ───────────────────────────────────────────
def update_whitelist(results):
    wl_path = 'lstm_whitelist.json'
    try:
        with open(wl_path) as f:
            wl = json.load(f)
    except:
        wl = {}
    wl = {k: v for k, v in wl.items() if not k.startswith('_')}

    updated = []
    for r in results:
        sym = r['symbol']
        if r.get('is_valid'):
            wl[sym] = {
                'threshold':    r['threshold'],
                'accuracy':     r['accuracy'],
                'precision':    r['precision'],
                'recall':       r['recall'],
                'version':      r.get('version', 'v6'),
                'industries':   r.get('industries', []),
                'n_features':   r.get('n_features', 15),
                'feature_cols': r.get('feature_cols', []),
                'updated':      datetime.now().strftime('%Y-%m-%d')
            }
            updated.append(sym)
        else:
            if sym in wl:
                del wl[sym]
                print(f"   ⚠️  {sym} 不合格，已從白名單移除")

    output = {
        '_meta': {
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'total_stocks': len(wl),
            'version': 'v6'
        }
    }
    output.update(wl)
    with open(wl_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n📋 白名單更新：{len(wl)} 支  新增: {updated}")
    return updated


# ─── 主程式 ──────────────────────────────────────────────
def main():
    global ALPHA_THRESHOLD

    parser = argparse.ArgumentParser(description='LSTM v6 - 趨勢股四大類特徵訓練')
    parser.add_argument('--stocks', type=str, default='')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--whitelist', action='store_true')
    parser.add_argument('--industry', type=str, default='',
                        help=f'指定產業: {list(INDUSTRY_MAP.keys())}')
    parser.add_argument('--no-rf', action='store_true')
    parser.add_argument('--top-n', type=int, default=TOP_N_FEATURES)
    parser.add_argument('--alpha', type=float, default=ALPHA_THRESHOLD)
    args = parser.parse_args()

    use_rf = RF_SELECTION and not args.no_rf
    top_n  = args.top_n
    ALPHA_THRESHOLD = args.alpha

    # 決定訓練清單
    if args.industry:
        ind = args.industry.upper()
        if ind not in INDUSTRY_MAP:
            print(f"❌ 未知產業 {ind}，可選: {list(INDUSTRY_MAP.keys())}")
            return
        stock_list = INDUSTRY_MAP[ind]
        print(f"📋 產業訓練 [{ind}]: {stock_list}")
    elif args.all:
        stock_list = sorted([f.replace('_model.h5', '')
                             for f in os.listdir(MODEL_DIR) if f.endswith('_model.h5')])
        print(f"📋 全部重訓: {len(stock_list)} 支")
    elif args.whitelist:
        with open('lstm_whitelist.json') as f:
            wl = json.load(f)
        stock_list = [k for k in wl.keys() if not k.startswith('_')]
        print(f"📋 白名單重訓: {len(stock_list)} 支")
    elif args.stocks:
        stock_list = [s.strip() for s in args.stocks.split(',')]
        print(f"📋 指定股票: {stock_list}")
    else:
        # 預設：核心趨勢股
        stock_list = ['2330', '2454', '2317', '2337', '2344', '6770',
                      '3037', '2383', '4256', '3706', '2382', '2408']
        print(f"📋 預設核心趨勢股: {stock_list}")

    print(f"\n⚙️  設定: SEQ={SEQ_LEN}, EPOCHS={EPOCHS}, LR={LR}")
    print(f"   特徵版本: v3 ({len(ALL_FEATURE_COLS_V3)} 個) → RF → Top {top_n}")
    print(f"   Alpha閾值: {ALPHA_THRESHOLD} ({ALPHA_THRESHOLD*100:.1f}% 跑贏大盤)")
    print()

    results = []
    start_t = datetime.now()
    total = len(stock_list)

    for i, sym in enumerate(stock_list, 1):
        elapsed = (datetime.now() - start_t).seconds
        eta_per = elapsed / i if i > 1 else 200
        remaining = int(eta_per * (total - i))
        print(f"\n[{i}/{total}] ETA 約 {remaining//60}分{remaining%60}秒")
        result = train_one(sym, use_rf=use_rf)
        results.append(result)

    elapsed_total = (datetime.now() - start_t).seconds
    ok   = [r for r in results if r.get('is_valid')]
    poor = [r for r in results if not r.get('is_valid') and r.get('status') not in ('data_error', 'insufficient_data')]
    err  = [r for r in results if r.get('status') in ('data_error', 'insufficient_data')]

    print(f"\n\n{'='*65}")
    print("📊 v6 訓練結果統計")
    print(f"{'='*65}")

    print(f"\n✅ 合格 ({len(ok)} 支):")
    for r in ok:
        ind_str = f" {r.get('industries', [])}" if r.get('industries') else ''
        print(f"   {r['symbol']}{ind_str}  閾值={r['threshold']:.3f}  "
              f"P={r['precision']*100:.1f}%  R={r['recall']*100:.1f}%  F1={r['f1']*100:.1f}%")

    print(f"\n⚠️  未達標 ({len(poor)} 支): {[r['symbol'] for r in poor]}")
    print(f"❌ 錯誤 ({len(err)} 支): {[r['symbol'] for r in err]}")

    update_whitelist(results)

    report = {
        'train_date':     datetime.now().isoformat(),
        'method':         f'LSTM_v6_trend4class_RF{top_n}',
        'feature_count':  len(ALL_FEATURE_COLS_V3),
        'top_n_features': top_n,
        'alpha_threshold': ALPHA_THRESHOLD,
        'total': total, 'ok': len(ok),
        'elapsed_sec': elapsed_total,
        'results': results
    }
    out_file = f"train_v6_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n⏱️  總耗時: {elapsed_total//60} 分 {elapsed_total%60} 秒")
    print(f"📄 報告: {out_file}")
    print(f"\n{'='*65}")
    print(f"✅ 完成! 合格率: {len(ok)}/{total} ({len(ok)/max(total,1)*100:.0f}%)")
    print(f"{'='*65}")
    print(f"\n👉 下一步:")
    print(f"   python3 lstm_backtest.py --threshold auto --period 3m")


if __name__ == '__main__':
    main()
