#!/usr/bin/env python3
"""
LSTM模型自动优化训练脚本
Automated Hyperparameter Optimization for LSTM

功能:
1. 测试多种模型配置
2. 自动选择最佳模型
3. 保存优化结果
"""

import numpy as np
import os
import json
from datetime import datetime
from train_lstm import load_prepared_data, train_model, evaluate_model, save_model_and_results
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout


def build_lstm_model_custom(input_shape, layers, dropout):
    """
    构建自定义LSTM模型
    
    Args:
        input_shape: 输入形状 (sequence_length, features)
        layers: LSTM层的单元数列表
        dropout: Dropout比例
    
    Returns:
        model: 编译好的模型
    """
    print(f"\n🔨 构建LSTM模型...")
    print(f"   输入形状: {input_shape}")
    print(f"   LSTM层: {layers}")
    print(f"   Dropout: {dropout}")
    
    model = Sequential()
    
    # 第一层LSTM
    model.add(LSTM(units=layers[0], return_sequences=True, input_shape=input_shape))
    model.add(Dropout(dropout))
    
    # 中间LSTM层
    for units in layers[1:-1]:
        model.add(LSTM(units=units, return_sequences=True))
        model.add(Dropout(dropout))
    
    # 最后一层LSTM
    model.add(LSTM(units=layers[-1]))
    model.add(Dropout(dropout))
    
    # 输出层
    model.add(Dense(units=1))
    
    # 编译模型
    model.compile(optimizer='adam', loss='mean_squared_error', metrics=['mae'])
    
    print(f"✅ 模型构建完成")
    print(f"   总参数: {model.count_params():,}")
    
    return model


def test_configuration(symbol, config, data):
    """
    测试单个配置
    
    Args:
        symbol: 股票代码
        config: 配置字典
        data: 训练数据
    
    Returns:
        配置和结果
    """
    print("\n" + "="*70)
    print(f"🧪 测试配置: {config['name']}")
    print("="*70)
    
    # 构建模型
    input_shape = (data['X_train'].shape[1], data['X_train'].shape[2])
    model = build_lstm_model_custom(
        input_shape, 
        config['layers'], 
        config['dropout']
    )
    
    # 训练模型
    history = train_model(
        model,
        data['X_train'], data['y_train'],
        data['X_val'], data['y_val'],
        epochs=config['epochs'],
        batch_size=config['batch_size'],
        patience=config['patience']
    )
    
    # 评估模型
    metrics = evaluate_model(model, data['X_test'], data['y_test'], symbol)
    
    # 添加配置信息到结果
    result = {
        'config': config,
        'metrics': metrics,
        'training_epochs': len(history.history['loss']),
        'final_train_loss': float(history.history['loss'][-1]),
        'final_val_loss': float(history.history['val_loss'][-1])
    }
    
    return result, model, history


def optimize_hyperparameters(symbol):
    """
    自动优化超参数
    
    Args:
        symbol: 股票代码
    """
    print("\n" + "="*70)
    print(f"🚀 开始自动优化 {symbol} 模型")
    print("="*70)
    
    # 加载数据
    data = load_prepared_data(symbol)
    if data is None:
        return
    
    # 定义要测试的配置
    configurations = [
        {
            'name': 'Baseline',
            'layers': [64, 64, 32],
            'dropout': 0.2,
            'epochs': 50,
            'batch_size': 32,
            'patience': 10
        },
        {
            'name': 'Deeper Model',
            'layers': [128, 128, 64],
            'dropout': 0.3,
            'epochs': 100,
            'batch_size': 32,
            'patience': 15
        },
        {
            'name': 'Wider Model',
            'layers': [128, 64],
            'dropout': 0.25,
            'epochs': 80,
            'batch_size': 32,
            'patience': 12
        },
        {
            'name': 'High Dropout',
            'layers': [96, 96, 48],
            'dropout': 0.4,
            'epochs': 60,
            'batch_size': 16,
            'patience': 10
        },
        {
            'name': 'Small Batch',
            'layers': [64, 64, 32],
            'dropout': 0.3,
            'epochs': 60,
            'batch_size': 16,
            'patience': 12
        }
    ]
    
    results = []
    best_score = float('inf')
    best_config = None
    best_model = None
    best_history = None
    
    # 测试每个配置
    for i, config in enumerate(configurations, 1):
        print(f"\n\n{'='*70}")
        print(f"进度: {i}/{len(configurations)}")
        print(f"{'='*70}")
        
        try:
            result, model, history = test_configuration(symbol, config, data)
            results.append(result)
            
            # 使用综合评分：MAPE + (1 - 方向准确率)
            score = result['metrics']['mape'] + (1 - result['metrics']['direction_accuracy']) * 100
            
            print(f"\n📊 配置评分: {score:.2f}")
            print(f"   MAPE: {result['metrics']['mape']:.2f}%")
            print(f"   方向准确率: {result['metrics']['direction_accuracy']:.2%}")
            
            if score < best_score:
                best_score = score
                best_config = config
                best_model = model
                best_history = history
                print(f"✨ 新的最佳配置！")
            
        except Exception as e:
            print(f"❌ 配置失败: {e}")
            results.append({
                'config': config,
                'error': str(e)
            })
    
    # 保存最佳模型
    if best_model is not None:
        print("\n" + "="*70)
        print("🏆 最佳配置")
        print("="*70)
        print(f"\n配置: {best_config['name']}")
        print(f"层数: {best_config['layers']}")
        print(f"Dropout: {best_config['dropout']}")
        print(f"批次大小: {best_config['batch_size']}")
        
        best_result = next(r for r in results if r.get('config', {}).get('name') == best_config['name'])
        print(f"\n性能:")
        print(f"  MAPE: {best_result['metrics']['mape']:.2f}%")
        print(f"  方向准确率: {best_result['metrics']['direction_accuracy']:.2%}")
        print(f"  R²: {best_result['metrics']['r2']:.4f}")
        print(f"  RMSE: {best_result['metrics']['rmse']:.2f}")
        
        # 保存最佳模型
        save_model_and_results(
            best_model, 
            best_history, 
            best_result['metrics'], 
            f"{symbol}_optimized"
        )
        
        # 保存优化报告
        report = {
            'symbol': symbol,
            'optimization_date': datetime.now().isoformat(),
            'configurations_tested': len(configurations),
            'best_config': best_config,
            'best_metrics': best_result['metrics'],
            'all_results': results
        }
        
        report_path = f"models/lstm/{symbol}_optimization_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n✅ 优化报告已保存: {report_path}")
    
    # 打印对比表格
    print("\n" + "="*70)
    print("📊 所有配置对比")
    print("="*70)
    print(f"\n{'配置':<20} {'MAPE':<10} {'方向准确率':<12} {'R²':<10} {'评分':<10}")
    print("-" * 70)
    
    for result in results:
        if 'error' in result:
            continue
        config_name = result['config']['name']
        mape = result['metrics']['mape']
        dir_acc = result['metrics']['direction_accuracy']
        r2 = result['metrics']['r2']
        score = mape + (1 - dir_acc) * 100
        
        marker = "✨" if config_name == best_config['name'] else "  "
        print(f"{marker}{config_name:<18} {mape:<10.2f} {dir_acc*100:<12.2f} {r2:<10.4f} {score:<10.2f}")
    
    print("\n" + "="*70)
    print("✅ 优化完成！")
    print("="*70)


def main():
    """主函数"""
    print("\n" + "="*70)
    print("🎯 LSTM自动超参数优化系统")
    print("="*70)
    print("\n⚡ 将测试5种不同配置，找出最佳模型")
    print("⏰ 预计时间: 10-15分钟（取决于硬件）")
    
    # 优化股票列表
    stocks = ["2330"]  # 可以添加更多: ["2330", "2317", "2454"]
    
    print(f"\n📋 计划优化: {', '.join(stocks)}")
    
    input("\n按Enter开始优化...")
    
    for symbol in stocks:
        optimize_hyperparameters(symbol)
        print("\n")
    
    print("="*70)
    print("🎉 所有优化完成！")
    print("="*70)
    print("\n📁 最佳模型保存为: models/lstm/{symbol}_optimized_model.h5")
    print("📊 优化报告保存为: models/lstm/{symbol}_optimization_report.json")


if __name__ == "__main__":
    main()
