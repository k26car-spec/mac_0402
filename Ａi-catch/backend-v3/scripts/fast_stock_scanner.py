#!/usr/bin/env python3
"""
快速股票掃描器 v2.0
Fast Stock Scanner

優化：
1. 併發數 5 → 20
2. Timeout 15 → 8 秒
3. 進度條顯示
4. 更好的錯誤處理
"""

import requests
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# 54 支監控股票
STOCKS = [
    "2317", "5521", "2313", "8074", "3163", "1303", "6257", "3231", "1815", "8422",
    "6770", "3265", "3706", "2367", "2337", "2344", "3481", "2312", "3037", "3363",
    "2327", "8155", "6282", "5498", "2314", "1326", "1605", "2330", "2454", "3034",
    "2379", "2382", "3008", "2881", "2882", "2891", "2412", "2609", "2618", "1301",
    "1101", "2002", "2912", "9910", "2301", "8046", "3189", "2408", "2303", "6285",
    "8150", "1802", "2371", "6239"
]

# 優化參數
MAX_WORKERS = 20  # 併發數
TIMEOUT = 8       # 秒
API_BASE = "http://localhost:8000"

def check_stock(symbol: str) -> dict:
    """檢查單一股票"""
    try:
        resp = requests.get(
            f"{API_BASE}/api/entry-check/quick/{symbol}",
            timeout=TIMEOUT
        )
        if resp.status_code == 200:
            d = resp.json()
            return {
                "symbol": symbol,
                "price": d.get("entry_price", 0),
                "score": d.get("checks", {}).get("smart_score", {}).get("score", 0),
                "confidence": d.get("confidence", 0),
                "should_enter": d.get("should_enter", False),
                "action": d.get("checks", {}).get("smart_score", {}).get("action", ""),
                "status": d.get("checks", {}).get("smart_score", {}).get("factors", {}).get("orb", {}).get("status", ""),
                "reason": d.get("reason", "")[:50]
            }
    except requests.Timeout:
        return {"symbol": symbol, "error": "timeout"}
    except Exception as e:
        return {"symbol": symbol, "error": str(e)[:30]}
    return {"symbol": symbol, "error": "unknown"}

def print_progress(current, total, width=40):
    """顯示進度條"""
    percent = current / total
    filled = int(width * percent)
    bar = "█" * filled + "░" * (width - filled)
    sys.stdout.write(f"\r掃描進度: [{bar}] {current}/{total} ({percent*100:.0f}%)")
    sys.stdout.flush()

def main():
    print(f"🚀 快速股票掃描器 v2.0")
    print(f"⏰ 時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 掃描 {len(STOCKS)} 支股票 (併發: {MAX_WORKERS}, Timeout: {TIMEOUT}s)")
    print("=" * 70)
    
    start_time = datetime.now()
    results = []
    errors = []
    completed = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_stock, s): s for s in STOCKS}
        
        for future in as_completed(futures):
            completed += 1
            print_progress(completed, len(STOCKS))
            
            result = future.result()
            if result and "error" not in result:
                results.append(result)
            else:
                errors.append(result)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"\n\n{'='*70}")
    print(f"✅ 掃描完成！耗時: {elapsed:.1f} 秒")
    print(f"📊 成功: {len(results)} | 失敗: {len(errors)}")
    print("=" * 70)
    
    # 排序：建議進場優先，然後按評分
    results.sort(key=lambda x: (-int(x.get("should_enter", False)), -x.get("score", 0)))
    
    # 建議進場
    recommended = [r for r in results if r.get("should_enter")]
    if recommended:
        print(f"\n✅ 【建議進場】({len(recommended)} 支):")
        print("-" * 70)
        for r in recommended:
            print(f"   🟢 {r['symbol']:5} | ${r['price']:>8.1f} | 評分: {r['score']:5.1f} | {r['action']}")
    else:
        print("\n❌ 目前無建議進場標的")
    
    # Top 10
    print(f"\n📈 【評分 Top 10】:")
    print("-" * 70)
    for i, r in enumerate(results[:10], 1):
        emoji = "🟢" if r.get("should_enter") else "🔴"
        print(f" {i:2}. {emoji} {r['symbol']:5} | ${r['price']:>8.1f} | 評分: {r['score']:5.1f} | {r['action']:6} | {r['status']}")
    
    # BUY 訊號
    buys = [r for r in results if r.get("action") == "BUY"]
    if buys:
        print(f"\n🔥 【BUY 訊號】({len(buys)} 支):")
        print("-" * 70)
        for r in buys:
            emoji = "✅" if r.get("should_enter") else "⚠️"
            print(f"   {emoji} {r['symbol']:5} | ${r['price']:>8.1f} | 評分: {r['score']:5.1f} | {r['status']}")
    
    # 可觀察
    watch = [r for r in results if 45 <= r.get("score", 0) < 65 and r.get("action") not in ["SELL"]]
    if watch:
        print(f"\n⚠️ 【可觀察】(評分 45-65, 非 SELL):")
        for r in watch[:5]:
            print(f"   ⚠️ {r['symbol']:5} | ${r['price']:>8.1f} | 評分: {r['score']:5.1f} | {r['action']}")
    
    # 錯誤報告
    if errors:
        print(f"\n⚠️ 掃描失敗 ({len(errors)} 支):")
        for e in errors[:5]:
            print(f"   ❌ {e['symbol']}: {e.get('error', 'unknown')}")
    
    print(f"\n{'='*70}")
    print(f"⏱️ 總耗時: {elapsed:.1f} 秒 (平均 {elapsed/len(STOCKS)*1000:.0f}ms/支)")
    
    # 保存結果
    output = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": elapsed,
        "total": len(STOCKS),
        "success": len(results),
        "errors": len(errors),
        "recommended": recommended,
        "top10": results[:10],
        "buys": buys,
        "all_results": results
    }
    
    with open("/tmp/scan_result.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"💾 結果已存至 /tmp/scan_result.json")

if __name__ == "__main__":
    main()
