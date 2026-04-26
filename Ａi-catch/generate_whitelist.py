"""
根据回测结果生成LSTM白名单
只对准确率 >= 50% 的股票启用LSTM
"""

import json
import os

THRESHOlD_ACCURACY = 0.50

def generate_whitelist():
    print("=" * 70)
    print("📋 生成 LSTM 白名单")
    print("=" * 70)
    
    # 1. 读取回测结果
    result_file = 'lstm_adaptive_results.json'
    if not os.path.exists(result_file):
        print(f"❌ 找不到回测结果文件: {result_file}")
        return
        
    with open(result_file, 'r') as f:
        results = json.load(f)
        
    # 2. 筛选合格股票
    whitelist = []
    skipped = []
    
    print(f"\n筛选标准: 准确率 >= {THRESHOlD_ACCURACY*100:.1f}%")
    
    for r in results:
        stock = r['stock_code']
        acc = r['accuracy']
        threshold = r['threshold']
        
        if acc >= THRESHOlD_ACCURACY:
            whitelist.append({
                'stock_code': stock,
                'accuracy': acc,
                'threshold': threshold
            })
            print(f"  ✅ {stock}: {acc*100:.1f}% (阈值: {threshold:.4f})")
        else:
            skipped.append({
                'stock_code': stock,
                'accuracy': acc
            })
            
    # 3. 保存白名单
    output_file = 'lstm_whitelist.json'
    
    # 我们只保存必要的字段：股票代码和最佳阈值
    # 这样在实际预测时可以直接读取最佳阈值，不用再重新计算
    final_whitelist = {}
    for item in whitelist:
        final_whitelist[item['stock_code']] = {
            'threshold': item['threshold'],
            'accuracy': item['accuracy']
        }
        
    with open(output_file, 'w') as f:
        json.dump(final_whitelist, f, indent=2)
        
    print(f"\n{'='*70}")
    print(f"📊 统计")
    print(f"  ✅ 合格股票: {len(whitelist)} 支")
    print(f"  ❌ 未达标: {len(skipped)} 支")
    print(f"  📂 白名单已保存至: {output_file}")
    
    # 计算合格股票的平均准确率
    if whitelist:
        avg_acc = sum([x['accuracy'] for x in whitelist]) / len(whitelist)
        print(f"  📈 合格股票平均准确率: {avg_acc*100:.2f}%")
    
    print(f"{'='*70}")

if __name__ == "__main__":
    generate_whitelist()
