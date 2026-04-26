#!/usr/bin/env python3
"""
測試批量股票查詢API的性能
"""
import requests
import time

API_BASE = "http://localhost:8000"

# 測試股票
test_codes = [
    "2330", "2454", "2317", "2337", "2344", "3034", "2379", "2408",
    "3231", "2603", "2609", "2615", "2881", "2882", "2891", "2886",
    "2002", "1301", "1303", "1326", "6505", "2912", "9910", "2301"
]

print("=" * 60)
print("🚀 批量股票查詢API性能測試")
print("=" * 60)

# 測試批量API
print(f"\n📊 測試 {len(test_codes)} 檔股票...")
print("-" * 60)

start_time = time.time()

try:
    response = requests.post(
        f"{API_BASE}/api/stocks/batch-names",
        json={"codes": test_codes},
        timeout=30
    )
    
    elapsed = time.time() - start_time
    
    if response.status_code == 200:
        results = response.json()
        
        print(f"✅ 批量查詢成功！")
        print(f"   總耗時: {elapsed:.2f}秒")
        print(f"   查詢數量: {len(results)} 檔")
        print(f"   平均每檔: {(elapsed / len(results) * 1000):.0f}ms")
        print()
        
        # 統計來源
        sources = {}
        for result in results:
            source = result.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        print("📈 數據來源統計:")
        for source, count in sources.items():
            print(f"   {source:12s}: {count} 檔")
        
        print()
        print("🔍 查詢結果樣本 (前10檔):")
        for i, result in enumerate(results[:10], 1):
            print(f"   {i:2d}. {result['code']} - {result['name']:8s} [{result['source']}]")
        
        # 效能評估
        print()
        print("=" * 60)
        if elapsed < 1.0:
            print("🎉 性能優異！< 1秒")
        elif elapsed < 2.0:
            print("✅ 性能良好！< 2秒")
        elif elapsed < 5.0:
            print("⚠️ 性能尚可，建議優化")
        else:
            print("❌ 性能較差，需要優化")
        print("=" * 60)
        
    else:
        print(f"❌ API返回錯誤: {response.status_code}")
        print(f"   {response.text}")
        
except requests.exceptions.Timeout:
    print(f"❌ 請求超時 (>30秒)")
except requests.exceptions.ConnectionError:
    print(f"❌ 無法連接到API服務器")
    print(f"   請確認後端服務已啟動: {API_BASE}")
except Exception as e:
    print(f"❌ 測試失敗: {e}")

print()
