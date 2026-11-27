// 00981A 官方資料報表（讀 etf/00981A/report.json 與 status.json，不使用任何預設值）
(function () {
    const RED = '#dc2626', GREEN = '#16a34a', GRAY = '#6b7280';
    let selected = new URLSearchParams(location.search).get('date');   // 日期或 'range'
    let cache = null;

    const esc = v => String(v ?? '').replace(/[&<>"']/g, c =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const num = (v, d = 0) => v.toLocaleString('zh-TW', { minimumFractionDigits: d, maximumFractionDigits: d });
    const lots = v => v.toLocaleString('zh-TW', { maximumFractionDigits: 3 });
    const sign = v => (v > 0 ? '+' : v < 0 ? '−' : '');
    const colorOf = v => (v > 0 ? RED : v < 0 ? GREEN : GRAY);
    const md = d => d.slice(5).replace('-', '/');
    const time = s => (s ? s.slice(0, 16).replace('T', ' ') : '--');
    const link = (url, text) => url
        ? `<a href="${esc(url)}" target="_blank" rel="noopener" style="color:#2563eb;text-decoration:underline;">${esc(text)}</a>` : '';

    function change(pct, label) {
        if (pct === null || pct === undefined) return `<span style="color:${GRAY};">${label}：無法比較</span>`;
        const flat = Math.abs(pct) < 0.005;
        const word = flat ? '持平' : pct > 0 ? '上漲' : '下跌';
        return `<span style="color:${flat ? GRAY : colorOf(pct)};font-weight:700;">${label} ${word} ${flat ? '' : sign(pct)}${Math.abs(pct).toFixed(2)}%</span>`;
    }

    function card(title, value, lines) {
        return `<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:14px;">
            <div style="font-size:12px;color:${GRAY};font-weight:700;">${title}</div>
            <div style="font-size:22px;font-weight:900;color:#111827;margin:4px 0;">${value}</div>
            ${lines.map(l => `<div style="font-size:11px;color:${GRAY};line-height:1.7;">${l}</div>`).join('')}
        </div>`;
    }

    const pending = `<span style="color:${GRAY};">待核實</span>`;

    // 手機版：欄位多的表格改成一檔一張卡片，不用左右滑（列印不受影響）
    const css = document.createElement('style');
    css.textContent = `@media screen and (max-width:640px){
        .etf-wide thead{display:none}
        .etf-wide, .etf-wide tbody{display:block;width:100%}
        .etf-wide tr{display:grid;grid-template-columns:1fr 1fr;padding:8px 12px;gap:2px 16px}
        .etf-wide td{display:flex;justify-content:space-between;align-items:center;gap:6px;padding:2px 0 !important;white-space:normal !important}
        .etf-wide td:first-child, .etf-wide td.etf-full{grid-column:1/-1;justify-content:flex-start}
        .etf-wide td.etf-empty{justify-content:center}
        .etf-wide td[data-label]:not(:first-child)::before{content:attr(data-label);color:#6b7280;font-size:11px}
    }`;
    document.head.appendChild(css);

    function table(headers, rows, empty) {
        const th = headers.map((h, i) => `<th style="padding:7px 10px;font-size:11px;color:${GRAY};text-align:${i ? 'right' : 'left'};white-space:nowrap;">${h}</th>`).join('');
        const body = rows.length
            ? rows.map(r => `<tr style="border-top:1px solid #f3f4f6;">${r.map((c, i) => `<td data-label="${headers[i]}" class="${headers[i] === '資料來源' ? 'etf-full' : ''}" style="padding:7px 10px;font-size:13px;text-align:${i ? 'right' : 'left'};white-space:nowrap;">${c}</td>`).join('')}</tr>`).join('')
            : `<tr><td class="etf-full etf-empty" colspan="${headers.length}" style="padding:12px;text-align:center;color:${GRAY};font-size:13px;">${empty}</td></tr>`;
        return `<div style="overflow-x:auto;"><table class="${headers.length > 3 ? 'etf-wide' : ''}" style="width:100%;border-collapse:collapse;"><thead><tr>${th}</tr></thead><tbody>${body}</tbody></table></div>`;
    }

    function section(title, color, inner) {
        return `<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;margin-bottom:14px;">
            <div style="background:${color};color:#fff;font-weight:900;font-size:14px;padding:9px 14px;">${title}</div>${inner}</div>`;
    }

    function changeSections(r, prefix) {
        const kinds = [['new', '新增', RED], ['add', '加碼', RED], ['reduce', '減碼', GREEN], ['delete', '刪除', GREEN]];
        const src = `${link(r.sources.start && r.sources.start.snapshot, r.start_date ? md(r.start_date) : '')}${r.start_date ? '→' : ''}${link(r.sources.end.snapshot, md(r.basis_date))}`;
        return kinds.map(([key, label, color]) => {
            if (!r.comparable) return section(`${prefix}${label}`, GRAY,
                `<div style="padding:12px;text-align:center;color:${GRAY};font-size:13px;">無法比較／待核實：${esc(r.reason)}</div>`);
            const rows = r.changes[key].map(c => [
                `<b>${esc(c.name)}</b> <span style="color:${GRAY};font-size:11px;">${esc(c.code)}</span>`,
                lots(c.previous_shares / 1000), lots(c.shares / 1000),
                `<b style="color:${color};">${label} ${sign(c.delta_lots)}${lots(Math.abs(c.delta_lots))}</b>`,
                c.change_pct === null ? '新進（無基期）' : `<span style="color:${color};">${sign(c.change_pct)}${Math.abs(c.change_pct).toFixed(2)}%</span>`,
                `${c.previous_weight.toFixed(2)}% → ${c.weight.toFixed(2)}%`,
                `<span style="font-size:11px;">投信 PCF ${src}</span>`,
            ]);
            return section(`${prefix}${label}（${rows.length} 檔）`, color, table(
                ['股票', '前期持股（張）', '本期持股（張）', '增減（張）', '增減比例', '持股權重', '資料來源'], rows,
                `比較完整持股清單後，${prefix}無${label}`));
        }).join('');
    }

    function render(panel) {
        const { report, status, errorsUrl } = cache;
        const dates = Object.keys(report.daily).sort().reverse();
        if (selected !== 'range' && !report.daily[selected]) selected = dates[0];
        if (selected === 'range' && !report.cumulative) selected = dates[0];
        const r = selected === 'range' ? report.cumulative : report.daily[selected];
        const range = r.kind === 'range';
        const s = r.sources.end;

        // 三件事分開判斷：① 資料是否為最新應公布交易日 ② 排程是否有在跑 ③ 官方來源狀態
        // ① 依交易日曆的下一個應公布時間判斷，連續休市不會因為時間久就被當成過期
        const consistent = dates[0] === status.latest_basis_date;   // 版本一致性在載入時已檢查
        const overdue = !!status.next_due_at && Date.now() >= Date.parse(status.next_due_at);
        const dataCurrent = status.data_current === true && consistent && !overdue;
        // ② 排程每天（含假日）跑 4 次，超過 36 小時沒有任何一次執行才算異常
        const schedulerOk = Date.now() - Date.parse(status.last_attempt_at) <= 36 * 36e5;
        // ③ 來源
        const labels = { not_published: '官方尚未公布', source_error: '資料來源異常', data_gap: '交易日資料缺漏' };
        const issues = status.issues || [];
        const hasError = status.state === 'error';
        const latest = r.basis_date === dates[0];
        const current = dataCurrent && !hasError && latest;   // 才能稱為「當日」
        const prefix = range ? '區間' : current ? '當日' : `${md(r.basis_date)} 單日`;
        const allGood = dataCurrent && schedulerOk && status.state === 'ok';
        // 「更新異常」只用於來源失敗、驗證不過、交易日資料缺漏（state === 'error'）
        const notPublished = status.state === 'pending' && issues.some(i => i.category === 'not_published');
        const waiting = notPublished ? '待更新／官方尚未公布' : '待更新（尚未確認官方是否公布）';
        const headline = hasError ? '⚠️ 更新異常'
            : !dataCurrent ? `⏳ ${waiting}`
                : schedulerOk ? '✅ 更新正常' : '⚠️ 更新排程未執行（現有資料仍是最新應公布交易日）';
        const dataText = dataCurrent ? `✅ 最新應公布交易日 ${esc(status.expected_basis_date)}`
            : status.data_current === null ? '⚠️ 無法確認是否為最新'
                : overdue ? `⏳ 下一交易日資料應於 ${time(status.next_due_at)} 後公布，本頁尚未取得`
                    : `⏳ 最新應公布交易日 ${esc(status.expected_basis_date)}，目前資料 ${esc(status.latest_basis_date)}`;
        const sourceText = issues.length
            ? issues.map(i => `${labels[i.category] || esc(i.category)}${i.date ? ` ${esc(i.date)}` : ''}：${esc(i.detail)}`).join('<br>　　')
            : '✅ 正常';
        const banner = `<div style="background:${allGood ? '#f8fafc' : '#fffbeb'};border:1px solid ${allGood ? '#e2e8f0' : '#f59e0b'};border-radius:12px;padding:10px 14px;margin-bottom:12px;font-size:12px;line-height:1.9;overflow-wrap:anywhere;">
            <b style="font-size:14px;">${headline}</b><br>
            <b>資料版本</b>　${dataText}<br>
            <b>更新排程</b>　${schedulerOk ? '✅ 正常' : '⚠️ 超過 36 小時未執行'}｜最後嘗試 ${time(status.last_attempt_at)}｜最後成功更新 <b>${time(status.last_success_at)}</b>（台北）<br>
            <b>官方來源</b>　${sourceText}${issues.length || (status.warnings || []).length ? `<br>　　${link(errorsUrl, '錯誤紀錄')}` : ''}
        </div>`;

        const alertBox = text => `<div role="alert" style="background:#fef3c7;border:2px solid #d97706;border-radius:12px;padding:12px 14px;margin-bottom:12px;font-size:14px;font-weight:700;color:#92400e;">⚠️ ${text}</div>`;
        const notice = [
            !dataCurrent && alertBox(`${hasError ? '更新異常' : waiting}。以下是持股基準日 ${esc(r.basis_date)} 的已保存資料，請勿當作最新當日資料。${consistent ? '' : '（狀態檔與報表日期不一致）'}`),
            dataCurrent && hasError && alertBox(`更新異常（見下方「官方來源」）。目前顯示的是上一次通過驗證的資料。`),
            !schedulerOk && alertBox('更新排程可能已停止，請確認 GitHub Actions。'),
            !latest && !range && `<div style="background:#f1f5f9;border-radius:12px;padding:10px 14px;margin-bottom:12px;font-size:13px;color:#475569;">目前顯示歷史日期 ${esc(r.basis_date)}。</div>`,
        ].filter(Boolean).join('');
        const closures = (status.closures || []).map(c => `${esc(c.date)} ${esc(c.reason)}`).join('<br>');

        const options = dates.map(d => `<option value="${d}" ${d === selected ? 'selected' : ''}>單日 ${d}</option>`)
            .concat(report.cumulative ? [`<option value="range" ${range ? 'selected' : ''}>區間累計 ${report.cumulative.start_date} → ${report.cumulative.basis_date}</option>`] : []).join('');

        const word = range ? '區間' : '單日';
        const p = r.price;
        const cards = [
            card('基金規模（淨資產）', `${num(r.aum.value / 1e8, 2)} 億元`, [
                change(r.aum.change_pct, word),
                `其中 淨值 ${r.nav.change_pct === null ? '--' : sign(r.nav.change_pct) + Math.abs(r.nav.change_pct).toFixed(2) + '%'}、單位數 ${r.units.change_pct === null ? '--' : sign(r.units.change_pct) + Math.abs(r.units.change_pct).toFixed(2) + '%'}`,
                `${r.basis_date}｜投信・官方核實`]),
            card('收盤市價', p ? `${p.value.toFixed(2)} 元` : pending, p ? [
                change(p.change_pct, word), `${p.date}${p.previous_date ? `（比 ${md(p.previous_date)}）` : ''}｜${link(s.price_url, '證交所')}・官方核實`] : ['證交所收盤價尚未取得']),
            card('每單位淨值', `${r.nav.value.toFixed(2)} 元`, [change(r.nav.change_pct, word), `${r.nav.date}｜投信・官方核實`]),
            card('折溢價', r.premium.value === null ? pending
                : `<span style="color:${colorOf(r.premium.value)};">${r.premium.value > 0 ? '溢價 +' : r.premium.value < 0 ? '折價 −' : ''}${Math.abs(r.premium.value).toFixed(2)}%</span>`,
                [esc(r.premium.note), '依官方市價與淨值計算']),
            card('現金占淨資產', r.cash ? `${r.cash.ratio.toFixed(2)}%` : pending, r.cash
                ? [`${num(r.cash.amount / 1e8, 2)} 億元`, `${r.basis_date}｜${link(s.assets_url, '投信')}金額 ÷ 淨資產`]
                : ['官方只提供最新一天，此日期未留存']),
            card('期貨保證金占淨資產', r.futures_margin ? `${r.futures_margin.ratio.toFixed(2)}%` : pending, r.futures_margin
                ? [`${num(r.futures_margin.amount / 1e8, 2)} 億元`, `${r.basis_date}｜與現金分列，不相加`]
                : ['官方只提供最新一天，此日期未留存']),
        ].join('');

        const futures = section('衍生商品部位（不列入股票排名）', '#334155', table(
            ['商品', '契約月份', '方向', '口數（口）', '名目曝險（億元）', '占淨資產'],
            r.futures.map(f => [`<b>${esc(f.name)}</b> <span style="color:${GRAY};font-size:11px;">${esc(f.code)}</span>`,
                esc(f.month), esc(f.side), `${num(f.contracts)} 口`, num(f.notional / 1e8, 2), `${f.weight.toFixed(2)}%`]),
            '官方清單無期貨部位'));

        const holdingRows = list => list.map((h, i) => [
            `${i + 1}. <b>${esc(h.name)}</b> <span style="color:${GRAY};font-size:11px;">${esc(h.code)}</span>`,
            lots(h.lots), `${h.weight.toFixed(2)}%`]);
        const heads = ['股票', '持股張數（張）', '持股權重'];
        const holdings = section(`前十大股票持股｜合計 ${r.top10_weight.toFixed(2)}%`, '#6d28d9', table(heads, holdingRows(r.holdings.slice(0, 10)), '無資料'))
            + section(`前二十大股票持股｜合計 ${r.top20_weight.toFixed(2)}%`, '#7c3aed', table(heads, holdingRows(r.holdings.slice(0, 20)), '無資料'))
            + `<details class="no-print" style="margin-bottom:14px;"><summary style="cursor:pointer;font-size:13px;font-weight:700;">完整股票清單（${r.stock_count} 檔，含權重 0.00%）</summary>${table(heads, holdingRows(r.holdings), '無資料')}</details>`;

        panel.innerHTML = `
        <div class="no-print" style="display:flex;gap:8px;justify-content:flex-end;margin-bottom:10px;">
            <select id="etf-date" style="border:1px solid #cbd5e1;border-radius:8px;padding:8px;font-size:13px;">${options}</select>
            <button onclick="window.print()" style="background:#7c3aed;color:#fff;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:700;">📄 分享 PDF</button>
        </div>
        ${notice}
        ${banner}
        <div style="background:#1a1a2e;border-radius:14px;padding:18px;margin-bottom:14px;text-align:center;color:#fff;">
            <h2 style="font-size:24px;font-weight:900;">${esc(report.fund)} ${range
                ? `<span style="color:#fbbf24;">區間累計 ${r.start_date} → ${r.basis_date}</span> 持股增減`
                : `<span style="color:#fbbf24;">${r.basis_date}</span> 持股調整`}</h2>
            <div style="font-size:12px;color:#cbd5e1;margin-top:6px;">持股基準日 ${r.basis_date}${r.comparable ? `｜比較基準 ${r.start_date}` : ''}｜PCF 適用日 ${s.pcf_apply_date}｜官網資料編輯時間 ${time(s.announced_at)}｜擷取時間 ${time(s.fetched_at)}</div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-bottom:14px;">${cards}</div>
        ${changeSections(r, prefix)}
        ${futures}
        ${holdings}
        <div style="font-size:11px;color:${GRAY};line-height:1.8;">
            持股增減是兩份官方持股快照的差額，不等於基金的完整成交紀錄；規模增減包含淨值與單位數變動，不能直接解讀為投資人贖回。<br>
            ${closures ? `近期休市核對：<br>${closures}<br>` : ''}
            紅色＝上漲／新增／加碼，綠色＝下跌／減碼／刪除，灰色＝持平或資料不足。<br>
            來源：${link(s.pcf_url, '統一投信申購買回清單')}｜${link(s.snapshot, `${md(r.basis_date)} 原始快照`)}${r.sources.start ? `｜${link(r.sources.start.snapshot, `${md(r.start_date)} 原始快照`)}` : ''}
        </div>`;
        panel.querySelector('#etf-date').onchange = e => { selected = e.target.value; render(panel); };
    }

    async function load(fund, panel) {
        const base = `etf/${fund}/`;
        const get = async name => {
            const resp = await fetch(`${base}${name}?v=${Date.now()}`, { cache: 'no-store' });
            if (!resp.ok) throw new Error(`${name} HTTP ${resp.status}`);
            return resp.json();
        };
        panel.innerHTML = `<div style="padding:40px;text-align:center;color:${GRAY};">官方資料載入中…</div>`;
        try {
            // report 與 status 必須是同一資料版本；快取或發布交界可能一新一舊，重抓幾次仍不同就不顯示
            let report, status;
            for (let attempt = 1; ; attempt++) {
                [report, status] = await Promise.all([get('report.json'), get('status.json')]);
                if (report.data_version && report.data_version === status.data_version) break;
                if (attempt === 3) throw new Error('資料版本不一致，請稍後重新整理');
                await new Promise(done => setTimeout(done, 1500 * attempt));
            }
            cache = { report, status, errorsUrl: `${base}errors.jsonl` };
            if (typeof currentSummaryETF !== 'undefined' && currentSummaryETF !== fund) return;
            render(panel);
        } catch (e) {
            console.error(e);
            if (typeof currentSummaryETF !== 'undefined' && currentSummaryETF !== fund) return;
            panel.innerHTML = `<div style="padding:40px;text-align:center;color:${GRAY};">待更新／無法比較：官方資料載入失敗（${esc(e.message)}）</div>`;
        }
    }

    window.renderOfficialETF = load;
    window.addEventListener('DOMContentLoaded', () => {
        if (new URLSearchParams(location.search).get('etf') === '00981A') switchSummary('00981A');
    });
})();
