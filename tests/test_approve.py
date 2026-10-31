"""Tests of approve.py: approvals recorded in one step, refused when the result would not pass the checks."""
from __future__ import annotations

import re
import sys
import unittest
from datetime import date

from common import (PLAN_OK, REVIEW_OK, SPEC_OK, TASKS_OK, TmpDir, copy_scripts, git, git_repo, load, run, write)

spec_lint = load("spec_lint")
TODAY = date.today().isoformat()
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
F = "docs/specs/001-x/"


def unapproved(text: str) -> str:
    text = re.sub(r"^- Hash:.*\n", "", text, flags=re.M)
    text = re.sub(r"^- Based on spec:.*\n", "", text, flags=re.M)
    return text.replace("Anna Smith, 2026-10-19", "<name, yyyy-mm-dd>").replace("Status: approved", "Status: draft")


def cli(d, *args: str):
    return run([sys.executable, "scripts/approve.py", *args], d, env=GIT_ENV)


class TestApprove(unittest.TestCase):
    def prepare(self, d):
        copy_scripts(d)
        git_repo(d, "main")
        write(d, "README.md", "# p\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feat/001-x")

    def test_spec_plan_and_tasks(self):
        with TmpDir() as d:
            self.prepare(d)
            write(d, F + "spec.md", unapproved(SPEC_OK))
            write(d, F + "plan.md", unapproved(PLAN_OK))
            write(d, F + "tasks.md", TASKS_OK)
            self.assertEqual(cli(d, "plan", F + "plan.md", "--by", "Anna").returncode, 1)  # spec not approved yet
            r = cli(d, "spec", F + "spec.md", "--by", "Anna Smith", "--commit")
            self.assertEqual(r.returncode, 0, r.stdout)
            spec = (d / F / "spec.md").read_text(encoding="utf-8")
            self.assertIn("- Status: approved", spec)
            self.assertIn(f"- Approved by / date: Anna Smith, {TODAY}", spec)
            self.assertEqual(spec_lint.lint_spec(spec, "001-x")[0], [])
            self.assertIn("001: approve spec (Anna Smith)", git(d, "log", "-1", "--format=%B"))
            self.assertIn("Approved-by: Anna Smith", git(d, "log", "-1", "--format=%B"))
            self.assertEqual(cli(d, "plan", F + "plan.md", "--by", "Anna Smith").returncode, 0)
            plan = (d / F / "plan.md").read_text(encoding="utf-8")
            self.assertEqual(spec_lint.lint_plan(spec, plan)[0], [])
            self.assertEqual(cli(d, "tasks", F + "tasks.md").returncode, 0)
            tasks = (d / F / "tasks.md").read_text(encoding="utf-8")
            self.assertEqual(spec_lint.tasks_on_plan(plan, tasks), ([], []))

    def test_refused_when_the_result_would_not_pass(self):
        with TmpDir() as d:
            self.prepare(d)
            blocking = unapproved(SPEC_OK).replace("## Open questions\n- none",
                                                   "## Open questions\n- Which encoding? — blocking: yes")
            write(d, F + "spec.md", blocking)
            r = cli(d, "spec", F + "spec.md", "--by", "Anna")
            self.assertEqual(r.returncode, 1)
            self.assertIn("NOT RECORDED", r.stdout)
            self.assertEqual((d / F / "spec.md").read_text(encoding="utf-8"), blocking)  # nothing written
            self.assertEqual(cli(d, "spec", F + "spec.md").returncode, 2)  # no name
            self.assertEqual(cli(d, "spec", F + "spec.md", "--by", "<name>").returncode, 2)

    def test_tests_and_review(self):
        with TmpDir() as d:
            self.prepare(d)
            write(d, F + "spec.md", SPEC_OK)
            tasks = TASKS_OK.replace(" — tests approved: Anna Smith, 2026-10-19, abc1234", "").replace("[ ] T-01", "[x] T-01")
            write(d, F + "tasks.md", tasks)
            self.assertEqual(cli(d, "tests", F[:-1], "T-01", "--by", "Anna").returncode, 1)  # no Test-Lock commit
            write(d, "tests/test_export.py", "def test_AC_001(): assert False\n")
            git(d, "add", "-A")
            git(d, "commit", "-qm", "red tests", "-m", "Test-Lock: T-01")
            sha = git(d, "rev-parse", "--short=7", "HEAD")
            r = cli(d, "tests", F[:-1], "T-01", "--by", "Anna", "--commit")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertEqual(spec_lint.test_approvals((d / F / "tasks.md").read_text(encoding="utf-8")),
                             {"T-01": sha})
            write(d, F + "review.md", REVIEW_OK.replace("Anna Smith, 2026-10-19", "<name, yyyy-mm-dd>")
                  + "- Human diff review: <name, yyyy-mm-dd>\n")
            self.assertEqual(cli(d, "review", F[:-1], "--by", "Anna", "--diff-read").returncode, 0)
            review = (d / F / "review.md").read_text(encoding="utf-8")
            self.assertIn(f"- Decided by: Anna, {TODAY}", review)
            self.assertIn(f"- Human diff review: Anna, {TODAY}", review)


class TestSoloFlow(unittest.TestCase):
    """End to end in the solo profile: the agent approves only what the user selected and moves main by fast-forward."""

    def test_level_s_feature(self):
        import json
        with TmpDir() as d:
            copy_scripts(d)
            git_repo(d, "main")
            write(d, "AGENTS.md", "# A\n\n## Process\n- Profile: solo\n- Approvers: Anna Smith\n")
            git(d, "add", "-A")
            git(d, "commit", "-qm", "init")
            git(d, "checkout", "-qb", "feat/001-x")
            write(d, F + "spec.md", unapproved(SPEC_OK).replace("- Status:", "- Level: S\n- Status:"))
            write(d, F + "tasks.md", "- Based on plan: n/a\n\n- [ ] T-01 Tests — verify: `pytest` (expected: red) — "
                                     "covers: AC-001, AC-002\n- [ ] T-02 Compose — verify: `pytest` — covers: AC-001, "
                                     "AC-002\n- [ ] T-SYNC Reconcile\n")
            self.assertEqual(cli(d, "spec", F + "spec.md", "--by", "Anna Smith", "--commit").returncode, 0)
            self.assertEqual(cli(d, "tasks", F + "tasks.md", "--commit").returncode, 0)

            def nxt():
                r = run([sys.executable, "scripts/state.py", "--json"], d)
                return json.loads(r.stdout)["next"]

            self.assertIn("git fetch . HEAD:main", nxt()["reason"])
            git(d, "fetch", "-q", ".", "HEAD:main")  # fast-forward of main, the branch stays checked out
            self.assertEqual(nxt()["skill"], "sdd-implement")
            r = run([sys.executable, "scripts/spec_lint.py", F + "spec.md", "--tasks", F + "tasks.md", "--base", "main"], d)
            self.assertEqual(r.returncode, 0, r.stdout)
            for f in ("compose.yaml", ".env.example", "clickhouse/users.xml", "clickhouse/config.xml"):
                write(d, f, "x\n")
            write(d, "scripts/verify.py", "# adapted steps\n")
            r = run([sys.executable, "scripts/diff_scope.py", F[:-1]], d)
            self.assertEqual(r.returncode, 0, r.stdout)  # level S kept: the size is a warning, not a violation
            self.assertIn("[WARN] level S with 4 production files", r.stdout)


if __name__ == "__main__":
    unittest.main()
