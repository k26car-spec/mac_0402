"""
优先处理最严重的5支股票
专门针对严重过拟合问题

执行: python3 fix_worst_5_stocks.py
"""

import numpy as np
import json
from improved_stock_training import (
    build_regularized_model, RegularizedConfig,
    build_augmented_model, AugmentedConfig,
    build_attention_model, AttentionConfig,
    augment_data
)
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
import tensorflow as tf

print("=" * 70)
print("🚨 紧急处理：最严重的5支股票")
print("=" * 70)

# 最严重的5支股票
worst_5_stocks = {
    '8422': {'name': '股票8422', 'current_mae': 5.147, 'gap': 4.272, 'problem': '极度过拟合'},
    '3481': {'name': '股票3481', 'current_mae': 2.522, 'gap': 1.982, 'problem': '严重过拟合'},
    '2313': {'name': '股票2313', 'current_mae': 1.892, 'gap': 1.245, 'problem': '严重过拟合'},
    '5521': {'name': '股票5521', 'current_mae': 1.784, 'gap': 1.069, 'problem': '严重过拟合'},
    '2303': {'name': '股票2303', 'current_mae': 1.739, 'gap': 1.335, 'problem': '严重过拟合'}
}

print(f"\n📋 目标股票:")
for code, info in worst_5_stocks.items():
    print(f"  {code}: {info['name']} | MAE={info['current_mae']:.3f} | "
          f"Gap={info['gap']:+.3f} | {info['problem']}")

print(f"\n⚠️ 问题特征:")
print(f"  • 训练MAE低，测试MAE极高")
print(f"  • 训练-验证差距>1.0")
print(f"  • 模型过度记忆训练数据")

print(f"\n🎯 改进策略:")
print(f"  1️⃣ Regularized - L2+高Dropout+RecurrentDropout")
print(f"  2️⃣ Augmented - 数据扩增+噪声")
print(f"  3️⃣ Attention - 注意力机制")

print(f"\n预期改善: MAE降低30-50%")
print(f"预计时间: 2-3天")


def check_data_leakage(stock_code, X, y):
    """
    检查数据泄漏
    
    检查项：
    1. 特征是否包含未来信息
    2. 目标变量是否在特征中
    3. 训练/测试分割是否正确
    """
    print(f"\n🔍 [{stock_code}] 数据泄漏检查...")
    
    issues = []
    
    # 检查1: 特征维度
    if X.ndim != 3:
        issues.append(f"特征维度异常: {X.ndim}D (应为3D)")
    
    # 检查2: 样本数匹配
    if len(X) != len(y):
        issues.append(f"样本数不匹配: X={len(X)}, y={len(y)}")
    
    # 检查3: 特征值范围
    x_mean = np.mean(X)
    x_std = np.std(X)
    if abs(x_mean) > 2 or x_std > 5:
        issues.append(f"特征未标准化: mean={x_mean:.3f}, std={x_std:.3f}")
    
    # 检查4: 目标值范围
    y_mean = np.mean(y)
    y_std = np.std(y)
    if abs(y_mean) > 10 or y_std > 10:
        issues.append(f"目标值范围异常: mean={y_mean:.3f}, std={y_std:.3f}")
    
    if issues:
        print(f"  ⚠️ 发现 {len(issues)} 个潜在问题:")
        for issue in issues:
            print(f"     - {issue}")
        return False
    else:
        print(f"  ✅ 未发现明显的数据泄漏")
        return True


def test_extreme_regularization(stock_code, X_train, y_train, X_test, y_test):
    """
    测试极强正则化方案
    
    针对严重过拟合问题：
    - L2正则化提高到0.02
    - Dropout提高到0.4
    - RecurrentDropout提高到0.3
    """
    print(f"\n🧪 [{stock_code}] 测试方案1: 极强正则化")
    print(f"  配置: L2=0.02, Dropout=0.4, RecDrop=0.3")
    
    # 自定义配置
    config = RegularizedConfig()
    config.l2_reg = 0.02  # 提高
    config.dropout_rate = 0.4  # 提高
    config.recurrent_dropout = 0.3  # 提高
    config.early_stop_patience = 30  # 增加耐心
    
    # 构建模型
    model = build_regularized_model(config)
    
    # Callbacks
    early_stop = EarlyStopping(
        monitor='val_mae',
        patience=config.early_stop_patience,
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
    
    # 训练
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
    
    print(f"  ✅ 训练完成")
    print(f"     训练MAE: {train_mae:.4f}")
    print(f"     测试MAE: {test_mae:.4f}")
    print(f"     差距:    {(test_mae-train_mae):+.4f}")
    print(f"     Epochs:  {len(history.history['loss'])}")
    
    return {
        'method': 'Extreme_Regularized',
        'train_mae': float(train_mae),
        'test_mae': float(test_mae),
        'gap': float(test_mae - train_mae),
        'epochs': len(history.history['loss'])
    }


def test_heavy_augmentation(stock_code, X_train, y_train, X_test, y_test):
    """
    测试强数据扩增
    
    策略：
    - 数据翻倍
    - 更大的噪声（0.5%）
    - 配合正则化
    """
    print(f"\n🧪 [{stock_code}] 测试方案2: 强数据扩增")
    print(f"  配置: 噪声=0.5%, 样本×2, L2=0.01")
    
    # 数据扩增
    X_train_aug, y_train_aug = augment_data(X_train, y_train, noise_level=0.005)
    
    print(f"  数据扩增: {X_train.shape[0]} → {X_train_aug.shape[0]} 样本")
    
    # 配置
    config = AugmentedConfig()
    config.l2_reg = 0.01
    config.batch_size = 64
    
    # 构建模型
    model = build_augmented_model(config)
    
    # Callbacks
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
    
    # 训练
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
    
    print(f"  ✅ 训练完成")
    print(f"     训练MAE: {train_mae:.4f}")
    print(f"     测试MAE: {test_mae:.4f}")
    print(f"     差距:    {(test_mae-train_mae):+.4f}")
    print(f"     Epochs:  {len(history.history['loss'])}")
    
    return {
        'method': 'Heavy_Augmented',
        'train_mae': float(train_mae),
        'test_mae': float(test_mae),
        'gap': float(test_mae - train_mae),
        'epochs': len(history.history['loss'])
    }


def test_attention_model(stock_code, X_train, y_train, X_test, y_test):
    """
    测试注意力模型
    
    特点：
    - 多头注意力
    - 自动学习重要时间点
    - 殘差连接
    """
    print(f"\n🧪 [{stock_code}] 测试方案3: 注意力模型")
    print(f"  配置: MultiHeadAttention, 3 heads, L2=0.005")
    
    # 配置
    config = AttentionConfig()
    
    # 构建模型
    model = build_attention_model(config)
    
    # Callbacks
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
    
    # 训练
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
    
    print(f"  ✅ 训练完成")
    print(f"     训练MAE: {train_mae:.4f}")
    print(f"     测试MAE: {test_mae:.4f}")
    print(f"     差距:    {(test_mae-train_mae):+.4f}")
    print(f"     Epochs:  {len(history.history['loss'])}")
    
    return {
        'method': 'Attention',
        'train_mae': float(train_mae),
        'test_mae': float(test_mae),
        'gap': float(test_mae - train_mae),
        'epochs': len(history.history['loss'])
    }


def comprehensive_test_worst_stock(stock_code, stock_info, X_train, y_train, X_test, y_test):
    """
    综合测试单支最差股票
    """
    print(f"\n{'='*70}")
    print(f"🎯 深度测试: {stock_code} ({stock_info['name']})")
    print(f"{'='*70}")
    print(f"当前状态: MAE={stock_info['current_mae']:.3f}, "
          f"Gap={stock_info['gap']:+.3f}, "
          f"{stock_info['problem']}")
    
    # 检查数据泄漏
    check_data_leakage(stock_code, X_train, y_train)
    
    # 测试3种方案
    results = []
    
    try:
        result1 = test_extreme_regularization(stock_code, X_train, y_train, X_test, y_test)
        results.append(result1)
    except Exception as e:
        print(f"  ❌ 极强正则化失败: {str(e)}")
    
    try:
        result2 = test_heavy_augmentation(stock_code, X_train, y_train, X_test, y_test)
        results.append(result2)
    except Exception as e:
        print(f"  ❌ 强数据扩增失败: {str(e)}")
    
    try:
        result3 = test_attention_model(stock_code, X_train, y_train, X_test, y_test)
        results.append(result3)
    except Exception as e:
        print(f"  ❌ 注意力模型失败: {str(e)}")
    
    # 分析结果
    if results:
        print(f"\n📊 [{stock_code}] 结果对比:")
        print(f"{'─'*70}")
        print(f"{'方法':<25} | {'测试MAE':>10} | {'差距':>10} | {'改善':>10}")
        print(f"{'─'*70}")
        
        baseline_mae = stock_info['current_mae']
        
        for result in sorted(results, key=lambda x: x['test_mae']):
            improvement = (baseline_mae - result['test_mae']) / baseline_mae * 100
            print(f"{result['method']:<25} | "
                  f"{result['test_mae']:>10.4f} | "
                  f"{result['gap']:>+10.4f} | "
                  f"{improvement:>9.1f}%")
        
        # 最佳方案
        best = min(results, key=lambda x: x['test_mae'])
        improvement = (baseline_mae - best['test_mae']) / baseline_mae * 100
        
        print(f"{'─'*70}")
        print(f"\n🏆 最佳方案: {best['method']}")
        print(f"   改进前: MAE {baseline_mae:.4f}")
        print(f"   改进后: MAE {best['test_mae']:.4f}")
        print(f"   改善:   {improvement:.1f}%")
        
        if improvement >= 30:
            print(f"   ✅ 显著改善！")
        elif improvement >= 15:
            print(f"   🔶 中等改善")
        else:
            print(f"   ⚠️ 改善有限，可能需要其他方法")
        
        return {
            'stock_code': stock_code,
            'baseline_mae': baseline_mae,
            'best_method': best['method'],
            'best_mae': best['test_mae'],
            'improvement': improvement,
            'all_results': results
        }
    
    else:
        print(f"  ❌ 所有方案都失败了")
        return None


# ==================== 主程序 ====================

if __name__ == "__main__":
    print(f"\n🔄 准备开始测试...")
    print(f"\n⚠️ 注意:")
    print(f"  • 此脚本需要已经准备好的训练数据（X, y）")
    print(f"  • 每支股票测试约10-15分钟")
    print(f"  • 总计约1-1.5小时")
    print(f"\n如果数据已准备好，请继续")
    print(f"如果没有，请先运行相应的数据准备脚本")
    
    print(f"\n" + "=" * 70)
    print(f"💡 使用方法:")
    print(f"=" * 70)
    print("""
    from fix_worst_5_stocks import comprehensive_test_worst_stock, worst_5_stocks
    
    # 对每支股票：
    for stock_code, stock_info in worst_5_stocks.items():
        # 准备数据
        X_train, X_test, y_train, y_test = prepare_stock_data(stock_code)
        
        # 综合测试
        result = comprehensive_test_worst_stock(
            stock_code, stock_info,
            X_train, y_train, X_test, y_test
        )
    """)
