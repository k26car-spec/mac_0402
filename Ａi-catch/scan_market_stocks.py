"""
📊 台股全市場績優股掃描器
掃描所有上市上櫃股票，找出高潛力標的
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# 添加專案路徑
PROJECT_ROOT = "/Users/Mac/Documents/ETF/AI/Ａi-catch"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fubon_client import fubon_client


# ==================== 台股股票代碼列表 ====================

def get_twse_stock_list():
    """
    取得台灣證券交易所上市股票代碼
    包含：上市股票（1XXX-9XXX）
    """
    # 主要上市股票範圍
    stock_codes = []
    
    # 1. 台灣50成份股及主要大型股（快速測試用）
    major_stocks = [
        '2330', '2317', '2454', '2881', '2882', '2886', '2891', '2892',  # 權值股
        '2303', '2308', '2382', '2412', '2002', '1303', '1301', '1326',  # 科技股
        '2801', '2880', '2884', '2885', '2887', '2888', '2889', '2890',  # 金融股
        '2207', '2357', '2379', '2395', '2474', '3008', '3045', '3711',  # 電子股
        '3034', '3037', '3231', '3443', '4938', '5871', '5876', '6505',  # 其他產業
        '6669', '9904', '9910', '9914', '9917', '9921', '9933', '9941'   # 更多產業
    ]
    
    stock_codes.extend(major_stocks)
    
    # 2. 中小型股票（3XXX-6XXX 範圍）
    # 可選：如果要掃描更多股票，取消以下註解
    # for i in range(3000, 3999):
    #     stock_codes.append(str(i))
    # for i in range(4000, 4999):
    #     stock_codes.append(str(i))
    # for i in range(5000, 5999):
    #     stock_codes.append(str(i))
    # for i in range(6000, 6999):
    #     stock_codes.append(str(i))
    
    return stock_codes


def get_otc_stock_list():
    """
    取得櫃買中心上櫃股票代碼
    包含：上櫃股票（主要在 3XXX-8XXX）
    """
    otc_codes = []
    
    # 主要上櫃績優股
    major_otc = [
        '3380', '3413', '3450', '3466', '3518', '3563', '3581',  # 電子類
        '4906', '4952', '4968', '5203', '5469', '5484', '6116',  # 其他產業
        '6152', '6176', '6214', '6548', '8046', '8070', '8081'   # 更多類別
    ]
    
    otc_codes.extend(major_otc)
    
    return otc_codes


# ==================== 股票分析函數 ====================

async def get_stock_candles(symbol, days=90):
    """獲取股票歷史K線"""
    try:
        if not fubon_client.is_connected:
            await fubon_client.connect()
        
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        candles = await fubon_client.get_candles(symbol, from_date, to_date, timeframe="D")
        return candles
    except Exception as e:
        print(f"  ⚠️  {symbol} 獲取K線失敗: {e}")
        return None


def calculate_growth_rate(candles, period_days):
    """計算成長率"""
    if not candles or len(candles) < 2:
        return 0.0
    
    try:
        latest_price = float(candles[-1]['close'])
        
        if len(candles) > period_days:
            old_price = float(candles[-period_days-1]['close'])
        else:
            old_price = float(candles[0]['close'])
        
        if old_price > 0:
            growth_rate = ((latest_price - old_price) / old_price) * 100
            return round(growth_rate, 2)
    except:
        pass
    
    return 0.0


def analyze_potential(symbol, name, price, volume, growth_1, growth_2, growth_3, change_percent):
    """潛力分析（與 Streamlit 儀表板相同的演算法）"""
    score = 50
    signals = []
    
    # 1. 趨勢評分（40分）
    trend_score = 0
    
    if growth_1 > 5:
        trend_score += 10
        signals.append("✓ 週線強勢")
    elif growth_1 > 1:
        trend_score += 7
    elif growth_1 > 0:
        trend_score += 5
    elif growth_1 > -3:
        trend_score += 3
    else:
        signals.append("✗ 週線走弱")
    
    if growth_2 > 10:
        trend_score += 15
        signals.append("✓ 月線強勁")
    elif growth_2 > 3:
        trend_score += 12
    elif growth_2 > 0:
        trend_score += 8
    elif growth_2 > -5:
        trend_score += 4
    
    if growth_3 > 15:
        trend_score += 15
        signals.append("✓ 長線看漲")
    elif growth_3 > 5:
        trend_score += 12
    elif growth_3 > 0:
        trend_score += 8
    
    score += trend_score
    
    # 2. 趨勢一致性（20分）
    if growth_1 > 0 and growth_2 > 0 and growth_3 > 0:
        score += 20
        signals.append("✓ 多週期向上")
    elif growth_2 > growth_1:
        score += 10
        signals.append("⚠ 動能累積")
    
    # 3. 當日表現（15分）
    if change_percent > 5:
        score += 15
        signals.append("✓ 今日強勢")
    elif change_percent > 2:
        score += 10
    elif change_percent > 0:
        score += 5
    elif change_percent < -3:
        score -= 5
    
    # 4. 動能評估（15分）
    if growth_1 > growth_2 and growth_2 > 0:
        score += 15
        signals.append("✓ 加速上漲")
    elif growth_2 > growth_3 and growth_3 > 0:
        score += 10
        signals.append("✓ 穩步向上")
    elif growth_1 > 10 and growth_2 < growth_1:
        score -= 5
        signals.append("⚠ 短線過熱")
    
    # 5. 成交量評估（10分）
    if volume > 1000000:
        score += 10
        signals.append("✓ 成交活絡")
    elif volume > 500000:
        score += 7
    elif volume > 100000:
        score += 4
    elif price > 300 and volume > 10000:
        score += 6
    elif volume < 50000:
        score -= 3
    
    score = max(0, min(100, score))
    
    if score >= 90:
        level = "極佳 🔥"
    elif score >= 70:
        level = "良好 👍"
    elif score >= 50:
        level = "普通 ➡️"
    else:
        level = "不佳 ⛔"
    
    return {
        'score': round(score, 1),
        'level': level,
        'signals': signals[:3]
    }


async def scan_single_stock(symbol, progress_callback=None):
    """掃描單一股票"""
    try:
        # 獲取報價
        quote = await fubon_client.get_quote(symbol)
        if not quote or quote['price'] <= 0:
            return None
        
        # 獲取歷史數據
        candles = await get_stock_candles(symbol, 90)
        if not candles:
            return None
        
        # 計算成長率
        growth_1 = calculate_growth_rate(candles, 7)   # 週
        growth_2 = calculate_growth_rate(candles, 30)  # 月
        growth_3 = calculate_growth_rate(candles, 60)  # 雙月
        
        # 潛力分析
        potential = analyze_potential(
            symbol, quote.get('name', symbol), quote['price'], quote['volume'],
            growth_1, growth_2, growth_3, quote['change_percent']
        )
        
        result = {
            '代號': symbol,
            '名稱': quote.get('name', symbol),
            '潛力評分': potential['score'],
            '評級': potential['level'],
            '現價': quote['price'],
            '漲跌幅': quote['change_percent'],
            '成交量': quote['volume'],
            '週成長': growth_1,
            '月成長': growth_2,
            '雙月成長': growth_3,
            '關鍵信號': ' | '.join(potential['signals']) if potential['signals'] else '-'
        }
        
        if progress_callback:
            progress_callback(symbol, potential['score'])
        
        return result
        
    except Exception as e:
        if progress_callback:
            progress_callback(symbol, 0, error=str(e))
        return None


async def scan_market(stock_list, min_score=70, max_stocks=50, show_progress=True):
    """
    掃描市場
    
    Args:
        stock_list: 股票代碼列表
        min_score: 最低潛力評分（預設70）
        max_stocks: 最多掃描股票數量（預設50）
        show_progress: 是否顯示進度
    
    Returns:
        DataFrame: 績優股列表
    """
    print(f"\n🔍 開始掃描市場...")
    print(f"📊 掃描範圍: {len(stock_list)} 支股票")
    print(f"🎯 篩選條件: 潛力評分 >= {min_score}")
    print(f"⏱️  預計時間: 約 {len(stock_list) * 2} 秒\n")
    
    # 連接富邦 API
    if not fubon_client.is_connected:
        print("🔌 連接富邦 API...")
        await fubon_client.connect()
        print("✅ 連接成功\n")
    
    results = []
    scanned = 0
    found = 0
    
    def progress_callback(symbol, score, error=None):
        nonlocal scanned, found
        scanned += 1
        
        if error:
            if show_progress:
                print(f"  [{scanned}/{len(stock_list)}] {symbol}: ❌ {error}")
        elif score >= min_score:
            found += 1
            if show_progress:
                print(f"  [{scanned}/{len(stock_list)}] {symbol}: ✅ 評分 {score} 🔥")
        elif show_progress and scanned % 10 == 0:
            print(f"  [{scanned}/{len(stock_list)}] 已掃描 {scanned} 支，找到 {found} 支績優股...")
    
    # 批次掃描（避免過度並發）
    batch_size = 5
    for i in range(0, min(len(stock_list), max_stocks), batch_size):
        batch = stock_list[i:i+batch_size]
        tasks = [scan_single_stock(symbol, progress_callback) for symbol in batch]
        batch_results = await asyncio.gather(*tasks)
        
        for result in batch_results:
            if result and result['潛力評分'] >= min_score:
                results.append(result)
        
        # 短暫延遲，避免 API 限流
        await asyncio.sleep(0.5)
    
    print(f"\n✅ 掃描完成!")
    print(f"📊 共掃描 {scanned} 支股票")
    print(f"🎯 找到 {len(results)} 支績優股 (評分 >= {min_score})\n")
    
    if not results:
        print("⚠️  未找到符合條件的股票，建議降低篩選標準")
        return pd.DataFrame()
    
    # 轉換為 DataFrame 並排序
    df = pd.DataFrame(results)
    df = df.sort_values('潛力評分', ascending=False)
    
    return df


# ==================== 主程式 ====================

async def main():
    """主程式"""
    print("=" * 60)
    print("📈 台股全市場績優股掃描器")
    print("=" * 60)
    
    # 選擇掃描範圍
    print("\n請選擇掃描範圍:")
    print("1. 快速掃描（約 60 支主要股票，2-3 分鐘）")
    print("2. 完整掃描上市股（數百支，需較長時間）")
    print("3. 完整掃描上市+上櫃（數千支，需很長時間）")
    
    choice = input("\n請輸入選項 (1/2/3，預設1): ").strip() or "1"
    
    if choice == "1":
        stock_list = get_twse_stock_list()
        scan_name = "快速掃描"
    elif choice == "2":
        stock_list = get_twse_stock_list()
        # 這裡可以擴展完整上市股票列表
        scan_name = "上市股掃描"
    elif choice == "3":
        stock_list = get_twse_stock_list() + get_otc_stock_list()
        scan_name = "全市場掃描"
    else:
        print("❌ 無效選項，使用快速掃描")
        stock_list = get_twse_stock_list()
        scan_name = "快速掃描"
    
    # 設定篩選條件
    min_score_input = input("\n最低潛力評分 (預設70): ").strip()
    min_score = int(min_score_input) if min_score_input else 70
    
    max_stocks_input = input("最多掃描股票數 (預設100): ").strip()
    max_stocks = int(max_stocks_input) if max_stocks_input else 100
    
    # 開始掃描
    print(f"\n🚀 開始 {scan_name}...")
    df = await scan_market(stock_list[:max_stocks], min_score=min_score, max_stocks=max_stocks)
    
    if len(df) == 0:
        print("\n未找到符合條件的績優股")
        return
    
    # 顯示結果
    print("\n" + "=" * 60)
    print(f"🏆 找到 {len(df)} 支績優股（評分 >= {min_score}）")
    print("=" * 60)
    print(df.to_string(index=False))
    
    # 儲存結果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"/Users/Mac/Documents/ETF/AI/Ａi-catch/scan_results_{timestamp}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n💾 結果已儲存至: {filename}")
    
    # 顯示前5名
    print("\n🥇 評分TOP 5:")
    print("-" * 60)
    top5 = df.head(5)
    for idx, row in top5.iterrows():
        print(f"{row['代號']} {row['名稱']:8s} | 評分: {row['潛力評分']:5.1f} {row['評級']:10s} | "
              f"週成長: {row['週成長']:6.2f}% | 月成長: {row['月成長']:6.2f}%")
        print(f"    信號: {row['關鍵信號']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
