"""
LSTM 白名單自動擴充工具
========================
流程：
  1. 讀取 ORB 強勢股清單（data/orb_watchlist.json）
  2. 過濾掉已在白名單的股票（不重複訓練）
  3. 對每支股票訓練 LSTM v5 模型
  4. 執行 3 個月回測（相對大盤 Alpha）
  5. 符合條件的自動加入白名單：
       ・精確率 ≥ 55%
       ・超額報酬 > 0%
       ・不是全買（召回率 < 90%）
       ・有足夠訓練樣本（≥ 50）

執行：
    python3 lstm_auto_expand.py               # 掃描全部 ORB 強勢股
    python3 lstm_auto_expand.py --dry-run     # 只顯示，不修改白名單
    python3 lstm_auto_expand.py --force       # 包含白名單已有的股票也重訓
"""

import sys, os, json, pickle, warnings, argparse
import numpy as np
import pandas as pd
import yfinance as yf
import patch_yfinance  # 🆕 導入修補模組
from datetime import datetime
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.preprocessing import MinMaxScaler
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# 路徑常數
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR  = os.path.join(BASE_DIR, "models/lstm_smart_entry")
WL_PATH    = os.path.join(BASE_DIR, "lstm_whitelist.json")
ORB_PATH   = os.path.join(BASE_DIR, "data/orb_watchlist.json")

# 合格門檻
MIN_PRECISION = 0.55   # 精確率 ≥ 55%
MIN_ALPHA     = 0.0    # 超額報酬要正
MAX_RECALL    = 0.90   # 召回率 < 90%（防全買）
MIN_SAMPLES   = 50     # 最少樣本數

os.makedirs(MODEL_DIR, exist_ok=True)


# ─── 工具函數 ─────────────────────────────────────────────

def load_whitelist() -> dict:
    try:
        with open(WL_PATH) as f:
            wl = json.load(f)
        return {k: v for k, v in wl.items() if not k.startswith('_')}
    except:
        return {}


def save_whitelist(stocks: dict):
    output = {
        '_meta': {
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'total_stocks': len(stocks),
            'version': 'v5',
            'source': 'lstm_auto_expand'
        }
    }
    output.update(stocks)
    with open(WL_PATH, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)


def load_orb_stocks() -> list:
    """讀取 ORB 強勢股清單"""
    try:
        with open(ORB_PATH) as f:
            d = json.load(f)
        stocks = d.get('watchlist', [])
        print(f"📋 ORB 強勢股：{len(stocks)} 支（更新：{d.get('updated_at','?')}）")
        return [str(s) for s in stocks]
    except Exception as e:
        print(f"❌ 無法讀取 ORB 清單: {e}")
        return []


def strip_tz(idx):
    if hasattr(idx, 'tz') and idx.tz is not None:
        return idx.tz_localize(None)
    return idx


# 上櫃股票快取（避免重複探測）
_OTC_CACHE: dict = {}   # symbol -> 'TW' | 'TWO'

def get_yf_data(symbol: str, period: str = "3y") -> pd.DataFrame:
    """
    智能取得台灣股票 yfinance 資料。
    先嘗試原始代碼，若無資料且未包含 .TWO，嘗試補上 .TWO 再次查詢。
    捕獲 yfinance 拋出的錯誤 (如 too many values to unpack)。
    """
    import pandas as pd
    try:
        # 如果已帶後綴，直接查
        if symbol.endswith('.TW') or symbol.endswith('.TWO'):
            df = yf.Ticker(symbol).history(period=period)
        else:
            # 先試 .TW
            sym_tw = f"{symbol}.TW"
            df = yf.Ticker(sym_tw).history(period=period)
            if df.empty:
                # 嘗試 .TWO
                sym_two = f"{symbol}.TWO"
                df = yf.Ticker(sym_two).history(period=period)
                if not df.empty:
                    print(f"  ℹ️  {symbol} 為上櫃股票，使用 .TWO 後綴")
                    _OTC_CACHE[symbol] = 'TWO'
                    
        if df.empty:
            print(f"  ⚠️  {symbol} 無法取得資料（可能已下市或停止交易）")
            return pd.DataFrame()
            
        return df
    except Exception as e:
        print(f"  ⚠️  {symbol} yfinance 查詢失敗: {e}")
        return pd.DataFrame()




def get_refined_features(df, labels, top_n=12):
    """
    輸入：原始全量特徵的 DataFrame 與 漲跌標籤
    輸出：貢獻度前 N 名的特徵清單（由 RandomForest 診斷）
    """
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(df, labels)
    importances = pd.Series(model.feature_importances_, index=df.columns)
    top_features = importances.nlargest(top_n).index.tolist()
    print(f"🚀 [AI 診斷] 偵測到當前環境下最強的 {top_n} 個特徵：")
    for i, feat in enumerate(top_features):
        print(f"  {i+1}. {feat} ({importances[feat]:.4f})")
    return top_features


def train_one(symbol: str, df_bench: pd.DataFrame) -> dict:
    """訓練單支股票 v5 模型（整合 RF 自動特徵篩選）"""
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from lstm_feature_builder import make_sequences_v2

    SEQ_LEN = 20
    try:
        # 自動辨識上市/上櫃（8155, 8074, 3163 等上櫃股票需 .TWO）
        df_stock = get_yf_data(symbol, period="3y")
        if df_stock.empty or len(df_stock) < 150:
            return {'status': 'data_error'}

        # ✅ 修正：接收 6 個回傳值（含 alpha_threshold）
        X, y, class_weights, scaler, feature_cols, alpha_thr = make_sequences_v2(
            df_stock, df_bench, seq_len=SEQ_LEN, pred_days=5
        )
        if len(X) < MIN_SAMPLES:
            return {'status': 'insufficient_data', 'samples': len(X)}

        # ✅ RF 動態特徵篩選（從 35 個特徵挑選最強 12 個）
        n_seq, seq, n_all_feat = X.shape
        X_flat = X.reshape(n_seq, seq * n_all_feat)   # 攤平成 2D 給 RF
        # 用特徵「最後一步」作為簡易輸入（計算量小、速度快）
        X_last = X[:, -1, :]   # shape (n_seq, n_all_feat)
        top_feat_names = get_refined_features(
            pd.DataFrame(X_last, columns=feature_cols), pd.Series(y), top_n=12
        )
        top_feat_idx = [feature_cols.index(f) for f in top_feat_names]
        X = X[:, :, top_feat_idx]   # 只保留篩選後的特徵維度
        n_feat = len(top_feat_names)
        print(f"  📊 特徵縮減: {len(feature_cols)} → {n_feat} 個")

        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        model = Sequential([
            LSTM(64, return_sequences=True,
                 input_shape=(SEQ_LEN, n_feat),
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
        model.compile(optimizer=Adam(0.0003),
                      loss='binary_crossentropy', metrics=['accuracy'])

        callbacks = [
            EarlyStopping(monitor='val_loss', patience=35,
                          restore_best_weights=True, verbose=0),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5,
                              patience=10, min_lr=1e-6, verbose=0)
        ]
        model.fit(X_train, y_train, epochs=300, batch_size=16,
                  validation_split=0.2, class_weight=class_weights,
                  callbacks=callbacks, verbose=0)

        # 搜尋最佳閾值（排除全買）
        preds = model.predict(X_test, verbose=0).flatten()
        best_thr, best_f1 = 0.5, 0.0
        for thr in np.arange(0.35, 0.80, 0.05):
            pb = (preds > thr).astype(int)
            n_pos = pb.sum()
            if n_pos == 0 or n_pos == len(pb): continue
            rec_t = recall_score(y_test, pb, zero_division=0)
            if rec_t >= MAX_RECALL: continue
            f = f1_score(y_test, pb, zero_division=0)
            if f > best_f1:
                best_f1, best_thr = f, thr

        pb_final  = (preds > best_thr).astype(int)
        prec_val  = float(precision_score(y_test, pb_final, zero_division=0))
        rec_val   = float(recall_score(y_test, pb_final, zero_division=0))
        f1_val    = float(f1_score(y_test, pb_final, zero_division=0))
        n_pos     = int(pb_final.sum())

        # ✅ 重新 fit 精簡版 scaler（只對 n_feat 個特徵）
        from lstm_feature_builder import build_features_full as _bff
        _df_f, _ = _bff(df_stock, df_bench)
        _df_f = _df_f.replace([float('inf'), float('-inf')], float('nan')).dropna()
        scaler_new = MinMaxScaler()
        scaler_new.fit(_df_f[top_feat_names].fillna(0).values)
        print(f"  ✅ 精簡 scaler fit 完成（{n_feat} 個特徵）")

        # 儲存
        model.save(os.path.join(MODEL_DIR, f"{symbol}_model.h5"))
        with open(os.path.join(MODEL_DIR, f"{symbol}_scaler_v5.pkl"), 'wb') as f:
            pickle.dump({
                'scaler': scaler_new,
                'feature_cols': top_feat_names,
                'top_feat_names': top_feat_names,
                'version': 'v5'
            }, f)

        return {
            'status':         'ok',
            'samples':        len(X),
            'threshold':      round(best_thr, 4),
            'precision':      round(prec_val, 4),
            'recall':         round(rec_val, 4),
            'f1':             round(f1_val, 4),
            'pos_preds':      n_pos,
            'total_test':     len(y_test),
            'feature_cols':   top_feat_names,       # 回傳篩選後的特徵
            'alpha_threshold': alpha_thr,
        }

    except ValueError as e:
        return {'status': 'insufficient_data', 'error': str(e)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)[:80]}



# ─── 回測（3 個月，相對大盤 Alpha）─────────────────────────

def backtest_3m(symbol: str, threshold: float,
                df_bench: pd.DataFrame) -> dict | None:
    """3 個月回測，返回精確率 & 超額報酬"""
    from tensorflow.keras.models import load_model

    SEQ_LEN = 20
    try:
        # 自動辨識上市/上櫃
        df = get_yf_data(symbol, period="8mo")
        if df.empty or len(df) < 100:
            return None

        scaler_path = os.path.join(MODEL_DIR, f"{symbol}_scaler_v5.pkl")
        if not os.path.exists(scaler_path):
            return None
        with open(scaler_path, 'rb') as f:
            saved = pickle.load(f)
        scaler       = saved['scaler']
        feature_cols = saved['feature_cols']
        top_feat_names = saved.get('top_feat_names', feature_cols)  # 相容舊格式
        model_ver    = saved.get('version', 'v5')

        model = load_model(os.path.join(MODEL_DIR, f"{symbol}_model.h5"),
                           compile=False)

        # ─── 依版本選擇特徵建構器 ───────────────────────────
        if model_ver == 'v6':
            from lstm_feature_builder_v3 import build_features_v3
            df_feat, all_cols = build_features_v3(df, df_bench)
        else:
            from lstm_feature_builder import build_features_full
            df_feat, all_cols = build_features_full(df, df_bench)
        if len(df_feat) < SEQ_LEN + 10:
            return None

        # 標籤
        bench_s = df_bench['Close'].copy()
        bench_s.index = strip_tz(pd.to_datetime(bench_s.index))
        stock_s = df['Close'].copy()
        stock_s.index = strip_tz(pd.to_datetime(stock_s.index))
        bench_a = bench_s.reindex(df_feat.index, method='ffill')
        stock_a = stock_s.reindex(df_feat.index, method='ffill')
        alpha_vals = ((stock_a.pct_change(5) - bench_a.pct_change(5)) * 100).shift(-5)

        df_feat = df_feat.copy()
        df_feat['alpha'] = alpha_vals
        df_feat = df_feat.dropna(subset=['alpha'])
        if len(df_feat) < SEQ_LEN + 5:
            return None

        X_raw = df_feat[feature_cols].fillna(0).values
        X_sc  = scaler.transform(X_raw)

        # 取出訓練時篩選的特徵索引（與訓練對齊）
        top_feat_idx = [feature_cols.index(f) for f in top_feat_names if f in feature_cols]
        X_sc_sel = X_sc[:, top_feat_idx]  # 切片至篩選特徵

        X, y, alphas = [], [], []
        for i in range(len(df_feat) - SEQ_LEN):
            X.append(X_sc_sel[i:i + SEQ_LEN])
            a = df_feat['alpha'].iloc[i + SEQ_LEN]
            y.append(1 if a > 0 else 0)
            alphas.append(a)

        X, y = np.array(X), np.array(y)
        alphas = np.array(alphas)


        # 最近 60 個交易日（約 3 個月）
        n = min(60, len(X))
        X_t, y_t, a_t = X[-n:], y[-n:], alphas[-n:]

        preds = model.predict(X_t, verbose=0).flatten()
        pb    = (preds > threshold).astype(int)
        traded = a_t[pb == 1]
        avg_alpha = float(np.mean(traded)) if len(traded) > 0 else 0.0

        return {
            'precision':  float(precision_score(y_t, pb, zero_division=0)),
            'recall':     float(recall_score(y_t, pb, zero_division=0)),
            'f1':         float(f1_score(y_t, pb, zero_division=0)),
            'avg_alpha':  round(avg_alpha, 3),
            'pos_preds':  int(pb.sum()),
            'samples':    n,
        }
    except Exception as e:
        return None


# ─── 主程式 ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='LSTM 白名單自動擴充')
    parser.add_argument('--dry-run', action='store_true',
                        help='只顯示結果，不修改白名單')
    parser.add_argument('--force', action='store_true',
                        help='包含白名單已有的股票也重新訓練')
    parser.add_argument('--skip-train', action='store_true',
                        help='跳過訓練，只對已有模型做回測')
    args = parser.parse_args()

    print("=" * 65)
    print("🔍 LSTM 白名單自動擴充（ORB 強勢股）")
    print("=" * 65)
    if args.dry_run:
        print("⚠️  DRY-RUN 模式：不修改白名單\n")

    # 讀取清單
    orb_stocks = load_orb_stocks()
    if not orb_stocks:
        return

    whitelist = load_whitelist()
    print(f"📋 現有白名單：{list(whitelist.keys())}")

    # 決定要處理的股票
    if args.force:
        to_process = orb_stocks
    else:
        to_process = [s for s in orb_stocks if s not in whitelist]

    already_in = [s for s in orb_stocks if s in whitelist]
    print(f"\n✅ 已在白名單（跳過）：{already_in}")
    print(f"🔄 待處理：{len(to_process)} 支 → {to_process}\n")

    if not to_process:
        print("🎉 所有 ORB 強勢股都已在白名單！")
        return

    # 預載大盤
    print("📡 載入大盤數據...")
    bench_df = yf.Ticker("^TWII").history(period="3y")
    bench_df.index = strip_tz(pd.to_datetime(bench_df.index))

    # 逐支處理
    added, skipped, failed = [], [], []
    total = len(to_process)
    start_t = datetime.now()

    for i, sym in enumerate(to_process, 1):
        elapsed = (datetime.now() - start_t).seconds
        eta = int(elapsed / i * (total - i)) if i > 1 else 0
        print(f"\n[{i}/{total}] {sym}  ETA: {eta//60}分{eta%60}秒")
        print(f"{'─'*50}")

        has_model = os.path.exists(os.path.join(MODEL_DIR, f"{sym}_model.h5"))
        has_scaler_v5 = os.path.exists(os.path.join(MODEL_DIR, f"{sym}_scaler_v5.pkl"))

        # Step 1: 訓練（若無 v5 模型）
        if not args.skip_train and not (has_model and has_scaler_v5):
            print(f"  🚀 訓練 {sym}（無 v5 模型）...")
            train_result = train_one(sym, bench_df)
            print(f"  訓練結果: {train_result.get('status')} "
                  f"P={train_result.get('precision',0)*100:.1f}% "
                  f"n={train_result.get('samples','?')}")
            if train_result['status'] not in ('ok',):
                print(f"  ❌ 訓練失敗: {train_result.get('error','')}")
                failed.append({'symbol': sym, 'reason': train_result['status']})
                continue
            threshold = train_result.get('threshold', 0.5)
        elif has_scaler_v5:
            # 已有 v5 scaler → 從 whitelist 或預設值取閾值
            threshold = whitelist.get(sym, {}).get('threshold', 0.5)
            print(f"  ♻️  使用現有 v5 模型  thr={threshold:.3f}")
        else:
            print(f"  ⚠️  無 v5 模型且跳過訓練，略過")
            skipped.append(sym)
            continue

        # Step 2: 3 個月回測
        print(f"  📊 回測中（3m）...")
        bt = backtest_3m(sym, threshold, bench_df)
        if bt is None:
            print(f"  ❌ 回測失敗")
            failed.append({'symbol': sym, 'reason': 'backtest_failed'})
            continue

        prec  = bt['precision']
        rec   = bt['recall']
        alpha = bt['avg_alpha']
        n_pos = bt['pos_preds']
        n_tot = bt['samples']

        print(f"  結果: P={prec*100:.1f}%  R={rec*100:.1f}%  "
              f"alpha={alpha:+.2f}%  +={n_pos}/{n_tot}")

        # Step 3: 合格判斷
        is_qualified = (
            prec >= MIN_PRECISION and
            alpha > MIN_ALPHA and
            rec < MAX_RECALL and
            n_pos > 0 and n_pos < n_tot
        )

        if is_qualified:
            print(f"  ✅ 合格！加入白名單")
            entry = {
                'threshold':  threshold,
                'precision':  round(prec, 4),
                'recall':     round(rec, 4),
                'f1':         round(bt['f1'], 4),
                'avg_alpha':  alpha,
                'version':    'v5',
                'source':     'orb_auto_expand',
                'updated':    datetime.now().strftime('%Y-%m-%d'),
            }
            added.append({'symbol': sym, **entry})
            if not args.dry_run:
                whitelist[sym] = entry
        else:
            reasons = []
            if prec < MIN_PRECISION: reasons.append(f"P={prec*100:.1f}%<{MIN_PRECISION*100:.0f}%")
            if alpha <= MIN_ALPHA:   reasons.append(f"alpha={alpha:+.2f}%≤0")
            if rec >= MAX_RECALL:    reasons.append(
                f"R={rec*100:.1f}%≥90%（全買警告：模型對此股可能 Overfitting，閾值過低）"
            )
            if n_pos == 0:           reasons.append("無買進預測")
            print(f"  ⚠️  不合格: {', '.join(reasons)}")
            if rec >= MAX_RECALL:
                print(f"      💡 全買建議：此股 ({sym}) LSTM 預測幾乎每天買入，")
                print(f"         表示模型失效（可嘗試更嚴格的特徵工程或更長訓練期）")
            skipped.append(sym)

    # 儲存白名單
    if added and not args.dry_run:
        save_whitelist(whitelist)

    # 最終報告
    elapsed_total = (datetime.now() - start_t).seconds
    print(f"\n\n{'═'*65}")
    print(f"📊 擴充結果總覽")
    print(f"{'═'*65}")
    print(f"⏱️  耗時: {elapsed_total//60}分{elapsed_total%60}秒")
    print(f"\n✅ 新增白名單 ({len(added)} 支):")
    for r in sorted(added, key=lambda x: -x['precision']):
        print(f"   ⭐ {r['symbol']}  P={r['precision']*100:.1f}%  "
              f"alpha={r['avg_alpha']:+.2f}%  thr={r['threshold']:.3f}")

    print(f"\n⚠️  不合格/已跳過 ({len(skipped)} 支): {skipped}")
    print(f"❌ 失敗 ({len(failed)} 支): {[r['symbol'] for r in failed]}")

    if not args.dry_run:
        final_wl = load_whitelist()
        print(f"\n📋 白名單最終 ({len(final_wl)} 支):")
        for k, v in sorted(final_wl.items(),
                           key=lambda x: -x[1].get('precision', 0)):
            src = '🆕' if v.get('source') == 'orb_auto_expand' else '  '
            print(f"   {src} {k}  P={v.get('precision',0)*100:.1f}%  "
                  f"thr={v['threshold']:.3f}  alpha={v.get('avg_alpha',0):+.2f}%")

    # 儲存報告
    report = {
        'run_date': datetime.now().isoformat(),
        'orb_stocks': orb_stocks,
        'processed': to_process,
        'added': added,
        'skipped': skipped,
        'failed': failed,
        'elapsed_sec': elapsed_total,
    }
    fname = f"orb_expand_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n📄 報告: {fname}")
    print(f"{'═'*65}")


if __name__ == '__main__':
    main()
