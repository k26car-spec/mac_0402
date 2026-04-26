# 進階券商爬蟲 - 完整實現指南

## 📋 系統概述

進階券商爬蟲專門設計用於突破富邦證券等網站的反爬蟲機制，提供穩定可靠的券商進出數據抓取。

### 核心特性

✅ **多層反爬蟲策略**
- User-Agent 輪替（5種真實瀏覽器UA）
- 隨機請求延遲（3-8秒）
- 自動批次休息（每5次請求休息15-30秒）
- 指數退避重試機制
- Session管理與Cookie維護

✅ **智能錯誤處理**
- 自動重試（最多5次）
- 多種HTTP狀態碼處理
- 備用方案切換
- 詳細錯誤日誌

✅ **數據解析優化**
- 智能HTML解析
- 多種數字格式支援
- 自動編碼檢測
- 調試模式（保存HTML）

## 🏗️ 技術架構

### 反爬蟲策略層次

```
第1層：User-Agent 輪替
    ↓
第2層：隨機延遲（3-8秒）
    ↓
第3層：批次休息（每5次請求休息15-30秒）
    ↓
第4層：指數退避重試（最多5次）
    ↓
第5層：Session管理（Cookie維護）
    ↓
第6層：備用方案（失敗時切換）
```

### 請求流程

```
[發起請求]
    ↓
[檢查Session] → 無 → [創建Session]
    ↓
[隨機延遲 3-8秒]
    ↓
[選擇隨機UA]
    ↓
[發送請求]
    ↓
[檢查狀態碼]
    ├─ 200 → [解析數據] → [批次休息檢查] → [返回結果]
    ├─ 403 → [重試]
    ├─ 429 → [等待後重試]
    └─ 其他 → [指數退避重試]
```

## 📦 安裝依賴

```bash
pip install requests beautifulsoup4 pandas lxml
```

## 🚀 使用方式

### 方法一：使用便捷函數

```python
from app.services.advanced_broker_crawler import (
    get_fubon_xindan_data,
    get_fubon_xindan_top_stocks_advanced
)

# 獲取富邦新店最近5天數據
df = get_fubon_xindan_data(days=5)

# 獲取買超前20名
top_stocks = get_fubon_xindan_top_stocks_advanced(top_n=20)
```

### 方法二：使用爬蟲類

```python
from app.services.advanced_broker_crawler import AdvancedBrokerCrawler

# 創建爬蟲實例
crawler = AdvancedBrokerCrawler()

# 抓取特定日期數據
df = crawler.get_broker_flow_by_date(
    broker_code='9600',  # 富邦新店
    start_date='2024-12-25',
    end_date='2024-12-31'
)

# 獲取買超前N名
top_stocks = crawler.get_top_stocks_by_broker(
    broker_code='9600',
    top_n=20,
    min_net_count=50,
    days=5
)

# 保存數據
crawler.save_to_csv(df, 'broker_data.csv')

# 清理資源
crawler.close()
```

### 方法三：使用上下文管理器

```python
from app.services.advanced_broker_crawler import AdvancedBrokerCrawler

with AdvancedBrokerCrawler() as crawler:
    # 抓取數據
    df = crawler.get_broker_flow_by_date('9600')
    
    # 自動清理資源
```

## 📊 支援的券商代碼

| 券商名稱 | 代碼 | 類型 |
|---------|------|------|
| 富邦-新店 | 9600 | 國內 |
| 富邦-台北 | 9601 | 國內 |
| 元大-台北 | 1160 | 國內 |
| 凱基-台北 | 8880 | 國內 |
| 美林 | 9A9A | 外資 |
| 瑞銀 | 9A9C | 外資 |
| 摩根士丹利 | 9A9B | 外資 |
| 高盛 | 9A9D | 外資 |

## 🔧 進階配置

### 自訂延遲時間

```python
crawler = AdvancedBrokerCrawler()

# 調整延遲範圍
crawler.min_delay = 5  # 最小5秒
crawler.max_delay = 12  # 最大12秒
```

### 調整批次大小

```python
crawler = AdvancedBrokerCrawler()

# 每3次請求休息一次
crawler.batch_size = 3
```

### 調整重試次數

```python
crawler = AdvancedBrokerCrawler()

# 最多重試10次
crawler.max_retries = 10

# 重試延遲15秒
crawler.retry_delay = 15
```

## 🎯 使用場景

### 場景1：每日數據抓取

```python
from datetime import datetime
from app.services.advanced_broker_crawler import AdvancedBrokerCrawler

def daily_broker_data_job():
    """每日抓取券商數據"""
    with AdvancedBrokerCrawler() as crawler:
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 抓取富邦新店數據
        df = crawler.get_broker_flow_by_date(
            broker_code='9600',
            start_date=today,
            end_date=today
        )
        
        if not df.empty:
            # 保存數據
            filename = f'broker_data_{today}.csv'
            crawler.save_to_csv(df, filename)
            print(f"✅ 數據已保存: {filename}")
        else:
            print("⚠️ 未抓取到數據")

# 執行
daily_broker_data_job()
```

### 場景2：批次抓取多個券商

```python
from app.services.advanced_broker_crawler import AdvancedBrokerCrawler

def batch_fetch_brokers():
    """批次抓取多個券商數據"""
    broker_codes = ['9600', '9601', '1160', '8880']
    
    with AdvancedBrokerCrawler() as crawler:
        all_data = crawler.get_multiple_brokers_data(
            broker_codes=broker_codes,
            date='2024-12-31'
        )
        
        if not all_data.empty:
            print(f"✅ 總共抓取 {len(all_data)} 筆數據")
            crawler.save_to_csv(all_data, 'all_brokers_data.csv')

# 執行
batch_fetch_brokers()
```

### 場景3：歷史數據回補

```python
from datetime import datetime, timedelta
from app.services.advanced_broker_crawler import AdvancedBrokerCrawler

def backfill_historical_data(days=30):
    """回補歷史數據"""
    with AdvancedBrokerCrawler() as crawler:
        end_date = datetime.now()
        
        for i in range(days):
            date = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
            
            print(f"抓取 {date} 數據...")
            
            df = crawler.get_broker_flow_by_date(
                broker_code='9600',
                start_date=date,
                end_date=date
            )
            
            if not df.empty:
                crawler.save_to_csv(df, f'broker_data_{date}.csv')
                print(f"  ✅ 成功: {len(df)} 筆")
            else:
                print(f"  ⚠️ 無數據")

# 執行（回補最近30天）
backfill_historical_data(days=30)
```

## ⚠️ 注意事項

### 1. 請求頻率控制

**重要**: 請務必遵守合理的請求頻率，避免對目標網站造成負擔。

- ✅ 建議: 每次請求間隔 3-8 秒
- ✅ 建議: 每 5 次請求休息 15-30 秒
- ❌ 避免: 連續快速請求
- ❌ 避免: 同時多線程爬取

### 2. 錯誤處理

```python
from app.services.advanced_broker_crawler import AdvancedBrokerCrawler

with AdvancedBrokerCrawler() as crawler:
    try:
        df = crawler.get_broker_flow_by_date('9600')
        
        if df.empty:
            print("⚠️ 未抓取到數據，可能原因:")
            print("  1. 網站結構變更")
            print("  2. IP被封鎖")
            print("  3. 日期參數錯誤")
            print("  4. 網路連線問題")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
```

### 3. 調試模式

當抓取失敗時，系統會自動保存HTML到調試文件：

```python
# 調試文件會自動生成
# 格式: debug_html_YYYYMMDD_HHMMSS.html
# 或: debug_broker_9600_YYYYMMDD_HHMMSS.html
```

查看調試文件可以幫助診斷問題：
- 檢查HTML結構是否變更
- 確認是否被重定向到驗證頁面
- 查看實際返回的內容

### 4. IP封鎖處理

如果遇到IP被封鎖（403錯誤）：

1. **增加延遲時間**
```python
crawler.min_delay = 10
crawler.max_delay = 20
```

2. **減少批次大小**
```python
crawler.batch_size = 3  # 每3次請求休息
```

3. **使用代理IP**（未來版本支援）
```python
crawler = AdvancedBrokerCrawler(use_proxy=True)
```

## 🔍 故障排除

### 問題1: 一直返回空數據

**可能原因**:
- 網站HTML結構變更
- 日期參數格式錯誤
- 券商代碼錯誤

**解決方案**:
1. 檢查調試HTML文件
2. 驗證日期格式（YYYY-MM-DD）
3. 確認券商代碼正確

### 問題2: 請求被拒絕（403）

**可能原因**:
- 請求過於頻繁
- User-Agent被識別
- IP被暫時封鎖

**解決方案**:
1. 增加延遲時間
2. 減少請求頻率
3. 等待一段時間後重試

### 問題3: 請求超時

**可能原因**:
- 網路連線不穩定
- 目標網站回應慢

**解決方案**:
1. 檢查網路連線
2. 增加timeout時間
3. 重試請求

## 📈 效能優化

### 1. 批次處理

```python
# 不建議：逐一處理
for code in stock_codes:
    df = crawler.get_broker_flow_by_date(code)
    process(df)

# 建議：批次處理
df_all = crawler.get_multiple_brokers_data(stock_codes)
process(df_all)
```

### 2. 資源管理

```python
# 使用上下文管理器自動清理
with AdvancedBrokerCrawler() as crawler:
    # 使用爬蟲
    pass
# 自動清理資源
```

### 3. 錯誤恢復

```python
from app.services.advanced_broker_crawler import AdvancedBrokerCrawler

def robust_fetch(broker_code, max_attempts=3):
    """穩健的抓取函數"""
    for attempt in range(max_attempts):
        try:
            with AdvancedBrokerCrawler() as crawler:
                df = crawler.get_broker_flow_by_date(broker_code)
                
                if not df.empty:
                    return df
                    
        except Exception as e:
            print(f"嘗試 {attempt + 1} 失敗: {e}")
            
            if attempt < max_attempts - 1:
                import time
                time.sleep(30)  # 等待30秒後重試
    
    return pd.DataFrame()
```

## 🔄 整合到選股系統

進階爬蟲已整合到 `broker_flow_analyzer.py`：

```python
from app.services.broker_flow_analyzer import broker_flow_analyzer

# 自動使用進階爬蟲
flow_summary = broker_flow_analyzer.get_broker_flow_summary('2330', days=5)

# 如果進階爬蟲失敗，會自動切換到備用方案
```

## 📞 測試與驗證

### 運行測試腳本

```bash
# 測試進階爬蟲
python3 test_advanced_crawler.py

# 測試券商分析器（整合版）
python3 test_broker_flow_simple.py
```

### 預期輸出

```
================================================================================
🔍 測試進階券商爬蟲
================================================================================

【測試1】抓取富邦新店最近5天數據
--------------------------------------------------------------------------------
✅ 請求成功: https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm... (嘗試 1 次)
✅ 解析成功，共 150 筆數據
✅ 成功抓取 150 筆數據

前10筆數據:
  stock_code stock_name  buy_count  sell_count  net_count
0       2330       台積電       1500         500       1000
1       2454      聯發科        800         300        500
...
```

## 📝 更新日誌

### v1.0.0 (2026-01-01)
- ✅ 初始版本發布
- ✅ 支援富邦證券券商進出數據抓取
- ✅ 實現5層反爬蟲策略
- ✅ 自動重試與錯誤處理
- ✅ 批次處理與資源管理
- ✅ 調試模式與日誌記錄

---

**建立日期**: 2026-01-01  
**版本**: v1.0.0  
**狀態**: ✅ 已完成並可用  
**維護**: 持續更新中
