#!/usr/bin/env python3
# sdd-playbook: 0.16.0
"""Closing check of a feature: spec, tasks, review, area page and traceability aligned.

Usage:
  python scripts/sync_check.py docs/specs/001-x [--area docs/system/<area>.md] [--tests DIR ...] [--junit FILE ...]

Checks:
  1. spec valid and with Status = implemented
  2. no open task in tasks.md; at level L (or M with "- Task review: on" in progress.md) every closed T-nn task has
     "- T-nn: pass" in "## Task reviews" of progress.md
  3. review.md present with a valid Outcome other than "non-compliant", and the human decision filled in
  4. area page (--area, or the first one in docs/system/ that cites the spec) with the required sections,
     "Last aligned" filled in and the spec among the "Linked specs"
  5. every AC cited in at least one test of this spec (trace_check: qualified IDs SPEC-nnn/AC-nnn)
Levels (playbook §2.1): S requires neither review.md (the review is the PR review) nor the area page; L also requires
"- Human diff review:" filled in in review.md. At levels M and L closed test tasks carry "tests approved:". With
--junit FILE|DIR the ACs must be verified by the report of executed tests (see trace_check); at level L the report is
mandatory. The spec folder may also follow the options.
Exit code: 0 aligned; 1 errors; 2 wrong usage. Standard library only, cross-platform.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the project: it would count as a changed file
sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_lint  # noqa: E402
import trace_check  # noqa: E402

PLACEHOLDER = re.compile(r"<[^<>\n]{1,100}>")
OUTCOMES = ("compliant", "compliant with reservations", "non-compliant")
AREA_SECTIONS = ("Current behaviour", "Constraints and delicate points", "Characterization tests")


def field(text: str, name: str) -> str:
    m = re.search(rf"^\s*[-*]\s+{re.escape(name)}\s*:\s*(.*)$", text, re.M)
    return re.sub(r"<!--.*?-->", "", m.group(1)).strip() if m else ""


def spec_label(spec: str, feature: Path) -> str:
    sid = spec_lint.spec_id(spec)
    return f"SPEC-{sid}" if sid else feature.name


def cites(text: str, spec_id: str) -> bool:
    """The text cites exactly this spec (SPEC-2026-10-24-x does not match SPEC-2026-10-24-x-y)."""
    key = spec_lint.id_key(spec_id[5:] if spec_id.startswith("SPEC-") else spec_id)
    return key in {spec_lint.id_key(n) for n in trace_check.SPEC_REF.findall(text)}


def find_area(spec_id: str, explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit) if Path(explicit).is_file() else None
    for p in sorted(Path("docs/system").glob("*.md")) if Path("docs/system").is_dir() else []:
        if p.name != "map.md" and cites(p.read_text(encoding="utf-8"), spec_id):
            return p
    return None


def check(feature: Path, area_arg: str | None, tests: list[Path], junit: list[str] | None = None) -> list[str]:
    err: list[str] = []
    spec_p = feature / "spec.md"
    if not spec_p.is_file():
        return [f"{spec_p.as_posix()} not found"]
    spec = spec_p.read_text(encoding="utf-8")
    spec_id = spec_label(spec, feature)
    level = spec_lint.level(spec)

    e, _ = spec_lint.lint_spec(spec, feature.resolve().name)
    err += [f"spec: {x}" for x in e]
    state = spec_lint.clean(spec_lint.field(spec, "Status")).split("|")[0].strip()
    if state != "implemented":
        err.append(f"spec: Status is '{state}', expected 'implemented'")

    tasks_p = feature / "tasks.md"
    if tasks_p.is_file():
        tasks = tasks_p.read_text(encoding="utf-8")
        still_open = re.findall(r"^\s*-\s+\[ \]\s+(T-[A-Z0-9]+)", tasks, re.M)
        if still_open:
            err.append("tasks still open: " + ", ".join(still_open))
        unapproved = spec_lint.tests_to_approve(tasks) if level != "S" else []
        if unapproved:
            err.append(f"locked tests without human approval ('tests approved:'): {', '.join(unapproved)}")
        progress_p = feature / "progress.md"
        progress = progress_p.read_text(encoding="utf-8") if progress_p.is_file() else ""
        unreviewed = spec_lint.task_reviews_missing(spec, tasks, progress)
        if unreviewed:
            err.append("task reviews missing or not passed (progress.md, '## Task reviews'): " + ", ".join(unreviewed))
    else:
        err.append("tasks.md not found")

    rev_p = feature / "review.md"
    if not rev_p.is_file():
        if level != "S":
            err.append("review.md missing (run sdd-review-diff)")
    else:
        review = rev_p.read_text(encoding="utf-8")
        outcome = field(review, "Outcome")
        if outcome not in OUTCOMES:
            err.append(f"review.md: invalid Outcome '{outcome}' (expected: {', '.join(OUTCOMES)})")
        elif outcome == "non-compliant":
            err.append("review.md: Outcome 'non-compliant'")
        decision = field(review, "Decided by")
        if not decision or PLACEHOLDER.search(decision):
            err.append("review.md: 'Decided by' not filled in (the review decision belongs to the human)")
        human = field(review, "Human diff review")
        if level == "L" and (not human or PLACEHOLDER.search(human)):
            err.append("review.md: level L without 'Human diff review' (who read the diff, and when)")

    area = find_area(spec_id, area_arg)
    if area is None and level == "S":
        pass  # level S: the area page is optional
    elif area is None:
        err.append(f"no area page in docs/system/ citing {spec_id} (use --area)")
    else:
        t = area.read_text(encoding="utf-8")
        for s in AREA_SECTIONS:
            if not re.search(rf"^##\s+{re.escape(s)}\s*$", t, re.M):
                err.append(f"{area.as_posix()}: missing section '## {s}'")
        aligned = field(t, "Last aligned")
        if not aligned or PLACEHOLDER.search(aligned):
            err.append(f"{area.as_posix()}: 'Last aligned' not filled in")
        if not cites(field(t, "Linked specs"), spec_id):
            err.append(f"{area.as_posix()}: {spec_id} is not among the 'Linked specs'")

    folders = [d for d in (tests or [Path(c) for c in trace_check.FOLDERS]) if d.is_dir()]
    if not folders:
        err.append("no test folder found (use --tests)")
    else:
        result = trace_check.analyze(spec, folders)
        if result.missing:
            note = (f" ({len(result.ambiguous)} ambiguous citations: use {spec_id}/AC-nnn or declare the spec in the "
                    "file)" if result.ambiguous else "")
            err.append("ACs without tests: " + ", ".join(result.missing) + note)
        if junit:
            try:
                executed = trace_check.executions(spec, folders, trace_check.report_files(junit))
            except ValueError as e:
                return err + [str(e)]
            ko = [ac for ac, x in executed.items() if x["failed"] or not x["passed"]]
            if ko:
                err.append("ACs not verified by the report of executed tests (failed or not run): " + ", ".join(ko))
    if level == "L" and not junit:
        err.append("level L: the report of executed tests is required (--junit)")
    return err


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    area = argv[argv.index("--area") + 1] if "--area" in argv else None
    tests = [Path(t) for t in trace_check.values(argv, "--tests")]
    junit = trace_check.values(argv, "--junit")
    # the spec folder may also follow --tests or --junit: it is the one containing spec.md
    spec_dirs = [a for a in args if a != area and (Path(a) / "spec.md").is_file()]
    rest = [a for a in args if a != area and a not in junit and Path(a) not in tests]
    if not spec_dirs and not rest:
        print(__doc__)
        return 2
    feature = Path(spec_dirs[0] if spec_dirs else rest[0])
    tests = [x for x in tests if x != feature]
    junit = [x for x in junit if Path(x) != feature]
    err = check(feature, area, tests, junit)
    for e in err:
        print(f"[ERROR] {e}")
    print("SYNC: " + ("OK" if not err else f"{len(err)} errors"))
    return 1 if err else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # UTF-8 even with a cp1252 console (Windows)
        stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
