/**
 * 股票代碼工具
 * 自動處理台灣上市/上櫃股票的代碼格式
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// 預設上櫃股票清單（會從後端動態更新）
let otcStocks: Set<string> = new Set([
    // 專家確認的上櫃股票
    '3363', '3163', '5438', '6163',
    // 常見上櫃股票
    '8021', '8110', '8046', '8155', '5475', '3706',
    '6257', '3231', '7610', '3030', '1605',
    '3057', '3062', '3064', '3092', '3115', '3144',
    '3188', '3217', '3224', '3242', '3252', '3265',
]);

// 已知上市股票清單
const twseStocks: Set<string> = new Set([
    // 台灣50成分股
    '2330', '2317', '2454', '2881', '2882', '2412', '2308', '3008',
    '2886', '2891', '2303', '1301', '1303', '2884', '2357', '2382',
    '2395', '3711', '5880', '2883', '2892', '2912', '2002', '1216',
    '2207', '2379', '2327', '3045', '2885', '6505',
    // 其他上市股票
    '2603', '2609', '2615', '2618', '3034', '2408', '2301', '2474',
    '6669', '3037', '2352', '2377', '2409', '3481', '2356', '3443',
    '1802', '2313', '2331', '2337', '2344', '2449', '3264', '5521',
]);

/**
 * 判斷股票市場類型
 */
export type MarketType = 'TWSE' | 'OTC' | 'EMERGING' | 'UNKNOWN';

export function getMarketType(code: string): MarketType {
    const cleanCode = code.replace(/\.(TW|TWO)$/i, '');

    if (otcStocks.has(cleanCode)) {
        return 'OTC';
    }

    if (twseStocks.has(cleanCode)) {
        return 'TWSE';
    }

    // 預設判斷（基於代碼特徵）
    const numCode = parseInt(cleanCode);

    // 8xxx 開頭通常是上櫃股
    if (cleanCode.startsWith('8') && cleanCode.length === 4) {
        return 'OTC';
    }

    // 3xxx 開頭有可能是上櫃
    if (cleanCode.startsWith('3') && cleanCode.length === 4 && numCode >= 3500) {
        return 'OTC';
    }

    // 6xxx 開頭可能是上櫃
    if (cleanCode.startsWith('6') && cleanCode.length === 4 && numCode >= 6100) {
        return 'OTC';
    }

    return 'UNKNOWN';
}

/**
 * 正規化股票代碼
 * 去除空格和非數字字符，並添加適當的市場後綴
 */
export function normalizeStockCode(code: string): string {
    // 去除空格和非數字字符
    const cleanCode = code.replace(/[^0-9]/g, '');

    // 如果是4位數，自動補上市場後綴
    if (cleanCode.length === 4) {
        const marketType = getMarketType(cleanCode);

        if (marketType === 'OTC') {
            return cleanCode + '.TWO';
        } else {
            return cleanCode + '.TW';
        }
    }

    return cleanCode;
}

/**
 * 獲取正確的 Yahoo Finance 代碼
 */
export function getYahooSymbol(code: string): string {
    const cleanCode = code.replace(/[^0-9]/g, '');

    if (cleanCode.length === 4) {
        const marketType = getMarketType(cleanCode);

        if (marketType === 'OTC') {
            return `${cleanCode}.TWO`;
        } else {
            return `${cleanCode}.TW`;
        }
    }

    return code;
}

/**
 * 從後端獲取最新的上櫃股票清單
 */
export async function fetchOtcStocksList(): Promise<string[]> {
    try {
        const response = await fetch(`${API_BASE}/api/stocks/otc-list`);
        if (response.ok) {
            const data = await response.json();
            if (data.stocks && Array.isArray(data.stocks)) {
                // 更新本地快取
                otcStocks = new Set(data.stocks);
                return data.stocks;
            }
        }
    } catch (error) {
        console.warn('無法從後端獲取上櫃股票清單，使用預設清單');
    }
    return Array.from(otcStocks);
}

/**
 * 手動添加上櫃股票到清單
 */
export function addOtcStock(code: string): void {
    const cleanCode = code.replace(/[^0-9]/g, '');
    if (cleanCode.length === 4) {
        otcStocks.add(cleanCode);
    }
}

/**
 * 驗證股票代碼格式
 */
export function isValidStockCode(code: string): boolean {
    const cleanCode = code.replace(/[^0-9]/g, '');
    return cleanCode.length === 4 && /^\d{4}$/.test(cleanCode);
}

/**
 * 格式化顯示用的股票代碼
 */
export function formatStockDisplay(code: string, name?: string): string {
    const cleanCode = code.replace(/\.(TW|TWO)$/i, '');
    if (name) {
        return `${cleanCode} ${name}`;
    }
    return cleanCode;
}

/**
 * 獲取市場類型的中文名稱
 */
export function getMarketTypeName(marketType: MarketType): string {
    switch (marketType) {
        case 'TWSE':
            return '上市';
        case 'OTC':
            return '上櫃';
        case 'EMERGING':
            return '興櫃';
        default:
            return '未知';
    }
}
