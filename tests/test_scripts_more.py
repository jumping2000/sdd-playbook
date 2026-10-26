"""Tests of trace_check, bug_lint, diff_scope, scan_repo, docs_check, sync_check."""
from __future__ import annotations

import sys
import unittest

from common import (AREA_OK, BUG_OK, PLAN_OK, REVIEW_OK, SPEC_OK, TASKS_OK, TmpDir, copy_scripts, git, git_repo, load,
                    read, run, write)

bug_lint = load("bug_lint")
trace_check = load("trace_check")
diff_scope = load("diff_scope")
scan_repo = load("scan_repo")


def cli(d, script: str, *args: str):
    return run([sys.executable, f"scripts/{script}.py", *args], d)


class TestTraceCheck(unittest.TestCase):
    def test_coverage(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "spec.md", SPEC_OK)
            write(d, "tests/test_a.py", "def test_AC_001_ok(): pass\n# AC-099 of another spec\n")
            r = cli(d, "trace_check", "spec.md")
            self.assertEqual(r.returncode, 1)
            self.assertIn("AC-002: NO TEST", r.stdout)
            self.assertIn("AC-099", r.stdout)
            self.assertEqual(cli(d, "trace_check", "spec.md", "--warn-only").returncode, 0)
            write(d, "tests/test_b.py", "# AC-002: clear error\n")
            self.assertEqual(cli(d, "trace_check", "spec.md").returncode, 0)

    def test_id_formats(self):
        with TmpDir() as d:
            write(d, "tests/t.py", "def test_AC001(): pass\ndef test_x_AC_002_y(): pass\n# ACCESS 12\n")
            found, _, _ = trace_check.collect([d / "tests"], "1", single_spec=True)
            self.assertEqual(sorted(found), [1, 2])
            write(d, "tests/q.py", "def test_SPEC001_AC003(): pass\ndef test_SPEC_001_AC_004(): pass\n"
                                   "it('SPEC-001/AC-005: x')\n# SPEC-001-AC-006\n# SPEC-002/AC-007\n")
            found, _, _ = trace_check.collect([d / "tests"], "1", single_spec=False)
            self.assertEqual(sorted(found), [3, 4, 5, 6])

    def test_id_with_date_and_slug(self):
        csv = SPEC_OK.replace("# SPEC-001: Example", "# SPEC-2026-10-24-export-csv: Export CSV")
        short = SPEC_OK.replace("# SPEC-001: Example", "# SPEC-2026-10-24-export: Export")
        with TmpDir() as d:
            write(d, "tests/test_qualified.py",
                  "it('SPEC-2026-10-24-export-csv/AC-001: valid csv')\n"
                  "def test_SPEC_2026_10_24_export_csv_AC_002_empty(): pass\n")
            write(d, "tests/test_declared.py", "# SPEC-2026-10-24-export\ndef test_AC_001(): pass\n")
            result = trace_check.analyze(csv, [d / "tests"], single_spec=False)
            self.assertEqual(result.missing, [])
            self.assertEqual(len(result.covered["AC-001"]), 1)  # the file of SPEC-2026-10-24-export does not count
            result = trace_check.analyze(short, [d / "tests"], single_spec=False)
            self.assertEqual(result.missing, ["AC-002"])  # a spec with a shorter ID does not inherit the citations

    def test_qualified_acs_with_several_specs(self):
        spec2 = SPEC_OK.replace("SPEC-001", "SPEC-002")
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "docs/specs/001-a/spec.md", SPEC_OK)
            write(d, "docs/specs/002-b/spec.md", spec2)
            # SPEC-001 tests without a declaration: with two specs they are ambiguous and do not cover SPEC-002
            write(d, "tests/test_old.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")
            r = cli(d, "trace_check", "docs/specs/002-b/spec.md")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("TRACE: 2 ACs without tests: AC-001, AC-002", r.stdout)
            self.assertIn("2 AC citations without a spec", r.stdout)
            # a file declared for SPEC-001 does not cover SPEC-002
            write(d, "tests/test_old.py", "# SPEC-001\ndef test_AC_001(): pass\ndef test_AC_002(): pass\n")
            self.assertEqual(cli(d, "trace_check", "docs/specs/002-b/spec.md").returncode, 1)
            self.assertEqual(cli(d, "trace_check", "docs/specs/001-a/spec.md").returncode, 0)
            # file declared for SPEC-002 and a qualified citation in any file
            write(d, "tests/test_b.py", "# SPEC-002\ndef test_AC_001(): pass\n")
            write(d, "tests/test_c.py", "def test_SPEC002_AC002_error(): pass\n")
            r = cli(d, "trace_check", "docs/specs/002-b/spec.md")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertNotIn("AC citations without a spec", r.stdout)

    def test_reminders_do_not_count(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "spec.md", SPEC_OK)
            write(d, "tests/test_a.py", "def test_AC_001(): pass\n# TODO AC-002 to write\n")
            r = cli(d, "trace_check", "spec.md")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("AC-002: NO TEST", r.stdout)
            self.assertIn("1 citations on TODO/FIXME/XXX lines ignored", r.stdout)

    def test_spec_without_id_in_the_title(self):
        no_id = SPEC_OK.replace("# SPEC-001: Example", "# Example")
        with TmpDir() as d:
            write(d, "tests/t.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")
            self.assertEqual(trace_check.analyze(no_id, [d / "tests"], single_spec=True).missing, [])
            result = trace_check.analyze(no_id, [d / "tests"], single_spec=False)
            self.assertEqual(result.missing, ["AC-001", "AC-002"])
            self.assertEqual(len(result.ambiguous), 2)

    def test_without_test_folder(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "spec.md", SPEC_OK)
            self.assertEqual(cli(d, "trace_check", "spec.md").returncode, 2)


class TestBugLint(unittest.TestCase):
    def test_complete_bug(self):
        self.assertEqual(bug_lint.lint(BUG_OK), [])

    def test_open_template_asks_for_the_reproduction(self):
        err = bug_lint.lint(read("skills/sdd-bugfix/references/bugfix-template.md"))
        self.assertEqual(err, ["Reproduction not filled in"])

    def test_requirements_grow_with_the_status(self):
        diag = BUG_OK.replace("Status: verified", "Status: diagnosed")
        self.assertEqual(bug_lint.lint(diag), [])
        no_red = diag.replace("`tests/test_export.py::test_comma`", "`<path>`")
        self.assertTrue(any("red test" in e.lower() for e in bug_lint.lint(no_red)))
        no_unchanged = diag.replace("- The separator stays the comma", "- <list>")
        self.assertTrue(any("NOT change" in e for e in bug_lint.lint(no_unchanged)))
        fixed = BUG_OK.replace("Status: verified", "Status: fixed")
        self.assertEqual(bug_lint.lint(fixed), [])
        self.assertTrue(any("Non-regression" in e for e in bug_lint.lint(
            fixed.replace("`tests/test_export.py::test_separator`", "`<x>`"))))
        self.assertTrue(any("not ticked" in e for e in bug_lint.lint(BUG_OK.replace("[x] verify", "[ ] verify"))))

    def test_invalid_status(self):
        self.assertTrue(bug_lint.lint(BUG_OK.replace("Status: verified", "Status: whatever")))


class TestDiffScope(unittest.TestCase):
    def prepare(self, d, agents="- Do not modify: legacy/\n"):
        git_repo(d, "main")
        write(d, "AGENTS.md", "# A\n" + agents)
        write(d, "legacy/a.py", "v1\n")
        write(d, "src/old.py", "v1\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feature/x")
        write(d, "docs/specs/001-x/plan.md", PLAN_OK)

    def test_violations_and_out_of_plan(self):
        with TmpDir() as d:
            copy_scripts(d)
            self.prepare(d)
            write(d, "src/export.py", "new\n")
            write(d, "legacy/a.py", "v2\n")
            write(d, "other.py", "x\n")
            write(d, "docs/system/export.md", "x\n")
            write(d, "docs/glossary.md", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x", "--base", "main")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("file in a forbidden zone (AGENTS.md): legacy/a.py", r.stdout)
            self.assertIn("[WARN] file outside the plan: other.py", r.stdout)
            self.assertNotIn("outside the plan: docs/system", r.stdout)
            self.assertNotIn("outside the plan: docs/glossary.md", r.stdout)
            self.assertNotIn("outside the plan: src/export.py", r.stdout)
            self.assertIn("in the plan but not touched: tests/", r.stdout)

    def test_ok_and_strict(self):
        with TmpDir() as d:
            copy_scripts(d)
            self.prepare(d)
            write(d, "src/export.py", "new\n")
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)
            write(d, "other.py", "x\n")
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x", "--strict").returncode, 1)

    def test_without_git_or_base(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "docs/specs/001-x/plan.md", PLAN_OK)
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 2)

    def test_paths(self):
        self.assertTrue(diff_scope.matches("src/a/b.py", "src/"))
        self.assertTrue(diff_scope.matches("src/a/b.py", "src/a"))
        self.assertTrue(diff_scope.matches("src/a/b.py", "src/**/*.py"))
        self.assertFalse(diff_scope.matches("srcx/b.py", "src"))
        self.assertEqual(diff_scope.plan_paths(PLAN_OK), ["src/export.py", "tests/"])
        self.assertEqual(diff_scope.forbidden_paths("- Do not modify: `a/`, b.py; <x>\n"), ["a/", "b.py"])

    def test_paths_with_leading_dot(self):
        self.assertTrue(diff_scope.matches(".github/workflows/ci.yml", ".github/"))
        self.assertTrue(diff_scope.matches(".github/workflows/ci.yml", "./.github"))
        self.assertTrue(diff_scope.matches(".env", ".env"))
        self.assertFalse(diff_scope.matches("github/x.yml", ".github/"))

    def test_plan_annotations_and_where_column(self):
        plan = ("## Components and files to create/modify\n- src/a.py (new): x\n- `src/b c.py`: y\n"
                "- <path>: <what changes>\n\n## Test strategy (mapped to ACs)\n"
                "| AC | Level | Where | Notes |\n|---|---|---|---|\n| AC-001 | unit | `tests/test_a.py::test_x` | n |\n"
                "| AC-002 | e2e | manual | n |\n| AC-003 | unit | tests/<file> | n |\n")
        self.assertEqual(diff_scope.plan_paths(plan), ["src/a.py", "src/b c.py", "tests/test_a.py"])
        focus = plan + "\n## Review focus\n| Case | Expected behaviour | Where |\n|---|---|---|\n| empty | error | `tests/test_e.py` |\n"
        self.assertEqual(diff_scope.plan_paths(focus)[-1], "tests/test_e.py")
        agents = "- Do not modify: legacy/\n- Text\n- Do not modify: .github/; migrations/\n"
        self.assertEqual(diff_scope.forbidden_paths(agents), ["legacy/", ".github/", "migrations/"])

    def test_forbidden_zones_with_dot_on_a_real_repo(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, ".github/workflows/ci.yml", "on: push\n")
            self.prepare(d, agents="- Do not modify: legacy/\n- Do not modify: .github/\n")
            write(d, ".github/workflows/ci.yml", "on: [push, pull_request]\n")
            r = cli(d, "diff_scope", "docs/specs/001-x", "--base", "main")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("file in a forbidden zone (AGENTS.md): .github/workflows/ci.yml", r.stdout)

    def test_recognizes_test_files(self):
        for p in ("tests/x.py", "src/a.test.ts", "pkg/foo_test.go", "src/FooTest.java", "web/b.spec.js", "test_a.py"):
            self.assertTrue(diff_scope.is_test(p), p)
        for p in ("src/export.py", "src/latest.py", "docs/specs/001-x/spec.md", "src/contest.py"):
            self.assertFalse(diff_scope.is_test(p), p)


class TestTestLock(unittest.TestCase):
    """Red tests locked with the Test-Lock trailer: the implementation cannot change them."""

    def prepare(self, d):
        copy_scripts(d)
        git_repo(d, "main")
        write(d, "AGENTS.md", "# A\n")
        write(d, "src/old.py", "v1\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feature/x")
        write(d, "docs/specs/001-x/plan.md", PLAN_OK)
        write(d, "src/export.py", "def export(): raise NotImplementedError\n")
        write(d, "tests/test_export.py", "def test_AC_001(): assert False\n")
        git(d, "add", "src/export.py", "tests/test_export.py")
        git(d, "commit", "-qm", "red tests for AC-001", "-m", "Test-Lock: T-01")
        write(d, "src/export.py", "def export(): return 'csv'\n")
        git(d, "add", "src/export.py")
        git(d, "commit", "-qm", "implement T-02")

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


class TestScanRepo(unittest.TestCase):
    def test_inventory(self):
        with TmpDir() as d:
            write(d, "pyproject.toml")
            write(d, "src/main.py", "a\nb\nc\n")
            write(d, "src/util.py", "x\n")
            write(d, "tests/test_a.py")
            write(d, "README.md")
            write(d, ".github/workflows/ci.yml")
            write(d, "node_modules/x/index.js", "ignored\n")
            r = scan_repo.scan(d)
            self.assertEqual(r["stack"], ["Python"])
            self.assertEqual(r["languages"][0], {"name": "Python", "files": 3, "lines": 5})
            self.assertEqual(r["test_folders"], ["tests"])
            self.assertEqual(r["likely_entry_points"], ["src/main.py"])
            self.assertEqual(r["ci"], [".github/workflows/ci.yml"])
            self.assertEqual(r["documentation"], ["README.md"])

    def test_cli_json_and_missing_folder(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "a.py")
            self.assertIn('"total_files"', cli(d, "scan_repo", ".", "--json").stdout)
            self.assertEqual(cli(d, "scan_repo", "does-not-exist").returncode, 2)


class TestDocsCheck(unittest.TestCase):
    def test_links_and_examples(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "docs/b.md", "# B\n")
            write(d, "README.md", "[ok](docs/b.md) [web](https://x.y) [anc](#a)\n```\n[in code](broken.md)\n```\n"
                                  "`[inline](broken2.md)`\n")
            self.assertEqual(cli(d, "docs_check", "README.md", "docs").returncode, 0)
            write(d, "README.md", "[broken](docs/does-not-exist.md)\n")
            r = cli(d, "docs_check", "README.md")
            self.assertEqual(r.returncode, 1)
            self.assertIn("broken link -> docs/does-not-exist.md", r.stdout)

    def test_runnable_examples(self):
        with TmpDir() as d:
            copy_scripts(d)
            ok = "```python\n# docs-check: run\nprint(1 + 1)\n```\n"
            ko = "```python\n# docs-check: run\nraise SystemExit(3)\n```\n"
            not_run = "```python\nraise SystemExit(9)\n```\n"
            write(d, "README.md", ok + not_run)
            r = cli(d, "docs_check", "README.md", "--run-examples")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("1 examples run", r.stdout)
            write(d, "README.md", ok + ko)
            r = cli(d, "docs_check", "README.md", "--run-examples")
            self.assertEqual(r.returncode, 1)
            self.assertIn("example #2 failed (exit 3)", r.stdout)
            self.assertEqual(cli(d, "docs_check", "README.md").returncode, 0)  # without --run-examples nothing runs


class TestSyncCheck(unittest.TestCase):
    def prepare(self, d):
        copy_scripts(d)
        f = "docs/specs/001-x/"
        write(d, f + "spec.md", SPEC_OK.replace("Status: approved", "Status: implemented"))
        write(d, f + "tasks.md", TASKS_OK.replace("[ ]", "[x]"))
        write(d, f + "review.md", REVIEW_OK)
        write(d, "docs/system/export.md", AREA_OK)
        write(d, "tests/test_export.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")

    def test_aligned(self):
        with TmpDir() as d:
            self.prepare(d)
            r = cli(d, "sync_check", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_errors(self):
        cases = {
            "Status is 'approved'": lambda d: write(d, "docs/specs/001-x/spec.md", SPEC_OK),
            "tasks still open: T-SYNC": lambda d: write(d, "docs/specs/001-x/tasks.md", TASKS_OK.replace(
                "[ ] T-0", "[x] T-0").replace("[ ] T-DOC", "[x] T-DOC")),
            "review.md missing": lambda d: (d / "docs/specs/001-x/review.md").unlink(),
            "Outcome 'non-compliant'": lambda d: write(d, "docs/specs/001-x/review.md", REVIEW_OK.replace(
                "Outcome: compliant", "Outcome: non-compliant")),
            "'Decided by' not filled in": lambda d: write(d, "docs/specs/001-x/review.md", REVIEW_OK.replace(
                "Anna Smith, 2026-10-19", "<name>")),
            "no area page": lambda d: (d / "docs/system/export.md").unlink(),
            "'Last aligned' not filled in": lambda d: write(d, "docs/system/export.md", AREA_OK.replace(
                "2026-10-19\n- Linked", "<yyyy-mm-dd>\n- Linked")),
            "missing section '## Constraints and delicate points'": lambda d: write(
                d, "docs/system/export.md", AREA_OK.replace("## Constraints and delicate points", "## Other")),
            "ACs without tests: AC-002": lambda d: write(d, "tests/test_export.py", "def test_AC_001(): pass\n"),
        }
        for expected, breaker in cases.items():
            with self.subTest(expected):
                with TmpDir() as d:
                    self.prepare(d)
                    breaker(d)
                    r = cli(d, "sync_check", "docs/specs/001-x")
                    self.assertEqual(r.returncode, 1, r.stdout)
                    self.assertIn(expected, r.stdout)

    def test_tests_of_another_spec_are_not_enough(self):
        with TmpDir() as d:
            self.prepare(d)
            write(d, "docs/specs/002-y/spec.md", SPEC_OK.replace("SPEC-001", "SPEC-002"))
            write(d, "tests/test_export.py", "# SPEC-002\ndef test_AC_001(): pass\ndef test_AC_002(): pass\n")
            r = cli(d, "sync_check", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("ACs without tests: AC-001, AC-002", r.stdout)
            write(d, "tests/test_export.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")
            self.assertIn("ambiguous citations: use SPEC-001/AC-nnn", cli(d, "sync_check", "docs/specs/001-x").stdout)
            write(d, "tests/test_export.py", "def test_SPEC001_AC001(): pass\ndef test_SPEC001_AC002(): pass\n")
            self.assertEqual(cli(d, "sync_check", "docs/specs/001-x").returncode, 0)

    def test_dated_spec_and_area_page(self):
        folder = "docs/specs/2026-10-24-export-csv/"
        with TmpDir() as d:
            copy_scripts(d)
            spec = SPEC_OK.replace("# SPEC-001: Example", "# SPEC-2026-10-24-export-csv: Export").replace(
                "Status: approved", "Status: implemented")
            write(d, folder + "spec.md", spec)
            write(d, folder + "tasks.md", TASKS_OK.replace("[ ]", "[x]"))
            write(d, folder + "review.md", REVIEW_OK)
            write(d, "tests/test_export.py", "# SPEC-2026-10-24-export-csv\ndef test_AC_001(): pass\n"
                                             "def test_AC_002(): pass\n")
            # a page that only cites a spec with a shorter ID does not count
            write(d, "docs/system/export.md", AREA_OK.replace("SPEC-001", "SPEC-2026-10-24-export"))
            r = cli(d, "sync_check", folder)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("no area page in docs/system/ citing SPEC-2026-10-24-export-csv", r.stdout)
            write(d, "docs/system/export.md", AREA_OK.replace("SPEC-001", "SPEC-2026-10-24-export-csv"))
            r = cli(d, "sync_check", folder)
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_utf8_output_even_with_a_cp1252_console(self):
        with TmpDir() as d:
            self.prepare(d)
            write(d, "docs/specs/001-x/spec.md", SPEC_OK)
            r = run([sys.executable, "scripts/sync_check.py", "docs/specs/001-x"], d,
                    env={"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"})
            self.assertIsNotNone(r.stdout)
            self.assertIn("Status is 'approved'", r.stdout)


if __name__ == "__main__":
    unittest.main()
