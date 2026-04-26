import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { mainForceApi } from '@/lib/api-client';
import type { MainForceAnalysis } from '@/types/analysis';

/**
 * Hook for fetching main force analysis for a single stock
 */
export function useMainForceAnalysis(symbol: string, enabled = true): UseQueryResult<MainForceAnalysis, Error> {
    return useQuery({
        queryKey: ['mainforce-analysis', symbol],
        queryFn: () => mainForceApi.analyze(symbol),
        enabled: enabled && !!symbol,
        staleTime: 3 * 60 * 1000, // 3分鐘
        cacheTime: 10 * 60 * 1000, // 10分鐘
    });
}

/**
 * Hook for fetching expert signals
 */
export function useExpertSignals(symbol: string, enabled = true) {
    return useQuery({
        queryKey: ['expert-signals', symbol],
        queryFn: () => mainForceApi.getSignals(symbol),
        enabled: enabled && !!symbol,
        staleTime: 3 * 60 * 1000,
    });
}

/**
 * Hook for fetching timeframe analysis
 */
export function useTimeframeAnalysis(symbol: string, enabled = true) {
    return useQuery({
        queryKey: ['timeframe-analysis', symbol],
        queryFn: () => mainForceApi.getTimeframeAnalysis(symbol),
        enabled: enabled && !!symbol,
        staleTime: 5 * 60 * 1000,
    });
}
