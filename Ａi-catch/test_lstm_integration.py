"""
测试 LSTM 集成功能
验证 Smart Entry 系统是否正确调用 LSTM Manager 并调整信心分数
"""

import sys
import os
import json
import logging

# 添加 backend-v3 路径以导入模块
sys.path.append(os.path.abspath("backend-v3"))

try:
    from app.services.smart_entry_system import SmartEntrySystem
    import yfinance as yf
    
    # 初始化
    system = SmartEntrySystem()
    
    # 挑选一支在白名单且表现好的股票进行测试
    # 根据之前的白名单，6285 (63.1%) 是个好选择
    TEST_STOCK = "6285" 
    
    print(f"🔬 开始测试 LSTM 集成 (股票: {TEST_STOCK})...")
    
    # 模拟获取最新数据 (假设今天收盘)
    # 为了测试方便，我们直接获取 yfinance 的最新数据并构造成 system 需要的格式
    ticker = yf.Ticker(f"{TEST_STOCK}.TW")
    hist = ticker.history(period="1mo")
    
    if hist.empty:
        print("❌ 无法获取测试数据")
        sys.exit(1)
        
    latest = hist.iloc[-1]
    prev = hist.iloc[-2]
    
    # 构造 Smart Entry 需要的 dict 格式
    # 注意：这些指标需要手动计算一下简单的版本
    ma5 = hist['Close'].rolling(5).mean().iloc[-1]
    ma20 = hist['Close'].rolling(20).mean().iloc[-1]
    
    stock_data = {
        'symbol': TEST_STOCK,
        'price': float(latest['Close']),
        'change_pct': float((latest['Close'] - prev['Close']) / prev['Close'] * 100),
        'volume': int(latest['Volume']),
        'volume_ratio': 1.2, # 假设量能一般
        'ma5': float(ma5),
        'ma20': float(ma20),
        'above_ma5': float(latest['Close']) > float(ma5),
        'above_ma20': float(latest['Close']) > float(ma20),
        'trend': '上升' if float(latest['Close']) > float(ma5) else '盘整'
    }
    
    print("\n📊 输入数据:")
    print(f"  价格: {stock_data['price']}")
    print(f"  涨跌: {stock_data['change_pct']:.2f}%")
    print(f"  趋势: {stock_data['trend']}")
    
    # 执行评估 (这会触发内部的 LSTM 调用)
    print("\n🔍 调用 Smart Entry 评估...")
    
    # 先进行风险检查 (calculate_confidence 需要这个)
    risk_check = system.check_entry_risk(stock_data)
    
    # 调用核心方法
    result = system.calculate_confidence(stock_data, risk_check)
    
    confidence = result['confidence']
    factors = result['factors']
    
    print(f"\n📈 评估结果:")
    print(f"  最终信心分数: {confidence}")
    print(f"  影响因子:")
    
    lstm_triggered = False
    for f in factors:
        print(f"    - {f}")
        if "AI" in f or "🤖" in f or "⚠️" in f:
            lstm_triggered = True
            
    print("\n" + "="*50)
    if lstm_triggered:
        print("✅ 测试成功！LSTM 模块已成功介入决策。")
        if "AI推薦" in str(factors):
            print("   -> AI 看涨，给予加分")
        elif "AI預警" in str(factors):
            print("   -> AI 看跌，给予扣分")
    else:
        print("❌ 测试失败？未看到 LSTM 相关日志 (可能是数据不足或网络问题)")
        
except Exception as e:
    print(f"❌ 测试出错: {e}")
    import traceback
    traceback.print_exc()
