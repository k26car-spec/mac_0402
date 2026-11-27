"""workflow 的三種執行模式，以及用本機暫存 Git 倉庫實跑提交步驟（不連 GitHub）。"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
import etf_official as E  # noqa: E402
from test_etf_official import D26, D27, FakeSource, at  # noqa: E402

WF = REPO / ".github" / "workflows"
LEGACY, OFFICIAL = WF / "update_data.yml", WF / "etf_official.yml"
LEGACY_FILES = ["data.json", "docs/data.json", "baseline.json"]
FUND = "docs/etf/00981A"


def commit_script(path: Path) -> str:
    """取出名稱以 Commit 開頭那一步的 run 內容（該步驟必須在檔案最後）。"""
    text = path.read_text(encoding="utf-8")
    block = re.search(r"- name: Commit.*?run: \|\n(.*)\Z", text, re.S).group(1)
    return "\n".join(line[10:] for line in block.splitlines())


def jobs() -> dict:
    text = OFFICIAL.read_text(encoding="utf-8").split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([\w-]+):\n", text, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def would_run(event, *, enabled=None, deploy=None, ref="refs/heads/main") -> set:
    """把各 job 的 if 條件實際求值。未設定的 variable／input 在 GitHub 是空值。"""
    result = set()
    for name, body in jobs().items():
        expr = re.search(r"^    if: \$\{\{ (.*) \}\}$", body, re.M).group(1)
        py = expr.replace("&&", " and ").replace("||", " or ")
        for token, var in (("github.event_name", "event"), ("github.ref", "ref"),
                           ("vars.ETF_OFFICIAL_ENABLED", "enabled"), ("inputs.deploy", "deploy")):
            py = py.replace(token, var)
        py = re.sub(r"\btrue\b(?!')", "True", py)
        if eval(py, {"__builtins__": {}}, dict(event=event, ref=ref, enabled=enabled, deploy=deploy)):
            result.add(name)
    return result


class Modes(unittest.TestCase):
    def test_scheduled_is_off_by_default(self):
        for value in (None, "", "false", "TRUE-ish", "0"):
            self.assertEqual(would_run("schedule", enabled=value), set(), value)

    def test_scheduled_enabled(self):
        self.assertEqual(would_run("schedule", enabled="true"), {"publish"})
        self.assertEqual(would_run("schedule", enabled="true", ref="refs/heads/other"), set())

    def test_manual_default_is_dry_run(self):
        for enabled in (None, "true"):
            for ref in ("refs/heads/main", "refs/heads/feature"):
                self.assertEqual(would_run("workflow_dispatch", enabled=enabled, deploy=False, ref=ref), {"dry-run"})

    def test_manual_deploy_on_main(self):
        for enabled in (None, "false", "true"):
            self.assertEqual(would_run("workflow_dispatch", enabled=enabled, deploy=True), {"publish"})

    def test_manual_deploy_elsewhere_is_rejected(self):
        for ref in ("refs/heads/feature", "refs/tags/main"):
            self.assertEqual(would_run("workflow_dispatch", deploy=True, ref=ref), {"guard"})
        self.assertIn("exit 1", jobs()["guard"])

    def test_deploy_input_defaults_false(self):
        self.assertRegex(OFFICIAL.read_text(encoding="utf-8"),
                         r"deploy:\n\s+description: .*\n\s+type: boolean\n\s+default: false")

    def test_dry_run_job_cannot_write(self):
        body = jobs()["dry-run"]
        self.assertIn("contents: read", body)
        self.assertIn("persist-credentials: false", body)
        self.assertIn("--dry-run", body)
        for bad in ("contents: write", "git push", "git commit", "git add"):
            self.assertNotIn(bad, body)

    def test_only_publish_can_write(self):
        top = OFFICIAL.read_text(encoding="utf-8").split("\njobs:\n")[0]
        self.assertIn("permissions:\n  contents: read", top)
        self.assertEqual([n for n, b in jobs().items() if "contents: write" in b], ["publish"])

    def test_tests_run_before_fetch_and_commit_needs_fetch(self):
        body = jobs()["publish"]
        self.assertLess(body.index("- name: Test"), body.index("id: fetch"))
        self.assertIn("if: ${{ !cancelled() && steps.fetch.outcome != 'skipped' }}", body)


class Static(unittest.TestCase):
    def test_no_destructive_git(self):
        for f in WF.glob("*.yml"):
            code = "\n".join(l for l in f.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("#"))
            for bad in (r"--force", r"push\s+.*\s-f\b", r"--orphan", r"reset\s+--hard", r"push\s+\S+\s+\+"):
                self.assertIsNone(re.search(bad, code), f"{f.name}: {bad}")

    def test_written_paths_do_not_overlap(self):
        legacy = " ".join(re.findall(r"git add (.+)", commit_script(LEGACY))).split()
        self.assertEqual(legacy, LEGACY_FILES)
        script = commit_script(OFFICIAL)
        self.assertEqual(re.findall(r"git add (.+)", script), ["-A docs/etf", '"$f"'])
        self.assertIn("docs/etf/*/status.json docs/etf/*/errors.jsonl", script)

    def test_verify_before_commit_and_after_rebase(self):
        script = commit_script(OFFICIAL)
        self.assertLess(script.index('--verify "$check/docs/etf"'), script.index("git commit"))
        self.assertRegex(script, r"git pull --rebase origin main && python3 etf_official.py --verify docs/etf && git push")

    def test_gitignore(self):
        def ignored(path):
            return subprocess.run(["git", "check-ignore", "-q", "--no-index", path], cwd=REPO).returncode == 0
        for path in (f"{FUND}/report.json", f"{FUND}/status.json", f"{FUND}/errors.jsonl",
                     f"{FUND}/snapshots/{D27}.json", "docs/etf/README.md", "docs/etf-official.js",
                     "etf_official.py", f"tests/fixtures/{D27}.json", "scripts/rollback_00981a.sh"):
            self.assertFalse(ignored(path), path)
        for path in ("docs/etf/.00981A.staging/new/00981A/status.json",
                     "docs/etf/.00981A.staging/failed/00981A/snapshots/x.json", ".trail/learnings/x.md",
                     "__pycache__/x.pyc", "tests/__pycache__/x.pyc"):
            self.assertTrue(ignored(path), path)


class PushSimulation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
                    "FETCH_OUTCOME": "success", "PYTHONDONTWRITEBYTECODE": "1"}
        self.remote = self.root / "remote.git"
        self.git(self.root, "init", "-q", "--bare", "-b", "main", str(self.remote))
        seed = self.root / "seed"
        self.git(self.root, "clone", "-q", str(self.remote), str(seed))
        self.git(seed, "checkout", "-q", "-B", "main")
        for name in [*LEGACY_FILES, "market-analysis.json"]:
            self.write(seed, name, "seed")
        for name in ("etf_official.py", ".gitignore"):
            shutil.copy(REPO / name, seed / name)
        self.update(seed, D26, "2026-11-26T17:10")
        self.commit_push(seed, "seed")

    def tearDown(self):
        self.tmp.cleanup()

    def update(self, repo, published, when, fail=()):
        """用正式程式產生一次資料更新。"""
        src = FakeSource(published)
        src.fail.update(fail)
        with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            return E.run(src, "00981A", at(when), root=repo / "docs" / "etf", days=3)

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def write(self, repo, name, text):
        p = repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text + "\n")

    def commit_push(self, repo, message):
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-qm", message)
        self.git(repo, "push", "-q", "origin", "HEAD:main")

    def runner(self, name):
        """和 actions/checkout 一樣的淺層複製。"""
        path = self.root / name
        self.git(self.root, "clone", "-q", "--depth", "1", self.remote.as_uri(), str(path))
        return path

    def step(self, repo, workflow, outcome="success"):
        script = "sleep() { :; }\n" + commit_script(workflow)
        return subprocess.run(["bash", "-e", "-c", script], cwd=repo,
                              env={**self.env, "FETCH_OUTCOME": outcome}, capture_output=True, text=True)

    def show(self, name):
        return self.git(self.remote, "show", f"main:{name}").strip()

    def history(self):
        return self.git(self.remote, "log", "--format=%s", "main").splitlines()

    def verify_remote(self):
        check = Path(tempfile.mkdtemp(dir=self.root)) / "c"
        self.git(self.root, "clone", "-q", self.remote.as_uri(), str(check))
        self.assertEqual(E.verify_folder(check / FUND), [])

    def changed_in_head(self):
        return self.git(self.remote, "show", "--format=", "--name-only", "main").split()

    def test_both_workflows_and_manual_push_all_survive(self):
        old, new, human = self.runner("old"), self.runner("new"), self.runner("human")
        self.write(human, "market-analysis.json", "human")
        self.commit_push(human, "market analysis")
        for name in LEGACY_FILES[::2]:
            self.write(old, name, "legacy")
        self.assertEqual(self.update(new, D27, "2026-11-27T17:10"), 0)
        for repo, wf in ((new, OFFICIAL), (old, LEGACY)):
            r = self.step(repo, wf)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(self.show("market-analysis.json"), "human")
        self.assertEqual(self.show("docs/data.json"), "legacy")
        self.assertIn(D27, self.show(f"{FUND}/status.json"))
        self.assertEqual(len(self.history()), 4)   # 沒有任何 commit 被蓋掉
        self.verify_remote()

    def test_failed_run_commits_only_status_and_log(self):
        new = self.runner("new")
        self.assertEqual(self.update(new, D27, "2026-11-27T17:10", fail=[D27]), 1)
        r = self.step(new, OFFICIAL, "failure")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(sorted(self.changed_in_head()), [f"{FUND}/errors.jsonl", f"{FUND}/status.json"])
        self.verify_remote()

    def test_failed_outcome_never_commits_data_files(self):
        """即使工作目錄的快照被改過，失敗時也不會提交。"""
        new = self.runner("new")
        self.update(new, D27, "2026-11-27T17:10", fail=[D27])
        self.write(new, f"{FUND}/snapshots/{D27}.json", "{}")
        self.step(new, OFFICIAL, "failure")
        self.assertNotIn(f"{D27}.json", self.git(self.remote, "ls-tree", "-r", "--name-only", "main"))

    def test_inconsistent_data_is_not_committed(self):
        new = self.runner("new")
        self.update(new, D27, "2026-11-27T17:10")
        (new / FUND / "snapshots" / f"{D27}.json").unlink()
        head = self.history()
        r = self.step(new, OFFICIAL)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.history(), head)

    def test_leftover_staging_is_not_committed(self):
        new = self.runner("new")
        self.update(new, D27, "2026-11-27T17:10")
        self.write(new, "docs/etf/.00981A.staging/new/00981A/status.json", "partial")
        self.assertEqual(self.step(new, OFFICIAL).returncode, 0)
        self.assertNotIn("staging", self.git(self.remote, "ls-tree", "-r", "--name-only", "main"))

    def test_rebase_that_breaks_version_is_not_pushed(self):
        """別人改了某個舊快照：Git 能自動合併，但版本已對不上，必須拒絕推送。"""
        new, human = self.runner("new"), self.runner("human")
        old_snapshot = sorted((human / FUND / "snapshots").glob("*.json"))[0]
        self.update(new, D26, "2026-11-26T19:10")
        extra = old_snapshot.with_name("2026-11-20.json")
        extra.write_text(old_snapshot.read_text(encoding="utf-8"), encoding="utf-8")
        self.commit_push(human, "stray snapshot")
        head = self.history()
        r = self.step(new, OFFICIAL)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.history(), head)

    def test_push_race_is_retried(self):
        """第一次 push 前一刻被別人搶先：重試後兩邊都保留。"""
        new, human = self.runner("new"), self.runner("human")
        self.update(new, D27, "2026-11-27T17:10")
        self.write(human, "market-analysis.json", "raced")
        self.git(human, "add", "-A")
        self.git(human, "commit", "-qm", "raced")
        hook = new / ".git" / "hooks" / "pre-push"
        hook.write_text(f'#!/bin/sh\n[ -e "{self.root}/done" ] && exit 0\ntouch "{self.root}/done"\n'
                        f'env -u GIT_DIR git -C "{human}" push -q origin HEAD:main\n')
        hook.chmod(0o755)
        r = self.step(new, OFFICIAL)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(self.show("market-analysis.json"), "raced")
        self.assertIn(D27, self.show(f"{FUND}/status.json"))
        self.verify_remote()

    def test_same_file_conflict_fails_without_overwriting(self):
        first, stale = self.runner("first"), self.runner("stale")
        self.write(first, "data.json", "first")
        self.assertEqual(self.step(first, LEGACY).returncode, 0)
        head = self.history()
        self.write(stale, "data.json", "stale")
        self.assertNotEqual(self.step(stale, LEGACY).returncode, 0)
        self.assertEqual(self.show("data.json"), "first")
        self.assertEqual(self.history(), head)

    def test_official_conflict_fails_without_overwriting(self):
        first, stale = self.runner("first"), self.runner("stale")
        self.update(first, D27, "2026-11-27T17:10")
        self.assertEqual(self.step(first, OFFICIAL).returncode, 0)
        head = self.history()
        self.update(stale, D27, "2026-11-27T19:10")
        self.assertNotEqual(self.step(stale, OFFICIAL).returncode, 0)
        self.assertEqual(self.history(), head)
        self.verify_remote()

    def test_no_change_means_no_commit(self):
        new = self.runner("new")
        self.assertEqual(self.step(new, OFFICIAL).returncode, 0)
        self.assertEqual(self.history(), ["seed"])


if __name__ == "__main__":
    unittest.main()
