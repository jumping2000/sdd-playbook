"""Tests of the per-task review: review_package.py and the task review checks (spec_lint, state, sync_check, loop)."""
from __future__ import annotations

import os
import sys
import unittest

from common import PLAN_OK, SPEC_OK, TASKS_OK, TmpDir, copy_scripts, git, git_repo, load, run, write

spec_lint = load("spec_lint")
state = load("state")
PY = os.path.basename(sys.executable)
DONE = TASKS_OK.replace("[ ] T-01", "[x] T-01").replace("[ ] T-02", "[x] T-02")
PASSED = "## Task reviews\n- T-01: pass\n- T-02: pass\n"


def with_level(level: str) -> str:
    text = SPEC_OK.replace("- Status: approved\n", f"- Status: approved\n- Level: {level}\n")
    return text.replace(spec_lint.field(text, "Hash"), spec_lint.fingerprint(text))


class TestTaskReviewRule(unittest.TestCase):
    def test_when_it_is_required(self):
        self.assertEqual(spec_lint.task_reviews_missing(with_level("M"), DONE, ""), [])
        self.assertEqual(spec_lint.task_reviews_missing(with_level("M"), DONE, "- Task review: on\n"), ["T-01", "T-02"])
        self.assertEqual(spec_lint.task_reviews_missing(with_level("M"), DONE, "- Task review: <on | off>\n"), [])
        self.assertEqual(spec_lint.task_reviews_missing(with_level("S"), DONE, "- Task review: on\n"), [])
        self.assertEqual(spec_lint.task_reviews_missing(with_level("L"), DONE, ""), ["T-01", "T-02"])

    def test_only_passed_reviews_of_closed_tasks_count(self):
        self.assertEqual(spec_lint.task_reviews_missing(with_level("L"), DONE, PASSED), [])
        fix_needed = PASSED.replace("T-02: pass", "T-02: fix needed")
        self.assertEqual(spec_lint.task_reviews_missing(with_level("L"), DONE, fix_needed), ["T-02"])
        elsewhere = "## Done\n- T-01: pass\n- T-02: pass\n"  # outside the "Task reviews" section it does not count
        self.assertEqual(spec_lint.task_reviews_missing(with_level("L"), DONE, elsewhere), ["T-01", "T-02"])
        self.assertEqual(spec_lint.task_reviews_missing(with_level("L"), TASKS_OK, ""), [])  # nothing closed yet

    def test_state_asks_for_the_task_reviews(self):
        with TmpDir() as d:
            write(d, "AGENTS.md")
            write(d, "scripts/verify.py")
            spec = with_level("L")
            write(d, "docs/specs/001-x/spec.md", spec)
            write(d, "docs/specs/001-x/plan.md", PLAN_OK.replace(spec_lint.field(PLAN_OK, "Based on spec"),
                                                                 spec_lint.fingerprint(spec)))
            write(d, "docs/specs/001-x/tasks.md", DONE)
            p = state.analyze(d)["next"]
            self.assertEqual(p["skill"], "sdd-implement")
            self.assertIn("task reviews missing for T-01, T-02", p["reason"])
            write(d, "docs/specs/001-x/progress.md", PASSED)
            self.assertEqual(state.analyze(d)["next"]["skill"], "sdd-review-diff")

    def test_loop_final_checks(self):
        with TmpDir() as d:
            copy_scripts(d, ["loop", "spec_lint"])
            write(d, "scripts/verify.py", "import sys\nsys.exit(0)\n")
            write(d, "docs/specs/001-x/spec.md", with_level("L"))
            write(d, "docs/specs/001-x/tasks.md", DONE)
            write(d, "docs/specs/001-x/PROMPT.md", "p\n")
            write(d, "agent.py", "import sys\nsys.stdin.read()\n")
            git_repo(d, "feature/x")
            env = {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]}
            args = [sys.executable, "scripts/loop.py", "docs/specs/001-x", "--agent", f"{PY} agent.py"]
            r = run(args, d, env=env)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("task reviews missing in progress.md: T-01, T-02", r.stdout)
            write(d, "docs/specs/001-x/progress.md", PASSED)
            self.assertEqual(run(args, d, env=env).returncode, 0)


class TestReviewPackage(unittest.TestCase):
    def prepare(self, d):
        copy_scripts(d)
        git_repo(d, "main")
        write(d, "src/old.py", "v1\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feature/x")
        write(d, "docs/specs/001-x/spec.md", SPEC_OK)
        write(d, "docs/specs/001-x/plan.md", PLAN_OK + "\n## Interfaces (APIs, schemas, contracts)\n"
                                                      "- exporter: produces export_csv(report) -> str\n")
        write(d, "docs/specs/001-x/tasks.md", TASKS_OK)
        write(d, "docs/specs/001-x/progress.md", "## Rulings\n- T-02: csv module — stdlib — none\n"
                                                 "- T-03: other — x — y\n")
        write(d, "tests/test_export.py", "def test_AC_001(): assert False\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "red tests", "-m", "Test-Lock: T-01")
        write(d, "src/export.py", "def export_csv(r): return ''\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "implement export", "-m", "Task: T-02")
        write(d, "src/other.py", "x\n")
        write(d, "reports/junit.xml", "<testsuite/>")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "other work", "-m", "Task: T-03")

    def test_package_of_one_task(self):
        with TmpDir() as d:
            self.prepare(d)
            r = run([sys.executable, "scripts/review_package.py", "docs/specs/001-x", "T-02"], d)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("REVIEW PACKAGE: reports/review/001-x/T-02.md (1 commits, 1 files)", r.stdout)
            text = (d / "reports/review/001-x/T-02.md").read_text(encoding="utf-8")
            self.assertIn("- [ ] T-02 Implement", text)
            self.assertIn("AC-001 [REQ-001]: Given a report", text)
            self.assertIn("export_csv(report) -> str", text)
            self.assertIn("- T-02: csv module", text)
            self.assertNotIn("- T-03: other", text)
            self.assertIn("+def export_csv(r)", text)
            self.assertNotIn("src/other.py", text)

    def test_test_lock_commit_and_whole_branch(self):
        with TmpDir() as d:
            self.prepare(d)
            r = run([sys.executable, "scripts/review_package.py", "docs/specs/001-x", "T-01", "--out", "t1.md"], d)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("tests/test_export.py", (d / "t1.md").read_text(encoding="utf-8"))
            r = run([sys.executable, "scripts/review_package.py", "docs/specs/001-x"], d)
            self.assertIn("(3 commits", r.stdout)
            text = (d / "reports/review/001-x/branch.md").read_text(encoding="utf-8")
            self.assertIn("src/other.py", text)
            self.assertIn("AC-002", text)
            self.assertNotIn("reports/junit.xml", text)  # generated files excluded

    def test_errors(self):
        with TmpDir() as d:
            self.prepare(d)
            r = run([sys.executable, "scripts/review_package.py", "docs/specs/001-x", "T-09"], d)
            self.assertEqual(r.returncode, 2)
            self.assertIn("no commit with 'Task: T-09' or 'Test-Lock: T-09'", r.stdout)
            self.assertEqual(run([sys.executable, "scripts/review_package.py", "docs/specs/001-x", "X-1"], d).returncode,
                             2)
            self.assertEqual(run([sys.executable, "scripts/review_package.py", "missing"], d).returncode, 2)


if __name__ == "__main__":
    unittest.main()
