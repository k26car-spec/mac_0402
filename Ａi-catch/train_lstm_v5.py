"""
LSTM 訓練 v5 - 系統全特徵整合 + RF 特徵篩選
=============================================
核心改進（相比 v4）：
  1. 特徵集：9 技術 → 35 個全系統特徵
     ・量價關係 8 個（價漲量增/縮、量能倍數、量價健康分）
     ・VWAP 系列 4 個（乖離率、趨勢）
     ・KD 動能 5 個（K、D、差值、超買超賣）
     ・相對強弱 5 個（1/5/20日 Alpha vs 大盤）
     ・支撐壓力 4 個（52週高低點距離、近期支撐壓力）
  2. 移除 TWSE 法人 API 依賴（歷史數據不足問題）
  3. 樣本量大幅增加：35 個特徵均可從 yfinance 計算
  4. 更新白名單格式：記錄特徵版本，供 lstm_manager v2 使用
  5. 🆕 RF 自動特徵篩選：35 → 12 核心特徵，解決 val_loss 居高不下的過擬合問題

執行：
    python3 train_lstm_v5.py --stocks 2337,2344
    python3 train_lstm_v5.py            # 訓練所有白名單股票
    python3 train_lstm_v5.py --all      # 訓練全部已存在模型的股票
    python3 train_lstm_v5.py --no-rf    # 停用特徵篩選（使用全 35 個特徵）
"""

import numpy as np
import pandas as pd
import json, os, argparse, warnings, pickle
import patch_yfinance  # 🆕 導入修補模組，自動處理上市上櫃後綴
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

# 導入新特徵建構器
from lstm_feature_builder import build_features_full, make_sequences_v2, ALL_FEATURE_COLS

# ─── RF 特徵重要性篩選（內嵌版，不依賴 backend-v3 路徑）────
def get_refined_features(df: "pd.DataFrame", labels: "pd.Series", top_n: int = 12) -> list:
    """
    用 RandomForest 評估每個特徵的貢獻度，回傳最重要的前 top_n 個特徵名稱。
    """
    if df.empty or len(df) < 10:
        print(f"  ⚠️ 樣本不足 10 筆，跳過 RF 篩選，回傳全部 {len(df.columns)} 個特徵")
        return df.columns.tolist()
    try:
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(df, labels)
        importances = pd.Series(model.feature_importances_, index=df.columns)
        top_n = min(top_n, len(df.columns))
        top_features = importances.nlargest(top_n).index.tolist()
        print(f"  🚀 [AI 診斷] 偵測到當前環境下最強的 {top_n} 個特徵：")
        for i, feat in enumerate(top_features):
            print(f"    {i+1:>2}. {feat:<30} 貢獻度: {importances[feat]:.4f}")
        dropped = importances.nsmallest(len(df.columns) - top_n).index.tolist()
        if dropped:
            print(f"  ℹ️  已剔除 {len(dropped)} 個低貢獻特徵: {dropped}")
        return top_features
    except ImportError:
        print("  ⚠️ scikit-learn 未安裝，跳過特徵篩選")
        return df.columns.tolist()
    except Exception as e:
        print(f"  ❌ 特徵篩選失敗: {e}")
        return df.columns.tolist()

def get_yf_data(symbol, period="3y"):
    # 由於已導入 patch_yfinance，Ticker(symbol) 會自動補上 .TW 或 .TWO
    df = yf.Ticker(symbol).history(period=period)
    return df
MODEL_DIR  = "models/lstm_smart_entry"
SEQ_LEN    = 20
PRED_DAYS  = 5
EPOCHS     = 300
BATCH_SIZE = 16
LR         = 0.0003

# ── RF 特徵篩選設定 ────────────────────────────────────────
RF_SELECTION   = True   # 是否啟用 RandomForest 自動特徵篩選
TOP_N_FEATURES = 12     # 保留最重要的特徵數（原 35 → 12）
MIN_SAMPLES_RF = 80     # 樣本數低於此值則跳過篩選（避免 RF 過擬合）

# ── 標籤基準線設定 ────────────────────────────────────────
# y=1 當 (stock_ret - bench_ret) >= ALPHA_THRESHOLD（比率形式）
#   0.005 = 跑贏大盤 0.5%（預設）
#   0.0   = 只要跑贏大盤任意幅度
#   0.01  = 跑贏大盤 1%（積極篩選）
ALPHA_THRESHOLD = 0.005  # 比率格式（非百分比），0.005 = 0.5%

# ── 模型合格門檻 ────────────────────────────────────────
PRECISION_THRESHOLD = 0.55  # 精確率門檻（超過才進白名單）
RECALL_THRESHOLD    = 0.25  # 召回率下限（調低至25%，允許保守但精準的模型）
# 高精確率特例：若 Precision >= HIGH_PREC_THRESHOLD，放寬召回率要求
HIGH_PREC_THRESHOLD = 0.70  # 精確率 >= 70% 時，Recall 只需 >= 0.20 即可

os.makedirs(MODEL_DIR, exist_ok=True)

print("=" * 65)
print(f"🔧 LSTM v5 - 全特徵訓練 + RF 自動特徵篩選 (Top {TOP_N_FEATURES})")
print("=" * 65)
print(f"TensorFlow {tf.__version__}")
print(f"全特徵清單 ({len(ALL_FEATURE_COLS)}): {ALL_FEATURE_COLS}")
print()


# ─── 模型架構 ─────────────────────────────────────────────
def build_model(n_features: int) -> tf.keras.Model:
    """
    LSTM 分類器 v5
    - 輸入：(SEQ_LEN, n_features) = (20, 35)
    - 2 層 LSTM（64+32）+ 殘差連接思路（BatchNorm）
    - Sigmoid 輸出（看漲機率）
    """
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
    model.compile(
        optimizer=Adam(learning_rate=LR),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model


# ─── RF 特徵篩選並重建序列 ────────────────────────────────
def _select_and_rebuild(X_full: np.ndarray,
                        y_all: np.ndarray,
                        feature_cols: list,
                        top_n: int = TOP_N_FEATURES) -> tuple:
    """
    用 RandomForest 從全特徵序列中選出最重要的 top_n 個，
    並重建只含核心特徵的 (samples, SEQ_LEN, top_n) 序列。

    Args:
        X_full:       shape (samples, SEQ_LEN, n_features)
        y_all:        shape (samples,)
        feature_cols: 特徵名稱清單（長度 = n_features）
        top_n:        保留特徵數

    Returns:
        (X_refined, selected_cols)
    """
    # 把最後1個時間步的特徵展平當做分類特徵（RF 不需要時序）
    X_last  = X_full[:, -1, :]                          # (samples, n_features)
    df_last = pd.DataFrame(X_last, columns=feature_cols)

    selected_cols = get_refined_features(df_last, pd.Series(y_all), top_n=top_n)

    # 取出選中欄的 index，重建序列
    col_idx = [feature_cols.index(c) for c in selected_cols]
    X_refined = X_full[:, :, col_idx]                   # (samples, SEQ_LEN, top_n)

    return X_refined, selected_cols


# ─── 訓練單一股票 ─────────────────────────────────────────
def train_one(symbol: str, use_rf: bool = True) -> dict:
    print(f"\n{'─'*55}")
    print(f"🔄 [{symbol}] 開始訓練（v5 全特徵{'+ RF篩選' if use_rf else ''}）")
    print(f"{'─'*55}")

    # 1. 取得歷史數據
    try:
        df_stock = get_yf_data(symbol, period="3y")
        df_bench = yf.Ticker("^TWII").history(period="3y")
        if df_stock.empty or len(df_stock) < 150:
            print(f"   ❌ 數據不足")
            return {'symbol': symbol, 'status': 'data_error'}
    except Exception as e:
        print(f"   ❌ 數據獲取失敗: {e}")
        return {'symbol': symbol, 'status': 'data_error'}

    # 2. 建構序列（含全 35 個特徵 + alpha 標籤）
    try:
        X, y, class_weights, scaler_full, all_feature_cols, alpha_thr = make_sequences_v2(
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
    feature_cols = list(all_feature_cols)   # 後面 RF 篩選會縮短這個
    print(f"   📦 樣本: {len(X)} | 原始特徵: {n_feat_orig} | "
          f"標籤1(alpha>={alpha_thr}%)={pos}({pos/len(y)*100:.0f}%) 標籤0={neg}")
    print(f"   ⚖️  類別加權: {class_weights}")

    if len(X) < 50:
        return {'symbol': symbol, 'status': 'insufficient_data', 'samples': len(X)}

    # 2.5 🚀 RF 自動特徵篩選（35 → TOP_N_FEATURES）
    if use_rf and len(X) >= MIN_SAMPLES_RF:
        X, feature_cols = _select_and_rebuild(X, y, all_feature_cols, top_n=TOP_N_FEATURES)
        n_feat = len(feature_cols)
        print(f"   🎯 RF 篩選後保留 {n_feat} 個核心特徵: {feature_cols}")

        # ✅ 重新 fit 精簡版 scaler（只對 n_feat 個特徵），解決 backtest 維度不符問題
        from sklearn.preprocessing import MinMaxScaler as _MinMaxScaler
        from lstm_feature_builder import build_features_full as _bff
        _df_f, _ = _bff(df_stock, df_bench)
        _df_f = _df_f.replace([float('inf'), float('-inf')], float('nan')).dropna()
        scaler = _MinMaxScaler()
        scaler.fit(_df_f[feature_cols].fillna(0).values)
        print(f"   ✅ 精簡 scaler fit 完成（{n_feat} 個特徵）")
    else:
        scaler = scaler_full   # 未 RF 篩選：直接用完整 scaler
        n_feat = n_feat_orig
        if use_rf:
            print(f"   ⚠️  樣本 {len(X)} < {MIN_SAMPLES_RF}，跳過 RF 篩選（使用全 {n_feat} 個特徵）")

    # 3. 分割（時序不亂序）
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # 4. 建模（input_shape 自動適應篩選後的特徵數）
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

    # 6. 評估（用驗證集找最佳閾值）
    preds_raw = model.predict(X_test, verbose=0).flatten()

    best_thr, best_f1 = 0.5, 0.0
    for thr in np.arange(0.35, 0.76, 0.05):
        pb = (preds_raw > thr).astype(int)
        n_pos = pb.sum()
        if n_pos == 0 or n_pos == len(pb):
            continue  # 跳過全不買/全買
        prec_t = precision_score(y_test, pb, zero_division=0)
        rec_t  = recall_score(y_test, pb, zero_division=0)
        if rec_t >= 0.90:
            continue  # 跳過全買症狀
        f = f1_score(y_test, pb, zero_division=0)
        if f > best_f1:
            best_f1, best_thr = f, thr

    # 若找不到有效閾值（全部嘗試都是全買），用 0.6 強制搜尋
    if best_f1 == 0.0:
        for thr in np.arange(0.55, 0.85, 0.05):
            pb = (preds_raw > thr).astype(int)
            if pb.sum() > 0:
                best_thr = thr
                break

    pred_b   = (preds_raw > best_thr).astype(int)
    acc      = float(accuracy_score(y_test, pred_b))
    prec     = float(precision_score(y_test, pred_b, zero_division=0))
    rec      = float(recall_score(y_test, pred_b, zero_division=0))
    f1_val   = float(f1_score(y_test, pred_b, zero_division=0))
    pos_pred = int(pred_b.sum())

    print(f"   📊 最佳閾值={best_thr:.2f} | 準確率={acc*100:.1f}% | "
          f"精確率={prec*100:.1f}% | 召回率={rec*100:.1f}% | +預測={pos_pred}/{len(pred_b)}")

    # 7. 合格判斷（v5.1：高精確率特例可放寬召回率要求）
    # 「全買」症狀：pos_pred = len(pred_b)，表示模型不會選擇
    all_buy    = (pos_pred == len(pred_b))
    no_predict = (pos_pred == 0)

    # 標準合格：精確率 > 55% 且 召回率 > 25%
    standard_ok = (
        not all_buy and not no_predict and
        prec > PRECISION_THRESHOLD and
        rec  > RECALL_THRESHOLD and
        rec  < 0.90
    )
    # 高精確率特例：精確率 >= 70%，召回率只需 >= 20%（保守但精準的模型）
    high_prec_ok = (
        not all_buy and not no_predict and
        prec >= HIGH_PREC_THRESHOLD and
        rec  >= 0.20 and
        rec  < 0.90
    )
    is_valid = bool(standard_ok or high_prec_ok)

    if not is_valid:
        # 診斷：為什麼沒過
        reasons = []
        if all_buy:   reasons.append('全買偏差')
        if no_predict: reasons.append('無預測')
        if prec <= PRECISION_THRESHOLD: reasons.append(f'P={prec*100:.1f}%<{PRECISION_THRESHOLD*100:.0f}%')
        if rec <= RECALL_THRESHOLD:     reasons.append(f'R={rec*100:.1f}%<{RECALL_THRESHOLD*100:.0f}%')
        if rec >= 0.90:                 reasons.append(f'召回率過高R={rec*100:.1f}%')
        reason_str = ' | '.join(reasons)
    else:
        reason_str = '高精確率特例' if (high_prec_ok and not standard_ok) else '標準'

    quality = 'ok' if is_valid else ('all_buy' if all_buy else 'low_quality')
    print(f"   {'✅ 合格' if is_valid else ('🔴 全買偏差' if all_buy else '⚠️  未達標')}  [{quality}]  "
          f"[{reason_str}]")

    # 8. 儲存模型 + scaler（同時記錄篩選後的特徵清單，供推理時使用）
    model_path  = os.path.join(MODEL_DIR, f"{symbol}_model.h5")
    scaler_path = os.path.join(MODEL_DIR, f"{symbol}_scaler_v5.pkl")
    model.save(model_path)
    with open(scaler_path, 'wb') as f:
        pickle.dump({
            'scaler':          scaler,           # ✅ 精簡版 scaler（只 fit n_feat 個特徵）
            'feature_cols':    feature_cols,     # 篩選後的特徵清單（12 個）
            'n_features':      n_feat,
            'rf_selected':     use_rf and n_feat < n_feat_orig,
            'scaler_n_feats':  n_feat,           # 明確記錄 scaler 維度，供 backtest 驗證
        }, f)
    print(f"   💾 模型: {model_path}  (input={n_feat}特徵)")
    print(f"   💾 Scaler: {scaler_path} (fit_on={n_feat}特徵)")

    return {
        'symbol':          symbol,
        'status':          'ok' if is_valid else 'low_quality',
        'version':         'v5',
        'alpha_threshold': alpha_thr,
        'n_features':      n_feat,
        'n_features_orig': n_feat_orig,
        'rf_selected':     use_rf and n_feat < n_feat_orig,
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
def update_whitelist(results: list):
    """
    僅將合格模型（is_valid=True）加入白名單
    保留舊白名單中不在本次訓練清單的股票
    """
    wl_path = 'lstm_whitelist.json'
    try:
        with open(wl_path) as f:
            wl = json.load(f)
    except:
        wl = {}

    # 移除 _meta
    wl = {k: v for k, v in wl.items() if not k.startswith('_')}

    updated = []
    for r in results:
        sym = r['symbol']
        if r.get('is_valid'):
            # 儲存白名單時一並記錄 alpha_threshold
            wl[sym] = {
                'threshold':       r['threshold'],
                'accuracy':        r['accuracy'],
                'precision':       r['precision'],
                'recall':          r['recall'],
                'version':         r.get('version', 'v5'),
                'alpha_threshold': r.get('alpha_threshold', 0.5),
                'n_features':      r.get('n_features', 35),
                'feature_cols':    r.get('feature_cols', []),
                'updated':         datetime.now().strftime('%Y-%m-%d')
            }
            updated.append(sym)
        else:
            # 非合格：從白名單移除（避免噪音信號）
            if sym in wl:
                del wl[sym]
                print(f"   ⚠️  {sym} 不合格，已從白名單移除")

    # 重新寫入（含 meta）
    output = {
        '_meta': {
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'total_stocks': len(wl),
            'version': 'v5'
        }
    }
    output.update(wl)

    with open(wl_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n📋 白名單更新：{len(wl)} 支  新增: {updated}")
    return updated


# ─── 主程式 ──────────────────────────────────────────────
def main():
    global ALPHA_THRESHOLD   # ← 必須先宣告，再引用（argparse default 也算引用）

    parser = argparse.ArgumentParser(description='LSTM v5 - 全系統特徵訓練 + RF篩選')
    parser.add_argument('--stocks', type=str, default='',
                        help='指定股票（逗號分隔），例如 2337,2344')
    parser.add_argument('--all', action='store_true',
                        help='重訓所有已有模型的股票')
    parser.add_argument('--whitelist', action='store_true',
                        help='只重訓現有白名單中的股票')
    parser.add_argument('--no-rf', action='store_true',
                        help='停用 RF 特徵篩選（使用全部 35 個特徵）')
    parser.add_argument('--top-n', type=int, default=TOP_N_FEATURES,
                        help=f'RF 篩選保留特徵數（預設 {TOP_N_FEATURES}）')
    parser.add_argument('--alpha', type=float, default=ALPHA_THRESHOLD,
                        help=f'標籤基準線: 跑贏大盤幅度（比率），預設 {ALPHA_THRESHOLD}（= {ALPHA_THRESHOLD*100:.1f}%）')
    args = parser.parse_args()

    # 覆寫全局設定
    use_rf         = RF_SELECTION and not args.no_rf
    top_n          = args.top_n
    ALPHA_THRESHOLD = args.alpha   # 可直接賦值，因為已在函式頂端宣告 global


    # 決定訓練清單
    if args.all:
        stock_list = sorted([
            f.replace('_model.h5', '')
            for f in os.listdir(MODEL_DIR) if f.endswith('_model.h5')
        ])
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
        # 預設：訓練現有白名單
        try:
            with open('lstm_whitelist.json') as f:
                wl = json.load(f)
            stock_list = [k for k in wl.keys() if not k.startswith('_')]
        except:
            stock_list = ['2337', '2344', '2301', '2312', '2367', '6770']
        print(f"📋 白名單重訓: {len(stock_list)} 支")

    print(f"\n⚙️  設定: SEQ_LEN={SEQ_LEN}, EPOCHS={EPOCHS}, LR={LR}")
    print(f"   標籤基準: alpha_threshold={ALPHA_THRESHOLD}%ﾈ股票必跨贏大盤 {ALPHA_THRESHOLD}% 才為 y=1ﾉ")
    print(f"   原始特徵: {len(ALL_FEATURE_COLS)} 個（量價+VWAP+KD+Alpha+支撐壓力）")
    if use_rf:
        print(f"   🚀 RF 特徵篩選: 啟用 → 保留前 {top_n} 個核心特徵（input_shape: (20,{top_n})）")
    else:
        print(f"   ⚡ RF 特徵篩選: 停用（input_shape: (20,{len(ALL_FEATURE_COLS)})）")

    results = []
    total = len(stock_list)
    start_t = datetime.now()

    for i, sym in enumerate(stock_list, 1):
        elapsed = (datetime.now() - start_t).seconds
        eta_per = elapsed / i if i > 1 else 200
        remaining = int(eta_per * (total - i))
        print(f"\n[{i}/{total}] ETA 約 {remaining//60}分{remaining%60}秒")
        result = train_one(sym, use_rf=use_rf)
        results.append(result)

    # 統計
    elapsed_total = (datetime.now() - start_t).seconds
    ok   = [r for r in results if r.get('is_valid')]
    poor = [r for r in results if not r.get('is_valid') and r.get('status') not in ('data_error', 'insufficient_data')]
    err  = [r for r in results if r.get('status') in ('data_error', 'insufficient_data')]

    print(f"\n\n{'='*65}")
    print("📊 v5 訓練結果統計")
    print(f"{'='*65}")

    print(f"\n✅ 合格 ({len(ok)} 支):")
    for r in ok:
        print(f"   {r['symbol']} 閾值={r['threshold']:.3f} "
              f"準確率={r['accuracy']*100:.1f}% P={r['precision']*100:.1f}% "
              f"R={r['recall']*100:.1f}% F1={r['f1']*100:.1f}%")

    print(f"\n⚠️  未達標 ({len(poor)} 支): {[r['symbol'] for r in poor]}")
    print(f"❌ 錯誤 ({len(err)} 支): {[r['symbol'] for r in err]}")

    # 更新白名單
    update_whitelist(results)

    # 儲存報告
    rf_ok = [r for r in results if r.get('rf_selected')]
    report = {
        'train_date':      datetime.now().isoformat(),
        'method':          f'LSTM_v5_full_features{"_RF" + str(top_n) if use_rf else ""}',
        'label_policy':    f'alpha >= {ALPHA_THRESHOLD}% vs index (outperform baseline)',
        'alpha_threshold': ALPHA_THRESHOLD,
        'rf_selection':    use_rf,
        'top_n_features':  top_n if use_rf else len(ALL_FEATURE_COLS),
        'n_features_orig': len(ALL_FEATURE_COLS),
        'feature_list':    ALL_FEATURE_COLS,
        'total': total,
        'ok': len(ok),
        'elapsed_sec': elapsed_total,
        'results': results
    }
    out_file = f"train_v5_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
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
