"""
验证已改进股票的性能
检查19支已改进股票在最新数据下的表现是否稳定

执行: python3 validate_improved_stocks.py
"""

import numpy as np
import pandas as pd
import yfinance as yf
import json
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
from improved_stock_training import (
    build_regularized_model, RegularizedConfig,
    build_augmented_model, AugmentedConfig,
    augment_data
)
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("📊 验证已改进股票性能")
print("=" * 70)
print(f"验证日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 加载所有已改进的股票结果
improved_stocks = {}

print(f"\n加载已改进股票结果...")

try:
    with open('top4_improvement_results.json', 'r') as f:
        data = json.load(f)
        improved_stocks.update(data)
        print(f"  ✅ Top 4: {len(data)}支")
except FileNotFoundError:
    print(f"  ⚠️ Top 4结果文件未找到")

try:
    with open('severe_overfitting_results.json', 'r') as f:
        data = json.load(f)
        improved_stocks.update(data)
        print(f"  ✅ 批量处理: {len(data)}支")
except FileNotFoundError:
    print(f"  ⚠️ 批量处理结果文件未找到")

try:
    with open('remaining_3_severe_results.json', 'r') as f:
        data = json.load(f)
        improved_stocks.update(data)
        print(f"  ✅ 剩余严重: {len(data)}支")
except FileNotFoundError:
    print(f"  ⚠️ 剩余3支结果文件未找到")

if not improved_stocks:
    print(f"\n❌ 没有找到任何已改进股票的结果文件")
    print(f"请先运行改进脚本")
    exit(1)

print(f"\n总计加载: {len(improved_stocks)}支已改进股票")


def fetch_and_prepare_stock_data(stock_code):
    """获取并准备股票数据（与改进时相同的方法）"""
    try:
        ticker = yf.Ticker(f"{stock_code}.TW")
        df = ticker.history(period="365d")
        
        if df.empty or len(df) < 100:
            return None
        
        # 技术指标（与改进时完全相同）
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['Volume_MA5'] = df['Volume'].rolling(window=5).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['Volatility'] = df['Close'].rolling(window=20).std()
        
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        
        df['Target'] = (df['Close'].shift(-5) / df['Close'] - 1) * 100
        
        df = df.dropna()
        
        if len(df) < 160:
            return None
        
        feature_cols = ['Close', 'Volume', 'MA5', 'MA10', 'MA20', 
                        'Volume_MA5', 'RSI', 'Volatility', 'MACD']
        
        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        
        df[feature_cols] = scaler_X.fit_transform(df[feature_cols])
        df[['Target']] = scaler_y.fit_transform(df[['Target']])
        
        sequence_length = 60
        X, y = [], []
        
        for i in range(len(df) - sequence_length):
            X.append(df[feature_cols].iloc[i:i+sequence_length].values)
            y.append(df['Target'].iloc[i+sequence_length])
        
        X = np.array(X)
        y = np.array(y)
        
        # 75/25分割
        split_idx = int(len(X) * 0.75)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        return X_train, X_test, y_train, y_test
        
    except Exception as e:
        return None


def quick_evaluate(stock_code, best_method, X_train, y_train, X_test, y_test):
    """快速评估性能（使用与改进时相同的方法）"""
    try:
        if best_method == 'Augmented':
            X_train_aug, y_train_aug = augment_data(X_train, y_train, noise_level=0.003)
            config = AugmentedConfig()
            model = build_augmented_model(config)
            train_X, train_y = X_train_aug, y_train_aug
        else:  # Regularized
            config = RegularizedConfig()
            config.l2_reg = 0.02
            config.dropout_rate = 0.4
            config.recurrent_dropout = 0.25
            model = build_regularized_model(config)
            train_X, train_y = X_train, y_train
        
        early_stop = EarlyStopping(monitor='val_mae', patience=20, restore_best_weights=True, verbose=0)
        reduce_lr = ReduceLROnPlateau(monitor='val_mae', factor=0.5, patience=8, min_lr=1e-7, verbose=0)
        
        history = model.fit(
            train_X, train_y,
            validation_data=(X_test, y_test),
            epochs=config.max_epochs,
            batch_size=config.batch_size,
            callbacks=[early_stop, reduce_lr],
            verbose=0
        )
        
        test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
        train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
        
        return {
            'test_mae': float(test_mae),
            'train_mae': float(train_mae),
            'gap': float(test_mae - train_mae)
        }
        
    except Exception as e:
        return None


# ==================== 主程序 ====================

print(f"\n{'='*70}")
print(f"开始验证...")
print(f"{'='*70}")

validation_results = []
need_retrain = []

for i, (stock_code, original_result) in enumerate(improved_stocks.items(), 1):
    print(f"\n[{i}/{len(improved_stocks)}] {stock_code}")
    print(f"  原始: MAE={original_result['best_mae']:.4f} ({original_result['best_method']})")
    
    # 获取最新数据
    print(f"  获取最新数据...", end="", flush=True)
    data = fetch_and_prepare_stock_data(stock_code)
    
    if data is None:
        print(f" 失败")
        continue
    
    X_train, X_test, y_train, y_test = data
    print(f" OK")
    
    # 重新评估
    print(f"  重新评估...", end="", flush=True)
    current = quick_evaluate(
        stock_code, 
        original_result['best_method'],
        X_train, y_train, X_test, y_test
    )
    
    if current is None:
        print(f" 失败")
        continue
    
    print(f" MAE={current['test_mae']:.4f}")
    
    # 对比
    original_mae = original_result['best_mae']
    current_mae = current['test_mae']
    change_pct = (current_mae - original_mae) / original_mae * 100
    
    print(f"  变化: {change_pct:+.1f}%", end="")
    
    if abs(change_pct) <= 5:
        print(f" ✅ 稳定")
        status = '稳定'
    elif change_pct > 5:
        print(f" ⚠️ 性能下降")
        status = '下降'
        need_retrain.append({
            'code': stock_code,
            'original_mae': original_mae,
            'current_mae': current_mae,
            'change_pct': change_pct,
            'method': original_result['best_method']
        })
    else:
        print(f" ✅ 性能提升")
        status = '提升'
    
    validation_results.append({
        'code': stock_code,
        'original_mae': original_mae,
        'current_mae': current_mae,
        'change_pct': change_pct,
        'status': status,
        'method': original_result['best_method']
    })

# 总结
print(f"\n\n{'='*70}")
print(f"📊 验证总结")
print(f"{'='*70}")

if validation_results:
    total = len(validation_results)
    stable = len([r for r in validation_results if r['status'] == '稳定'])
    declined = len([r for r in validation_results if r['status'] == '下降'])
    improved = len([r for r in validation_results if r['status'] == '提升'])
    
    print(f"\n验证成功: {total}/{len(improved_stocks)} 支")
    print(f"\n状态分布:")
    print(f"  ✅ 稳定: {stable} 支 ({stable/total*100:.1f}%)")
    print(f"  📈 提升: {improved} 支 ({improved/total*100:.1f}%)")
    print(f"  ⚠️ 下降: {declined} 支 ({declined/total*100:.1f}%)")
    
    # 变化统计
    changes = [r['change_pct'] for r in validation_results]
    print(f"\n性能变化统计:")
    print(f"  平均: {np.mean(changes):+.1f}%")
    print(f"  最大提升: {max(changes):+.1f}%")
    print(f"  最大下降: {min(changes):+.1f}%")
    print(f"  标准差: {np.std(changes):.1f}%")
    
    # 需要重训的股票
    if need_retrain:
        print(f"\n⚠️ 需要重新训练的股票:")
        for stock in sorted(need_retrain, key=lambda x: x['change_pct'], reverse=True):
            print(f"  {stock['code']}: "
                  f"{stock['original_mae']:.4f}→{stock['current_mae']:.4f} "
                  f"({stock['change_pct']:+.1f}%)")
        
        # 保存需要重训列表
        output_file = 'need_retrain.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(need_retrain, f, indent=2, ensure_ascii=False)
        print(f"\n📄 已保存需要重训列表: {output_file}")
        
        print(f"\n💡 下一步:")
        print(f"  python3 retrain_declined_stocks.py")
    else:
        print(f"\n✅ 所有股票性能稳定，无需重新训练")
    
    # 保存验证结果
    output_file = f"validation_results_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, indent=2, ensure_ascii=False)
    print(f"\n📄 验证结果已保存: {output_file}")

else:
    print(f"\n❌ 验证失败，没有成功验证任何股票")

print(f"\n{'='*70}")
print(f"✅ 验证完成")
print(f"{'='*70}")
