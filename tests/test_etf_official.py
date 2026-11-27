"""驗收測試。fixtures 是 2026-11-23～27 的官方原始回應（不連網）。"""
import copy
import json
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import etf_official as E  # noqa: E402

FIX = Path(__file__).parent / "fixtures"
SNAPS = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in FIX.glob("*.json")}
D23, D24, D25, D26, D27 = sorted(SNAPS)


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=E.TPE)


class FakeSource:
    """published = 此刻官方已公布到哪一天。"""

    def __init__(self, published=D27, calendar=None):
        self.published = published
        self.calendar = calendar or sorted(SNAPS)
        self.raw = {d: copy.deepcopy(s["pcf"]["raw"]) for d, s in SNAPS.items()}
        self.fail = set()
        self.pcf_calls = []
        self.closed = {}          # 官方休市行事曆
        self.no_data = set()      # 投信沒有清單的日期

    def holidays(self, year):
        if "holidays" in self.fail:
            raise E.DataError("schedule down")
        return dict(self.closed)

    def calendar_url(self, m): return "cal"
    def price_url(self, f, m): return "price"

    def trading_days(self, month):
        if "calendar" in self.fail:
            raise E.DataError("calendar down")
        return [d for d in self.calendar if d <= self.published and d[:7] == month.isoformat()[:7]]

    def prices(self, fund, month):
        return {d: s["price"]["close"] for d, s in SNAPS.items() if d <= self.published}

    def pcf(self, code, query):
        q = query.isoformat()
        for d, s in SNAPS.items():
            if s["pcf"]["query_date"] == q and d <= self.published and d not in self.no_data:
                self.pcf_calls.append(d)
                if d in self.fail:
                    raise E.DataError("timeout")
                return copy.deepcopy(self.raw[d])
        return {"pcf": [], "asset": []}

    def assets(self, code):
        """基金頁永遠只有最新一天。"""
        p = E.parse_pcf(self.raw[self.published])
        block = lambda c, v: {"AssetCode": c, "Value": v}
        return [
            block("NAV", p["values"]["NAV"]), block("OUT_UNIT", p["values"]["OUT_UNIT"]),
            {"AssetCode": "ST", "Value": p["stock_total"], "Details": p["stocks"]},
            block("CASH", 37568139028.0), block("GDM", 7494829754.0)]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.dir = self.root / "00981A"

    def tearDown(self):
        self.tmp.cleanup()

    def run_at(self, src, when, **kw):
        kw.setdefault("days", 3)
        return E.run(src, "00981A", at(when), root=self.root, **kw)

    def read(self, name):
        return json.loads((self.dir / name).read_text(encoding="utf-8"))

    def snap_text(self, d):
        return (self.dir / "snapshots" / f"{d}.json").read_text(encoding="utf-8")


def stock(shares, code="6805", weight=1.0):
    return {"DetailCode": code, "DetailName": code, "Share": shares, "NavRate": weight, "Amount": weight}


class SpecCases(unittest.TestCase):
    """需求書指定的六個情境。"""

    def delta(self, a, b):
        return E.compare_holdings([stock(a)], [stock(b)])["add"][0]["delta_lots"]

    def test_1_daily_and_range(self):
        self.assertEqual(self.delta(1676000, 1801000), 125)
        self.assertEqual(self.delta(1801000, 1877000), 76)
        self.assertEqual(self.delta(1676000, 1877000), 201)

    def test_2_stock_lots(self):
        r = E.compare_holdings([], [stock(1533000)])["new"][0]
        self.assertEqual(r["delta_lots"], 1533)

    def test_3_futures_contracts_not_divided(self):
        f = E.build_report(SNAPS[D27], SNAPS[D26])["futures"][0]
        self.assertEqual((f["contracts"], f["month"], f["side"]), (1533, "2026/12", "多單"))

    def test_4_missing_previous_makes_no_conclusion(self):
        r = E.build_report(SNAPS[D27], None)
        self.assertFalse(r["comparable"])
        self.assertIsNone(r["changes"])
        self.assertIsNone(r["nav"]["change_pct"])

    def test_5_top10_stocks_only_and_filled_from_full_list(self):
        snap = copy.deepcopy(SNAPS[D27])
        for a in snap["pcf"]["raw"]["asset"]:
            if a["AssetCode"] == "GD":
                a["Details"][0]["NavRate"] = 99.0
        r = E.build_report(snap, SNAPS[D26])
        codes = [h["code"] for h in r["holdings"][:10]]
        self.assertEqual(len(codes), 10)
        self.assertNotIn("TX", codes)
        self.assertEqual(r["top10_weight"], 61.56)
        self.assertEqual(r["top20_weight"], 80.79)

    def test_6_price_nav_date_mismatch(self):
        p = E.premium(21.58, D27, 21.80, D26)
        self.assertIsNone(p["value"])
        self.assertIn(D26, p["note"])
        self.assertIn(D27, p["note"])


class Official(unittest.TestCase):
    """用官方原始資料核對 11/26、11/27、兩日累計。"""

    def lots(self, r):
        return {k: {x["name"]: x["delta_lots"] for x in v} for k, v in r["changes"].items()}

    def test_1126(self):
        c = self.lots(E.build_report(SNAPS[D26], SNAPS[D25]))
        self.assertEqual(c["new"], {"中砂": 200})
        self.assertEqual(c["delete"], {"南茂": -1})
        self.assertEqual(c["reduce"], {})
        self.assertEqual(c["add"], {
            "緯創": 2291, "日月光投控": 2121, "金像電": 718, "緯穎": 578, "貿聯-KY": 446, "同欣電": 370,
            "智邦": 320, "奇鋐": 236, "旺矽": 130, "富世達": 125, "大立光": 1})

    def test_1127(self):
        r = E.build_report(SNAPS[D27], SNAPS[D26])
        self.assertEqual(self.lots(r), {"new": {}, "add": {"富世達": 76}, "reduce": {"南電": -2467}, "delete": {}})
        self.assertAlmostEqual(r["price"]["change_pct"], (21.58 / 21.89 - 1) * 100)
        self.assertAlmostEqual(r["nav"]["change_pct"], (21.69 / 21.80 - 1) * 100)
        self.assertAlmostEqual(r["premium"]["value"], (21.58 / 21.69 - 1) * 100)
        self.assertEqual(r["aum"]["value"], 278019574075)
        self.assertEqual(r["stock_count"], 51)

    def test_range(self):
        r = E.build_report(SNAPS[D27], SNAPS[D25], "range")
        self.assertEqual(self.lots(r)["add"]["富世達"], 201)
        self.assertEqual((r["start_date"], r["basis_date"]), (D25, D27))

    def test_daily_rejects_non_adjacent(self):
        r = E.build_report(SNAPS[D27], SNAPS[D25])
        self.assertFalse(r["comparable"])
        self.assertIsNone(r["changes"])

    def test_both_official_date_formats(self):
        self.assertEqual(E.to_date("/Date(1795708800000)/"), "2026-11-27")
        self.assertEqual(E.to_date("2026-11-27T00:00:00"), "2026-11-27")
        self.assertIsNone(E.to_date("/Date(-62135596800000)/"))
        self.assertIsNone(E.to_date("0001-01-01T00:00:00"))


class Schedule(Base):
    def test_cross_midnight_run_uses_official_date(self):
        """重現原始事故：11/26 的排程延到 11/27 02:56。"""
        self.assertEqual(self.run_at(FakeSource(D26), "2026-11-27T02:56"), 0)
        r = self.read("report.json")
        self.assertEqual(max(r["daily"]), D26)
        self.assertEqual(r["daily"][D26]["start_date"], D25)
        self.assertEqual(self.run_at(FakeSource(D27), "2026-11-27T17:10"), 0)
        day = self.read("report.json")["daily"][D27]
        self.assertEqual(day["start_date"], D26)
        self.assertEqual(day["changes"]["add"][0]["delta_lots"], 76)

    def test_weekend(self):
        for when in ("2026-11-28T09:00", "2026-11-29T23:10"):
            self.assertEqual(self.run_at(FakeSource(), when), 0)
            s = self.read("status.json")
            self.assertEqual((s["state"], s["latest_basis_date"]), ("ok", D27))

    def closed_on_25(self):
        """模擬 11/25 沒開市：證交所、投信都沒有該日資料。"""
        src = FakeSource(calendar=[D23, D24, D26, D27])
        src.no_data.add(D25)
        out = lambda d: E.parse_pcf(src.raw[d])["values"]["OUT_UNIT"]
        for row in src.raw[D26]["pcf"]:   # 單位差異改成相對 11/24
            if row["PCFCode"] == "DIFF_UNIT":
                row["Amount"] = out(D26) - out(D24)
        return src

    def test_holiday_uses_previous_trading_day(self):
        src = self.closed_on_25()
        src.closed = {D25: "測試假日"}
        self.assertEqual(self.run_at(src, "2026-11-28T09:00"), 0)
        self.assertEqual(self.read("report.json")["daily"][D26]["start_date"], D24)
        self.assertIn("官方行事曆休市", self.read("status.json")["closures"][0]["reason"])

    def test_unscheduled_closure_confirmed_by_later_trading(self):
        self.assertEqual(self.run_at(self.closed_on_25(), "2026-11-28T09:00"), 0)
        self.assertIn("臨時休市", self.read("status.json")["closures"][0]["reason"])

    def test_calendar_missing_a_real_day_is_error(self):
        """證交所清單漏掉 11/26、投信卻有資料：不可跨日比較。"""
        src = FakeSource(calendar=[D23, D24, D25, D27])
        self.assertEqual(self.run_at(src, "2026-11-28T09:00"), 1)
        self.assertEqual(self.read("status.json")["state"], "error")
        self.assertFalse((self.dir / "snapshots" / f"{D27}.json").exists())

    def test_expected_day_without_any_data_is_not_ok(self):
        """交易日晚上兩邊都沒資料：可能臨時休市或延遲，不能顯示更新正常。"""
        self.assertEqual(self.run_at(FakeSource(D26), "2026-11-27T23:10"), 0)
        s = self.read("status.json")
        self.assertEqual((s["state"], s["expected_basis_date"], s["latest_basis_date"]), ("pending", D27, D26))
        self.assertNotIn("last_success_at", s)

    def test_scheduled_holiday_stays_ok(self):
        src = FakeSource(D26)
        src.closed = {D27: "測試假日"}
        self.assertEqual(self.run_at(src, "2026-11-27T23:10"), 0)
        self.assertEqual(self.read("status.json")["state"], "ok")

    def test_holiday_schedule_unavailable_is_error(self):
        src = FakeSource()
        src.fail.add("holidays")
        self.assertEqual(self.run_at(src, "2026-11-27T17:10"), 1)
        self.assertNotIn("last_success_at", self.read("status.json"))

    def test_missed_runs_are_backfilled(self):
        self.run_at(FakeSource(D25), "2026-11-25T17:10", days=2)
        self.run_at(FakeSource(D27), "2026-11-27T17:10", days=3)
        self.assertEqual(self.read("report.json")["daily"][D26]["start_date"], D25)

    def not_published(self):
        src = FakeSource()
        src.no_data.add(D27)
        return src

    def test_before_publish_time_is_not_stale(self):
        self.assertEqual(self.run_at(self.not_published(), "2026-11-27T15:00"), 0)
        s = self.read("status.json")
        self.assertEqual((s["state"], s["data_current"], s["expected_basis_date"]), ("ok", True, D26))
        self.assertEqual([i["category"] for i in s["issues"]], ["not_published"])
        self.assertEqual(s["next_due_at"], "2026-11-27T17:00:00+08:00")

    def test_after_publish_time_is_pending_not_error_or_closure(self):
        for when in ("2026-11-27T17:00", "2026-11-28T08:30", "2026-11-29T23:00"):
            self.assertEqual(self.run_at(self.not_published(), when), 0, when)
            s = self.read("status.json")
            self.assertEqual((s["state"], s["data_current"], s["expected_basis_date"], s["latest_basis_date"]),
                             ("pending", False, D27, D26), when)
            self.assertEqual([i["category"] for i in s["issues"]], ["not_published"])
            self.assertEqual(s["closures"], [])
            self.assertNotIn("last_success_at", s)
        self.assertIn("not_published", (self.dir / "errors.jsonl").read_text(encoding="utf-8"))

    def test_publish_time_is_adjustable(self):
        later = E.parse_time("18:30")
        self.assertEqual(self.run_at(self.not_published(), "2026-11-27T17:10", publish_time=later), 0)
        s = self.read("status.json")
        self.assertEqual((s["state"], s["publish_time"], s["next_due_at"]),
                         ("ok", "18:30", "2026-11-27T18:30:00+08:00"))
        self.run_at(self.not_published(), "2026-11-27T18:30", publish_time=later)
        self.assertEqual(self.read("status.json")["state"], "pending")
        with self.assertRaises(ValueError):
            E.parse_time("25:00")

    def test_published_early_counts_as_current(self):
        self.assertEqual(self.run_at(FakeSource(), "2026-11-27T16:40"), 0)
        s = self.read("status.json")
        self.assertEqual((s["state"], s["expected_basis_date"], s["next_due_at"]),
                         ("ok", D27, "2026-11-30T17:00:00+08:00"))

    def test_long_holiday_stays_current(self):
        """連假期間排程照跑：資料仍是最新交易日，下一次應公布時間跳過整段假期。"""
        src = FakeSource()
        src.closed = {f"2026-11-30": "測試連假", "2026-12-01": "測試連假", "2026-12-02": "測試連假"}
        self.assertEqual(self.run_at(src, "2026-12-02T23:10"), 0)
        s = self.read("status.json")
        self.assertEqual((s["state"], s["data_current"], s["latest_basis_date"]), ("ok", True, D27))
        self.assertEqual(s["next_due_at"], "2026-12-03T17:00:00+08:00")
        self.assertEqual(len([c for c in s["closures"] if c["category"] == "confirmed_closure"]), 3)


class Probe(Base):
    """PCF 查詢三種結果，以及空白、跳過、網路失敗、尚未公布的處理。"""

    def categories(self):
        return {(i["date"], i["category"]) for i in self.read("status.json")["issues"]}

    def test_found(self):
        state, got = E.probe_pcf(FakeSource(), "49YTW", D26)
        self.assertEqual((state, E.pcf_basis_date(got[0]), got[1]), ("found", D26, D27))

    def test_skipped(self):
        src = FakeSource()
        src.no_data.add(D25)
        self.assertEqual(E.probe_pcf(src, "49YTW", D25), ("skipped", None))

    def test_empty(self):
        src = FakeSource()
        src.no_data.add(D27)
        self.assertEqual(E.probe_pcf(src, "49YTW", D27), ("empty", None))

    def test_blank_api_is_never_a_closure(self):
        """API 整個回空白，且證交所少一天：不能判定休市。"""
        src = FakeSource(calendar=[D23, D24, D26, D27])
        src.no_data.update(SNAPS)
        self.assertEqual(self.run_at(src, "2026-11-28T09:00"), 1)
        s = self.read("status.json")
        self.assertEqual(s["closures"], [])
        self.assertIn((D25, "data_gap"), self.categories())
        self.assertIn((D27, "not_published"), self.categories())

    def test_skipped_trading_day_is_data_gap(self):
        src = FakeSource()
        src.no_data.add(D26)
        self.assertEqual(self.run_at(src, "2026-11-28T09:00"), 1)
        self.assertIn((D26, "data_gap"), self.categories())
        self.assertFalse((self.dir / "report.json").exists())   # 整批不發布

    def test_network_failure_is_source_error_not_closure(self):
        class Down(FakeSource):
            def pcf(self, code, query):
                raise E.SourceError("連線逾時")
        src = Down(calendar=[D23, D24, D26, D27])
        self.assertEqual(self.run_at(src, "2026-11-28T09:00"), 1)
        s = self.read("status.json")
        self.assertEqual((s["state"], s["closures"]), ("error", []))
        self.assertIn((D25, "source_error"), self.categories())
        self.assertIn((D27, "source_error"), self.categories())

    def test_calendar_endpoint_down_is_source_error(self):
        src = FakeSource()
        src.fail.add("calendar")
        self.assertEqual(self.run_at(src, "2026-11-28T09:00"), 1)
        s = self.read("status.json")
        self.assertIsNone(s["data_current"])
        self.assertEqual({i["category"] for i in s["issues"]}, {"source_error"})

    def test_holiday_schedule_down_cannot_claim_current(self):
        src = FakeSource()
        src.fail.add("holidays")
        self.assertEqual(self.run_at(src, "2026-11-27T17:10"), 1)
        s = self.read("status.json")
        self.assertEqual((s["state"], s["data_current"]), ("error", None))
        self.assertNotIn("last_success_at", s)

    def test_exchange_lagging_behind_issuer_is_not_current(self):
        """證交所還沒有 11/27，投信已經有：不能把 11/26 標成最新。"""
        self.run_at(FakeSource(D26), "2026-11-26T17:10")
        before = self.read("status.json")["last_success_at"]
        src = FakeSource(calendar=[D23, D24, D25, D26])
        self.assertEqual(self.run_at(src, "2026-11-27T23:10"), 1)
        s = self.read("status.json")
        self.assertEqual((s["state"], s["data_current"], s["expected_basis_date"], s["latest_basis_date"]),
                         ("error", False, D27, D26))
        self.assertEqual(s["last_success_at"], before)

    def test_failure_keeps_previous_last_success(self):
        self.run_at(FakeSource(D26), "2026-11-26T17:10")
        before = self.read("status.json")["last_success_at"]
        src = FakeSource()
        src.no_data.add(D27)
        self.run_at(src, "2026-11-27T23:10")
        s = self.read("status.json")
        self.assertEqual((s["last_success_at"], s["data_current"]), (before, False))

    def test_real_client_rejects_malformed_response(self):
        """HTTP 200 但不是預期格式（改版、錯誤頁）≠ 空白。"""
        class Resp:
            def __init__(self, body): self.body = body
            def json(self): return json.loads(self.body)
        src = E.OfficialSource.__new__(E.OfficialSource)
        src.client = type("C", (), {"cookies": {"a": 1}})()
        for body in ("<html>error</html>", "{}", '{"error": 1}'):
            src._request = lambda *a, **k: Resp(body)
            with self.assertRaises(E.SourceError, msg=body):
                src.pcf("49YTW", date(2026, 11, 30))
        src._request = lambda *a, **k: Resp('{"pcf": [], "asset": []}')
        self.assertEqual(src.pcf("49YTW", date(2026, 11, 28)), {"pcf": [], "asset": []})


class Safety(Base):
    def seed(self):
        self.assertEqual(self.run_at(FakeSource(), "2026-11-27T17:10"), 0)
        return self.snap_text(D27), self.read("status.json")["last_success_at"]

    def expect_rejected(self, src, before, success, keyword):
        self.assertEqual(self.run_at(src, "2026-11-27T19:10"), 1)
        self.assertEqual(self.snap_text(D27), before)
        s = self.read("status.json")
        self.assertEqual((s["state"], s["last_success_at"]), ("error", success))
        self.assertIn(keyword, (self.dir / "errors.jsonl").read_text(encoding="utf-8"))

    def test_fetch_failure_keeps_good_data(self):
        before, ok = self.seed()
        src = FakeSource()
        src.fail.add(D27)
        self.expect_rejected(src, before, ok, "timeout")

    def test_previous_fetch_failure_no_conclusion(self):
        src = FakeSource()
        src.fail.add(D26)
        self.assertEqual(self.run_at(src, "2026-11-27T17:10"), 1)
        self.assertFalse((self.dir / "report.json").exists())   # 前期抓不到：不產生任何結論
        self.assertFalse(list((self.dir / "snapshots").glob("*.json")))
        self.assertIsNone(self.read("status.json")["latest_basis_date"])

    def test_calendar_failure(self):
        before, ok = self.seed()
        src = FakeSource()
        src.fail.add("calendar")
        self.expect_rejected(src, before, ok, "交易日曆")

    def stocks(self, src):
        return next(a for a in src.raw[D27]["asset"] if a["AssetCode"] == "ST")

    def test_filtered_zero_weight_stocks_rejected(self):
        """舊程式的 51 → 38 檔。"""
        before, ok = self.seed()
        src = FakeSource()
        block = self.stocks(src)
        block["Details"] = [s for s in block["Details"] if s["NavRate"] > 0]
        self.assertEqual(len(block["Details"]), 38)
        self.expect_rejected(src, before, ok, "股票清單不完整")

    def test_count_anomaly_even_if_total_matches(self):
        before, ok = self.seed()
        src = FakeSource()
        block = self.stocks(src)
        block["Details"] = [s for s in block["Details"] if s["NavRate"] > 0]
        block["Value"] = sum(s["Amount"] for s in block["Details"])
        self.expect_rejected(src, before, ok, "股票檔數異常")

    def test_wrong_date_rejected(self):
        before, ok = self.seed()
        src = FakeSource()
        self.stocks(src)["Details"][0]["TranDate"] = "2026-11-26T00:00:00"
        self.expect_rejected(src, before, ok, "日期不符")

    def test_rerun_refetches_and_updates(self):
        self.seed()
        src = FakeSource()
        row = next(s for s in self.stocks(src)["Details"] if s["DetailCode"] == "6805")
        row["Share"] += 1000   # 官方更正
        self.assertEqual(self.run_at(src, "2026-11-27T23:10"), 0)
        self.assertIn(D27, src.pcf_calls)
        day = self.read("report.json")["daily"][D27]
        self.assertEqual(day["changes"]["add"][0]["delta_lots"], 77)

    def test_cash_only_from_same_date_and_never_blanked(self):
        self.seed()
        r = self.read("report.json")["daily"]
        self.assertAlmostEqual(r[D27]["cash"]["ratio"], 13.5128, places=3)
        self.assertIsNone(r[D26]["cash"])   # 沒留存就待核實，不借用別天
        older = copy.deepcopy(FakeSource())
        older.assets = lambda code: []
        self.assertEqual(self.run_at(older, "2026-11-28T07:10"), 0)
        self.assertIsNotNone(self.read("report.json")["daily"][D27]["cash"])


if __name__ == "__main__":
    unittest.main()
