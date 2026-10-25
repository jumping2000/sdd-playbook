"""Regressions from the problems of the critical review of 0.11.0 (I1-I8 and minor ones)."""
from __future__ import annotations

import json
import os
import sys
import unittest

from common import HOOKS, PLAN_OK, SPEC_OK, TASKS_OK, TmpDir, copy_scripts, git, git_repo, load, read, run, write

spec_lint = load("spec_lint")
trace_check = load("trace_check")
PY = os.path.basename(sys.executable)


def cli(d, script: str, *args: str):
    return run([sys.executable, f"scripts/{script}.py", *args], d)


def spec_with_level(level: str) -> str:
    text = SPEC_OK.replace("- Status: approved\n", f"- Status: approved\n- Level: {level}\n")
    return text.replace(spec_lint.field(text, "Hash"), spec_lint.fingerprint(text))


def repo(d, agents="# A\n", spec=None, plan=PLAN_OK):
    copy_scripts(d)
    git_repo(d, "main")
    write(d, "AGENTS.md", agents)
    write(d, "src/old.py", "v1\n")
    if spec:
        write(d, "docs/specs/001-x/spec.md", spec)
    git(d, "add", "-A")
    git(d, "commit", "-qm", "base")
    git(d, "checkout", "-qb", "feature/x")
    if plan:
        write(d, "docs/specs/001-x/plan.md", plan)


class TestApprovalTiedToTheSha(unittest.TestCase):  # I1
    def test_new_test_lock_after_the_approval(self):
        with TmpDir() as d:
            repo(d)
            write(d, "tests/test_export.py", "def test_AC_001(): assert False\n")
            git(d, "add", "tests/test_export.py")
            git(d, "commit", "-qm", "red tests", "-m", "Test-Lock: T-01")
            sha = git(d, "rev-parse", "--short=7", "HEAD")
            tasks = TASKS_OK.replace("[ ] T-01", "[x] T-01").replace("abc1234", sha)
            write(d, "docs/specs/001-x/tasks.md", tasks)
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)
            write(d, "tests/test_export.py", "def test_AC_001(): assert True\n")
            git(d, "add", "tests/test_export.py")
            git(d, "commit", "-qm", "weakened tests", "-m", "Test-Lock: T-01")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("T-01: new Test-Lock commit after the approval", r.stdout)
            write(d, "docs/specs/001-x/tasks.md", tasks.replace(sha, "1234567"))
            self.assertIn("is not a 'Test-Lock: T-01' commit", cli(d, "diff_scope", "docs/specs/001-x").stdout)

    def test_approval_format(self):
        closed = "- [x] T-01 Test — verify: `t` (Expected: Red) — covers: AC-001 — tests approved: {}\n"
        for value, valid in (("Anna, 2026-10-24, abc1234", True), ("Anna, 2026-10-24", False),
                             ("no, to redo", False), ("Mario <date>, 2026-10-24, abc1234", False)):
            with self.subTest(value):
                self.assertEqual(spec_lint.tests_to_approve(closed.format(value)) == [], valid)


class TestLevelCannotBeBypassed(unittest.TestCase):  # I2
    def test_rename_out_of_the_sensitive_area(self):
        with TmpDir() as d:
            write(d, "src/auth/login.py", "v1\n")  # already on the base
            repo(d, agents="# A\n- Sensitive areas: `src/auth/`\n", spec=spec_with_level("S"), plan=None)
            git(d, "mv", "src/auth/login.py", "src/login.py")
            r = cli(d, "diff_scope", "docs/specs/001-x", "--base", "main")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("sensitive area (AGENTS.md): src/auth/login.py", r.stdout)

    def test_agents_and_level_read_from_the_base(self):
        with TmpDir() as d:
            repo(d, agents="# A\n- Sensitive areas: src/auth/\n", spec=spec_with_level("M"))
            write(d, "AGENTS.md", "# A\n")  # the branch tries to remove the sensitive area
            write(d, "docs/specs/001-x/spec.md", spec_with_level("L"))
            write(d, "src/auth/login.py", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("AGENTS.md changed in the branch", r.stdout)
            self.assertIn("the spec declares M, the diff requires at least L", r.stdout)

    def test_descriptive_entries(self):
        with TmpDir() as d:
            repo(d, agents="# A\n- Sensitive areas: `src/auth/` (login), payments\n", spec=spec_with_level("M"))
            write(d, "src/auth/login.py", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertIn("the diff requires at least L", r.stdout)
            self.assertIn("does not look like a path, ignored: 'payments'", r.stdout)


class TestDependenciesAndAdr(unittest.TestCase):  # I3 and lockfiles
    def prepare(self, d, plan=PLAN_OK):
        repo(d, plan=plan)
        write(d, "docs/adr/README.md", "# ADR\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "adr readme")
        write(d, "package.json", "{}\n")
        write(d, "package-lock.json", "{}\n")

    def test_a_new_adr_is_needed(self):
        with TmpDir() as d:
            self.prepare(d)
            write(d, "docs/adr/README.md", "# ADR\nupdated\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("dependencies changed without plan or ADR: package.json", r.stdout)
            write(d, "docs/adr/0001-new-dependency.md", "# ADR 1\n")
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)

    def test_lockfile_of_the_planned_manifest(self):
        plan = PLAN_OK.replace("- `tests/`: new tests", "- `tests/`: new tests\n- package.json: dependency x")
        with TmpDir() as d:
            self.prepare(d, plan=plan)
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)


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


class TestGeneratedFiles(unittest.TestCase):  # I5
    def test_pycache_and_reports_do_not_count(self):
        with TmpDir() as d:
            repo(d, spec=spec_with_level("S"), plan=None)
            for i in range(3):
                write(d, f"src/m{i}.py", "x\n")
            write(d, "reports/junit.xml", "<testsuite/>")
            write(d, "scripts/__pycache__/x.cpython-313.pyc", "x")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertFalse((d / "scripts" / "__pycache__" / "spec_lint.cpython-313.pyc").exists())

    def test_a_changing_report_is_not_progress(self):
        agent = ("import sys, time\nsys.stdin.read()\nimport os\nos.makedirs('reports', exist_ok=True)\n"
                 "open('reports/junit.xml', 'w').write(str(time.time()))\n")
        with TmpDir() as d:
            copy_scripts(d, ["loop", "spec_lint"])
            write(d, "scripts/verify.py", "import sys\nsys.exit(0)\n")
            write(d, "docs/specs/001-x/tasks.md", "- [ ] T-01 a\n")
            write(d, "docs/specs/001-x/PROMPT.md", "p\n")
            write(d, "agent.py", agent)
            git_repo(d, "feature/x")
            env = {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]}
            r = run([sys.executable, "scripts/loop.py", "docs/specs/001-x", "--agent", f"{PY} agent.py",
                     "--stall", "2", "--max", "6"], d, env=env)
            self.assertIn("No progress for 2 iterations", r.stdout)


class TestLoopUsesSpecLint(unittest.TestCase):  # I6
    def test_level_in_the_revisions_does_not_count(self):
        with TmpDir() as d:
            copy_scripts(d, ["loop", "spec_lint"])
            write(d, "scripts/verify.py", "import sys\nsys.exit(1)\n")
            write(d, "docs/specs/001-x/spec.md", "# SPEC-001: x\n\n- Level: L\n\n## Revisions\n- Level: S (before)\n")
            write(d, "docs/specs/001-x/tasks.md", "- [x] T-01 t (expected: red) — tests approved: Mario <date>\n"
                                                  "- [ ] T-02 i\n")
            write(d, "docs/specs/001-x/PROMPT.md", "p\n")
            write(d, "agent.py", "import sys\nsys.stdin.read()\n")
            git_repo(d, "feature/x")
            env = {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]}
            r = run([sys.executable, "scripts/loop.py", "docs/specs/001-x", "--agent", f"{PY} agent.py",
                     "--dry-run"], d, env=env)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("are waiting for human approval", r.stdout)


class TestLoopPermissions(unittest.TestCase):  # I8
    def test_checks_and_rules_not_writable(self):
        perm = json.loads(read("skills/sdd-loop/references/settings.loop.json"))["permissions"]
        for protected in ("./scripts/**", "./AGENTS.md", "./.github/**", "./docs/specs/*/spec.md"):
            self.assertIn(f"Edit({protected})", perm["deny"])
            self.assertIn(f"Write({protected})", perm["deny"])
        self.assertIn("Bash(python3 scripts/verify.py:*)", perm["allow"])


class TestMinor(unittest.TestCase):
    def test_secrets_non_ascii_names_and_exclusions(self):
        token = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
        with TmpDir() as d:
            copy_scripts(d, ["secrets_check"])
            git_repo(d, "main")
            write(d, "src/configuración_è.py", f'T = "{token}"\n')
            write(d, ".env.local.example", "X=\n")
            write(d, ".env.development", "X=1\n")
            git(d, "add", "-A")
            git(d, "commit", "-qm", "base")
            r = cli(d, "secrets_check", "--all")
            self.assertIn("src/configuración_è.py:1: GitHub token", r.stdout)
            self.assertNotIn(".env.local.example", r.stdout)
            self.assertIn(".env.development: .env file", r.stdout)
            write(d, ".secrets-ignore", "# Vite convention\n.env.development\n")
            self.assertNotIn(".env.development", cli(d, "secrets_check", "--all").stdout)

    def test_guard_variants(self):
        def guard(c):
            return run([sys.executable, str(HOOKS / "pretool_guard.py")], HOOKS,
                       stdin=json.dumps({"tool_name": "Bash", "tool_input": {"command": c}}),
                       env={"SDD_GUARD": "1"}).returncode
        for c in ("git reset HEAD~1 --hard", "git -C . reset --hard", "git clean -d -f", "cat .env>out.txt",
                  "cat <.env", "python3 -c \"open('.env')\"", "find . -delete"):
            with self.subTest(c):
                self.assertEqual(guard(c), 2)
        for c in ("git rm -r --cached build/", "grep -n '\\.env' .gitignore", "git check-ignore -v .env",
                  "git commit -m 'rm -rf in the message'"):
            with self.subTest(c):
                self.assertEqual(guard(c), 0)
        r = run([sys.executable, str(HOOKS / "pretool_guard.py")], HOOKS,
                stdin=json.dumps({"tool_name": "Bash", "tool_input": "x"}), env={"SDD_GUARD": "1"})
        self.assertEqual(r.returncode, 2)

    def test_sync_check_folder_after_the_options(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "docs/specs/001-x/spec.md", SPEC_OK)
            write(d, "r.xml", "<testsuite/>")
            r = cli(d, "sync_check", "--junit", "r.xml", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("Status is 'approved'", r.stdout)


if __name__ == "__main__":
    unittest.main()
