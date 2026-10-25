"""Tests of the test verification: JUnit report (trace_check, sync_check, loop) and approval of the locked tests."""
from __future__ import annotations

import os
import sys
import unittest

from common import PLAN_OK, REVIEW_OK, SPEC_OK, TASKS_OK, TmpDir, copy_scripts, git_repo, load, run, write

spec_lint = load("spec_lint")
trace_check = load("trace_check")
state = load("state")
PY = os.path.basename(sys.executable)
APPROVAL = " — tests approved: Anna Smith, 2026-10-19, abc1234"


def junit(*cases: tuple[str, str, str]) -> str:
    """JUnit report with cases (classname, name, outcome: passed | failed | skipped)."""
    child = {"passed": "", "failed": "<failure message='x'/>", "skipped": "<skipped/>"}
    rows = "".join(f'<testcase classname="{c}" name="{n}">{child[o]}</testcase>' for c, n, o in cases)
    return f'<?xml version="1.0"?><testsuites><testsuite name="s">{rows}</testsuite></testsuites>'


def cli(d, script: str, *args: str):
    return run([sys.executable, f"scripts/{script}.py", *args], d)


class TestJUnit(unittest.TestCase):
    def prepare(self, d, report: str):
        copy_scripts(d)
        write(d, "spec.md", SPEC_OK)
        write(d, "tests/test_export.py", "def test_AC_001_ok(): pass\ndef test_AC_002_error(): pass\n")
        write(d, "reports/junit.xml", report)

    def test_acs_verified_by_the_report(self):
        with TmpDir() as d:
            self.prepare(d, junit(("tests.test_export", "test_AC_001_ok", "passed"),
                                  ("tests.test_export", "test_AC_002_error", "passed")))
            r = cli(d, "trace_check", "spec.md", "--junit", "reports")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("verified against the report", r.stdout)

    def test_cited_but_failed_skipped_or_not_run(self):
        with TmpDir() as d:
            self.prepare(d, junit(("tests.test_export", "test_AC_001_ok", "failed"),
                                  ("tests.test_export", "test_AC_002_error", "skipped")))
            r = cli(d, "trace_check", "spec.md", "--junit", "reports/junit.xml")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("AC-001: failed tests in the report", r.stdout)
            self.assertIn("AC-002: no executed and passing test in the report (1 skipped)", r.stdout)
            self.assertEqual(cli(d, "trace_check", "spec.md").returncode, 0)  # without a report the citation is enough
            write(d, "reports/junit.xml", junit(("tests.test_export", "test_AC_001_ok", "passed")))
            r = cli(d, "trace_check", "spec.md", "--junit", "reports/junit.xml")
            self.assertIn("AC-002: no executed and passing test in the report\n", r.stdout)

    def test_unreadable_report(self):
        with TmpDir() as d:
            self.prepare(d, "<testsuite><broken")
            r = cli(d, "trace_check", "spec.md", "--junit", "reports/junit.xml")
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("unreadable JUnit report", r.stdout)

    def test_attribution_with_several_specs(self):
        spec2 = SPEC_OK.replace("SPEC-001", "SPEC-002")
        with TmpDir() as d:
            write(d, "tests/test_one.py", "# SPEC-001\ndef test_AC_001(): pass\n")
            write(d, "tests/test_two.py", "# SPEC-002\ndef test_AC_001(): pass\n")
            report = d / "junit.xml"
            report.write_text(junit(("tests.test_two", "test_AC_001", "passed"),
                                    ("", "SPEC-001/AC-002 clear error", "passed"),
                                    ("tests.test_one", "test_AC_001", "failed")), encoding="utf-8")
            ex = trace_check.executions(SPEC_OK, [d / "tests"], [report], single_spec=False)
            self.assertEqual(ex["AC-001"]["failed"], ["tests.test_one::test_AC_001"])
            self.assertEqual(ex["AC-001"]["passed"], [])  # the case of test_two belongs to SPEC-002
            self.assertEqual(ex["AC-002"]["passed"], ["SPEC-001/AC-002 clear error"])
            ex2 = trace_check.executions(spec2, [d / "tests"], [report], single_spec=False)
            self.assertEqual(ex2["AC-001"]["passed"], ["tests.test_two::test_AC_001"])


class TestTestApproval(unittest.TestCase):
    CLOSED = TASKS_OK.replace("[ ] T-01", "[x] T-01")

    def test_tests_to_approve(self):
        self.assertEqual(spec_lint.tests_to_approve(self.CLOSED), [])
        without = self.CLOSED.replace(APPROVAL, "")
        self.assertEqual(spec_lint.tests_to_approve(without), ["T-01"])
        self.assertEqual(spec_lint.tests_to_approve(without.replace("— covers", "— tests approved: <name> — covers")),
                         ["T-01"])
        self.assertEqual(spec_lint.tests_to_approve(TASKS_OK.replace(APPROVAL, "")), [])  # task still open

    def test_state_asks_for_the_approval(self):
        without = self.CLOSED.replace(APPROVAL, "")
        with TmpDir() as d:
            write(d, "AGENTS.md")
            write(d, "scripts/verify.py")
            write(d, "docs/specs/001-x/spec.md", SPEC_OK)
            write(d, "docs/specs/001-x/plan.md", PLAN_OK)
            write(d, "docs/specs/001-x/tasks.md", without)
            p = state.analyze(d)["next"]
            self.assertEqual(p["skill"], "sdd-tests-from-ac")
            self.assertIn("T-01 to be approved", p["reason"])
            write(d, "docs/specs/001-x/tasks.md", self.CLOSED)
            self.assertEqual(state.analyze(d)["next"]["skill"], "sdd-implement")

    def test_sync_check(self):
        without = TASKS_OK.replace(APPROVAL, "").replace("[ ]", "[x]")
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "docs/specs/001-x/spec.md", SPEC_OK.replace("Status: approved", "Status: implemented"))
            write(d, "docs/specs/001-x/tasks.md", without)
            write(d, "docs/specs/001-x/review.md", REVIEW_OK)
            r = cli(d, "sync_check", "docs/specs/001-x")
            self.assertIn("locked tests without human approval ('tests approved:'): T-01", r.stdout)


RED_TEST_AGENT = (
    "import sys\n"
    "sys.stdin.read()\n"
    "p = 'docs/specs/001-x/tasks.md'\n"
    "t = open(p, encoding='utf-8').read()\n"
    "open(p, 'w', encoding='utf-8').write(t.replace('[ ] T-01', '[x] T-01', 1))\n"
)


class TestLoopApproval(unittest.TestCase):
    def project(self, d, tasks: str, spec: str | None = None):
        copy_scripts(d, ["loop", "spec_lint"])
        write(d, "scripts/verify.py", "import sys\nsys.exit(1)\n")
        write(d, "docs/specs/001-x/tasks.md", tasks)
        write(d, "docs/specs/001-x/PROMPT.md", "prompt\n")
        if spec:
            write(d, "docs/specs/001-x/spec.md", spec)
        write(d, "agent.py", RED_TEST_AGENT)
        git_repo(d, "feature/x")

    def loop(self, d, *extra: str):
        env = {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]}
        return run([sys.executable, "scripts/loop.py", "docs/specs/001-x", "--agent", f"{PY} agent.py", *extra],
                   d, env=env)

    TASKS = "- [ ] T-01 Test — verify: `t` (expected: red) — covers: AC-001\n- [ ] T-02 Implement\n"

    def test_pause_after_the_red_tests(self):
        with TmpDir() as d:
            self.project(d, self.TASKS)
            r = self.loop(d, "--allow-red-baseline", "--max", "5")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("Pause: the locked tests of T-01 must be approved", r.stdout)
            r = self.loop(d, "--dry-run")
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("are waiting for human approval", r.stdout)

    def test_level_s_does_not_stop(self):
        with TmpDir() as d:
            self.project(d, self.TASKS, spec="# SPEC-001: x\n\n- Level: S\n")
            r = self.loop(d, "--allow-red-baseline", "--max", "2")
            self.assertNotIn("Pause", r.stdout)
            self.assertIn("Cap reached", r.stdout)


if __name__ == "__main__":
    unittest.main()
