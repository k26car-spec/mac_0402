# 富邦SDK安裝問題解決方案

## 🔍 問題診斷

### 發現的問題：
1. ✅ 您在**全域Python**安裝了 `fubon-neo` (2.2.5版本)
2. ❌ 但後端使用**虛擬環境(venv)**
3. ❌ venv中的pip**找不到fubon-neo套件**
4. ❌ PyPI上**沒有fubon-neo這個公開套件**

### 結論：
`fubon-neo` 不是公開套件，可能是：
- 富邦證券提供的私有SDK
- 需要從富邦官方網站下載
- 或者通過特殊管道獲取

---

## 💡 解決方案

### **方案一：使用系統site-packages（推薦）**

讓venv使用全域Python的套件：

```bash
# 1. 刪除現有venv
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
rm -rf venv

# 2. 重新創建venv，允許訪問系統套件
python3 -m venv venv --system-site-packages

# 3. 啟動venv並安裝其他依賴
source venv/bin/activate
pip install -r requirements-v3.txt

# 4. 重啟後端
# uvicorn會自動重載
```

**優點**: 
- ✅ 可以使用全域的fubon-neo
- ✅ 不需要重新下載SDK

---

### **方案二：在venv中手動安裝**

如果fubon-neo有安裝檔：

```bash
cd backend-v3
source venv/bin/activate

# 如果有.whl文件
pip install /path/to/fubon_neo-2.2.5-py3-none-any.whl

# 或如果有.tar.gz
pip install /path/to/fubon-neo-2.2.5.tar.gz
```

---

### **方案三：不使用venv（臨時方案）**

修改啟動命令，直接使用全域Python：

```bash
# 停止當前後端
# Ctrl+C 在運行的terminal

# 直接使用系統Python
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
python3 -m uvicorn app.main:app --reload --port 8000
```

**缺點**:
- ⚠️ 可能與其他專案的套件衝突

---

## 🧪 測試SDK是否生效

### **測試腳本**：

```python
# test_fubon_sdk.py
import sys
print(f"Python路徑: {sys.executable}")
print(f"Python版本: {sys.version}")

try:
    import fubon_neo
    print(f"✅ fubon_neo模塊已導入")
    print(f"   版本: {fubon_neo.__version__ if hasattr(fubon_neo, '__version__') else '未知'}")
    print(f"   路徑: {fubon_neo.__file__}")
    
    from fubon_neo.sdk import FubonSDK
    print(f"✅ FubonSDK類已導入")
    
except ImportError as e:
    print(f"❌ 導入失敗: {e}")
```

### **在venv中測試**：
```bash
cd backend-v3
source venv/bin/activate
python test_fubon_sdk.py
```

### **在全域測試**：
```bash
python3 test_fubon_sdk.py
```

---

## 📊 當前狀態

| 項目 | 狀態 | 說明 |
|-----|------|------|
| 全域Python fubon-neo | ✅ 已安裝 | 2.2.5版本 |
| venv fubon-neo | ❌ 未安裝 | pip找不到套件 |
| 後端運行環境 | venv | 使用虛擬環境 |
| 真實數據啟用 | ❌ 未生效 | SDK在venv中不可用 |

---

## 🚀 立即行動建議

### **最快方案（5分鐘）**：

```bash
# 1. 重建venv with系統套件
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
rm -rf venv
python3 -m venv venv --system-site-packages

# 2. 重新安裝依賴
source venv/bin/activate
pip install -r requirements-v3.txt

# 3. 測試
python -c "import fubon_neo; print('✅ SDK可用')"

# 4. 檢查後端日誌
# uvicorn會自動重載，查看是否有富邦連接成功的訊息
```

---

## 📝 檢查是否生效

刷新 `http://127.0.0.1:8082/premarket` 然後：

### **查看後端日誌**：
```bash
# 在後端terminal會看到
✅ 富邦SDK已載入           # SDK可用
📊 成功獲取17支股票技術數據  # 真實數據

# 或者
⚠️ fubon-neo未安裝        # SDK不可用
```

### **查看股價**：
如果生效，股價會：
- ✅ **每30秒變動**（即時報價）
- ✅ **顯示買賣5檔**
- ✅ **技術指標是真實計算的**

如果沒生效，股價是：
- ❌ **固定不變**
- ❌ **1035, 110, 1275等固定值**

---

## ⚠️ 注意事項

1. **富邦SDK特性**：
   - 可能需要富邦證券帳戶
   - 需要API憑證(帳號、密碼、憑證密碼)
   - 只在台股交易時間可用

2. **配置需求**：
   - 確保 `fubon.env` 配置正確
   - 確保 `ENCRYPTION_SECRET_KEY` 存在

3. **測試時機**：
   - 最好在台股交易時間測試（09:00-13:30）
   - 盤後只能測試連接，無法獲取即時報價

---

## 🎯 預期結果

### **成功後您會看到**：

```
🏆 監控清單精選分析
┌────────────────────────────┐
│ 🥇 台積電 (2330)           │
│ 價格: 1037.50  ← 即時變動！│
│ 信心度: 87%    ← 真實計算！│
│ ✅ 量能放大2.5倍            │
│ ✅ 突破月線1035             │
│ ✅ 外資買超18000張          │
└────────────────────────────┘
```

vs 現在的固定值：
```
價格: 1035.00  ← 永遠不變
信心度: 85%    ← 公式計算
```

---

*建議使用【方案一】重建venv with --system-site-packages*  
*預計5分鐘內完成，最快啟用真實數據！*
