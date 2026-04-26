"""
自动股票分类和测试计划生成器
基于Baseline测试结果自动分类股票并生成测试计划

作者: AI Trading System
日期: 2026-02-08
版本: v1.0
"""

import numpy as np
import pandas as pd
import json
from typing import Dict, List, Tuple
from datetime import datetime


def auto_classify_stock(stock_code: str, baseline_results: Dict) -> Dict:
    """
    根据Baseline结果自动分类股票
    
    Parameters:
    -----------
    stock_code: str
        股票代码
    baseline_results: dict
        包含 test_mae, train_mae, gap 等指标
    
    Returns:
    --------
    dict: 分类结果和建议
    """
    test_mae = baseline_results.get('test_mae', baseline_results.get('val_mae', 0))
    train_mae = baseline_results.get('train_mae', 0)
    train_val_gap = baseline_results.get('gap', test_mae - train_mae)
    
    # 类型A：训练良好
    if test_mae < 0.06 and abs(train_val_gap) < 0.01:
        return {
            'stock_code': stock_code,
            'type': 'A',
            'type_name': '训练良好型',
            'test_mae': test_mae,
            'train_mae': train_mae,
            'gap': train_val_gap,
            'recommendation': 'Baseline',
            'action': '✅ 保持现有方案，无需改进',
            'priority': 'LOW',
            'expected_improvement': '0%（已经很好）',
            'test_methods': [],
            'estimated_hours': 0
        }
    
    # 类型B：严重问题
    elif test_mae > 0.10 or abs(train_val_gap) > 0.03:
        
        # 进一步细分问题类型
        if train_val_gap > 0.03:
            problem_type = '严重过拟合'
            methods = ['Regularized', 'Augmented', 'Optimized']
            improvement = '25-35%'
        elif test_mae > 0.15:
            problem_type = '预测能力差'
            methods = ['Larger', 'Attention', 'Optimized']
            improvement = '30-40%'
        else:
            problem_type = '泛化不佳'
            methods = ['Regularized', 'Larger', 'Attention']
            improvement = '20-30%'
        
        return {
            'stock_code': stock_code,
            'type': 'B',
            'type_name': '需要改进型',
            'test_mae': test_mae,
            'train_mae': train_mae,
            'gap': train_val_gap,
            'problem_type': problem_type,
            'recommendation': '测试多种方案',
            'action': '⚠️ 需要深入测试和优化',
            'priority': 'HIGH',
            'expected_improvement': improvement,
            'test_methods': methods,
            'estimated_hours': 4
        }
    
    # 类型C：中等难度
    else:
        return {
            'stock_code': stock_code,
            'type': 'C',
            'type_name': '中等难度型',
            'test_mae': test_mae,
            'train_mae': train_mae,
            'gap': train_val_gap,
            'problem_type': '可优化空间',
            'recommendation': 'Baseline 或 Optimized',
            'action': '🤔 可选择性优化',
            'priority': 'MEDIUM',
            'expected_improvement': '10-15%',
            'test_methods': ['Optimized', 'Attention'],
            'estimated_hours': 2
        }


def batch_classify(all_baseline_results: Dict) -> Dict:
    """
    批量分类所有股票
    
    Parameters:
    -----------
    all_baseline_results: dict
        {stock_code: {test_mae, train_mae, gap, ...}, ...}
    
    Returns:
    --------
    dict: 分类结果
    """
    classifications = {}
    
    for stock_code, results in all_baseline_results.items():
        classification = auto_classify_stock(stock_code, results)
        classifications[stock_code] = classification
    
    # 统计
    type_counts = {
        'A': len([c for c in classifications.values() if c['type'] == 'A']),
        'B': len([c for c in classifications.values() if c['type'] == 'B']),
        'C': len([c for c in classifications.values() if c['type'] == 'C'])
    }
    
    total = len(classifications)
    
    print("=" * 70)
    print("📊 股票分类统计")
    print("=" * 70)
    print(f"总股票数: {total} 支\n")
    print(f"类型A（训练良好）: {type_counts['A']:2d} 支 ({type_counts['A']/total*100:5.1f}%) ✅")
    print(f"类型B（需要改进）: {type_counts['B']:2d} 支 ({type_counts['B']/total*100:5.1f}%) ⚠️")
    print(f"类型C（中等难度）: {type_counts['C']:2d} 支 ({type_counts['C']/total*100:5.1f}%) 🤔")
    print("=" * 70)
    
    # 生成详细报告
    for type_key in ['B', 'C', 'A']:  # 按优先级排序
        stocks = [c for c in classifications.values() if c['type'] == type_key]
        if stocks:
            print(f"\n📋 {stocks[0]['type_name']} ({len(stocks)}支):")
            print("-" * 70)
            
            # 按MAE降序排列（问题最严重的优先）
            for stock in sorted(stocks, key=lambda x: x['test_mae'], reverse=True):
                print(f"  {stock['stock_code']:6s} | "
                      f"MAE={stock['test_mae']:.4f} | "
                      f"Gap={stock['gap']:+.4f} | "
                      f"建议={stock['recommendation']:12s} | "
                      f"{stock['action']}")
                
                # 如果是类型B，显示具体问题
                if type_key == 'B':
                    print(f"         问题: {stock['problem_type']} | "
                          f"测试方案: {', '.join(stock['test_methods'])}")
    
    return classifications


def generate_test_plan(classifications: Dict) -> Dict:
    """
    根据分类结果自动生成测试计划
    
    Parameters:
    -----------
    classifications: dict
        batch_classify返回的分类结果
    
    Returns:
    --------
    dict: 测试计划
    """
    plan = {
        'keep_baseline': [],
        'test_methods': {},
        'total_stocks': len(classifications),
        'estimated_hours': 0,
        'estimated_days': 0,
        'priority_high': [],
        'priority_medium': [],
        'priority_low': []
    }
    
    for stock_code, info in classifications.items():
        if info['type'] == 'A':
            plan['keep_baseline'].append(stock_code)
            plan['priority_low'].append(stock_code)
        
        elif info['type'] == 'B':
            plan['test_methods'][stock_code] = {
                'methods': info['test_methods'],
                'problem_type': info['problem_type'],
                'expected_improvement': info['expected_improvement']
            }
            plan['estimated_hours'] += info['estimated_hours']
            plan['priority_high'].append(stock_code)
        
        elif info['type'] == 'C':
            plan['test_methods'][stock_code] = {
                'methods': info['test_methods'],
                'problem_type': info['problem_type'],
                'expected_improvement': info['expected_improvement']
            }
            plan['estimated_hours'] += info['estimated_hours']
            plan['priority_medium'].append(stock_code)
    
    # 计算天数（每天工作8小时）
    plan['estimated_days'] = plan['estimated_hours'] / 8
    
    print("\n" + "=" * 70)
    print("🎯 测试计划生成")
    print("=" * 70)
    print(f"\n总股票数: {plan['total_stocks']} 支")
    print(f"\n策略分配:")
    print(f"  • 保持Baseline:   {len(plan['keep_baseline']):2d} 支 ✅")
    print(f"  • 需要深入测试:   {len(plan['priority_high']):2d} 支 ⚠️ (优先级:高)")
    print(f"  • 可选择性优化:   {len(plan['priority_medium']):2d} 支 🤔 (优先级:中)")
    
    print(f"\n预计测试工作量:")
    print(f"  • 测试小时数: {plan['estimated_hours']:.1f} 小时")
    print(f"  • 测试天数:   {plan['estimated_days']:.1f} 天")
    
    # 时间节省对比
    if plan['total_stocks'] > 0:
        naive_hours = plan['total_stocks'] * 6  # 每支股票测试6种方法*1小时
        saved_hours = naive_hours - plan['estimated_hours']
        saved_percent = (saved_hours / naive_hours) * 100
        
        print(f"\n⚡ 效率提升:")
        print(f"  • 朴素方法: {naive_hours:.0f} 小时 ({naive_hours/8:.1f} 天)")
        print(f"  • 智能方法: {plan['estimated_hours']:.0f} 小时 ({plan['estimated_days']:.1f} 天)")
        print(f"  • 节省时间: {saved_hours:.0f} 小时 ({saved_hours/8:.1f} 天)")
        print(f"  • 时间节省: {saved_percent:.1f}% ⭐⭐⭐")
    
    print("=" * 70)
    
    return plan


def save_classification_report(classifications: Dict, plan: Dict, filename: str = None):
    """
    保存分类报告
    
    Parameters:
    -----------
    classifications: dict
        分类结果
    plan: dict
        测试计划
    filename: str
        保存文件名
    """
    if filename is None:
        filename = f"classification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'total_stocks': len(classifications),
        'summary': {
            'type_A': len([c for c in classifications.values() if c['type'] == 'A']),
            'type_B': len([c for c in classifications.values() if c['type'] == 'B']),
            'type_C': len([c for c in classifications.values() if c['type'] == 'C'])
        },
        'classifications': classifications,
        'test_plan': plan
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 分类报告已保存: {filename}")
    
    # 同时保存CSV版本
    csv_filename = filename.replace('.json', '.csv')
    df_data = []
    for stock_code, info in classifications.items():
        df_data.append({
            '股票代码': stock_code,
            '类型': info['type'],
            '类型名称': info['type_name'],
            '测试MAE': f"{info['test_mae']:.6f}",
            '训练MAE': f"{info['train_mae']:.6f}",
            '差距': f"{info['gap']:+.6f}",
            '建议': info['recommendation'],
            '行动': info['action'],
            '优先级': info['priority'],
            '预期改善': info['expected_improvement']
        })
    
    df = pd.DataFrame(df_data)
    df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"📄 CSV报告已保存: {csv_filename}")
    
    return filename


def quick_recommend(test_mae: float, gap: float) -> str:
    """
    快速推荐方法（单股票）
    
    Parameters:
    -----------
    test_mae: float
        测试MAE
    gap: float
        训练-验证差距
    
    Returns:
    --------
    str: 推荐方法
    """
    if test_mae < 0.06 and abs(gap) < 0.01:
        return "Baseline ✅"
    elif gap > 0.05:
        return "Regularized or Augmented ⚠️"
    elif test_mae > 0.12:
        return "Larger or Attention ⚠️"
    elif abs(gap) < 0.005:
        return "Baseline (already good) ⭐"
    else:
        return "Optimized 🤔"


# ==================== 主程序示例 ====================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🤖 自动股票分类和测试计划生成器")
    print("=" * 70)
    
    # 示例：使用TEST_STOCK的结果
    print("\n示例: 使用TEST_STOCK测试结果")
    
    example_results = {
        'TEST_STOCK': {
            'test_mae': 0.044063,
            'train_mae': 0.039744,
            'gap': 0.004318
        }
    }
    
    # 分类单个股票
    classification = auto_classify_stock('TEST_STOCK', example_results['TEST_STOCK'])
    
    print("\n单股票分类结果:")
    print("-" * 70)
    for key, value in classification.items():
        print(f"  {key:20s}: {value}")
    
    # 模拟多个股票的结果进行批量分类
    print("\n\n" + "=" * 70)
    print("示例: 模拟批量分类")
    print("=" * 70)
    
    # 生成模拟数据
    np.random.seed(42)
    simulated_results = {}
    
    stock_codes = [f'Stock_{i:03d}' for i in range(1, 51)]  # 50支股票
    
    for code in stock_codes:
        # 模拟不同类型的结果
        rand = np.random.rand()
        
        if rand < 0.4:  # 40% 良好
            test_mae = np.random.uniform(0.03, 0.06)
            train_mae = test_mae - np.random.uniform(0.001, 0.008)
        elif rand < 0.7:  # 30% 中等
            test_mae = np.random.uniform(0.06, 0.10)
            train_mae = test_mae - np.random.uniform(0.005, 0.015)
        else:  # 30% 问题
            test_mae = np.random.uniform(0.10, 0.15)
            train_mae = test_mae - np.random.uniform(0.015, 0.040)
        
        simulated_results[code] = {
            'test_mae': test_mae,
            'train_mae': max(0.01, train_mae),
            'gap': test_mae - train_mae
        }
    
    # 批量分类
    classifications = batch_classify(simulated_results)
    
    # 生成测试计划
    plan = generate_test_plan(classifications)
    
    # 保存报告
    report_file = save_classification_report(
        classifications, 
        plan, 
        './improved_results/stock_classification_report.json'
    )
    
    print("\n" + "=" * 70)
    print("✅ 自动分类和测试计划生成完成！")
    print("=" * 70)
    
    print("\n💡 使用方法:")
    print("""
    # 导入
    from stock_auto_classifier import batch_classify, generate_test_plan
    
    # 准备Baseline结果（dict格式）
    baseline_results = {
        '2330': {'test_mae': 0.045, 'train_mae': 0.041, 'gap': 0.004},
        '2317': {'test_mae': 0.089, 'train_mae': 0.085, 'gap': 0.004},
        # ...更多股票
    }
    
    # 自动分类
    classifications = batch_classify(baseline_results)
    
    # 生成测试计划
    plan = generate_test_plan(classifications)
    
    # 保存报告
    save_classification_report(classifications, plan, 'my_report.json')
    """)
