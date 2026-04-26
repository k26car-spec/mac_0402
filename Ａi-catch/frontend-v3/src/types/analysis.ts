// 专家信号
export interface ExpertSignal {
    name: string;
    score: number;
    weight: number;
    status: 'bullish' | 'bearish' | 'neutral';
    evidence: string[];
    confidence: number;
}

// 主力分析结果
export interface MainForceAnalysis {
    symbol: string;
    confidence: number;
    signals: ExpertSignal[];
    action: 'entry' | 'exit' | 'hold';
    actionReason: string;
    timeframe: {
        daily: number;
        weekly: number;
        monthly: number;
    };
    riskLevel: 'low' | 'medium' | 'high';
    recommendation: string;
    timestamp: string;
}

// 15位专家列表
export const EXPERT_NAMES = [
    '大单分析',
    '籌碼集中度',
    '量能爆發',
    '連續買賣',
    '時段動量',
    '換手率',
    '成本估算',
    '法人動向',
    '資金流向',
    '相對強弱',
    '型態識別',
    '量價背離',
    '突破專家',
    '籌碼穩定',
    '趨勢強度',
] as const;

export type ExpertName = typeof EXPERT_NAMES[number];

// 多时间框架分析
export interface TimeframeAnalysis {
    timeframe: 'daily' | 'weekly' | 'monthly';
    confidence: number;
    trend: 'bullish' | 'bearish' | 'neutral';
    strength: number;
    signals: ExpertSignal[];
}

// 主力动作
export interface MainForceAction {
    type: 'large_buy' | 'large_sell' | 'accumulation' | 'distribution';
    timestamp: string;
    volume: number;
    price: number;
    confidence: number;
    description: string;
}

// 增強型低點分析 (Buy on Dip)
export interface DipAnalysis {
    quality: string;
    score: number;
    confidence: number;
    reasons: string[];
    warnings: string[];
    passed: boolean;
}

// 進場檢查結果
export interface EntryCheckResult {
    symbol: string;
    entry_price: number;
    should_enter: boolean;
    confidence: number;
    recommended_action: string;
    reason: string;
    status?: string;
    checks: {
        smart_score?: any;
        technical?: any;
        institutional?: any;
        support_resistance?: any;
        lessons?: any;
        risk?: any;
        dip_analysis?: DipAnalysis;
    };
    blockers?: string[];
}
