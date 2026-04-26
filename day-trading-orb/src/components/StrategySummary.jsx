
import React, { useState, useEffect } from 'react';

const StrategySummary = ({ marketData, levels, orbData, mopsData, vixData, symbol, chipData, highPoints }) => {
    const [epsData, setEpsData] = useState(null);
    const [kgiData, setKgiData] = useState(null);
    const [showChipDetail, setShowChipDetail] = useState(false);
    const [marginData, setMarginData] = useState(null);   // 融資融券

    useEffect(() => {
        if (!symbol || symbol.length < 4) {
            setEpsData(null);
            setKgiData(null);
            setMarginData(null);   // ← 切換股票時清空
            return;
        }

        // 先清空，避免切換時短暫顯示舊資料
        setEpsData(null);
        setKgiData(null);
        setMarginData(null);

        const API_BASE = `http://${window.location.hostname}:8000`;

        fetch(`${API_BASE}/api/market/eps-evaluation/${symbol}`)
            .then(res => res.json())
            .then(json => { if (json.success) setEpsData(json.data); })
            .catch(() => {});

        fetch(`${API_BASE}/api/mops/kgi-research/${symbol}`)
            .then(res => res.json())
            .then(json => { if (json.status === 'success') setKgiData(json.data); })
            .catch(() => {});

        // ── 融資融券 ──
        fetch(`${API_BASE}/api/institutional/margin-trading/${symbol}`)
            .then(res => res.json())
            .then(json => {
                if (json.success && json.data && json.data.length > 0) {
                    // 過濾非平日資料，取最近一筆
                    const weekdayData = json.data.filter(d => {
                        try {
                            const day = new Date(d.date).getDay();
                            return day >= 1 && day <= 5;
                        } catch { return true; }
                    });
                    setMarginData(weekdayData[0] || json.data[0]);
                }
            })
            .catch(() => {});
    }, [symbol]);

    if (!marketData || !marketData.current) return null;

    const currentPrice = marketData.current;
    const prevHigh = marketData.prevHigh || 0;
    const prevLow = marketData.prevLow || 0;
    const hasLevels = levels && levels.length > 0;

    // ── 只取「距離當前價格 15% 以內」的有效支撐壓力 ──
    const MAX_DIST = 0.15;
    const resistanceLevels = hasLevels
        ? levels
            .filter(l => l.type === 'resistance' && l.price > currentPrice && (l.price - currentPrice) / currentPrice < MAX_DIST)
            .sort((a, b) => a.price - b.price)
        : [];
    const supportLevels = hasLevels
        ? levels
            .filter(l => l.type === 'support' && l.price < currentPrice && (currentPrice - l.price) / currentPrice < MAX_DIST)
            .sort((a, b) => b.price - a.price)
        : [];

    const nearestRes = resistanceLevels[0];
    const nearestSup = supportLevels[0];
    const strongSup = supportLevels.find(l => (l.resonance || 0) >= 2) || nearestSup;

    // 備援：昨高昨低（也限距離 15%）
    const usesPrevHigh = !nearestRes && prevHigh > currentPrice && (prevHigh - currentPrice) / currentPrice < MAX_DIST;
    const usesPrevLow = !nearestSup && prevLow > 0 && prevLow < currentPrice && (currentPrice - prevLow) / currentPrice < MAX_DIST;
    const fallbackRes = usesPrevHigh ? { price: prevHigh, label: '昨高' } : nearestRes ? { ...nearestRes, label: '壓力' } : null;
    const fallbackSup = usesPrevLow ? { price: prevLow, label: '昨低' } : nearestSup ? { ...nearestSup, label: '支撐' } : null;

    // 計算漲跌幅供判斷
    const chgPct = prevHigh > 0 ? (currentPrice - prevHigh) / prevHigh * 100 : 0;

    // ── 1. 現況 ──
    let statusText = '區間震盪整理';
    let statusColor = 'text-gray-700';

    if (fallbackRes && (fallbackRes.price - currentPrice) / currentPrice < 0.008) {
        statusText = `逼近${fallbackRes.label} ${fallbackRes.price.toFixed(1)}，多空關鍵`;
        statusColor = 'text-orange-600 font-bold';
    } else if (fallbackSup && (currentPrice - fallbackSup.price) / currentPrice < 0.008) {
        statusText = `回測${fallbackSup.label} ${fallbackSup.price.toFixed(1)}，守穩注意`;
        statusColor = 'text-blue-600 font-bold';
    } else if (orbData?.high && currentPrice > orbData.high && (currentPrice - orbData.high) / orbData.high < 0.12) {
        statusText = 'ORB 突破後持強，趨勢向上';
        statusColor = 'text-red-600 font-bold';
    } else if (prevHigh > 0 && currentPrice > prevHigh) {
        statusText = `突破昨高 ${prevHigh.toFixed(1)}，強勢格局`;
        statusColor = 'text-red-600 font-bold';
    } else if (prevLow > 0 && currentPrice < prevLow) {
        statusText = `跌破昨低 ${prevLow.toFixed(1)}，留意風險`;
        statusColor = 'text-green-700 font-bold';
    } else if (prevHigh > 0) {
        const pct = ((currentPrice - prevHigh) / prevHigh * 100).toFixed(1);
        statusText = `相對昨高 ${pct}%，${parseFloat(pct) > -3 ? '整理偏強' : '整理觀望'}`;
        statusColor = parseFloat(pct) > -3 ? 'text-red-500' : 'text-gray-600';
    }

    // ── 判斷整體多空狀態 (Trend) ──
    let trendName = '中性震盪';
    let trendBg = 'bg-slate-100 text-slate-600 border-slate-200';
    let trendIcon = '⚖️';

    const midPoint = (prevHigh > 0 && prevLow > 0) ? (prevHigh + prevLow) / 2 : 0;

    if (prevHigh > 0 && currentPrice > prevHigh) {
        trendName = '極悍多頭 (軋空/創高)';
        trendBg = 'bg-red-500 text-white border-red-600 shadow-sm';
        trendIcon = '🚀';
    } else if (orbData?.high > 0 && currentPrice > orbData.high) {
        trendName = '強勢多頭 (突破ORB)';
        trendBg = 'bg-red-100 text-red-700 border-red-200';
        trendIcon = '📈';
    } else if (prevLow > 0 && currentPrice < prevLow) {
        trendName = '極弱空頭 (破底/殺盤)';
        trendBg = 'bg-green-600 text-white border-green-700 shadow-sm';
        trendIcon = '📉';
    } else if (orbData?.low > 0 && currentPrice < orbData.low) {
        trendName = '弱勢空頭 (跌破ORB)';
        trendBg = 'bg-green-100 text-green-700 border-green-200';
        trendIcon = '⚠️';
    } else if (midPoint > 0 && currentPrice >= midPoint) {
        trendName = '偏多整理';
        trendBg = 'bg-rose-50 text-rose-600 border-rose-100';
        trendIcon = '↗️';
    } else if (midPoint > 0 && currentPrice < midPoint) {
        trendName = '偏空整理';
        trendBg = 'bg-emerald-50 text-emerald-600 border-emerald-100';
        trendIcon = '↘️';
    }

    // ── 2. 短線計畫 ──
    let shortTermPlan = '觀察量能與方向，等待訊號確認';
    if (statusText.includes('逼近') && statusText.includes('壓力')) {
        shortTermPlan = `不追高！等量能放大突破 ${fallbackRes?.price.toFixed(1)} 後站穩確認，或出現上影線時考慮獲利了結`;
    } else if (statusText.includes('逼近') && statusText.includes('昨高')) {
        shortTermPlan = `昨高 ${fallbackRes?.price.toFixed(1)} 為短線壓力，爆量過昨高可追，陰線收黑則退場`;
    } else if (statusText.includes('回測')) {
        const sp = fallbackSup?.price.toFixed(1);
        shortTermPlan = `${sp} 附近留意止跌訊號（下影線、量縮回穩），守穩可短多；跌破則出場`;
    } else if (statusText.includes('突破')) {
        shortTermPlan = `順勢操作，以 5 分 K MA5 為短線防守，不破前低續抱，切勿逆勢放空`;
    } else if (statusText.includes('跌破')) {
        shortTermPlan = `趨勢偏弱，反彈至壓力區可考慮放空；若量縮止跌翻紅再觀察`;
    } else {
        shortTermPlan = `現價 ${currentPrice.toFixed(1)} 在昨高（${prevHigh.toFixed(1)}）下方整理，等待突破或回測支撐再進場`;
    }

    // ── 3. 波段計畫 ──
    let swingPlan;
    if (strongSup) {
        const labels = strongSup.labels?.slice(0, 2).join('+') || '支撐共振';
        swingPlan = `波段支撐在 ${strongSup.price.toFixed(1)}（${labels}），可設為停損參考；守穩可持有至近期壓力`;
    } else if (fallbackSup) {
        swingPlan = `以${fallbackSup.label} ${fallbackSup.price.toFixed(1)} 為波段停損線；若跌破則出清，否則可跟隨趨勢持有`;
    } else if (prevLow > 0) {
        swingPlan = `近期無明顯共振支撐，以昨低 ${prevLow.toFixed(1)} 為粗略停損參考，操作以短線為主`;
    } else {
        swingPlan = '目前缺乏明確支撐數據，建議輕倉觀察或空手等待更佳機會';
    }

    // ── 4. 停利目標（改用最近壓力，不用 ORB 測幅） ──
    let profitTarget;
    if (fallbackRes) {
        const nextRes = resistanceLevels[1];
        if (nextRes) {
            profitTarget = `${fallbackRes.price.toFixed(1)}（第一目標）→ ${nextRes.price.toFixed(1)}（第二目標）`;
        } else {
            profitTarget = `${fallbackRes.price.toFixed(1)}（${fallbackRes.label}）`;
        }
    } else if (prevHigh > currentPrice) {
        profitTarget = `${prevHigh.toFixed(1)}（昨高壓力）`;
    } else if (prevHigh > 0 && currentPrice > prevHigh) {
        // 已突破昨高，用昨高 + 突破幅度測幅
        const breakRange = currentPrice - prevHigh;
        const target1 = (currentPrice + breakRange * 0.5).toFixed(1);
        const target2 = (currentPrice + breakRange).toFixed(1);
        profitTarget = `${target1} ~ ${target2}（突破測幅）`;
    } else {
        profitTarget = '等待壓力位確認後設定';
    }

    // ── 即時籌碼分析 ──
    const chipSignal = (() => {
        if (!chipData?.foreign || !chipData?.trust || !chipData?.dealer || !chipData?.total) return null;
        const f1  = chipData.foreign.d1  || 0;
        const t1  = chipData.trust.d1    || 0;
        const d1  = chipData.dealer.d1   || 0;
        const tot1 = chipData.total.d1   || 0;
        const f5  = chipData.foreign.d5  || 0;
        const t5  = chipData.trust.d5    || 0;
        const tot5 = chipData.total.d5   || 0;
        const tot10 = chipData.total.d10 || 0;

        // 三大法人今日各自方向
        const foreignDir = f1 > 500 ? 'buy' : f1 < -500 ? 'sell' : 'flat';
        const trustDir   = t1 > 200 ? 'buy' : t1 < -200 ? 'sell' : 'flat';
        const dealerDir  = d1 > 200 ? 'buy' : d1 < -200 ? 'sell' : 'flat';

        // 買入方計數
        const buyCount  = [foreignDir, trustDir, dealerDir].filter(v => v === 'buy').length;
        const sellCount = [foreignDir, trustDir, dealerDir].filter(v => v === 'sell').length;

        // 趨勢：5日 + 10日
        const trend5  = tot5  > 2000 ? '持續買超' : tot5  < -2000 ? '持續賣超' : '盤整';
        const trend10 = tot10 > 5000 ? '長線蓄積' : tot10 < -5000 ? '長線出貨' : '中性';

        // 綜合信號
        let signal, signalColor, signalBg, signalIcon;
        if (buyCount >= 2 && tot5 > 0) {
            signal = '積極買超 🔥';  signalColor = 'text-red-600';   signalBg = 'bg-red-50 border-red-200';    signalIcon = '📈';
        } else if (buyCount >= 2) {
            signal = '溫和買超';     signalColor = 'text-red-500';   signalBg = 'bg-red-50 border-red-100';    signalIcon = '↗️';
        } else if (sellCount >= 2 && tot5 < 0) {
            signal = '積極賣超 ⚠️'; signalColor = 'text-green-700'; signalBg = 'bg-green-50 border-green-200'; signalIcon = '📉';
        } else if (sellCount >= 2) {
            signal = '溫和賣超';     signalColor = 'text-green-600'; signalBg = 'bg-green-50 border-green-100'; signalIcon = '↘️';
        } else {
            signal = '多空拉鋸';    signalColor = 'text-slate-600'; signalBg = 'bg-slate-50 border-slate-200'; signalIcon = '⚖️';
        }

        return { f1, t1, d1, tot1, f5, t5, tot5, tot10, foreignDir, trustDir, dealerDir, buyCount, sellCount, signal, signalColor, signalBg, signalIcon, trend5, trend10 };
    })();


    // ════════════════════════════════════════════════════════════
    // ██  五大維度 AI 判定引擎（K線×籌碼×量價×趨勢×綜合情境）  ██
    // ════════════════════════════════════════════════════════════
    const vol      = marketData?.volume      || 0;
    const avgVol   = marketData?.avgVolume5d || 0;
    const openPrice = marketData?.open       || currentPrice;
    const dayHigh  = orbData?.high           || openPrice;
    const dayLow   = orbData?.low            || openPrice;
    const ma5      = mopsData?.tech?.ma5     || 0;
    const marginChg        = mopsData?.chip_analysis?.margin_change_5d  || marginData?.margin_change || 0;
    const shortMarginRatio = mopsData?.chip_analysis?.short_margin_ratio || marginData?.margin_short_ratio || 0;

    // ── 融資融券即時訊號 ──
    const marginSignal = (() => {
        if (!marginData) return null;
        const mb  = marginData.margin_balance || 0;  // 融資餘額
        const mc  = marginData.margin_change  || 0;  // 融資增減
        const mu  = marginData.margin_utilization || 0;
        const sb  = marginData.short_balance  || 0;  // 融券餘額
        const sc  = marginData.short_change   || 0;  // 融券增減
        // 正確券資比 = 融券餘額 / 融資餘額 × 100（API 的 margin_short_ratio 計算不同，不使用）
        const msr = mb > 0 ? (sb / mb * 100) : 0;
        const date= marginData.date || '';

        // ── 籌碼行為判斷（白話版） ──
        let verdict = '', type = 'neutral', icon = '⚖️';
        const priceUp = (marketData?.changePercent || 0) > 0;

        if (mc > 2000 && !priceUp) {
            verdict = `股票在跌，但還是有人借錢買進（融資 +${mc.toLocaleString()} 張）。這些人賭股票會反彈，但一旦繼續跌，就會被券商強制賠售（斷頭），讓股價跌更快。⚡ 現在接股票要小心。`;
            type = 'negative'; icon = '⚠️';
        } else if (mc > 2000 && priceUp) {
            verdict = `股票在漲，但大量散戶借錢追高（融資 +${mc.toLocaleString()} 張）。散戶借錢衝進來，通常是漲勢快結束的信號。主力很可能趁機賣給這些追高的人。`;
            type = 'warning'; icon = '🔔';
        } else if (mc < -1500 && priceUp) {
            verdict = `股票在漲，同時借錢買的人反而減少（融資 ${mc.toLocaleString()} 張）。這是「健康上漲」—不是散戶瘋狂追，而是主力穩穩吃貨，續漲潛力較大。`;
            type = 'positive'; icon = '✅';
        } else if (mc < -1500 && !priceUp) {
            verdict = `股票跌，融資的人因撐不住陸續認賠賣出（融資 ${mc.toLocaleString()} 張）。這種「斷頭潮」會讓股價短期加速下跌，但有時也是最後一波殺盤。`;
            type = 'negative'; icon = '💣';
        } else if (sc < -80 && priceUp) {
            verdict = `放空的人大量回補（融券減 ${Math.abs(sc).toLocaleString()} 張）+ 股票在漲。放空就是「借股票賣掉、等跌再買回來」，現在他們被迫高價買回，反而助推股價上漲（軋空行情）。`;
            type = 'positive'; icon = '🚀';
        } else if (sc > 80) {
            verdict = `有人增加放空（融券 +${sc.toLocaleString()} 張）。他們認為股票即將下跌，若空單持續增加，表示看空力量變強，留意下跌壓力。`;
            type = 'warning'; icon = '📉';
        } else {
            verdict = `融資餘額 ${mb.toLocaleString()} 張（使用率 ${mu.toFixed(1)}%），融券 ${sb.toLocaleString()} 張，今日借錢買賣的行為沒有明顯異常，市場維持平穩。`;
            type = 'neutral'; icon = '➖';
        }

        // 軋空潛力
        const squeezePotential = msr > 20 ? `券資比 ${msr.toFixed(1)}%（融券/融資）超過 20%，放空者眾多，一旦漲起來放空者被迫回補，容易引發軋空暴漲。` : '';

        return { mb, mc, sb, sc, mu, msr, verdict, type, icon, squeezePotential, date };
    })();

    const volRatio      = avgVol > 0 ? vol / avgVol : 0;
    const isBearCandle  = currentPrice < openPrice;
    const isBullCandle  = currentPrice > openPrice;
    const bodySize      = Math.abs(currentPrice - openPrice);
    const totalRange    = Math.max(dayHigh - dayLow, 0.01);
    const upperShadow   = dayHigh - Math.max(currentPrice, openPrice);
    const lowerShadow   = Math.min(currentPrice, openPrice) - dayLow;
    const upperShadowPct = upperShadow / totalRange;
    const bodyPct       = bodySize / totalRange;

    // ── 一、K線型態判定 ──
    let klinePattern = null;
    if (totalRange > 0) {
        if (isBearCandle && upperShadowPct > 0.55 && bodyPct < 0.35) {
            const sev = upperShadowPct > 0.7 ? '極強' : '標準';
            klinePattern = { name: upperShadowPct > 0.7 ? '射擊之星' : '上影線黑K', type: 'negative',
                verdict: `${sev}頭部反轉型態，上影線佔全幅 ${(upperShadowPct*100).toFixed(0)}%，多方攻高失敗、高檔賣壓極重。` };
        } else if (isBearCandle && upperShadowPct > 0.8 && bodyPct < 0.08) {
            klinePattern = { name: '墓碑十字線', type: 'negative',
                verdict: '開高走低收平，多方完全失守，極強反轉訊號，頭部幾乎確認。' };
        } else if (isBearCandle && bodyPct > 0.6 && volRatio > 1.5) {
            klinePattern = { name: '帶量長黑K', type: 'negative',
                verdict: `大實體黑K（實體 ${(bodyPct*100).toFixed(0)}%），量達均量 ${volRatio.toFixed(1)} 倍，主力倒貨確認，空方主導。` };
        } else if (isBullCandle && bodyPct > 0.6 && volRatio > 2) {
            klinePattern = { name: volRatio > 3 ? '天量長紅K（頭部疑慮）' : '強勢長紅K', type: volRatio > 3 ? 'warning' : 'positive',
                verdict: volRatio > 3 ? `天量（均量 ${volRatio.toFixed(1)} 倍）長紅，量能過大形成「天量天價」疑慮，留意頭部巨量反轉。`
                    : `強勢長紅K，量增價漲，短線多頭動能明確。` };
        } else if (isBullCandle && volRatio < 0.6 && bodyPct > 0.4) {
            klinePattern = { name: '量縮紅K（逃命波疑慮）', type: 'warning',
                verdict: `上漲但量縮至均量 ${(volRatio*100).toFixed(0)}%，「價漲量縮」—動能不足，假突破/高檔逃命波警訊。` };
        } else if (!isBearCandle && upperShadowPct > 0.5 && volRatio > 1.5) {
            klinePattern = { name: '爆量長上影', type: 'negative',
                verdict: `創高後大量收縮、留長上影，「爆量長上影」頭部確認度極高，賣壓極重。` };
        }
    }

    // ── 二、籌碼面精細判定 ──
    const chipJudgments = [];
    if (chipSignal) {
        const cs = chipSignal;
        // 主力吃貨
        if (cs.buyCount >= 2 && isBullCandle && marginChg < 0) {
            chipJudgments.push({ name: '主力吃貨型態', type: 'positive',
                verdict: `法人${cs.buyCount}方同步買超，融資反而減少（${marginChg.toLocaleString()}張），籌碼由弱手轉強手，偏多。` });
        }
        // 散戶高檔接刀
        if (marginChg > 3000 && (isBearCandle || upperShadowPct > 0.4)) {
            chipJudgments.push({ name: '散戶高檔接刀陷阱', type: 'negative',
                verdict: `融資暴增 ${marginChg.toLocaleString()} 張 + ${isBearCandle ? '黑K' : '長上影'}，主力出貨散戶追高，籌碼從強手轉弱手。危險！` });
        }
        // 主力出貨
        if (cs.sellCount >= 2 && marginChg > 1000) {
            chipJudgments.push({ name: '主力出貨型態', type: 'negative',
                verdict: `法人${cs.sellCount}方同步賣超 + 融資增加${marginChg.toLocaleString()}張，籌碼從強手轉弱手，偏空。` });
        }
        // 軋空行情
        if (shortMarginRatio > 15 && cs.buyCount >= 2 && trendName.includes('多頭')) {
            chipJudgments.push({ name: '軋空行情確認', type: 'positive',
                verdict: `券資比 ${shortMarginRatio.toFixed(1)}% + 法人積極買超 + 股價強勢，空方被迫回補，軋空動能強。` });
        }
        // 軋空結束
        if (shortMarginRatio > 20 && cs.sellCount >= 1 && isBearCandle) {
            chipJudgments.push({ name: '軋空行情恐結束', type: 'warning',
                verdict: `券資比雖高（${shortMarginRatio.toFixed(1)}%）但股價轉黑、法人賣超，空方回補完畢，上漲動能消失。` });
        }
        // 籌碼鬆動
        if (cs.sellCount >= 2 && cs.tot5 < -2000) {
            chipJudgments.push({ name: '籌碼鬆動', type: 'negative',
                verdict: `外資/投信 5日淨賣超 ${cs.tot5.toLocaleString()} 張，主流資金撤退，支撐弱化。` });
        }
    }

    // ── 三、量價關係六型判定 ──
    let volPriceJudgment = null;
    if (vol > 0 && avgVol > 0) {
        if (isBullCandle && volRatio > 1.3) {
            volPriceJudgment = { name: '價漲量增', type: 'positive', icon: '✅',
                verdict: `量能達均量 ${volRatio.toFixed(1)} 倍，正常多方訊號，量價配合良好。` };
        } else if (isBullCandle && volRatio < 0.7) {
            volPriceJudgment = { name: '價漲量縮（假突破警訊）', type: 'warning', icon: '⚠️',
                verdict: `上漲但量縮至均量 ${(volRatio*100).toFixed(0)}%，動能不足，假突破/高檔逃命波風險高。` };
        } else if (isBearCandle && volRatio > 2.5) {
            volPriceJudgment = { name: '天量天價帶量下殺', type: 'negative', icon: '🚨',
                verdict: `爆量長黑（均量 ${volRatio.toFixed(1)} 倍）！主力倒貨典型，「天量天價」頭部確認度極高。` };
        } else if (isBearCandle && volRatio > 1.5) {
            volPriceJudgment = { name: '價跌量增', type: 'negative', icon: '❌',
                verdict: `量增黑K（均量 ${volRatio.toFixed(1)} 倍），賣壓確認，主力藉量能掩護出貨。` };
        } else if (isBearCandle && volRatio < 0.7) {
            volPriceJudgment = { name: '價跌量縮（止跌觀察）', type: 'neutral', icon: '➖',
                verdict: `下跌但量縮（均量 ${(volRatio*100).toFixed(0)}%），賣壓減輕，等待量縮打底確認。` };
        }
    }

    // ── 四、趨勢與結構面 ──
    const trendJudgments = [];
    if (ma5 > 0) {
        const ma5Bias = ((currentPrice - ma5) / ma5) * 100;
        if (ma5Bias > 12) {
            trendJudgments.push({ name: 'MA5 高度乖離（高檔鈍化）', type: 'negative',
                verdict: `正乖離 ${ma5Bias.toFixed(1)}%，技術面嚴重過熱，均線強力回拉壓力，RSI/KD 可能高檔鈍化即將反轉。` });
        } else if (ma5Bias > 6) {
            trendJudgments.push({ name: 'MA5 乖離偏高', type: 'warning',
                verdict: `正乖離 ${ma5Bias.toFixed(1)}%，短線偏熱，逢高減碼保護利潤。` });
        } else if (ma5Bias < -6) {
            trendJudgments.push({ name: 'MA5 負乖離（超賣）', type: 'neutral',
                verdict: `負乖離 ${Math.abs(ma5Bias).toFixed(1)}%，技術面超賣，均線附近留意止跌訊號。` });
        }
    }
    // 假突破 Bull Trap
    if (prevHigh > 0 && dayHigh > prevHigh && currentPrice < prevHigh && isBearCandle) {
        trendJudgments.push({ name: '假突破（Bull Trap）', type: 'negative',
            verdict: `盤中突破昨高 ${prevHigh.toFixed(1)} 後迅速拉回收黑，典型誘多陷阱！主力誘散戶追高後出貨。` });
    }
    // 支撐失守
    if (prevLow > 0 && currentPrice < prevLow) {
        trendJudgments.push({ name: '支撐失守', type: 'negative',
            verdict: `跌破昨低 ${prevLow.toFixed(1)}，多方支撐瓦解，趨勢轉空。` });
    }

    // ── 五、綜合情境判定（最高優先級 Banner）──
    const scenarios = [];
    const isDistributionComplete = volRatio > 2 && isBearCandle && marginChg > 5000 && chipSignal?.sellCount >= 2;
    if (isDistributionComplete) {
        scenarios.push({ name: '⚠️ 主力出貨完成', gradient: 'from-red-600 to-rose-700',
            badge: '強烈賣出', verdict: `天量(${volRatio.toFixed(1)}倍)+黑K+融資暴增${marginChg.toLocaleString()}張+法人${chipSignal.sellCount}方賣超→頭部確立，主力出貨完成度高。` });
    }
    const isRetailTrap = !isDistributionComplete && marginChg > 3000 && upperShadowPct > 0.35 && (isBearCandle || volRatio < 0.9);
    if (isRetailTrap) {
        scenarios.push({ name: '🪤 散戶高檔接刀', gradient: 'from-orange-500 to-red-600',
            badge: '高風險', verdict: `融資暴增${marginChg.toLocaleString()}張+上影/黑K—高檔誘多，籌碼從強手轉弱手。建議立即減碼或空手觀望。` });
    }
    const isBullTrap = !isDistributionComplete && !isRetailTrap && prevHigh > 0 && dayHigh > prevHigh && currentPrice < prevHigh && isBearCandle && volRatio < 1.2;
    if (isBullTrap) {
        scenarios.push({ name: '🐂 Bull Trap 假突破', gradient: 'from-amber-500 to-orange-600',
            badge: '誘多陷阱', verdict: `突破昨高後量不配合(${volRatio.toFixed(1)}倍)+收黑拉回，典型Bull Trap！反手做空機會，設停損於昨高上方。` });
    }
    const isWashout = !isDistributionComplete && !isRetailTrap && !isBullTrap && volRatio < 0.8 && isBearCandle && bodyPct < 0.3 && chipSignal?.buyCount >= 1 && ma5 > 0 && currentPrice > ma5;
    if (isWashout) {
        scenarios.push({ name: '🧹 正常洗盤回調', gradient: 'from-emerald-500 to-teal-600',
            badge: '偏多看待', verdict: `量縮小黑K回測均線+籌碼集中（法人仍買超）+守MA5，正常回調洗盤，偏多結構未破。` });
    }
    const isPanicSell = volRatio > 2.5 && isBearCandle && bodyPct > 0.6 && marginChg < -3000;
    if (isPanicSell) {
        scenarios.push({ name: '😱 恐慌性殺盤', gradient: 'from-slate-600 to-slate-800',
            badge: '逃命波警戒', verdict: `大量長黑(${volRatio.toFixed(1)}倍均量)+融資斷頭(${Math.abs(marginChg).toLocaleString()}張)+短期超賣，可能出現逃命波短暫反彈，非反轉信號。` });
    }

    // ── 建立 defenseAlerts ──
    const defenseAlerts = [];
    if (marketData?.marketSummary) {
        defenseAlerts.push({ type: 'info', label: '大盤局勢', text: marketData.marketSummary });
    }
    if (epsData?.evaluation?.macro_advice) {
        defenseAlerts.push({ type: 'positive', label: '大盤資金聯動', text: epsData.evaluation.macro_advice });
    }
    if (klinePattern) {
        defenseAlerts.push({ type: klinePattern.type, label: `K線｜${klinePattern.name}`, text: klinePattern.verdict });
    }
    if (volPriceJudgment) {
        defenseAlerts.push({ type: volPriceJudgment.type, label: `量價｜${volPriceJudgment.name}`, text: volPriceJudgment.verdict });
    }
    if (chipSignal) {
        const cs = chipSignal;
        const dl = d => d === 'buy' ? '買超' : d === 'sell' ? '賣超' : '持平';
        const alertType = cs.buyCount >= 2 ? 'positive' : cs.sellCount >= 2 ? 'negative' : 'neutral';
        defenseAlerts.push({ type: alertType, label: `法人籌碼｜${cs.signal}`,
            text: `外資${dl(cs.foreignDir)}(${cs.f1>0?'+':''}${cs.f1.toLocaleString()}) 投信${dl(cs.trustDir)}(${cs.t1>0?'+':''}${cs.t1.toLocaleString()}) 自營${dl(cs.dealerDir)}(${cs.d1>0?'+':''}${cs.d1.toLocaleString()}) ｜5日${cs.trend5}(${cs.tot5>0?'+':''}${cs.tot5.toLocaleString()}) 10日${cs.trend10}` });
    }
    chipJudgments.forEach(cj => defenseAlerts.push({ type: cj.type, label: `籌碼｜${cj.name}`, text: cj.verdict }));
    trendJudgments.forEach(tj => defenseAlerts.push({ type: tj.type, label: `結構｜${tj.name}`, text: tj.verdict }));
    if (mopsData?.news) {
        const titles = mopsData.news.map(n => n.title).join(' ');
        const hasHype = ['目標價','上看','調升','史詩','超狂'].some(kw => titles.includes(kw));
        const hasReal = ['營收','獲利','法說','報價','現貨價','財報'].some(kw => titles.includes(kw));
        if (hasHype && !hasReal) defenseAlerts.push({ type: 'warning', label: '產業驗證', text: '新聞狂喊「超狂目標價」但缺乏實質基本面佐證，留意消息面掩護出貨。' });
        else if (hasHype && hasReal) defenseAlerts.push({ type: 'positive', label: '產業驗證', text: '法人報告+實質營收/報價趨勢皆具備基本面支撐。' });
    }


    // (5) EPS 基本面評估
    if (epsData) {
        if (epsData.evaluation.score >= 75) {
             defenseAlerts.push({
                 type: 'positive',
                 label: 'EPS 護城河',
                 text: `基本面優良護體：${epsData.evaluation.verdict}`
             });
        } else if (epsData.evaluation.score <= 50) {
             defenseAlerts.push({
                 type: 'warning',
                 label: 'EPS 風險',
                 text: `基本面疲弱警戒：${epsData.evaluation.verdict}`
             });
        }
    }

    // (6) 凱基投顧評價彙整
    if (kgiData && kgiData.length > 0) {
        const latestKgi = kgiData[0];
        const rating = latestKgi.rating;
        const tp = latestKgi.target_price;
        
        let type = 'neutral';
        if (rating.includes('買進') || rating.includes('增加') || rating.includes('優於')) type = 'positive';
        if (rating.includes('賣出') || rating.includes('減碼') || rating.includes('低於')) type = 'negative';
        
        defenseAlerts.push({
             type: type,
             label: '凱基投顧評價',
             text: `最新評等「${rating}」，目標價 ${tp || '未定'} (預估2026 EPS: ${latestKgi.eps_2026 || '--'})。`
        });
    }

    // (7) 美股聯動效應 (US Market Context)
    if (marketData?.sp500) {
        // 解析格式 "+1.23%"
        try {
            const sp500Pct = parseFloat(marketData.sp500.replace('%', ''));
            if (!isNaN(sp500Pct)) {
                if (sp500Pct >= 1.0) {
                    defenseAlerts.push({
                        type: 'positive',
                        label: '美股聯動',
                        text: `昨夜 S&P 500 大漲 ${marketData.sp500}，全球資金風險胃納提升，台股早盤易受激勵向上，順勢做多勝率較高。`
                    });
                } else if (sp500Pct <= -1.0) {
                    defenseAlerts.push({
                        type: 'negative',
                        label: '美股聯動',
                        text: `昨夜 S&P 500 重挫 ${marketData.sp500}！美股承壓恐拖累台股大盤與科技股表現，今日建議嚴控持股、勿輕易接刀。`
                    });
                } else if (sp500Pct > 0) {
                    defenseAlerts.push({
                        type: 'neutral',
                        label: '美股聯動',
                        text: `昨夜 S&P 500 小漲 ${marketData.sp500}，美股平穩，台股走勢將回歸個股籌碼與基本面表現。`
                    });
                } else {
                     defenseAlerts.push({
                        type: 'warning',
                        label: '美股聯動',
                        text: `昨夜 S&P 500 小跌 ${marketData.sp500}，美股震盪整理，近期需慎防外資連動式的獲利了結賣壓。`
                    });
                }
            }
        } catch (e) {
            console.warn("SP500 parse error", e);
        }
    }

    // ── VIX 恐慌分析整合 ──
    const fear      = vixData?.fear_analysis ?? null;
    const twAdvice  = vixData?.taiwan_advice  ?? null;
    const vixVal    = fear?.vix_value ?? 0;
    const vixEmoji  = fear?.emoji ?? '';
    const fearLabel = fear?.label ?? '';
    const fearScore = fear?.score ?? 0;
    const strategy  = twAdvice?.strategy ?? '';

    // VIX 對多空判斷的修正文字
    let vixImpact = null;
    if (vixVal >= 35) {
        vixImpact = { color: 'text-red-700', bg: 'bg-red-50 border-red-200', text: `VIX ${vixVal.toFixed(1)} 極度恐慌！外資大幅撤退，台股系統性風險升高，建議以資金安全為第一優先，大幅降低持股。` };
    } else if (vixVal >= 28) {
        vixImpact = { color: 'text-orange-700', bg: 'bg-orange-50 border-orange-200', text: `VIX ${vixVal.toFixed(1)} 進入恐慌區，美股波動加劇，台股隔日跳空風險高，持有部位需設置嚴格停損，避免追高追強。` };
    } else if (vixVal >= 20) {
        vixImpact = { color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200', text: `VIX ${vixVal.toFixed(1)} 偏高，市場轉趨謹慎，建議以個股基本面為主，順大盤方向操作，嚴控部位大小。` };
    } else if (vixVal > 0 && vixVal < 15) {
        vixImpact = { color: 'text-orange-600', bg: 'bg-orange-50 border-orange-200', text: `VIX ${vixVal.toFixed(1)} 極低，市場高度樂觀，短線過熱風險提升，注意追高陷阱，逢高減碼保護利潤。` };
    } else if (vixVal >= 15 && vixVal < 20) {
        vixImpact = { color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200', text: `VIX ${vixVal.toFixed(1)} 處於健康區間，市場波動正常，個股行情可以積極把握，以技術面為主要進出依據。` };
    }

    // 策略徽章
    const STRATEGY_LABEL = {
        cash: { label: '全部現金', color: 'bg-red-100 text-red-700 border-red-200' },
        defensive: { label: '防守縮倉', color: 'bg-orange-100 text-orange-700 border-orange-200' },
        bear: { label: '空方避險', color: 'bg-rose-100 text-rose-700 border-rose-200' },
        neutral: { label: '個股自選', color: 'bg-slate-100 text-slate-600 border-slate-200' },
        bull_caution: { label: '謹慎做多', color: 'bg-amber-100 text-amber-700 border-amber-200' },
        bull: { label: '積極做多', color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
        follow_us: { label: '順勢美股', color: 'bg-blue-100 text-blue-700 border-blue-200' },
    };
    const stratBadge = STRATEGY_LABEL[strategy] ?? STRATEGY_LABEL.neutral;

    return (
        <section className="bg-gradient-to-r from-cyan-50 to-blue-50 border border-cyan-200 rounded-xl p-4 mt-4 shadow-sm">
            <h3 className="text-sm font-bold text-cyan-800 mb-3 flex items-center gap-2 flex-wrap">
                📝 總結操作建議
                <span className="text-xs bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold px-2.5 py-0.5 rounded-full shadow-sm flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></span>
                    AI 即時運算
                </span>
                {!hasLevels && (
                    <span className="text-xs bg-yellow-100 text-yellow-600 px-2 py-0.5 rounded-full font-normal">基本模式（K線載入後升級）</span>
                )}
            </h3>

            <div className="space-y-3 text-sm">
                <div className="flex flex-col gap-1 bg-white/60 p-2.5 rounded-lg border border-cyan-100 hover:bg-white/80 transition-colors">
                    <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500 font-bold">📍 現況與多空</span>
                        <span className={`text-[11px] font-bold px-2 py-0.5 rounded-md border flex items-center gap-1 ${trendBg}`}>
                            <span>{trendIcon}</span> {trendName}
                        </span>
                    </div>
                    <span className={`font-semibold mt-1 ${statusColor}`}>{statusText}</span>
                </div>

                {/* ── AI 綜合情境判定 Banner（高優先） */}
                {scenarios.length > 0 && scenarios.map((sc, i) => (
                    <div key={i} className={`p-3 rounded-xl bg-gradient-to-r ${sc.gradient} text-white shadow-md`}>
                        <div className="flex items-center justify-between mb-1.5">
                            <span className="text-[12px] font-black tracking-wide">{sc.name}</span>
                            <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-white/20">{sc.badge}</span>
                        </div>
                        <p className="text-[11px] leading-snug opacity-90">{sc.verdict}</p>
                    </div>
                ))}

                {defenseAlerts.length > 0 && (
                <div className="flex flex-col gap-2 bg-gradient-to-br from-indigo-50 to-purple-50 p-3 rounded-lg border border-indigo-100 shadow-inner">
                    <span className="text-xs text-indigo-700 font-bold flex items-center gap-1">
                        🛡️ 五維防護分析 <span className="px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[9px] font-black uppercase leading-none">AI偵測</span>
                    </span>
                    <div className="space-y-1.5 mt-0.5">
                        {defenseAlerts.map((alert, idx) => {
                            let color = "text-gray-700";
                            let badgeBase = "bg-gray-100 text-gray-600 border-gray-200";
                            
                            if (alert.type === 'positive') { 
                                color = "text-rose-700"; 
                                badgeBase = "bg-rose-100 text-rose-700 border-rose-200"; 
                            }
                            if (alert.type === 'negative') { 
                                color = "text-emerald-700"; 
                                badgeBase = "bg-emerald-100 text-emerald-700 border-emerald-200"; 
                            }
                            if (alert.type === 'warning') { 
                                color = "text-amber-700"; 
                                badgeBase = "bg-amber-100 text-amber-700 border-amber-200"; 
                            }
                            
                            return (
                                <div key={idx} className={`text-[12px] leading-snug flex items-start gap-2 p-1.5 bg-white/60 rounded-md border border-white/50 ${color}`}>
                                    <span className={`shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded border ${badgeBase}`}>
                                        {alert.label}
                                    </span>
                                    <span className="font-semibold">{alert.text}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>
                )}

                {/* ── 即時籌碼分析區塊 ── */}
                {chipSignal && (
                <div className={`flex flex-col gap-2 p-3 rounded-lg border shadow-inner ${chipSignal.signalBg}`}>
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-slate-700 flex items-center gap-1.5">
                            📊 即時籌碼分析
                            <span className="px-1.5 py-0.5 bg-purple-600 text-white rounded text-[9px] font-black uppercase leading-none">法人動向</span>
                        </span>
                        <div className="flex items-center gap-2">
                            <span className={`text-[11px] font-black px-2 py-0.5 rounded-full border ${chipSignal.signalBg} ${chipSignal.signalColor}`}>
                                {chipSignal.signalIcon} {chipSignal.signal}
                            </span>
                            <button onClick={() => setShowChipDetail(v => !v)}
                                className="text-[9px] text-slate-400 hover:text-slate-600 font-bold">
                                {showChipDetail ? '收合▲' : '展開▼'}
                            </button>
                        </div>
                    </div>

                    {/* 三大法人今日快欄 */}
                    <div className="grid grid-cols-3 gap-1.5">
                        {[
                            { label: '外資', val: chipSignal.f1, dir: chipSignal.foreignDir },
                            { label: '投信', val: chipSignal.t1, dir: chipSignal.trustDir },
                            { label: '自營', val: chipSignal.d1, dir: chipSignal.dealerDir },
                        ].map(({ label, val, dir }) => (
                            <div key={label} className={`p-2 rounded-lg text-center border ${
                                dir === 'buy'  ? 'bg-red-50   border-red-100'   :
                                dir === 'sell' ? 'bg-green-50 border-green-100' :
                                                 'bg-white    border-slate-100'
                            }`}>
                                <div className="text-[9px] text-slate-400 font-bold">{label} 今日</div>
                                <div className={`text-[12px] font-black font-mono ${
                                    dir === 'buy'  ? 'text-red-500'   :
                                    dir === 'sell' ? 'text-green-600' : 'text-slate-500'
                                }`}>{val > 0 ? '+' : ''}{val.toLocaleString()}</div>
                            </div>
                        ))}
                    </div>

                    {/* 展開：5日 / 10日 趨勢 */}
                    {showChipDetail && (
                    <div className="space-y-1.5 pt-1 border-t border-white/50">
                        {/* 5日合計 */}
                        <div className="flex items-center justify-between bg-white/70 rounded-lg px-2.5 py-1.5 border border-white/50">
                            <span className="text-[10px] text-slate-500 font-bold">三大法人 5日</span>
                            <span className={`text-[12px] font-black font-mono ${
                                chipSignal.tot5 > 0 ? 'text-red-500' : chipSignal.tot5 < 0 ? 'text-green-600' : 'text-slate-400'
                            }`}>{chipSignal.tot5 > 0 ? '+' : ''}{chipSignal.tot5.toLocaleString()}張｜{chipSignal.trend5}</span>
                        </div>
                        {/* 10日合計 */}
                        <div className="flex items-center justify-between bg-white/70 rounded-lg px-2.5 py-1.5 border border-white/50">
                            <span className="text-[10px] text-slate-500 font-bold">三大法人 10日</span>
                            <span className={`text-[12px] font-black font-mono ${
                                chipSignal.tot10 > 0 ? 'text-red-500' : chipSignal.tot10 < 0 ? 'text-green-600' : 'text-slate-400'
                            }`}>{chipSignal.tot10 > 0 ? '+' : ''}{chipSignal.tot10.toLocaleString()}張｜{chipSignal.trend10}</span>
                        </div>
                        {/* 棒形圖視覺化 */}
                        <div className="bg-white/60 rounded-lg p-2 border border-white/50">
                            <div className="text-[9px] text-slate-400 font-bold mb-1.5">買賣超棒形圖（今日張數）</div>
                            {[
                                { label: '外資', val: chipSignal.f1 },
                                { label: '投信', val: chipSignal.t1 },
                                { label: '自營', val: chipSignal.d1 },
                            ].map(({ label, val }) => {
                                const max = Math.max(Math.abs(chipSignal.f1), Math.abs(chipSignal.t1), Math.abs(chipSignal.d1), 1000);
                                const pct = Math.min(100, Math.abs(val) / max * 100);
                                return (
                                    <div key={label} className="flex items-center gap-1.5 mb-1">
                                        <span className="text-[9px] text-slate-500 w-6 shrink-0 font-bold">{label}</span>
                                        <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden relative">
                                            {val > 0 ? (
                                                <div className="absolute left-1/2 top-0 bottom-0 bg-red-400 rounded-r-full" style={{ width: `${pct/2}%` }} />
                                            ) : (
                                                <div className="absolute right-1/2 top-0 bottom-0 bg-green-400 rounded-l-full" style={{ width: `${pct/2}%` }} />
                                            )}
                                            <div className="absolute left-1/2 top-0 bottom-0 border-l border-slate-300" />
                                        </div>
                                        <span className={`text-[9px] font-mono font-black w-16 text-right shrink-0 ${
                                            val > 0 ? 'text-red-500' : val < 0 ? 'text-green-600' : 'text-slate-400'
                                        }`}>{val > 0 ? '+' : ''}{val.toLocaleString()}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                    )}
                </div>
                )}

                {/* ── 融資融券籌碼區塊 ── */}
                {marginSignal && (
                <div className="flex flex-col gap-2 p-3 rounded-lg border shadow-inner bg-amber-50 border-amber-100">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-slate-700 flex items-center gap-1.5">
                            💳 融資融券籌碼
                            <span className="px-1.5 py-0.5 bg-amber-600 text-white rounded text-[9px] font-black uppercase leading-none">信用交易</span>
                        </span>
                        <span className="text-[10px] text-slate-400 font-bold">{marginSignal.date}</span>
                    </div>

                    {/* 四格數字 */}
                    <div className="grid grid-cols-4 gap-1.5">
                        {[
                            { label: '融資餘額', val: marginSignal.mb, unit: '張', color: 'text-slate-700' },
                            { label: '融資增減', val: marginSignal.mc, unit: '張', color: marginSignal.mc > 0 ? 'text-orange-600' : marginSignal.mc < 0 ? 'text-emerald-600' : 'text-slate-400' },
                            { label: '融券餘額', val: marginSignal.sb, unit: '張', color: 'text-slate-700' },
                            { label: '券資比',   val: marginSignal.msr.toFixed(1), unit: '%', color: marginSignal.msr > 20 ? 'text-red-600' : 'text-slate-600' },
                        ].map(({ label, val, unit, color }) => (
                            <div key={label} className="p-2 rounded-lg text-center bg-white border border-amber-100">
                                <div className="text-[9px] text-slate-400 font-bold">{label}</div>
                                <div className={`text-[12px] font-black font-mono ${color}`}>
                                    {typeof val === 'number' ? (val > 0 ? '+' : '') + val.toLocaleString() : val}{unit}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* AI 判斷 */}
                    <div className={`flex items-start gap-2 p-2 rounded-lg border text-[12px] leading-snug ${
                        marginSignal.type === 'positive' ? 'bg-rose-50 border-rose-100 text-rose-700' :
                        marginSignal.type === 'negative' ? 'bg-green-50 border-green-100 text-green-700' :
                        marginSignal.type === 'warning'  ? 'bg-amber-50 border-amber-200 text-amber-800' :
                                                             'bg-white border-slate-100 text-slate-600'
                    }`}>
                        <span className="text-base shrink-0 mt-px">{marginSignal.icon}</span>
                        <span className="font-semibold">
                            {marginSignal.verdict}
                            {marginSignal.squeezePotential && <span className="ml-1 text-red-600 font-black">{marginSignal.squeezePotential}</span>}
                        </span>
                    </div>

                    {/* 融資使用率Bar */}
                    <div className="bg-white/70 rounded-lg px-2.5 py-2 border border-amber-100">
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-[9px] text-slate-500 font-bold">融資使用率</span>
                            <span className={`text-[11px] font-black font-mono ${
                                marginSignal.mu > 50 ? 'text-red-500' : marginSignal.mu > 25 ? 'text-amber-600' : 'text-emerald-600'
                            }`}>{marginSignal.mu.toFixed(1)}%</span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all ${
                                    marginSignal.mu > 50 ? 'bg-red-400' : marginSignal.mu > 25 ? 'bg-amber-400' : 'bg-emerald-400'
                                }`}
                                style={{ width: `${Math.min(100, marginSignal.mu)}%` }}
                            />
                        </div>
                    </div>
                </div>
                )}

                <div className="flex flex-col gap-1 bg-white/60 p-2.5 rounded-lg border border-cyan-100 hover:bg-white/80 transition-colors">
                    <span className="text-xs text-gray-500 font-bold">⚡ 短線計畫</span>
                    <span className="text-gray-800 leading-snug text-[13px]">{shortTermPlan}</span>
                </div>

                <div className="flex flex-col gap-1 bg-white/60 p-2.5 rounded-lg border border-cyan-100 hover:bg-white/80 transition-colors">
                    <span className="text-xs text-gray-500 font-bold">🌊 波段計畫</span>
                    <span className="text-gray-800 leading-snug text-[13px]">{swingPlan}</span>
                </div>

                <div className="flex flex-col gap-1 bg-white/60 p-2.5 rounded-lg border border-cyan-100 hover:bg-white/80 transition-colors">
                    <span className="text-xs text-gray-500 font-bold">🎯 停利目標</span>
                    <span className="text-red-600 font-mono font-bold tracking-wide text-[13px]">{profitTarget}</span>
                </div>

                {/* ── VIX 恐慌分析總結 ── */}
                {fear && vixVal > 0 && (
                    <div className="flex flex-col gap-2 bg-gradient-to-br from-slate-50 to-blue-50 p-3 rounded-lg border border-slate-200 shadow-inner mt-1">
                        {/* 標題列 */}
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-700 font-black flex items-center gap-1.5">
                                🌐 VIX 恐慌分析總結
                                <span className="px-1.5 py-0.5 bg-slate-700 text-white rounded text-[9px] font-black uppercase leading-none">美股數據</span>
                            </span>
                            <span className={`text-[10px] font-black px-2 py-0.5 rounded-full border ${stratBadge.color}`}>
                                {stratBadge.label}
                            </span>
                        </div>

                        {/* VIX 數值 + 恐慌計 */}
                        <div className="flex items-center gap-3 bg-white/70 rounded-lg px-3 py-2 border border-white/50">
                            {/* 迷你環形儀表 */}
                            <div className="relative w-12 h-12 flex-shrink-0">
                                <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                                    <circle cx="18" cy="18" r="14" fill="none" stroke="#e2e8f0" strokeWidth="4" />
                                    <circle
                                        cx="18" cy="18" r="14" fill="none"
                                        stroke={
                                            vixVal >= 35 ? '#dc2626' :
                                            vixVal >= 28 ? '#f97316' :
                                            vixVal >= 20 ? '#f59e0b' :
                                            vixVal < 15  ? '#f97316' : '#10b981'
                                        }
                                        strokeWidth="4"
                                        strokeDasharray={`${Math.min(fearScore, 99)} ${100 - Math.min(fearScore, 99)}`}
                                        strokeLinecap="round"
                                    />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center leading-none">
                                    <span className="text-[8px] font-black text-slate-600">{fearScore}</span>
                                    <span className="text-[6px] text-slate-400">分</span>
                                </div>
                            </div>

                            {/* VIX 數字 + 等級 */}
                            <div className="flex-1 min-w-0">
                                <div className="flex items-baseline gap-1.5">
                                    <span className="text-[10px] text-slate-400 font-bold">VIX</span>
                                    <span className={`text-xl font-black font-mono tabular-nums ${
                                        vixVal >= 28 ? 'text-red-600' :
                                        vixVal >= 20 ? 'text-amber-600' :
                                        vixVal < 15  ? 'text-orange-500' : 'text-emerald-600'
                                    }`}>{vixVal.toFixed(2)}</span>
                                    <span className="text-base">{vixEmoji}</span>
                                </div>
                                <div className={`text-[11px] font-bold truncate ${
                                    vixVal >= 28 ? 'text-red-600' :
                                    vixVal >= 20 ? 'text-amber-600' :
                                    vixVal < 15  ? 'text-orange-500' : 'text-emerald-600'
                                }`}>{fearLabel}</div>
                            </div>
                        </div>

                        {/* AI 影響分析 */}
                        {vixImpact && (
                            <div className={`flex items-start gap-2 text-[12px] leading-snug p-2.5 rounded-lg border ${vixImpact.bg}`}>
                                <span className="flex-shrink-0 mt-px">🤖</span>
                                <span className={`font-semibold ${vixImpact.color}`}>{vixImpact.text}</span>
                            </div>
                        )}

                        {/* 台股策略建議（簡版） */}
                        {twAdvice?.advice && (
                            <div className="text-[11px] text-slate-600 leading-relaxed bg-white/60 rounded-lg px-2.5 py-2 border border-slate-100">
                                <span className="text-slate-400 font-bold">台股建議：</span>
                                {twAdvice.advice}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* ══════════════════════════════════════════
                 即時行動方案（H1/H2/H3 × VWAP 情境）
                ══════════════════════════════════════════ */}
            {(() => {
                const h1 = highPoints?.[0]?.price || 0;
                const h2 = highPoints?.[1]?.price || 0;
                const h3 = highPoints?.[2]?.price || 0;
                const vwap = marketData?.vwap || 0;
                const curP = currentPrice;
                const prevLowP = marketData?.prevLow || 0;
                const orbLow = orbData?.low || 0;

                if (!h1) return null;

                // ── 判斷情境 ──
                const h1NotBroken   = curP < h1;                          // H1 未突破
                const descendHigh   = h3 > 0 && h2 > 0 && h3 < h2;       // 高點遞降
                const belowVWAP     = vwap > 0 && curP < vwap;            // 在 VWAP 下
                const nearVWAP      = vwap > 0 && Math.abs(curP - vwap) / vwap < 0.008; // 距 VWAP <0.8%
                const breakH3cond   = h3 > 0 && curP > h3 * 1.005;       // 突破 H3
                const aboveVWAP     = vwap > 0 && curP >= vwap;           // 站上 VWAP

                // 停損價 = H3 * 1.005（多方緊停損）/ H2 * 0.995（空方回補）
                const longStop   = h3 > 0 ? (h3 * 0.995).toFixed(2) : '--';
                const shortStop  = h3 > 0 ? (h3 * 1.006).toFixed(2) : '--';
                const revTarget1 = h2 > 0 ? h2.toFixed(2) : '--';
                const priceFmt   = v => v ? v.toFixed(2) : '--';

                // 跌勢模式
                const isBearMode = h1NotBroken && (descendHigh || belowVWAP);
                // 轉多條件達成度
                const bullCondMet = [breakH3cond, aboveVWAP].filter(Boolean).length;
                const bullCondTotal = 2;

                return (
                <div className="mt-4 flex flex-col gap-3">
                    <div className="text-[11px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                        ⚡ 即時情境行動方案
                        <span className="h-px flex-1 bg-slate-200" />
                    </div>

                    {/* ── 情境A：跌勢操作 ── */}
                    <div className={`rounded-xl border-2 p-3 flex flex-col gap-2 ${
                        isBearMode ? 'border-red-300 bg-red-50 shadow-md' : 'border-slate-200 bg-white/60 opacity-60'
                    }`}>
                        <div className="flex items-center justify-between">
                            <span className="text-[12px] font-black text-red-700 flex items-center gap-1.5">
                                🔴 跌勢操作方案
                            </span>
                            <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${
                                isBearMode ? 'bg-red-600 text-white animate-pulse' : 'bg-slate-200 text-slate-500'
                            }`}>{isBearMode ? '▣ 觸發中' : '待確認'}</span>
                        </div>
                        {/* 觸發條件 */}
                        <div className="grid grid-cols-3 gap-1">
                            {[
                                { label: 'H1未突破', ok: h1NotBroken, val: `H1=${priceFmt(h1)}` },
                                { label: '高點遞降', ok: descendHigh, val: h3>0?`H3<H2`:'等待H3' },
                                { label: 'VWAP下方', ok: belowVWAP,   val: vwap>0?`VWAP ${priceFmt(vwap)}`:'無VWAP' },
                            ].map(({label,ok,val}) => (
                                <div key={label} className={`flex flex-col items-center p-1.5 rounded-lg text-center ${
                                    ok ? 'bg-red-100 border border-red-200' : 'bg-slate-50 border border-slate-100'
                                }`}>
                                    <span className={`text-[9px] font-bold ${ ok?'text-red-600':'text-slate-400' }`}>{label}</span>
                                    <span className={`text-[10px] font-black font-mono ${ ok?'text-red-700':'text-slate-400' }`}>{ok?'✓':''} {val}</span>
                                </div>
                            ))}
                        </div>
                        {/* 具體操作步驟 */}
                        <div className="space-y-1 bg-white/80 rounded-lg p-2 border border-red-100">
                            <div className="text-[9px] text-red-500 font-black uppercase">📋 操作步驟</div>
                            <div className="flex items-start gap-1.5">
                                <span className="text-red-500 shrink-0 font-black text-[10px]">①</span>
                                <span className="text-[11px] text-slate-700 leading-snug">
                                    <b>持有部位：</b>停損設在 <span className="text-red-600 font-black font-mono">{shortStop}</span>（H3 上方 0.6%），跌破均線出場
                                </span>
                            </div>
                            <div className="flex items-start gap-1.5">
                                <span className="text-red-500 shrink-0 font-black text-[10px]">②</span>
                                <span className="text-[11px] text-slate-700 leading-snug">
                                    <b>等待空點：</b>{nearVWAP ? <span className="text-orange-600 font-black">⚡現在正在 VWAP 附近！量縮是最佳空點</span> : `反彈至 VWAP ${priceFmt(vwap)} 附近、量縮時做空`}
                                </span>
                            </div>
                            <div className="flex items-start gap-1.5">
                                <span className="text-red-500 shrink-0 font-black text-[10px]">③</span>
                                <span className="text-[11px] text-slate-700 leading-snug">
                                    <b>目標：</b>第一目標 {prevLowP > 0 ? <span className="text-slate-600 font-mono font-black">{prevLowP.toFixed(2)}</span> : (orbLow > 0 ? <span className="text-slate-600 font-mono font-black">{orbLow.toFixed(2)}</span> : '前低/ORB低點')}，逃命波反彈勿追
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* ── 情境B：轉強翻多條件 ── */}
                    <div className={`rounded-xl border-2 p-3 flex flex-col gap-2 ${
                        bullCondMet === bullCondTotal ? 'border-emerald-400 bg-emerald-50 shadow-md' : 'border-slate-200 bg-white/60'
                    }`}>
                        <div className="flex items-center justify-between">
                            <span className="text-[12px] font-black text-emerald-700 flex items-center gap-1.5">
                                🟢 轉強翻多條件
                            </span>
                            <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${
                                bullCondMet === bullCondTotal ? 'bg-emerald-600 text-white animate-pulse'
                                : bullCondMet === 1 ? 'bg-amber-400 text-white'
                                : 'bg-slate-200 text-slate-500'
                            }`}>
                                {bullCondMet}/{bullCondTotal} 達成
                            </span>
                        </div>
                        {/* 必要條件 checklist */}
                        <div className="space-y-1">
                            {[
                                { label: `① 突破 H3 (${h3>0?priceFmt(h3):'--'}) 並收紅K站穩`, ok: breakH3cond },
                                { label: `② 站上並守住 VWAP (${priceFmt(vwap)})`, ok: aboveVWAP },
                            ].map(({label, ok}) => (
                                <div key={label} className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg border ${
                                    ok ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-100'
                                }`}>
                                    <span className={`text-sm shrink-0 ${ ok ? 'text-emerald-500' : 'text-slate-300' }`}>{ok ? '✅' : '⬜'}</span>
                                    <span className={`text-[11px] font-semibold ${ ok ? 'text-emerald-700' : 'text-slate-500' }`}>{label}</span>
                                </div>
                            ))}
                        </div>
                        {/* 達成後操作 */}
                        <div className="bg-white/80 rounded-lg p-2 border border-emerald-100">
                            <div className="text-[9px] text-emerald-600 font-black uppercase mb-1">✅ 兩條件全達成後操作</div>
                            <div className="flex items-start gap-1.5 mb-1">
                                <span className="text-emerald-600 font-black text-[10px] shrink-0">進場</span>
                                <span className="text-[11px] text-slate-700">確認量能 &gt; 均量 1.2倍 + 紅K收關後進場試多</span>
                            </div>
                            <div className="flex items-start gap-1.5 mb-1">
                                <span className="text-emerald-600 font-black text-[10px] shrink-0">停損</span>
                                <span className="text-[11px] text-slate-700 font-mono font-black">{longStop}</span>
                                <span className="text-[10px] text-slate-400">（H3 下方 0.5%，若跌回即出）</span>
                            </div>
                            <div className="flex items-start gap-1.5">
                                <span className="text-emerald-600 font-black text-[10px] shrink-0">目標</span>
                                <span className="text-[11px] text-slate-700">第一目標 <span className="font-mono font-black">{revTarget1}</span>（H2），守住後再看 H1 <span className="font-mono font-black">{priceFmt(h1)}</span></span>
                            </div>
                        </div>
                    </div>
                </div>
                );
            })()}

        </section>
    );
};

export default StrategySummary;
