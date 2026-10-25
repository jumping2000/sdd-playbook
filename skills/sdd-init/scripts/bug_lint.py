#!/usr/bin/env python3
# sdd-playbook: 0.14.0
"""Checks on a bug file (docs/bugs/BUG-nnn-*.md) according to the playbook.

Usage: python scripts/bug_lint.py docs/bugs/BUG-001-example.md

Requirements grow with the status:
  open       reproduction filled in
  diagnosed  + actual/expected, "must NOT change", root cause, red test indicated
  fixed      + minimal fix and non-regression test indicated
  verified   + every "Closure" item ticked
Exit code: 0 no errors; 1 errors; 2 wrong usage. Standard library only, cross-platform.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

STATES = ("open", "diagnosed", "fixed", "verified")
SECTIONS = ("Reproduction", "Actual vs expected behaviour", "Behaviour that must NOT change",
            "Root cause", "Fix and tests", "Closure")
PLACEHOLDER = re.compile(r"<[^<>\n]{1,100}>")


def sections(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*?)\s*$", line)
        if m:
            current = m.group(1)
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return out


def real(lines: list[str]) -> list[str]:
    """Lines with real content: nothing is left once comments, placeholders and labels ("Actual:") are removed."""
    out = []
    for line in lines:
        t = PLACEHOLDER.sub("", re.sub(r"<!--.*?-->", "", line)).strip()
        if ":" in t:
            t = t.split(":", 1)[1]
        if re.sub(r"[\s\-*`.,;]+", "", t):
            out.append(line.strip())
    return out


def line_value(lines: list[str], label: str) -> str:
    for line in lines:
        if label.lower() in line.lower() and ":" in line:
            return line.split(":", 1)[1].strip()
    return ""


def valid_path(value: str) -> bool:
    m = re.search(r"`([^`]+)`", value)
    return bool(m) and not PLACEHOLDER.fullmatch(m.group(1).strip())


def lint(text: str) -> list[str]:
    err: list[str] = []
    m = re.search(r"^\s*[-*]\s+Status\s*:\s*(.*)$", text, re.M)
    state = re.sub(r"<!--.*?-->", "", m.group(1)).strip().split("|")[0].strip() if m else ""
    if state not in STATES:
        return [f"Status missing or invalid (expected: {', '.join(STATES)}); found '{state}'"]
    sec = sections(text)
    for s in SECTIONS:
        if s not in sec:
            err.append(f"Missing section: '## {s}'")
    if err:
        return err
    stage = STATES.index(state)
    if not real(sec["Reproduction"]):
        err.append("Reproduction not filled in")
    if stage >= 1:
        if len(real(sec["Actual vs expected behaviour"])) < 2:
            err.append("Both the actual and the expected behaviour are needed")
        if not real(sec["Behaviour that must NOT change"]):
            err.append("'Behaviour that must NOT change' is empty: it is the non-regression net")
        if not real(sec["Root cause"]):
            err.append("Root cause not filled in")
        if not valid_path(line_value(sec["Fix and tests"], "Red test")):
            err.append("Red test missing (path in backticks in 'Red test ...')")
    if stage >= 2:
        fix = line_value(sec["Fix and tests"], "Minimal fix")
        if not fix or PLACEHOLDER.search(fix):
            err.append("Minimal fix not described")
        if not valid_path(line_value(sec["Fix and tests"], "Non-regression")):
            err.append("Non-regression test missing (path in backticks)")
    if stage >= 3:
        items = [line for line in sec["Closure"] if re.match(r"^\s*-\s+\[[ xX]\]", line)]
        unticked = [line for line in items if re.match(r"^\s*-\s+\[ \]", line)]
        if not items:
            err.append("'Closure' without tickable items")
        if unticked:
            err.append(f"'Closure': {len(unticked)} items not ticked")
    return err


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    err = lint(Path(argv[0]).read_text(encoding="utf-8"))
    for e in err:
        print(f"[ERROR] {e}")
    print("BUG-LINT: " + ("OK" if not err else f"{len(err)} errors"))
    return 1 if err else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # UTF-8 even with a cp1252 console (Windows)
        stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
