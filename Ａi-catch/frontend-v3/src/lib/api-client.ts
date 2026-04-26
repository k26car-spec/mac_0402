import axios, { AxiosInstance, AxiosError } from 'axios';
import type { LSTMPrediction, BatchPredictionResult, LSTMModel } from '@/types/lstm';
import type { MainForceAnalysis, EntryCheckResult } from '@/types/analysis';
import type { StockQuote, OrderBook } from '@/types/stock';
import type { Alert } from '@/types/alert';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// 創建 axios 實例
export const apiClient: AxiosInstance = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000, // 增加到 30 秒，因為分析可能較慢
    headers: {
        'Content-Type': 'application/json',
    },
});

// 請求攔截器
apiClient.interceptors.request.use(
    (config) => config,
    (error) => Promise.reject(error)
);

// 響應攔截器
apiClient.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
    }
);

// ============ LSTM API ============
export const lstmApi = {
    /**
     * 獲取單支股票的 LSTM 預測
     */
    predict: async (symbol: string): Promise<LSTMPrediction> => {
        const response = await apiClient.get(`/api/lstm/predict/${symbol}`);
        return response.data;
    },

    /**
     * 批量獲取多支股票的 LSTM 預測
     */
    batchPredict: async (symbols: string[]): Promise<BatchPredictionResult> => {
        const response = await apiClient.post('/api/lstm/batch-predict', { symbols });
        return response.data;
    },

    /**
     * 獲取所有已訓練的模型列表
     */
    getModels: async (): Promise<LSTMModel[]> => {
        const response = await apiClient.get('/api/lstm/models');
        // API 返回 { total_models: N, models: [...] }，需提取 models 陣列
        if (response.data && Array.isArray(response.data.models)) {
            return response.data.models;
        }
        // 相容舊格式或直接返回陣列的情況
        if (Array.isArray(response.data)) {
            return response.data;
        }
        return [];
    },

    /**
     * 重新訓練指定股票的模型
     */
    retrain: async (symbol: string): Promise<{ message: string }> => {
        const response = await apiClient.post(`/api/lstm/retrain/${symbol}`);
        return response.data;
    },
};

// ============ 主力分析 API ============
export const mainForceApi = {
    /**
     * 獲取主力分析結果
     */
    analyze: async (symbol: string): Promise<MainForceAnalysis> => {
        const response = await apiClient.get(`/api/analysis/mainforce/${symbol}`);
        return response.data;
    },

    /**
     * 獲取專家信號
     */
    getSignals: async (symbol: string) => {
        const response = await apiClient.get(`/api/analysis/signals/${symbol}`);
        return response.data;
    },

    /**
     * 獲取多時間框架分析
     */
    getTimeframeAnalysis: async (symbol: string) => {
        const response = await apiClient.get(`/api/analysis/timeframe/${symbol}`);
        return response.data;
    },
};

// ============ 實時數據 API ============
export const realtimeApi = {
    /**
     * 獲取實時報價
     */
    getQuote: async (symbol: string): Promise<StockQuote> => {
        const response = await apiClient.get(`/api/realtime/quote/${symbol}`);
        return response.data;
    },

    /**
     * 獲取五檔掛單
     */
    getOrderBook: async (symbol: string): Promise<OrderBook> => {
        const response = await apiClient.get(`/api/realtime/orderbook/${symbol}`);
        return response.data;
    },

    /**
     * 批量獲取報價
     */
    getBatchQuotes: async (symbols: string[]): Promise<StockQuote[]> => {
        const response = await apiClient.post('/api/realtime/batch-quotes', { symbols });
        return response.data;
    },
};

// ============ 股票列表 API ============
export const stocksApi = {
    /**
     * 獲取所有股票列表
     */
    getList: async () => {
        const response = await apiClient.get('/api/stocks/list');
        return response.data;
    },

    /**
     * 搜尋股票
     */
    search: async (query: string) => {
        const response = await apiClient.get(`/api/stocks/search?q=${query}`);
        return response.data;
    },

    /**
     * 獲取股票詳情
     */
    getInfo: async (symbol: string) => {
        const response = await apiClient.get(`/api/stocks/${symbol}`);
        return response.data;
    },
};

// ============ 警報 API ============
export const alertsApi = {
    /**
     * 獲取活躍警報
     */
    getActive: async (): Promise<Alert[]> => {
        const response = await apiClient.get('/api/alerts/active');
        return response.data;
    },

    /**
     * 獲取歷史警報
     */
    getHistory: async (limit = 100): Promise<Alert[]> => {
        const response = await apiClient.get(`/api/alerts/history?limit=${limit}`);
        return response.data;
    },

    /**
     * 標記警報為已讀
     */
    markAsRead: async (alertId: string): Promise<void> => {
        await apiClient.post(`/api/alerts/${alertId}/read`);
    },

    /**
     * 刪除警報
     */
    delete: async (alertId: string): Promise<void> => {
        await apiClient.delete(`/api/alerts/${alertId}`);
    },
};

// ============ 進場檢查 API ============
export const entryCheckApi = {
    /**
     * 獲取股票進場檢查分析 (包含增強型低點分析)
     */
    quickCheck: async (symbol: string): Promise<EntryCheckResult> => {
        const response = await apiClient.get(`/api/entry-check/quick/${symbol}`);
        return response.data;
    },

    /**
     * 獲取完整進場分析報告
     */
    comprehensive: async (symbol: string): Promise<EntryCheckResult> => {
        const response = await apiClient.get(`/api/entry-check/comprehensive/${symbol}`);
        return response.data;
    }
};

// ============ 健康檢查 API ============
export const healthApi = {
    /**
     * 檢查後端健康狀態
     */
    check: async () => {
        const response = await apiClient.get('/health');
        return response.data;
    },
};

export default apiClient;
