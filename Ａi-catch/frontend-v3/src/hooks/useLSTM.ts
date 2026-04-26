import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { lstmApi } from '@/lib/api-client';
import type { LSTMPrediction } from '@/types/lstm';

/**
 * Hook for fetching LSTM prediction for a single stock
 */
export function useLSTMPrediction(symbol: string, enabled = true): UseQueryResult<LSTMPrediction, Error> {
    return useQuery({
        queryKey: ['lstm-prediction', symbol],
        queryFn: () => lstmApi.predict(symbol),
        enabled: enabled && !!symbol,
        staleTime: 5 * 60 * 1000, // 5分钟
        cacheTime: 10 * 60 * 1000, // 10分钟
    });
}

/**
 * Hook for fetching LSTM predictions for multiple stocks
 */
export function useBatchLSTMPredictions(symbols: string[], enabled = true) {
    return useQuery({
        queryKey: ['lstm-batch-predictions', symbols.join(',')],
        queryFn: () => lstmApi.batchPredict(symbols),
        enabled: enabled && symbols.length > 0,
        staleTime: 5 * 60 * 1000,
    });
}

/**
 * Hook for fetching all LSTM models
 */
export function useLSTMModels(enabled = true) {
    return useQuery({
        queryKey: ['lstm-models'],
        queryFn: () => lstmApi.getModels(),
        enabled,
        staleTime: 60 * 60 * 1000, // 1小时
    });
}
