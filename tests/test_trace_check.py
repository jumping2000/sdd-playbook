"""Tests of trace_check: AC -> test traceability, JUnit verification, attribution and the --task scope."""
from __future__ import annotations

import sys
import unittest

from common import PLAN_OK, SPEC_OK, TmpDir, copy_scripts, load, run, write

trace_check = load("trace_check")


def cli(d, script: str, *args: str):
    return run([sys.executable, f"scripts/{script}.py", *args], d)


def junit(*cases: tuple[str, str, str]) -> str:
    """JUnit report with cases (classname, name, outcome: passed | failed | skipped)."""
    child = {"passed": "", "failed": "<failure message='x'/>", "skipped": "<skipped/>"}
    rows = "".join(f'<testcase classname="{c}" name="{n}">{child[o]}</testcase>' for c, n, o in cases)
    return f'<?xml version="1.0"?><testsuites><testsuite name="s">{rows}</testsuite></testsuites>'


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


class TestJUnitAttribution(unittest.TestCase):  # I4
    def test_same_name_files_in_different_folders(self):
        spec_a = SPEC_OK.replace("SPEC-001", "SPEC-002")
        with TmpDir() as d:
            write(d, "tests/a/test_api.py", "# SPEC-001\ndef test_AC_001(): pass\n")
            write(d, "tests/b/test_api.py", "# SPEC-002\ndef test_AC_001(): pass\n")
            report = d / "junit.xml"
            report.write_text('<testsuite><testcase classname="tests.a.test_api" name="test_AC_001"><skipped/>'
                              '</testcase><testcase classname="tests.b.test_api" name="test_AC_001"><failure/>'
                              '</testcase></testsuite>', encoding="utf-8")
            ex1 = trace_check.executions(SPEC_OK, [d / "tests"], [report], single_spec=False)
            self.assertEqual((ex1["AC-001"]["passed"], ex1["AC-001"]["failed"]), ([], []))
            self.assertEqual(ex1["AC-001"]["skipped"], ["tests.a.test_api::test_AC_001"])
            ex2 = trace_check.executions(spec_a, [d / "tests"], [report], single_spec=False)
            self.assertEqual(ex2["AC-001"]["failed"], ["tests.b.test_api::test_AC_001"])

    def test_go_and_java_conventions(self):
        with TmpDir() as d:
            write(d, "src/test/java/com/acme/ExportTest.java", "// SPEC-001\n@Test void AC_001_exports() {}\n")
            write(d, "pkg/export_test.go", "// SPEC-001\nfunc TestAC002_Error(t *testing.T) {}\n")
            found, _, _ = trace_check.collect([d / "src", d / "pkg"], "1", single_spec=False)
            self.assertEqual(sorted(found), [1, 2])
            report = d / "junit.xml"
            report.write_text('<testsuite><testcase classname="com.acme.ExportTest" name="AC_001_exports"/>'
                              '</testsuite>', encoding="utf-8")
            ex = trace_check.executions(SPEC_OK, [d / "src"], [report], single_spec=False)
            self.assertEqual(ex["AC-001"]["passed"], ["com.acme.ExportTest::AC_001_exports"])

    def test_junit_without_value(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "spec.md", SPEC_OK)
            write(d, "tests/t.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")
            self.assertEqual(cli(d, "trace_check", "spec.md", "--junit").returncode, 2)


class TestTaskScope(unittest.TestCase):
    def test_only_the_acs_of_the_task(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "docs/specs/001-x/spec.md", SPEC_OK)
            write(d, "docs/specs/001-x/plan.md", PLAN_OK)
            write(d, "tests/test_export.py", "def test_AC_001_ok(): pass\n")  # T-02 (AC-002) not done yet
            self.assertEqual(cli(d, "trace_check", "docs/specs/001-x/spec.md").returncode, 1)
            r = cli(d, "trace_check", "docs/specs/001-x/spec.md", "--task", "T-01")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertNotIn("AC-002", r.stdout)
            r = cli(d, "trace_check", "docs/specs/001-x/spec.md", "--task", "T-02")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("AC-002: NO TEST", r.stdout)
            write(d, "reports/junit.xml", junit(("tests.test_export", "test_AC_001_ok", "passed")))
            r = cli(d, "trace_check", "docs/specs/001-x/spec.md", "--task", "T-01", "--junit", "reports")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertEqual(cli(d, "trace_check", "docs/specs/001-x/spec.md", "--task", "T-09").returncode, 2)


if __name__ == "__main__":
    unittest.main()
