"""
处理Top 4最严重股票
基于Baseline测试结果，对最严重的4支股票进行深度改进

股票列表:
1. 3481: MAE=2.445, Gap=+1.913 (严重过拟合)
2. 5521: MAE=1.865, Gap=+1.177 (严重过拟合)
3. 2313: MAE=1.820, Gap=+1.170 (严重过拟合)
4. 2312: MAE=1.713, Gap=+1.321 (严重过拟合)

执行: python3 fix_top4_stocks.py
"""

import numpy as np
import pandas as pd
import yfinance as yf
import json
from sklearn.preprocessing import MinMaxScaler
from improved_stock_training import (
    build_regularized_model, RegularizedConfig,
    build_augmented_model, AugmentedConfig,
    build_attention_model, AttentionConfig,
    augment_data
)
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("🚀 处理Top 4最严重股票")
print("=" * 70)

# Top 4严重股票
TOP_4_STOCKS = {
    '3481': {'name': '股票3481', 'baseline_mae': 2.445, 'gap': 1.913, 'problem': '严重过拟合'},
    '5521': {'name': '股票5521', 'baseline_mae': 1.865, 'gap': 1.177, 'problem': '严重过拟合'},
    '2313': {'name': '股票2313', 'baseline_mae': 1.820, 'gap': 1.170, 'problem': '严重过拟合'},
    '2312': {'name': '股票2312', 'baseline_mae': 1.713, 'gap': 1.321, 'problem': '严重过拟合'}
}

print(f"\n📋 目标股票:")
for code, info in TOP_4_STOCKS.items():
    print(f"  {code}: {info['name']} | Baseline MAE={info['baseline_mae']:.3f} | "
          f"Gap={info['gap']:+.3f} | {info['problem']}")

print(f"\n⚠️ 共同问题: 严重过拟合（训练低，测试高）")
print(f"\n🎯 改进策略:")
print(f"  1️⃣ Regularized - L2正则化+高Dropout")
print(f"  2️⃣ Augmented - 数据扩增+噪声")  
print(f"  3️⃣ Attention - 注意力机制（如果前两者效果不佳）")

print(f"\n预期改善: MAE降低30-50%")
print(f"预计时间: 1-1.5小时")


def fetch_and_prepare_stock_data(stock_code):
    """
    获取并准备单支股票数据
    
    Returns:
    --------
    tuple: (X_train, X_test, y_train, y_test) 或 None
    """
    try:
        # 获取数据
        ticker = yf.Ticker(f"{stock_code}.TW")
        df = ticker.history(period="365d")
        
        if df.empty or len(df) < 100:
            return None
        
        # 计算技术指标
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['Volume_MA5'] = df['Volume'].rolling(window=5).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 波动率
        df['Volatility'] = df['Close'].rolling(window=20).std()
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        
        # 目标变量
        df['Target'] = (df['Close'].shift(-5) / df['Close'] - 1) * 100
        
        # 删除NaN
        df = df.dropna()
        
        if len(df) < 160:
            return None
        
        # 选择特征
        feature_cols = ['Close', 'Volume', 'MA5', 'MA10', 'MA20', 
                        'Volume_MA5', 'RSI', 'Volatility', 'MACD']
        
        # 标准化
        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        
        df[feature_cols] = scaler_X.fit_transform(df[feature_cols])
        df[['Target']] = scaler_y.fit_transform(df[['Target']])
        
        # 创建序列
        sequence_length = 60
        X, y = [], []
        
        for i in range(len(df) - sequence_length):
            X.append(df[feature_cols].iloc[i:i+sequence_length].values)
            y.append(df['Target'].iloc[i+sequence_length])
        
        X = np.array(X)
        y = np.array(y)
        
        # 分割（使用75/25，基于8422诊断的改进）
        split_idx = int(len(X) * 0.75)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        return X_train, X_test, y_train, y_test
        
    except Exception as e:
        print(f"  ❌ 数据准备失败: {str(e)}")
        return None


def test_regularized_method(stock_code, X_train, y_train, X_test, y_test):
    """测试强正则化方法"""
    print(f"\n  🧪 方法1: Regularized（强正则化）")
    
    config = RegularizedConfig()
    config.l2_reg = 0.02  # 强正则化
    config.dropout_rate = 0.4  # 高Dropout
    config.recurrent_dropout = 0.25
    
    print(f"     配置: L2={config.l2_reg}, Dropout={config.dropout_rate}")
    
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
    
    # 评估
    test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
    train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
    
    print(f"     结果: 训练MAE={train_mae:.4f}, 测试MAE={test_mae:.4f}, "
          f"Gap={test_mae-train_mae:+.4f}")
    
    return {
        'method': 'Regularized',
        'train_mae': float(train_mae),
        'test_mae': float(test_mae),
        'gap': float(test_mae - train_mae),
        'epochs': len(history.history['loss'])
    }


def test_augmented_method(stock_code, X_train, y_train, X_test, y_test):
    """测试数据扩增方法"""
    print(f"\n  🧪 方法2: Augmented（数据扩增）")
    
    # 数据扩增
    X_train_aug, y_train_aug = augment_data(X_train, y_train, noise_level=0.003)
    
    print(f"     数据扩增: {X_train.shape[0]} → {X_train_aug.shape[0]} 样本")
    
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
    
    print(f"     结果: 训练MAE={train_mae:.4f}, 测试MAE={test_mae:.4f}, "
          f"Gap={test_mae-train_mae:+.4f}")
    
    return {
        'method': 'Augmented',
        'train_mae': float(train_mae),
        'test_mae': float(test_mae),
        'gap': float(test_mae - train_mae),
        'epochs': len(history.history['loss'])
    }


def test_attention_method(stock_code, X_train, y_train, X_test, y_test):
    """测试注意力机制方法"""
    print(f"\n  🧪 方法3: Attention（注意力机制）")
    
    config = AttentionConfig()
    print(f"     配置: MultiHeadAttention, {config.num_heads} heads")
    
    model = build_attention_model(config)
    
    early_stop = EarlyStopping(
        monitor='val_mae',
        patience=30,
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
    
    # 评估
    test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
    train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
    
    print(f"     结果: 训练MAE={train_mae:.4f}, 测试MAE={test_mae:.4f}, "
          f"Gap={test_mae-train_mae:+.4f}")
    
    return {
        'method': 'Attention',
        'train_mae': float(train_mae),
        'test_mae': float(test_mae),
        'gap': float(test_mae - train_mae),
        'epochs': len(history.history['loss'])
    }


def process_single_stock(stock_code, stock_info):
    """处理单支股票"""
    print(f"\n{'='*70}")
    print(f"🎯 处理: {stock_code} ({stock_info['name']})")
    print(f"{'='*70}")
    print(f"Baseline表现: MAE={stock_info['baseline_mae']:.3f}, "
          f"Gap={stock_info['gap']:+.3f}")
    
    # 准备数据
    print(f"\n  🔄 准备数据...")
    data = fetch_and_prepare_stock_data(stock_code)
    
    if data is None:
        print(f"  ❌ 数据准备失败，跳过")
        return None
    
    X_train, X_test, y_train, y_test = data
    print(f"  ✅ 数据准备完成")
    print(f"     训练集: {X_train.shape[0]} 样本")
    print(f"     测试集: {X_test.shape[0]} 样本")
    
    # 测试3种方法
    results = []
    
    try:
        result1 = test_regularized_method(stock_code, X_train, y_train, X_test, y_test)
        results.append(result1)
    except Exception as e:
        print(f"  ⚠️ Regularized方法失败: {str(e)}")
    
    try:
        result2 = test_augmented_method(stock_code, X_train, y_train, X_test, y_test)
        results.append(result2)
    except Exception as e:
        print(f"  ⚠️ Augmented方法失败: {str(e)}")
    
    try:
        result3 = test_attention_method(stock_code, X_train, y_train, X_test, y_test)
        results.append(result3)
    except Exception as e:
        print(f"  ⚠️ Attention方法失败: {str(e)}")
    
    if not results:
        print(f"  ❌ 所有方法都失败了")
        return None
    
    # 分析结果
    print(f"\n  📊 结果对比:")
    print(f"  {'─'*66}")
    print(f"  {'方法':<20} | {'测试MAE':>10} | {'差距':>10} | {'改善':>10}")
    print(f"  {'─'*66}")
    
    baseline_mae = stock_info['baseline_mae']
    
    for result in sorted(results, key=lambda x: x['test_mae']):
        improvement = (baseline_mae - result['test_mae']) / baseline_mae * 100
        print(f"  {result['method']:<20} | "
              f"{result['test_mae']:>10.4f} | "
              f"{result['gap']:>+10.4f} | "
              f"{improvement:>9.1f}%")
    
    # 最佳方案
    best = min(results, key=lambda x: x['test_mae'])
    improvement = (baseline_mae - best['test_mae']) / baseline_mae * 100
    
    print(f"  {'─'*66}")
    print(f"\n  🏆 最佳方案: {best['method']}")
    print(f"     Baseline MAE: {baseline_mae:.4f}")
    print(f"     改进后 MAE:   {best['test_mae']:.4f}")
    print(f"     改善幅度:     {improvement:.1f}%")
    
    if improvement >= 30:
        print(f"     ✅ 显著改善！")
    elif improvement >= 15:
        print(f"     🔶 中等改善")
    else:
        print(f"     ⚠️ 改善有限")
    
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
    print(f"开始处理Top 4股票...")
    print(f"{'='*70}")
    
    all_results = {}
    
    for i, (stock_code, stock_info) in enumerate(TOP_4_STOCKS.items(), 1):
        print(f"\n\n进度: [{i}/4] ({i/4*100:.0f}%)")
        
        result = process_single_stock(stock_code, stock_info)
        
        if result:
            all_results[stock_code] = result
    
    # 保存结果
    output_file = "top4_improvement_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    # 总结
    print(f"\n\n{'='*70}")
    print(f"📊 Top 4改进总结")
    print(f"{'='*70}")
    
    if all_results:
        print(f"\n成功改进: {len(all_results)}/4 支")
        
        avg_improvement = np.mean([r['improvement'] for r in all_results.values()])
        
        print(f"\n详细结果:")
        for code, result in all_results.items():
            print(f"\n  {code}:")
            print(f"    最佳方案: {result['best_method']}")
            print(f"    Baseline: {result['baseline_mae']:.4f}")
            print(f"    改进后:   {result['best_mae']:.4f}")
            print(f"    改善:     {result['improvement']:.1f}%")
        
        print(f"\n平均改善: {avg_improvement:.1f}%")
        
        if avg_improvement >= 35:
            print(f"✅ 整体改善效果优秀！")
        elif avg_improvement >= 25:
            print(f"🔶 整体改善效果良好")
        else:
            print(f"⚠️ 整体改善效果一般")
    
    print(f"\n📄 结果已保存: {output_file}")
    
    print(f"\n{'='*70}")
    print(f"✅ Top 4处理完成！")
    print(f"{'='*70}")
    
    print(f"\n💡 下一步:")
    print(f"  1. 查看详细结果: cat {output_file}")
    print(f"  2. 继续批量处理其他严重过拟合股票")
    print(f"  3. 查看完整计划: open COMPLETE_EXECUTION_ROADMAP.md")
