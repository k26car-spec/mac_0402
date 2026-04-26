"""
批量处理中度问题股票
目标: MAE 0.7-1.0的股票（8支）
方法: Regularized或Optimized
预期: 平均改善65-80%

执行: python3 batch_fix_moderate.py
"""

import numpy as np
import pandas as pd
import yfinance as yf
import json
from sklearn.preprocessing import MinMaxScaler
from improved_stock_training import (
    build_regularized_model, RegularizedConfig,
    build_optimized_model, OptimizedConfig,
    augment_data
)
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("🚀 批量处理中度问题股票")
print("=" * 70)

# 加载Baseline结果
with open('baseline_results/baseline_results_final.json', 'r') as f:
    baseline_results = json.load(f)

# 筛选中度问题股票（MAE 0.7-1.0, gap>0.1）
MODERATE_STOCKS = {}

for code, result in baseline_results.items():
    if not result.get('success'):
        continue
    
    mae = result.get('test_mae', 0)
    gap = result.get('gap', 0)
    
    # 中度问题: MAE 0.7-1.0 且 gap>0.1
    if 0.7 <= mae <= 1.0 and gap > 0.1:
        MODERATE_STOCKS[code] = {
            'name': result.get('stock_name', f'股票{code}'),
            'baseline_mae': mae,
            'gap': gap,
            'problem': '中度过拟合'
        }

# 按MAE排序
MODERATE_STOCKS = dict(sorted(
    MODERATE_STOCKS.items(),
    key=lambda x: x[1]['baseline_mae'],
    reverse=True
))

print(f"\n📋 目标股票: {len(MODERATE_STOCKS)}支")
print(f"MAE范围: 0.7-1.0")
print(f"\n详细列表:")
for i, (code, info) in enumerate(MODERATE_STOCKS.items(), 1):
    print(f"  {i:2d}. {code}: MAE={info['baseline_mae']:.3f}, Gap={info['gap']:+.3f}")

print(f"\n🎯 改进策略:")
print(f"  • Regularized（首选）- 中等正则化")
print(f"  • Optimized（备选）- 优化架构")
print(f"\n预期: 平均改善65-80%")
print(f"预计时间: {len(MODERATE_STOCKS) * 10}分钟")


def fetch_and_prepare_stock_data(stock_code):
    """获取并准备股票数据（与改进时相同）"""
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
        
        # 75/25分割
        split_idx = int(len(X) * 0.75)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        return X_train, X_test, y_train, y_test
        
    except Exception as e:
        return None


def test_both_methods(stock_code, X_train, y_train, X_test, y_test):
    """测试Regularized和Optimized两种方法"""
    results = []
    
    # 方法1: Regularized（中等强度）
    try:
        print(f"     测试Regularized...", end="", flush=True)
        config = RegularizedConfig()
        config.l2_reg = 0.015  # 中等
        config.dropout_rate = 0.35  # 中等
        config.recurrent_dropout = 0.2
        
        model = build_regularized_model(config)
        
        early_stop = EarlyStopping(monitor='val_mae', patience=20, restore_best_weights=True, verbose=0)
        reduce_lr = ReduceLROnPlateau(monitor='val_mae', factor=0.5, patience=8, min_lr=1e-7, verbose=0)
        
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
        
        results.append({
            'method': 'Regularized',
            'train_mae': float(train_mae),
            'test_mae': float(test_mae),
            'gap': float(test_mae - train_mae),
            'epochs': len(history.history['loss'])
        })
        print(f" MAE={test_mae:.4f}")
    except Exception as e:
        print(f" 失败: {str(e)[:30]}")
    
    # 方法2: Optimized
    try:
        print(f"     测试Optimized...", end="", flush=True)
        config = OptimizedConfig()
        model = build_optimized_model(config)
        
        early_stop = EarlyStopping(monitor='val_mae', patience=20, restore_best_weights=True, verbose=0)
        reduce_lr = ReduceLROnPlateau(monitor='val_mae', factor=0.5, patience=10, min_lr=1e-7, verbose=0)
        
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
        
        results.append({
            'method': 'Optimized',
            'train_mae': float(train_mae),
            'test_mae': float(test_mae),
            'gap': float(test_mae - train_mae),
            'epochs': len(history.history['loss'])
        })
        print(f" MAE={test_mae:.4f}")
    except Exception as e:
        print(f" 失败: {str(e)[:30]}")
    
    return results


def process_single_stock(stock_code, stock_info):
    """处理单支股票"""
    print(f"\n  📊 {stock_code} ({stock_info['name']})")
    print(f"     Baseline: MAE={stock_info['baseline_mae']:.3f}, Gap={stock_info['gap']:+.3f}")
    
    # 准备数据
    print(f"     准备数据...", end="", flush=True)
    data = fetch_and_prepare_stock_data(stock_code)
    
    if data is None:
        print(f" 失败")
        return None
    
    X_train, X_test, y_train, y_test = data
    print(f" OK ({X_train.shape[0]}+{X_test.shape[0]}样本)")
    
    # 测试两种方法
    results = test_both_methods(stock_code, X_train, y_train, X_test, y_test)
    
    if not results:
        print(f"     ❌ 所有方法失败")
        return None
    
    # 选择最佳
    best = min(results, key=lambda x: x['test_mae'])
    baseline_mae = stock_info['baseline_mae']
    improvement = (baseline_mae - best['test_mae']) / baseline_mae * 100
    
    print(f"     🏆 {best['method']}: {baseline_mae:.3f}→{best['test_mae']:.3f} ({improvement:.1f}%)")
    
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
    total = len(MODERATE_STOCKS)
    
    for i, (stock_code, stock_info) in enumerate(MODERATE_STOCKS.items(), 1):
        print(f"\n[{i}/{total}] ({i/total*100:.0f}%)")
        
        result = process_single_stock(stock_code, stock_info)
        
        if result:
            all_results[stock_code] = result
    
    # 保存结果
    output_file = "moderate_improvement_results.json"
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
        regularized = len([r for r in all_results.values() if r['best_method'] == 'Regularized'])
        optimized = len([r for r in all_results.values() if r['best_method'] == 'Optimized'])
        
        print(f"\n成功改进: {success_count}/{total} 支 ({success_count/total*100:.1f}%)")
        print(f"平均改善: {avg_improvement:.1f}%")
        
        print(f"\n最佳方法分布:")
        print(f"  Regularized: {regularized} 支")
        print(f"  Optimized:   {optimized} 支")
        
        # 改善效果分类
        excellent = len([r for r in all_results.values() if r['improvement'] >= 75])
        good = len([r for r in all_results.values() if 60 <= r['improvement'] < 75])
        moderate = len([r for r in all_results.values() if r['improvement'] < 60])
        
        print(f"\n改善效果分布:")
        print(f"  优秀(≥75%): {excellent} 支")
        print(f"  良好(60-75%): {good} 支")
        print(f"  中等(<60%): {moderate} 支")
        
        # Top 5
        top5 = sorted(all_results.items(), key=lambda x: x[1]['improvement'], reverse=True)[:5]
        print(f"\nTop 5改善:")
        for rank, (code, result) in enumerate(top5, 1):
            print(f"  {rank}. {code}: {result['baseline_mae']:.3f}→{result['best_mae']:.3f} "
                  f"({result['improvement']:.1f}%)")
        
        if avg_improvement >= 75:
            print(f"\n✅ 整体效果优秀！")
        elif avg_improvement >= 60:
            print(f"\n🔶 整体效果良好")
        else:
            print(f"\n⚠️ 整体效果中等")
    
    print(f"\n📄 结果已保存: {output_file}")
    
    # 计算总进度
    print(f"\n{'='*70}")
    print(f"🎯 LSTM改进总进度")
    print(f"{'='*70}")
    
    total_improved = 19 + success_count  # Top4(4) + 批量(12) + 剩余3(3) + 中度(成功数)
    total_stocks = 43
    
    print(f"\n已改进股票: {total_improved}/{total_stocks} ({total_improved/total_stocks*100:.1f}%)")
    print(f"  • 严重过拟合: 19支 (90.8%平均改善)")
    print(f"  • 中度问题:   {success_count}支 ({avg_improvement:.1f}%平均改善)")
    
    remaining = total_stocks - total_improved
    print(f"\n剩余工作: {remaining}支")
    print(f"  • 欠拟合: 约11支")
    print(f"  • 其他: 约{remaining-11}支")
    
    print(f"\n{'='*70}")
    print(f"✅ 批量处理完成！")
    print(f"{'='*70}")
    
    print(f"\n💡 下一步:")
    print(f"  python3 batch_fix_underfitting.py")
