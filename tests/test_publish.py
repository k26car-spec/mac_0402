"""資料發布：原子互換、中斷、不支援的系統、版本一致性、失敗保護、dry-run。"""
import copy
import errno
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import etf_official as E  # noqa: E402
from test_etf_official import D26, D27, FakeSource, at  # noqa: E402


def tree(folder: Path) -> dict:
    return {str(f.relative_to(folder)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(folder.rglob("*")) if f.is_file()}


def data_only(folder: Path) -> dict:
    """正式資料：快照與報表（不含狀態與錯誤紀錄）。"""
    return {k: v for k, v in tree(folder).items() if k.startswith("snapshots") or k == "report.json"}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.dir = self.root / "00981A"

    def tearDown(self):
        self.tmp.cleanup()

    def run_at(self, src, when):
        return E.run(src, "00981A", at(when), root=self.root, days=3)

    def seed(self):
        """已發布到 11/26 的正確資料。"""
        self.assertEqual(self.run_at(FakeSource(D26), "2026-11-26T17:10"), 0)
        return tree(self.dir), self.json("status.json")

    def json(self, name):
        return json.loads((self.dir / name).read_text(encoding="utf-8"))

    def assert_consistent(self, latest):
        self.assertEqual(E.verify_folder(self.dir), [])
        status, report = self.json("status.json"), self.json("report.json")
        self.assertEqual(status["data_version"], report["data_version"])
        self.assertEqual(status["data_version"], E.data_version(self.dir))
        self.assertEqual((status["latest_basis_date"], max(report["daily"]),
                          max(f.stem for f in (self.dir / "snapshots").glob("*.json"))), (latest,) * 3)


class Versions(Base):
    def test_same_version_and_date_after_success(self):
        self.seed()
        self.assert_consistent(D26)
        first = self.json("status.json")["data_version"]
        self.assertEqual(self.run_at(FakeSource(), "2026-11-27T17:10"), 0)
        self.assert_consistent(D27)
        self.assertNotEqual(self.json("status.json")["data_version"], first)

    def tamper(self, name, edit):
        self.seed()
        path = self.dir / name
        data = json.loads(path.read_text(encoding="utf-8"))
        edit(data)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        self.assertTrue(E.verify_folder(self.dir))

    def test_detects_changed_snapshot(self):
        self.tamper(f"snapshots/{D26}.json", lambda d: d.update(fetched_at="x"))

    def test_detects_report_version(self):
        self.tamper("report.json", lambda d: d.update(data_version="0" * 16))

    def test_detects_status_version(self):
        self.tamper("status.json", lambda d: d.update(data_version="0" * 16))

    def test_detects_status_date(self):
        self.tamper("status.json", lambda d: d.update(latest_basis_date=D27))

    def test_detects_report_content(self):
        self.tamper("report.json", lambda d: d["daily"][D26]["aum"].update(value=1))


class Sanitized(Base):
    """公開快照只留計算與追溯需要的欄位。"""

    def test_no_personal_fields_written(self):
        src = FakeSource()
        for rows in (src.raw[D27]["pcf"], src.raw[D27]["asset"]):
            rows[0].update(EditEmployee="00000", RowCreator="someone", NewPersonalField="x")
        self.assertEqual(self.run_at(src, "2026-11-27T17:10"), 0)
        for f in self.dir.rglob("*.json"):
            text = f.read_text(encoding="utf-8")
            for word in ("EditEmployee", "RowCreator", "NewPersonalField", "someone"):
                self.assertNotIn(word, text, f.name)
        self.assert_consistent(D27)

    def test_repository_data_has_only_whitelisted_fields(self):
        """版本庫裡的快照與測試資料不得帶有白名單以外的欄位。"""
        repo = HERE.parent
        files = [*HERE.glob("fixtures/*.json"), *repo.glob("docs/etf/*/snapshots/*.json")]
        self.assertGreater(len(files), 5)
        for f in files:
            snap = json.loads(f.read_text(encoding="utf-8"))
            self.assertEqual(E.sanitize(snap), snap, str(f.relative_to(repo)))

    def test_calculations_unchanged_and_no_rows_dropped(self):
        from test_etf_official import SNAPS
        a, b = copy.deepcopy(SNAPS[D27]), copy.deepcopy(SNAPS[D26])
        for snap in (a, b):   # 模擬官方原始回應帶有多餘欄位
            raw = snap["pcf"]["raw"]
            for row in raw["pcf"] + raw["asset"] + [d for x in raw["asset"] for d in x["Details"]]:
                row["EditEmployee"] = "00000"
        self.assertNotEqual(E.sanitize(a), a)
        self.assertEqual(E.build_report(E.sanitize(a), E.sanitize(b)), E.build_report(a, b))
        self.assertEqual(E.validate(E.sanitize(a), E.sanitize(b)), [])
        before, after = E.parse_pcf(a["pcf"]["raw"]), E.parse_pcf(E.sanitize(a)["pcf"]["raw"])
        self.assertEqual((len(before["stocks"]), len(before["futures"]), before["values"]),
                         (len(after["stocks"]), len(after["futures"]), after["values"]))
        self.assertEqual(E.sanitize(E.sanitize(a)), E.sanitize(a))


class FailureProtection(Base):
    def failing_validation(self):
        """抓取成功，但 11/27 清單驗算不過。"""
        src = FakeSource()
        stocks = next(a for a in src.raw[D27]["asset"] if a["AssetCode"] == "ST")
        stocks["Details"].pop()
        return src

    def test_fetch_ok_but_validation_fails(self):
        _, before_status = self.seed()
        before = data_only(self.dir)
        self.assertEqual(self.run_at(self.failing_validation(), "2026-11-27T17:10"), 1)
        self.assertEqual(data_only(self.dir), before)   # 快照與報表一個位元組都沒變
        self.assertFalse((self.dir / "snapshots" / f"{D27}.json").exists())
        s = self.json("status.json")
        self.assertEqual((s["state"], s["latest_basis_date"], s["data_current"]), ("error", D26, False))
        self.assertEqual(s["last_success_at"], before_status["last_success_at"])
        self.assertEqual(s["last_attempt_at"], "2026-11-27T17:10:00+08:00")
        self.assertIn("股票清單不完整", (self.dir / "errors.jsonl").read_text(encoding="utf-8"))
        self.assert_consistent(D26)
        changed = {k for k, v in tree(self.dir).items() if before.get(k) != v and k not in before}
        self.assertEqual(changed, {"status.json", "errors.jsonl"})

    def test_repeated_failures_never_move_last_success(self):
        _, s0 = self.seed()
        for when in ("2026-11-27T17:10", "2026-11-27T19:10", "2026-11-27T23:10"):
            self.run_at(self.failing_validation(), when)
            self.assertEqual(self.json("status.json")["last_success_at"], s0["last_success_at"])

    def test_unexpected_exception(self):
        self.seed()
        before = data_only(self.dir)
        with mock.patch.object(E, "make_report", side_effect=[RuntimeError("boom")]):
            self.assertEqual(self.run_at(FakeSource(), "2026-11-27T17:10"), 1)
        self.assertEqual(data_only(self.dir), before)
        self.assert_consistent(D26)

    def test_inconsistent_new_data_is_not_published(self):
        self.seed()
        before = data_only(self.dir)
        real = E._run

        def corrupt(*args):
            code = real(*args)
            report = args[3] / "00981A" / "report.json"
            report.write_text(report.read_text(encoding="utf-8").replace(D27, D26), encoding="utf-8")
            return code

        with mock.patch.object(E, "_run", corrupt):
            self.assertEqual(self.run_at(FakeSource(), "2026-11-27T17:10"), 1)
        self.assertEqual(data_only(self.dir), before)
        self.assert_consistent(D26)

    def test_dry_run_changes_nothing(self):
        self.seed()
        before = tree(self.root)
        for src, code in ((FakeSource(), 0), (self.failing_validation(), 1)):
            with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
                self.assertEqual(E.dry_run(src, "00981A", at("2026-11-27T17:10"), root=self.root, days=3), code)
            self.assertEqual(tree(self.root), before)


CHILD = """
import os, signal, sys
sys.path[:0] = [{tests!r}, {repo!r}]
from pathlib import Path
import etf_official as E
from test_etf_official import FakeSource, D27, at
die = lambda: os.kill(os.getpid(), signal.SIGKILL)
{patch}
src = FakeSource()
{prepare}
E.run(src, "00981A", at("2026-11-27T17:10"), root=Path({root!r}), days=3)
print("not killed")
"""


class Interrupted(Base):
    """用 SIGKILL 真的砍掉行程（finally 不會執行）。"""

    def kill_run(self, patch, prepare=""):
        code = CHILD.format(tests=str(HERE), repo=str(HERE.parent), root=str(self.root),
                            patch=textwrap.dedent(patch), prepare=prepare)
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(r.returncode, -signal.SIGKILL, r.stdout + r.stderr)

    def assert_old_then_recovers(self, before):
        self.assertEqual(tree(self.dir), before)
        self.assert_consistent(D26)
        self.assertEqual(self.run_at(FakeSource(), "2026-11-27T19:10"), 0)
        self.assert_consistent(D27)
        self.assertEqual([p.name for p in self.root.iterdir()], ["00981A"])   # 殘留暫存已清掉

    def test_killed_while_writing_staging(self):
        for nth in (1, 2, 3, 4):   # 寫完第 N 個檔案後中斷
            with self.subTest(nth=nth):
                self.tearDown(); self.setUp()
                before, _ = self.seed()
                self.kill_run(f"""
                    real, n = E.write_json, [0]
                    def w(*a):
                        real(*a); n[0] += 1
                        if n[0] == {nth}: die()
                    E.write_json = w
                    """)
                self.assert_old_then_recovers(before)

    def test_killed_just_before_switch(self):
        before, _ = self.seed()
        self.kill_run("E.exchange_dirs = lambda a, b: die()")
        self.assert_old_then_recovers(before)

    def test_killed_just_after_switch(self):
        self.seed()
        self.kill_run("""
            real = E.exchange_dirs
            def x(a, b):
                real(a, b); die()
            E.exchange_dirs = x
            """)
        self.assert_consistent(D27)   # 完整新版
        self.assertEqual(self.run_at(FakeSource(), "2026-11-27T19:10"), 0)
        self.assertEqual([p.name for p in self.root.iterdir()], ["00981A"])

    def test_killed_while_publishing_failure_status(self):
        before, _ = self.seed()
        self.kill_run("E.exchange_dirs = lambda a, b: die()",
                      prepare="src.fail.add(D27)")
        self.assert_old_then_recovers(before)

    def two_versions(self):
        a, b = self.root / "live", self.root / "next"
        for folder, tag in ((a, "A"), (b, "B")):
            folder.mkdir()
            for name in ("status", "report", "snapshot"):
                (folder / name).write_text(tag * 2000)
        return a, b

    SWAPPER = ("import sys; sys.path.insert(0, {repo!r}); import etf_official as E; from pathlib import Path\n"
               "while True: E.exchange_dirs(Path({b!r}), Path({a!r}))")

    def swapper(self, a, b):
        return subprocess.Popen([sys.executable, "-c",
                                 self.SWAPPER.format(repo=str(HERE.parent), a=str(a), b=str(b))])

    def read_version(self, folder):
        """開一次資料夾控制代碼，從同一版本讀三個檔案。"""
        fd = os.open(folder, os.O_RDONLY)
        try:
            tags = set()
            for name in ("status", "report", "snapshot"):
                f = os.open(name, os.O_RDONLY, dir_fd=fd)
                data = os.read(f, 4000)
                os.close(f)
                self.assertEqual(len(data), 2000)
                tags.add(data[:1])
            self.assertEqual(len(tags), 1, tags)
            return tags.pop()
        finally:
            os.close(fd)

    def test_reader_never_sees_gap_or_mix_during_switch(self):
        a, b = self.two_versions()
        proc = self.swapper(a, b)
        seen, missing, end = set(), 0, time.time() + 2
        try:
            reads = 0
            while time.time() < end or len(seen) < 2:
                missing += not os.path.exists(a)
                seen.add(self.read_version(a))
                reads += 1
                self.assertLess(time.time(), end + 20)
        finally:
            proc.kill(); proc.wait()
        self.assertEqual((missing, seen), (0, {b"A", b"B"}))
        self.assertGreater(reads, 500)

    def test_random_kill_during_switch_loop(self):
        a, b = self.two_versions()
        for i in range(30):
            proc = self.swapper(a, b)
            time.sleep(0.05 + (i % 7) * 0.013)
            proc.kill(); proc.wait()
            self.assertTrue(a.is_dir() and b.is_dir(), i)
            self.assertNotEqual(self.read_version(a), self.read_version(b))


class Unsupported(Base):
    def assert_safe_failure(self, patcher):
        before, _ = self.seed()
        moved = []
        real_replace = os.replace

        def spy(src, dst):
            if Path(dst) == self.dir or Path(src) == self.dir:
                moved.append((src, dst))
            return real_replace(src, dst)

        with patcher, mock.patch.object(E.os, "replace", spy), mock.patch("sys.stderr"):
            self.assertEqual(self.run_at(FakeSource(), "2026-11-27T17:10"), 1)
        self.assertEqual(moved, [])   # 沒有退回「改名兩次」之類的做法
        self.assertEqual(tree(self.dir), before)
        self.assert_consistent(D26)

    def libc(self, code):
        def fail(*args):
            E.ctypes.set_errno(code)
            return -1
        lib = mock.Mock(renamex_np=fail, renameat2=fail)
        return mock.patch.object(E.ctypes, "CDLL", return_value=lib)

    def test_filesystem_not_supported(self):
        self.assert_safe_failure(self.libc(errno.ENOTSUP))

    def test_kernel_not_supported(self):
        self.assert_safe_failure(self.libc(errno.ENOSYS))

    def test_invalid_argument(self):
        self.assert_safe_failure(self.libc(errno.EINVAL))

    def test_missing_libc_function(self):
        self.assert_safe_failure(mock.patch.object(E.ctypes, "CDLL", return_value=object()))

    def test_unknown_platform(self):
        self.assert_safe_failure(mock.patch.object(E.sys, "platform", "win32"))


if __name__ == "__main__":
    unittest.main()
