"""
LSTM 訓練系統 - 整合 Smart Entry v2.0
訓練 ORB 監控股票列表，使用深度學習輔助進場決策

訓練目標：
- 預測股票未來 N 天的漲跌
- 輔助 smart_entry_v2 提高進場準確率

作者：AI Trading System
日期：2026-02-07
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import logging

# TensorFlow/Keras imports
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    print(f"✅ TensorFlow {tf.__version__} 已加載")
except ImportError:
    print("❌ 請安裝 TensorFlow: pip install tensorflow")
    exit(1)

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 設置隨機種子以確保可重現性
np.random.seed(42)
tf.random.set_seed(42)

# ==================== 配置參數 ====================

class TrainingConfig:
    """訓練配置 - 改進版 v2.1"""
    
    # 數據參數
    LOOKBACK_DAYS = 60          # 回看天數（用過去60天預測）
    PREDICTION_DAYS = 5         # 預測未來5天
    TRAIN_TEST_SPLIT = 0.8      # 80% 訓練，20% 測試
    VALIDATION_SPLIT = 0.2      # 從訓練集中分出 20% 作為驗證集
    
    # 模型參數（簡化架構）
    LSTM_UNITS = [64, 32]       # 2層 LSTM（簡化，避免過深）
    DROPOUT_RATE = 0.3          # Dropout 比例
    RECURRENT_DROPOUT = 0.2     # Recurrent Dropout（LSTM 內部）
    L2_REGULARIZATION = 0.01    # L2 正則化係數
    
    # 訓練參數
    BATCH_SIZE = 32             # 批次大小
    MAX_EPOCHS = 100            # 最大訓練輪數（Early Stop 會提前停止）
    LEARNING_RATE = 0.001       # 初始學習率
    
    # Early Stopping 參數
    EARLY_STOP_PATIENCE = 15    # 15 個 epoch 沒改善就停止
    REDUCE_LR_PATIENCE = 5      # 5 個 epoch 沒改善就降低學習率
    REDUCE_LR_FACTOR = 0.5      # 學習率減半
    MIN_LR = 1e-6               # 最小學習率
    
    # 數據增強
    USE_DATA_AUGMENTATION = True  # 是否使用數據增強
    NOISE_LEVEL = 0.01            # 噪聲水平
    
    # 交叉驗證
    USE_TIME_SERIES_CV = False    # 是否使用時間序列交叉驗證（耗時）
    N_SPLITS = 5                  # 交叉驗證折數
    
    # 輸出參數
    PRINT_EVERY = 10            # 每 10 個 epoch 打印一次（更頻繁）
    
    # 路徑
    PROJECT_ROOT = "/Users/Mac/Documents/ETF/AI/Ａi-catch"
    WATCHLIST_PATH = f"{PROJECT_ROOT}/data/orb_watchlist.json"
    MODEL_SAVE_PATH = f"{PROJECT_ROOT}/models/lstm_smart_entry"
    PLOT_SAVE_PATH = f"{PROJECT_ROOT}/training_results"

config = TrainingConfig()

# 創建必要目錄
os.makedirs(config.MODEL_SAVE_PATH, exist_ok=True)
os.makedirs(config.PLOT_SAVE_PATH, exist_ok=True)


# ==================== 數據加載 ====================

def load_orb_watchlist() -> List[str]:
    """載入 ORB 監控股票列表"""
    try:
        with open(config.WATCHLIST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            watchlist = data.get('watchlist', [])
            logger.info(f"✅ 載入 {len(watchlist)} 支 ORB 監控股票")
            return watchlist
    except Exception as e:
        logger.error(f"❌ 載入監控列表失敗: {e}")
        return []


def fetch_stock_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    獲取股票歷史數據
    
    Args:
        symbol: 股票代碼
        days: 獲取天數
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        import yfinance as yf
        
        # 台股代碼處理
        ticker_symbol = f"{symbol}.TW"
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
            # 嘗試上櫃
            ticker_symbol = f"{symbol}.TWO"
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(start=start_date, end=end_date)
        
        if not df.empty:
            logger.info(f"  📊 {symbol}: 獲取 {len(df)} 天數據")
            return df
        else:
            logger.warning(f"  ⚠️  {symbol}: 無數據")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"  ❌ {symbol} 數據獲取失敗: {e}")
        return pd.DataFrame()


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    準備特徵工程
    
    技術指標：
    - MA5, MA20, MA60 (移動平均線)
    - RSI (相對強弱指數)
    - MACD (指數平滑異同移動平均線)
    - Volume Ratio (成交量比率)
    - Price Change (價格變化率)
    """
    df = df.copy()
    
    # 移動平均線
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 成交量比率
    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA20']
    
    # 價格變化率
    df['Price_Change'] = df['Close'].pct_change()
    
    # 未來收益（目標變量）
    df['Future_Return'] = df['Close'].shift(-config.PREDICTION_DAYS) / df['Close'] - 1
    
    # 移除 NaN
    df = df.dropna()
    
    return df


def create_sequences(data: np.ndarray, lookback: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    創建時間序列數據
    
    Args:
        data: 特徵數據
        lookback: 回看天數
    
    Returns:
        X: (samples, lookback, features)
        y: (samples,) - 未來收益率
    """
    X, y = [], []
    
    for i in range(lookback, len(data)):
        X.append(data[i-lookback:i, :-1])  # 所有特徵除了目標
        y.append(data[i-1, -1])             # 未來收益率
    
    return np.array(X), np.array(y)


# ==================== 模型構建 ====================

def build_lstm_model(input_shape: Tuple[int, int]) -> keras.Model:
    """
    構建 LSTM 模型
    
    架構：
    - 3層 LSTM (128 -> 64 -> 32 units)
    - Dropout 防止過擬合
    - BatchNormalization 加速訓練
    - Dense 輸出層
    
    Args:
        input_shape: (lookback_days, n_features)
    
    Returns:
        Compiled Keras model
    """
    model = Sequential(name='LSTM_SmartEntry_v2')
    
    # 第一層 LSTM
    model.add(LSTM(
        units=config.LSTM_UNITS[0],
        return_sequences=True,
        input_shape=input_shape,
        name='LSTM_Layer_1'
    ))
    model.add(BatchNormalization(name='BN_1'))
    model.add(Dropout(config.DROPOUT_RATE, name='Dropout_1'))
    
    # 第二層 LSTM
    model.add(LSTM(
        units=config.LSTM_UNITS[1],
        return_sequences=True,
        name='LSTM_Layer_2'
    ))
    model.add(BatchNormalization(name='BN_2'))
    model.add(Dropout(config.DROPOUT_RATE, name='Dropout_2'))
    
    # 第三層 LSTM
    model.add(LSTM(
        units=config.LSTM_UNITS[2],
        return_sequences=False,
        name='LSTM_Layer_3'
    ))
    model.add(BatchNormalization(name='BN_3'))
    model.add(Dropout(config.DROPOUT_RATE, name='Dropout_3'))
    
    # 輸出層
    model.add(Dense(1, name='Output_Layer'))
    
    # 編譯模型
    # 使用 Adam 優化器：
    # 原因：
    # 1. 自適應學習率：每個參數都有獨立的學習率，自動調整
    # 2. 動量累積：結合過去梯度信息，避免震盪
    # 3. 收斂更快：比 SGD 更聰明，通常需要更少的 epochs
    # 4. 適合處理稀疏梯度：在金融時間序列中很常見
    # 5. 對超參數不敏感：默認參數通常就很好
    optimizer = Adam(
        learning_rate=config.LEARNING_RATE,
        beta_1=0.9,   # 一階動量衰減率
        beta_2=0.999  # 二階動量衰減率
    )
    
    model.compile(
        optimizer=optimizer,
        loss='mse',  # MSE (均方誤差) - 適合回歸問題
        metrics=['mae', 'mse']  # 同時追蹤 MAE 和 MSE
    )
    
    return model


# ==================== 訓練循環 ====================

class TrainingLogger(keras.callbacks.Callback):
    """自定義訓練日誌記錄器"""
    
    def __init__(self):
        super().__init__()
        self.epoch_losses = []
        self.epoch_val_losses = []
    
    def on_epoch_end(self, epoch, logs=None):
        self.epoch_losses.append(logs['loss'])
        self.epoch_val_losses.append(logs.get('val_loss', 0))
        
        # 每 50 個 epoch 打印一次
        if (epoch + 1) % config.PRINT_EVERY == 0:
            logger.info(
                f"📊 Epoch {epoch+1}/{config.EPOCHS} | "
                f"Loss: {logs['loss']:.6f} | "
                f"Val Loss: {logs.get('val_loss', 0):.6f} | "
                f"MAE: {logs['mae']:.6f}"
            )


def train_model_for_stock(symbol: str) -> Dict:
    """
    為單支股票訓練 LSTM 模型
    
    Args:
        symbol: 股票代碼
    
    Returns:
        訓練結果字典
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"🎯 開始訓練: {symbol}")
    logger.info(f"{'='*60}")
    
    # 1. 獲取數據
    df = fetch_stock_data(symbol, days=365)
    if df.empty or len(df) < config.LOOKBACK_DAYS + 100:
        logger.warning(f"⚠️  {symbol}: 數據不足，跳過")
        return {'success': False, 'reason': 'insufficient_data'}
    
    # 2. 特徵工程
    df = prepare_features(df)
    
    # 3. 準備訓練數據
    feature_cols = ['Close', 'MA5', 'MA20', 'MA60', 'RSI', 'MACD', 
                    'MACD_Signal', 'Volume_Ratio', 'Price_Change', 'Future_Return']
    data = df[feature_cols].values
    
    # 標準化
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data)
    
    # 創建序列
    X, y = create_sequences(data_scaled, config.LOOKBACK_DAYS)
    
    # 分割訓練集和測試集
    split_idx = int(len(X) * config.TRAIN_TEST_SPLIT)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    logger.info(f"  訓練集: {X_train.shape[0]} 樣本")
    logger.info(f"  測試集: {X_test.shape[0]} 樣本")
    logger.info(f"  特徵維度: {X_train.shape[2]}")
    
    # 4. 構建模型
    model = build_lstm_model(input_shape=(X_train.shape[1], X_train.shape[2]))
    
    # 5. 訓練模型
    logger.info(f"\n🚀 開始訓練 {config.EPOCHS} 個 Epochs...")
    logger.info(f"📝 優化器: Adam (比 SGD 更聰明，自適應學習率)")
    logger.info(f"📉 損失函數: MSE (均方誤差)\n")
    
    # 訓練記錄器
    training_logger = TrainingLogger()
    
    # Early Stopping: 如果 val_loss 20 個 epoch 沒改善就停止
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=20,
        restore_best_weights=True,
        verbose=1
    )
    
    # 學習率調整: 如果 val_loss 10 個 epoch 沒改善就降低學習率
    reduce_lr = ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=10,
        min_lr=1e-6,
        verbose=1
    )
    
    # 開始訓練
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=config.EPOCHS,
        batch_size=config.BATCH_SIZE,
        callbacks=[training_logger, early_stopping, reduce_lr],
        verbose=0  # 使用自定義日誌
    )
    
    # 6. 評估模型
    train_loss = model.evaluate(X_train, y_train, verbose=0)
    test_loss = model.evaluate(X_test, y_test, verbose=0)
    
    logger.info(f"\n✅ 訓練完成！")
    logger.info(f"  訓練集 Loss: {train_loss[0]:.6f}")
    logger.info(f"  測試集 Loss: {test_loss[0]:.6f}")
    
    # 7. 保存模型
    model_path = f"{config.MODEL_SAVE_PATH}/{symbol}_model.h5"
    model.save(model_path)
    logger.info(f"  💾 模型已保存: {model_path}")
    
    return {
        'success': True,
        'symbol': symbol,
        'train_loss': float(train_loss[0]),
        'test_loss': float(test_loss[0]),
        'epoch_losses': training_logger.epoch_losses,
        'epoch_val_losses': training_logger.epoch_val_losses,
        'epochs_trained': len(training_logger.epoch_losses)
    }


def plot_training_curve(results: List[Dict]):
    """
    繪製訓練損失曲線
    
    展示「機器如何一步一步減少痛苦」
    """
    logger.info(f"\n{'='*60}")
    logger.info("📊 繪製訓練損失曲線...")
    logger.info(f"{'='*60}")
    
    # 設置中文字體
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 計算需要的子圖數量
    n_stocks = len([r for r in results if r['success']])
    n_cols = 3
    n_rows = (n_stocks + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 5*n_rows))
    fig.suptitle(
        '🤖 LSTM 訓練損失曲線 - 機器學習的痛苦減少過程\n'
        f'訓練配置: {config.EPOCHS} Epochs | Adam 優化器 | MSE 損失函數',
        fontsize=16,
        fontweight='bold'
    )
    
    axes = axes.flatten() if n_stocks > 1 else [axes]
    
    plot_idx = 0
    for result in results:
        if not result['success']:
            continue
        
        ax = axes[plot_idx]
        symbol = result['symbol']
        losses = result['epoch_losses']
        val_losses = result['epoch_val_losses']
        epochs = range(1, len(losses) + 1)
        
        # 繪製訓練損失
        ax.plot(epochs, losses, 'b-', linewidth=2, label='訓練損失', alpha=0.8)
        ax.plot(epochs, val_losses, 'r--', linewidth=2, label='驗證損失', alpha=0.8)
        
        ax.set_title(f'{symbol} - 損失下降曲線', fontsize=12, fontweight='bold')
        ax.set_xlabel('Epoch', fontsize=10)
        ax.set_ylabel('MSE Loss (痛苦值)', fontsize=10)
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # 標註最小損失
        min_loss_idx = np.argmin(val_losses)
        min_loss = val_losses[min_loss_idx]
        ax.plot(min_loss_idx+1, min_loss, 'g*', markersize=15, 
                label=f'最佳 (Epoch {min_loss_idx+1})')
        ax.annotate(
            f'最小損失: {min_loss:.6f}',
            xy=(min_loss_idx+1, min_loss),
            xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.5),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
        )
        
        plot_idx += 1
    
    # 隱藏多餘的子圖
    for idx in range(plot_idx, len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    
    # 保存圖表
    plot_path = f"{config.PLOT_SAVE_PATH}/training_curves_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    logger.info(f"✅ 損失曲線已保存: {plot_path}")
    
    # 顯示圖表
    plt.show()
    
    # 繪製總體統計
    plot_overall_statistics(results)


def plot_overall_statistics(results: List[Dict]):
    """繪製總體訓練統計"""
    successful_results = [r for r in results if r['success']]
    
    if not successful_results:
        return
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    
    # 1. 最終損失分佈
    ax1 = axes[0]
    symbols = [r['symbol'] for r in successful_results]
    test_losses = [r['test_loss'] for r in successful_results]
    
    bars = ax1.bar(range(len(symbols)), test_losses, color='skyblue', edgecolor='navy')
    ax1.set_xlabel('股票代碼', fontsize=12)
    ax1.set_ylabel('測試集 MSE Loss', fontsize=12)
    ax1.set_title('各股票最終測試損失', fontsize=14, fontweight='bold')
    ax1.set_xticks(range(len(symbols)))
    ax1.set_xticklabels(symbols, rotation=45, ha='right')
    ax1.grid(axis='y', alpha=0.3)
    
    # 標註平均值
    avg_loss = np.mean(test_losses)
    ax1.axhline(y=avg_loss, color='r', linestyle='--', linewidth=2, 
                label=f'平均損失: {avg_loss:.6f}')
    ax1.legend()
    
    # 2. 訓練 vs 測試損失
    ax2 = axes[1]
    train_losses = [r['train_loss'] for r in successful_results]
    
    x = np.arange(len(symbols))
    width = 0.35
    
    ax2.bar(x - width/2, train_losses, width, label='訓練損失', color='lightgreen')
    ax2.bar(x + width/2, test_losses, width, label='測試損失', color='lightcoral')
    
    ax2.set_xlabel('股票代碼', fontsize=12)
    ax2.set_ylabel('MSE Loss', fontsize=12)
    ax2.set_title('訓練 vs 測試損失比較', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(symbols, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    # 保存
    plot_path = f"{config.PLOT_SAVE_PATH}/overall_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    logger.info(f"✅ 統計圖表已保存: {plot_path}")
    
    plt.show()


# ==================== 主程序 ====================

def main():
    """主訓練流程"""
    logger.info(f"\n{'='*70}")
    logger.info("🤖 LSTM Smart Entry v2.0 - 深度學習訓練系統")
    logger.info(f"{'='*70}\n")
    
    logger.info("📋 訓練配置:")
    logger.info(f"  • 回看天數: {config.LOOKBACK_DAYS} 天")
    logger.info(f"  • 預測天數: {config.PREDICTION_DAYS} 天")
    logger.info(f"  • LSTM 架構: {' -> '.join(map(str, config.LSTM_UNITS))} units")
    logger.info(f"  • Dropout率: {config.DROPOUT_RATE}")
    logger.info(f"  • 批次大小: {config.BATCH_SIZE}")
    logger.info(f"  • 訓練輪數: {config.EPOCHS} epochs")
    logger.info(f"  • 學習率: {config.LEARNING_RATE}")
    logger.info(f"  • 優化器: Adam (自適應學習率)")
    logger.info(f"  • 損失函數: MSE (均方誤差)\n")
    
    # 載入 ORB 監控列表
    watchlist = load_orb_watchlist()
    
    if not watchlist:
        logger.error("❌ 無法載入監控列表，訓練終止")
        return
    
    logger.info(f"📊 將訓練 {len(watchlist)} 支股票\n")
    
    # 訓練所有股票
    results = []
    
    for idx, symbol in enumerate(watchlist, 1):
        logger.info(f"\n進度: [{idx}/{len(watchlist)}]")
        
        try:
            result = train_model_for_stock(symbol)
            results.append(result)
        except Exception as e:
            logger.error(f"❌ {symbol} 訓練失敗: {e}")
            results.append({'success': False, 'symbol': symbol, 'error': str(e)})
    
    # 統計結果
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    logger.info(f"\n{'='*70}")
    logger.info("🎉 訓練完成！")
    logger.info(f"{'='*70}")
    logger.info(f"  ✅ 成功: {successful} 支")
    logger.info(f"  ❌ 失敗: {failed} 支")
    logger.info(f"  📊 總計: {len(results)} 支\n")
    
    # 繪製損失曲線
    if successful > 0:
        plot_training_curve(results)
    
    # 保存訓練報告
    report = {
        'training_date': datetime.now().isoformat(),
        'config': {
            'epochs': config.EPOCHS,
            'batch_size': config.BATCH_SIZE,
            'learning_rate': config.LEARNING_RATE,
            'lstm_units': config.LSTM_UNITS,
            'dropout_rate': config.DROPOUT_RATE
        },
        'results': results,
        'summary': {
            'total': len(results),
            'successful': successful,
            'failed': failed
        }
    }
    
    report_path = f"{config.MODEL_SAVE_PATH}/training_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📝 訓練報告已保存: {report_path}\n")
    logger.info("🎊 所有任務完成！")


if __name__ == "__main__":
    main()
