# 🎨 Week 5: Next.js 前端整合完整計劃

**開始日期**: 2025-12-17  
**預計時程**: 7 天  
**前置條件**: ✅ LSTM 系統 100% 完成 | ✅ 真實數據整合 100% 完成

---

## 🎯 Week 5 總體目標

將後端所有功能（LSTM 預測、主力偵測、即時數據、警報系統）整合到一個**現代化、專業級的 Next.js 14 前端**。

### 核心成果
- ✅ 完整的 Next.js 14 前端框架（App Router）
- ✅ 與後端 API 100% 整合
- ✅ 即時 WebSocket 數據流
- ✅ LSTM 預測可視化
- ✅ 主力偵測儀表板
- ✅ 響應式設計（桌面 + 移動端）
- ✅ 現代化 UI/UX（TailwindCSS + Shadcn/ui）

---

## 📋 前置檢查清單

### ✅ 已完成項目
- [x] LSTM 模型訓練完成（2330, 2454, 等）
- [x] LSTM API 端點完成（`/api/lstm/predict`）
- [x] 主力偵測 v3.0 完成（15位專家）
- [x] 100% 真實數據整合（富邦 + 證交所 + Yahoo Finance）
- [x] WebSocket 即時推送（富邦 5-level orderbook）
- [x] PostgreSQL 數據庫完成
- [x] FastAPI 後端運行中（port 8000）

### 📦 現有資源
- ✅ `backend-v3/` - FastAPI 後端
- ✅ `models/` - 訓練好的 LSTM 模型
- ✅ `frontend-v3/` - Next.js 骨架（需完善）
- ✅ 現有 Dashboard：盤前分析（port 8082）

---

## 🗓️ Day 1-2: Next.js 專案初始化與架構

### Day 1 上午：專案設置

#### 1. 初始化 Next.js 專案（如未完成）
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/frontend-v3

# 確認 Next.js 安裝
npx create-next-app@latest . --typescript --tailwind --app --use-npm

# 安裝核心依賴
npm install axios socket.io-client
npm install recharts lucide-react date-fns
npm install @tanstack/react-query zustand
npm install clsx tailwind-merge class-variance-authority
```

#### 2. 安裝 UI 組件庫（Shadcn/ui）
```bash
npx shadcn-ui@latest init

# 安裝常用組件
npx shadcn-ui@latest add card
npx shadcn-ui@latest add button
npx shadcn-ui@latest add table
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add toast  
npx shadcn-ui@latest add chart
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add select
```

### Day 1 下午：基礎架構

#### 創建項目結構
```
frontend-v3/
├── src/
│   ├── app/
│   │   ├── layout.tsx              # 根布局
│   │   ├── page.tsx                # 首頁
│   │   ├── dashboard/              # 儀表板
│   │   │   ├── page.tsx
│   │   │   ├── [symbol]/           # 個股詳情頁
│   │   │   │   └── page.tsx
│   │   │   ├── scanner/            # 選股掃描器
│   │   │   ├── alerts/             # 警報中心
│   │   │   └── lstm/               # LSTM 預測頁
│   │   │
│   │   └── api/                    # API 路由（可選）
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx         # 側邊欄導航
│   │   │   ├── Header.tsx          # 頂部欄
│   │   │   └── Footer.tsx
│   │   │
│   │   ├── charts/
│   │   │   ├── PriceChart.tsx      # 價格走勢圖
│   │   │   ├── VolumeChart.tsx     # 量能圖
│   │   │   ├── LSTMPredictionChart.tsx  # LSTM 預測圖
│   │   │   └── ExpertRadarChart.tsx     # 專家雷達圖
│   │   │
│   │   ├── analysis/
│   │   │   ├── MainForcePanel.tsx      # 主力面板
│   │   │   ├── ExpertSignalsPanel.tsx  # 15專家信號
│   │   │   ├── LSTMPredictionPanel.tsx # LSTM 預測面板
│   │   │   └── MarketSentiment.tsx     # 市場情緒
│   │   │
│   │   └── realtime/
│   │       ├── RealtimeTicker.tsx      # 即時股價
│   │       ├── OrderBookPanel.tsx      # 五檔掛單
│   │       └── AlertIndicator.tsx      # 警報提示
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts         # WebSocket Hook
│   │   ├── useRealtimeQuote.ts     # 即時報價
│   │   ├── useLSTMPrediction.ts    # LSTM 預測
│   │   └── useMainForce.ts         # 主力偵測
│   │
│   ├── lib/
│   │   ├── api-client.ts           # API 客戶端
│   │   ├── websocket-client.ts     # WebSocket 客戶端
│   │   └── utils.ts                # 工具函數
│   │
│   └── types/
│       ├── stock.ts                # 股票類型
│       ├── analysis.ts             # 分析類型
│       ├── lstm.ts                 # LSTM 類型
│       └── alert.ts                # 警報類型
│
├── public/
│   └── logo.svg
│
└── tailwind.config.ts
```

### Day 2：API 客戶端與類型定義

#### 1. 創建 TypeScript 類型定義
```typescript
// src/types/stock.ts
export interface Stock {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  updatedAt: string;
}

// src/types/lstm.ts
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
  indicators: {
    rsi: number;
    macd: number;
    ma5: number;
    ma20: number;
  };
}

// src/types/analysis.ts
export interface MainForceAnalysis {
  symbol: string;
  confidence: number;
  signals: ExpertSignal[];
  action: 'entry' | 'exit' | 'hold';
  timeframe: {
    daily: number;
    weekly: number;
    monthly: number;
  };
}

export interface ExpertSignal {
  name: string;
  score: number;
  weight: number;
  status: 'bullish' | 'bearish' | 'neutral';
}
```

#### 2. 創建 API 客戶端
```typescript
// src/lib/api-client.ts
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
  predict: (symbol: string) => 
    apiClient.get(`/api/lstm/predict/${symbol}`),
  
  batchPredict: (symbols: string[]) =>
    apiClient.post('/api/lstm/batch-predict', { symbols }),
};

// 主力偵測 API
export const mainForceApi = {
  analyze: (symbol: string) =>
    apiClient.get(`/api/analysis/mainforce/${symbol}`),
    
  getSignals: (symbol: string) =>
    apiClient.get(`/api/analysis/signals/${symbol}`),
};

// 即時數據 API
export const realtimeApi = {
  getQuote: (symbol: string) =>
    apiClient.get(`/api/realtime/quote/${symbol}`),
    
  getOrderBook: (symbol: string) =>
    apiClient.get(`/api/realtime/orderbook/${symbol}`),
};
```

---

## 🗓️ Day 3-4: 核心頁面開發

### Day 3 上午：首頁與整體布局

#### 1. 創建 Sidebar 導航
```tsx
// src/components/layout/Sidebar.tsx
import Link from 'next/link';
import { Home, TrendingUp, AlertCircle, Brain, Search } from 'lucide-react';

export function Sidebar() {
  return (
    <aside className="w-64 bg-gray-900 text-white h-screen fixed">
      <div className="p-6">
        <h1 className="text-2xl font-bold">AI 股票智能</h1>
      </div>
      
      <nav className="space-y-2 px-4">
        <NavItem href="/" icon={Home} label="首頁" />
        <NavItem href="/dashboard" icon={TrendingUp} label="儀表板" />
        <NavItem href="/dashboard/lstm" icon={Brain} label="LSTM 預測" />
        <NavItem href="/dashboard/scanner" icon={Search} label="選股掃描" />
        <NavItem href="/dashboard/alerts" icon={AlertCircle} label="警報中心" />
      </nav>
    </aside>
  );
}
```

#### 2. 創建首頁（概覽）
```tsx
// src/app/page.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, Brain, AlertCircle } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-4xl font-bold mb-8">AI 股票分析平台</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatsCard 
          title="LSTM 預測準確率"
          value="74.2%"
          icon={Brain}
          trend="+2.3%"
        />
        <StatsCard 
          title="主力偵測信號"
          value="12"
          icon={TrendingUp}
          trend="今日"
        />
        <StatsCard 
          title="活躍警報"
          value="3"
          icon={AlertCircle}
          trend="需關注"
        />
      </div>
      
      {/* 市場概覽 */}
      <MarketOverview />
      
      {/* 今日推薦 */}
      <TodayRecommendations />
    </div>
  );
}
```

### Day 3 下午：LSTM 預測頁面

#### LSTM 預測儀表板
```tsx
// src/app/dashboard/lstm/page.tsx
'use client';

import { useState } from 'react';
import { useLSTMPrediction } from '@/hooks/useLSTMPrediction';
import { LSTMPredictionChart } from '@/components/charts/LSTMPredictionChart';
import { Card } from '@/components/ui/card';

export default function LSTMPage() {
  const [symbol, setSymbol] = useState('2330');
  const { data: prediction, isLoading } = useLSTMPrediction(symbol);

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">LSTM 價格預測</h1>
      
      {/* 股票選擇器 */}
      <StockSelector value={symbol} onChange={setSymbol} />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {/* 預測圖表 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>{symbol} - 價格預測走勢</CardTitle>
          </CardHeader>
          <CardContent>
            <LSTMPredictionChart data={prediction} />
          </CardContent>
        </Card>
        
        {/* 預測數值 */}
        <PredictionNumbers prediction={prediction} />
        
        {/* 技術指標 */}
        <TechnicalIndicators indicators={prediction?.indicators} />
      </div>
      
      {/* 模型資訊 */}
      <ModelInfo modelStats={prediction?.modelInfo} />
    </div>
  );
}
```

### Day 4：主力偵測儀表板

#### 主力偵測頁面
```tsx
// src/app/dashboard/page.tsx
'use client';

import { useMainForce } from '@/hooks/useMainForce';
import { ExpertRadarChart } from '@/components/charts/ExpertRadarChart';
import { MainForcePanel } from '@/components/analysis/MainForcePanel';

export default function DashboardPage() {
  const { data: analysis } = useMainForce('2330');

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">主力偵測儀表板</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左側：15專家信號 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>15位專家信號</CardTitle>
          </CardHeader>
          <CardContent>
            <ExpertRadarChart signals={analysis?.signals} />
            <ExpertSignalsTable signals={analysis?.signals} />
          </CardContent>
        </Card>
        
        {/* 右側：主力分析面板 */}
        <MainForcePanel analysis={analysis} />
      </div>
      
      {/* 多時間框架分析 */}
      <MultiTimeframePanel timeframe={analysis?.timeframe} />
    </div>
  );
}
```

---

## 🗓️ Day 5: WebSocket 即時數據整合

### 上午：WebSocket 客戶端

#### 1. WebSocket Hook
```typescript
// src/hooks/useWebSocket.ts
import { useEffect, useState } from 'react';
import io from 'socket.io-client';

export function useWebSocket(url: string) {
  const [socket, setSocket] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const socketInstance = io(url, {
      transports: ['websocket'],
    });

    socketInstance.on('connect', () => {
      setIsConnected(true);
    });

    socketInstance.on('disconnect', () => {
      setIsConnected(false);
    });

    setSocket(socketInstance);

    return () => {
      socketInstance.disconnect();
    };
  }, [url]);

  return { socket, isConnected };
}
```

#### 2. 即時報價 Hook
```typescript
// src/hooks/useRealtimeQuote.ts
import { useEffect, useState } from 'react';
import { useWebSocket } from './useWebSocket';

export function useRealtimeQuote(symbol: string) {
  const { socket, isConnected } = useWebSocket('http://localhost:8000');
  const [quote, setQuote] = useState(null);

  useEffect(() => {
    if (!socket || !isConnected) return;

    // 訂閱股票報價
    socket.emit('subscribe_quote', { symbol });

    // 監聽報價更新
    socket.on('quote_update', (data: any) => {
      if (data.symbol === symbol) {
        setQuote(data);
      }
    });

    return () => {
      socket.emit('unsubscribe_quote', { symbol });
      socket.off('quote_update');
    };
  }, [socket, isConnected, symbol]);

  return { quote, isConnected };
}
```

### 下午：即時組件開發

#### RealtimeTicker 組件
```tsx
// src/components/realtime/RealtimeTicker.tsx
'use client';

import { useRealtimeQuote } from '@/hooks/useRealtimeQuote';
import { ArrowUp, ArrowDown } from 'lucide-react';

export function RealtimeTicker({ symbol }: { symbol: string }) {
  const { quote, isConnected } = useRealtimeQuote(symbol);

  if (!quote) return <div>加載中...</div>;

  return (
    <div className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
      <div>
        <div className="text-sm text-gray-500">{symbol}</div>
        <div className="text-2xl font-bold">{quote.price}</div>
      </div>
      
      <div className={quote.change >= 0 ? 'text-red-500' : 'text-green-500'}>
        {quote.change >= 0 ? <ArrowUp /> : <ArrowDown />}
        <span className="ml-1">{quote.changePercent}%</span>
      </div>
      
      {isConnected && (
        <div className="ml-auto">
          <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="ml-2 text-xs text-gray-500">即時</span>
        </div>
      )}
    </div>
  );
}
```

---

## 🗓️ Day 6: 圖表與數據可視化

### 上午：LSTM 預測圖表

```tsx
// src/components/charts/LSTMPredictionChart.tsx
'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export function LSTMPredictionChart({ data }: { data: any }) {
  const chartData = [
    // 歷史數據
    ...data.history.map((d: any) => ({
      date: d.date,
      actual: d.price,
      type: 'history',
    })),
    // 預測數據
    ...data.predictions.map((d: any) => ({
      date: d.date,
      predicted: d.price,
      upper: d.upperBound,
      lower: d.lowerBound,
      type: 'prediction',
    })),
  ];

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        
        {/* 實際價格線 */}
        <Line 
          type="monotone" 
          dataKey="actual" 
          stroke="#3b82f6" 
          strokeWidth={2}
          name="實際價格"
        />
        
        {/* 預測價格線 */}
        <Line 
          type="monotone" 
          dataKey="predicted" 
          stroke="#f59e0b" 
          strokeWidth={2}
          strokeDasharray="5 5"
          name="預測價格"
        />
        
        {/* 預測區間 */}
        <Line 
          type="monotone" 
          dataKey="upper" 
          stroke="#10b981" 
          strokeWidth={1}
          opacity={0.3}
          name="上限"
        />
        <Line 
          type="monotone" 
          dataKey="lower" 
          stroke="#ef4444" 
          strokeWidth={1}
          opacity={0.3}
          name="下限"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### 下午：專家雷達圖

```tsx
// src/components/charts/ExpertRadarChart.tsx
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts';

export function ExpertRadarChart({ signals }: { signals: any[] }) {
  const data = signals.map(s => ({
    name: s.name,
    score: s.score * 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <RadarChart data={data}>
        <PolarGrid />
        <PolarAngleAxis dataKey="name" />
        <PolarRadiusAxis angle={90} domain={[0, 100]} />
        <Radar 
          name="專家評分" 
          dataKey="score" 
          stroke="#8884d8" 
          fill="#8884d8" 
          fillOpacity={0.6} 
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
```

---

## 🗓️ Day 7: 優化、測試與部署

### 上午：性能優化

1. **代碼分割與懶加載**
```tsx
import dynamic from 'next/dynamic';

const LSTMPredictionChart = dynamic(
  () => import('@/components/charts/LSTMPredictionChart'),
  { ssr: false }
);
```

2. **React Query 數據緩存**
```tsx
// src/app/layout.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1分鐘
      cacheTime: 5 * 60 * 1000, // 5分鐘
    },
  },
});
```

3. **圖片優化**
```tsx
import Image from 'next/image';

<Image 
  src="/logo.svg" 
  alt="Logo" 
  width={200} 
  height={50}
  priority
/>
```

### 下午：測試與部署

#### 1. 運行開發服務器
```bash
cd frontend-v3
npm run dev
```

#### 2. 構建生產版本
```bash
npm run build
npm run start
```

#### 3. Docker 部署（可選）
```dockerfile
# frontend-v3/Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
```

---

## 📊 驗收標準

### 功能完整性
- [ ] 所有頁面正常訪問
- [ ] API 調用成功（LSTM、主力偵測、即時數據）
- [ ] WebSocket 即時更新正常
- [ ] 圖表正常渲染
- [ ] 響應式設計（桌面 + 移動端）

### 性能指標
- [ ] 首屏加載時間 < 2秒
- [ ] API 響應時間 < 500ms
- [ ] WebSocket 延遲 < 100ms
- [ ] Lighthouse 性能分數 > 90

### 用戶體驗
- [ ] UI 設計現代、專業
- [ ] 數據展示清晰易懂
- [ ] 交互流暢無卡頓
- [ ] 錯誤處理友好

---

## 🚀 關鍵 API 端點整合

### 1. LSTM 預測 API
```
GET /api/lstm/predict/{symbol}
Response:
{
  "symbol": "2330",
  "current_price": 1037.50,
  "predictions": {
    "day1": 1045.20,
    "day3": 1052.80,
    "day5": 1038.90
  },
  "confidence": 0.742,
  "trend": "up"
}
```

### 2. 主力偵測 API
```
GET /api/analysis/mainforce/{symbol}
Response:
{
  "symbol": "2330",
  "confidence": 0.857,
  "action": "entry",
  "signals": [
    {"name": "大單分析", "score": 0.92, "weight": 0.15},
    {"name": "籌碼集中度", "score": 0.85, "weight": 0.12},
    // ... 15位專家
  ]
}
```

### 3. 即時報價 WebSocket
```
// 訂閱
socket.emit('subscribe_quote', { symbol: '2330' })

// 接收
socket.on('quote_update', (data) => {
  // { symbol: '2330', price: 1037.50, change: 2.50, ... }
})
```

---

## 🎯 Week 5 成功標準

完成後應達成：
- ✅ 完整的 Next.js 14 前端應用
- ✅ 所有後端功能前端可視化
- ✅ 即時數據流整合
- ✅ 專業級 UI/UX
- ✅ 可部署的生產版本

---

## 📚 參考文檔

- Next.js 14 文檔: https://nextjs.org/docs
- Shadcn/ui: https://ui.shadcn.com
- Recharts: https://recharts.org
- Socket.IO: https://socket.io/docs/v4/client-api

---

## 🎊 下一步

完成 Week 5 後，進入：
- **Week 6**: 性能優化與進階功能
- **Week 7**: 系統整合測試
- **Week 8**: 生產環境部署

---

**準備好打造專業級前端了嗎？讓我們開始 Week 5！** 🚀

---

*創建日期: 2025-12-17*  
*預計完成: 2025-12-24*  
*狀態: Ready to Start*
