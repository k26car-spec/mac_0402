"""
一鍵執行完整選股流程
自動完成：抓取券商數據 → 解析數據 → 選股分析 → 生成報告
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("🚀 全自動選股決策引擎 - 一鍵執行")
print("=" * 80)
print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 確認當前目錄
current_dir = Path.cwd()
print(f"📁 當前目錄: {current_dir}")

# 步驟1: 抓取券商數據
print("\n" + "=" * 80)
print("步驟 1/3: 抓取富邦券商數據")
print("=" * 80)

try:
    result = subprocess.run(
        [sys.executable, 'test_fubon_direct.py'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 0:
        print("✅ 券商數據抓取成功")
        
        # 檢查是否有HTML文件
        html_files = list(Path('.').glob('fubon_test_*.html'))
        if html_files:
            latest_html = max(html_files, key=lambda p: p.stat().st_mtime)
            print(f"   HTML文件: {latest_html.name}")
        else:
            print("   ⚠️ 未找到HTML文件")
    else:
        print("❌ 券商數據抓取失敗")
        print(result.stderr)
        
except Exception as e:
    print(f"❌ 步驟1執行失敗: {e}")

# 步驟2: 解析券商數據
print("\n" + "=" * 80)
print("步驟 2/3: 解析券商數據")
print("=" * 80)

try:
    result = subprocess.run(
        [sys.executable, 'analyze_fubon_html.py'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 0:
        print("✅ 數據解析成功")
        
        # 檢查CSV文件
        csv_file = Path('broker_data_extracted.csv')
        if csv_file.exists():
            import pandas as pd
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            print(f"   提取數據: {len(df)} 筆")
            
            # 顯示買超前5名
            if not df.empty and '差額' in df.columns:
                top5 = df.nlargest(5, '差額')
                print("\n   買超前5名:")
                for i, row in top5.iterrows():
                    print(f"   {i+1}. {row['券商名稱'][:20]:20s} 差額: {row['差額']:+6d}")
        else:
            print("   ⚠️ 未找到CSV文件")
    else:
        print("❌ 數據解析失敗")
        print(result.stderr)
        
except Exception as e:
    print(f"❌ 步驟2執行失敗: {e}")

# 步驟3: 執行選股分析
print("\n" + "=" * 80)
print("步驟 3/3: 執行選股分析")
print("=" * 80)
print("這可能需要1-2分鐘，請稍候...")

try:
    result = subprocess.run(
        [sys.executable, 'test_integration_complete.py'],
        capture_output=True,
        text=True,
        timeout=180  # 3分鐘超時
    )
    
    if result.returncode == 0:
        print("✅ 選股分析完成")
        
        # 檢查報告文件
        report_dir = Path('backend-v3/reports')
        if report_dir.exists():
            csv_files = list(report_dir.glob('fubon_broker_analysis*.csv'))
            if csv_files:
                latest_report = max(csv_files, key=lambda p: p.stat().st_mtime)
                print(f"   報告文件: {latest_report}")
                
                # 讀取並顯示摘要
                import pandas as pd
                df = pd.read_csv(latest_report, encoding='utf-8-sig')
                
                if not df.empty:
                    print(f"\n   分析股票數: {len(df)}")
                    
                    # 顯示買入建議
                    if '建議動作' in df.columns:
                        buy_stocks = df[df['建議動作'].isin(['強力買入', '買入'])]
                        
                        if not buy_stocks.empty:
                            print(f"   買入建議: {len(buy_stocks)} 檔")
                            print("\n   推薦股票:")
                            for _, row in buy_stocks.iterrows():
                                print(f"   • {row['股票代碼']} - {row['建議動作']} (評分: {row['綜合評分']:.2f})")
                        else:
                            print("   買入建議: 無")
        else:
            print("   ⚠️ 報告目錄不存在")
    else:
        print("❌ 選股分析失敗")
        # 顯示部分輸出以供調試
        if result.stdout:
            lines = result.stdout.split('\n')
            print("   最後輸出:")
            for line in lines[-10:]:
                if line.strip():
                    print(f"   {line}")
        
except subprocess.TimeoutExpired:
    print("❌ 分析超時（超過3分鐘）")
except Exception as e:
    print(f"❌ 步驟3執行失敗: {e}")

# 總結
print("\n" + "=" * 80)
print("📊 執行總結")
print("=" * 80)

# 檢查生成的文件
files_to_check = [
    ('fubon_test_*.html', '券商HTML'),
    ('broker_data_extracted.csv', '券商數據'),
    ('backend-v3/reports/fubon_broker_analysis*.csv', '分析報告')
]

print("\n生成的文件:")
for pattern, description in files_to_check:
    files = list(Path('.').glob(pattern))
    if files:
        latest = max(files, key=lambda p: p.stat().st_mtime)
        size = latest.stat().st_size / 1024  # KB
        print(f"✅ {description:10s}: {latest.name} ({size:.1f} KB)")
    else:
        print(f"❌ {description:10s}: 未找到")

print("\n" + "=" * 80)
print("✅ 流程執行完畢")
print("=" * 80)

# 提供下一步建議
print("\n💡 下一步:")
print("1. 查看分析報告: open backend-v3/reports/fubon_broker_analysis.csv")
print("2. 查看券商數據: open broker_data_extracted.csv")
print("3. 執行自訂分析: python3 stock_selector_examples.py")
print()
