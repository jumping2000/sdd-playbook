"""Fixtures and helpers shared by the tests. Standard library only."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "sdd-init" / "scripts"
HOOKS = ROOT / "hooks"


def load(name: str):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(root: Path, rel: str, text: str = "x") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def run(args: list[str], cwd: Path, stdin: str | None = None, env: dict | None = None):
    return subprocess.run(args, cwd=cwd, input=stdin, capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, **(env or {})})


def git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                       cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, f"git {' '.join(args)}: {r.stderr}"
    return r.stdout.strip()


def git_repo(root: Path, branch: str = "main") -> None:
    git(root, "init", "-q")
    git(root, "symbolic-ref", "HEAD", f"refs/heads/{branch}")


def copy_scripts(dest: Path, names: list[str] | None = None) -> None:
    (dest / "scripts").mkdir(parents=True, exist_ok=True)
    for f in SCRIPTS.glob("*.py"):
        if names is None or f.stem in names:
            (dest / "scripts" / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")


class TmpDir:
    def __enter__(self) -> Path:
        self._t = tempfile.TemporaryDirectory()
        return Path(self._t.name)

    def __exit__(self, *a):
        self._t.cleanup()


SPEC_OK = """# SPEC-001: Example

- Status: approved
- Owner: Anna
- Approved by / date: Anna Smith, 2026-10-19

## Problem and goal
Export the report as CSV.

## Scope
- Included: CSV export
- **Non-scope (explicit):** no change to the PDF format
- **Anti-goals:** a CSV that spreadsheets open with broken columns

## Requirements
- REQ-001 (functional): the report can be exported as CSV

## Acceptance criteria
- AC-001 [REQ-001]: Given a report, when I export it, then I get a valid CSV
- AC-002 [REQ-001, error]: Given an empty report, when I export it, then I get a clear error

## Open questions
- none
"""
DIAGRAMS_OK = """
## Diagrams

### Flowchart
```mermaid
flowchart TD
    A[export] --> B{rows?}
```

### Sequence diagram
- n/a: one function, no collaborators

### State diagram
- n/a: no lifecycle

### Class diagram
- n/a: no new types

### ER diagram
- n/a: no persistent data
"""
PLAN_OK = """# PLAN for SPEC-001

- Approved by / date: Anna Smith, 2026-10-19

## Components and files to create/modify
- src/export.py: new export function
- `tests/`: new tests

## Test strategy (mapped to ACs)
| AC-001 | unit |
| AC-002 | unit |

## Review focus
- none
""" + DIAGRAMS_OK
_spec_lint = load("spec_lint")
APPROVED_SPEC = "- Approved by / date: Anna Smith, 2026-10-19\n"
SPEC_OK = SPEC_OK.replace(APPROVED_SPEC, APPROVED_SPEC + f"- Hash: {_spec_lint.fingerprint(SPEC_OK)}\n")
PLAN_OK = PLAN_OK.replace(APPROVED_SPEC, APPROVED_SPEC + f"- Based on spec: {_spec_lint.fingerprint(SPEC_OK)}\n"
                          f"- Hash: {_spec_lint.fingerprint(PLAN_OK)}\n")
TASKS_OK = """- [ ] T-01 Test — verify: `pytest -k AC_001` (expected: red) — covers: AC-001, AC-002 — tests approved: Anna Smith, 2026-10-19, abc1234
- [ ] T-02 Implement — verify: `pytest` — covers: AC-001, AC-002
- [ ] T-DOC Documentation
- [ ] T-SYNC Reconciliation
"""
REVIEW_OK = """# Review of SPEC-001

- Outcome: compliant
- Date: 2026-10-19
- Diff base: main

## Human decision
- Decided by: Anna Smith, 2026-10-19
"""
AREA_OK = """# Area: export

- Last aligned: 2026-10-19
- Linked specs: SPEC-001

## Current behaviour
Exports to CSV.

## Constraints and delicate points
- none

## Characterization tests
- tests/test_char.py: current CSV format
""" + DIAGRAMS_OK
BUG_OK = """# BUG-001: Broken export

- Status: verified
- Severity / impact: medium
- Affected spec or area: SPEC-001

## Reproduction
Export a report with a comma in the name.

## Actual vs expected behaviour
- Actual: the CSV is malformed
- Expected: the field is enclosed in quotes

## Behaviour that must NOT change
- The separator stays the comma

## Root cause
Escaping is missing in the writer.

## Fix and tests
- Red test reproducing the bug: `tests/test_export.py::test_comma`
- Minimal fix: use csv.writer in src/export.py
- Non-regression test on the unchanged behaviour: `tests/test_export.py::test_separator`

## Closure
- [x] verify green
- [x] spec updated
- [x] lesson recorded
"""
