// LSTM 预测结果
export interface LSTMPrediction {
    symbol: string;
    currentPrice: number;
    predictions: {
        day1: number;
        day3: number;
        day5: number;
    };
    scenarios?: {
        optimistic: number;
        neutral: number;
        pessimistic: number;
    };
    confidence: number;
    trend: 'up' | 'down' | 'neutral';
    indicators: {
        rsi: number;
        macd: number;
        ma5: number;
        ma20: number;
    };
    modelInfo: {
        name: string;
        accuracy: number;
        mse: number;
        mae: number;
        mape: number;
        trainedAt: string;
        dataRange?: string;
        version: string;
    };
    timestamp: string;
}

// 批量预测结果
export interface BatchPredictionResult {
    predictions: LSTMPrediction[];
    totalCount: number;
    successCount: number;
    failedSymbols: string[];
}

// 预测历史
export interface PredictionHistory {
    date: string;
    actual?: number;  // 实际价格
    predicted: number;  // 预测价格
    upperBound?: number;  // 上限
    lowerBound?: number;  // 下限
}

// LSTM 模型信息
export interface LSTMModel {
    symbol: string;
    modelPath: string;
    accuracy: number;
    mse: number;
    mae: number;
    mape: number;
    directionalAccuracy: number;
    trainedAt: string;
    trainingDataRange: {
        start: string;
        end: string;
    };
    hyperparameters: {
        lstmUnits: number[];
        dropout: number;
        batchSize: number;
        epochs: number;
        lookback: number;
    };
}
