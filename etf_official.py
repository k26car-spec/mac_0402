"""00981A 官方資料管線：抓取 → 驗證 → 保存每日完整快照 → 產生報表。

原則（詳見 docs/etf/README.md）：
- 資料日期一律取官方回傳的「持股基準日」(TranDate)，不用執行日期。
- 每次執行都重新抓取最近幾個交易日；通過驗證才覆蓋舊快照。
- 抓不到就標示「待更新／待核實」，不沿用別天的值、不放預設值。
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import html
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from datetime import time as dtime
from pathlib import Path

TPE = timezone(timedelta(hours=8))
DEFAULT_PUBLISH_TIME = dtime(17, 0)   # 官網約 16:30 編輯；可用參數或 ETF_PUBLISH_TIME 調整
FUNDS = {"00981A": {"fund_code": "49YTW", "name": "主動統一台股增長"}}
ROOT = Path(__file__).resolve().parent / "docs" / "etf"

EZ = "https://www.ezmoney.com.tw/ETF"
TWSE = "https://www.twse.com.tw/exchangeReport"

MAX_STOCK_COUNT_CHANGE = 10   # 相鄰交易日股票檔數變動上限
MAX_NAV_MOVE = 0.12           # 單日淨值變動上限（台股漲跌幅 10%）


class DataError(Exception):
    category = "data_gap"          # 交易日資料缺漏


class SourceError(DataError):
    category = "source_error"      # 資料來源異常（連線、格式、驗證不過），不可當成休市


def parse_time(text: str) -> dtime:
    return datetime.strptime(text, "%H:%M").time()


def due_at(day: str, publish_time: dtime) -> datetime:
    """交易日到了 publish_time，官方持股清單視為「應已公布」。"""
    return datetime.combine(date.fromisoformat(day), publish_time, TPE)


# ── 日期工具 ──────────────────────────────────────────────
def to_dt(value: str) -> datetime | None:
    """官方回應會混用 /Date(毫秒)/ 與 2026-11-27T00:00:00 兩種格式。"""
    m = re.search(r"/Date\((-?\d+)", value or "")
    if m:
        return datetime.fromtimestamp(int(m.group(1)) / 1000, TPE) if int(m.group(1)) > 0 else None
    if not value or value.startswith("0001"):
        return None
    d = datetime.fromisoformat(value[:19])
    return d.replace(tzinfo=TPE)


def to_date(value: str) -> str | None:
    d = to_dt(value)
    return d.date().isoformat() if d else None


def roc(d: date) -> str:
    return f"{d.year - 1911}/{d.month:02d}/{d.day:02d}"


def roc_to_iso(s: str) -> str:
    y, m, d = s.strip().split("/")
    return date(int(y) + 1911, int(m), int(d)).isoformat()


# ── 官方來源 ──────────────────────────────────────────────
class OfficialSource:
    def __init__(self, retries: int = 3, wait: float = 5.0):
        import httpx
        self.client = httpx.Client(
            timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        self.retries, self.wait = retries, wait

    def _request(self, method: str, url: str, **kw):
        for attempt in range(1, self.retries + 1):
            try:
                r = self.client.request(method, url, **kw)
                r.raise_for_status()
                return r
            except Exception as e:  # 網路錯誤／非 2xx：重試
                if attempt == self.retries:
                    raise SourceError(f"抓取失敗 {url}：{e}") from e
                time.sleep(self.wait * attempt)

    def _twse_rows(self, url: str) -> list:
        j = self._request("GET", url).json()
        if j.get("stat") != "OK":
            if "沒有符合條件" in str(j.get("stat")):   # 月初尚無交易日
                return []
            raise SourceError(f"證交所回應異常 {url}：{j.get('stat')}")
        return j["data"]

    def calendar_url(self, month: date) -> str:
        return f"{TWSE}/FMTQIK?response=json&date={month:%Y%m}01"

    def price_url(self, fund: str, month: date) -> str:
        return f"{TWSE}/STOCK_DAY?response=json&date={month:%Y%m}01&stockNo={fund}"

    def holidays(self, year: int) -> dict[str, str]:
        """證交所公布的休市日。清單裡的「開始／最後交易日」是交易日，要排除。"""
        url = ("https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule"
               f"?response=json&date={year}0101")
        j = self._request("GET", url).json()
        if j.get("stat") != "ok" or str(j.get("date", ""))[:4] != str(year) or not j.get("data"):
            raise SourceError(f"休市行事曆回應異常（{year} 年）")
        return {r[0]: r[1] for r in j["data"]
                if not any(k in r[1] for k in ("開始交易", "最後交易"))}

    def trading_days(self, month: date) -> list[str]:
        return [roc_to_iso(r[0]) for r in self._twse_rows(self.calendar_url(month))]

    def prices(self, fund: str, month: date) -> dict[str, float]:
        out = {}
        for r in self._twse_rows(self.price_url(fund, month)):
            try:
                out[roc_to_iso(r[0])] = float(r[6].replace(",", ""))
            except ValueError:   # "--" 表示當日無成交
                pass
        return out

    def pcf(self, fund_code: str, query_date: date) -> dict:
        if not self.client.cookies:
            self._request("GET", f"{EZ}/Transaction/PCF?fundCode={fund_code}")
        r = self._request("POST", f"{EZ}/Transaction/GetPCF", json={
            "fundCode": fund_code, "date": roc(query_date), "specificDate": True})
        try:
            j = r.json()
            return {"pcf": j["pcf"] or [], "asset": j["asset"] or []}
        except (ValueError, KeyError, TypeError) as e:   # 非 JSON 或欄位改版 ≠ 空白
            raise SourceError(f"投信 PCF 回應格式異常（{query_date}）：{e!r}") from e

    def assets(self, fund_code: str) -> list:
        text = self._request("GET", f"{EZ}/Fund/Info?fundCode={fund_code}").text
        m = re.search(r'id="DataAsset" data-content="([^"]*)"', text)
        if not m:
            raise SourceError("投信基金頁找不到 DataAsset 區塊（版面可能改版）")
        return json.loads(html.unescape(m.group(1)))


# ── 解析 ─────────────────────────────────────────────────
def pcf_basis_date(raw: dict) -> str | None:
    return to_date(raw["pcf"][0]["TranDate"]) if raw.get("pcf") else None


def parse_pcf(raw: dict) -> dict:
    values = {r["PCFCode"]: r["Amount"] for r in raw["pcf"]}
    blocks = {a["AssetCode"]: a for a in raw["asset"]}
    return {
        "values": values,
        "stock_total": blocks.get("ST", {}).get("Value"),
        "stocks": blocks.get("ST", {}).get("Details") or [],
        "futures": blocks.get("GD", {}).get("Details") or [],
    }


def probe_pcf(src, fund_code: str, basis: str) -> tuple[str, tuple[dict, str] | None]:
    """PCF 查詢日是「適用日」，不固定等於基準日 +1，所以往後找到 TranDate 相符為止。

    回傳 ("found", (原始回應, 查詢日))；
    ("skipped", None)＝官方有回傳更晚的基準日，確定沒有這一天；
    ("empty", None)＝查不到任何佐證（尚未公布或來源異常），不能當成休市。
    """
    start = date.fromisoformat(basis)
    for offset in range(1, 15):
        q = start + timedelta(days=offset)
        raw = src.pcf(fund_code, q)
        got = pcf_basis_date(raw)
        if got == basis:
            return "found", (raw, q.isoformat())
        if got and got > basis:
            return "skipped", None
    return "empty", None


def match_assets(items: list, basis: str, p: dict) -> list | None:
    """基金頁只有最新一天的現金／保證金；日期與總額都和該日 PCF 一致才採用。"""
    a = {x["AssetCode"]: x for x in items}
    stock_dates = {to_date(d["TranDate"]) for d in (a.get("ST", {}).get("Details") or [])}
    same = (
        stock_dates == {basis}
        and a.get("NAV", {}).get("Value") == p["values"].get("NAV")
        and a.get("OUT_UNIT", {}).get("Value") == p["values"].get("OUT_UNIT")
        and a.get("ST", {}).get("Value") == p["stock_total"]
        and "CASH" in a and "GDM" in a
    )
    if not same:
        return None
    return [{k: v for k, v in x.items() if k != "Details"} for x in items]


# ── 快照欄位白名單 ───────────────────────────────────────
# 公開 repo 只保存計算與追溯用得到的欄位；投信回應裡的員工編號等其他欄位不寫入。
# 資料列一筆都不刪，只刪欄位。
KEEP_PCF = {"PCFCode", "PCFName", "Amount", "TranDate", "PostDate", "EditDate", "ValueDate"}
KEEP_ASSET = {"AssetCode", "AssetName", "Value", "EditDate", "Details"}
KEEP_DETAIL = {"DetailCode", "DetailName", "TranDate", "Share", "Amount", "NavRate",
               "Position", "MTH", "EditTime"}


def keep(row: dict, allowed: set) -> dict:
    out = {k: v for k, v in row.items() if k in allowed}
    if out.get("Details"):
        out["Details"] = [keep(d, KEEP_DETAIL) for d in out["Details"]]
    return out


def sanitize(snap: dict) -> dict:
    raw = snap["pcf"]["raw"]
    raw = {"pcf": [keep(r, KEEP_PCF) for r in raw["pcf"]],
           "asset": [keep(a, KEEP_ASSET) for a in raw["asset"]]}
    assets = snap.get("assets")
    if assets:
        assets = {**assets, "raw": [keep(a, KEEP_ASSET - {"Details"}) for a in assets["raw"]]}
    return {**snap, "pcf": {**snap["pcf"], "raw": raw}, "assets": assets}


# ── 驗證 ─────────────────────────────────────────────────
def validate(snap: dict, prev: dict | None, allow_count_change: bool = False) -> list[str]:
    errors = []
    basis = snap["basis_date"]
    raw = snap["pcf"]["raw"]
    p = parse_pcf(raw)
    v = p["values"]

    dates = {to_date(r["TranDate"]) for r in raw["pcf"] + p["stocks"] + p["futures"]}
    if dates != {basis}:
        errors.append(f"日期不符：預期 {basis}，資料內含 {sorted(map(str, dates))}")

    missing = [k for k in ("NAV", "OUT_UNIT", "P_UNIT") if not v.get(k) or v[k] <= 0]
    if "DIFF_UNIT" not in v:
        missing.append("DIFF_UNIT")
    if missing:
        return errors + [f"缺少必要欄位：{missing}"]
    if not p["stocks"] or p["stock_total"] is None:
        return errors + ["股票明細為空"]

    codes = [s["DetailCode"] for s in p["stocks"]]
    if len(codes) != len(set(codes)):
        errors.append("股票代號重複")
    if any(s["Share"] <= 0 or s["Share"] != int(s["Share"]) for s in p["stocks"]):
        errors.append("股數出現非正整數")
    total = sum(s["Amount"] for s in p["stocks"])
    if abs(total - p["stock_total"]) > 1:
        errors.append(f"股票清單不完整：{len(codes)} 檔金額合計 {total:,.0f}，官方股票總額 {p['stock_total']:,.0f}")
    bad = [s["DetailCode"] for s in p["stocks"] if abs(s["Amount"] / v["NAV"] * 100 - s["NavRate"]) > 0.011]
    if bad:
        errors.append(f"權重與金額不一致：{bad[:5]}")
    if abs(v["OUT_UNIT"] * v["P_UNIT"] - v["NAV"]) > v["OUT_UNIT"] * 0.005 + 1:
        errors.append("單位數 × 每單位淨值 與基金淨資產差距超過四捨五入容許值")
    for f in p["futures"]:
        if f["Share"] != int(f["Share"]) or f["Position"] not in ("B", "S") or not re.fullmatch(r"\d{4}/\d{2}", f["MTH"]):
            errors.append(f"期貨欄位異常：{f['DetailCode']}")

    if prev and prev["basis_date"] == snap["previous_trading_date"]:
        q = parse_pcf(prev["pcf"]["raw"])
        if abs(v["OUT_UNIT"] - q["values"]["OUT_UNIT"] - v["DIFF_UNIT"]) > 1:
            errors.append("單位數差異與前一交易日快照對不上")
        if abs(v["P_UNIT"] / q["values"]["P_UNIT"] - 1) > MAX_NAV_MOVE:
            errors.append(f"每單位淨值單日變動超過 {MAX_NAV_MOVE:.0%}")
        diff = len(p["stocks"]) - len(q["stocks"])
        if abs(diff) > MAX_STOCK_COUNT_CHANGE and not allow_count_change:
            errors.append(f"股票檔數異常：{len(q['stocks'])} → {len(p['stocks'])}（確認屬實可加 --allow-count-change）")
    return errors


# ── 快照存取 ─────────────────────────────────────────────
def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_snapshot(folder: Path, basis: str) -> dict | None:
    path = folder / "snapshots" / f"{basis}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def log_error(folder: Path, now: datetime, basis: str | None, message: str,
              category: str = "warning") -> None:
    path = folder / "errors.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    lines.append(json.dumps({"at": now.isoformat(timespec="seconds"), "basis_date": basis,
                             "category": category, "error": message}, ensure_ascii=False))
    path.write_text("\n".join(lines[-500:]) + "\n", encoding="utf-8")
    print(f"❌ {basis or ''} {message}", file=sys.stderr)


def fetch_snapshot(src, fund: str, basis: str, prev_day: str, now: datetime,
                   old: dict | None) -> tuple[dict | None, list[str]]:
    """回傳 (快照, 非致命問題)。查無清單時回傳 (None, ["empty" 或 "skipped"])。"""
    code = FUNDS[fund]["fund_code"]
    found, got = probe_pcf(src, code, basis)
    if not got:
        return None, [found]
    raw, query_date = got
    stamp = now.isoformat(timespec="seconds")
    p = parse_pcf(raw)
    warnings = []
    snap = {
        "fund": fund, "basis_date": basis, "previous_trading_date": prev_day,
        "fetched_at": stamp,
        "pcf": {"url": f"{EZ}/Transaction/PCF?fundCode={code}", "query_date": query_date, "raw": raw},
        "price": None, "assets": None,
    }
    try:
        month, prev_month = date.fromisoformat(basis), date.fromisoformat(prev_day)
        closes = src.prices(fund, month)
        if (prev_month.year, prev_month.month) != (month.year, month.month):
            closes = {**src.prices(fund, prev_month), **closes}
        if basis in closes:
            snap["price"] = {"url": src.price_url(fund, month), "fetched_at": stamp, "date": basis,
                             "close": closes[basis], "previous_date": prev_day,
                             "previous_close": closes.get(prev_day)}
        else:
            warnings.append("證交所尚無當日收盤價")
    except DataError as e:
        warnings.append(str(e))
    try:
        items = match_assets(src.assets(code), basis, p)
        if items:
            snap["assets"] = {"url": f"{EZ}/Fund/Info?fundCode={code}", "fetched_at": stamp, "raw": items}
    except DataError as e:
        warnings.append(str(e))

    # 同一基準日、已核實過的區塊，不用空值蓋掉（現金頁只提供最新一天）
    if old and old["basis_date"] == basis:
        if not snap["price"] and old.get("price"):
            snap["price"] = old["price"]
        if not snap["assets"] and old.get("assets") and match_nav(old, p):
            snap["assets"] = old["assets"]
    return snap, warnings


def match_nav(old: dict, p: dict) -> bool:
    nav = next((x["Value"] for x in old["assets"]["raw"] if x["AssetCode"] == "NAV"), None)
    return nav == p["values"].get("NAV")


# ── 計算 ─────────────────────────────────────────────────
def ratio_change(current, previous) -> float | None:
    if current is None or not previous:
        return None
    return (current / previous - 1) * 100


def premium(price, price_date, nav, nav_date) -> dict:
    if price is None or nav is None:
        return {"value": None, "note": "缺少市價或淨值，待核實"}
    if price_date != nav_date:
        return {"value": None, "note": f"市價日期 {price_date} 與淨值日期 {nav_date} 不同，不計算"}
    return {"value": (price / nav - 1) * 100, "note": f"{nav_date} 同日市價 ÷ 淨值 − 1"}


def compare_holdings(previous: list, current: list) -> dict:
    """以原始股數比較兩份完整清單。"""
    a = {s["DetailCode"]: s for s in previous}
    b = {s["DetailCode"]: s for s in current}
    out = {"new": [], "add": [], "reduce": [], "delete": []}
    for code in sorted(set(a) | set(b)):
        x, y = a.get(code), b.get(code)
        before = int(x["Share"]) if x else 0
        after = int(y["Share"]) if y else 0
        delta = after - before
        if not delta:
            continue
        kind = "new" if not x else "delete" if not y else "add" if delta > 0 else "reduce"
        out[kind].append({
            "code": code, "name": (y or x)["DetailName"],
            "previous_shares": before, "shares": after, "delta_shares": delta,
            "delta_lots": delta / 1000,
            "change_pct": delta / before * 100 if before else None,
            "previous_weight": x["NavRate"] if x else 0, "weight": y["NavRate"] if y else 0,
        })
    for rows in out.values():
        rows.sort(key=lambda r: (-abs(r["delta_shares"]), r["code"]))
    return out


def build_report(end: dict, start: dict | None, kind: str = "daily") -> dict:
    """kind='daily' 只接受相鄰交易日；'range' 為區間累計。"""
    p = parse_pcf(end["pcf"]["raw"])
    v = p["values"]
    basis = end["basis_date"]
    comparable, reason = True, None
    if start is None:
        comparable, reason = False, (
            f"缺少 {end['previous_trading_date']} 的完整快照" if kind == "daily" else "缺少起始日完整快照")
    elif kind == "daily" and start["basis_date"] != end["previous_trading_date"]:
        comparable, reason = False, (
            f"比較基準 {start['basis_date']} 不是前一交易日 {end['previous_trading_date']}")
    elif start["basis_date"] >= basis:
        comparable, reason = False, "起始日必須早於結束日"
    q = parse_pcf(start["pcf"]["raw"]) if comparable else None

    price = end.get("price")
    prev_close = prev_close_date = None
    if kind == "daily" and price:
        prev_close, prev_close_date = price["previous_close"], price["previous_date"]
    elif comparable and start.get("price"):
        prev_close, prev_close_date = start["price"]["close"], start["basis_date"]

    amounts = {x["AssetCode"]: x["Value"] for x in end["assets"]["raw"]} if end.get("assets") else {}

    def asset(code):
        value = amounts.get(code)
        return None if value is None else {"amount": value, "ratio": value / v["NAV"] * 100}

    stocks = sorted(p["stocks"], key=lambda s: (-s["Amount"], s["DetailCode"]))
    rows = [{"code": s["DetailCode"], "name": s["DetailName"], "shares": int(s["Share"]),
             "lots": s["Share"] / 1000, "weight": s["NavRate"]} for s in stocks]

    def source(s):
        return {"basis_date": s["basis_date"], "pcf_apply_date": s["pcf"]["query_date"],
                "announced_at": to_dt(s["pcf"]["raw"]["pcf"][0]["EditDate"]).isoformat(timespec="seconds"),
                "fetched_at": s["fetched_at"], "pcf_url": s["pcf"]["url"],
                "snapshot": f"etf/{s['fund']}/snapshots/{s['basis_date']}.json",
                "price_url": (s.get("price") or {}).get("url"),
                "assets_url": (s.get("assets") or {}).get("url")}

    return {
        "kind": kind, "basis_date": basis,
        "start_date": start["basis_date"] if comparable else None,
        "comparable": comparable, "reason": reason,
        "aum": {"value": v["NAV"], "change_pct": ratio_change(v["NAV"], q and q["values"]["NAV"])},
        "nav": {"value": v["P_UNIT"], "date": basis,
                "change_pct": ratio_change(v["P_UNIT"], q and q["values"]["P_UNIT"])},
        "units": {"value": v["OUT_UNIT"],
                  "change_pct": ratio_change(v["OUT_UNIT"], q and q["values"]["OUT_UNIT"])},
        "price": None if not price else {
            "value": price["close"], "date": price["date"], "previous_date": prev_close_date,
            "change_pct": ratio_change(price["close"], prev_close)},
        "premium": premium(price and price["close"], price and price["date"], v["P_UNIT"], basis),
        "cash": asset("CASH"), "futures_margin": asset("GDM"),
        "futures": [{"code": f["DetailCode"], "name": f["DetailName"], "month": f["MTH"],
                     "side": "多單" if f["Position"] == "B" else "空單", "contracts": int(f["Share"]),
                     "notional": f["Amount"], "weight": f["NavRate"]} for f in p["futures"]],
        "changes": compare_holdings(q["stocks"], p["stocks"]) if comparable else None,
        "stock_count": len(rows),
        "top10_weight": round(sum(r["weight"] for r in rows[:10]), 2),
        "top20_weight": round(sum(r["weight"] for r in rows[:20]), 2),
        "holdings": rows,
        "sources": {"end": source(end), "start": source(start) if comparable else None},
    }


# ── 休市日驗證 ───────────────────────────────────────────
def issue(day: str | None, category: str, detail: str) -> dict:
    """category：not_published 尚未公布／source_error 來源異常／data_gap 交易日資料缺漏。"""
    return {"date": day, "category": category, "detail": detail}


def verify_calendar(src, fund_code: str, calendar: list[str], now: datetime,
                    publish_time: dtime) -> dict:
    """三種官方資料互相核對：休市行事曆、實際成交紀錄（calendar）、投信 PCF。

    只有「行事曆有列」或「之後已恢復交易，且投信確定跳過該日」才認定休市；
    抓取失敗與空白回應一律不算休市。
    """
    result = {"closures": [], "issues": [], "unconfirmed": [], "missing_days": [], "schedule": {},
              "verified": True}
    day, end = date.fromisoformat(calendar[0]), now.date()
    schedule = result["schedule"]
    try:
        for year in range(day.year, end.year + 1):
            schedule.update(src.holidays(year))
    except Exception as e:
        result["verified"] = False
        result["issues"].append(issue(None, "source_error", f"休市行事曆無法取得，休市日未驗證：{e}"))
        return result

    def closed(d, reason):
        result["closures"].append({"date": d, "category": "confirmed_closure", "reason": reason})

    while day <= end:
        d = day.isoformat()
        weekend = day.weekday() >= 5
        day += timedelta(days=1)
        if d in calendar:
            if d in schedule:
                closed_note = f"行事曆列為「{schedule[d]}」，但有實際成交資料，以實際資料為準"
                result["closures"].append({"date": d, "category": "calendar_overridden", "reason": closed_note})
        elif weekend:
            continue
        elif d in schedule:
            closed(d, f"官方行事曆休市：{schedule[d]}")
        elif now >= due_at(d, publish_time):
            try:
                found = probe_pcf(src, fund_code, d)[0]
            except Exception as e:
                result["issues"].append(issue(d, "source_error", f"無法查核是否休市：{e}"))
                result["missing_days"].append(d)
                if d > calendar[-1]:
                    result["unconfirmed"].append(d)
                continue
            if found == "found":
                result["issues"].append(issue(d, "data_gap", "投信有持股清單，但證交所缺成交資料"))
                result["missing_days"].append(d)
                if d > calendar[-1]:   # 這天確實該有資料，不能把更早的資料當最新
                    result["unconfirmed"].append(d)
            elif d > calendar[-1]:
                result["unconfirmed"].append(d)
                result["issues"].append(issue(d, "not_published", "尚無成交資料與持股清單，無法確認是臨時休市或尚未公布"))
            elif found == "skipped":
                closed(d, "臨時休市：行事曆未列，市場之後已恢復交易，且投信清單確定跳過該日")
            else:
                result["issues"].append(issue(d, "data_gap", "證交所缺該日資料，投信回應空白，無法確認是否休市"))
                result["missing_days"].append(d)
    return result


def next_due(src, schedule: dict, after: str, publish_time: dtime) -> str:
    """下一個行事曆交易日的應公布時間；過了這個時間，網頁就不能把現有資料當最新。"""
    day, years = date.fromisoformat(after), {int(k[:4]) for k in schedule}
    while True:
        day += timedelta(days=1)
        if day.year not in years:
            years.add(day.year)
            try:
                schedule = {**schedule, **src.holidays(day.year)}
            except Exception:
                pass   # 新年度行事曆尚未公布：只排除週末，寧可提早提醒
        if day.weekday() < 5 and day.isoformat() not in schedule:
            return due_at(day.isoformat(), publish_time).isoformat()


# ── 主流程 ───────────────────────────────────────────────
def recent_trading_days(src, today: date, count: int) -> list[str]:
    days: set[str] = set()
    month = today.replace(day=1)
    for _ in range(4):
        days |= {d for d in src.trading_days(month) if d <= today.isoformat()}
        if len(days) >= count:
            break
        month = (month - timedelta(days=1)).replace(day=1)
    if len(days) < 2:
        raise DataError("交易日曆資料不足")
    return sorted(days)[-count:]


def run(src, fund: str, now: datetime, root: Path = ROOT, days: int = 5,
        allow_count_change: bool = False, publish_time: dtime = DEFAULT_PUBLISH_TIME) -> int:
    """整批通過才更新正式資料。

    先在同一磁碟的暫存副本完整產生並核對，通過才用單一系統呼叫換上整個資料夾；
    任何失敗或中途中斷，正式資料夾都是完整的舊版或完整的新版，不會消失或半套。
    """
    root.mkdir(parents=True, exist_ok=True)
    folder, work = root / fund, root / f".{fund}.staging"
    shutil.rmtree(work, ignore_errors=True)   # 上次中斷留下的暫存，內容一律不採用
    staging = work / "new" / fund
    staging.parent.mkdir(parents=True)
    try:
        if folder.exists():
            shutil.copytree(folder, staging)
        try:
            code = _run(src, fund, now, staging.parent, days, allow_count_change, publish_time)
            problems = verify_folder(staging) if code == 0 else []
        except Exception as e:   # 程式錯誤也要留下紀錄，且不能動到正式資料
            code, problems = 1, [f"更新程式異常：{e!r}"]
        if code == 0 and not problems:
            publish(staging, folder)
            return 0
        failed = work / "failed" / fund
        keep_published_data(staging, folder, failed, now, problems)
        publish(failed, folder)
        print("❌ 本次有失敗項目：正式快照與報表未更新，只記錄錯誤與狀態", file=sys.stderr)
        return 1
    except OSError as e:   # 含「不支援原子互換」：寧可不更新，絕不改用有空窗的做法
        print(f"❌ 無法安全寫入，正式資料維持原樣：{e}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


def exchange_dirs(a: Path, b: Path) -> None:
    """原子互換兩個資料夾（單一系統呼叫，兩個路徑全程都存在）。

    macOS(APFS) 用 renamex_np(RENAME_SWAP)，Linux 用 renameat2(RENAME_EXCHANGE)。
    系統或檔案系統不支援時直接失敗，不退回非原子做法。
    """
    libc = ctypes.CDLL(None, use_errno=True)
    x, y = os.fsencode(a), os.fsencode(b)
    try:
        if sys.platform == "darwin":
            result = libc.renamex_np(x, y, ctypes.c_uint(2))
        elif sys.platform.startswith("linux"):
            result = libc.renameat2(-100, x, -100, y, ctypes.c_uint(2))   # -100 = AT_FDCWD
        else:
            raise OSError(errno.ENOTSUP, f"此系統不支援原子互換：{sys.platform}")
    except AttributeError as e:   # C 函式庫沒有這個呼叫
        raise OSError(errno.ENOSYS, f"系統函式庫不支援原子互換：{e}") from e
    if result != 0:
        err = ctypes.get_errno()
        raise OSError(err, f"原子互換失敗：{os.strerror(err)}", str(b))


def publish(staging: Path, folder: Path) -> None:
    if folder.exists():
        exchange_dirs(staging, folder)   # 換完後 staging 內是舊版，由呼叫端清掉
    else:
        os.replace(staging, folder)      # 第一次發布：單一改名即原子


def data_version(folder: Path) -> str | None:
    """由全部快照內容算出的版本碼；status 與 report 必須帶同一個值。"""
    files = sorted((folder / "snapshots").glob("*.json"))
    if not files:
        return None
    digest = hashlib.sha256()
    for f in files:
        digest.update(f.name.encode() + b"\0" + f.read_bytes() + b"\0")
    return digest.hexdigest()[:16]


def verify_folder(folder: Path) -> list[str]:
    """status.json、report.json、snapshots 是否同一資料版本、日期與內容一致。"""
    try:
        status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
        saved = sorted(f.stem for f in (folder / "snapshots").glob("*.json"))
        latest = saved[-1] if saved else None
        problems = []
        if status.get("latest_basis_date") != latest:
            problems.append(f"status 最新日期 {status.get('latest_basis_date')} ≠ 快照最新日期 {latest}")
        for day in saved:
            s = load_snapshot(folder, day)
            inside = {to_date(r["TranDate"]) for r in s["pcf"]["raw"]["pcf"]}
            if s["basis_date"] != day or inside != {day}:
                problems.append(f"快照 {day} 的內容日期不符")
        version = data_version(folder)
        if status.get("data_version") != version:
            problems.append("status.json 的資料版本與快照不符")
        path = folder / "report.json"
        if not saved:
            return problems + (["沒有快照卻有 report.json"] if path.exists() else [])
        report = json.loads(path.read_text(encoding="utf-8"))
        rebuilt = json.loads(json.dumps(make_report(folder, report["fund"]), ensure_ascii=False))
        if report != rebuilt:
            problems.append(f"report.json 與快照重算結果不一致（報表最新 {max(report['daily'])}，快照最新 {latest}）")
        return problems
    except Exception as e:
        return [f"資料夾無法核對：{e!r}"]


def make_report(folder: Path, fund: str) -> dict:
    saved = sorted(f.stem for f in (folder / "snapshots").glob("*.json"))
    snaps = {d: load_snapshot(folder, d) for d in saved[-21:]}
    daily = {d: build_report(s, snaps.get(s["previous_trading_date"])) for d, s in sorted(snaps.items())[-20:]}
    cumulative = None
    end = snaps[saved[-1]]
    middle = snaps.get(end["previous_trading_date"])
    if middle:
        start = snaps.get(middle["previous_trading_date"])
        if start:
            cumulative = build_report(end, start, "range")
    return {"fund": fund, "name": FUNDS[fund]["name"], "data_version": data_version(folder),
            "daily": daily, "cumulative": cumulative}


def keep_published_data(staging: Path, folder: Path, failed: Path, now: datetime,
                        problems: list[str]) -> None:
    """失敗時在 failed 組出「已發布的快照與報表 ＋ 本次錯誤與狀態」。

    狀態依實際已發布的資料描述；last_success_at 沿用已發布的值。
    """
    failed.parent.mkdir(parents=True, exist_ok=True)
    if folder.exists():
        shutil.copytree(folder, failed)
    else:
        failed.mkdir()
    for message in problems:
        log_error(staging, now, None, message, "source_error")
    try:
        attempt = json.loads((staging / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        attempt = {}
    if problems:   # 程式異常或一致性核對不過：不採用本次推算的狀態
        attempt = {"last_attempt_at": now.isoformat(timespec="seconds"), "data_current": None,
                   "issues": [issue(None, "source_error", m) for m in problems],
                   "message": "更新程式異常或資料核對不通過"}
    path = failed / "status.json"
    status = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    published = sorted(f.stem for f in (failed / "snapshots").glob("*.json"))
    latest = published[-1] if published else None
    for key in ("last_attempt_at", "publish_time", "issues", "warnings", "closures",
                "expected_basis_date", "next_due_at"):
        if key in attempt:
            status[key] = attempt[key]
    current = attempt.get("data_current")
    if current is not None:
        current = bool(latest) and latest >= attempt["expected_basis_date"]
    status.update({"state": "error", "latest_basis_date": latest, "data_current": current,
                   "data_version": data_version(failed),
                   "message": f"{attempt['message']}；本次未更新正式資料"})
    if (staging / "errors.jsonl").exists():
        shutil.copyfile(staging / "errors.jsonl", failed / "errors.jsonl")
    write_json(path, status)


def _run(src, fund: str, now: datetime, root: Path, days: int,
         allow_count_change: bool, publish_time: dtime) -> int:
    folder = root / fund
    status_path = folder / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    status.update({"last_attempt_at": now.isoformat(timespec="seconds"),
                   "publish_time": publish_time.strftime("%H:%M")})
    issues, warnings_all = [], []

    def record(item):
        issues.append(item)
        log_error(folder, now, item["date"], item["detail"], item["category"])

    try:
        calendar = recent_trading_days(src, now.date(), days + 1)
    except Exception as e:
        record(issue(None, "source_error", f"交易日曆取得失敗：{e}"))
        status.update({"state": "error", "message": "無法取得交易日曆，本次未更新任何資料",
                       "data_current": None, "issues": issues})
        write_json(status_path, status)
        return 1

    check = verify_calendar(src, FUNDS[fund]["fund_code"], calendar, now, publish_time)
    for item in check["issues"]:
        record(item)

    targets = list(zip(calendar[:-1], calendar[1:]))
    for prev_day, basis in targets:
        old = load_snapshot(folder, basis)
        try:
            gap = [g for g in check["missing_days"] if prev_day < g <= basis]
            if gap:
                raise DataError(f"交易日曆缺少 {gap[0]}，無法確定相鄰交易日")
            snap, warnings = fetch_snapshot(src, fund, basis, prev_day, now, old)
            if snap is None:
                found = warnings[0]   # "empty" 或 "skipped"
                if basis == calendar[-1] and found == "empty":
                    # 最新一天沒有清單：只是尚未公布，不認定為休市或錯誤
                    if now >= due_at(basis, publish_time):
                        record(issue(basis, "not_published",
                                     f"已過 {publish_time:%H:%M}，投信查詢回應空白（尚未公布）"))
                    else:
                        issues.append(issue(basis, "not_published", "尚未到公布時間"))
                    continue
                raise DataError("投信清單跳過此交易日" if found == "skipped"
                                else "投信查詢回應空白，缺少此交易日清單")
            errors = validate(snap, load_snapshot(folder, prev_day), allow_count_change)
            if errors:
                raise SourceError("驗證未通過，保留原有資料：" + "；".join(errors))
            write_json(folder / "snapshots" / f"{basis}.json", sanitize(snap))
            if basis == calendar[-1] and not snap["assets"]:
                warnings.append("現金／期貨保證金尚無同日官方資料")
            for w in warnings:
                warnings_all.append(f"{basis} {w}")
                log_error(folder, now, basis, w)
            print(f"✅ {basis} 已驗證（股票 {len(parse_pcf(snap['pcf']['raw'])['stocks'])} 檔）")
        except Exception as e:
            record(issue(basis, getattr(e, "category", "source_error"), str(e)))

    saved = sorted(f.stem for f in (folder / "snapshots").glob("*.json"))
    latest = saved[-1] if saved else None
    # 最新「應公布」的交易日：公布時間已過的實際交易日，加上無法確認是否休市的日子
    due = [d for d in [*calendar, *check["unconfirmed"]] if now >= due_at(d, publish_time)]
    expected = max([*due, latest or ""])
    # 休市行事曆沒驗證成功時，無法確定「最新應公布交易日」是哪天
    current = (bool(latest) and latest >= expected) if check["verified"] else None
    failures = [i for i in issues if i["category"] in ("source_error", "data_gap")]
    if failures:
        days_failed = "、".join(dict.fromkeys(i["date"] or "交易日核對" for i in failures))
        state, message = "error", f"{days_failed} 更新異常，詳見錯誤紀錄"
    elif check["unconfirmed"]:
        state, message = "pending", f"{expected} 無法確認是臨時休市或尚未公布"
    elif not current:
        state, message = "pending", f"{expected} 官方資料尚未公布，待更新"
    else:
        state, message = "ok", "資料已通過驗證" + (f"（{len(warnings_all)} 項待核實）" if warnings_all else "")
    status.update({"state": state, "message": message, "expected_basis_date": expected,
                   "latest_basis_date": latest, "data_current": current,
                   "next_due_at": next_due(src, check["schedule"], expected, publish_time),
                   "warnings": warnings_all, "issues": issues, "closures": check["closures"]})

    status["data_version"] = data_version(folder)
    if saved:
        write_json(folder / "report.json", make_report(folder, fund))
    if current and not failures and not check["unconfirmed"]:
        status["last_success_at"] = now.isoformat(timespec="seconds")
    write_json(status_path, status)
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fund", default="00981A", choices=list(FUNDS))
    ap.add_argument("--days", type=int, default=5, help="重新抓取最近幾個交易日")
    ap.add_argument("--allow-count-change", action="store_true")
    ap.add_argument("--publish-time", type=parse_time,
                    default=os.environ.get("ETF_PUBLISH_TIME") or DEFAULT_PUBLISH_TIME.strftime("%H:%M"),
                    help="官方清單應公布時間（台北 HH:MM），也可用環境變數 ETF_PUBLISH_TIME")
    ap.add_argument("--dry-run", action="store_true", help="只抓取、驗算並輸出結果，不改任何正式檔案")
    ap.add_argument("--verify", metavar="DIR", help="只核對某資料夾（含基金子資料夾）的日期一致性")
    args = ap.parse_args()
    if args.verify:
        problems = verify_folder(Path(args.verify) / args.fund)
        print("\n".join(problems) or "一致性核對通過")
        return 1 if problems else 0
    options = dict(days=args.days, allow_count_change=args.allow_count_change,
                   publish_time=args.publish_time)
    if args.dry_run:
        return dry_run(OfficialSource(), args.fund, datetime.now(TPE), **options)
    return run(OfficialSource(), args.fund, datetime.now(TPE), **options)


def dry_run(src, fund: str, now: datetime, root: Path = ROOT, **options) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        if (root / fund).exists():
            shutil.copytree(root / fund, Path(tmp) / fund)
        code = run(src, fund, now, root=Path(tmp), **options)
        folder = Path(tmp) / fund
        print("── dry-run 結果（未寫入任何正式檔案）──")
        print((folder / "status.json").read_text(encoding="utf-8"))
        if code == 0 and (folder / "report.json").exists():
            report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
            for day in sorted(report["daily"])[-2:]:
                print(summary(report["daily"][day]))
        print("dry-run 通過" if code == 0 else "dry-run 失敗")
    return code


def summary(r: dict) -> str:
    changes = r["changes"] and {k: {x["name"]: x["delta_lots"] for x in v} for k, v in r["changes"].items()}
    return json.dumps({
        "basis_date": r["basis_date"], "start_date": r["start_date"], "aum": r["aum"]["value"],
        "nav": r["nav"]["value"], "price": r["price"] and r["price"]["value"],
        "premium_pct": r["premium"]["value"], "cash_pct": r["cash"] and r["cash"]["ratio"],
        "margin_pct": r["futures_margin"] and r["futures_margin"]["ratio"],
        "futures": [(f["code"], f["month"], f["side"], f["contracts"]) for f in r["futures"]],
        "stock_count": r["stock_count"], "top10": r["top10_weight"], "changes": changes}, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
