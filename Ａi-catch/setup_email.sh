#!/bin/bash
# setup_email.sh - Email 通知設定助手

echo "📧 Email 通知設定助手"
echo "====================="
echo ""

# 檢查 .env 檔案
if [ ! -f ".env" ]; then
    echo "📝 建立 .env 檔案..."
    cp .env.example .env
    echo "✓ .env 檔案已建立"
    echo ""
fi

echo "請依照以下步驟設定 Gmail Email 通知:"
echo ""
echo "📌 步驟 1: 取得 Gmail 應用程式密碼"
echo "-----------------------------------"
echo "1. 前往: https://myaccount.google.com/security"
echo "2. 啟用「兩步驟驗證」"
echo "3. 在「應用程式密碼」中產生新密碼"
echo "4. 選擇「郵件」和「其他裝置」"
echo "5. 複製 16 位元密碼 (例如: abcd efgh ijkl mnop)"
echo ""

read -p "請輸入您的 Gmail 地址: " email_user
read -sp "請輸入應用程式密碼 (16位元): " email_pass
echo ""
echo ""

# 移除空格
email_pass_clean=$(echo "$email_pass" | tr -d ' ')

# 更新 .env 檔案
if grep -q "EMAIL_USERNAME=" .env; then
    sed -i.bak "s|EMAIL_USERNAME=.*|EMAIL_USERNAME=$email_user|" .env
    sed -i.bak "s|EMAIL_PASSWORD=.*|EMAIL_PASSWORD=$email_pass_clean|" .env
else
    echo "EMAIL_USERNAME=$email_user" >> .env
    echo "EMAIL_PASSWORD=$email_pass_clean" >> .env
fi

echo "✓ 環境變數已設定"
echo ""

# 詢問是否更新 config.yaml
read -p "是否要自動更新 config.yaml 啟用 Email 通知? (y/n): " update_config

if [ "$update_config" = "y" ] || [ "$update_config" = "Y" ]; then
    # 備份 config.yaml
    cp config.yaml config.yaml.bak
    
    # 使用 Python 更新 YAML (更安全)
    python3 << EOF
import yaml

with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 啟用 Email 通知
config['notifications']['email']['enabled'] = True
config['notifications']['email']['recipients'] = ['$email_user']

with open('config.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

print("✓ config.yaml 已更新 (備份: config.yaml.bak)")
EOF
fi

echo ""
echo "📧 Email 設定完成！"
echo ""
echo "🧪 測試設定:"
echo "   export EMAIL_USERNAME='$email_user'"
echo "   export EMAIL_PASSWORD='$email_pass_clean'"
echo "   python3 test_email.py"
echo ""
echo "🚀 或直接啟動系統:"
echo "   ./start_monitor.sh"
echo ""
