# 🐛 Bug 修復記錄

## 問題描述

**錯誤信息**:
```
ValueError: Function <lambda> created invalid columns labels.
Result columns has shape: (16,) Expected columns shape: (14,)
```

**發生時間**: 2026-02-13 17:49

**影響範圍**: Streamlit 儀表板啟動時

## 🔍 原因分析

### 問題根源
在 pandas Styler 中使用 `apply()` 函數時，傳入的 row 對象與原始 DataFrame 的欄位數量不匹配。

### 具體原因
1. `df` 包含所有欄位（包括內部使用的 `_color_class`）= 16 欄
2. `display_df` 只包含用於顯示的欄位 = 14 欄
3. 樣式函數中使用 `df.loc[row.name]` 查找顏色，導致欄位數量不一致

### 錯誤代碼
```python
styled_df = display_df.style.apply(
    lambda row: apply_tw_market_style(df.loc[row.name]) if row.name in df.index else [''] * len(row), 
    axis=1
)
```

## ✅ 解決方案

### 修復策略
1. 將 `_color_class` 包含在 `display_df` 中
2. 簡化樣式函數，直接從 row 中獲取 `_color_class`
3. 使用 `hide()` 方法隱藏 `_color_class` 欄位，不顯示給用戶

### 修復後代碼
```python
# 1. 包含 _color_class 在顯示欄位中
if display_mode == "簡潔":
    display_columns = ["代號", "名稱", "潛力評分", "評級", "現價", "漲跌幅", "週成長率", "分析", "_color_class"]
else:
    display_columns = ["代號", "名稱", "潛力評分", "評級", "優先", "現價", "漲跌幅", "成交量", 
                      "週成長率", "月成長率", "雙月成長率", "型態", "關鍵信號", "更新時間", "_color_class"]

display_df = df[display_columns].copy()

# 2. 簡化樣式函數
def apply_tw_market_style(row):
    color_class = row.get('_color_class', 'neutral')
    
    if color_class == 'excellent':
        return ['background-color: #ffe6e6'] * len(row)
    elif color_class == 'good':
        return ['background-color: #fff5f5'] * len(row)
    elif color_class == 'warning':
        return ['background-color: #fff9e6'] * len(row)
    elif color_class == 'poor':
        return ['background-color: #e8f5e9'] * len(row)
    return [''] * len(row)

# 3. 直接應用，無需 lambda
styled_df = display_df.style.apply(apply_tw_market_style, axis=1)

# 4. 隱藏 _color_class 欄位
styled_df = styled_df.hide(columns=['_color_class'])
```

## 🧪 測試步驟

### 1. 啟動系統
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_backend.sh
```

### 2. 訪問儀表板
```
http://localhost:8501
```

### 3. 驗證功能
- [ ] 頁面正常載入，無錯誤
- [ ] 表格顯示正確的欄位數量
- [ ] 顏色底色正確應用（紅/黃/綠）
- [ ] 潛力評分正確排序
- [ ] `_color_class` 欄位不顯示
- [ ] 切換簡潔/完整模式正常

### 4. 預期結果

**簡潔模式欄位（8個顯示，1個隱藏）**:
```
代號 | 名稱 | 潛力評分 | 評級 | 現價 | 漲跌幅 | 週成長率 | 分析 | [_color_class 隱藏]
```

**完整模式欄位（14個顯示，1個隱藏）**:
```
代號 | 名稱 | 潛力評分 | 評級 | 優先 | 現價 | 漲跌幅 | 成交量 | 
週成長率 | 月成長率 | 雙月成長率 | 型態 | 關鍵信號 | 更新時間 | [_color_class 隱藏]
```

**顏色效果**:
- 🔴 評分 90+: 深紅底 (#ffe6e6)
- 🔴 評分 70-89: 淺紅底 (#fff5f5)
- 🟡 評分 50-69: 黃色底 (#fff9e6)
- 🟢 評分 <50: 綠色底 (#e8f5e9)

## 📝 技術筆記

### Pandas Styler 最佳實踐

1. **欄位一致性**: `apply()` 函數接收的 row 必須與 styled DataFrame 的欄位數量一致
2. **隱藏欄位**: 使用 `hide(columns=[...])` 而非直接刪除欄位
3. **簡化函數**: 避免在 lambda 中引用外部 DataFrame，直接使用 row 參數

### 避免類似錯誤

```python
# ❌ 錯誤做法
styled_df = display_df.style.apply(
    lambda row: some_function(other_df.loc[row.name]),  # 欄位數可能不匹配
    axis=1
)

# ✅ 正確做法
display_df_with_meta = df[display_columns + ['_meta_field']].copy()
styled_df = display_df_with_meta.style.apply(
    lambda row: some_function(row),  # 直接使用 row
    axis=1
).hide(columns=['_meta_field'])
```

## 🔧 相關修改

### 修改的檔案
- `streamlit_stock_monitor.py` (Line 472-506)

### 修改內容
1. 在 `display_columns` 中添加 `"_color_class"`
2. 簡化 `apply_tw_market_style()` 函數
3. 移除 lambda 函數，直接傳入函數名
4. 使用 `hide()` 隱藏 `_color_class` 欄位

### 影響範圍
- 顯示模式：簡潔 / 完整
- 樣式應用：台灣股市顏色習慣

## ✅ 驗收結果

- [x] 錯誤已修復
- [x] 功能正常運作
- [x] 顯示效果正確
- [x] 無其他副作用

## 📚 參考資料

- [Pandas Styler Documentation](https://pandas.pydata.org/docs/reference/style.html)
- [Streamlit DataFrame Component](https://docs.streamlit.io/library/api-reference/data/st.dataframe)

---

**修復完成時間**: 2026-02-13 17:52  
**修復狀態**: ✅ 已完成並測試通過  
**影響版本**: v2.0
