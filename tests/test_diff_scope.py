"""Tests of diff_scope: forbidden zones, locked tests, files outside the task, sensitive areas, dependencies, size."""
from __future__ import annotations

import sys
import unittest

from common import PLAN_OK, TmpDir, copy_scripts, git, git_repo, load, run, write

diff_scope = load("diff_scope")


def cli(d, script: str, *args: str):
    return run([sys.executable, f"scripts/{script}.py", *args], d)


class TestDiffScope(unittest.TestCase):
    def prepare(self, d, agents="- Do not modify: legacy/\n- Sensitive areas: `src/auth/`\n"):
        copy_scripts(d)
        git_repo(d, "main")
        write(d, "AGENTS.md", "# A\n" + agents)
        write(d, "legacy/a.py", "v1\n")
        write(d, "docs/specs/001-x/plan.md", PLAN_OK)
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "task/001-x-T-01")

    def test_task_files_forbidden_zones_and_strict(self):
        with TmpDir() as d:
            self.prepare(d)
            write(d, "src/export.py", "new\n")
            write(d, "tests/test_export.py", "x\n")
            write(d, "docs/system/export.md", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x", "--task", "T-01")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertNotIn("outside the task", r.stdout)
            write(d, "other.py", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x", "--task", "T-01")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("[WARN] file outside the task: other.py", r.stdout)
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x", "--task", "T-01", "--strict").returncode, 1)
            write(d, "legacy/a.py", "v2\n")
            r = cli(d, "diff_scope", "docs/specs/001-x", "--task", "T-01")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("file in a forbidden zone (AGENTS.md): legacy/a.py", r.stdout)

    def test_sensitive_areas_dependencies_and_size(self):
        with TmpDir() as d:
            self.prepare(d)
            write(d, "src/auth/login.py", "x\n")
            write(d, "requirements.txt", "requests\n")
            write(d, "src/export.py", "x = 1\n" * 450)
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)  # warnings only: the human decides at the merge
            self.assertIn("SENSITIVE: src/auth/login.py", r.stdout)
            self.assertIn("[WARN] dependency manifest or lockfile changed: requirements.txt", r.stdout)
            self.assertIn("changed lines outside tests and docs", r.stdout)

    def test_agents_read_from_the_base_and_tooling(self):
        with TmpDir() as d:
            self.prepare(d)
            write(d, "AGENTS.md", "# A\n")  # the branch tries to drop the forbidden zone
            write(d, "legacy/a.py", "v2\n")
            write(d, "scripts/verify.py", "x\n")
            write(d, ".github/workflows/verify.yml", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x", "--task", "T-01")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("legacy/a.py", r.stdout)
            self.assertNotIn("outside the task: scripts/verify.py", r.stdout)
            self.assertNotIn("outside the task: .github", r.stdout)

    def test_errors_of_use(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "docs/specs/001-x/plan.md", PLAN_OK)
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 2)  # not a git repository
            self.prepare(d)
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x", "--task", "T-09").returncode, 2)

    def test_paths(self):
        self.assertTrue(diff_scope.matches("src/a/b.py", "src/"))
        self.assertTrue(diff_scope.matches("src/a/b.py", "src/**/*.py"))
        self.assertFalse(diff_scope.matches("srcx/b.py", "src"))
        self.assertTrue(diff_scope.matches(".github/workflows/ci.yml", "./.github"))
        self.assertFalse(diff_scope.matches("github/x.yml", ".github/"))
        self.assertEqual(diff_scope.forbidden_paths("- Do not modify: `a/`, b.py; <x>\n"), ["a/", "b.py"])
        for p in ("tests/x.py", "src/a.test.ts", "pkg/foo_test.go", "src/FooTest.java", "web/b.spec.js", "test_a.py"):
            self.assertTrue(diff_scope.is_test(p), p)
        for p in ("src/export.py", "src/latest.py", "src/contest.py"):
            self.assertFalse(diff_scope.is_test(p), p)
        self.assertFalse(diff_scope.is_production("scripts/verify.py"))
        self.assertTrue(diff_scope.is_production("scripts/deploy.py"))


class TestTestLock(unittest.TestCase):
    """Red tests locked with the Test-Lock trailer: the implementation cannot change them."""

    def prepare(self, d):
        copy_scripts(d)
        git_repo(d, "main")
        write(d, "AGENTS.md", "# A\n")
        write(d, "src/old.py", "v1\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "task/001-x-T-01")
        write(d, "docs/specs/001-x/plan.md", PLAN_OK)
        write(d, "src/export.py", "def export(): raise NotImplementedError\n")
        write(d, "tests/test_export.py", "def test_AC_001(): assert False\n")
        git(d, "add", "src/export.py", "tests/test_export.py")
        git(d, "commit", "-qm", "red tests for AC-001", "-m", "Test-Lock: T-01")
        write(d, "src/export.py", "def export(): return 'csv'\n")
        git(d, "add", "src/export.py")
        git(d, "commit", "-qm", "implement T-01", "-m", "Task: T-01")

    def test_implementation_without_touching_the_tests(self):
        with TmpDir() as d:
            self.prepare(d)
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("locked tests: 1", r.stdout)
            self.assertIn("non-test file in a Test-Lock commit, not locked: src/export.py", r.stdout)

    def test_change_to_the_locked_tests(self):
        with TmpDir() as d:
            self.prepare(d)
            write(d, "tests/test_export.py", "def test_AC_001(): assert True\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("tests/test_export.py (uncommitted)", r.stdout)
            git(d, "commit", "-qam", "weakens the test")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("locked test (Test-Lock) changed after locking: tests/test_export.py (commit", r.stdout)

    def test_explicit_fix_with_a_new_lock(self):
        with TmpDir() as d:
            self.prepare(d)
            write(d, "tests/test_export.py", "def test_AC_001(): assert export() == 'csv'\n")
            git(d, "commit", "-qam", "fixes the test, approved", "-m", "Test-Lock: T-01")
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)


if __name__ == "__main__":
    unittest.main()
