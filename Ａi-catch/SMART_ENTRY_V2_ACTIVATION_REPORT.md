# 智能進場系統 v2.0 自動掃描功能啟用報告

## 📅 更新時間
2026-02-07 14:20

## ✅ 完成的修改

### 1. **添加自動定時掃描任務** 
文件：`/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/app/main.py`

#### 修改內容：
在 `lifespan` 函數中添加了智能進場系統 v2.0 的後台掃描任務：

```python
# 🆕 啟動智能進場系統 v2.0（定時掃描）
try:
    from app.services.smart_entry_system import smart_entry_system
    
    async def smart_entry_scanner():
        """智能進場系統定時掃描
        
        在交易時段每5分鐘掃描一次，執行以下策略：
        1. 回檔買 (Pullback) - 保守
        2. 突破買 (Breakout) - 激進
        3. 動能買 (Momentum) - 看量
        4. VWAP 反彈 - 技術面
        """
        import asyncio
        from datetime import datetime, time as dt_time
        
        while True:
            await asyncio.sleep(300)  # 每5分鐘掃描一次
            
            # 只在交易時段運行 (09:30-13:00)
            now = datetime.now()
            current_time = now.time()
            
            if dt_time(9, 30) <= current_time <= dt_time(13, 0):
                try:
                    result = await smart_entry_system.run_scan_and_trade()
                    signals_found = result.get('signals_found', 0)
                    positions_opened = result.get('positions_opened', 0)
                    
                    if signals_found > 0:
                        logger.info(
                            f"🎯 智能進場 v2.0: 發現 {signals_found} 個信號，"
                            f"成功建倉 {positions_opened} 筆"
                        )
                    else:
                        logger.debug("🎯 智能進場 v2.0: 本次掃描無符合條件的進場信號")
                        
                except Exception as e:
                    logger.error(f"智能進場系統掃描失敗: {e}")
    
    import asyncio
    asyncio.create_task(smart_entry_scanner())
    print("🎯 智能進場系統 v2.0 已啟動（交易時段每5分鐘掃描 - 4策略評估）")
    app.state.smart_entry_system = smart_entry_system
except Exception as e:
    print(f"⚠️ 智能進場系統啟動失敗: {e}")
```

#### 功能說明：
- **運行時間**：僅在交易時段 (09:30-13:00) 運行
- **掃描頻率**：每 5 分鐘掃描一次
- **自動執行**：發現符合條件的信號時自動建倉
- **日誌記錄**：記錄掃描結果和建倉情況

---

### 2. **更新啟動日誌信息**
文件：`/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/app/main.py`

在 AI 交易輔助功能列表中添加：
```python
print("   🎯 智能進場:   GET  /api/smart-entry/system-status")
```

---

### 3. **更新啟動腳本顯示**
文件：`/Users/Mac/Documents/ETF/AI/Ａi-catch/start_v3.sh`

添加智能進場系統 v2.0 的 API 端點說明：

```bash
echo -e "${CYAN}📌 智能進場系統 v2.0 API (Port 8000) [NEW!]：${NC}"
echo "   • 系統狀態:        http://localhost:8000/api/smart-entry/system-status"
echo "   • 掃描信號:        http://localhost:8000/api/smart-entry/scan"
echo "   • 掃描並交易:      http://localhost:8000/api/smart-entry/scan-and-trade"
echo "   • 評估單股:        http://localhost:8000/api/smart-entry/evaluate/{symbol}"
echo "   💡 說明: 交易時段每5分鐘自動掃描 - 4種策略評估（回檔/突破/動能/VWAP反彈）"
```

---

## 🎯 智能進場系統 v2.0 架構

### 四大策略：

1. **回檔買 (Pullback)** - 保守策略
   - 條件：價格接近 MA5（乖離 < 5%）+ 量比 > 1.2 + 趨勢向上
   - 適合：穩健型投資者

2. **突破買 (Breakout)** - 激進策略
   - 條件：漲幅 5-10% + 量比 > 1.5x + 突破 MA5 和 MA20
   - 適合：積極型投資者

3. **動能買 (Momentum)** - 看量策略
   - 條件：量比 > 3x（爆量）+ 漲幅 > 3% + 價格在高檔區
   - 適合：短線追漲

4. **VWAP 反彈** - 技術面策略
   - 條件：價格曾跌破 VWAP 後回升 + 整體趨勢仍上漲
   - 適合：技術分析派

### 風險控制：

- **動態閾值管理**：根據市場狀況和時間動態調整進場閾值
- **進場時間控制**：
  - 黃金期 09:30-10:30：最佳進場時段
  - 可接受期 10:31-11:00：需更嚴格的停利停損
  - 限制期 11:01-13:00：僅極優質信號
- **大盤過濾**：整合市場狀況判斷，大盤不佳時限制進場
- **信心度計算**：綜合評分系統，只選擇高信心度標的

### 技術指標：

系統自動計算以下指標：
- MA5, MA20（移動平均線）
- VWAP（成交量加權平均價）
- 量比（Volume Ratio）
- 乖離率（Deviation）
- ATR（停損計算用）

---

## 📊 使用方式

### 自動模式（已啟用）
系統啟動後會自動運行，無需手動操作。

### 手動調用 API

1. **查看系統狀態**
```bash
curl http://localhost:8000/api/smart-entry/system-status
```

2. **手動掃描信號**
```bash
curl -X POST http://localhost:8000/api/smart-entry/scan
```

3. **手動掃描並交易**
```bash
curl -X POST http://localhost:8000/api/smart-entry/scan-and-trade
```

4. **評估單個股票**
```bash
curl -X POST http://localhost:8000/api/smart-entry/evaluate/2330
```

5. **重置系統（清除今日已發送信號）**
```bash
curl -X POST http://localhost:8000/api/smart-entry/reset
```

---

## 🔄 如何重啟系統以應用更改

### 方法 1：使用啟動腳本（推薦）

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh
```

### 方法 2：手動重啟

1. 停止現有服務：
```bash
# 找到並殺掉 backend 進程
lsof -ti:8000 | xargs kill -9

# 或使用保存的 PID
kill -9 $(cat /Users/Mac/Documents/ETF/AI/Ａi-catch/.backend.pid)
```

2. 重新啟動：
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
```

---

## 📝 監控和日誌

### 查看系統日誌

```bash
# 實時查看後端日誌
tail -f /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/backend.log

# 搜索智能進場相關日誌
grep "智能進場" /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/backend.log
```

### 預期日誌輸出

系統啟動時會顯示：
```
🎯 智能進場系統 v2.0 已啟動（交易時段每5分鐘掃描 - 4策略評估）
```

掃描時會記錄：
```
🎯 智能進場 v2.0: 發現 3 個信號，成功建倉 2 筆
```

或

```
🎯 智能進場 v2.0: 本次掃描無符合條件的進場信號
```

---

## ✨ 預期效果

系統重啟後，您將看到以下變化：

1. **啟動時**：控制台會顯示 "🎯 智能進場系統 v2.0 已啟動"
2. **交易時段**：每 5 分鐘自動掃描一次，發現機會自動建倉
3. **建倉通知**：建倉成功後會發送 Email 通知（如已配置）
4. **持倉管理**：可在 Portfolio 中查看建立的持倉
5. **API 訪問**：可通過 API 端點查詢系統狀態和手動觸發掃描

---

## 🎉 總結

✅ **已完成**：
- 添加智能進場系統 v2.0 的自動定時掃描任務
- 更新啟動腳本和日誌信息
- 整合 4 種進場策略和風險控制機制

✅ **自動運行**：
- 交易時段 (09:30-13:00) 每 5 分鐘自動掃描
- 發現符合條件的信號自動建倉
- 自動發送 Email 通知（需配置郵件設定）

✅ **可手動控制**：
- 提供完整的 REST API 端點
- 可查看狀態、手動掃描、評估個股
- 可重置系統清除今日信號

---

**smart_entry_v2 現在已經完全啟用並自動運行！** 🚀
