# 🎯 立即開始使用 - 5分鐘快速指南

## 第一步：確認環境 (1分鐘)

```bash
# 檢查 Python 版本 (需要 3.9+)
python3 --version

# 應該看到: Python 3.9.x 或更高
```

如果版本太舊，請先升級 Python。

---

## 第二步：安裝依賴 (2分鐘)

```bash
# 進入專案目錄
cd Ａi-catch

# 安裝必要套件
pip3 install -r requirements.txt

# 等待安裝完成...
```

---

## 第三步：測試系統 (1分鐘)

```bash
# 運行測試腳本
python3 test_system.py
```

**期望結果**:
```
🚀 AI主力偵測系統 - 完整測試
====================================
✓ imports: PASS
✓ config: PASS
✓ database: PASS
✓ detector: PASS
...
總計: 7/7 測試通過 (100.0%)
🎉 所有測試通過！系統可以正常運行。
```

---

## 第四步：啟動監控 (1分鐘)

```bash
# 給腳本執行權限 (首次使用)
chmod +x start_monitor.sh

# 啟動系統
./start_monitor.sh

# 選擇: 1 (前台運行)
```

**你會看到**:
```
🚀 啟動 AI 主力監控系統...
✓ Python 版本檢查通過: 3.11
✓ 配置文件檢查通過
====================================
🚀 啟動AI主力監控系統
📊 監控清單: ['2330.TW', '2317.TW', ...]
⏰ 將在交易時間自動運行
====================================
```

---

## 🎉 完成！

系統現在正在運行！

### 接下來會發生什麼？

1. **非交易時間**: 系統等待，每分鐘檢查一次
2. **交易時間** (09:00-13:30): 
   - 自動獲取股票數據
   - 分析主力特徵
   - 發現主力時顯示警報

### 停止系統

```bash
# 按 Ctrl+C 停止
# 或者使用停止腳本
./stop_monitor.sh
```

---

## 🔧 可選：啟用通知 (額外5分鐘)

### LINE Notify

1. 前往: https://notify-bot.line.me/my/
2. 點擊「發行權杖」
3. 複製權杖

```bash
# 設定環境變數
export LINE_NOTIFY_TOKEN="你的權杖"
```

4. 編輯 `config.yaml`:
```yaml
notifications:
  line:
    enabled: true  # 改為 true
```

5. 重啟系統，完成！

---

## 📊 查看結果

### 即時日誌

```bash
tail -f logs/stock_monitor.log
```

### 查看警示記錄

```bash
sqlite3 data/stock_monitor.db "SELECT * FROM stock_alerts ORDER BY timestamp DESC LIMIT 10;"
```

---

## ❓ 常見問題

**Q: 沒有收到通知？**  
A: 確認已設定環境變數並在 config.yaml 啟用

**Q: 系統沒有發出警報？**  
A: 
- 檢查是否為交易時間
- 降低信心閥值 (config.yaml 中 confidence_threshold: 0.5)
- 等待一段時間，主力不是每天都有

**Q: 如何調整監控清單？**  
A: 編輯 `config.yaml` 中的 `watchlist.stocks` 區塊

---

## 📚 延伸閱讀

- [完整文檔](README.md) - 詳細說明
- [快速指南](QUICKSTART.md) - 進階設定
- [架構說明](ARCHITECTURE.md) - 深入理解
- [專案總結](PROJECT_SUMMARY.md) - 全面回顧

---

## 🎓 下一步建議

1. **第1天**: 熟悉系統輸出
2. **第2-3天**: 調整參數找到最佳設定
3. **第1週**: 啟用通知，實際使用
4. **第2週**: 分析歷史警示，優化策略
5. **長期**: 訓練自己的 ML 模型

---

## 💡 專業提示

1. 先從 3-5 支熟悉的股票開始
2. 不要設定太低的信心閥值 (建議 0.7-0.8)
3. 定期檢視警示準確度
4. 結合技術分析，不要盲目跟單
5. 設定停損，控制風險

---

**祝您交易順利！** 📈💰

有問題隨時查看文檔或開 Issue 討論。

---

**快速連結**:
- [系統測試](test_system.py) - `python3 test_system.py`
- [啟動系統](start_monitor.sh) - `./start_monitor.sh`
- [停止系統](stop_monitor.sh) - `./stop_monitor.sh`
- [配置文件](config.yaml) - 調整設定
- [完整文檔](README.md) - 詳細說明
