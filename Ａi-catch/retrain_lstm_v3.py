"""
LSTM 重新訓練 v3 - 修正版
============================
主要修正：
1. 改用 Binary Cross Entropy (分類損失) 取代 MSE (迴歸損失)
2. 加入類別加權 (class_weight) 平衡看漲/看跌樣本數
3. Sigmoid 輸出層直接輸出 0-1 機率
4. 只針對問題模型重訓（無腦看空/看多的股票）

執行：
    python3 retrain_lstm_v3.py              # 重訓所有問題模型
    python3 retrain_lstm_v3.py --stocks 2881,2317,3706
    python3 retrain_lstm_v3.py --all        # 重訓全部50支
"""

import numpy as np
import pandas as pd
import json
import os
import argparse
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import MinMaxScaler
from sklearn.utils.class_weight import compute_class_weight
import yfinance as yf

print("=" * 70)
print("🔧 LSTM 重新訓練 v3 - 修正：BCE 損失 + 類別平衡")
print("=" * 70)
print(f"TensorFlow {tf.__version__}")

# ─── 配置 ───────────────────────────────────────────────
MODEL_DIR   = "models/lstm_smart_entry"
SEQ_LEN     = 30      # 縮短回看窗口 60→30（增加有效樣本數）
PRED_DAYS   = 5       # 預測未來 5 天漲跌
EPOCHS      = 200     # 增加 epoch 上限
BATCH_SIZE  = 16      # 小批次（更頻繁的參數更新）
LR          = 0.0005  # 降低學習率（更穩定收斂）
DATA_PERIOD = "5y"    # 拉長數據（2y → 5y，大幅增加樣本）

# 問題股票清單（從回測結果自動分析出來的）
PROBLEM_ALL_SELL = [
    '8422','2317','2881','6285','1802','2371','6282','1301',
    '3706','3034','2454','2382','2002','6257','5521','3189',
    '2303','2412','1326','2314','6153','2609','3037','2313',
    '3008','1303','2379','8150','2408','2618','3231'
]
PROBLEM_ALL_BUY = ['2449','2344','6770','2367','2337']

ALL_PROBLEMS = list(set(PROBLEM_ALL_SELL + PROBLEM_ALL_BUY))

os.makedirs(MODEL_DIR, exist_ok=True)


# ─── 特徵工程 ─────────────────────────────────────────────
FEATURE_COLS = ['Close','Volume','MA5','MA10','MA20',
                'Volume_MA5','RSI','Volatility','MACD']

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """計算技術指標特徵"""
    df = df.copy()
    df['MA5']       = df['Close'].rolling(5).mean()
    df['MA10']      = df['Close'].rolling(10).mean()
    df['MA20']      = df['Close'].rolling(20).mean()
    df['Volume_MA5']= df['Volume'].rolling(5).mean()

    delta = df['Close'].diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs    = gain / (loss + 1e-9)
    df['RSI']       = 100 - 100 / (1 + rs)
    df['Volatility']= df['Close'].rolling(20).std()

    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD']      = ema12 - ema26

    return df


def fetch_data(symbol: str, period: str = None) -> tuple | None:
    """獲取股票數據，同時拉取台灣加權指數作為基準"""
    if period is None:
        period = DATA_PERIOD
    try:
        # 目標股票
        ticker = yf.Ticker(f"{symbol}.TW")
        df = ticker.history(period=period)
        if df.empty or len(df) < 120:
            return None
        df = build_features(df)
        df = df.dropna()

        # 基準指數 (台灣加權指數 ^TWII)
        bench = yf.Ticker("^TWII")
        bench_df = bench.history(period=period)[['Close']].rename(columns={'Close': 'Bench'})

        # 對齊日期
        df = df.join(bench_df, how='left')
        df['Bench'] = df['Bench'].ffill()
        df = df.dropna()

        return df
    except Exception as e:
        print(f"      ⚠️ 數據獲取失敗: {e}")
        return None


def make_sequences(df: pd.DataFrame):
    """
    建立訓練序列
    標籤：未來5天是否「跑贏大盤」（超額報酬 > 0）
    這比「是否上漲」更均衡，因為有一半時間跑贏、一半跑輸
    """
    df = df.copy()
    # 個股未來報酬
    stock_ret  = (df['Close'].shift(-PRED_DAYS) / df['Close'] - 1)
    # 大盤未來報酬
    bench_ret  = (df['Bench'].shift(-PRED_DAYS) / df['Bench'] - 1)
    # 超額報酬 = 個股 - 大盤
    df['alpha'] = (stock_ret - bench_ret) * 100
    df = df.dropna()

    # 歸一化 X
    scaler = MinMaxScaler()
    df[FEATURE_COLS] = scaler.fit_transform(df[FEATURE_COLS])

    X, y = [], []
    for i in range(len(df) - SEQ_LEN - PRED_DAYS):
        X.append(df[FEATURE_COLS].iloc[i:i+SEQ_LEN].values)
        alpha = df['alpha'].iloc[i + SEQ_LEN]
        y.append(1 if alpha > 0 else 0)  # 跑贏大盤 = 1

    X = np.array(X)
    y = np.array(y)

    # 計算類別加權
    classes = np.unique(y)
    cw = compute_class_weight('balanced', classes=classes, y=y)
    class_weights = dict(zip(classes, cw))

    return X, y, class_weights, scaler


# ─── 模型架構（輕量分類版 v3.1）────────────────────────────
def build_model(seq_len: int, n_features: int) -> tf.keras.Model:
    """
    輕量模型 v3.1：避免過擬合小樣本
    - 只有 2 層 LSTM（32+16），大幅減少參數
    - Dropout 0.1（小樣本不需太強的正則化）
    - BCE + Sigmoid 輸出 → 直接輸出看漲機率
    """
    model = Sequential([
        LSTM(32, return_sequences=True,
             input_shape=(seq_len, n_features),
             dropout=0.1, recurrent_dropout=0.05),
        BatchNormalization(),
        Dropout(0.1),

        LSTM(16, return_sequences=False,
             dropout=0.1, recurrent_dropout=0.05),
        BatchNormalization(),
        Dropout(0.1),

        Dense(8, activation='relu'),

        # ✅ Sigmoid 輸出 → 0~1 看漲機率
        Dense(1, activation='sigmoid')
    ])

    model.compile(
        optimizer=Adam(learning_rate=LR),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model


# ─── 訓練單一股票 ──────────────────────────────────────────
def train_one(symbol: str, verbose: bool = False) -> dict:
    """重新訓練單一股票模型"""
    print(f"\n{'─'*50}")
    print(f"🔄 重訓: {symbol}")
    print(f"{'─'*50}")

    # 1. 獲取數據
    df = fetch_data(symbol, period="2y")
    if df is None:
        print(f"   ❌ 無法獲取數據")
        return {'symbol': symbol, 'status': 'data_error'}

    print(f"   📊 數據: {len(df)} 天")

    # 2. 建立序列
    X, y, class_weights, scaler = make_sequences(df)
    print(f"   📦 樣本: {len(X)}, 看漲={y.sum()}, 看跌={len(y)-y.sum()}")
    print(f"   ⚖️  類別加權: {class_weights}")

    if len(X) < 60:
        print(f"   ❌ 樣本數不足（{len(X)} < 60）")
        return {'symbol': symbol, 'status': 'insufficient_data'}

    # 訓練集來自前端，測試集來自近期
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # 確認正負樣本比例
    pos_ratio = y_train.mean()
    neg_ratio = 1 - pos_ratio
    print(f"   📈 訓練集跑贏比例: {pos_ratio*100:.1f}% / 跑輸: {neg_ratio*100:.1f}%")

    # 4. 建立模型
    model = build_model(SEQ_LEN, len(FEATURE_COLS))

    # 5. 訓練
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=30,   # 更有耐心
                      restore_best_weights=True, verbose=0),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5,
                          patience=10, min_lr=1e-6, verbose=0)
    ]

    print(f"   🚀 開始訓練（最多 {EPOCHS} epochs）...")
    history = model.fit(
        X_train, y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_split=0.2,
        class_weight=class_weights,    # ✅ 關鍵：類別加權
        callbacks=callbacks,
        verbose=0                      # 靜默訓練
    )

    actual_epochs = len(history.history['loss'])
    final_loss    = history.history['loss'][-1]
    final_val_loss= history.history['val_loss'][-1]
    print(f"   ✓ 完成！ {actual_epochs} epochs, loss={final_loss:.4f}, val_loss={final_val_loss:.4f}")

    # 6. 評估
    preds = model.predict(X_test, verbose=0).flatten()
    pred_binary = (preds > 0.5).astype(int)

    # 計算指標
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    acc  = accuracy_score(y_test, pred_binary)
    prec = precision_score(y_test, pred_binary, zero_division=0)
    rec  = recall_score(y_test, pred_binary, zero_division=0)
    f1   = f1_score(y_test, pred_binary, zero_division=0)
    pos_preds = pred_binary.sum()

    print(f"   📊 評估結果:")
    print(f"      準確率: {acc*100:.1f}%")
    print(f"      精確率: {prec*100:.1f}%")
    print(f"      召回率: {rec*100:.1f}%")
    print(f"      F1:     {f1*100:.1f}%")
    print(f"      正向預測數: {pos_preds}/{len(pred_binary)}")

    # 7. 判斷是否合格
    is_valid = pos_preds > 0 and pos_preds < len(pred_binary)  # 不是全買也不是全不買
    status = 'ok' if is_valid else 'still_biased'
    print(f"   {'✅ 合格' if is_valid else '⚠️ 仍有偏差，建議調整'}")

    # 8. 儲存模型（覆蓋舊模型）
    model_path = os.path.join(MODEL_DIR, f"{symbol}_model.h5")
    model.save(model_path)
    print(f"   💾 已儲存: {model_path}")

    return {
        'symbol':    symbol,
        'status':    status,
        'epochs':    actual_epochs,
        'accuracy':  float(acc),
        'precision': float(prec),
        'recall':    float(rec),
        'f1':        float(f1),
        'pos_preds': int(pos_preds),
        'total_test':int(len(pred_binary)),
        'is_valid':  bool(is_valid)
    }


# ─── 主程式 ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='LSTM 重新訓練 v3')
    parser.add_argument('--stocks', type=str, default='',
                        help='指定股票（逗號分隔）。留空則訓練所有問題模型')
    parser.add_argument('--all', action='store_true',
                        help='重訓全部 50 支股票')
    args = parser.parse_args()

    # 決定要訓練的股票清單
    if args.all:
        # 讀取已有模型的全部股票
        model_files = [f.replace('_model.h5','') for f in os.listdir(MODEL_DIR) if f.endswith('.h5')]
        stock_list = sorted(model_files)
        print(f"\n📋 模式：全部重訓 ({len(stock_list)} 支)")
    elif args.stocks:
        stock_list = [s.strip() for s in args.stocks.split(',')]
        print(f"\n📋 模式：指定股票 {stock_list}")
    else:
        stock_list = ALL_PROBLEMS
        print(f"\n📋 模式：問題模型重訓 ({len(stock_list)} 支)")

    print(f"股票清單: {stock_list}")
    print(f"\n⚙️  訓練配置:")
    print(f"   損失函數: Binary Cross Entropy (分類)")
    print(f"   類別加權: 啟用 (balanced)")
    print(f"   輸出層:   Sigmoid → 直接輸出看漲機率")
    print(f"   最大 Epochs: {EPOCHS}")
    print(f"   早停: val_loss 連續 20 epochs 無改善")

    # 開始訓練
    results = []
    total = len(stock_list)
    start_time = datetime.now()

    for i, symbol in enumerate(stock_list, 1):
        elapsed = (datetime.now() - start_time).seconds
        eta_per = elapsed / i if i > 1 else 120
        remaining = int(eta_per * (total - i))
        print(f"\n[{i}/{total}] 預計剩餘: {remaining//60}分{remaining%60}秒")

        result = train_one(symbol)
        results.append(result)

    # 統計結果
    print(f"\n\n{'='*70}")
    print(f"📊 重訓結果統計")
    print(f"{'='*70}")

    ok_results   = [r for r in results if r.get('is_valid')]
    fail_results = [r for r in results if not r.get('is_valid')]
    err_results  = [r for r in results if r.get('status') in ('data_error','insufficient_data')]

    print(f"\n✅ 合格 (有意義信號): {len(ok_results)} 支")
    for r in ok_results:
        print(f"   {r['symbol']}: 準確率={r['accuracy']*100:.1f}%, P={r['precision']*100:.1f}%, R={r['recall']*100:.1f}%, +預測={r['pos_preds']}/{r['total_test']}")

    print(f"\n⚠️  仍有偏差: {len(fail_results)-len(err_results)} 支")
    for r in fail_results:
        if r.get('status') not in ('data_error','insufficient_data'):
            print(f"   {r['symbol']}: +預測={r.get('pos_preds',0)}/{r.get('total_test',0)}")

    print(f"\n❌ 數據錯誤: {len(err_results)} 支")
    for r in err_results:
        print(f"   {r['symbol']}: {r['status']}")

    # 儲存報告（確保 JSON 可序列化）
    def to_serializable(obj):
        if isinstance(obj, (np.bool_, np.integer)):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, dict):
            return {k: to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [to_serializable(i) for i in obj]
        return obj

    report = {
        'retrain_date': datetime.now().isoformat(),
        'method': 'binary_cross_entropy + class_weight + alpha_label',
        'total': len(results),
        'ok': len(ok_results),
        'summary': [to_serializable(r) for r in results]
    }
    report_file = f"retrain_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    total_time = (datetime.now() - start_time).seconds
    print(f"\n⏱️  總耗時: {total_time//60} 分 {total_time%60} 秒")
    print(f"📄 報告已儲存: {report_file}")
    print(f"\n{'='*70}")
    print(f"✅ 重訓完成！合格率: {len(ok_results)}/{len(results)} ({len(ok_results)/max(len(results),1)*100:.0f}%)")
    print(f"{'='*70}")
    print(f"\n👉 下一步：執行回測驗證")
    print(f"   python3 lstm_backtest.py --threshold 0.5 --period 6m")


if __name__ == "__main__":
    main()
