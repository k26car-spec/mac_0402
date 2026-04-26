"""
阶段2: 自动分类和测试计划生成
基于阶段1的Baseline结果自动分类股票

执行: python3 run_stage2_classification.py
"""

import json
import os
from stock_auto_classifier import batch_classify, generate_test_plan, save_classification_report

print("=" * 70)
print("📊 阶段2: 自动分类和测试计划生成")
print("=" * 70)

# ==================== 配置 ====================

PROJECT_ROOT = "/Users/Mac/Documents/ETF/AI/Ａi-catch"
RESULTS_DIR = f"{PROJECT_ROOT}/baseline_results"
BASELINE_RESULTS_FILE = f"{RESULTS_DIR}/baseline_results_final.json"

# ==================== 加载Baseline结果 ====================

print(f"\n🔄 加载Baseline测试结果...")

try:
    with open(BASELINE_RESULTS_FILE, 'r', encoding='utf-8') as f:
        all_results = json.load(f)
    
    print(f"✅ 成功加载结果文件")
    print(f"   文件: {BASELINE_RESULTS_FILE}")
    print(f"   股票数: {len(all_results)}")
    
except FileNotFoundError:
    print(f"❌ 找不到Baseline结果文件!")
    print(f"   期望路径: {BASELINE_RESULTS_FILE}")
    print(f"\n请先运行阶段1:")
    print(f"   python3 batch_baseline_test.py")
    exit(1)

# ==================== 过滤成功的结果 ====================

print(f"\n🔍 过滤有效结果...")

# 只保留成功的测试结果
successful_results = {
    code: result 
    for code, result in all_results.items() 
    if result.get('success', False)
}

print(f"✅ 有效结果: {len(successful_results)} 支")

if len(successful_results) == 0:
    print(f"❌ 没有成功的测试结果!")
    exit(1)

# ==================== 执行自动分类 ====================

print(f"\n" + "=" * 70)
print(f"🤖 开始自动分类...")
print(f"=" * 70)

# 批量分类
classifications = batch_classify(successful_results)

# ==================== 生成测试计划 ====================

print(f"\n" + "=" * 70)
print(f"📋 生成测试计划...")
print(f"=" * 70)

# 生成计划
plan = generate_test_plan(classifications)

# ==================== 保存报告 ====================

print(f"\n" + "=" * 70)
print(f"💾 保存分类报告...")
print(f"=" * 70)

# 保存报告
report_files = save_classification_report(
    classifications,
    plan,
    f"{RESULTS_DIR}/stock_classification_report.json"
)

# ==================== 策略建议 ====================

print(f"\n" + "=" * 70)
print(f"🎯 策略建议")
print(f"=" * 70)

# 计算类型A比例
total = len(classifications)
type_a_count = len([c for c in classifications.values() if c['type'] == 'A'])
type_a_ratio = type_a_count / total

print(f"\n类型A比例: {type_a_ratio*100:.1f}%")

if type_a_ratio >= 0.70:
    recommended_strategy = "保守策略"
    estimated_days = "3.5天"
    description = """
    📍 建议使用保守策略
    
    原因:
      • 超过70%的股票训练良好
      • 只需要对少数问题股票进行深入测试
      • 可以快速完成
    
    执行:
      1. 保持类型A股票使用Baseline
      2. 对类型B进行深入测试（3-6种方法）
      3. 对类型C进行快速测试（2种方法）
    
    预计时间: 3.5天
    """
else:
    recommended_strategy = "激进策略"
    estimated_days = "5-7天"
    description = """
    📍 建议使用激进策略
    
    原因:
      • 需要改进的股票较多
      • 需要全面测试找到最佳方案
      • 潜在改进空间大
    
    执行:
      1. 类型B全面测试（所有6种方法）
      2. 类型C全面测试（3-4种方法）
      3. 详细分析每支股票
    
    预计时间: 5-7天
    """

print(f"\n推荐策略: {recommended_strategy}")
print(f"预计时间: {estimated_days}")
print(description)

# ==================== 详细分类列表 ====================

print(f"\n" + "=" * 70)
print(f"📋 详细分类列表")
print(f"=" * 70)

# 按类型分组
for type_key in ['B', 'C', 'A']:
    stocks = [c for c in classifications.values() if c['type'] == type_key]
    
    if stocks:
        type_name = stocks[0]['type_name']
        print(f"\n{type_name} ({len(stocks)}支):")
        print("-" * 70)
        
        for stock in sorted(stocks, key=lambda x: x['test_mae'], reverse=True):
            print(f"  {stock['stock_code']:6s} | "
                  f"MAE={stock['test_mae']:.4f} | "
                  f"Gap={stock['gap']:+.4f} | "
                  f"{stock['action']}")

# ==================== 下一步建议 ====================

print(f"\n\n" + "=" * 70)
print(f"✅ 阶段2完成!")
print(f"=" * 70)

print(f"\n📄 生成的文件:")
print(f"   1. JSON报告: {RESULTS_DIR}/stock_classification_report.json")
print(f"   2. CSV报告:  {RESULTS_DIR}/stock_classification_report.csv")

print(f"\n💡 下一步:")
print(f"   1. 查看分类报告:")
print(f"      open {RESULTS_DIR}/stock_classification_report.csv")
print(f"")
print(f"   2. 根据推荐策略执行阶段3:")
if type_a_ratio >= 0.70:
    print(f"      # 保守策略（推荐）")
    print(f"      python3 run_stage3_conservative.py")
else:
    print(f"      # 激进策略（推荐）")
    print(f"      python3 run_stage3_aggressive.py")

print(f"\n" + "=" * 70)
