"""
LSTM 訓練系統 v2.1 - 改進版
整合 Smart Entry v2.0 + 深度學習最佳實踐

改進項目：
1. 簡化模型架構（2層 LSTM）
2. 加入 L2 正則化和 Recurrent Dropout
3. Early Stopping 和 Learning Rate 調整
4. RobustScaler 數據預處理
5. 數據增強
6. 詳細的訓練曲線圖

作者：AI Trading System
日期：2026-02-07
版本：v2.1
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
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
    from tensorflow.keras.regularizers import l2
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

# 設置隨機種子
np.random.seed(42)
tf.random.set_seed(42)

# ==================== 配置參數 ====================

class TrainingConfig:
    """訓練配置 - 改進版 v2.1"""
    
    # 數據參數
    LOOKBACK_DAYS = 60
    PREDICTION_DAYS = 5
    TRAIN_TEST_SPLIT = 0.8
    VALIDATION_SPLIT = 0.2
    
    # 模型參數（簡化架構）
    LSTM_UNITS = [64, 32]       # 2層 LSTM（避免過深）
    DENSE_UNITS = 16             # 中間 Dense 層
    DROPOUT_RATE = 0.3
    RECURRENT_DROPOUT = 0.2     # LSTM 內部 Dropout
    L2_REG = 0.01               # L2 正則化係數
    
    # 訓練參數
    BATCH_SIZE = 32
    MAX_EPOCHS = 100            # 最大輪數（Early Stop 會提前停止）
    LEARNING_RATE = 0.001
    
    # Callbacks 參數
    EARLY_STOP_PATIENCE = 15    # 15 epoch 無改善則停止
    REDUCE_LR_PATIENCE = 5      # 5 epoch 無改善則降低學習率
    REDUCE_LR_FACTOR = 0.5
    MIN_LR = 1e-6
    
    # 數據增強
    USE_DATA_AUGMENTATION = True
    NOISE_LEVEL = 0.01
    
    # 輸出參數
    PRINT_EVERY = 10
    
    # 路徑
    PROJECT_ROOT = "/Users/Mac/Documents/ETF/AI/Ａi-catch"
    WATCHLIST_PATH = f"{PROJECT_ROOT}/data/orb_watchlist.json"
    MODEL_SAVE_PATH = f"{PROJECT_ROOT}/models/lstm_smart_entry_v2.1"
    PLOT_SAVE_PATH = f"{PROJECT_ROOT}/training_results"

config = TrainingConfig()
os.makedirs(config.MODEL_SAVE_PATH, exist_ok=True)
os.makedirs(config.PLOT_SAVE_PATH, exist_ok=True)


# ==================== 數據處理 ====================

def load_orb_watchlist() -> List[str]:
    """載入 ORB 監控列表"""
    try:
        with open(config.WATCHLIST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            watchlist = data.get('watchlist', [])
            logger.info(f"✅ 載入 {len(watchlist)} 支 ORB 監控股票")
            return watchlist
    except Exception as e:
        logger.error(f"❌ 載入列表失敗: {e}")
        return []


def fetch_stock_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """獲取股票數據"""
    try:
        import yfinance as yf
        ticker_symbol = f"{symbol}.TW"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
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
        logger.error(f"  ❌ {symbol} 失敗: {e}")
        return pd.DataFrame()


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """特徵工程"""
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
    
    # 目標變量：未來收益
    df['Future_Return'] = df['Close'].shift(-config.PREDICTION_DAYS) / df['Close'] - 1
    
    df = df.dropna()
    return df


def add_noise(data: np.ndarray, noise_level: float = 0.01) -> np.ndarray:
    """數據增強：添加微小噪聲"""
    noise = np.random.normal(0, noise_level, data.shape)
    return data + noise


def create_sequences(data: np.ndarray, lookback: int) -> Tuple[np.ndarray, np.ndarray]:
    """創建時間序列"""
    X, y = [], []
    for i in range(lookback, len(data)):
        X.append(data[i-lookback:i, :-1])
        y.append(data[i-1, -1])
    return np.array(X), np.array(y)


# ==================== 模型構建（改進版）====================

def build_improved_lstm(input_shape: Tuple[int, int]) -> keras.Model:
    """
    構建改進的 LSTM 模型
    
    改進項目：
    1. 簡化為 2 層 LSTM（避免過深）
    2. 加入 L2 正則化
    3. 加入 Recurrent Dropout
    4. 添加中間 Dense 層
    
    參數：
        input_shape: (lookback_days, n_features)
    
    Returns:
        編譯好的 Keras 模型
    """
    model = Sequential(name='LSTM_SmartEntry_v2.1_Improved')
    
    # 第一層 LSTM
    # - units=64: 適中的單元數
    # - return_sequences=True: 返回完整序列給下一層
    # - kernel_regularizer=l2(0.01): L2 正則化防止過擬合
    # - recurrent_dropout=0.2: LSTM 內部 Dropout
    model.add(LSTM(
        units=config.LSTM_UNITS[0],
        return_sequences=True,
        input_shape=input_shape,
        kernel_regularizer=l2(config.L2_REG),
        recurrent_dropout=config.RECURRENT_DROPOUT,
        name='LSTM_Layer_1'
    ))
    model.add(Dropout(config.DROPOUT_RATE, name='Dropout_1'))
    
    # 第二層 LSTM
    # - units=32: 逐層遞減
    # - return_sequences=False: 只返回最後一個輸出
    model.add(LSTM(
        units=config.LSTM_UNITS[1],
        return_sequences=False,
        kernel_regularizer=l2(config.L2_REG),
        recurrent_dropout=config.RECURRENT_DROPOUT,
        name='LSTM_Layer_2'
    ))
    model.add(Dropout(config.DROPOUT_RATE, name='Dropout_2'))
    
    # 中間 Dense 層
    # - activation='relu': ReLU 激活函數
    # - units=16: 進一步壓縮特徵
    model.add(Dense(
        config.DENSE_UNITS,
        activation='relu',
        kernel_regularizer=l2(config.L2_REG),
        name='Dense_Middle'
    ))
    model.add(Dropout(0.2, name='Dropout_3'))
    
    # 輸出層
    model.add(Dense(1, name='Output'))
    
    # 編譯模型
    # Adam 優化器的 5 大優勢：
    # 1. 自適應學習率 - 每個參數獨立調整
    # 2. 動量累積 - 結合過去梯度，避免震盪
    # 3. 收斂更快 - 比 SGD 需要更少的 epochs
    # 4. 適合稀疏梯度 - 金融數據的特性
    # 5. 超參數不敏感 - 默認值通常就很好
    optimizer = Adam(
        learning_rate=config.LEARNING_RATE,
        beta_1=0.9,
        beta_2=0.999
    )
    
    model.compile(
        optimizer=optimizer,
        loss='mse',  # MSE: 均方誤差
        metrics=['mae']  # MAE: 平均絕對誤差
    )
    
    return model


# ==================== 訓練流程（改進版）====================

class ImprovedTrainingLogger(keras.callbacks.Callback):
    """改進的訓練日誌記錄器"""
    
    def __init__(self):
        super().__init__()
        self.epoch_losses = []
        self.epoch_val_losses = []
        self.epoch_maes = []
        self.epoch_val_maes = []
    
    def on_epoch_end(self, epoch, logs=None):
        self.epoch_losses.append(logs['loss'])
        self.epoch_val_losses.append(logs.get('val_loss', 0))
        self.epoch_maes.append(logs['mae'])
        self.epoch_val_maes.append(logs.get('val_mae', 0))
        
        if (epoch + 1) % config.PRINT_EVERY == 0:
            logger.info(
                f"📊 Epoch {epoch+1:3d}/{config.MAX_EPOCHS} | "
                f"Loss: {logs['loss']:.6f} | "
                f"Val_Loss: {logs.get('val_loss', 0):.6f} | "
                f"MAE: {logs['mae']:.6f} | "
                f"Val_MAE: {logs.get('val_mae', 0):.6f}"
            )


def train_improved_model(symbol: str) -> Dict:
    """
    改進的訓練流程
    
    改進項目：
    1. 使用 RobustScaler（對異常值更穩健）
    2. 數據增強（添加噪聲）
    3. Early Stopping
    4. Learning Rate 調整
    5. 保存最佳模型
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"🎯 開始訓練: {symbol}")
    logger.info(f"{'='*60}")
    
    # 1. 獲取數據
    df = fetch_stock_data(symbol, days=365)
    if df.empty or len(df) < config.LOOKBACK_DAYS + 100:
        logger.warning(f"⚠️  {symbol}: 數據不足")
        return {'success': False, 'reason': 'insufficient_data'}
    
    # 2. 特徵工程
    df = prepare_features(df)
    
    # 3. 數據準備
    feature_cols = ['Close', 'MA5', 'MA20', 'MA60', 'RSI', 'MACD',
                    'MACD_Signal', 'Volume_Ratio', 'Price_Change', 'Future_Return']
    data = df[feature_cols].values
    
    # 使用 RobustScaler（對異常值更穩健）
    from sklearn.preprocessing import RobustScaler
    scaler = RobustScaler()
    data_scaled = scaler.fit_transform(data)
    
    # 創建序列
    X, y = create_sequences(data_scaled, config.LOOKBACK_DAYS)
    
    # 分割數據
    split_idx = int(len(X) * config.TRAIN_TEST_SPLIT)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # 數據增強（訓練集）
    if config.USE_DATA_AUGMENTATION:
        X_train_aug = add_noise(X_train, config.NOISE_LEVEL)
        logger.info(f"  🔊 數據增強: 添加 {config.NOISE_LEVEL} 水平噪聲")
    else:
        X_train_aug = X_train
    
    logger.info(f"  訓練集: {X_train.shape[0]} 樣本")
    logger.info(f"  測試集: {X_test.shape[0]} 樣本")
    logger.info(f"  特徵維度: {X_train.shape[2]}")
    
    # 4. 構建模型
    model = build_improved_lstm(input_shape=(X_train.shape[1], X_train.shape[2]))
    
    logger.info(f"\n🏗️ 模型架構:")
    logger.info(f"  • LSTM 層: {' → '.join(map(str, config.LSTM_UNITS))}")
    logger.info(f"  • Dense 層: {config.DENSE_UNITS}")
    logger.info(f"  • Dropout: {config.DROPOUT_RATE}")
    logger.info(f"  • Recurrent Dropout: {config.RECURRENT_DROPOUT}")
    logger.info(f"  • L2 正則化: {config.L2_REG}")
    
    # 5. 設置 Callbacks
    logger.info(f"\n⚙️ 訓練策略:")
    logger.info(f"  • Early Stopping: patience={config.EARLY_STOP_PATIENCE}")
    logger.info(f"  • Learning Rate 調整: patience={config.REDUCE_LR_PATIENCE}, factor={config.REDUCE_LR_FACTOR}")
    logger.info(f"  • 最大 Epochs: {config.MAX_EPOCHS}\n")
    
   # Training logger
    training_logger = ImprovedTrainingLogger()
    
    # Early Stopping
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=config.EARLY_STOP_PATIENCE,
        restore_best_weights=True,
        verbose=1
    )
    
    # Learning Rate 調整
    reduce_lr = ReduceLROnPlateau(
        monitor='val_loss',
        factor=config.REDUCE_LR_FACTOR,
        patience=config.REDUCE_LR_PATIENCE,
        min_lr=config.MIN_LR,
        verbose=1
    )
    
    # 保存最佳模型
    best_model_path = f"{config.MODEL_SAVE_PATH}/best_{symbol}.h5"
    checkpoint = ModelCheckpoint(
        best_model_path,
        monitor='val_loss',
        save_best_only=True,
        verbose=0
    )
    
    # 6. 訓練
    logger.info("🚀 開始訓練...")
    logger.info("📝 優化器: Adam (自適應學習率)")
    logger.info("📉 損失函數: MSE (均方誤差)\n")
    
    history = model.fit(
        X_train_aug, y_train,
        validation_data=(X_test, y_test),
        epochs=config.MAX_EPOCHS,
        batch_size=config.BATCH_SIZE,
        callbacks=[training_logger, early_stopping, reduce_lr, checkpoint],
        verbose=0,
        shuffle=True  # 打亂訓練數據
    )
    
    # 7. 評估
    train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
    test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
    
    logger.info(f"\n✅ 訓練完成！")
    logger.info(f"  實際訓練 Epochs: {len(training_logger.epoch_losses)}")
    logger.info(f"  訓練集 Loss: {train_loss:.6f} | MAE: {train_mae:.6f}")
    logger.info(f"  測試集 Loss: {test_loss:.6f} | MAE: {test_mae:.6f}")
    
    # 檢查過擬合
    if train_loss < test_loss * 0.5:
        logger.warning(f"  ⚠️  可能過擬合！訓練損失遠小於測試損失")
    
    # 8. 保存最終模型
    final_model_path = f"{config.MODEL_SAVE_PATH}/{symbol}_final.h5"
    model.save(final_model_path)
    logger.info(f"  💾 最終模型: {final_model_path}")
    logger.info(f"  💾 最佳模型: {best_model_path}")
    
    return {
        'success': True,
        'symbol': symbol,
        'train_loss': float(train_loss),
        'test_loss': float(test_loss),
        'train_mae': float(train_mae),
        'test_mae': float(test_mae),
        'epoch_losses': training_logger.epoch_losses,
        'epoch_val_losses': training_logger.epoch_val_losses,
        'epoch_maes': training_logger.epoch_maes,
        'epoch_val_maes': training_logger.epoch_val_maes,
        'epochs_trained': len(training_logger.epoch_losses)
    }


# ==================== 可視化（改進版）====================

def plot_improved_training_curves(results: List[Dict]):
    """繪製改進的訓練曲線"""
    logger.info(f"\n{'='*60}")
    logger.info("📊 繪製訓練曲線...")
    logger.info(f"{'='*60}")
    
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    successful_results = [r for r in results if r['success']]
    n_stocks = len(successful_results)
    
    if n_stocks == 0:
        logger.warning("沒有成功的訓練結果")
        return
    
    n_cols = min(3, n_stocks)
    n_rows = (n_stocks + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 6*n_rows))
    fig.suptitle(
        '🤖 LSTM v2.1 訓練曲線 - 改進版（簡化架構 + 正則化 + Early Stop）\n'
        f'{config.MAX_EPOCHS} Max Epochs | Adam 優化器 | L2正則化 | RobustScaler',
        fontsize=16,
        fontweight='bold'
    )
    
    if n_stocks == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    for idx, result in enumerate(successful_results):
        ax = axes[idx]
        symbol = result['symbol']
        losses = result['epoch_losses']
        val_losses = result['epoch_val_losses']
        epochs = range(1, len(losses) + 1)
        
        # 繪製損失曲線
        ax.plot(epochs, losses, 'b-', linewidth=2, label='訓練損失', alpha=0.8)
        ax.plot(epochs, val_losses, 'r--', linewidth=2, label='驗證損失', alpha=0.8)
        
        ax.set_title(f'{symbol} - 損失下降曲線 ({len(losses)} epochs)', 
                     fontsize=12, fontweight='bold')
        ax.set_xlabel('Epoch', fontsize=10)
        ax.set_ylabel('MSE Loss', fontsize=10)
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # 標註最佳點
        min_idx = np.argmin(val_losses)
        min_loss = val_losses[min_idx]
        ax.plot(min_idx+1, min_loss, 'g*', markersize=15)
        ax.annotate(
            f'最佳: {min_loss:.6f}\n(Epoch {min_idx+1})',
            xy=(min_idx+1, min_loss),
            xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5),
            arrowprops=dict(arrowstyle='->')
        )
    
    # 隱藏多餘子圖
    for idx in range(n_stocks, len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    
    # 保存
    plot_path = f"{config.PLOT_SAVE_PATH}/training_curves_v2.1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    logger.info(f"✅ 訓練曲線已保存: {plot_path}")
    
    plt.show()
    
    # 繪製 MAE 曲線
    plot_mae_curves(successful_results)


def plot_mae_curves(results: List[Dict]):
    """繪製 MAE 曲線"""
    n_stocks = len(results)
    n_cols = min(3, n_stocks)
    n_rows = (n_stocks + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 6*n_rows))
    fig.suptitle('MAE (平均絕對誤差) 曲線', fontsize=16, fontweight='bold')
    
    if n_stocks == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    for idx, result in enumerate(results):
        ax = axes[idx]
        maes = result['epoch_maes']
        val_maes = result['epoch_val_maes']
        epochs = range(1, len(maes) +1)
        
        ax.plot(epochs, maes, 'g-', linewidth=2, label='訓練 MAE')
        ax.plot(epochs, val_maes, 'm--', linewidth=2, label='驗證 MAE')
        ax.set_title(f"{result['symbol']} - MAE")
        ax.set_xlabel('Epoch')
        ax.set_ylabel('MAE')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    for idx in range(n_stocks, len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    
    plot_path = f"{config.PLOT_SAVE_PATH}/mae_curves_v2.1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    logger.info(f"✅ MAE 曲線已保存: {plot_path}")
    
    plt.show()


# ==================== 主程序 ====================

def main():
    """主訓練流程"""
    logger.info(f"\n{'='*70}")
    logger.info("🤖 LSTM Smart Entry v2.1 - 改進版訓練系統")
    logger.info(f"{'='*70}\n")
    
    logger.info("🆕 改進項目:")
    logger.info("  1. ✅ 簡化架構: 2層 LSTM (64→32)")
    logger.info("  2. ✅ L2 正則化: 防止過擬合")
    logger.info("  3. ✅ Recurrent Dropout: LSTM 內部 Dropout")
    logger.info("  4. ✅ Early Stopping: 15 epoch patience")
    logger.info("  5. ✅ Learning Rate 調整: 自動降低學習率")
    logger.info("  6. ✅ RobustScaler: 對異常值更穩健")
    logger.info("  7. ✅ 數據增強: 添加微小噪聲\n")
    
    logger.info("📋 訓練配置:")
    logger.info(f"  • LSTM: {' → '.join(map(str, config.LSTM_UNITS))} units")
    logger.info(f"  • Dense: {config.DENSE_UNITS} units")
    logger.info(f"  • Dropout: {config.DROPOUT_RATE}")
    logger.info(f"  • Recurrent Dropout: {config.RECURRENT_DROPOUT}")
    logger.info(f"  • L2 正則化: {config.L2_REG}")
    logger.info(f"  • 最大 Epochs: {config.MAX_EPOCHS}")
    logger.info(f"  • Early Stop: {config.EARLY_STOP_PATIENCE} patience")
    logger.info(f"  • 批次大小: {config.BATCH_SIZE}")
    logger.info(f"  • 學習率: {config.LEARNING_RATE}\n")
    
    # 載入監控列表
    watchlist = load_orb_watchlist()
    if not watchlist:
        logger.error("❌ 無法載入監控列表")
        return
    
    logger.info(f"📊 將訓練 {len(watchlist)} 支股票\n")
    
    # 訓練所有股票
    results = []
    for idx, symbol in enumerate(watchlist, 1):
        logger.info(f"\n進度: [{idx}/{len(watchlist)}]")
        try:
            result = train_improved_model(symbol)
            results.append(result)
        except Exception as e:
            logger.error(f"❌ {symbol} 失敗: {e}")
            results.append({'success': False, 'symbol': symbol, 'error': str(e)})
    
    # 統計
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    logger.info(f"\n{'='*70}")
    logger.info("🎉 訓練完成！")
    logger.info(f"{'='*70}")
    logger.info(f"  ✅ 成功: {successful} 支")
    logger.info(f"  ❌ 失敗: {failed} 支")
    logger.info(f"  📊 總計: {len(results)} 支\n")
    
    # 繪製曲線
    if successful > 0:
        plot_improved_training_curves(results)
    
    # 保存報告
    report = {
        'version': 'v2.1',
        'training_date': datetime.now().isoformat(),
        'improvements': [
            '簡化架構(2層LSTM)',
            'L2正則化',
            'Recurrent Dropout',
            'Early Stopping',
            'Learning Rate 調整',
            'RobustScaler',
            '數據增強'
        ],
        'config': {
            'lstm_units': config.LSTM_UNITS,
            'dense_units': config.DENSE_UNITS,
            'dropout': config.DROPOUT_RATE,
            'recurrent_dropout': config.RECURRENT_DROPOUT,
            'l2_reg': config.L2_REG,
            'max_epochs': config.MAX_EPOCHS,
            'early_stop_patience': config.EARLY_STOP_PATIENCE,
            'batch_size': config.BATCH_SIZE,
            'learning_rate': config.LEARNING_RATE
        },
        'results': results,
        'summary': {
            'total': len(results),
            'successful': successful,
            'failed': failed
        }
    }
    
    report_path = f"{config.MODEL_SAVE_PATH}/training_report_v2.1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📝 訓練報告: {report_path}\n")
    logger.info("🎊 所有任務完成！")


if __name__ == "__main__":
    main()
