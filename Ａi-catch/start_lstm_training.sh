#!/bin/bash
#
# LSTM Smart Entry v2.0 訓練啟動腳本
# 快速啟動 LSTM 訓練系統
#
# 使用方式: ./start_lstm_training.sh
#

echo "============================================================"
echo "🤖 LSTM Smart Entry v2.0 - 深度學習訓練系統"
echo "============================================================"
echo ""

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 設定根目錄
ROOT_DIR="/Users/Mac/Documents/ETF/AI/Ａi-catch"
cd "$ROOT_DIR" || exit 1

# ===== 1. 檢查 Python 環境 =====
echo -e "${BLUE}📦 檢查 Python 環境...${NC}"

if ! command -v python3 &> /dev/null
then
    echo -e "${RED}❌ Python3 未安裝${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"

# ===== 2. 檢查必要套件 =====
echo ""
echo -e "${BLUE}📦 檢查必要套件...${NC}"

# 檢查 TensorFlow
if python3 -c "import tensorflow" 2>/dev/null; then
    TF_VERSION=$(python3 -c "import tensorflow as tf; print(tf.__version__)")
    echo -e "${GREEN}✅ TensorFlow $TF_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️  TensorFlow 未安裝${NC}"
    echo -e "${BLUE}正在安裝 TensorFlow...${NC}"
    pip3 install tensorflow -q
fi

# 檢查其他套件
REQUIRED_PACKAGES=("numpy" "pandas" "matplotlib" "sklearn" "yfinance")

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        echo -e "${GREEN}✅ $package${NC}"
    else
        echo -e "${YELLOW}⚠️  $package 未安裝，正在安裝...${NC}"
        pip3 install $package -q
    fi
done

# ===== 3. 檢查 ORB 監控列表 =====
echo ""
echo -e "${BLUE}📋 檢查 ORB 監控列表...${NC}"

WATCHLIST_FILE="$ROOT_DIR/data/orb_watchlist.json"

if [ -f "$WATCHLIST_FILE" ]; then
    STOCK_COUNT=$(python3 -c "import json; f=open('$WATCHLIST_FILE'); d=json.load(f); print(len(d['watchlist']))")
    echo -e "${GREEN}✅ 監控列表已載入: $STOCK_COUNT 支股票${NC}"
    
    # 顯示前 10 支
    echo -e "${BLUE}前 10 支股票:${NC}"
    python3 -c "import json; f=open('$WATCHLIST_FILE'); d=json.load(f); print(', '.join(d['watchlist'][:10]))"
else
    echo -e "${RED}❌ 監控列表文件不存在: $WATCHLIST_FILE${NC}"
    exit 1
fi

# ===== 4. 創建輸出目錄 =====
echo ""
echo -e "${BLUE}📁 創建輸出目錄...${NC}"

mkdir -p "$ROOT_DIR/models/lstm_smart_entry"
mkdir -p "$ROOT_DIR/training_results"

echo -e "${GREEN}✅ 目錄已準備${NC}"
echo "   • 模型保存: $ROOT_DIR/models/lstm_smart_entry"
echo "   • 圖表保存: $ROOT_DIR/training_results"

# ===== 5. 顯示訓練配置 =====
echo ""
echo -e "${BLUE}⚙️  訓練配置:${NC}"
echo "   • 訓練輪數: 500 epochs"
echo "   • 批次大小: 32"
echo "   • 學習率: 0.001"
echo "   • 優化器: Adam (自適應學習率)"
echo "   • 損失函數: MSE (均方誤差)"
echo "   • LSTM 架構: 128 → 64 → 32 units"
echo "   • Dropout: 0.3"
echo "   • 回看天數: 60 天"
echo "   • 預測天數: 5 天"

# ===== 6. 確認開始訓練 =====
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}⚠️  注意事項:${NC}"
echo "   1. 訓練時間: 每支股票約 3-5 分鐘"
echo "   2. 總計時間: 約 2.5-4 小時 (50支股票)"
echo "   3. 網路連線: 需要下載歷史數據"
echo "   4. 記憶體: 建議至少 4GB 可用"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

read -p "是否開始訓練? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${YELLOW}訓練已取消${NC}"
    exit 0
fi

# ===== 7. 開始訓練 =====
echo ""
echo -e "${GREEN}🚀 開始訓練...${NC}"
echo ""

python3 "$ROOT_DIR/train_lstm_smart_entry_v2.py"

TRAIN_EXIT_CODE=$?

# ===== 8. 訓練完成 =====
echo ""
if [ $TRAIN_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}🎉 訓練完成！${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    echo -e "${BLUE}📊 查看結果:${NC}"
    echo "   • 訓練曲線: ls -lht $ROOT_DIR/training_results/*.png | head -2"
    echo "   • 訓練報告: ls -lht $ROOT_DIR/models/lstm_smart_entry/*.json | head -1"
    echo "   • 模型文件: ls $ROOT_DIR/models/lstm_smart_entry/*.h5 | wc -l"
    echo ""
    echo -e "${BLUE}📈 打開圖表:${NC}"
    echo "   open $ROOT_DIR/training_results/"
    echo ""
else
    echo -e "${RED}❌ 訓練過程中發生錯誤${NC}"
    echo -e "${YELLOW}請查看上方錯誤訊息${NC}"
    exit 1
fi

# ===== 9. 顯示統計 =====
MODEL_COUNT=$(ls -1 "$ROOT_DIR/models/lstm_smart_entry"/*.h5 2>/dev/null | wc -l)
echo -e "${GREEN}✅ 成功訓練 $MODEL_COUNT 個模型${NC}"

# 自動打開結果目錄
echo ""
read -p "是否打開結果目錄? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    open "$ROOT_DIR/training_results"
fi

echo ""
echo -e "${GREEN}🎊 所有任務完成！${NC}"
echo ""
