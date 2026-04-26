#!/usr/bin/env python3
"""
訂單流模式識別系統 - 測試腳本
Order Flow Pattern Recognition System - Test Script

演示如何使用訂單流模式識別系統：
1. 創建模擬的逐筆成交和五檔數據
2. 提取特徵
3. 檢測市場模式
4. 顯示分析結果
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List

# 添加專案路徑
import sys
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

from app.ml.order_flow import (
    MarketPattern,
    MARKET_MICRO_PATTERNS,
    PatternThresholds,
    OrderFlowFeatureExtractor,
    PatternLabeler,
)
from app.ml.order_flow.features import TickData, OrderBookSnapshot
from app.services.order_flow_service import order_flow_service


def generate_mock_ticks(
    base_price: float = 100.0,
    count: int = 50,
    scenario: str = "neutral",
) -> List[TickData]:
    """生成模擬的逐筆成交數據"""
    ticks = []
    price = base_price
    now = datetime.now()
    
    for i in range(count):
        timestamp = now - timedelta(seconds=(count - i) * 2)
        
        # 根據場景調整價格和方向
        if scenario == "aggressive_buy":
            # 積極買盤：大量買單，價格上漲
            direction = "BUY" if random.random() < 0.8 else "SELL"
            price_change = random.uniform(0.01, 0.05)
            volume = random.randint(50, 200) if direction == "BUY" else random.randint(10, 50)
        elif scenario == "aggressive_sell":
            # 積極賣盤：大量賣單，價格下跌
            direction = "SELL" if random.random() < 0.8 else "BUY"
            price_change = random.uniform(-0.05, -0.01)
            volume = random.randint(50, 200) if direction == "SELL" else random.randint(10, 50)
        elif scenario == "support_test":
            # 測試支撐：先跌後穩
            if i < count * 0.5:
                direction = "SELL" if random.random() < 0.7 else "BUY"
                price_change = random.uniform(-0.03, 0)
            else:
                direction = "BUY" if random.random() < 0.6 else "SELL"
                price_change = random.uniform(0, 0.02)
            volume = random.randint(30, 100)
        else:
            # 中性：隨機
            direction = "BUY" if random.random() < 0.5 else "SELL"
            price_change = random.uniform(-0.02, 0.02)
            volume = random.randint(20, 80)
        
        price = max(price * (1 + price_change / 100), 1)
        
        ticks.append(TickData(
            timestamp=timestamp,
            price=round(price, 2),
            volume=volume,
            direction=direction,
            order_type="LARGE" if volume > 100 else "NORMAL",
        ))
    
    return ticks


def generate_mock_orderbook(
    mid_price: float = 100.0,
    imbalance: float = 0.0,  # -1 到 1，正數表示買盤強
) -> OrderBookSnapshot:
    """生成模擬的五檔訂單簿"""
    spread = 0.5
    
    bids = []
    asks = []
    
    for i in range(5):
        bid_price = mid_price - (i + 1) * spread
        ask_price = mid_price + (i + 1) * spread
        
        # 根據不平衡度調整量
        base_vol = random.randint(50, 150)
        bid_vol = int(base_vol * (1 + imbalance * 0.5))
        ask_vol = int(base_vol * (1 - imbalance * 0.5))
        
        bids.append({"price": round(bid_price, 2), "volume": max(bid_vol, 10)})
        asks.append({"price": round(ask_price, 2), "volume": max(ask_vol, 10)})
    
    return OrderBookSnapshot(
        timestamp=datetime.now(),
        bids=bids,
        asks=asks,
        last_price=mid_price,
    )


async def test_pattern_detection():
    """測試模式檢測功能"""
    print("\n" + "=" * 70)
    print("🧪 訂單流模式識別系統測試")
    print("=" * 70)
    
    # 創建工具
    extractor = OrderFlowFeatureExtractor(large_order_threshold=100)
    labeler = PatternLabeler()
    
    # 測試場景
    scenarios = [
        ("aggressive_buy", "積極買盤攻擊場景"),
        ("aggressive_sell", "積極賣盤攻擊場景"),
        ("support_test", "測試支撐場景"),
        ("neutral", "中性場景"),
    ]
    
    for scenario, description in scenarios:
        print(f"\n📊 {description}")
        print("-" * 50)
        
        # 生成模擬數據
        ticks = generate_mock_ticks(base_price=100, count=50, scenario=scenario)
        orderbooks = [
            generate_mock_orderbook(
                mid_price=ticks[-1].price,
                imbalance=0.5 if "buy" in scenario else (-0.5 if "sell" in scenario else 0)
            )
        ]
        
        # 添加到提取器
        extractor.reset_buffers()
        for tick in ticks:
            extractor.add_tick(tick)
        for ob in orderbooks:
            extractor.add_orderbook(ob)
        
        # 提取特徵
        features = extractor.extract_features()
        print(f"  特徵數量: {len(features)}")
        print(f"  買入量比例: {features.get('buy_volume_ratio', 0):.2%}")
        print(f"  大單淨流: {features.get('large_net_flow', 0):.4f}")
        print(f"  訂單簿不平衡: {features.get('order_book_imbalance', 0):.4f}")
        
        # 檢測模式
        detections = labeler.detect_patterns(
            symbol="TEST",
            ticks=ticks,
            orderbooks=orderbooks,
        )
        
        print(f"\n  檢測到的模式:")
        for det in detections:
            pattern_name = MARKET_MICRO_PATTERNS.get(det.pattern, "未知")
            print(f"    • {pattern_name}")
            print(f"      信心度: {det.confidence:.2%}, 強度: {det.strength:.4f}")
            if det.evidence:
                for key, val in det.evidence.items():
                    if isinstance(val, float):
                        print(f"      {key}: {val:.4f}")
                    else:
                        print(f"      {key}: {val}")
    
    print("\n" + "=" * 70)
    print("✅ 測試完成！")
    print("=" * 70)


async def test_service_integration():
    """測試服務整合"""
    print("\n" + "=" * 70)
    print("🔗 服務整合測試")
    print("=" * 70)
    
    symbol = "2330"
    
    # 模擬 API 數據格式
    quotes = [
        {
            "price": 1000 + i * random.uniform(-5, 5),
            "volume": random.randint(50, 200),
            "open": 1000,
            "prevClose": 995,
            "timestamp": (datetime.now() - timedelta(seconds=i * 2)).isoformat(),
        }
        for i in range(20, 0, -1)
    ]
    
    orderbook = {
        "bids": [
            {"price": 999 - i, "volume": random.randint(50, 150)}
            for i in range(5)
        ],
        "asks": [
            {"price": 1001 + i, "volume": random.randint(50, 150)}
            for i in range(5)
        ],
        "lastPrice": 1000,
        "timestamp": datetime.now().isoformat(),
    }
    
    # 處理報價
    print(f"\n📥 處理 {len(quotes)} 筆報價數據...")
    for quote in quotes:
        await order_flow_service.process_realtime_quote(symbol, quote)
    
    # 處理五檔
    print(f"📥 處理五檔訂單簿...")
    await order_flow_service.process_orderbook(symbol, orderbook)
    
    # 獲取特徵
    print(f"\n📊 獲取特徵向量...")
    features_result = await order_flow_service.get_features(symbol)
    if features_result.get("success"):
        print(f"  特徵數量: {features_result.get('feature_count', 0)}")
        features = features_result.get("features", {})
        for key in ["buy_volume_ratio", "order_book_imbalance", "price_return"]:
            if key in features:
                print(f"  {key}: {features[key]:.6f}")
    
    # 檢測模式
    print(f"\n🎯 檢測市場模式...")
    patterns_result = await order_flow_service.detect_patterns(symbol)
    if patterns_result.get("success"):
        primary = patterns_result.get("primary_pattern", {})
        print(f"  主要模式: {primary.get('pattern_name', '未知')}")
        print(f"  信心度: {primary.get('confidence', 0):.2%}")
        print(f"  交易建議: {primary.get('trading_hint', {}).get('action', 'N/A')}")
    
    # 獲取統計
    print(f"\n📈 獲取統計資訊...")
    stats_result = await order_flow_service.get_statistics(symbol)
    if stats_result.get("success"):
        stats = stats_result.get("statistics", {})
        print(f"  總檢測次數: {stats.get('total_detections', 0)}")
        print(f"  平均信心度: {stats.get('avg_confidence', 0):.2%}")
    
    # 顯示系統狀態
    print(f"\n🖥️ 系統狀態:")
    status = order_flow_service.get_system_status()
    print(f"  監控股票數: {status.get('monitored_symbols', 0)}")
    print(f"  監控列表: {status.get('symbols', [])}")
    
    print("\n" + "=" * 70)
    print("✅ 服務整合測試完成！")
    print("=" * 70)


async def main():
    """主測試函數"""
    print("\n🚀 訂單流模式識別系統 v1.0")
    print("替代傳統 LSTM 價格預測的新一代系統")
    
    # 測試模式檢測
    await test_pattern_detection()
    
    # 測試服務整合
    await test_service_integration()
    
    # 測試推理引擎
    await test_inference_engine()
    
    print("\n💡 提示: 啟動 FastAPI 服務後，可以訪問以下 API:")
    print("   GET  /api/order-flow/status          - 系統狀態")
    print("   GET  /api/order-flow/patterns/{sym}  - 模式檢測")
    print("   GET  /api/order-flow/features/{sym}  - 特徵提取")
    print("   POST /api/order-flow/analyze         - 完整分析")
    print("   GET  /api/order-flow/patterns/types  - 所有模式類型")


async def test_inference_engine():
    """測試推理引擎"""
    print("\n" + "=" * 70)
    print("🧠 推理引擎測試")
    print("=" * 70)
    
    from app.ml.engine import (
        RealTimeInferenceEngine,
        Decision,
        TradingAction,
        RiskLevel,
    )
    
    engine = RealTimeInferenceEngine()
    
    # 模擬模式檢測結果
    pattern_results = [
        {
            "success": True,
            "primary_pattern": {
                "pattern": "AGGRESSIVE_BUYING",
                "pattern_name": "積極買盤攻擊",
                "confidence": 0.85,
            },
        },
        {
            "success": True,
            "primary_pattern": {
                "pattern": "SUPPORT_TESTING",
                "pattern_name": "測試支撐",
                "confidence": 0.72,
            },
        },
        {
            "success": True,
            "primary_pattern": {
                "pattern": "NEUTRAL",
                "pattern_name": "中性",
                "confidence": 0.6,
            },
        },
    ]
    
    for i, pattern_result in enumerate(pattern_results):
        print(f"\n📊 場景 {i + 1}: {pattern_result['primary_pattern']['pattern_name']}")
        print("-" * 40)
        
        decision = engine.process(
            symbol="2330",
            pattern_result=pattern_result,
            market_data={"volatility": 0.01, "total_depth": 1000},
        )
        
        print(f"  決策: {decision.action.value}")
        print(f"  信心度: {decision.confidence:.2%}")
        print(f"  風險等級: {decision.risk_level.value}")
        print(f"  推理: {decision.reasoning}")
        print(f"  被過濾: {decision.filtered}")
        if decision.filter_reason:
            print(f"  過濾原因: {decision.filter_reason}")
    
    # 獲取統計
    stats = engine.get_stats("2330")
    print(f"\n📈 統計資訊:")
    print(f"  總決策數: {stats.get('total_decisions', 0)}")
    print(f"  過濾率: {stats.get('filter_rate', 0):.2%}")
    
    print("\n" + "=" * 70)
    print("✅ 推理引擎測試完成！")
    print("=" * 70)



if __name__ == "__main__":
    asyncio.run(main())
