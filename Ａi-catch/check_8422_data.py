import json

with open('baseline_results/baseline_results_final.json', 'r') as f:
    results = json.load(f)

stock_8422 = results.get('8422', {})

print("=" * 70)
print("🔍 8422 数据检查")
print("=" * 70)
print(f"\n当前状态:")
print(f"  训练MAE: {stock_8422.get('train_mae', 0):.3f}")
print(f"  测试MAE: {stock_8422.get('test_mae', 0):.3f}")
print(f"  差距:    {stock_8422.get('gap', 0):+.3f}")
print(f"  训练轮数: {stock_8422.get('epochs_trained', 0)}")
print(f"\n⚠️ 差距 +4.104 非常异常！")
print(f"\n可能原因:")
print(f"  1. 数据泄漏 - 训练集包含未来信息")
print(f"  2. 测试集数据异常/离群值")
print(f"  3. 特征工程问题")
print(f"  4. 极端过拟合")
print(f"\n建议:")
print(f"  → 如无法解决，强烈建议排除此股票")
print(f"  → 43支中排除1支影响不大（仍有42支）")
print(f"  → 可以节省大量调试时间")
