// 警报类型
export interface Alert {
    id: string;
    symbol: string;
    stockName: string;
    type: 'mainforce_entry' | 'mainforce_exit' | 'lstm_signal' | 'price_change' | 'volume_spike';
    level: 'low' | 'medium' | 'high' | 'critical';
    message: string;
    confidence: number;
    timestamp: string;
    isRead: boolean;
    metadata?: Record<string, any>;
}

// 警报规则
export interface AlertRule {
    id: string;
    name: string;
    enabled: boolean;
    conditions: AlertCondition[];
    notificationChannels: ('browser' | 'email' | 'line')[];
}

export interface AlertCondition {
    type: 'price_change' | 'volume_change' | 'mainforce_confidence' | 'lstm_prediction';
    operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte';
    value: number;
}

// 活跃警报
export interface ActiveAlert {
    alert: Alert;
    stock: {
        symbol: string;
        name: string;
        price: number;
        changePercent: number;
    };
    analysis?: {
        confidence: number;
        action: string;
    };
}
