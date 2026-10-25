"""Tests of the levels S/M/L (playbook §2): spec_lint, diff_scope, state, sync_check."""
from __future__ import annotations

import sys
import unittest

from common import (AREA_OK, PLAN_OK, REVIEW_OK, SPEC_OK, TASKS_OK, TmpDir, copy_scripts, git, git_repo, load, run,
                    write)

REVIEWED = "## Task reviews\n- T-01: pass\n- T-02: pass\n"

spec_lint = load("spec_lint")
diff_scope = load("diff_scope")
state = load("state")


def with_level(spec: str, level: str) -> str:
    """Approved spec with the given level and the hash recomputed."""
    text = spec.replace("- Status: approved\n", f"- Status: approved\n- Level: {level}\n")
    old = spec_lint.field(text, "Hash")
    return text.replace(old, spec_lint.fingerprint(text))


def plan_for(spec: str) -> str:
    """PLAN_OK approved on the given version of the spec."""
    return PLAN_OK.replace(spec_lint.field(PLAN_OK, "Based on spec"), spec_lint.fingerprint(spec))


def cli(d, script: str, *args: str):
    return run([sys.executable, f"scripts/{script}.py", *args], d)


class TestSpecLintLevels(unittest.TestCase):
    def test_missing_level_counts_as_m(self):
        err, warn = spec_lint.lint_spec(SPEC_OK)
        self.assertEqual(err, [])
        self.assertTrue(any("Level not set" in w for w in warn))
        self.assertEqual(spec_lint.level(SPEC_OK), "M")

    def test_valid_and_invalid_level(self):
        for lvl in ("S", "M", "L"):
            err, warn = spec_lint.lint_spec(with_level(SPEC_OK, lvl))
            self.assertEqual(err, [], lvl)
            self.assertFalse(any("Level" in w for w in warn))
        err, _ = spec_lint.lint_spec(with_level(SPEC_OK, "XL"))
        self.assertTrue(any("Invalid level 'XL'" in e for e in err), err)

    def test_lowering_the_level_voids_the_approval(self):
        spec_l = with_level(SPEC_OK, "L")
        self.assertEqual(spec_lint.lint_spec(spec_l)[0], [])
        err, _ = spec_lint.lint_spec(spec_l.replace("- Level: L", "- Level: S"))
        self.assertTrue(any("Hash does not match" in e for e in err), err)
        # specs written before the levels keep their hash
        self.assertEqual(spec_lint.hash_problems(SPEC_OK, "Spec"), [])

    def test_level_s_without_t_doc(self):
        no_doc = TASKS_OK.replace("- [ ] T-DOC Documentation\n", "")
        self.assertEqual(spec_lint.lint_tasks(with_level(SPEC_OK, "S"), no_doc)[0], [])
        self.assertIn("Task T-DOC missing", spec_lint.lint_tasks(SPEC_OK, no_doc)[0])


class TestDiffScopeLevels(unittest.TestCase):
    def prepare(self, d, level: str, plan: bool = True):
        copy_scripts(d)
        git_repo(d, "main")
        write(d, "AGENTS.md", "# A\n- Sensitive areas: src/auth/, migrations/\n")
        write(d, "src/old.py", "v1\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feature/x")
        write(d, "docs/specs/001-x/spec.md", with_level(SPEC_OK, level))
        if plan:
            write(d, "docs/specs/001-x/plan.md", PLAN_OK)

    def test_required_level(self):
        self.assertEqual(diff_scope.required_level(["src/a.py", "tests/test_a.py", "README.md"], ""), ("S", []))
        lvl, reasons = diff_scope.required_level([f"src/m{i}.py" for i in range(4)], "")
        self.assertEqual(lvl, "M")
        self.assertIn("4 production files", reasons[0])
        lvl, reasons = diff_scope.required_level(["requirements-dev.txt", "web/package-lock.json"], "")
        self.assertEqual(lvl, "M")
        self.assertIn("dependencies changed", reasons[0])
        lvl, reasons = diff_scope.required_level(["src/auth/login.py"], "- Sensitive areas: `src/auth/`\n")
        self.assertEqual(lvl, "L")
        self.assertIn("src/auth/login.py", reasons[0])

    def test_s_without_plan_within_limits(self):
        with TmpDir() as d:
            self.prepare(d, "S", plan=False)
            write(d, "src/export.py", "x\n")
            write(d, "tests/test_export.py", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("level: S", r.stdout)
            self.assertIn("plan comparison skipped", r.stdout)
            self.assertNotIn("outside the plan", r.stdout)

    def test_s_underestimated(self):
        with TmpDir() as d:
            self.prepare(d, "S", plan=False)
            for i in range(4):
                write(d, f"src/m{i}.py", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("level underestimated: the spec declares S, the diff requires at least M", r.stdout)

    def test_sensitive_area_requires_l(self):
        with TmpDir() as d:
            self.prepare(d, "M")
            write(d, "src/auth/login.py", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("the diff requires at least L (sensitive area (AGENTS.md): src/auth/login.py)", r.stdout)
            write(d, "docs/specs/001-x/spec.md", with_level(SPEC_OK, "L"))
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)


class TestStateLevels(unittest.TestCase):
    def next(self, level: str, plan=False, tasks=None, review=None, progress=None) -> dict:
        with TmpDir() as r:
            write(r, "AGENTS.md")
            write(r, "scripts/verify.py")
            spec = with_level(SPEC_OK, level)
            write(r, "docs/specs/001-x/spec.md", spec)
            if plan:
                write(r, "docs/specs/001-x/plan.md", plan_for(spec))
            if tasks is not None:
                write(r, "docs/specs/001-x/tasks.md", tasks)
            if review is not None:
                write(r, "docs/specs/001-x/review.md", review)
            if progress is not None:
                write(r, "docs/specs/001-x/progress.md", progress)
            return state.analyze(r)["next"]

    def test_level_s_skips_plan_and_review(self):
        p = self.next("S")
        self.assertEqual((p["skill"], "without a plan" in p["reason"]), ("sdd-tasks", True))
        self.assertEqual(self.next("S", tasks=TASKS_OK)["skill"], "sdd-implement")
        done = TASKS_OK.replace("[ ] T-01", "[x] T-01").replace("[ ] T-02", "[x] T-02")
        self.assertEqual(self.next("S", tasks=done)["skill"], "sdd-docs")
        no_doc = done.replace("- [ ] T-DOC Documentation\n", "")
        self.assertEqual(self.next("S", tasks=no_doc)["skill"], "sdd-sync")
        nc = REVIEW_OK.replace("Outcome: compliant", "Outcome: non-compliant")
        self.assertEqual(self.next("S", tasks=no_doc, review=nc)["skill"], "sdd-review-diff")
        self.assertEqual(self.next("M")["skill"], "sdd-plan")

    def test_level_l_requires_the_human_review(self):
        done = TASKS_OK.replace("[ ] T-01", "[x] T-01").replace("[ ] T-02", "[x] T-02")
        p = self.next("L", plan=True, tasks=done, review=REVIEW_OK, progress=REVIEWED)
        self.assertEqual((p["skill"], "human reading of the diff" in p["reason"]), ("sdd-review-diff", True))
        human = REVIEW_OK + "- Human diff review: Anna Smith, 2026-10-20\n"
        self.assertEqual(self.next("L", plan=True, tasks=done, review=human, progress=REVIEWED)["skill"], "sdd-docs")
        self.assertEqual(self.next("M", plan=True, tasks=done, review=REVIEW_OK)["skill"], "sdd-docs")


class TestSyncCheckLevels(unittest.TestCase):
    def prepare(self, d, level: str):
        copy_scripts(d)
        f = "docs/specs/001-x/"
        write(d, f + "spec.md", with_level(SPEC_OK, level).replace("Status: approved", "Status: implemented"))
        write(d, f + "tasks.md", TASKS_OK.replace("[ ]", "[x]"))
        write(d, "tests/test_export.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")

    def test_s_without_review_or_area_page(self):
        with TmpDir() as d:
            self.prepare(d, "S")
            r = cli(d, "sync_check", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_l_requires_the_human_review(self):
        with TmpDir() as d:
            self.prepare(d, "L")
            write(d, "docs/specs/001-x/progress.md", REVIEWED)
            write(d, "docs/specs/001-x/review.md", REVIEW_OK)
            write(d, "docs/system/export.md", AREA_OK)
            r = cli(d, "sync_check", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("level L without 'Human diff review'", r.stdout)
            write(d, "docs/specs/001-x/review.md", REVIEW_OK + "- Human diff review: Anna Smith, 2026-10-20\n")
            r = cli(d, "sync_check", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("level L: the report of executed tests is required (--junit)", r.stdout)
            write(d, "reports/junit.xml", '<testsuite><testcase classname="tests.test_export" name="test_AC_001"/>'
                                          '<testcase classname="tests.test_export" name="test_AC_002"/></testsuite>')
            r = cli(d, "sync_check", "docs/specs/001-x", "--junit", "reports/junit.xml")
            self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
