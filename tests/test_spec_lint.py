"""Tests of spec_lint: spec, plan with vertical tasks, diagrams of the documentation pages."""
from __future__ import annotations

import sys
import unittest

from common import AREA_OK, PLAN_OK, SPEC_OK, TmpDir, copy_scripts, load, read, run, write

spec_lint = load("spec_lint")


class TestSpec(unittest.TestCase):
    def test_valid_spec(self):
        self.assertEqual(spec_lint.lint_spec(SPEC_OK, "001-x"), ([], []))

    def test_structure(self):
        cases = {
            "Status missing or invalid": SPEC_OK.replace("Status: approved", "Status: in-revision"),
            "Missing section: '## Scope'": SPEC_OK.replace("## Scope", "## Range"),
            "REQ-002 has no acceptance criterion": SPEC_OK.replace(
                "- REQ-001 (functional): the report can be exported as CSV",
                "- REQ-001 (functional): a\n- REQ-002 (functional): b"),
            "AC-001 cites REQ-009, which does not exist": SPEC_OK.replace("AC-001 [REQ-001]", "AC-001 [REQ-009]"),
            "Duplicate AC IDs": SPEC_OK.replace("AC-002 [REQ-001", "AC-001 [REQ-001"),
            "Non-scope missing or not filled in": SPEC_OK.replace("no change to the PDF format", "<what must not>"),
        }
        for expected, text in cases.items():
            with self.subTest(expected):
                self.assertTrue(any(expected in e for e in spec_lint.lint_spec(text)[0]), spec_lint.lint_spec(text))

    def test_open_questions(self):
        blocking = SPEC_OK.replace("- none", "- Which separator? — blocking: yes")
        self.assertTrue(any("blocking open questions" in e for e in spec_lint.lint_spec(blocking)[0]))
        unmarked = SPEC_OK.replace("- none", "- Which separator?")
        self.assertTrue(any("blocking open questions" in e for e in spec_lint.lint_spec(unmarked)[0]))
        self.assertEqual(spec_lint.lint_spec(unmarked.replace("approved", "draft"))[0], [])  # a draft may ask
        non_blocking = SPEC_OK.replace("- none", "- Which file name? — blocking: no")
        err, warn = spec_lint.lint_spec(non_blocking)
        self.assertEqual(err, [])
        self.assertTrue(any("Non-blocking open questions" in w for w in warn))

    def test_warnings(self):
        vague = SPEC_OK.replace("then I get a valid CSV", "then I get a CSV quickly, etc")
        self.assertTrue(any("AC-001: vague words (etc, quickly)" in w for w in spec_lint.lint_spec(vague)[1]))
        no_goals = SPEC_OK.replace("- **Anti-goals:** a CSV that spreadsheets open with broken columns\n", "")
        self.assertTrue(any("Anti-goals" in w for w in spec_lint.lint_spec(no_goals)[1]))
        assumption = SPEC_OK.replace("Export the report as CSV.", "Export the report as CSV. [ASSUMPTION] UTF-8")
        self.assertTrue(any("[ASSUMPTION]" in w for w in spec_lint.lint_spec(assumption)[1]))

    def test_date_id_and_folder(self):
        dated = SPEC_OK.replace("# SPEC-001: Example", "# SPEC-2026-10-24-export-csv: Example")
        self.assertEqual(spec_lint.lint_spec(dated, "2026-10-24-export-csv")[0], [])
        self.assertTrue(any("differs from the folder name" in e for e in spec_lint.lint_spec(dated, "2026-10-24-x")[0]))
        self.assertTrue(any("leading date is not valid" in e
                            for e in spec_lint.lint_spec(dated.replace("2026-10-24", "2026-13-40"))[0]))
        self.assertTrue(any("Title without ID" in e
                            for e in spec_lint.lint_spec(SPEC_OK.replace("# SPEC-001: Example", "# Example"))[0]))
        self.assertTrue(any("folder number" in e for e in spec_lint.lint_spec(SPEC_OK, "002-x")[0]))
        self.assertEqual(spec_lint.id_key("007"), "7")


class TestPlan(unittest.TestCase):
    def test_valid_plan(self):
        self.assertEqual(spec_lint.lint_plan(SPEC_OK, PLAN_OK), ([], []))
        tasks = spec_lint.parse_tasks(PLAN_OK)
        self.assertEqual([t["id"] for t in tasks], ["T-01", "T-02"])
        self.assertEqual(tasks[0]["files"], ["src/export.py", "tests/test_export.py"])
        self.assertEqual(tasks[1]["depends"], ["T-01"])
        self.assertEqual(tasks[1]["verify"], "pytest -k AC_002")

    def test_task_errors(self):
        t1 = "- [ ] T-01 Export a report as CSV — covers: AC-001 — files: `src/export.py`, `tests/test_export.py` — " \
             "depends: none — verify: `pytest -k AC_001`"
        cases = {
            "T-01: missing 'covers: AC-nnn'": t1.replace("covers: AC-001 — ", ""),
            "T-01: covers AC-009, which is not in the spec": t1.replace("covers: AC-001", "covers: AC-001, AC-009"),
            "T-01: missing 'files:'": t1.replace("files: `src/export.py`, `tests/test_export.py` — ", ""),
            "T-01: missing 'verify: `<command>`'": t1.replace(" — verify: `pytest -k AC_001`", ""),
            "T-01: missing 'depends: T-nn | none'": t1.replace("depends: none — ", ""),
            "T-01: depends on T-07, which is not a task": t1.replace("depends: none", "depends: T-07"),
            "T-01: placeholder not filled in": t1.replace("Export a report as CSV", "<goal>"),
            "Dependency cycle between tasks": t1.replace("depends: none", "depends: T-02"),
        }
        for expected, line in cases.items():
            with self.subTest(expected):
                err = spec_lint.lint_plan(SPEC_OK, PLAN_OK.replace(t1, line))[0]
                self.assertTrue(any(expected in e for e in err), err)

    def test_sections_and_coverage(self):
        only_one = PLAN_OK.replace(PLAN_OK.splitlines()[-4] + "\n", "")  # drops T-02, the task of AC-002
        self.assertTrue(any("AC-002 is not covered by any task" in e for e in spec_lint.lint_plan(SPEC_OK, only_one)[0]))
        no_flow = PLAN_OK.replace("flowchart TD", "sequenceDiagram")
        self.assertTrue(any("Flowchart not filled in" in e for e in spec_lint.lint_plan(SPEC_OK, no_flow)[0]))
        self.assertTrue(any("'## Flowchart' missing" in e
                            for e in spec_lint.lint_plan(SPEC_OK, PLAN_OK.replace("## Flowchart", "## Picture"))[0]))
        self.assertTrue(any("'## Tasks' missing" in e
                            for e in spec_lint.lint_plan(SPEC_OK, PLAN_OK.replace("## Tasks", "## Steps"))[0]))
        self.assertTrue(any("Review focus not filled in" in e
                            for e in spec_lint.lint_plan(SPEC_OK, PLAN_OK.replace("- none\n", "- <input>: <x>\n"))[0]))
        self.assertTrue(any("Approach" in w
                            for w in spec_lint.lint_plan(SPEC_OK, PLAN_OK.replace("## Approach", "## Idea"))[1]))

    def test_too_many_tasks_is_a_warning(self):
        lines = "".join(f"- [ ] T-{i:02d} Slice {i} — covers: AC-001, AC-002 — files: `src/m{i}.py` — depends: none "
                        f"— verify: `pytest`\n" for i in range(1, 10))
        plan = PLAN_OK.split("## Tasks")[0] + "## Tasks\n" + lines + "\n## Review focus\n- none\n"
        err, warn = spec_lint.lint_plan(SPEC_OK, plan)
        self.assertEqual(err, [])
        self.assertTrue(any("9 tasks (usually at most 8)" in w for w in warn))

    def test_templates_report_only_what_is_left_to_fill(self):
        spec = read("skills/sdd-start/references/spec-template.md")
        err, _ = spec_lint.lint_plan(spec, read("skills/sdd-plan/references/plan-template.md"))
        self.assertTrue(err)
        self.assertTrue(all("not filled in" in e for e in err), err)


class TestDiagrams(unittest.TestCase):
    def test_documentation_pages(self):
        self.assertEqual(spec_lint.diagram_problems(AREA_OK), [])
        drawn = "```mermaid\nerDiagram\n    REPORT ||--o{ ROW : has\n```"
        self.assertEqual(spec_lint.diagram_problems(AREA_OK.replace("- n/a: no persistent data", drawn)), [])
        cases = {
            "Section '## Diagrams' missing": AREA_OK.replace("## Diagrams", "## Pictures"),
            "subsection '### State diagram' missing": AREA_OK.replace("### State diagram", "### States"),
            "'ER diagram' needs a Mermaid block starting with erDiagram, found 'classDiagram'":
                AREA_OK.replace("- n/a: no persistent data", drawn.replace("erDiagram", "classDiagram")),
            "'Flowchart' always applies": AREA_OK.replace("```mermaid\nflowchart TD\n    A[export] --> B{rows?}\n```",
                                                          "- n/a: trivial"),
            "'Class diagram' not filled in": AREA_OK.replace("- n/a: no new types", "- <mermaid block>"),
        }
        for expected, text in cases.items():
            with self.subTest(expected):
                self.assertTrue(any(expected in p for p in spec_lint.diagram_problems(text)))
        self.assertEqual(spec_lint.mermaid_type("---\ntitle: x\n---\n%% note\nstateDiagram-v2\n[*] --> A"),
                         "stateDiagram-v2")


class TestCli(unittest.TestCase):
    def test_cli(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "docs/specs/001-x/spec.md", SPEC_OK)
            write(d, "docs/specs/001-x/plan.md", PLAN_OK)
            ok = run([sys.executable, "scripts/spec_lint.py", "docs/specs/001-x/spec.md", "--plan",
                      "docs/specs/001-x/plan.md"], d)
            self.assertEqual(ok.returncode, 0, ok.stdout)
            write(d, "docs/specs/001-x/plan.md", PLAN_OK.replace("covers: AC-002", "covers: AC-009"))
            ko = run([sys.executable, "scripts/spec_lint.py", "docs/specs/001-x/spec.md", "--plan",
                      "docs/specs/001-x/plan.md"], d)
            self.assertEqual(ko.returncode, 1, ko.stdout)
            self.assertEqual(run([sys.executable, "scripts/spec_lint.py"], d).returncode, 2)


if __name__ == "__main__":
    unittest.main()
