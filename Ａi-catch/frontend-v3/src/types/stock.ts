// 股票基础类型
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

// 详细报价
export interface StockQuote extends Stock {
    high: number;
    low: number;
    open: number;
    close: number;
    previousClose: number;
}

// 五档掛单
export interface OrderBook {
    symbol: string;
    bids: OrderLevel[];  // 买盘
    asks: OrderLevel[];  // 卖盘
    timestamp: string;
}

export interface OrderLevel {
    price: number;
    volume: number;
    orders?: number;
}

// 技术指标
export interface TechnicalIndicators {
    rsi: number;
    macd: {
        macd: number;
        signal: number;
        histogram: number;
    };
    ma5: number;
    ma10: number;
    ma20: number;
    ma60: number;
    kd: {
        k: number;
        d: number;
    };
    volumeRatio: number;
}

// 股票列表项
export interface StockListItem {
    symbol: string;
    name: string;
    price: number;
    changePercent: number;
    volume: number;
    confidence?: number;  // 主力信心度
    lstmPrediction?: number;  // LSTM 预测
}
