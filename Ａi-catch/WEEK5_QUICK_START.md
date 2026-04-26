# 🚀 Week 5 快速啟動指南

**當前狀態**: ✅ LSTM 系統 100% 完成  
**下一步**: Week 5 - Next.js 前端整合  
**預計時間**: 7 天

---

## ⚡ 立即開始（5分鐘）

### Step 1: 確認後端運行
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 檢查後端 API 是否運行（port 8000）
curl http://localhost:8000/health

# 如果未運行，啟動後端
./start_api_v3.sh
```

### Step 2: 初始化 Next.js 專案
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/frontend-v3

# 確認 Node.js 版本 (需要 18+)
node -v

# 初始化 Next.js（如果還沒有）
npx create-next-app@latest . --typescript --tailwind --app --use-npm

# 安裝核心依賴
npm install axios socket.io-client recharts lucide-react date-fns @tanstack/react-query zustand
```

### Step 3: 安裝 Shadcn/ui
```bash
# 初始化 Shadcn/ui
npx shadcn-ui@latest init

# 安裝常用組件
npx shadcn-ui@latest add card button table badge tabs toast chart dialog select
```

### Step 4: 啟動開發服務器
```bash
npm run dev
```

訪問: http://localhost:3000

---

## 📁 建議的文件創建順序

### Day 1: 基礎架構 ✅
```bash
# 1. 創建類型定義
touch src/types/stock.ts
touch src/types/lstm.ts
touch src/types/analysis.ts
touch src/types/alert.ts

# 2. 創建 API 客戶端
touch src/lib/api-client.ts
touch src/lib/websocket-client.ts
touch src/lib/utils.ts

# 3. 創建布局組件
mkdir -p src/components/layout
touch src/components/layout/Sidebar.tsx
touch src/components/layout/Header.tsx
touch src/components/layout/Footer.tsx
```

### Day 2-3: 頁面開發 ✅
```bash
# 4. 創建首頁
# 編輯 src/app/page.tsx

# 5. 創建 Dashboard 頁面
mkdir -p src/app/dashboard
touch src/app/dashboard/page.tsx
touch src/app/dashboard/layout.tsx

# 6. 創建 LSTM 頁面
mkdir -p src/app/dashboard/lstm
touch src/app/dashboard/lstm/page.tsx
```

### Day 4-5: 組件開發 ✅
```bash
# 7. 創建圖表組件
mkdir -p src/components/charts
touch src/components/charts/LSTMPredictionChart.tsx
touch src/components/charts/ExpertRadarChart.tsx
touch src/components/charts/PriceChart.tsx

# 8. 創建分析組件
mkdir -p src/components/analysis
touch src/components/analysis/MainForcePanel.tsx
touch src/components/analysis/ExpertSignalsPanel.tsx

# 9. 創建即時組件
mkdir -p src/components/realtime
touch src/components/realtime/RealtimeTicker.tsx
touch src/components/realtime/OrderBookPanel.tsx
```

---

## 🎯 今天的重點任務（Day 1）

### 任務 1: 環境配置 (15分鐘)
- [ ] 確認 Node.js 18+ 安裝
- [ ] 初始化 Next.js 專案
- [ ] 安裝所有依賴
- [ ] 確認開發服務器運行

### 任務 2: 創建基礎類型 (30分鐘)
**文件**: `src/types/lstm.ts`
```typescript
export interface LSTMPrediction {
  symbol: string;
  currentPrice: number;
  predictions: {
    day1: number;
    day3: number;
    day5: number;
  };
  confidence: number;
  trend: 'up' | 'down' | 'neutral';
  modelInfo: {
    accuracy: number;
    mse: number;
    trainedAt: string;
  };
}
```

**文件**: `src/types/stock.ts`
```typescript
export interface Stock {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  marketCap?: number;
  updatedAt: string;
}

export interface StockQuote extends Stock {
  high: number;
  low: number;
  open: number;
  close: number;
}
```

### 任務 3: 創建 API 客戶端 (45分鐘)
**文件**: `src/lib/api-client.ts`
```typescript
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// LSTM API
export const lstmApi = {
  predict: async (symbol: string) => {
    const response = await apiClient.get(`/api/lstm/predict/${symbol}`);
    return response.data;
  },
  
  batchPredict: async (symbols: string[]) => {
    const response = await apiClient.post('/api/lstm/batch-predict', { symbols });
    return response.data;
  },
};

// 主力偵測 API
export const mainForceApi = {
  analyze: async (symbol: string) => {
    const response = await apiClient.get(`/api/analysis/mainforce/${symbol}`);
    return response.data;
  },
  
  getSignals: async (symbol: string) => {
    const response = await apiClient.get(`/api/analysis/signals/${symbol}`);
    return response.data;
  },
};

// 即時數據 API
export const realtimeApi = {
  getQuote: async (symbol: string) => {
    const response = await apiClient.get(`/api/realtime/quote/${symbol}`);
    return response.data;
  },
};
```

### 任務 4: 創建基礎 Hook (30分鐘)
**文件**: `src/hooks/useLSTMPrediction.ts`
```typescript
import { useQuery } from '@tanstack/react-query';
import { lstmApi } from '@/lib/api-client';

export function useLSTMPrediction(symbol: string) {
  return useQuery({
    queryKey: ['lstm-prediction', symbol],
    queryFn: () => lstmApi.predict(symbol),
    staleTime: 5 * 60 * 1000, // 5分鐘
    enabled: !!symbol,
  });
}
```

---

## 🔧 環境配置文件

### `.env.local`
```bash
# API 配置
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# 功能開關
NEXT_PUBLIC_ENABLE_WEBSOCKET=true
NEXT_PUBLIC_ENABLE_LSTM=true
NEXT_PUBLIC_ENABLE_MAINFORCE=true
```

### `tsconfig.json` (確認路徑別名)
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

---

## 🎨 推薦的設計系統

### TailwindCSS 配置
```javascript
// tailwind.config.ts
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        success: '#10b981',
        danger: '#ef4444',
        warning: '#f59e0b',
      },
    },
  },
};
```

### 全局樣式
```css
/* src/app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    @apply h-full;
  }
  
  body {
    @apply h-full bg-gray-50 text-gray-900;
  }
}
```

---

## 📊 測試後端 API

### 快速測試腳本
```bash
# 測試 LSTM API
curl http://localhost:8000/api/lstm/predict/2330 | jq

# 測試主力偵測 API
curl http://localhost:8000/api/analysis/mainforce/2330 | jq

# 測試即時報價 API
curl http://localhost:8000/api/realtime/quote/2330 | jq

# 查看所有可用端點
curl http://localhost:8000/api/docs
```

---

## ✅ Day 1 檢查清單

完成以下項目後，Day 1 即完成：

- [ ] Next.js 專案初始化完成
- [ ] 所有依賴安裝成功
- [ ] Shadcn/ui 配置完成
- [ ] TypeScript 類型定義完成（stock, lstm, analysis）
- [ ] API 客戶端創建完成
- [ ] 至少 1 個 Hook 創建完成（useLSTMPrediction）
- [ ] 開發服務器正常運行
- [ ] 後端 API 測試通過

---

## 🚨 常見問題解決

### 問題 1: npm install 失敗
```bash
# 清除緩存重試
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

### 問題 2: TypeScript 報錯
```bash
# 確認 tsconfig.json 配置正確
# 重啟 VS Code TypeScript 服務器
# Cmd+Shift+P -> "TypeScript: Restart TS Server"
```

### 問題 3: API 連接失敗
```bash
# 檢查後端是否運行
curl http://localhost:8000/health

# 檢查 CORS 設置
# 確認後端允許 http://localhost:3000
```

---

## 📚 快速參考

### 常用命令
```bash
# 啟動開發服務器
npm run dev

# 構建生產版本
npm run build

# 運行生產服務器
npm run start

# 型別檢查
npm run type-check

# Lint 檢查
npm run lint
```

### 重要 URL
- 前端: http://localhost:3000
- 後端 API: http://localhost:8000
- API 文檔: http://localhost:8000/api/docs
- 現有盤前系統: http://localhost:8082

---

## 🎯 本週目標提醒

Week 5 結束時應達成：
- ✅ 完整的 Next.js 應用
- ✅ LSTM 預測可視化
- ✅ 主力偵測儀表板
- ✅ WebSocket 即時數據
- ✅ 響應式設計
- ✅ 可部署的版本

---

## 💡 開發建議

1. **小步前進**: 每完成一個組件就測試
2. **使用 React Query**: 簡化數據管理
3. **組件復用**: 盡量抽象通用組件
4. **類型安全**: 充分利用 TypeScript
5. **性能優化**: 使用 Next.js 的 Image、dynamic import

---

**現在就開始 Week 5 吧！** 🚀

從第一個命令開始：
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/frontend-v3
npm run dev
```

**加油！期待看到您打造的專業級前端！** 💪
