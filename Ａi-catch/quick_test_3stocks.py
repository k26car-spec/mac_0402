"""
快速测试 - 仅测试3支股票验证流程

执行: python3 quick_test_3stocks.py
"""

import json
from batch_baseline_test import test_baseline_single_stock, PROJECT_ROOT
import os

print("=" * 70)
print("🧪 快速测试 - 3支股票验证")
print("=" * 70)

# 固定测试3支主要股票
test_stocks = {
    "2330": "台积电",
    "2317": "鸿海",  
    "2454": "联发科"
}

print(f"\n📋 测试股票:")
for code, name in test_stocks.items():
    print(f"  • {code}  {name}")

print(f"\n预计时间: 6-10 分钟")
input("\n按 Enter 开始测试...")

# 创建结果目录
RESULTS_DIR = f"{PROJECT_ROOT}/baseline_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# 批量测试
results = {}

for i, (stock_code, stock_name) in enumerate(test_stocks.items(), 1):
    print(f"\n{'='*70}")
    print(f"进度: [{i}/3] ({i/3*100:.1f}%)")
    print(f"{'='*70}")
    
    result = test_baseline_single_stock(stock_code, stock_name)
    results[stock_code] = result

# 保存结果
output_file = f"{RESULTS_DIR}/quick_test_results.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# 统计
print(f"\n\n{'='*70}")
print(f"📊 测试完成")
print(f"{'='*70}")

success_count = sum(1 for r in results.values() if r['success'])
print(f"\n总测试: 3 支")
print(f"成功:   {success_count} 支 ✅")
print(f"失败:   {3-success_count} 支 ❌")

if success_count > 0:
    print(f"\n详细结果:")
    for code, result in results.items():
        if result['success']:
            print(f"\n  {code} ({result['stock_name']}):")
            print(f"    测试MAE:   {result['test_mae']:.6f}")
            print(f"    训练MAE:   {result['train_mae']:.6f}")
            print(f"    差距:      {result['gap']:+.6f}")
            print(f"    分类:      类型{result['category']} ({result['category_name']})")

print(f"\n📄 结果已保存: {output_file}")

if success_count == 3:
    print(f"\n✅ 验证成功！所有股票都测试完成")
    print(f"\n💡 现在可以运行完整测试:")
    print(f"   python3 batch_baseline_test.py")
elif success_count > 0:
    print(f"\n⚠️ 部分成功，可能是网络问题或数据问题")
    print(f"   建议重试失败的股票")
else:
    print(f"\n❌ 全部失败，请检查:")
    print(f"   1. 网络连接是否正常")
    print(f"   2. yfinance 是否正确安装")
    print(f"   3. TensorFlow 是否正常工作")

print(f"\n{'='*70}")
