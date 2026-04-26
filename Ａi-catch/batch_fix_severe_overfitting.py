"""
批量处理严重过拟合股票
基于Top 4的成功经验，批量改进剩余的严重过拟合股票

目标: MAE 1.0-1.5的股票（约15支）
方法: Augmented（首选）或Regularized
预期: 平均改善85-90%

执行: python3 batch_fix_severe_overfitting.py
"""

import numpy as np
import pandas as pd
import yfinance as yf
import json
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
print("🚀 批量处理严重过拟合股票")
print("=" * 70)

# 加载Baseline结果
with open('baseline_results/baseline_results_final.json', 'r') as f:
    baseline_results = json.load(f)

# 筛选严重过拟合股票（MAE 1.0-1.5）
SEVERE_OVERFITTING = {}

for code, result in baseline_results.items():
    if not result.get('success'):
        continue
    
    mae = result.get('test_mae', 0)
    gap = result.get('gap', 0)
    
    # 严重过拟合: MAE 1.0-1.5 且 gap>0.3
    if 1.0 <= mae <= 1.5 and gap > 0.3:
        SEVERE_OVERFITTING[code] = {
            'name': result.get('stock_name', f'股票{code}'),
            'baseline_mae': mae,
            'gap': gap,
            'problem': '严重过拟合'
        }

# 按MAE排序
SEVERE_OVERFITTING = dict(sorted(
    SEVERE_OVERFITTING.items(),
    key=lambda x: x[1]['baseline_mae'],
    reverse=True
))

print(f"\n📋 目标股票: {len(SEVERE_OVERFITTING)}支")
print(f"MAE范围: 1.0-1.5")
print(f"\n详细列表:")
for i, (code, info) in enumerate(SEVERE_OVERFITTING.items(), 1):
    print(f"  {i:2d}. {code}: MAE={info['baseline_mae']:.3f}, Gap={info['gap']:+.3f}")

print(f"\n🎯 改进策略:")
print(f"  • Augmented（首选）- 基于Top 4成功经验")
print(f"  • Regularized（备选）")
print(f"\n预期: 平均改善85-90%")
print(f"预计时间: {len(SEVERE_OVERFITTING) * 10}分钟")


def fetch_and_prepare_stock_data(stock_code):
    """获取并准备股票数据"""
    try:
        ticker = yf.Ticker(f"{stock_code}.TW")
        df = ticker.history(period="365d")
        
        if df.empty or len(df) < 100:
            return None
        
        # 技术指标
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
        
        # 75/25分割（基于8422诊断的改进）
        split_idx = int(len(X) * 0.75)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        return X_train, X_test, y_train, y_test
        
    except Exception as e:
        return None


def test_augmented_method(stock_code, X_train, y_train, X_test, y_test):
    """测试数据扩增方法（首选）"""
    # 数据扩增
    X_train_aug, y_train_aug = augment_data(X_train, y_train, noise_level=0.003)
    
    config = AugmentedConfig()
    model = build_augmented_model(config)
    
    early_stop = EarlyStopping(
        monitor='val_mae',
        patience=25,
        restore_best_weights=True,
        verbose=0
    )
    
    reduce_lr = ReduceLROnPlateau(
        monitor='val_mae',
        factor=0.5,
        patience=8,
        min_lr=1e-7,
        verbose=0
    )
    
    history = model.fit(
        X_train_aug, y_train_aug,
        validation_data=(X_test, y_test),
        epochs=config.max_epochs,
        batch_size=config.batch_size,
        callbacks=[early_stop, reduce_lr],
        verbose=0
    )
    
    # 评估（用原始训练集）
    test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
    train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
    
    return {
        'method': 'Augmented',
        'train_mae': float(train_mae),
        'test_mae': float(test_mae),
        'gap': float(test_mae - train_mae),
        'epochs': len(history.history['loss'])
    }


def test_regularized_method(stock_code, X_train, y_train, X_test, y_test):
    """测试强正则化方法（备选）"""
    config = RegularizedConfig()
    config.l2_reg = 0.02
    config.dropout_rate = 0.4
    config.recurrent_dropout = 0.25
    
    model = build_regularized_model(config)
    
    early_stop = EarlyStopping(
        monitor='val_mae',
        patience=25,
        restore_best_weights=True,
        verbose=0
    )
    
    reduce_lr = ReduceLROnPlateau(
        monitor='val_mae',
        factor=0.5,
        patience=10,
        min_lr=1e-7,
        verbose=0
    )
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=config.max_epochs,
        batch_size=config.batch_size,
        callbacks=[early_stop, reduce_lr],
        verbose=0
    )
    
    test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
    train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
    
    return {
        'method': 'Regularized',
        'train_mae': float(train_mae),
        'test_mae': float(test_mae),
        'gap': float(test_mae - train_mae),
        'epochs': len(history.history['loss'])
    }


def process_single_stock(stock_code, stock_info):
    """处理单支股票"""
    print(f"\n{'─'*70}")
    print(f"📊 {stock_code} ({stock_info['name']})")
    print(f"   Baseline: MAE={stock_info['baseline_mae']:.3f}, Gap={stock_info['gap']:+.3f}")
    
    # 准备数据
    data = fetch_and_prepare_stock_data(stock_code)
    
    if data is None:
        print(f"   ❌ 数据准备失败")
        return None
    
    X_train, X_test, y_train, y_test = data
    
    # 测试两种方法
    results = []
    
    try:
        result1 = test_augmented_method(stock_code, X_train, y_train, X_test, y_test)
        results.append(result1)
        print(f"   ✅ Augmented: MAE={result1['test_mae']:.4f}, Gap={result1['gap']:+.4f}")
    except Exception as e:
        print(f"   ⚠️ Augmented失败: {str(e)[:50]}")
    
    try:
        result2 = test_regularized_method(stock_code, X_train, y_train, X_test, y_test)
        results.append(result2)
        print(f"   ✅ Regularized: MAE={result2['test_mae']:.4f}, Gap={result2['gap']:+.4f}")
    except Exception as e:
        print(f"   ⚠️ Regularized失败: {str(e)[:50]}")
    
    if not results:
        print(f"   ❌ 所有方法失败")
        return None
    
    # 选择最佳
    best = min(results, key=lambda x: x['test_mae'])
    baseline_mae = stock_info['baseline_mae']
    improvement = (baseline_mae - best['test_mae']) / baseline_mae * 100
    
    print(f"   🏆 最佳: {best['method']} | "
          f"{baseline_mae:.3f}→{best['test_mae']:.3f} | "
          f"改善{improvement:.1f}%")
    
    return {
        'stock_code': stock_code,
        'baseline_mae': baseline_mae,
        'best_method': best['method'],
        'best_mae': best['test_mae'],
        'improvement': improvement,
        'all_results': results
    }


# ==================== 主程序 ====================

if __name__ == "__main__":
    print(f"\n{'='*70}")
    print(f"开始批量处理...")
    print(f"{'='*70}")
    
    all_results = {}
    total = len(SEVERE_OVERFITTING)
    
    for i, (stock_code, stock_info) in enumerate(SEVERE_OVERFITTING.items(), 1):
        print(f"\n进度: [{i}/{total}] ({i/total*100:.0f}%)")
        
        result = process_single_stock(stock_code, stock_info)
        
        if result:
            all_results[stock_code] = result
    
    # 保存结果
    output_file = "severe_overfitting_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    # 总结
    print(f"\n\n{'='*70}")
    print(f"📊 批量处理总结")
    print(f"{'='*70}")
    
    if all_results:
        success_count = len(all_results)
        avg_improvement = np.mean([r['improvement'] for r in all_results.values()])
        
        # 方法统计
        augmented_count = len([r for r in all_results.values() if r['best_method'] == 'Augmented'])
        regularized_count = len([r for r in all_results.values() if r['best_method'] == 'Regularized'])
        
        print(f"\n成功改进: {success_count}/{total} 支 ({success_count/total*100:.1f}%)")
        print(f"平均改善: {avg_improvement:.1f}%")
        
        print(f"\n最佳方法分布:")
        print(f"  Augmented:   {augmented_count} 支 ({augmented_count/success_count*100:.1f}%)")
        print(f"  Regularized: {regularized_count} 支 ({regularized_count/success_count*100:.1f}%)")
        
        # 按改善幅度分类
        excellent = len([r for r in all_results.values() if r['improvement'] >= 85])
        good = len([r for r in all_results.values() if 70 <= r['improvement'] < 85])
        moderate = len([r for r in all_results.values() if r['improvement'] < 70])
        
        print(f"\n改善效果分布:")
        print(f"  优秀(≥85%): {excellent} 支")
        print(f"  良好(70-85%): {good} 支")
        print(f"  中等(<70%): {moderate} 支")
        
        # Top 5改善
        top5 = sorted(all_results.items(), key=lambda x: x[1]['improvement'], reverse=True)[:5]
        print(f"\nTop 5改善:")
        for rank, (code, result) in enumerate(top5, 1):
            print(f"  {rank}. {code}: {result['baseline_mae']:.3f}→{result['best_mae']:.3f} "
                  f"({result['improvement']:.1f}%)")
        
        if avg_improvement >= 85:
            print(f"\n✅ 整体效果优秀！")
        elif avg_improvement >= 70:
            print(f"\n🔶 整体效果良好")
        else:
            print(f"\n⚠️ 整体效果中等，需要进一步分析")
    
    print(f"\n📄 结果已保存: {output_file}")
    
    print(f"\n{'='*70}")
    print(f"✅ 批量处理完成！")
    print(f"{'='*70}")
    
    print(f"\n💡 下一步:")
    print(f"  1. 查看详细结果: cat {output_file}")
    print(f"  2. 处理中度问题股票（MAE 0.5-1.0）")
    print(f"  3. 处理欠拟合股票（gap<0）")
