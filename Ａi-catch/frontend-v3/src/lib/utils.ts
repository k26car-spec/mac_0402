import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * 合并 Tailwind CSS 类名
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

/**
 * 格式化数字为百分比
 */
export function formatPercentage(value: number, decimals = 2): string {
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

/**
 * 格式化价格
 */
export function formatPrice(price: number, decimals = 2): string {
    return price.toFixed(decimals);
}

/**
 * 格式化大数字（K, M, B）
 */
export function formatLargeNumber(num: number): string {
    if (num >= 1e9) {
        return `${(num / 1e9).toFixed(1)}B`;
    }
    if (num >= 1e6) {
        return `${(num / 1e6).toFixed(1)}M`;
    }
    if (num >= 1e3) {
        return `${(num / 1e3).toFixed(1)}K`;
    }
    return num.toString();
}

/**
 * 格式化时间距离现在
 */
export function formatTimeAgo(timestamp: string): string {
    const now = new Date();
    const past = new Date(timestamp);
    const diffMs = now.getTime() - past.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return `${diffSecs}秒前`;
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays < 7) return `${diffDays}天前`;

    return past.toLocaleDateString('zh-TW');
}

/**
 * 根据涨跌获取颜色类名（台股）
 */
export function getChangeColor(change: number): string {
    if (change > 0) return 'text-rise';  // 红色（涨）
    if (change < 0) return 'text-fall';  // 绿色（跌）
    return 'text-gray-500';
}

/**
 * 根据涨跌获取背景颜色类名
 */
export function getChangeBgColor(change: number): string {
    if (change > 0) return 'bg-rise/10';
    if (change < 0) return 'bg-fall/10';
    return 'bg-gray-100';
}

/**
 * 获取信心度颜色
 */
export function getConfidenceColor(confidence: number): string {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-blue-600';
    if (confidence >= 0.4) return 'text-yellow-600';
    return 'text-red-600';
}

/**
 * 获取趋势箭头图标
 */
export function getTrendIcon(trend: 'up' | 'down' | 'neutral'): string {
    switch (trend) {
        case 'up': return '↑';
        case 'down': return '↓';
        case 'neutral': return '→';
    }
}

/**
 * 获取风险等级颜色
 */
export function getRiskLevelColor(level: 'low' | 'medium' | 'high'): string {
    switch (level) {
        case 'low': return 'text-green-600 bg-green-50';
        case 'medium': return 'text-yellow-600 bg-yellow-50';
        case 'high': return 'text-red-600 bg-red-50';
    }
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => any>(
    func: T,
    wait: number
): (...args: Parameters<T>) => void {
    let timeout: NodeJS.Timeout | null = null;

    return function executedFunction(...args: Parameters<T>) {
        const later = () => {
            timeout = null;
            func(...args);
        };

        if (timeout) clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: any[]) => any>(
    func: T,
    limit: number
): (...args: Parameters<T>) => void {
    let inThrottle: boolean;

    return function executedFunction(...args: Parameters<T>) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => (inThrottle = false), limit);
        }
    };
}

/**
 * 深度克隆对象
 */
export function deepClone<T>(obj: T): T {
    return JSON.parse(JSON.stringify(obj));
}

/**
 * 睡眠函数
 */
export function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}
