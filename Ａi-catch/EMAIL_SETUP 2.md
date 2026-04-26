# 📧 Email 通知設定指南

## 🚀 快速設定（3分鐘）

### 方法 A: 使用設定助手（最簡單）

```bash
./setup_email.sh
# 按照提示輸入 Gmail 地址和應用程式密碼
```

### 方法 B: 手動設定

#### 1️⃣ 取得 Gmail 應用程式密碼

**重要**: 必須使用「應用程式密碼」，不能使用您的 Gmail 登入密碼！

1. **前往**: https://myaccount.google.com/security
2. **啟用兩步驟驗證** (如果還沒啟用)
   - 在「登入 Google」區塊找到「兩步驟驗證」
   - 按照指示完成設定
3. **產生應用程式密碼**
   - 回到安全性頁面
   - 找到「應用程式密碼」
   - 選擇應用程式: **郵件**
   - 選擇裝置: **其他（自訂名稱）**
   - 輸入名稱: **AI主力偵測系統**
   - 點擊「產生」
   - 複製 16 位元密碼（例如: `abcd efgh ijkl mnop`）

#### 2️⃣ 設定環境變數

**選項 1: 使用 .env 檔案**（推薦）

```bash
# 複製範例檔案
cp .env.example .env

# 編輯 .env
nano .env
```

在 `.env` 中添加：

```bash
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=abcdefghijklmnop  # 移除空格
```

**選項 2: 直接設定環境變數**

```bash
export EMAIL_USERNAME="your_email@gmail.com"
export EMAIL_PASSWORD="abcdefghijklmnop"
```

#### 3️⃣ 啟用 Email 通知

編輯 `config.yaml`:

```yaml
notifications:
  email:
    enabled: true  # ← 改為 true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    recipients:
      - "your_email@gmail.com"  # ← 您的收件信箱
      - "another@example.com"   # ← 可添加多個收件人
```

#### 4️⃣ 測試設定

```bash
# 方法 1: 使用測試腳本
python3 test_email.py

# 方法 2: 直接啟動系統
./start_monitor.sh
```

---

## 🔧 其他 Email 服務商

### Outlook / Hotmail

```yaml
email:
  smtp_server: "smtp-mail.outlook.com"
  smtp_port: 587
  username: your_email@outlook.com
```

### Yahoo Mail

```yaml
email:
  smtp_server: "smtp.mail.yahoo.com"
  smtp_port: 587
  username: your_email@yahoo.com
```

### 其他

```yaml
email:
  smtp_server: "smtp.your-provider.com"
  smtp_port: 587  # 或 465 (SSL)
```

---

## 🐛 問題排除

### ❌ 535 Authentication failed

**原因**: 密碼錯誤或未使用應用程式密碼

**解決**:
1. 確認使用的是「應用程式密碼」而非 Gmail 登入密碼
2. 確認已啟用「兩步驟驗證」
3. 重新產生應用程式密碼

### ❌ Connection refused / Timeout

**原因**: 網路或防火牆問題

**解決**:
1. 檢查網路連線
2. 確認防火牆允許 SMTP (port 587)
3. 嘗試使用 port 465 (SSL)

### ❌ Name or service not known

**原因**: DNS 解析問題

**解決**:
1. 檢查 SMTP 伺服器地址是否正確
2. 測試網路連線: `ping smtp.gmail.com`

### 📬 沒收到郵件

**檢查**:
1. 查看垃圾郵件匣
2. 確認收件人地址正確
3. 等待幾秒鐘（Gmail 可能有延遲）
4. 查看系統日誌: `tail -f logs/stock_monitor.log`

---

## 📨 郵件範例

當系統偵測到主力時，您會收到：

**主旨**: `主力大單警報 - 2330.TW`

**內容**:
```
🚨 主力大單警報 🚨

📈 股票代碼: 2330.TW
⭐ 信心指數: 85.30%
🕒 時間: 2024-12-11 10:30:15

📊 關鍵特徵:
• 量能比率: 2.35
• 大單比例: 42.50%
• 資金流向: 78.20
• 法人追蹤: 0.65
• 型態突破: 6.20%

🔗 快速連結:
• Yahoo主力: https://tw.stock.yahoo.com/quote/2330.TW/agent
• 富邦分析: https://www.fubon.com/stock/2330.TW

───────────────────────
發送時間: 2024-12-11 10:30:15
```

---

## 💡 進階設定

### 多個收件人

```yaml
email:
  recipients:
    - "email1@gmail.com"
    - "email2@outlook.com"
    - "email3@yahoo.com"
```

### 自訂 SMTP Port

```yaml
email:
  smtp_port: 465  # SSL port
  # 或
  smtp_port: 587  # TLS port (預設)
```

### 使用 SSL

修改 `notifier.py` 中的郵件發送邏輯：

```python
# 使用 SMTP_SSL
import smtplib
from email.mime.text import MIMEText

# SSL 連線
with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
    server.login(self.email_username, self.email_password)
    server.send_message(msg)
```

---

## ✅ 檢核清單

設定完成後，確認：

- [ ] 已啟用 Gmail 兩步驟驗證
- [ ] 已產生應用程式密碼
- [ ] 已設定 EMAIL_USERNAME 環境變數
- [ ] 已設定 EMAIL_PASSWORD 環境變數
- [ ] 已在 config.yaml 啟用 Email (enabled: true)
- [ ] 已設定收件人地址
- [ ] 已運行 test_email.py 測試
- [ ] 已收到測試郵件

---

## 🚀 快速指令參考

```bash
# 設定助手
./setup_email.sh

# 測試 Email
python3 test_email.py

# 查看環境變數
echo $EMAIL_USERNAME
echo $EMAIL_PASSWORD

# 啟動系統
./start_monitor.sh

# 查看日誌
tail -f logs/stock_monitor.log
```

---

## 🔒 安全提示

1. ✅ **使用應用程式密碼**，不要使用主密碼
2. ✅ **不要分享**應用程式密碼
3. ✅ **不要提交** .env 檔案到 Git
4. ✅ **定期更換**應用程式密碼
5. ✅ **不再使用時**記得刪除應用程式密碼

---

## 📚 相關文件

- [Gmail 應用程式密碼說明](https://support.google.com/accounts/answer/185833)
- [Gmail SMTP 設定](https://support.google.com/mail/answer/7126229)
- [完整系統文檔](README.md)

---

**設定完成後，祝您使用愉快！** 📧✨
