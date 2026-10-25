"""Tests of verify.py, spec_lint.py and state.py."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

from common import (PLAN_OK, REVIEW_OK, SCRIPTS, SPEC_OK, TASKS_OK, TmpDir, copy_scripts, git, git_repo, load, read,
                    run, write)

spec_lint = load("spec_lint")
state = load("state")


class TestSpecLint(unittest.TestCase):
    def test_valid_spec(self):
        self.assertEqual(spec_lint.lint_spec(SPEC_OK)[0], [])

    def test_draft_template_reports_the_non_scope(self):
        err, _ = spec_lint.lint_spec(read("skills/sdd-spec/references/spec-template.md"))
        self.assertTrue(any("Non-scope" in e for e in err))

    def test_approved_without_approver(self):
        err, _ = spec_lint.lint_spec(SPEC_OK.replace("Anna Smith, 2026-10-19", "<name, yyyy-mm-dd>"))
        self.assertTrue(any("Approved by" in e for e in err))

    def test_req_without_ac(self):
        t = SPEC_OK.replace("- REQ-001 (functional): the report can be exported as CSV",
                            "- REQ-001 (functional): a\n- REQ-002 (functional): b")
        self.assertTrue(any("REQ-002" in e for e in spec_lint.lint_spec(t)[0]))

    def test_ac_with_missing_req(self):
        err, _ = spec_lint.lint_spec(SPEC_OK.replace("AC-002 [REQ-001, error]", "AC-002 [REQ-009]"))
        self.assertTrue(any("REQ-009" in e for e in err))

    def test_open_questions_on_approved_spec(self):
        err, _ = spec_lint.lint_spec(SPEC_OK.replace("- none", "- Which separator?"))
        self.assertTrue(any("open questions" in e for e in err))

    def test_empty_non_scope(self):
        err, _ = spec_lint.lint_spec(SPEC_OK.replace("no change to the PDF format", ""))
        self.assertTrue(any("Non-scope" in e for e in err))

    def test_plan(self):
        self.assertEqual(spec_lint.lint_plan(SPEC_OK, PLAN_OK)[0], [])
        err, _ = spec_lint.lint_plan(SPEC_OK, PLAN_OK.replace("AC-002", "AC-XXX"))
        self.assertTrue(any("AC-002" in e for e in err))
        _, warn = spec_lint.lint_plan(SPEC_OK, PLAN_OK.replace("Anna Smith, 2026-10-19", "<name>"))
        self.assertTrue(warn)

    def test_anti_goals_warning(self):
        self.assertFalse(any("Anti-goals" in w for w in spec_lint.lint_spec(SPEC_OK)[1]))
        no_anti = SPEC_OK.replace("a CSV that spreadsheets open with broken columns", "<what would make it fail>")
        err, warn = spec_lint.lint_spec(no_anti)
        self.assertFalse(any("Anti-goals" in e for e in err))
        self.assertTrue(any("Anti-goals" in w for w in warn))

    def test_review_focus(self):
        table = ("## Review focus\n| Case | Expected behaviour | Where |\n|---|---|---|\n"
                 "| empty report | clear error | tests/test_export.py |\n")
        self.assertEqual(spec_lint.review_focus_problems(PLAN_OK), [])
        self.assertEqual(spec_lint.review_focus_problems(PLAN_OK.replace("## Review focus\n- none\n", table)), [])
        missing = PLAN_OK.replace("## Review focus\n- none\n", "")
        self.assertTrue(any("Review focus" in e for e in spec_lint.lint_plan(SPEC_OK, missing)[0]))
        placeholder = PLAN_OK.replace("## Review focus\n- none\n", table.replace("empty report", "<input>"))
        self.assertTrue(any("Review focus" in e for e in spec_lint.lint_plan(SPEC_OK, placeholder)[0]))  # approved
        unsigned = placeholder.replace("Anna Smith, 2026-10-19", "<name, yyyy-mm-dd>")
        err, warn = spec_lint.lint_plan(SPEC_OK, unsigned)
        self.assertFalse(any("Review focus" in e for e in err))
        self.assertTrue(any("Review focus" in w for w in warn))
        empty = PLAN_OK.replace("## Review focus\n- none\n", "## Review focus\n")
        self.assertTrue(spec_lint.review_focus_problems(empty))

    def test_plan_looks_for_exact_ids_in_the_test_strategy(self):
        cited_elsewhere = PLAN_OK.replace("| AC-002 | unit |\n", "") + "\n## Risks\n- AC-002 to evaluate\n"
        self.assertTrue(any("AC-002" in e for e in spec_lint.lint_plan(SPEC_OK, cited_elsewhere)[0]))
        self.assertTrue(any("AC-001" in e for e in
                            spec_lint.lint_plan(SPEC_OK, PLAN_OK.replace("| AC-001 |", "| AC-0011 |"))[0]))
        without = PLAN_OK.replace("## Test strategy (mapped to ACs)", "## Notes")
        self.assertTrue(any("Test strategy" in e for e in spec_lint.lint_plan(SPEC_OK, without)[0]))

    def test_date_id_and_folder(self):
        dated = SPEC_OK.replace("# SPEC-001: Example", "# SPEC-2026-10-24-export-csv: Example")
        self.assertEqual(spec_lint.spec_id(dated), "2026-10-24-export-csv")
        self.assertEqual(spec_lint.lint_spec(dated, "2026-10-24-export-csv")[0], [])
        self.assertTrue(any("differs from the folder name" in e
                            for e in spec_lint.lint_spec(dated, "2026-10-24-export")[0]))
        bad_date = dated.replace("2026-10-24", "2026-13-40")
        self.assertTrue(any("leading date is not valid" in e for e in spec_lint.lint_spec(bad_date)[0]))
        no_id = SPEC_OK.replace("# SPEC-001: Example", "# Example")
        self.assertTrue(any("Title without ID" in e for e in spec_lint.lint_spec(no_id)[0]))
        self.assertEqual(spec_lint.lint_spec(SPEC_OK, "001-x")[0], [])  # old IDs are still valid
        self.assertTrue(any("folder number" in e for e in spec_lint.lint_spec(SPEC_OK, "002-x")[0]))
        self.assertEqual(spec_lint.id_key("SPEC_2026_10_24_Export_csv"[5:]), "2026-10-24-export-csv")
        self.assertEqual(spec_lint.id_key("007"), "7")

    def test_spec_in_revision(self):
        rev = SPEC_OK.replace("Status: approved", "Status: in-revision").replace(
            "Export the report as CSV.", "Export the report as CSV and XLSX.")
        self.assertTrue(any("Revisions" in e for e in spec_lint.lint_spec(rev)[0]))
        with_entry = rev + "\n## Revisions\n- 2026-10-24: XLSX added, requested by the customer\n"
        self.assertEqual(spec_lint.lint_spec(with_entry)[0], [])  # in revision the old hash does not count

    def test_review_tasks_and_tasks_tied_to_the_plan(self):
        with_r = TASKS_OK + "- [ ] T-R01 Handle the empty file — verify: `pytest -k empty`\n"
        self.assertEqual(spec_lint.lint_tasks(SPEC_OK, with_r)[0], [])
        no_verify = TASKS_OK + "- [ ] T-R01 Handle the empty file\n"
        self.assertTrue(any("T-R01" in e and "verify" in e for e in spec_lint.lint_tasks(SPEC_OK, no_verify)[0]))
        self.assertTrue(spec_lint.tasks_on_plan(PLAN_OK, TASKS_OK)[1])  # without 'Based on plan': warning
        tied = f"- Based on plan: {spec_lint.fingerprint(PLAN_OK)}\n" + TASKS_OK
        self.assertEqual(spec_lint.tasks_on_plan(PLAN_OK, tied), ([], []))
        new_plan = PLAN_OK.replace("new export function", "rewritten export")
        self.assertTrue(spec_lint.tasks_on_plan(new_plan, tied)[0])

    def test_anti_drift_hash_of_the_spec(self):
        self.assertEqual(spec_lint.lint_spec(SPEC_OK.replace("Status: approved", "Status: implemented"))[0], [])
        changed = SPEC_OK.replace("Export the report as CSV.", "Export the report as CSV and XLSX.")
        self.assertTrue(any("changed after approval" in e for e in spec_lint.lint_spec(changed)[0]))
        without = "\n".join(line for line in SPEC_OK.splitlines() if not line.startswith("- Hash:"))
        self.assertTrue(any("without '- Hash:'" in e for e in spec_lint.lint_spec(without)[0]))
        draft = without.replace("Status: approved", "Status: draft")
        self.assertEqual(spec_lint.lint_spec(draft)[0], [])
        self.assertEqual(spec_lint.fingerprint(SPEC_OK), spec_lint.fingerprint(SPEC_OK.replace("\n", "\r\n")))

    def test_plan_lapses_if_the_spec_changes(self):
        self.assertEqual(spec_lint.lint_plan(SPEC_OK, PLAN_OK)[0], [])
        new = SPEC_OK.replace("Export the report as CSV.", "Export the report.")
        self.assertTrue(any("another version of the spec" in e for e in spec_lint.lint_plan(new, PLAN_OK)[0]))
        plan = PLAN_OK.replace("new export function", "rewritten export function")
        self.assertTrue(any("Plan: content changed" in e for e in spec_lint.lint_plan(SPEC_OK, plan)[0]))

    def test_hash_and_base_from_the_command_line(self):
        with TmpDir() as d:
            copy_scripts(d)
            git_repo(d, "main")
            write(d, "docs/specs/001-x/spec.md", SPEC_OK)
            write(d, "docs/specs/001-x/plan.md", PLAN_OK)
            r = run([sys.executable, "scripts/spec_lint.py", "docs/specs/001-x/spec.md", "--hash"], d)
            self.assertEqual(r.stdout.strip(), spec_lint.fingerprint(SPEC_OK))
            args = [sys.executable, "scripts/spec_lint.py", "docs/specs/001-x/spec.md", "--plan",
                    "docs/specs/001-x/plan.md", "--base", "main"]
            r = run(args, d)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("is not on main", r.stdout)
            git(d, "add", "-A")
            git(d, "commit", "-qm", "design approved")
            git(d, "checkout", "-qb", "feature/x")
            self.assertEqual(run(args, d).returncode, 0)
            write(d, "docs/specs/001-x/plan.md", PLAN_OK + "\n")
            self.assertEqual(run(args, d).returncode, 0)  # trailing whitespace differences do not count
            write(d, "docs/specs/001-x/plan.md", PLAN_OK.replace("Anna Smith", "Agent"))
            r = run(args, d)
            self.assertEqual(r.returncode, 1)
            self.assertIn("differs from the version on main", r.stdout)

    def test_tasks(self):
        self.assertEqual(spec_lint.lint_tasks(SPEC_OK, TASKS_OK)[0], [])
        err, _ = spec_lint.lint_tasks(SPEC_OK, TASKS_OK.replace("- [ ] T-DOC Documentation\n", ""))
        self.assertTrue(any("T-DOC" in e for e in err))
        err, _ = spec_lint.lint_tasks(SPEC_OK, TASKS_OK.replace("— verify: `pytest` ", ""))
        self.assertTrue(any("T-02" in e and "verify" in e for e in err))
        err, _ = spec_lint.lint_tasks(SPEC_OK, TASKS_OK.replace("covers: AC-001, AC-002", "covers: AC-001"))
        self.assertTrue(any("AC-002" in e and "covered" in e for e in err))
        err, _ = spec_lint.lint_tasks(SPEC_OK, TASKS_OK.replace("`pytest`", "`<targeted test command>`"))
        self.assertIn("T-02: placeholder not filled in <targeted test command>", err)

    def test_cli(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "spec.md", SPEC_OK)
            self.assertEqual(run([sys.executable, "scripts/spec_lint.py", "spec.md"], d).returncode, 0)
            write(d, "spec.md", SPEC_OK.replace("- none", "- Which separator?"))
            self.assertEqual(run([sys.executable, "scripts/spec_lint.py", "spec.md"], d).returncode, 1)
            self.assertEqual(run([sys.executable, "scripts/spec_lint.py"], d).returncode, 2)


class TestVerify(unittest.TestCase):
    def attempt(self, steps: str, args: list[str]):
        text = (SCRIPTS / "verify.py").read_text(encoding="utf-8")
        start, end = text.index("STEPS = ["), text.index("def run_step")
        with TmpDir() as d:
            write(d, "scripts/verify.py", text[:start] + "STEPS = " + steps + "\n\n\n" + text[end:])
            return run([sys.executable, "scripts/verify.py", *args], d)

    OK, KO = '[sys.executable, "-c", "pass"]', '[sys.executable, "-c", "import sys; sys.exit(1)"]'

    def test_green_and_red(self):
        self.assertEqual(self.attempt(f'[("a", {self.OK}, True), ("b", {self.OK}, False)]', []).returncode, 0)
        r = self.attempt(f'[("a", {self.OK}, True), ("b", {self.KO}, False)]', [])
        self.assertEqual(r.returncode, 1)
        self.assertIn("RED -> b", r.stdout)

    def test_fast_and_selection(self):
        s = f'[("a", {self.OK}, True), ("b", {self.KO}, False)]'
        self.assertEqual(self.attempt(s, ["--fast"]).returncode, 0)
        self.assertEqual(self.attempt(s, ["a"]).returncode, 0)

    def test_missing_command(self):
        r = self.attempt('[("x", ["command-that-does-not-exist-xyz"], True)]', [])
        self.assertEqual(r.returncode, 1)
        self.assertIn("not found", r.stdout)


class TestState(unittest.TestCase):
    def next(self, setup) -> dict:
        with TmpDir() as d:
            setup(d)
            return state.analyze(d)["next"]

    @staticmethod
    def init(r: Path):
        write(r, "AGENTS.md")
        write(r, "scripts/verify.py")

    def with_spec(self, r: Path, plan=True, tasks=None, review=None, status="approved"):
        self.init(r)
        write(r, "docs/specs/001-x/spec.md", SPEC_OK.replace("approved", status))
        if plan:
            write(r, "docs/specs/001-x/plan.md", PLAN_OK)
        if tasks is not None:
            write(r, "docs/specs/001-x/tasks.md", tasks)
        if review is not None:
            write(r, "docs/specs/001-x/review.md", review)

    def test_progression(self):
        self.assertEqual(self.next(lambda r: None)["skill"], "sdd-init")
        self.assertEqual(self.next(self.init)["skill"], "sdd-spec")
        self.assertEqual(self.next(lambda r: self.with_spec(r, plan=False))["skill"], "sdd-plan")
        self.assertEqual(self.next(lambda r: self.with_spec(r))["skill"], "sdd-tasks")
        p = self.next(lambda r: self.with_spec(r, tasks=TASKS_OK))
        self.assertEqual(p["skill"], "sdd-implement")
        self.assertIn("T-01", p["reason"])
        done = TASKS_OK.replace("[ ] T-01", "[x] T-01").replace("[ ] T-02", "[x] T-02")
        self.assertEqual(self.next(lambda r: self.with_spec(r, tasks=done))["skill"], "sdd-review-diff")
        self.assertEqual(self.next(lambda r: self.with_spec(r, tasks=done, review=REVIEW_OK))["skill"], "sdd-docs")
        no_doc = done.replace("[ ] T-DOC", "[x] T-DOC")
        self.assertEqual(self.next(lambda r: self.with_spec(r, tasks=no_doc, review=REVIEW_OK))["skill"], "sdd-sync")
        nc = REVIEW_OK.replace("Outcome: compliant", "Outcome: non-compliant")
        p = self.next(lambda r: self.with_spec(r, tasks=done, review=nc))
        self.assertEqual((p["skill"], "T-R" in p["reason"]), ("sdd-review-diff", True))
        with_r = done + "- [ ] T-R01 Fix — verify: `pytest`\n"
        self.assertEqual(self.next(lambda r: self.with_spec(r, tasks=with_r, review=nc))["skill"], "sdd-implement")
        r_done = with_r.replace("[ ] T-R01", "[x] T-R01")
        p = self.next(lambda r: self.with_spec(r, tasks=r_done, review=nc))
        self.assertEqual((p["skill"], "repeat the review" in p["reason"]), ("sdd-review-diff", True))
        everything = done.replace("[ ]", "[x]")
        self.assertEqual(self.next(lambda r: self.with_spec(r, tasks=everything, review=REVIEW_OK,
                                                            status="implemented"))["skill"], "sdd-spec")

    def test_plan_not_approved(self):
        def setup(r):
            self.with_spec(r)
            write(r, "docs/specs/001-x/plan.md", PLAN_OK.replace("Anna Smith, 2026-10-19", "<name>"))
        self.assertEqual(self.next(setup)["skill"], "sdd-plan")

    def test_revision_and_tasks_on_another_plan(self):
        def in_revision(r):
            self.with_spec(r, tasks=TASKS_OK, status="in-revision")
        p = self.next(in_revision)
        self.assertEqual((p["skill"], "revision" in p["reason"]), ("sdd-spec", True))

        def old_tasks(r):
            self.with_spec(r, tasks="- Based on plan: sha256:old\n" + TASKS_OK)
        p = self.next(old_tasks)
        self.assertEqual((p["skill"], "another version of the plan" in p["reason"]), ("sdd-tasks", True))

    def test_several_active_specs(self):
        def two(r):
            self.with_spec(r, tasks=TASKS_OK)
            dated = SPEC_OK.replace("# SPEC-001: Example", "# SPEC-2026-10-24-export-csv: Export")
            write(r, "docs/specs/2026-10-24-export-csv/spec.md", dated)
        with TmpDir() as d:
            two(d)
            st = state.analyze(d)
            self.assertEqual(st["next"]["skill"], "choose")
            self.assertIn("001-x (sdd-implement)", st["next"]["reason"])
            self.assertIn("2026-10-24-export-csv (sdd-plan)", st["next"]["reason"])
            self.assertEqual(state.analyze(d, "SPEC-2026-10-24-export-csv")["next"]["skill"], "sdd-plan")
            self.assertEqual(state.analyze(d, "001-x")["next"]["skill"], "sdd-implement")
            self.assertEqual(state.analyze(d, "missing")["next"]["skill"], "choose")
            git_repo(d, "feat/2026-10-24-export-csv")
            self.assertEqual(state.analyze(d)["next"]["spec"], "2026-10-24-export-csv")
            copy_scripts(d)
            r = run([sys.executable, "scripts/state.py", "--spec", "001-x"], d)
            self.assertIn("NEXT: sdd-implement on 001-x", r.stdout)
            self.assertIn("BRANCH: feat/2026-10-24-export-csv", r.stdout)

    def test_lapsed_approvals(self):
        def spec_changed(r):
            self.with_spec(r, tasks=TASKS_OK)
            write(r, "docs/specs/001-x/spec.md", SPEC_OK.replace("Export the report as CSV.", "Other."))
        p = self.next(spec_changed)
        self.assertEqual(p["skill"], "sdd-spec")
        self.assertIn("Hash", p["reason"])

        def plan_changed(r):
            self.with_spec(r, tasks=TASKS_OK)
            write(r, "docs/specs/001-x/plan.md", PLAN_OK.replace("new export function", "other"))
        p = self.next(plan_changed)
        self.assertEqual(p["skill"], "sdd-plan")
        self.assertIn("must be re-approved", p["reason"])

    def test_brownfield_suggests_the_map(self):
        def setup(r):
            self.init(r)
            for i in range(4):
                write(r, f"src/m{i}.py")
        self.assertEqual(self.next(setup)["skill"], "sdd-map-codebase")

        def with_map(r):
            setup(r)
            write(r, "docs/system/map.md")
        self.assertEqual(self.next(with_map)["skill"], "sdd-spec")

    def test_scripts_and_docs_do_not_count_as_code(self):
        def setup(r):
            self.init(r)
            for i in range(5):
                write(r, f"scripts/s{i}.py")
        self.assertEqual(self.next(setup)["skill"], "sdd-spec")

    def test_unverified_bugs(self):
        with TmpDir() as d:
            self.init(d)
            write(d, "docs/bugs/BUG-001.md", "- Status: open\n")
            write(d, "docs/bugs/BUG-002.md", "- Status: verified\n")
            self.assertEqual([b["file"] for b in state.analyze(d)["open_bugs"]], ["BUG-001.md"])

    def test_cli_json(self):
        with TmpDir() as d:
            copy_scripts(d)
            r = run([sys.executable, "scripts/state.py", "--json"], d)
            self.assertEqual(r.returncode, 0)
            self.assertIn("sdd-init", r.stdout)


if __name__ == "__main__":
    unittest.main()
