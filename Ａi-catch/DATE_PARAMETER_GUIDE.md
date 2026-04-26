# ⚠️ 重要提醒：日期參數說明

## 📅 日期自動更新機制

### ✅ 已自動處理

所有爬蟲腳本都已配置為**自動使用當天日期**，您不需要手動修改！

```python
# 系統會自動使用今天的日期
today = datetime.now().strftime('%Y-%m-%d')  # 例如: 2026-01-01

params = {
    'e': today,   # 開始日期：今天
    'f': today    # 結束日期：今天
}
```

### 📊 富邦網址格式

富邦證券的URL格式：
```
https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a=9600&b=9661&c=E&e=2026-01-01&f=2026-01-01
                                                                                    ↑          ↑
                                                                              開始日期    結束日期
```

**重要**：
- `e` 參數：開始日期（格式：YYYY-MM-DD）
- `f` 參數：結束日期（格式：YYYY-MM-DD）
- 兩個日期相同表示查詢單日數據

---

## 🔧 已更新的文件

### 1. `test_fubon_direct.py`

**修改前**：
```python
params = {
    'e': '2024-12-31',  # ❌ 固定日期
    'f': '2024-12-31'
}
```

**修改後**：
```python
today = datetime.now().strftime('%Y-%m-%d')

params = {
    'e': today,   # ✅ 自動使用今天
    'f': today
}
```

### 2. `advanced_broker_crawler.py`

已內建自動日期處理（第328-331行）：
```python
# 設定預設日期
if not end_date:
    end_date = datetime.now().strftime('%Y-%m-%d')  # 自動使用今天
if not start_date:
    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')  # 最近5天
```

### 3. `broker_flow_analyzer.py`

已整合進階爬蟲，自動使用當天日期。

---

## 💡 使用範例

### 範例1：抓取今天的數據（預設）

```bash
# 自動使用今天的日期
python3 test_fubon_direct.py
```

### 範例2：抓取特定日期

```python
from app.services.advanced_broker_crawler import advanced_broker_crawler

# 指定日期
df = advanced_broker_crawler.get_broker_flow_by_date(
    broker_code='9600',
    start_date='2025-12-25',  # 指定開始日期
    end_date='2025-12-31'     # 指定結束日期
)
```

### 範例3：抓取最近N天

```python
from datetime import datetime, timedelta

# 最近7天
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

df = advanced_broker_crawler.get_broker_flow_by_date(
    broker_code='9600',
    start_date=start_date.strftime('%Y-%m-%d'),
    end_date=end_date.strftime('%Y-%m-%d')
)
```

---

## 🎯 一鍵執行（自動使用今天）

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 完整流程（自動使用今天的日期）
python3 run_full_analysis.py
```

這會：
1. ✅ 自動抓取**今天**的券商數據
2. ✅ 解析並提取買賣資訊
3. ✅ 執行選股分析
4. ✅ 生成報告

---

## 📝 日期格式說明

### 正確格式

```python
'2026-01-01'  # ✅ 正確：YYYY-MM-DD
'2025-12-31'  # ✅ 正確
```

### 錯誤格式

```python
'2026/01/01'  # ❌ 錯誤：使用斜線
'01-01-2026'  # ❌ 錯誤：順序錯誤
'2026-1-1'    # ❌ 錯誤：沒有補零
```

---

## 🔍 檢查當前使用的日期

執行任何腳本時，會顯示使用的日期：

```bash
$ python3 test_fubon_direct.py

📊 請求URL: https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm
📊 參數: {'a': '9600', 'b': '9600', 'c': 'E', 'e': '2026-01-01', 'f': '2026-01-01'}
📅 使用日期: 2026-01-01  ← 這裡會顯示實際使用的日期
```

---

## ⚙️ 自訂日期範圍

如果需要查詢歷史數據：

### 方法1：修改便捷函數

```python
from app.services.advanced_broker_crawler import advanced_broker_crawler

# 查詢2025年12月的數據
df = advanced_broker_crawler.get_broker_flow_by_date(
    broker_code='9600',
    start_date='2025-12-01',
    end_date='2025-12-31'
)
```

### 方法2：批量查詢多日

```python
from datetime import datetime, timedelta

# 查詢最近30天
for i in range(30):
    date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
    
    df = advanced_broker_crawler.get_broker_flow_by_date(
        broker_code='9600',
        start_date=date,
        end_date=date
    )
    
    if not df.empty:
        print(f"{date}: {len(df)} 筆數據")
```

---

## 📊 日期相關的常見問題

### Q1: 為什麼抓不到數據？

**A**: 可能原因：
1. 查詢的日期是**非交易日**（週末、假日）
2. 日期格式錯誤
3. 日期太舊（網站可能只保留近期數據）

**解決方案**：
```python
# 使用今天的日期（最可靠）
today = datetime.now().strftime('%Y-%m-%d')
```

### Q2: 如何確認使用的日期正確？

**A**: 查看腳本輸出：
```bash
📅 使用日期: 2026-01-01
```

### Q3: 可以查詢未來的日期嗎？

**A**: 不可以。只能查詢今天或過去的日期。

---

## ✅ 總結

1. **所有腳本已自動使用當天日期** - 您不需要手動修改
2. **一鍵執行即可** - `python3 run_full_analysis.py`
3. **需要歷史數據** - 使用 `get_broker_flow_by_date()` 並指定日期
4. **日期格式** - 必須是 `YYYY-MM-DD`

---

**現在就試試看！**

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 run_full_analysis.py
```

系統會自動使用今天的日期（2026-01-01）抓取最新數據！🚀
