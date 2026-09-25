import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
    Activity, TrendingUp, TrendingDown, Zap, Shield, Crosshair,
    Wifi, BarChart2, AlertTriangle, Cpu, Layers, Globe,
    Anchor, Target, Clock, CheckCircle2, XCircle, AlertOctagon,
    PlayCircle, Timer, Gauge, ArrowUpRight, ArrowDownRight,
    Flame, Eye, Info, Search, ChevronDown, ChevronUp, RefreshCw, Loader2,
    WifiOff, Users, ArrowRightLeft, TrendingDown as TrendDownIcon, Database,
    Briefcase, Wallet, History, X
} from 'lucide-react';
import StrategySummary from './components/StrategySummary';
import MOPSPanel, { KGISection } from './components/MOPSPanel';
import VixFearPanel from './components/VixFearPanel';
import MacroPanel from './components/MacroPanel';
import EpsEvaluationPanel from './components/EpsEvaluationPanel';


const API_BASE = typeof window !== 'undefined' ? `http://${window.location.hostname}:8000` : 'http://localhost:8000';

const ExpertSniper = () => {
    const [time, setTime] = useState(new Date());
    const [blink, setBlink] = useState(true);

    // --- 核心狀態 ---
    const [symbol, setSymbol] = useState('');
    const [inputSymbol, setInputSymbol] = useState('');
    const [stockName, setStockName] = useState('');
    const [showPortfolio, setShowPortfolio] = useState(false); // New state for Portfolio Modal
    const [loading, setLoading] = useState(false);
    const [isMonitoring, setIsMonitoring] = useState(false);
    const [connected, setConnected] = useState(false);
    const [tech5m, setTech5m] = useState(null);
    const [techLoading, setTechLoading] = useState(false);
    const [error5m, setError5m] = useState(null);

    // 1. 5分K 高點結構狀態
    const [highPoints, setHighPoints] = useState([
        { id: 'H1', price: 0, time: '--:--', status: 'fail' },
        { id: 'H2', price: 0, time: '--:--', status: 'fail' },
        { id: 'H3', price: 0, time: '--:--', status: 'fail' }
    ]);

    // 2. KD 進階狀態
    const [kd, setKd] = useState({ k: 0, d: 0, history: [] });

    // 3. 大盤數據
    const [marketIndices, setMarketIndices] = useState({
        tseValue: "---", tseChange: "0.00", tsePercent: "0.00%", isTseUp: false,
        otaValue: "---", otaChange: "0.00", otaPercent: "0.00%", isOtaUp: false,
        elecValue: "---", elecPercent: "0.00%",
        finValue: "---", finPercent: "0.00%",
        foreignNet: 0, trustNet: 0,
        sp500: "0.00%", nikkei: "0.00%", usdtwd: "---", usdtwdChange: "0.00%",
        marketSummary: "等待大盤數據...",
        aiRecommendation: "---"
    });

    // 4. 個股即時數據
    const [priceData, setPriceData] = useState({
        price: 0, changePercent: 0, open: 0, high: 0, low: 0, volume: 0,
        vwap: 0, support: 0, resistance: 0, prevClose: 0, rs: 0,
        buyPower: 50, sellPower: 50,
        foreignNet: 0, trustNet: 0, dealerNet: 0,
        bigMoneyFlow: '---',
        avgVolume5d: 0,
        institutionalCost: 0,
        concentration: 0,
        dataSource: '等待獲取...',
        orderBook: {
            bids: [],
            asks: []
        },
        institutionalHistory: {
            foreign: { d1: 0, d5: 0, d10: 0 },
            trust: { d1: 0, d5: 0, d10: 0 },
            dealer: { d1: 0, d5: 0, d10: 0 },
            total: { d1: 0, d5: 0, d10: 0 }
        }
    });

    // 🆕 新增：策略摘要所需狀態
    const [levels, setLevels] = useState([]);
    const [orbData, setOrbData] = useState({ high: 0, low: 0 });
    const [prevDayData, setPrevDayData] = useState({ high: 0, low: 0 });

    // 🌐 VIX 恐慌指數資料（統一在父層 fetch，供 VixFearPanel + StrategySummary 共用）
    const [vixData, setVixData] = useState(null);
    useEffect(() => {
        const load = async () => {
            try {
                const res  = await fetch(`${API_BASE}/api/market/vix`);
                const json = await res.json();
                if (json.success) setVixData(json);
            } catch {}
        };
        load();
        const t = setInterval(load, 5 * 60 * 1000); // 每 5 分鐘更新
        return () => clearInterval(t);
    }, []);

    // --- 數據獲取邏輯 ---
    const fetchTech5m = useCallback(async (stockCode) => {
        if (!stockCode) return;

        try {
            // ✅ 添加超時控制 - 5秒沒響應就放棄
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const res = await fetch(
                `${API_BASE}/api/stock-analysis/technical/5m/${stockCode}`,
                { signal: controller.signal }
            );
            clearTimeout(timeoutId);

            const data = await res.json();
            if (data?.success && data.data) {
                setTech5m(data.data);
                console.log(`✅ 5分K更新成功: ${new Date().toLocaleTimeString()}`);
            }
        } catch (e) {
            if (e.name === 'AbortError') {
                console.warn('⏱️ 5分K請求超時，保持舊數據');
            } else {
                console.error("❌ 5分K獲取失敗:", e);
            }
            // 失敗也不清空，保持舊數據
        }
        finally { setTechLoading(false); }
    }, []);

    // 🆕 法人籌碼獨立快速獲取（直接打 /institutional API，不等 comprehensive）
    const fetchInstitutional = useCallback(async (stockCode) => {
        if (!stockCode) return;
        try {
            const res = await fetch(
                `${API_BASE}/api/stock-analysis/institutional/${stockCode}?days=35`,
                { signal: AbortSignal.timeout(8000) }
            );
            const data = await res.json();
            if (data?.status === 'success' && data?.history?.length > 0) {
                // 從歷史記錄重建 d1/d5/d10 累積數據 (使用 shares 以確保精確度)
                const buildNet = (sharesKey, days) => {
                    const totalShares = data.history.slice(0, days).reduce((sum, d) => sum + (d[sharesKey] || 0), 0);
                    return Math.trunc(totalShares / 1000);
                };

                const institutionalHistory = {
                    foreign: { d1: buildNet('foreign_shares', 1), d5: buildNet('foreign_shares', 5), d10: buildNet('foreign_shares', 10), d20: buildNet('foreign_shares', 20) },
                    trust: { d1: buildNet('investment_shares', 1), d5: buildNet('investment_shares', 5), d10: buildNet('investment_shares', 10), d20: buildNet('investment_shares', 20) },
                    dealer: { d1: buildNet('dealer_shares', 1), d5: buildNet('dealer_shares', 5), d10: buildNet('dealer_shares', 10), d20: buildNet('dealer_shares', 20) },
                    total: { 
                        d1: buildNet('foreign_shares', 1) + buildNet('investment_shares', 1) + buildNet('dealer_shares', 1),
                        d5: buildNet('foreign_shares', 5) + buildNet('investment_shares', 5) + buildNet('dealer_shares', 5),
                        d10: buildNet('foreign_shares', 10) + buildNet('investment_shares', 10) + buildNet('dealer_shares', 10),
                        d20: buildNet('foreign_shares', 20) + buildNet('investment_shares', 20) + buildNet('dealer_shares', 20)
                    }
                };
                setPriceData(prev => ({
                    ...prev,
                    institutionalHistory
                }));
                console.log(`✅ 法人籌碼更新成功 ${stockCode}: 外資 ${institutionalHistory.foreign.d1}`);
            }
        } catch (e) {
            console.warn('⚠️ 法人籌碼獲取失敗:', e?.message || e);
        }
    }, []);


    // 🆕 局部高點偵測 (Fractal Detection) - 偵測 H1/H2/H3 結構
    // 參考專業演算法：真正的結構高點需要經過「時間確認」，比前後各 lookback 根 K 棒都高才算數
    useEffect(() => {
        if (!tech5m?.history || tech5m.history.length < 5) return;

        const klines = tech5m.history;
        const lookback = 1; // 向前向後比較的根數（改為 1 以適應快速行情）
        const maxHighs = 3; // 保留最近 3 個高點
        const detectedHighs = [];

        // 局部高點偵測：從第 lookback 根開始，到倒數第 lookback 根結束
        for (let i = lookback; i < klines.length - lookback; i++) {
            const current = klines[i];
            let isHighPoint = true;

            // 向前比較 lookback 根
            for (let j = 1; j <= lookback; j++) {
                if (current.high <= klines[i - j].high) {
                    isHighPoint = false;
                    break;
                }
            }

            // 向後比較 lookback 根（只有在向前比較通過時才需要）
            if (isHighPoint) {
                for (let j = 1; j <= lookback; j++) {
                    if (current.high <= klines[i + j].high) {
                        isHighPoint = false;
                        break;
                    }
                }
            }

            // 如果是高點，加入陣列
            if (isHighPoint) {
                const rawTime = current.date || current.time || '';
                const displayTime = rawTime.includes('T') ? rawTime.split('T')[1].substring(0, 5) : rawTime;

                detectedHighs.push({
                    price: current.high,
                    time: displayTime,
                    index: i
                });
            }
        }

        // 如果沒有偵測到結構高點（例如連續上漲），使用最高的3個K線高點作為替代
        if (detectedHighs.length === 0 && klines.length >= 3) {
            const sortedByHigh = [...klines]
                .map((k, idx) => ({
                    price: k.high,
                    time: (k.date || k.time || '').includes('T') ? (k.date || k.time).split('T')[1].substring(0, 5) : '--:--',
                    index: idx
                }))
                .sort((a, b) => b.price - a.price).slice(0, maxHighs);

            detectedHighs.push(...sortedByHigh);
        }

        if (detectedHighs.length > 0) {
            // 取最近 maxHighs 個局部高點
            const recentHighs = detectedHighs.slice(-maxHighs);

            // 加上標籤 (H1, H2, H3...)
            const formatted = recentHighs.map((h, idx) => ({
                id: `H${idx + 1}`,
                price: h.price,
                time: h.time,
                index: h.index,
                status: priceData.price >= h.price ? 'pass' : 'fail'
            }));

            // 如果高點不足三個，用 0 或基礎值墊平
            while (formatted.length < 3) {
                formatted.unshift({
                    id: `H${3 - formatted.length}`,
                    price: 0,
                    time: '--:--',
                    index: -1,
                    status: 'fail'
                });
            }

            // 確保 ID 順序為 H1, H2, H3
            const finalHighs = formatted.map((h, i) => ({ ...h, id: `H${i + 1}` }));
            setHighPoints(finalHighs);
        }
    }, [tech5m, priceData.price]);

    const loadedSymbolRef = useRef(null);

    // Performance Optimization: Separated fetching logic to prevent blocking
    const fetchRealTimeData = useCallback(async (stockCode, forceUpdate = false) => {
        if (!stockCode) return;

        // 1. Fetch Quote immediately (Fastest) - Always fetch real-time price
        try {
            const quoteRes = await fetch(`${API_BASE}/api/quote/${stockCode}`);
            const res = await quoteRes.json();
            const quote = res.data;

            if (quote?.price) {
                setConnected(true);
                // ✅ 正確讀取漲跌幅：優先 change_percent（富邦API），其次 change
                const newChangePct = quote.change_percent ?? quote.change ?? null;
                // Update basic price info immediately
                setPriceData(prev => ({
                    ...prev,
                    price: quote.price,
                    // 只在有效值時更新，避免連線中斷時歸零
                    changePercent: (newChangePct !== null && newChangePct !== 0)
                        ? newChangePct
                        : (prev.changePercent || 0),
                    volume: quote.volume || prev.volume,
                    open: quote.open || prev.open,
                    high: quote.high || prev.high,
                    low: quote.low || prev.low,
                    orderBook: quote.orderBook || prev.orderBook,
                    dataSource: quote.dataSource || "富邦API"
                }));
                // 只在有實際中文名稱時才更新（避免代碼數字或空值覆蓋正確股名）
                if (quote.name && quote.name.trim() && !/^\d+$/.test(quote.name.trim())) {
                    setStockName(quote.name);
                }
            }
        } catch (e) { console.error("Quote fetch error", e); }

        // 2. Fetch Analysis & Market Data (Asynchronous) - Conditional for chips
        try {
            const promises = [
                fetch(`${API_BASE}/api/market-decision/status`)
            ];

            // Only fetch stock analysis (heavy data) if symbol changed or forced
            if (loadedSymbolRef.current !== stockCode || forceUpdate) {
                const ts = Date.now();
                promises.push(fetch(`${API_BASE}/api/stock-analysis/comprehensive/${stockCode}?t=${ts}`));
                promises.push(fetch(`${API_BASE}/api/smart-entry/support-resistance/${stockCode}?t=${ts}`));
                promises.push(fetch(`${API_BASE}/api/smart-entry/score/${stockCode}?t=${ts}`));
                promises.push(fetch(`${API_BASE}/api/mops/full/${stockCode}?t=${ts}`));
            }

            const results = await Promise.all(promises);
            const marketRes = results[0];
            const analysisRes = results.length > 1 ? results[1] : null;
            const srRes = results.length > 2 ? results[2] : null;
            const scoreRes = results.length > 3 ? results[3] : null;
            const mopsRes = results.length > 4 ? results[4] : null;

            const market = await marketRes.json();

            // 處理額外數據
            if (srRes) {
                const srData = await srRes.json();
                if (srData.success && srData.levels) {
                    setLevels(srData.levels);
                }
            }
            if (scoreRes) {
                const scoreData = await scoreRes.json();
                if (scoreData.success) {
                    if (scoreData.prev_high && scoreData.prev_low) {
                        setPrevDayData({ high: scoreData.prev_high, low: scoreData.prev_low });
                    }
                    const orb = scoreData.factors?.orb;
                    if (orb) {
                        setOrbData({ high: orb.range_high || 0, low: orb.range_low || 0 });
                    }
                }
            }

            // Update complex analysis data if fetched
            if (analysisRes) {
                const analysis = await analysisRes.json();
                if (analysis) {
                    if (analysis.stock_name) setStockName(analysis.stock_name);
                    setPriceData(prev => ({
                        ...prev,
                        vwap: analysis?.volume_price_analysis?.vwap || prev.vwap,
                        support: analysis?.support_resistance?.support || prev.support,
                        resistance: analysis?.support_resistance?.resistance || prev.resistance,
                        institutionalCost: analysis?.institutional_trading?.main_force_avg_cost || prev.institutionalCost,
                        concentration: analysis?.institutional_trading?.chip_concentration || prev.concentration,
                        avgVolume5d: analysis?.volume_price_analysis?.avg_volume_5d || prev.avgVolume5d,
                        institutionalHistory: analysis?.institutional_trading?.institutional_history || prev.institutionalHistory
                    }));
                    loadedSymbolRef.current = stockCode; // Mark as loaded for this symbol
                }
            }
            if (mopsRes) {
                const mopsData = await mopsRes.json();
                if (mopsData.success) {
                    setPriceData(prev => ({ ...prev, mopsData }));
                }
            }

            // Update market data
            if (market?.market_data) {
                const md = market.market_data;
                setMarketIndices(prev => ({
                    ...prev,
                    foreignNet: md.foreign_net || 0,
                    trustNet: md.trust_net || 0,
                    tseValue: md.index?.toLocaleString(),
                    tseChange: md.change?.toFixed(2),
                    tsePercent: md.change_pct?.toFixed(2) + "%",
                    isTseUp: md.change_pct > 0
                }));
            }

        } catch (err) {
            console.error("Secondary data fetch error", err);
        }
    }, []);

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date()), 1000);
        const blinker = setInterval(() => setBlink(prev => !prev), 800);
        const simulator = setInterval(() => {
            setKd(prev => {
                const newK = Math.min(100, Math.max(0, prev.k + (Math.random() - 0.5) * 5));
                const newD = Math.min(100, Math.max(0, prev.d + (Math.random() - 0.5) * 2));
                return { k: newK, d: newD, history: [...prev.history.slice(-19), { k: newK, d: newD }] };
            });
        }, 3000);
        return () => { clearInterval(timer); clearInterval(blinker); clearInterval(simulator); };
    }, []);

    // 🆕 新增：獨立的大盤數據獲取函數
    const fetchMarketData = useCallback(async () => {
        try {
            const marketRes = await fetch(`${API_BASE}/api/market-decision/status`);
            const market = await marketRes.json();
            if (market?.market_data) {
                setConnected(true);
                const md = market.market_data;
                setMarketIndices({
                    tseValue: md.index?.toLocaleString() || "32,063.75",
                    tseChange: (md.change > 0 ? '+' : '') + (md.change?.toFixed(2) || "0.00"),
                    tsePercent: (md.change_pct > 0 ? '+' : '') + (md.change_pct?.toFixed(2) || "-1.45") + "%",
                    isTseUp: md.change_pct > 0,
                    otaValue: md.ota_index?.toLocaleString() || "300.78",
                    otaChange: (md.ota_change > 0 ? '+' : '') + (md.ota_change?.toFixed(2) || "0.00"),
                    otaPercent: (md.ota_change_pct > 0 ? '+' : '') + (md.ota_change_pct?.toFixed(2) || "-1.54") + "%",
                    isOtaUp: md.ota_change_pct > 0,
                    elecValue: "1,960.06", elecPercent: "-1.54%",
                    finValue: "2,404.41", finPercent: "-1.22%",
                    foreignNet: md.foreign_net || 0,
                    trustNet: md.trust_net || 0,
                    sp500: (md.sp500_change > 0 ? '+' : '') + (md.sp500_change?.toFixed(2) || "-0.43") + "%",
                    nikkei: (md.nikkei_change > 0 ? '+' : '') + (md.nikkei_change?.toFixed(2) || "-0.10") + "%",
                    usdtwd: md.usdtwd?.toString() || "31.49",
                    usdtwdChange: (md.usdtwd_change > 0 ? '+' : '') + (md.usdtwd_change?.toFixed(2) || "+0.71") + "%",
                    marketSummary: market.summary || `大盤${md.change_pct > 0 ? '上漲' : '下跌'} ${md.change_pct?.toFixed(2)}%`,
                    aiRecommendation: market.decision?.action?.replace(/[✅🟡❌]/g, '').trim() || "觀望",
                    macroResult: market.macro_result
                });
            }
        } catch (err) {
            console.error("獲取大盤數據失敗:", err);
            setConnected(false);
        }
    }, []);

    // 🆕 新增：在組件掛載與定期獲取大盤
    useEffect(() => {
        fetchMarketData();
        const marketTimer = setInterval(fetchMarketData, 30000); // 每 30 秒更新一次大盤
        return () => clearInterval(marketTimer);
    }, [fetchMarketData]);

    const startMonitoring = () => {
        if (!inputSymbol.trim()) return;
        setLoading(true);
        setTech5m(null); // ✅ 切換股票時先清空舊 K 線
        // ✅ 切換股票時重置法人籌碼，顯示 loading 而非舊股票數據
        setPriceData(prev => ({
            ...prev,
            institutionalHistory: {
                foreign: { d1: 0, d5: 0, d10: 0, d20: 0 },
                trust: { d1: 0, d5: 0, d10: 0, d20: 0 },
                dealer: { d1: 0, d5: 0, d10: 0, d20: 0 },
                total: { d1: 0, d5: 0, d10: 0, d20: 0 }
            }
        }));
        setSymbol(inputSymbol.trim());
        setIsMonitoring(true);
        fetchRealTimeData(inputSymbol.trim());
        fetchTech5m(inputSymbol.trim()).finally(() => setLoading(false));
        fetchInstitutional(inputSymbol.trim()); // ✅ 立即取法人籌碼（快速API）
    };

    const stopMonitoring = () => {
        setIsMonitoring(false);
        setSymbol('');
        // setInputSymbol(''); // Optional: Keep input for quick restart
    };

    useEffect(() => {
        if (isMonitoring && symbol) {
            // ✅ 立即執行一次，不要等10秒
            fetchRealTimeData(symbol);
            fetchTech5m(symbol);

            // MA 突破警報 checker（每5秒，與行情同步）
            const checkMACross = async () => {
                try {
                    const h1p = highPoints?.[0]?.price || 0;
                    const h2p = highPoints?.[1]?.price || 0;
                    const h3p = highPoints?.[2]?.price || 0;
                    const vwapP = priceData?.vwap || 0;
                    const API_BASE = `http://${window.location.hostname}:8000`;
                    const url = `${API_BASE}/api/stock-analysis/technical/ma-cross-alert/${symbol}?h1=${h1p}&h2=${h2p}&h3=${h3p}&vwap=${vwapP}`;
                    const res = await fetch(url);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.triggered && !data.already_sent) {
                            // 前端視覺提示（Telegram 由後端發送）
                            console.log(`🔔 MA雙線突破！${symbol} @ ${data.cur_bar_time} 現價${data.cur_close} MA5:${data.cur_ma5} MA10:${data.cur_ma10}`);
                        }
                    }
                } catch (e) { /* 靜默失敗，不影響主流程 */ }
            };

            // ✅ 改為5秒更新一次（從10秒改進）
            const timer = setInterval(() => {
                fetchRealTimeData(symbol);
                fetchTech5m(symbol);
                checkMACross();   // ← MA 突破偵測同步執行
            }, 5000);

            return () => clearInterval(timer);
        }
    }, [isMonitoring, symbol, fetchRealTimeData, fetchTech5m, highPoints, priceData?.vwap]);

    // ✅ 法人籌碼每 60 秒更新一次（日級數據，不需太頻繁）
    useEffect(() => {
        if (isMonitoring && symbol) {
            fetchInstitutional(symbol); // 立即取一次
            const chipTimer = setInterval(() => fetchInstitutional(symbol), 60000);
            return () => clearInterval(chipTimer);
        }
    }, [isMonitoring, symbol, fetchInstitutional]);

    // ✅ 高點數據提取 (加上可選鏈防止崩潰)
    const h1 = highPoints[0]?.price || 0;
    const h2 = highPoints[1]?.price || 0;
    const h3 = highPoints[2]?.price || 0;

    // ✅ 走弱判斷邏輯（修正版：加入突破與漲停防護）
    const isWeakening = useMemo(() => {
        // 基本檢查
        if (h2 <= 0 || h3 <= 0 || priceData.price <= 0) return false;

        // 🚨 防護 1：強勢突破
        // 如果當前價格已經高於 H2 (前高)，代表趨勢已經反轉或創新高，不視為走弱
        if (priceData.price >= h2) return false;

        // 🚨 防護 2：漲停/接近漲停
        // 如果漲幅超過 9.5%，視為強勢鎖死或即將漲停，不應發出走弱訊號
        if (priceData.changePercent >= 9.5) return false;

        // 原始邏輯：H3 < H2 代表高點降低 (Lower Highs)，且當前價格未創新高
        return h3 < h2;
    }, [h2, h3, priceData.price, priceData.changePercent]);

    // ✅ 走弱幅度計算（百分比）
    const weakeningPercent = useMemo(() => {
        if (!isWeakening || h2 <= 0) return 0; // 只有在確認走弱時才計算
        return ((h3 - h2) / h2) * 100;
    }, [h2, h3, isWeakening]);

    const kdK = kd.k;
    const kdD = kd.d;
    const kdDeathCross = kdK < kdD;
    const belowVwap = priceData.price < priceData.vwap;

    const score = useMemo(() => {
        let s = 50;
        if (marketIndices.isTseUp) s += 15;
        if (priceData.changePercent > 0.5) s += 15;
        if (kdDeathCross) s -= 10;
        if (isWeakening) s -= 30; // 使用新的走弱判斷
        return Math.max(0, Math.min(100, s));
    }, [marketIndices.isTseUp, priceData.changePercent, kdDeathCross, isWeakening]);

    return (
        <div className="min-h-screen bg-[#F8FAFC] text-slate-600 font-sans selection:bg-red-100">
            <header className="bg-white/80 backdrop-blur-xl border-b border-slate-200 sticky top-0 z-50">
                <div className="max-w-[1920px] mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-gradient-to-br from-red-600 to-red-500 rounded-xl flex items-center justify-center shadow-lg shadow-red-200">
                            <Crosshair className="text-white" size={24} />
                        </div>
                        <div>
                            <h1 className="text-xl font-black text-slate-800 tracking-tighter uppercase flex items-center gap-2">
                                當沖狙擊手 <span className="bg-slate-800 text-white px-2 py-0.5 rounded text-[10px] tracking-widest">PRO V3.0</span>
                            </h1>
                            <div className="flex items-center gap-2 text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                                <span className="text-slate-500">VWAP 智能演算法決策引擎</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="relative group">
                            <input
                                type="text"
                                value={inputSymbol}
                                onChange={(e) => setInputSymbol(e.target.value.toUpperCase())}
                                onKeyDown={(e) => e.key === 'Enter' && startMonitoring()}
                                placeholder="輸入代碼 (2330)"
                                className="w-48 bg-slate-100 border-none rounded-xl px-4 py-2.5 text-sm font-black text-slate-800 placeholder:text-slate-400 focus:ring-2 focus:ring-red-500/20 transition-all uppercase tracking-widest"
                            />
                            <button
                                onClick={startMonitoring}
                                disabled={loading}
                                className="absolute right-2 top-1.5 p-1.5 bg-white rounded-lg text-slate-400 hover:text-red-500 shadow-sm transition-all"
                            >
                                {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
                            </button>
                        </div>
                        {isMonitoring && (
                            <button onClick={stopMonitoring} className="px-4 py-2 bg-red-50 text-red-500 rounded-xl text-xs font-black hover:bg-red-100 transition-colors">停止監測</button>
                        )}
                        <button
                            onClick={() => setShowPortfolio(true)}
                            className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-xl text-xs font-black hover:bg-slate-700 transition-colors shadow-lg shadow-slate-200"
                        >
                            <Briefcase size={14} /> 投資組合
                        </button>
                    </div>

                    <div className="flex items-center gap-8">
                        <MarketIndex label="加權指數" value={marketIndices.tseValue} change={marketIndices.tseChange} points={marketIndices.tsePercent} isUp={marketIndices.isTseUp} />
                        <MarketIndex label="櫃買指數" value={marketIndices.otaValue} change={marketIndices.otaChange} points={marketIndices.otaPercent} isUp={marketIndices.isOtaUp} />
                        <div className="flex flex-col text-right">
                            <span className="text-[10px] text-slate-400 font-black mb-1">即時連線</span>
                            <Wifi size={16} className={connected ? "text-green-500" : "text-slate-300"} />
                        </div>
                    </div>
                </div>
            </header>

            {showPortfolio && <PortfolioOverview onClose={() => setShowPortfolio(false)} />}

            <main className="max-w-[1920px] mx-auto p-6 relative">
                {!symbol && (
                    <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-6">
                        <div className="w-24 h-24 bg-red-50 rounded-full flex items-center justify-center mb-4 animate-pulse">
                            <Crosshair size={48} className="text-red-500" />
                        </div>
                        <h2 className="text-3xl font-black text-slate-800 tracking-tighter">等待目標輸入</h2>
                        <p className="text-slate-400 font-medium max-w-md">請在上方輸入股票代碼以啟動狙擊系統</p>
                    </div>
                )}

                <div className={`grid grid-cols-12 gap-6 ${!symbol ? 'opacity-20 pointer-events-none' : ''}`}>
                    {/* Left Column - Market Driver & Pulse */}
                    <div className="col-span-12 lg:col-span-3 space-y-6">
                        {/* Market Pulse Section */}
                        <div className="bg-white rounded-[2rem] border border-slate-200 p-6 shadow-sm">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2">
                                    <Globe size={16} className="text-blue-500" />
                                    <span className="text-xs font-black text-slate-800 uppercase tracking-widest">市場驅動與決策</span>
                                </div>
                                <span className="text-[10px] font-bold text-red-500 animate-pulse">即時連線</span>
                            </div>

                            <div className="space-y-4">
                                <div className="p-4 bg-slate-50 rounded-2xl flex justify-between items-center">
                                    <div className="text-[10px] text-slate-400 font-black uppercase">台股加權 (TAIEX)</div>
                                    <div className={`text-xl font-black font-mono ${marketIndices.isTseUp ? 'text-red-500' : 'text-green-600'}`}>
                                        {marketIndices.tseValue}
                                    </div>
                                </div>
                                <div className={`px-3 py-1.5 rounded-lg text-center font-black text-sm ${marketIndices.isTseUp ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'}`}>
                                    {marketIndices.tsePercent}
                                </div>

                                <div className="grid grid-cols-2 gap-3 mt-4">
                                    <div className="p-4 bg-white border border-slate-100 rounded-2xl shadow-sm text-center">
                                        <div className="text-[9px] text-slate-400 font-black mb-2">外資持倉</div>
                                        <div className={`text-xl font-black font-mono ${marketIndices.foreignNet > 0 ? 'text-red-500' : 'text-green-600'}`}>
                                            {marketIndices.foreignNet > 0 ? '+' : ''}{marketIndices.foreignNet}
                                        </div>
                                        <span className="text-[9px] text-slate-400 font-bold">億</span>
                                    </div>
                                    <div className="p-4 bg-white border border-slate-100 rounded-2xl shadow-sm text-center">
                                        <div className="text-[9px] text-slate-400 font-black mb-2">投信動向</div>
                                        <div className={`text-xl font-black font-mono ${marketIndices.trustNet > 0 ? 'text-red-500' : 'text-green-600'}`}>
                                            {marketIndices.trustNet > 0 ? '+' : ''}{marketIndices.trustNet}
                                        </div>
                                        <span className="text-[9px] text-slate-400 font-bold">億</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* VIX 恐慌指數 AI 分析 */}
                        <VixFearPanel vixData={vixData} />

                        {/* 國際政經與地緣政治總匯 */}
                        <MacroPanel />

                        {/* Volume Analysis */}
                        <div className="bg-white rounded-[2rem] border border-slate-200 p-6 shadow-sm">
                            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">成交量對比分析</div>
                            <div className="space-y-4">
                                <div className="flex justify-between items-center">
                                    <span className="text-xs font-black text-slate-600">今日量</span>
                                    <span className="text-sm font-black font-mono text-slate-900">{priceData.volume.toLocaleString()} 張</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs font-black text-slate-400">5日均量</span>
                                    <span className="text-sm font-black font-mono text-slate-400">{priceData.avgVolume5d?.toLocaleString() || '---'} 張</span>
                                </div>
                                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                                    <div className={`h-full ${priceData.volume > (priceData.avgVolume5d || 0) ? 'bg-red-500' : 'bg-blue-400'}`} style={{ width: `${Math.min(100, (priceData.volume / (priceData.avgVolume5d || 1)) * 100)}%` }}></div>
                                </div>
                                <div className="flex justify-between items-center bg-slate-50 p-2 rounded-lg">
                                    <span className="text-[10px] font-bold text-slate-500">量能比</span>
                                    <span className={`text-xs font-black ${priceData.volume > (priceData.avgVolume5d || Infinity) ? 'text-red-500' : 'text-slate-500'}`}>
                                        {priceData.avgVolume5d ? ((priceData.volume / priceData.avgVolume5d) * 100).toFixed(0) : '---'}%
                                        {priceData.volume > (priceData.avgVolume5d || Infinity) && <span className="ml-1">🔥 爆量</span>}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Order Book & Chips */}
                        <Section title="盤口與籌碼分析" icon={<Layers size={12} className="text-purple-500" />} badge="實時監控">
                            <div className="space-y-1">
                                <div className="flex justify-between px-2 text-[8px] text-slate-400 font-bold uppercase tracking-widest mb-2">
                                    <span>賣出</span><span>張數</span>
                                </div>
                                {priceData.orderBook?.asks?.slice(0, 5).reverse().map((a, i) => (
                                    <OrderRow key={`ask-${i}`} type="ask" price={a.price} vol={a.volume} />
                                ))}
                                <div className="my-2 border-t border-slate-100"></div>
                                <div className="flex justify-between px-2 text-[8px] text-slate-400 font-bold uppercase tracking-widest mb-2">
                                    <span>Bid</span><span>Vol</span>
                                </div>
                                {priceData.orderBook?.bids?.slice(0, 5).map((b, i) => (
                                    <OrderRow key={`bid-${i}`} type="bid" price={b.price} vol={b.volume} />
                                ))}
                            </div>
                        </Section>
                    </div>

                    {/* Center Column - Chart & Main Info */}
                    <div className="col-span-12 lg:col-span-5 space-y-6">
                        {/* Big Ticker Card - Balanced & Beautiful */}
                        <div className="bg-white rounded-[2.5rem] px-8 py-6 border border-slate-100 shadow-xl shadow-slate-200/60 flex items-center justify-between relative overflow-hidden backdrop-blur-sm">
                            <div className="flex flex-col justify-center min-w-0 pr-4">
                                <div className="flex items-end gap-3 mb-2">
                                    {/* Stock Code */}
                                    <h2 className="text-6xl font-black tracking-tighter text-[#0f172a] leading-none select-none whitespace-nowrap">
                                        {symbol}
                                    </h2>

                                    {/* Name & Badge Group */}
                                    <div className="flex flex-col gap-1 pb-0.5">
                                        <div className="flex items-center gap-1.5">
                                            <span className="text-2xl font-bold text-[#1e293b] tracking-tight whitespace-nowrap">{stockName || '讀取中'}</span>
                                            <span className="bg-[#2563eb] text-white text-[10px] font-bold px-2 py-0.5 rounded-full tracking-wide shadow-sm shadow-blue-200 whitespace-nowrap">富邦API</span>
                                        </div>
                                        <div className="text-slate-400 font-bold text-[10px] tracking-widest text-left whitespace-nowrap">即時監控</div>
                                    </div>
                                </div>

                                {/* Volume Display */}
                                <div className="flex items-center gap-2 pl-1">
                                    <span className="text-slate-400 font-bold text-xs tracking-wider uppercase">Volume</span>
                                    <span className="text-[#334155] font-black text-xl font-mono tracking-tight">{priceData.volume.toLocaleString()}</span>
                                </div>
                            </div>

                            {/* Price Section */}
                            <div className="text-right flex flex-col items-end flex-shrink-0">
                                <div className={`text-7xl font-black tracking-tighter leading-none mb-1 select-none font-sans ${priceData.changePercent > 0 ? 'text-[#ef4444]' : priceData.changePercent < 0 ? 'text-[#22c55e]' : 'text-[#64748b]'}`}>
                                    {priceData.price.toFixed(2)}
                                </div>
                                <div className="flex items-center gap-2 pr-1">
                                    <div className={`w-2.5 h-2.5 rounded-full ${priceData.changePercent > 0 ? 'bg-red-400' : priceData.changePercent < 0 ? 'bg-green-400' : 'bg-slate-400'} animate-pulse shadow-sm`}></div>
                                    <div className={`text-3xl font-black tracking-tighter ${priceData.changePercent > 0 ? 'text-[#ef4444]' : priceData.changePercent < 0 ? 'text-[#22c55e]' : 'text-[#64748b]'}`}>
                                        {priceData.changePercent > 0 ? '+' : ''}{Number(priceData.changePercent).toFixed(2)}%
                                    </div>
                                </div>
                            </div>
                        </div>



                        <div className="grid grid-cols-2 gap-4">
                            <div className="bg-white p-4 rounded-2xl border border-slate-100 flex items-center justify-between relative overflow-hidden">
                                <div className="relative z-10">
                                    <div className="text-[9px] text-slate-400 font-black uppercase tracking-widest mb-1">今日盤中高點 H2</div>
                                    <div className="text-2xl font-black font-mono text-slate-800">{h2 > 0 ? h2.toFixed(2) : '--.--'}</div>
                                </div>
                                {isWeakening && <span className="px-2 py-1 bg-red-100 text-red-600 rounded text-[9px] font-bold animate-pulse">突破失敗</span>}
                            </div>
                            <div className="bg-white p-4 rounded-2xl border border-slate-100 flex items-center justify-between">
                                <div>
                                    <div className="text-[9px] text-slate-400 font-black uppercase tracking-widest mb-1">成交均價 (VWAP)</div>
                                    <div className="text-2xl font-black font-mono text-amber-500">{priceData.vwap.toFixed(2)}</div>
                                </div>
                                <span className={`px-2 py-1 rounded text-[9px] font-bold ${belowVwap ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                                    {belowVwap ? '跌破' : '站上'}
                                </span>
                            </div>
                        </div>

                        {/* ⚡ 即時行動方案 - K線圖正上方 */}
                        {highPoints?.[0]?.price > 0 && (() => {
                            const h1 = highPoints[0]?.price || 0;
                            const h2 = highPoints[1]?.price || 0;
                            const h3 = highPoints[2]?.price || 0;
                            const vwap = priceData.vwap || 0;
                            const cur  = priceData.price || 0;

                            const h1NotBroken = cur < h1;
                            const descendHigh = h3 > 0 && h2 > 0 && h3 < h2;
                            const belowVWAP   = vwap > 0 && cur < vwap;
                            const breakH3     = h3 > 0 && cur > h3 * 1.005;
                            const aboveVWAP   = vwap > 0 && cur >= vwap;

                            const isBear = h1NotBroken && (descendHigh || belowVWAP);
                            const isBull = breakH3 && aboveVWAP;
                            const bullMet = [breakH3, aboveVWAP].filter(Boolean).length;

                            const pf = v => v ? v.toFixed(2) : '--';

                            return (
                            <div className="flex gap-2 mb-2">

                                {/* 🔴 跌勢卡 */}
                                <div className={`flex-1 rounded-xl border-2 p-2.5 transition-all ${
                                    isBear ? 'border-red-400 bg-gradient-to-br from-red-50 to-rose-50 shadow-lg shadow-red-100'
                                           : 'border-slate-200 bg-white/50 opacity-50'
                                }`}>
                                    <div className="flex items-center justify-between mb-1.5">
                                        <span className="text-[11px] font-black text-red-700">🔴 跌勢方案</span>
                                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded-full ${
                                            isBear ? 'bg-red-600 text-white animate-pulse' : 'bg-slate-200 text-slate-400'
                                        }`}>{isBear ? '▣ 觸發' : '待確認'}</span>
                                    </div>
                                    {/* 條件燈 */}
                                    <div className="flex gap-1 mb-1.5">
                                        {[
                                            { t: 'H1未過', ok: h1NotBroken },
                                            { t: '高點降', ok: descendHigh },
                                            { t: 'VWAP下', ok: belowVWAP },
                                        ].map(({t,ok}) => (
                                            <span key={t} className={`flex-1 text-center text-[9px] font-bold py-0.5 rounded ${
                                                ok ? 'bg-red-500 text-white' : 'bg-slate-100 text-slate-400'
                                            }`}>{ok?'✓':''}{t}</span>
                                        ))}
                                    </div>
                                    {/* 操作摘要 */}
                                    <div className="text-[10px] text-slate-600 space-y-0.5">
                                        <div>🛑 <b>停損</b> <span className="font-mono text-red-600 font-black">{h3>0?(h3*1.006).toFixed(2):'--'}</span> (H3上方)</div>
                                        <div>🎯 <b>空點</b> 反彈至VWAP <span className="font-mono font-black">{pf(vwap)}</span> 量縮時</div>
                                        <div>📍 <b>目標</b> 前低 {priceData.prevLow>0?<span className="font-mono font-black">{priceData.prevLow.toFixed(2)}</span>:'ORB低點'}</div>
                                    </div>
                                </div>

                                {/* 🟢 翻多卡 */}
                                <div className={`flex-1 rounded-xl border-2 p-2.5 transition-all ${
                                    isBull ? 'border-emerald-400 bg-gradient-to-br from-emerald-50 to-teal-50 shadow-lg shadow-emerald-100'
                                           : 'border-slate-200 bg-white/50'
                                }`}>
                                    <div className="flex items-center justify-between mb-1.5">
                                        <span className="text-[11px] font-black text-emerald-700">🟢 翻多條件</span>
                                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded-full ${
                                            isBull ? 'bg-emerald-600 text-white animate-pulse'
                                            : bullMet===1 ? 'bg-amber-400 text-white'
                                            : 'bg-slate-200 text-slate-400'
                                        }`}>{bullMet}/2 達成</span>
                                    </div>
                                    {/* 條件燈 */}
                                    <div className="flex gap-1 mb-1.5">
                                        {[
                                            { t: `突破H3 ${pf(h3)}`, ok: breakH3 },
                                            { t: `站上VWAP ${pf(vwap)}`, ok: aboveVWAP },
                                        ].map(({t,ok}) => (
                                            <span key={t} className={`flex-1 text-center text-[9px] font-bold py-0.5 rounded ${
                                                ok ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-400'
                                            }`}>{ok?'✅':'⬜'} {t}</span>
                                        ))}
                                    </div>
                                    {/* 操作摘要 */}
                                    <div className="text-[10px] text-slate-600 space-y-0.5">
                                        <div>📈 <b>進場</b> 量&gt;均量1.2倍 + 紅K收關</div>
                                        <div>🛑 <b>停損</b> <span className="font-mono text-red-600 font-black">{h3>0?(h3*0.995).toFixed(2):'--'}</span> (H3下方)</div>
                                        <div>🎯 <b>目標</b> H2 <span className="font-mono font-black">{pf(h2)}</span> → H1 <span className="font-mono font-black">{pf(h1)}</span></div>
                                    </div>
                                </div>

                            </div>
                            );
                        })()}

                        <ChartComponent
                            tech5m={tech5m}
                            priceData={priceData}
                            highPoints={highPoints}
                            isWeakening={isWeakening}
                            weakeningPercent={weakeningPercent}
                        />

                        {/* Technical Indicators Summary */}
                        <div className="bg-white rounded-[2rem] p-6 border border-slate-200">
                            <div className="flex items-center gap-2 mb-4">
                                <BarChart2 size={16} className="text-blue-500" />
                                <span className="text-xs font-black text-slate-800 uppercase tracking-widest">5分鐘線技術分析評估</span>
                            </div>
                            <div className="grid grid-cols-4 gap-2">
                                <TradeLevel label="MA5" price={tech5m?.ma5 || 0} color="text-slate-800" />
                                <TradeLevel label="MA20" price={tech5m?.ma20 || 0} color="text-red-500" />
                                <TradeLevel label="RSI" price={tech5m?.rsi || 50} color="text-slate-800" />
                                <TradeLevel label="MACD" price={tech5m?.macd || 0} color="text-green-600" />
                            </div>
                        </div>

                        <Section
                            title="🤖 AI 2日股價預測 (LSTM v2 自學)"
                            icon={<Globe size={12} className="text-indigo-500" />}
                        >
                            <AIPricePredictionPanel symbol={symbol} />
                        </Section>

                        {/* 法人籌碼買賣超（保留） */}
                        <Section
                            title="🏦 法人籌碼買賣超"
                            icon={<Globe size={12} className="text-purple-500" />}
                            action={
                                <button
                                    onClick={() => { fetchRealTimeData(symbol, true); fetchInstitutional(symbol); }}
                                    className="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-500 rounded text-[9px] font-bold flex items-center gap-1 transition-colors"
                                >
                                    <RefreshCw size={8} /> 更新
                                </button>
                            }
                        >
                            <InstitutionalChipDashboard
                                data={priceData.institutionalHistory}
                                price={priceData.price}
                                stockName={stockName}
                                cost={priceData.institutionalCost}
                                concentration={priceData.concentration}
                            />
                        </Section>

                        {/* 🆕 國際政經總匯 (Global Macro Dashboard) */}
                        <InternationalMacroPanel data={marketIndices.macroResult} />

                        {/* MOPS Panel - 公開資訊觀測站 */}
                        <div className="bg-white rounded-[2rem] border border-slate-200 p-6 shadow-sm mt-6">
                            <MOPSPanel symbol={symbol} stockName={stockName} />
                            <KGISection symbol={symbol} />
                            <EpsEvaluationPanel symbol={symbol} stockName={stockName} />
                        </div>
                    </div>

                    {/* Right Column - Monitoring & Defense */}
                    <div className="col-span-12 lg:col-span-4 space-y-6">
                        {/* 🆕 總結操作建議 */}
                        <StrategySummary
                            marketData={{ ...marketIndices, current: priceData.price, prevHigh: prevDayData.high, prevLow: prevDayData.low, open: priceData.open, volume: priceData.volume, avgVolume5d: priceData.avgVolume5d, vwap: priceData.vwap }}
                            levels={levels}
                            orbData={orbData}
                            mopsData={priceData.mopsData}
                            vixData={vixData}
                            symbol={symbol}
                            chipData={priceData.institutionalHistory}
                            highPoints={highPoints}
                        />

                        <Section title="5分K 高點結構監控" icon={<Target size={12} className="text-slate-800" />} badge="監測中">
                            <div className="space-y-3">
                                <MonitorCard label="H1 前高數據" value={h1 > 0 ? h1.toFixed(2) : '--.--'} sub="Reference" />
                                <MonitorCard label="H2 前高數據" value={h2 > 0 ? h2.toFixed(2) : '--.--'} sub="Resistance" />
                                <div className={`p-4 rounded-2xl border text-center transition-all ${isWeakening ? 'bg-red-50 border-red-200 shadow-lg scale-105' : 'bg-white border-slate-100'}`}>
                                    <div className="text-[10px] text-slate-400 font-black uppercase mb-1.5 tracking-widest leading-none">H3 最新高點</div>
                                    <div className="text-3xl font-mono font-black text-red-500 leading-none">{h3 > 0 ? h3.toFixed(2) : '--.--'}</div>
                                    {isWeakening && <div className="mt-2 text-[9px] font-bold text-red-500 animate-pulse">⚠️ 結構轉弱確認</div>}
                                </div>
                                <div className="bg-slate-900 p-3 rounded-xl text-center">
                                    <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest">當前價格</span>
                                    <div className="text-white font-mono font-black text-xl">{priceData.price.toFixed(2)}</div>
                                </div>
                            </div>
                        </Section>

                        <Section title="三重出場防衛矩陣" icon={<Shield size={12} className="text-blue-500" />}>
                            <div className="space-y-3">
                                <DefenseLevel
                                    priority="第一道防線"
                                    label="H3 < H2 (二次高點破不了)"
                                    status={isWeakening ? 'triggered' : 'safe'}
                                    action="減碼多單"
                                    subInfo={`Weakness: ${weakeningPercent.toFixed(2)}%`}
                                />
                                <DefenseLevel
                                    priority="第二道防線"
                                    label="跌破實時 VWAP 均價線"
                                    status={belowVwap ? 'triggered' : 'safe'}
                                    action="出清持股"
                                    subInfo={`Gap: ${(priceData.price - priceData.vwap).toFixed(2)}`}
                                />
                                <DefenseLevel
                                    priority="第三道防線"
                                    label="KD 死亡交叉確認"
                                    status={kdDeathCross ? 'triggered' : 'safe'}
                                    action="反手放空"
                                    subInfo={`K:${kdK.toFixed(1)} / D:${kdD.toFixed(1)}`}
                                />
                            </div>
                        </Section>

                        <Section title="KD 指標結構" icon={<TrendingUp size={12} className="text-purple-500" />} badge="5分K週期">
                            <div className="grid grid-cols-2 gap-4 mb-3">
                                <div className="bg-white p-4 rounded-2xl border border-slate-100 text-center relative overflow-hidden">
                                    <div className="text-[9px] text-slate-400 font-black uppercase mb-1 z-10 relative">K 線值</div>
                                    <div className="text-3xl font-mono font-black text-red-500 z-10 relative">{kdK.toFixed(1)}</div>
                                    {kdK > 80 && <div className="absolute top-0 right-0 p-1"><Flame size={12} className="text-red-500/20" /></div>}
                                </div>
                                <div className="bg-white p-4 rounded-2xl border border-slate-100 text-center relative overflow-hidden">
                                    <div className="text-[9px] text-slate-400 font-black uppercase mb-1 z-10 relative">D 線值</div>
                                    <div className="text-3xl font-mono font-black text-blue-500 z-10 relative">{kdD.toFixed(1)}</div>
                                </div>
                            </div>
                            <div className="bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
                                <div className="text-[10px] font-bold text-slate-500 mb-1">當前狀態分析</div>
                                <div className={`text-sm font-black tracking-tight ${kdK > kdD ? 'text-red-500' : 'text-green-600'}`}>
                                    {kdK > kdD
                                        ? (kdK > 80 ? "🔥 高檔鈍化 (強勢整理)" : "📈 黃金交叉 (多頭確認)")
                                        : (kdK < 20 ? "❄️ 低檔鈍化 (超賣區域)" : "📉 死亡交叉 (小心回檔)")
                                    }
                                </div>
                                <div className="text-[9px] text-slate-400 mt-1">
                                    {kdK > kdD ? "建議：偏多操作，若跌破 D 線停利" : "建議：偏空觀望，等待打底訊號"}
                                </div>
                            </div>
                        </Section>

                        <div className="bg-slate-900 rounded-[2rem] p-8 text-white relative overflow-hidden group">
                            <div className="relative z-10">
                                <div className="flex justify-between items-start mb-2">
                                    <div className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">狙擊手評分 (Sniper Score)</div>
                                    <div className="group/hint relative">
                                        <Info size={12} className="text-slate-600 cursor-help" />
                                        <div className="absolute right-0 bottom-full mb-2 w-48 bg-slate-800 text-slate-200 text-[9px] p-2 rounded-lg opacity-0 group-hover/hint:opacity-100 transition-opacity pointer-events-none z-50">
                                            綜合考量技術面、籌碼面、型態與動能的 AI 評分系統 (0-100)
                                        </div>
                                    </div>
                                </div>
                                <div className="text-5xl font-black font-mono tracking-tighter mb-4">{score}</div>
                                <div className="flex gap-2">
                                    <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-widest ${score > 70 ? 'bg-red-500 text-white' : score < 30 ? 'bg-green-600 text-white' : 'bg-white/10 text-slate-300'}`}>
                                        {score > 70 ? '強力買進 (Strong Buy)' : score < 30 ? '強力賣出 (Strong Sell)' : '中性觀望 (Neutral)'}
                                    </span>
                                </div>
                                <div className="mt-4 text-[9px] text-slate-500 font-mono">
                                    Confidence: {(score > 60 || score < 40) ? 'HIGH' : 'MODERATE'}
                                </div>
                            </div>
                            {/* Background Ring Decoration */}
                            <div className={`absolute top-1/2 right-0 -translate-y-1/2 translate-x-1/2 w-48 h-48 rounded-full border-[12px] opacity-20 transition-colors duration-1000 ${score > 50 ? 'border-red-500' : 'border-green-500'}`}></div>
                            <div className={`absolute top-1/2 right-0 -translate-y-1/2 translate-x-1/2 w-32 h-32 rounded-full border-[12px] opacity-40 transition-colors duration-1000 ${score > 50 ? 'border-red-500' : 'border-green-500'}`}></div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};

// Helper Components
const MarketIndex = ({ label, value, change, points, isUp }) => (
    <div className="flex flex-col text-right">
        <span className="text-[10px] text-slate-400 uppercase font-black mb-1 tracking-widest leading-none">{label}</span>
        <div className="flex items-center gap-2 font-black">
            <span className="text-slate-800 font-mono tracking-tighter">{value}</span>
            <div className={`flex flex-col items-end px-1.5 py-0.5 rounded ${isUp ? 'bg-red-50 text-red-500' : 'bg-green-50 text-green-600'}`}>
                <span className="text-[9px] leading-tight font-black">{points}</span>
                <span className="text-[8px] leading-tight opacity-80">{change}</span>
            </div>
        </div>
    </div>
);

const Section = ({ title, badge, icon, action, children }) => (
    <div className="bg-white rounded-[2rem] border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-7 py-5 bg-slate-50/50 border-b border-slate-100 flex justify-between items-center">
            <h3 className="text-xs font-black text-slate-800 flex items-center gap-3 uppercase tracking-widest">
                <span className="p-2 bg-white rounded-xl shadow-sm border border-slate-100">{icon}</span>
                {title}
            </h3>
            <div className="flex items-center gap-2">
                {action}
                {badge && <span className="text-[9px] text-red-500 font-black tracking-widest uppercase leading-none">{badge}</span>}
            </div>
        </div>
        <div className="p-8">{children}</div>
    </div>
);

const PriceLabel = ({ label, price, color, value, sub }) => (
    <div className="flex-1 min-w-[180px] flex items-center gap-3 bg-white px-5 py-3 rounded-2xl border border-slate-100 shadow-sm">
        <div className={`w-2.5 h-2.5 rounded-full ${color} animate-pulse shrink-0`} /><div className="flex flex-col flex-1 truncate"><div className="flex items-center justify-between mb-0.5"><span className="text-[8px] text-slate-400 font-black uppercase tracking-widest leading-none">{label}</span><span className="text-[7px] bg-slate-50 text-slate-400 px-1 rounded font-black uppercase tracking-widest leading-none">{sub}</span></div><div className="flex items-center justify-between gap-2"><span className="text-lg font-mono font-black text-slate-800 tracking-tighter leading-none">{price === '0.00' ? '--.--' : price}</span><span className={`text-[9px] font-black px-1.5 py-0.5 rounded-lg whitespace-nowrap uppercase tracking-widest leading-none ${value.includes('突破') || value.includes('站上') ? 'bg-red-500 text-white' : 'bg-slate-100 text-slate-500'}`}>{value}</span></div></div>
    </div>
);

const TradeLevel = ({ label, price, color }) => (
    <div className="p-4 bg-slate-50 border border-slate-100 rounded-2xl text-center"><div className="text-[9px] text-slate-400 font-black uppercase mb-1 tracking-widest leading-none">{label}</div><div className={`text-xl font-black font-mono leading-none ${color}`}>{parseFloat(price) > 0 ? price : '--.--'}</div></div>
);

const DefenseLevel = ({ priority, label, status, action, subInfo }) => (
    <div className={`p-4 rounded-2xl border transition-all duration-500 ${status === 'triggered' ? 'bg-green-600 border-green-700 text-white shadow-lg' : 'bg-white border-slate-200 opacity-60'}`}>
        <div className="flex justify-between items-center mb-1"><div className="text-[8px] font-black uppercase opacity-70 tracking-widest leading-none">{priority}</div>{status === 'triggered' ? (<span className="text-[7px] bg-white/20 px-1.5 py-0.5 rounded font-black animate-pulse">ALARM</span>) : (<CheckCircle2 size={10} className="text-slate-300" />)}</div>
        <div className="font-bold text-sm tracking-tight leading-none">{label}</div>
        {status === 'triggered' && (<div className="mt-2 pt-2 border-t border-white/20"><div className="text-[10px] font-black italic flex items-center gap-1 uppercase tracking-widest leading-none"><Zap size={10} /> {action}</div>{subInfo && <div className="text-[8px] opacity-70 font-mono mt-0.5 uppercase tracking-widest leading-none">{subInfo}</div>}</div>)}
    </div>
);

const MonitorCard = ({ label, value, sub }) => (
    <div className="p-4 bg-white rounded-2xl border border-slate-100 text-center shadow-sm"><div className="text-[10px] text-slate-400 font-black uppercase mb-1.5 tracking-widest leading-none">{label}</div><div className="text-lg font-mono font-black text-slate-800 leading-none">{value || '--'}</div><div className={`text-[9px] font-black uppercase mt-1.5 tracking-widest leading-none ${sub === '偏多' || sub === '支撐' ? 'text-red-500' : 'text-green-600'}`}>{sub}</div></div>
);

const OrderRow = ({ type, price, vol }) => (
    <div className={`flex justify-between items-center p-1.5 rounded-lg transition-all ${type === 'ask' ? 'bg-red-50/50 hover:bg-red-100/50' : 'bg-green-50/50 hover:bg-green-100/50'}`}><span className={`font-mono font-black leading-none ${type === 'ask' ? 'text-red-500' : 'text-green-600'}`}>{parseFloat(price) > 0 ? price : '--.--'}</span><span className="text-slate-500 font-mono font-black text-[9px] leading-none">{vol !== '0' ? vol : '---'}</span></div>
);

// 🏦 法人籌碼監控儀表板
const InstitutionalChipDashboard = ({ data, price, stockName, cost, concentration }) => {
    const isDataEmpty = () => {
        if (!data || !data.foreign || !data.trust || !data.dealer || !data.total) return true;
        return ['d1','d5','d10','d20'].every(p =>
            (data.foreign[p]||0)===0 && (data.trust[p]||0)===0 &&
            (data.dealer[p]||0)===0 && (data.total[p]||0)===0
        );
    };
    const dataIsEmpty = isDataEmpty();
    const getMomentum = () => {
        if (dataIsEmpty) return { text:'計算中', color:'text-slate-500' };
        const v = data?.total?.d10 || 0;
        if (v > 5000) return { text:'強勢多方', color:'text-red-600' };
        if (v > 1000) return { text:'溫和多方', color:'text-red-500' };
        if (v > -1000) return { text:'多空平衡', color:'text-slate-700' };
        if (v > -5000) return { text:'溫和空方', color:'text-green-600' };
        return { text:'空方壓制', color:'text-green-700' };
    };
    const momentum = getMomentum();

    if (dataIsEmpty) return (
        <div className="flex flex-col items-center justify-center gap-3 py-8">
            <Loader2 size={36} className="text-blue-500 animate-spin" />
            <p className="text-sm font-bold text-slate-600">籌碼資料獲取中...</p>
            <p className="text-xs text-slate-400">首次載入需 15-30 秒</p>
        </div>
    );

    const rows = [
        { label:'外資 (Foreign)', key:'foreign' },
        { label:'投信 (Trust)', key:'trust' },
        { label:'自營商 (Dealer)', key:'dealer' },
        { label:'三大法人合計', key:'total', isTotal:true },
    ];

    return (
        <div className="flex flex-col gap-4">
            {/* 動能判讀 + 主力盈褒 + 集中度 */}
            <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-50 rounded-xl p-4 flex flex-col items-center border border-slate-100">
                    <span className="text-[9px] text-slate-400 font-bold uppercase tracking-widest mb-2">D10 動能</span>
                    <span className={`text-xl font-black ${momentum.color}`}>{momentum.text}</span>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 flex flex-col items-center border border-slate-100">
                    <span className="text-[9px] text-slate-400 font-bold uppercase tracking-widest mb-2">主力盈褒</span>
                    <span className={`text-lg font-black font-mono ${(price-(cost||price))>=0?'text-red-500':'text-green-600'}`}>
                        {cost>0?`${(price-cost)>=0?'+':''}${(price-cost).toFixed(2)}`:'-'}
                    </span>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 flex flex-col items-center border border-slate-100">
                    <span className="text-[9px] text-slate-400 font-bold uppercase tracking-widest mb-2">集中度</span>
                    <span className="text-2xl font-black font-mono text-slate-800">{concentration?concentration.toFixed(1):'0.0'}%</span>
                </div>
            </div>

            {/* 法人買賣超表格 */}
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
                <div className="flex items-center gap-2 p-3 border-b border-slate-100 bg-slate-50">
                    <div className="w-1.5 h-4 bg-purple-600 rounded-full" />
                    <span className="text-xs font-bold text-slate-700">🧳 法人買賣超 (單位:張)</span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left min-w-[480px]">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-100">
                                <th className="py-2 pl-4 text-xs font-bold text-slate-500">法人機構</th>
                                {['今日','┗5日','10日','20日'].map(h=><th key={h} className="py-2 pr-4 text-right text-xs font-bold text-slate-500">{h}</th>)}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {rows.map(row => (
                                <tr key={row.key} className={row.isTotal?'bg-slate-50/50':''}>
                                    <td className={`py-3 pl-4 text-xs font-bold ${row.isTotal?'text-slate-800':'text-slate-600'}`}>{row.label}</td>
                                    {['d1','d5','d10','d20'].map(p => {
                                        const v = data[row.key]?.[p]||0;
                                        return <td key={p} className="py-3 pr-4 text-right"><span className={`text-xs font-mono font-black ${v>0?'text-red-500':v<0?'text-green-600':'text-slate-400'}`}>{v>0?'+':''}{v.toLocaleString()}</span></td>;
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                <div className="bg-yellow-50 p-2 text-[9px] text-yellow-700 font-bold border-t border-yellow-100">
                    💡 資料來源：台灣證券交易所 TWSE T86，涵蓋至最近一個交易日收盤。
                </div>
            </div>
        </div>
    );
};

// 🤖 AI 2日股價預測面板 (LSTM v2 自學)
const AIPricePredictionPanel = ({ symbol }) => {
    const [pred, setPred] = React.useState(null);
    const [pred5, setPred5] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [history, setHistory] = React.useState([]);
    const [training, setTraining] = React.useState(false);
    const [trainMsg, setTrainMsg] = React.useState('');
    const API = 'http://localhost:8000/api/prediction';

    const fetchPrediction = async () => {
        if (!symbol) return;
        setLoading(true);
        try {
            const [r2, r5] = await Promise.all([
                fetch(`${API}/${symbol}?horizon=2&save=true`),
                fetch(`${API}/${symbol}?horizon=5&save=false`),
            ]);
            if (r2.ok) setPred(await r2.json());
            if (r5.ok) setPred5(await r5.json());
            const rh = await fetch(`${API}/history/${symbol}?limit=8`);
            if (rh.ok) { const d = await rh.json(); setHistory(d.history || []); }
        } catch (e) { console.error('預測失敗:', e); }
        finally { setLoading(false); }
    };

    const triggerTraining = async () => {
        setTraining(true);
        setTrainMsg('訓練中（約需1-2分鐘）...');
        try {
            const r = await fetch(`${API}/train/${symbol}?horizon=2`, { method: 'POST' });
            const d = await r.json();
            setTrainMsg(d.message || '訓練已啟動');
            setTimeout(() => { setTrainMsg(''); fetchPrediction(); }, 90000);
        } catch { setTrainMsg('訓練失敗'); }
        finally { setTraining(false); }
    };

    React.useEffect(() => { if (symbol) fetchPrediction(); }, [symbol]);

    const dirColor = (dir) => dir === 'up' ? 'text-red-500' : dir === 'down' ? 'text-green-600' : 'text-slate-500';
    const dirBg   = (dir) => dir === 'up' ? 'from-red-500 to-rose-500' : dir === 'down' ? 'from-green-500 to-emerald-600' : 'from-slate-400 to-slate-500';
    const dirEmoji = (dir) => dir === 'up' ? '📈' : dir === 'down' ? '📉' : '➡️';
    const dirLabel = (dir) => dir === 'up' ? '上漲' : dir === 'down' ? '下跌' : '盤整';

    const accuracy = pred?.accuracy_stats?.direction_accuracy_pct ?? 0;
    const totalVerified = pred?.accuracy_stats?.total ?? 0;
    const correctCount = pred?.accuracy_stats?.correct ?? 0;

    if (!symbol) return <div className="text-center text-slate-400 py-4">請先輸入股票代碼</div>;

    return (
        <div className="space-y-4">
            {/* 操作按鈕 */}
            <div className="flex gap-2 justify-end">
                <button onClick={triggerTraining} disabled={training}
                    className="px-3 py-1.5 text-[10px] bg-slate-100 text-slate-500 rounded-lg hover:bg-slate-200 font-bold disabled:opacity-40">
                    {training ? '⏳ 訓練中' : '🎓 訓練 LSTM'}
                </button>
                <button onClick={fetchPrediction} disabled={loading}
                    className={`px-3 py-1.5 text-[10px] rounded-lg font-bold ${loading ? 'bg-slate-200 text-slate-400' : 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:opacity-90'}`}>
                    {loading ? '⏳ 計算中...' : pred ? '🔄 重新預測' : '🚀 開始預測'}
                </button>
            </div>

            {trainMsg && <div className="p-2 bg-yellow-50 border border-yellow-200 rounded text-yellow-700 text-[10px] font-bold">⚙️ {trainMsg}</div>}

            {!pred ? (
                <div className="text-center py-8 text-slate-400">
                    <div className="text-4xl mb-3">🤖</div>
                    <p className="text-sm font-bold text-slate-500">LSTM 神經網路 + 18 特徵</p>
                    <p className="text-[10px] mt-1 text-indigo-400">每次預測存入 PostgreSQL，16:00 自動驗證</p>
                </div>
            ) : (
                <>
                    {/* 主預測卡 */}
                    <div className={`p-5 rounded-2xl bg-gradient-to-r ${dirBg(pred.prediction.predicted_direction)} text-white`}>
                        <div className="flex justify-between items-start">
                            <div>
                                <div className="text-[10px] opacity-70 uppercase tracking-widest">2日後方向</div>
                                <div className="text-3xl font-black mt-1">{dirEmoji(pred.prediction.predicted_direction)} {dirLabel(pred.prediction.predicted_direction)}</div>
                                <div className="text-[10px] opacity-70 mt-1">目標：{pred.prediction.target_date}</div>
                            </div>
                            <div className="text-right">
                                <div className="text-[10px] opacity-70">預測價</div>
                                <div className="text-2xl font-black font-mono">{pred.prediction.predicted_price?.toLocaleString()}</div>
                                <div className="text-sm font-bold">{pred.prediction.predicted_change_pct > 0 ? '+' : ''}{pred.prediction.predicted_change_pct?.toFixed(2)}%</div>
                            </div>
                        </div>
                        <div className="mt-3 pt-3 border-t border-white/30">
                            <div className="flex justify-between text-[10px] mb-1"><span className="opacity-70">信心度</span><span className="font-bold">{pred.prediction.confidence?.toFixed(1)}%</span></div>
                            <div className="w-full bg-white/30 rounded-full h-1.5"><div className="bg-white rounded-full h-1.5" style={{ width: `${Math.min(100, pred.prediction.confidence || 0)}%` }} /></div>
                        </div>
                    </div>

                    {/* 預測區間 + 5日 */}
                    <div className="grid grid-cols-2 gap-3">
                        <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                            <div className="text-[9px] text-slate-500 font-bold uppercase mb-2">2日預測區間</div>
                            <div className="space-y-1 text-[11px]">
                                <div className="flex justify-between"><span className="text-slate-400">高</span><span className="font-black text-red-500">{pred.prediction.predicted_high?.toLocaleString()}</span></div>
                                <div className="flex justify-between"><span className="text-slate-400">中</span><span className="font-black">{pred.prediction.predicted_price?.toLocaleString()}</span></div>
                                <div className="flex justify-between"><span className="text-slate-400">低</span><span className="font-black text-green-600">{pred.prediction.predicted_low?.toLocaleString()}</span></div>
                            </div>
                        </div>
                        {pred5 && (
                            <div className={`p-3 rounded-xl border ${pred5.prediction.predicted_direction === 'up' ? 'bg-red-50 border-red-100' : pred5.prediction.predicted_direction === 'down' ? 'bg-green-50 border-green-100' : 'bg-slate-50 border-slate-100'}`}>
                                <div className="text-[9px] text-slate-500 font-bold uppercase mb-2">5日預測（週線）</div>
                                <div className={`text-xl font-black ${dirColor(pred5.prediction.predicted_direction)}`}>{dirEmoji(pred5.prediction.predicted_direction)} {dirLabel(pred5.prediction.predicted_direction)}</div>
                                <div className={`text-[11px] font-bold mt-1 ${dirColor(pred5.prediction.predicted_direction)}`}>{pred5.prediction.predicted_price?.toLocaleString()} ({pred5.prediction.predicted_change_pct > 0 ? '+' : ''}{pred5.prediction.predicted_change_pct?.toFixed(2)}%)</div>
                                <div className="text-[9px] text-slate-400 mt-1">信心 {pred5.prediction.confidence?.toFixed(1)}%</div>
                            </div>
                        )}
                    </div>

                    {/* 關鍵指標 */}
                    {pred.key_indicators && (
                        <div className="p-3 bg-indigo-50 rounded-xl border border-indigo-100">
                            <div className="text-[9px] text-indigo-600 font-bold mb-2 uppercase tracking-widest">🔬 18特徵快照</div>
                            <div className="grid grid-cols-4 gap-2">
                                {[['RSI', pred.key_indicators.rsi?.toFixed(1)], ['MACD', pred.key_indicators.macd?.toFixed(3)], ['VIX', pred.key_indicators.vix?.toFixed(1)], ['法人', (pred.key_indicators.inst_net > 0 ? '+' : '') + (pred.key_indicators.inst_net || 0).toLocaleString()]].map(([l, v]) => (
                                    <div key={l} className="text-center bg-white rounded-lg p-2">
                                        <div className="text-[8px] text-slate-400 font-bold">{l}</div>
                                        <div className="text-[11px] font-black text-indigo-700">{v ?? '-'}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 準確率追蹤 */}
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                        <div className="flex justify-between items-center mb-2">
                            <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest">📊 14日準確率</span>
                            <span className={`text-[9px] font-black px-2 py-0.5 rounded-full ${accuracy >= 80 ? 'bg-green-100 text-green-700' : accuracy >= 60 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-600'}`}>
                                {totalVerified > 0 ? `${accuracy}% (${correctCount}/${totalVerified})` : '尚無驗證'}
                            </span>
                        </div>
                        <div className="relative w-full bg-slate-200 rounded-full h-2">
                            <div className={`h-2 rounded-full ${accuracy >= 80 ? 'bg-green-500' : accuracy >= 60 ? 'bg-yellow-400' : 'bg-red-400'}`} style={{ width: `${Math.min(100, accuracy)}%` }} />
                            <div className="absolute top-0 bottom-0 border-l-2 border-dashed border-indigo-400" style={{ left: '80%' }} />
                        </div>
                        <div className="text-[9px] text-slate-400 mt-1">
                            模型：{pred.model?.source === 'lstm_v2' ? '✅ LSTM v2' : '⚠️ 技術指標備援→點「訓練LSTM」升級'}
                        </div>

                        {/* 近期記錄 */}
                        {history.length > 0 && (
                            <div className="mt-2 space-y-0.5">
                                {history.slice(0, 4).map((h, i) => (
                                    <div key={i} className="flex justify-between text-[9px] py-0.5 border-b border-slate-100 last:border-0">
                                        <span className="text-slate-400">{h.prediction_date}→{h.target_date}</span>
                                        <span className={dirColor(h.predicted_direction)}>{dirEmoji(h.predicted_direction)}</span>
                                        {h.is_verified
                                            ? <span className={`font-bold ${h.direction_correct ? 'text-green-600' : 'text-red-500'}`}>{h.direction_correct ? '✅' : '❌'}</span>
                                            : <span className="text-slate-300">⏳</span>}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="text-[9px] text-slate-400 text-center">💡 僅供參考，非投資建議。每日14:00自動預測，16:00驗證學習。</div>
                </>
            )}
        </div>
    );
};




const AnalysisItem = ({ label, value, desc, icon }) => (
    <div className="p-3 rounded-xl border border-slate-100 flex flex-col gap-1 bg-slate-50/50 hover:border-blue-100 transition-all">
        <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
                {icon}
                <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest">{label}</span>
            </div>
            <span className="text-[10px] font-black font-mono text-slate-800">{value}</span>
        </div>
        <p className="text-[8px] text-slate-500 font-bold leading-tight">{desc}</p>
    </div>
);

const Sparkle = ({ size, className }) => (
    <Activity size={size} className={className} />
);


const ChartComponent = ({ tech5m, priceData, highPoints, isWeakening, weakeningPercent }) => {
    return (
        <div className="relative h-[420px] bg-[#1a1a1a] rounded-b-[2.5rem] overflow-hidden group cursor-crosshair">
            {/* 網格背景 */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                {[...Array(8)].map((_, i) => (<div key={`h-${i}`} className="absolute w-full h-[1px] bg-[#2a2a2a]" style={{ top: `${(i + 1) * 12.5}%` }}></div>))}
                {[...Array(9)].map((_, i) => (<div key={`v-${i}`} className="absolute h-full w-[1px] bg-[#2a2a2a]" style={{ left: `${(i + 1) * 10}%` }}></div>))}
            </div>

            {(() => {
                if (!tech5m?.history || tech5m.history.length === 0) {
                    return <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs gap-2">
                        <div className="text-slate-400 text-sm font-bold">⏳ 等待 K 線數據...</div>
                        <div className="text-slate-600 text-[10px]">市場即將開盤或資料加載中</div>
                    </div>;
                }

                const history = tech5m.history;
                const isEarlySession = history.length < 5;

                // ✅ 永遠從當前 history K棒重新計算 MA（不依賴後端預算值）
                // 這樣不論資料來自 Fubon 或 yfinance，MA線永遠基於圖上相同的K棒，不會跳變
                const buildMAMap = (period) => {
                    return history.map((_, i) => {
                        if (i < period - 1) return null; // 前幾根不足以計算，留空
                        const slice = history.slice(i - period + 1, i + 1);
                        const sum = slice.reduce((acc, c) => acc + (Number(c.close) || 0), 0);
                        return sum / period;
                    });
                };

                const ma5Map  = buildMAMap(5);
                const ma10Map = buildMAMap(10);
                const ma20Map = buildMAMap(20);


                // 2. VWAP：優先用 API 回傳的正確盤中 VWAP（priceData.vwap），
                //    只在 API 無值（=0）且 K 線是今日 5 分線時才本地計算
                const apiVwap = priceData.vwap;  // 來自 comprehensive API（136.38 等正確值）
                let currentVWAP = apiVwap || 0;

                // 只有當 API 沒有 VWAP 且 K 線是今日盤中資料（數量足夠）才本地算
                if (!currentVWAP && history.length > 0) {
                    let cumVol = 0, cumPV = 0;
                    const vwapMap = history.map(h => {
                        cumVol += h.volume;
                        cumPV += (h.close * h.volume);
                        return cumVol === 0 ? h.close : cumPV / cumVol;
                    });
                    currentVWAP = vwapMap[vwapMap.length - 1] || priceData.price;
                }

                // 若 K 線是歷史日線（90 根以上），強制用 API VWAP 避免日線累積拉低
                if (history.length > 30 && apiVwap > 0) {
                    currentVWAP = apiVwap;
                }

                // 注意: currentVWAP 僅用於本元件內部繪圖，不需要寫回父元件

                const vwapMap = Array(history.length).fill(currentVWAP); // 用固定值繪圖

                const currentMA5 = ma5Map[ma5Map.length - 1];
                const currentMA10 = ma10Map[ma10Map.length - 1];
                const currentMA20 = ma20Map[ma20Map.length - 1];
                const currentPrice = priceData.price;

                // 這裡我們直接使用傳入的 highPoints 數據，反轉是為了讓 H3 (最新) 在最後繪製
                const highsToShow = highPoints.slice().reverse();

                // 4. ✅ 正確計算 Y 軸縮放（修正版：使用 10% padding 避免 K線擠壓）
                const kHighs = history.map(h => h.high);
                const kLows = history.map(h => h.low);
                const maValues = [...ma5Map, ...ma10Map, ...ma20Map, ...vwapMap].filter(v => v);
                const hpValues = highPoints.map(h => h.price).filter(p => p > 0);

                // 找出真實的最高價和最低價
                const allValues = [...kHighs, ...kLows, ...maValues, ...hpValues, currentPrice].filter(v => v && !isNaN(v));
                const rawMax = Math.max(...allValues);
                const rawMin = Math.min(...allValues);
                const rawRange = rawMax - rawMin || 1;

                // ✅ 增加頂部預留空間（Headroom）給標籤避讓
                const maxP = rawMax + rawRange * 0.15; // 頂部預留 15% 空間
                const minP = rawMin - rawRange * 0.05; // 底部預留 5% 空間
                const range = maxP - minP || 1;

                // Y 座標計算：SVG 的 Y軸是反的（0 在上，100 在下）
                const getPriceY = (p) => 100 - ((p - minP) / range) * 100;

                // 5. 計算 X 軸縮放 (每根 K 棒佔一個等寬槽，中心在槽中央，左右各留半槽)
                const totalPoints = Math.max(history.length, 20); // 至少顯示 20 根的寬度

                // ✅ 修正：getX(i) 回傳第 i 根 K 棒的「中心」X%
                // 公式: 每槽寬 = 100/totalPoints，中心在槽的正中間
                // getX(0) = 100/(totalPoints*2)，getX(N-1) = 100 - 100/(totalPoints*2)
                // → 第一根和最後一根都不會超出 0%~100% 邊界
                const slotWidth = 100 / totalPoints;
                const getX = (idx) => slotWidth * (idx + 0.5);
                const barWidthPct = slotWidth * 0.4;  // 40%：Yahoo 風格細窄 K 棒

                // 繪圖輔助: 畫線
                const drawPath = (values, color, width = "1.5", dash = "", filterId = "") => {
                    const points = values.map((v, i) => {
                        if (v === null || isNaN(v)) return null;
                        return `${getX(i)},${getPriceY(v)}`;
                    }).filter(p => p).join(' L ');

                    if (!points) return null;
                    return <path d={`M ${points}`} fill="none" stroke={color} strokeWidth={width} strokeDasharray={dash} strokeLinecap="round" strokeLinejoin="round" style={filterId ? { filter: `url(#${filterId})` } : {}} />;
                };

                // 判斷當前價格與 VWAP 關係決定顏色
                const isPriceAboveVwap = currentPrice >= currentVWAP;
                const priceLineColor = isPriceAboveVwap ? '#22c55e' : '#ef4444'; // 綠(多) / 紅(空)

                return (
                    <>
                        {/* 右側 Y 軸標籤 */}
                        <div className="absolute right-0 top-0 bottom-[25%] w-12 border-l border-[#2a2a2a] bg-[#1a1a1a]/90 backdrop-blur-sm z-20 flex flex-col justify-between py-4 px-1 select-none pointer-events-none">
                            {[...Array(6)].map((_, i) => {
                                const price = maxP - (i * range / 5);
                                return <span key={i} className="text-[9px] font-mono font-bold text-slate-500 text-right">{price.toFixed(1)}</span>;
                            })}
                        </div>

                        {/* 頂部資訊列 ─ 玻璃感設計 */}
                        <div className="absolute top-0 left-0 right-12 z-20 flex items-center gap-1 px-3 overflow-x-auto no-scrollbar"
                            style={{ height:'36px', background:'linear-gradient(90deg,rgba(10,10,20,0.97),rgba(18,18,32,0.95))', borderBottom:'1px solid rgba(255,255,255,0.07)', backdropFilter:'blur(8px)' }}>

                            {/* MA5 */}
                            <div className="flex items-center gap-1 px-2 py-0.5 rounded shrink-0" style={{background:'rgba(167,139,250,0.12)',border:'1px solid rgba(167,139,250,0.3)'}}>
                                <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{background:'#a78bfa'}}></span>
                                <span className="text-[9px] text-slate-500 font-mono">MA5</span>
                                <span className="text-[11px] text-[#a78bfa] font-bold font-mono">{currentMA5?.toFixed(2)||'--'}</span>
                            </div>
                            {/* MA10 */}
                            <div className="flex items-center gap-1 px-2 py-0.5 rounded shrink-0" style={{background:'rgba(96,165,250,0.12)',border:'1px solid rgba(96,165,250,0.3)'}}>
                                <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{background:'#60a5fa'}}></span>
                                <span className="text-[9px] text-slate-500 font-mono">MA10</span>
                                <span className="text-[11px] text-[#60a5fa] font-bold font-mono">{currentMA10?.toFixed(2)||'--'}</span>
                            </div>
                            {/* MA20 */}
                            <div className="flex items-center gap-1 px-2 py-0.5 rounded shrink-0" style={{background:'rgba(245,158,11,0.12)',border:'1px solid rgba(245,158,11,0.3)'}}>
                                <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{background:'#f59e0b'}}></span>
                                <span className="text-[9px] text-slate-500 font-mono">MA20</span>
                                <span className="text-[11px] text-[#f59e0b] font-bold font-mono">{currentMA20?.toFixed(2)||'--'}</span>
                            </div>
                            {/* VWAP */}
                            <div className="flex items-center gap-1 px-2 py-0.5 rounded shrink-0" style={{background:'rgba(251,191,36,0.10)',border:'1px solid rgba(251,191,36,0.25)'}}>
                                <span className="text-[9px] text-slate-500 font-mono">VWAP</span>
                                <span className="text-[11px] text-[#fbbf24] font-bold font-mono">{currentVWAP?.toFixed(2)}</span>
                            </div>

                            {/* 高點 H1/H2/H3 */}
                            <div className="flex items-center gap-1 ml-1 pl-2 border-l border-slate-700/50 shrink-0">
                                {highPoints.filter(hp=>hp.price>0).map((hp,idx)=>{
                                    const isLatest = idx===highPoints.filter(hp=>hp.price>0).length-1;
                                    const hl = isLatest&&isWeakening;
                                    return <span key={hp.id} className={`px-1.5 py-0.5 rounded text-[9px] font-bold font-mono ${hl?'bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse':'bg-slate-700/60 text-slate-300'}`}>{hp.id}:{hp.price.toFixed(2)}</span>;
                                })}
                            </div>

                            {/* 開盤提示 */}
                            {isEarlySession&&(
                                <div className="ml-auto shrink-0 px-2 py-0.5 bg-blue-500/20 border border-blue-500/40 rounded text-[9px] text-blue-400 font-bold flex items-center gap-1 animate-pulse">
                                    <span>●</span>{history.length}根
                                </div>
                            )}
                        </div>

                        {/* 主圖示區 */}
                        <div className="absolute inset-0 right-12 bottom-[25%]" style={{top:'36px'}}>
                            <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                                {/* H1 / H2 / H3 垂直虛線線與圓點 (SVG 部分僅保留虛線) */}
                                {highPoints.map((hp, i) => {
                                    const matchIdx = history.findIndex(h => (h.date||'').includes(hp.time));
                                    if (matchIdx < 0) return null;
                                    const xPos = getX(matchIdx);
                                    const yPos = getPriceY(hp.price);
                                    const palette = ['#64748b', '#3b82f6', '#ef4444'];
                                    const isLatest = i === highPoints.length - 1;
                                    const col = (isLatest && isWeakening) ? '#ef4444' : (palette[i] ?? '#94a3b8');
                                    return (
                                        <line key={`vguide-${hp.id}`}
                                            x1={xPos} y1={0} x2={xPos} y2={yPos}
                                            stroke={col} strokeWidth={0.3}
                                            strokeDasharray="2,2" opacity={0.6}
                                        />
                                    );
                                })}

                                <defs>
                                    <filter id="glow-white" x="-30%" y="-30%" width="160%" height="160%">
                                        <feGaussianBlur stdDeviation="2.5" result="blur" />
                                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                                    </filter>
                                    <filter id="glow-blue" x="-30%" y="-30%" width="160%" height="160%">
                                        <feGaussianBlur stdDeviation="2.5" result="blur" />
                                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                                    </filter>
                                    <filter id="glow-yellow" x="-30%" y="-30%" width="160%" height="160%">
                                        <feGaussianBlur stdDeviation="2.5" result="blur" />
                                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                                    </filter>
                                </defs>

                                {/* ① K 棒先畫（底層）—— SVG 後繪的元素會蓋在前面，
                                     所以 K 棒放前面，MA 線放後面才能顯示在上方 */}
                                {history.map((h, i) => {
                                    const x      = getX(i);
                                    const barX   = x - barWidthPct / 2;
                                    const yOpen  = getPriceY(h.open);
                                    const yClose = getPriceY(h.close);
                                    const yHigh  = getPriceY(h.high);
                                    const yLow   = getPriceY(h.low);
                                    const isLive = h._live;
                                    const isBull = h.close >= h.open; // 收>=開 = 漲（台股紅）
                                    const color  = isBull ? '#ef4444' : '#22c55e';

                                    const yBodyTop = Math.min(yOpen, yClose);
                                    const yBodyBot = Math.max(yOpen, yClose);
                                    const bodyH    = Math.max(yBodyBot - yBodyTop, 0.2); // 最小 0.2 確保可見
                                    const wickW    = 0.12; // 影線寬度（viewBox 單位，≈1px）

                                    return (
                                        <g key={i} opacity={isLive ? 0.65 : 1}>
                                            {/* 上下影線：用 rect 精確控制寬度，避免 line+非均勻縮放的問題 */}
                                            <rect x={x - wickW/2} y={yHigh}
                                                width={wickW} height={Math.max(yLow - yHigh, 0.1)}
                                                fill={color} />
                                            {/* 實體 */}
                                            <rect x={barX} y={yBodyTop}
                                                width={barWidthPct} height={bodyH}
                                                fill={color} />
                                        </g>
                                    );
                                })}

                                {/* VWAP 虛線（標籤由 HTML div 處理）*/}
                                {currentVWAP > 0 && (
                                    <line
                                        x1={0} y1={getPriceY(currentVWAP)}
                                        x2={100} y2={getPriceY(currentVWAP)}
                                        stroke="#fbbf24" strokeWidth={0.4}
                                        strokeDasharray="2,1" opacity={0.85}
                                    />
                                )}

                                {/* ③ MA 線最後畫（頂層）—— 用 polyline 確保完整連線 */}
                                {(() => {
                                    const drawPolyline = (vals, color, width, dash) => {
                                        const pts = vals
                                            .map((v, i) => (v != null && !isNaN(v))
                                                ? `${getX(i).toFixed(2)},${getPriceY(v).toFixed(2)}`
                                                : null)
                                            .filter(Boolean)
                                            .join(' ');
                                        if (!pts) return null;
                                        return <polyline key={color} points={pts} fill="none"
                                            stroke={color} strokeWidth={width}
                                            strokeDasharray={dash} strokeLinecap="round"
                                            strokeLinejoin="round" opacity="0.95" />;
                                    };
                                    return (<>
                                        {/* MA 繪製順序：MA20(最底) → MA10 → MA5(最頂)
                                            後畫的覆蓋前畫，MA5 永遠顯示在最上方 */}
                                        {drawPolyline(ma20Map, "#f59e0b", 0.45, "1.8,0.9")}
                                        {drawPolyline(ma10Map, "#60a5fa", 0.55, "")}
                                        {drawPolyline(ma5Map,  "#c084fc", 0.7,  "")}
                                    </>);
                                })()}


                                {/* ✅ 當前價格線（加強版：更粗、更亮、帶陰影） */}
                                {currentPrice > 0 && (
                                    <>
                                        <line
                                            x1={0}
                                            y1={getPriceY(currentPrice)}
                                            x2={100}
                                            y2={getPriceY(currentPrice)}
                                            stroke={priceLineColor}
                                            strokeWidth="0.6"
                                            strokeDasharray="2,1"
                                            opacity="0.9"
                                        />
                                    </>
                                )}
                            </svg>

                            {/* ✅ 當前價格標籤 */}
                            {currentPrice > 0 && (
                                <div
                                    className="absolute left-0 px-3 py-1 text-white text-xs font-bold rounded-r z-30 shadow-lg flex items-center gap-1.5 font-mono"
                                    style={{ top:`calc(${getPriceY(currentPrice)}% - 12px)`, backgroundColor:priceLineColor, boxShadow:`0 0 10px ${priceLineColor}80` }}
                                >
                                    <span className="animate-pulse">●</span>
                                    {currentPrice.toFixed(2)}
                                </div>
                            )}

                            {/* VWAP 標籤（左側固定，仿股價樣式） */}
                            {currentVWAP > 0 && (
                                <div className="absolute left-0 px-2 py-0.5 text-black text-[10px] font-bold rounded-r z-30 shadow-lg flex items-center font-mono"
                                    style={{
                                        top: `calc(${getPriceY(currentVWAP)}% - 10px)`,
                                        backgroundColor: '#fbbf24',
                                        boxShadow: '0 0 8px rgba(251,191,36,0.5)'
                                    }}>
                                    VWAP {currentVWAP.toFixed(2)}
                                </div>
                            )}

                        {/* H2/H1/H3 完美標記（HTML 渲染：具備自動避讓邏輯） */}
                        {(() => {
                            // 預處理高點座標與避讓層級
                            const pointsWithPos = highPoints.map(hp => {
                                const idx = history.findIndex(h => (h.date||'').includes(hp.time));
                                return { ...hp, xPct: idx >= 0 ? getX(idx) : -1 };
                            }).filter(p => p.xPct >= 0);

                            // 避讓邏輯：若水平距離太近，則增加層級偏移
                            const levels = [];
                            pointsWithPos.forEach((p, i) => {
                                let level = 0;
                                for (let j = 0; j < i; j++) {
                                    const prev = pointsWithPos[j];
                                    if (Math.abs(p.xPct - prev.xPct) < 10) { // 10% 為重疊閥值
                                        level = Math.max(level, levels[j] + 1);
                                    }
                                }
                                levels[i] = level;
                            });

                            return pointsWithPos.map((hp, i) => {
                                const xPct = hp.xPct;
                                const yPct = getPriceY(hp.price);
                                const level = levels[i];
                                const topOffset = 12 + (level * 25); // 從 top: 12px 開始，確保不與頂部資訊列重疊
                                
                                const palette = ['#64748b', '#3b82f6', '#ef4444'];
                                const isLatest = i === highPoints.length - 1;
                                const col = (isLatest && isWeakening) ? '#ef4444' : (palette[i] ?? '#94a3b8');

                                return (
                                    <React.Fragment key={hp.id}>
                                        {/* 垂直導引線：從標籤底部 (topOffset + 24) 連到圓點 (yPct) */}
                                        <div 
                                            className="absolute w-px border-l border-dashed z-10 transition-all duration-300"
                                            style={{
                                                left: `${xPct}%`,
                                                top: `${topOffset + 24}px`, 
                                                height: `calc(${yPct}% - ${topOffset + 24}px)`,
                                                borderColor: col,
                                                opacity: 0.5
                                            }}
                                        />

                                        {/* 完美高光圓點 */}
                                        <div 
                                            className={`absolute transform -translate-x-1/2 -translate-y-1/2 w-3 h-3 rounded-full z-20 border border-black/30 shadow-sm ${isLatest && isWeakening ? 'animate-pulse' : ''}`}
                                            style={{
                                                left: `${xPct}%`,
                                                top: `${yPct}%`,
                                                background: `radial-gradient(circle at 30% 30%, white 0%, ${col} 45%, ${col} 100%)`,
                                                boxShadow: `0 0 10px ${col}aa`
                                            }}
                                        />

                                        {/* 頂部 HTML 標籤（具備「向下」避讓層級） */}
                                        <div
                                            className="absolute transform -translate-x-1/2 px-2 py-0.5 text-white text-[10px] font-bold rounded shadow-xl z-40 font-mono whitespace-nowrap transition-all duration-300"
                                            style={{
                                                left: `${xPct}%`,
                                                top: `${topOffset}px`,
                                                backgroundColor: col,
                                                boxShadow: `0 2px 6px rgba(0,0,0,0.5), 0 0 4px ${col}80`
                                            }}
                                        >
                                            {hp.id} {hp.price.toFixed(2)}
                                        </div>
                                    </React.Fragment>
                                );
                            });
                        })()}

                        </div>

                        {/* 底部成交量 (25% 高度, 紅綠柱, 爆量標示) */}
                        <div className="absolute left-0 right-12 bottom-0 h-[25%] border-t border-[#2a2a2a] bg-[#1a1a1a]">
                            <svg className="w-full h-[calc(100%-18px)]" preserveAspectRatio="none">
                                {(() => {
                                    const maxVol = Math.max(...history.map(h => h.volume));
                                    const avgVol = history.reduce((a, b) => a + b.volume, 0) / history.length;

                                    return history.map((h, i) => {
                                        const x = getX(i);
                                        const barX = x - (barWidthPct / 2);
                                        const hPct = maxVol ? (h.volume / maxVol) * 88 : 0;
                                        const color = h.close >= h.open ? '#ef4444' : '#22c55e';
                                        const isBurst = h.volume > avgVol * 2;

                                        return (
                                            <g key={i}>
                                                <rect x={`${barX}%`} y={`${100 - hPct}%`} width={`${barWidthPct}%`} height={`${hPct}%`} fill={color} opacity="0.8" />
                                                {isBurst && (
                                                    <text x={`${x}%`} y={`${100 - hPct - 5}%`} fontSize="8" textAnchor="middle">🔥</text>
                                                )}
                                            </g>
                                        );
                                    });
                                })()}
                            </svg>
                            {/* VOL 標籤 + 時間軸（整合在成交量區底部）*/}
                            <div className="absolute top-0.5 left-2 text-[9px] text-slate-500 font-mono font-bold">VOL</div>
                            <div className="absolute bottom-0 left-0 right-0 px-2 flex justify-between pointer-events-none select-none border-t border-[#2a2a2a]">
                                <span className="text-[9px] font-mono font-bold text-slate-500">{history[0]?.date?.split('T')[1]?.slice(0, 5)}</span>
                                <span className="text-[9px] font-mono font-bold text-slate-500">{history[Math.floor(history.length / 4)]?.date?.split('T')[1]?.slice(0, 5)}</span>
                                <span className="text-[9px] font-mono font-bold text-slate-500">{history[Math.floor(history.length / 2)]?.date?.split('T')[1]?.slice(0, 5)}</span>
                                <span className="text-[9px] font-mono font-bold text-slate-500">{history[Math.floor(history.length * 3 / 4)]?.date?.split('T')[1]?.slice(0, 5)}</span>
                                <span className="text-[9px] font-mono font-bold text-slate-500">{history[history.length - 1]?.date?.split('T')[1]?.slice(0, 5)}</span>
                            </div>
                        </div>
                    </>
                );
            })()}
        </div>
    );
};

// Helper to robustly parse UTC dates (Global Scope)
const parseDate = (dateStr) => {
    if (!dateStr) return null;
    try {
        if (typeof dateStr === 'string' && dateStr.includes('T') && !dateStr.endsWith('Z') && !dateStr.includes('+')) {
            // Heuristic for mixed timezone data:
            // - If hour is 00-07, it's likely UTC (08:00 - 15:00 TW Time) -> Append 'Z'
            // - If hour is 08+, it's likely already Local Time (Naive) -> Don't append 'Z'
            const timePart = dateStr.split('T')[1];
            const hour = timePart ? parseInt(timePart.split(':')[0], 10) : 0;

            if (hour >= 0 && hour <= 7) {
                return new Date(dateStr + 'Z');
            }
        }
        return new Date(dateStr);
    } catch (e) {
        return new Date();
    }
};

// 🆕 Portfolio Overview Modal Component (Integrated at end of file)
const PortfolioOverview = ({ onClose }) => {
    const [positions, setPositions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [summary, setSummary] = useState({
        todayRealized: 0,
        previousRealized: 0,
        totalRealized: 0,
        todayCount: 0,
        previousCount: 0
    });

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/portfolio/positions`);
            const data = await res.json();

            // Normalize and Sort data
            const allPositions = data.sort((a, b) => new Date(b.entry_date) - new Date(a.entry_date));
            setPositions(allPositions);

            // Calculate Summary
            const today = new Date().toLocaleDateString();
            let todayP = 0, prevP = 0, todayC = 0, prevC = 0;

            allPositions.forEach(p => {
                if (p.status !== 'open' && p.exit_date) {
                    // Remove exitDate variable as it was using raw string
                    const profit = p.realized_profit || 0;
                    // Use parseDate to get correct local date
                    const pDate = p.exit_date ? parseDate(p.exit_date) : null;
                    if (pDate && pDate.toLocaleDateString() === today) {
                        todayP += profit;
                        todayC++;
                    } else {
                        prevP += profit;
                        prevC++;
                    }
                }
            });

            setSummary({
                todayRealized: todayP,
                previousRealized: prevP,
                totalRealized: todayP + prevP,
                todayCount: todayC,
                previousCount: prevC
            });

        } catch (e) {
            console.error("Failed to fetch portfolio:", e);
        } finally {
            setLoading(false);
        }
    };

    // Helper to check if date is today
    const isToday = (dateStr) => {
        if (!dateStr) return false;
        return parseDate(dateStr).toLocaleDateString() === new Date().toLocaleDateString();
    };

    // Filter Lists
    const openPositions = positions.filter(p => p.status === 'open');

    // Get ALL closed trades for today (including 'target_hit', 'stopped', AND 'closed')
    const todayClosed = positions.filter(p => p.status !== 'open' && p.exit_date && isToday(p.exit_date));

    // Group by Profit/Loss to ensure numbers match summary
    const todayWins = todayClosed.filter(p => p.realized_profit > 0);
    const todayLosses = todayClosed.filter(p => p.realized_profit <= 0);

    // Calculate Subtotals for headers
    const todayWinAmount = todayWins.reduce((sum, p) => sum + (p.realized_profit || 0), 0);
    const todayLossAmount = todayLosses.reduce((sum, p) => sum + (p.realized_profit || 0), 0);


    const formatCurrency = (val) => val?.toLocaleString('zh-TW', { style: 'currency', currency: 'TWD', minimumFractionDigits: 0 });
    const formatPercent = (val) => `${(val || 0) > 0 ? '+' : ''}${(val || 0).toFixed(2)}%`;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-white rounded-[2rem] shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-slate-800 text-white rounded-xl shadow-lg shadow-slate-200">
                            <Wallet size={24} />
                        </div>
                        <div>
                            <h2 className="text-xl font-black text-slate-800 uppercase tracking-widest">投資組合總覽 (Portfolio)</h2>
                            <div className="text-xs text-slate-400 font-bold uppercase tracking-wider">今日損益與持倉明細</div>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-400 hover:text-slate-600">
                        <X size={24} />
                    </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-[#F8FAFC]">
                    {loading ? (
                        <div className="flex justify-center py-20"><Loader2 className="animate-spin text-slate-300" size={48} /></div>
                    ) : (
                        <>
                            {/* 1. Summary Cards */}
                            <div className="grid grid-cols-3 gap-6">
                                <SummaryCard title="今日已實現損益 (Today)" value={summary.todayRealized} count={summary.todayCount} color={summary.todayRealized >= 0 ? 'text-red-500' : 'text-green-600'} icon={<Activity size={18} />} />
                                <SummaryCard title="歷史已實現損益 (Previous)" value={summary.previousRealized} count={summary.previousCount} color={summary.previousRealized >= 0 ? 'text-red-500' : 'text-green-600'} icon={<History size={18} />} />
                                <SummaryCard title="總計已實現損益 (Total)" value={summary.totalRealized} count={summary.todayCount + summary.previousCount} color={summary.totalRealized >= 0 ? 'text-red-600' : 'text-green-600'} icon={<Database size={18} />} isTotal />
                            </div>

                            {/* 2. Lists Grid */}
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                {/* Holdings */}
                                <div className="space-y-4">
                                    <h3 className="flex items-center gap-2 text-sm font-black text-slate-700 uppercase tracking-widest">
                                        <Briefcase size={16} className="text-slate-400" /> 持股倉 (Holdings)
                                        <span className="bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full text-[10px]">{openPositions.length}</span>
                                    </h3>
                                    <div className="space-y-3">
                                        {openPositions.length === 0 ? <EmptyState label="無持倉" /> : openPositions.map(p => (
                                            <PositionCard key={p.id} data={p} type="open" />
                                        ))}
                                    </div>
                                </div>

                                {/* Target Reached aka Winners */}
                                <div className="space-y-4">
                                    <h3 className="flex items-center gap-2 text-sm font-black text-slate-700 uppercase tracking-widest">
                                        <CheckCircle2 size={16} className="text-red-500" /> 今日獲利 (Winners)
                                        <span className="bg-red-50 text-red-500 px-2 py-0.5 rounded-full text-[10px]">{todayWins.length}</span>
                                        <span className="text-[10px] font-mono text-red-500 font-bold ml-auto">{todayWinAmount > 0 ? '+' : ''}{todayWinAmount.toLocaleString()}</span>
                                    </h3>
                                    <div className="space-y-3">
                                        {todayWins.length === 0 ? <EmptyState label="今日無獲利" /> : todayWins.map(p => (
                                            <PositionCard key={p.id} data={p} type="win" />
                                        ))}
                                    </div>
                                </div>

                                {/* Stop Loss aka Losers */}
                                <div className="space-y-4">
                                    <h3 className="flex items-center gap-2 text-sm font-black text-slate-700 uppercase tracking-widest">
                                        <XCircle size={16} className="text-green-600" /> 今日虧損 (Losers)
                                        <span className="bg-green-50 text-green-600 px-2 py-0.5 rounded-full text-[10px]">{todayLosses.length}</span>
                                        <span className="text-[10px] font-mono text-green-600 font-bold ml-auto">{todayLossAmount.toLocaleString()}</span>
                                    </h3>
                                    <div className="space-y-3">
                                        {todayLosses.length === 0 ? <EmptyState label="今日無虧損" /> : todayLosses.map(p => (
                                            <PositionCard key={p.id} data={p} type="loss" />
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

const SummaryCard = ({ title, value, count, color, icon, isTotal }) => (
    <div className={`p-6 rounded-2xl border ${isTotal ? 'bg-slate-900 text-white border-slate-700' : 'bg-white border-slate-100'} shadow-sm relative overflow-hidden`}>
        <div className="flex justify-between items-start z-10 relative">
            <div>
                <div className={`text-[10px] font-black uppercase tracking-widest mb-2 flex items-center gap-2 ${isTotal ? 'text-slate-400' : 'text-slate-400'}`}>
                    {icon} {title}
                </div>
                <div className={`text-3xl font-mono font-black tracking-tighter ${isTotal ? (value >= 0 ? 'text-red-400' : 'text-green-400') : color}`}>
                    {value?.toLocaleString('zh-TW', { style: 'currency', currency: 'TWD', minimumFractionDigits: 0 })}
                </div>
                <div className={`text-[9px] font-mono mt-2 ${isTotal ? 'text-slate-500' : 'text-slate-400'}`}>
                    Trades Count: {count}
                </div>
            </div>
        </div>
    </div>
);

const PositionCard = ({ data, type }) => {
    const isWin = type === 'win' || (type === 'open' && data.unrealized_profit > 0);
    const profit = type === 'open' ? data.unrealized_profit : data.realized_profit;
    const percent = type === 'open' ? data.unrealized_profit_percent : data.realized_profit_percent;
    const profitColor = profit > 0 ? 'text-red-500' : profit < 0 ? 'text-green-600' : 'text-slate-500';

    // Status Label Logic
    const getStatusLabel = () => {
        if (type === 'open') return '持有中';
        if (data.status === 'target_hit') return 'TARGET REA';
        if (data.status === 'stopped') return 'STOP LOSS';
        return 'MANUAL'; // For 'closed' status
    };

    return (
        <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-2">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-black text-slate-800">{data.stock_name}</span>
                        <span className="text-[10px] font-mono text-slate-400">{data.symbol}</span>
                    </div>

                    {/* Buy Time */}
                    <div className="text-[10px] text-slate-500 font-medium flex items-center gap-1.5">
                        <span className="text-xs bg-slate-100 text-slate-500 px-1 rounded">買進</span>
                        <span className="font-mono">{parseDate(data.entry_date).toLocaleDateString([], { month: '2-digit', day: '2-digit' })} {parseDate(data.entry_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        <span className="font-mono font-bold text-slate-700">@ {data.entry_price}</span>
                    </div>

                    {/* Sell Time (if closed) */}
                    {type !== 'open' && data.exit_date && (
                        <div className="text-[10px] text-slate-500 font-medium flex items-center gap-1.5 mt-1">
                            <span className="text-xs bg-slate-100 text-slate-500 px-1 rounded">賣出</span>
                            <span className="font-mono">{parseDate(data.exit_date).toLocaleDateString([], { month: '2-digit', day: '2-digit' })} {parseDate(data.exit_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                            <span className="font-mono font-bold text-slate-700">@ {data.exit_price}</span>
                        </div>
                    )}
                </div>
                <div className={`text-right ${profitColor}`}>
                    <div className="text-sm font-black font-mono">{profit?.toLocaleString()}</div>
                    <div className="text-[10px] font-bold">{percent > 0 ? '+' : ''}{percent}%</div>
                </div>
            </div>

            <div className="pt-2 mt-2 border-t border-slate-50 flex justify-between items-center text-[9px]">
                <span className={`uppercase tracking-widest px-1.5 py-0.5 rounded font-bold ${type === 'win' ? 'bg-red-50 text-red-500' : type === 'loss' ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-500'}`}>
                    {getStatusLabel()}
                </span>
            </div>
        </div>
    );
};

const EmptyState = ({ label }) => (
    <div className="h-24 rounded-xl border border-dashed border-slate-200 flex items-center justify-center text-slate-300 text-xs font-bold uppercase tracking-widest">
        {label}
    </div>
);

export default ExpertSniper;

// 🆕 新增：國際政經總匯面板 (International Macro Highlights)
const InternationalMacroPanel = ({ data }) => {
    if (!data) return null;
    
    const sentiment = data.sentiment || "中性 🟡";
    const summary = data.summary || "暫無即時摘要";
    const recentHeadlines = data.recent_headlines || [];
    const topEvents = data.top_events || [];
    
    const isAlert = sentiment.includes('高度警戒') || sentiment.includes('恐慌');
    const isPositive = sentiment.includes('樂觀');

    return (
        <div className="bg-white rounded-[2rem] border border-slate-200 overflow-hidden shadow-sm mt-6">
            <div className="px-7 py-5 bg-slate-50/50 border-b border-slate-100 flex justify-between items-center">
                <h3 className="text-xs font-black text-slate-800 flex items-center gap-3 uppercase tracking-widest">
                    <span className="p-2 bg-indigo-600 text-white rounded-xl shadow-lg ring-4 ring-indigo-50">
                        <Globe size={12} />
                    </span>
                    國際政經總匯 (Global Macro)
                </h3>
                <div className={`px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest border ${isAlert ? 'bg-red-50 text-red-500 border-red-200 animate-pulse' : isPositive ? 'bg-green-50 text-green-600 border-green-200' : 'bg-slate-100 text-slate-500 border-slate-200'}`}>
                    市場情緒：{sentiment}
                </div>
            </div>
            
            <div className="p-8 space-y-6">
                {/* 1. 精要摘要 */}
                <div className={`p-5 rounded-2xl border ${isAlert ? 'bg-red-50/30 border-red-100' : 'bg-slate-50 border-slate-100'}`}>
                    <div className="text-[10px] text-slate-400 font-black uppercase mb-2 tracking-widest leading-none">🌍 國際觀點摘要</div>
                    <p className="text-sm text-slate-700 font-bold leading-relaxed whitespace-pre-line">{summary}</p>
                    {data.action_advice && (
                        <div className="mt-3 pt-3 border-t border-slate-200/50 flex gap-2">
                             <span className="text-[10px] bg-white px-2 py-0.5 rounded border border-slate-100 font-black text-indigo-500 shrink-0">建議</span>
                             <span className="text-[11px] text-slate-500 font-medium italic">{data.action_advice}</span>
                        </div>
                    )}
                </div>

                {/* 2. 關鍵事件列表 */}
                {topEvents.length > 0 && (
                    <div className="space-y-3">
                        <div className="text-[10px] text-slate-400 font-black uppercase tracking-widest leading-none">● 關鍵精選頭條 (Top Events)</div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {topEvents.map((ev, i) => (
                                <a key={i} href={ev.link} target="_blank" rel="noreferrer" className="flex items-center gap-3 p-3 bg-white border border-slate-100 rounded-xl hover:shadow-md transition-all group">
                                    <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${ev.impact === 'negative' ? 'bg-red-500' : 'bg-indigo-500'}`} />
                                    <span className="text-xs text-slate-600 font-bold group-hover:text-indigo-600 group-hover:underline truncate">{ev.title}</span>
                                    <span className="ml-auto text-[8px] bg-slate-50 text-slate-400 px-1.5 py-0.5 rounded uppercase font-black">{ev.source}</span>
                                </a>
                            ))}
                        </div>
                    </div>
                )}

                {/* 3. 最近頭條摘要瀑布 */}
                <div className="space-y-3">
                    <div className="text-[10px] text-slate-400 font-black uppercase tracking-widest leading-none">● 最新國際金融動態庫 (Recent Headlines)</div>
                    <div className="max-h-60 overflow-y-auto pr-2 space-y-2 no-scrollbar">
                        {recentHeadlines.map((h, i) => (
                            <div key={i} className="flex flex-col p-3 bg-slate-50/50 border border-transparent hover:border-slate-200 rounded-xl transition-all">
                                <div className="flex justify-between items-center mb-1">
                                    <span className={`text-[8px] font-black uppercase px-1.5 py-0.5 rounded ${h.is_foreign ? 'bg-indigo-50 text-indigo-500' : 'bg-slate-200 text-slate-500'}`}>{h.source}</span>
                                    {h.is_foreign && <span className="text-[8px] text-slate-400 font-mono">EN translated</span>}
                                </div>
                                <span className="text-xs text-slate-700 font-bold leading-tight">{h.title}</span>
                                {h.original_title && <span className="text-[9px] text-slate-400 mt-1 italic line-clamp-1">{h.original_title}</span>}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
