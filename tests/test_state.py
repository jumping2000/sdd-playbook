"""Tests of state.py: the next step of a feature, from the idea to the last merged task (git-based, end to end)."""
from __future__ import annotations

import json
import sys
import unittest

from common import PLAN_OK, SPEC_OK, TmpDir, copy_scripts, git, git_repo, load, run, write

state = load("state")
F = "docs/specs/001-x/"


def nxt(d, *args: str) -> dict:
    r = run([sys.executable, "scripts/state.py", "--json", *args], d)
    return json.loads(r.stdout)["next"]


def project(d):
    copy_scripts(d)
    git_repo(d, "main")
    write(d, "AGENTS.md", "# A\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "init")


def merge(d, branch: str):
    """What the agent does after the user selects the merge (no remote): fast-forward of main, back on main."""
    git(d, "switch", "-q", "main")
    git(d, "merge", "-q", "--ff-only", branch)


class TestFlow(unittest.TestCase):
    def test_feature_with_two_dependent_tasks(self):
        with TmpDir() as d:
            project(d)
            self.assertEqual(nxt(d)["skill"], "sdd-start")  # no spec yet
            git(d, "switch", "-qc", "spec/001-x")
            write(d, F + "spec.md", SPEC_OK.replace("Status: approved", "Status: draft"))
            self.assertEqual(nxt(d)["skill"], "sdd-start")
            write(d, F + "spec.md", SPEC_OK)  # the user confirmed the spec
            self.assertEqual(nxt(d)["skill"], "sdd-plan")
            write(d, F + "plan.md", PLAN_OK)
            step = nxt(d)
            self.assertEqual(step["skill"], "sdd-plan")
            self.assertIn("design PR", step["reason"])
            git(d, "add", "-A")
            git(d, "commit", "-qm", "001-x: spec and plan")
            merge(d, "spec/001-x")  # the merge of the design PR is the approval
            step = nxt(d)
            self.assertEqual((step["skill"], step["tasks"]), ("sdd-task", ["T-01"]))  # T-02 depends on T-01
            git(d, "switch", "-qc", "task/001-x-T-01")
            write(d, "src/export.py", "x\n")
            write(d, F + "plan.md", PLAN_OK.replace("- [ ] T-01", "- [x] T-01"))
            git(d, "add", "-A")
            git(d, "commit", "-qm", "T-01", "-m", "Task: T-01")
            self.assertEqual(nxt(d)["tasks"], ["T-01"])  # not merged yet: main still has it open
            merge(d, "task/001-x-T-01")
            self.assertEqual(nxt(d)["tasks"], ["T-02"])
            git(d, "switch", "-qc", "task/001-x-T-02")
            write(d, F + "plan.md", PLAN_OK.replace("- [ ]", "- [x]"))
            git(d, "commit", "-qam", "T-02", "-m", "Task: T-02")
            merge(d, "task/001-x-T-02")
            step = nxt(d)
            self.assertEqual(step["skill"], "sdd-task")
            self.assertIn("close the feature", step["reason"])
            write(d, F + "spec.md", SPEC_OK.replace("Status: approved", "Status: implemented"))
            self.assertEqual(nxt(d)["skill"], "sdd-start")  # no active spec: next idea

    def test_independent_tasks_run_in_parallel(self):
        plan = PLAN_OK.replace("— files: `src/export.py`, `tests/test_export.py` — depends: T-01",
                               "— files: `src/errors.py`, `tests/test_errors.py` — depends: none")
        with TmpDir() as d:
            project(d)
            write(d, F + "spec.md", SPEC_OK)
            write(d, F + "plan.md", plan)
            git(d, "add", "-A")
            git(d, "commit", "-qm", "design")
            step = nxt(d)
            self.assertEqual((step["skill"], step["tasks"]), ("sdd-parallel", ["T-01", "T-02"]))
            shared = plan.replace("`src/errors.py`", "`src/export.py`")  # same file: one after the other
            write(d, F + "plan.md", shared)
            git(d, "commit", "-qam", "plan revised")
            self.assertEqual(nxt(d)["skill"], "sdd-task")


class TestState(unittest.TestCase):
    def test_initialization_and_brownfield(self):
        with TmpDir() as d:
            copy_scripts(d, ["state", "spec_lint"])
            self.assertEqual(nxt(d)["skill"], "sdd-start")  # no AGENTS.md, no verify.py
            write(d, "AGENTS.md", "# A\n")
            write(d, "scripts/verify.py", "")
            for i in range(3):
                write(d, f"src/m{i}.py", "x\n")
            self.assertEqual(nxt(d)["skill"], "sdd-map")
            write(d, "docs/system/map.md", "# Map\n")
            self.assertEqual(nxt(d)["skill"], "sdd-start")

    def test_infrastructure_counts_as_existing_code(self):
        with TmpDir() as d:
            copy_scripts(d, ["state", "spec_lint"])
            write(d, "AGENTS.md", "# A\n")
            write(d, "scripts/verify.py", "")
            for f in ("compose.yaml", "Dockerfile", "charts/web/Chart.yaml"):
                write(d, f, "x\n")
            self.assertEqual(nxt(d)["skill"], "sdd-map")

    def test_several_specs_bugs_and_text_output(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "AGENTS.md", "# A\n")
            for sid in ("001-x", "002-y"):
                write(d, f"docs/specs/{sid}/spec.md", SPEC_OK.replace("Status: approved", "Status: draft"))
            write(d, "docs/bugs/BUG-001.md", "# BUG-001\n- Status: open\n")
            self.assertEqual(nxt(d)["skill"], "choose")
            self.assertEqual(nxt(d, "--spec", "002-y")["spec"], "002-y")
            r = run([sys.executable, "scripts/state.py"], d)
            self.assertIn("OPEN BUGS: BUG-001.md (open)", r.stdout)
            self.assertIn("NEXT: choose", r.stdout)

    def test_parallel_group(self):
        tasks = [{"id": "T-01", "files": ["a"]}, {"id": "T-02", "files": ["a", "b"]}, {"id": "T-03", "files": ["c"]},
                 {"id": "T-04", "files": ["d"]}, {"id": "T-05", "files": ["e"]}]
        self.assertEqual([t["id"] for t in state.parallel_group(tasks)], ["T-01", "T-03", "T-04"])


if __name__ == "__main__":
    unittest.main()
