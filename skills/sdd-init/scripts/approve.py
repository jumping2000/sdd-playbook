#!/usr/bin/env python3
# sdd-playbook: 0.20.0
"""Record an approval the user selected: fields, date and hashes written in one step, then checked.

Usage:
  python scripts/approve.py spec   docs/specs/<id>/spec.md  --by "<name>" [--commit]
  python scripts/approve.py plan   docs/specs/<id>/plan.md  --by "<name>" [--commit]
  python scripts/approve.py tasks  docs/specs/<id>/tasks.md [--commit]
  python scripts/approve.py tests  docs/specs/<id> T-01     --by "<name>" [--base main] [--commit]
  python scripts/approve.py review docs/specs/<id>          --by "<name>" [--diff-read] [--commit]

spec:   "- Status: approved", "- Approved by / date: <name>, <today>", "- Hash:" of the body.
plan:   "- Approved by / date:", "- Based on spec:" (hash of the approved spec next to it), "- Hash:" of the body.
tasks:  "- Based on plan:" (hash of the approved plan next to it); no name: the tasks are checked, not approved.
tests:  appends "— tests approved: <name>, <today>, <sha>" to the closed "expected: red" task, with the SHA of its
        last Test-Lock commit in the branch (merge-base with --base, default main, master, origin/main, origin/master).
review: "- Decided by: <name>, <today>" in review.md; with --diff-read also "- Human diff review:" (level L).
The new text must pass spec_lint (spec, plan, tasks) or the review rules: otherwise nothing is written (exit 1).
--commit adds and commits only that file: "<spec id>: approve <what> (<name>)" with the trailers "Spec:" and
"Approved-by:". Run it only in the turn where the user selected the approval, with the name they selected
(playbook §1.2): the autonomous loop never approves.
Exit code: 0 recorded; 1 refused (lint errors, task or Test-Lock commit not found); 2 wrong usage. Standard library +
git only, cross-platform.
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the project: it would count as a changed file
sys.path.insert(0, str(Path(__file__).resolve().parent))
import diff_scope  # noqa: E402
import spec_lint  # noqa: E402

KINDS = ("spec", "plan", "tasks", "tests", "review")
OUTCOMES = ("compliant", "compliant with reservations", "non-compliant")


def set_field(text: str, name: str, value: str, after: str | None = None) -> str:
    """Replace the value of "- <name>:"; if missing, insert it after the "- <after>:" line (or after the title)."""
    pattern = re.compile(rf"^(\s*[-*]\s+{re.escape(name)}\s*:).*$", re.M)
    if pattern.search(text):
        return pattern.sub(lambda m: f"{m.group(1)} {value}", text, count=1)
    lines = text.splitlines(keepends=True)
    anchor = next((i for i, line in enumerate(lines) if after and re.match(rf"^\s*[-*]\s+{re.escape(after)}\s*:", line)),
                  0 if lines and lines[0].startswith("#") else -1)
    lines.insert(anchor + 1, f"- {name}: {value}\n")
    return "".join(lines)


def spec_id(spec_text: str, folder: Path) -> str:
    return f"SPEC-{spec_lint.spec_id(spec_text) or folder.name}"


def approve_spec(path: Path, who: str) -> tuple[str, list[str]]:
    text = path.read_text(encoding="utf-8")
    new = set_field(text, "Status", "approved")
    new = set_field(new, "Approved by / date", who)
    new = set_field(new, "Hash", spec_lint.fingerprint(new), after="Approved by / date")
    err, _ = spec_lint.lint_spec(new, path.parent.name)
    return new, err


def approve_plan(path: Path, who: str) -> tuple[str, list[str]]:
    spec = (path.parent / "spec.md").read_text(encoding="utf-8")
    spec_err, _ = spec_lint.lint_spec(spec, path.parent.name)
    if spec_err or spec_lint.clean(spec_lint.field(spec, "Status")) not in ("approved", "implemented"):
        return "", ["approve the spec first (spec_lint must pass on an approved spec)"] + spec_err
    new = set_field(path.read_text(encoding="utf-8"), "Approved by / date", who)
    new = set_field(new, "Based on spec", spec_lint.fingerprint(spec), after="Approved by / date")
    new = set_field(new, "Hash", spec_lint.fingerprint(new), after="Based on spec")
    err, _ = spec_lint.lint_plan(spec, new)
    return new, err


def approve_tasks(path: Path) -> tuple[str, list[str]]:
    spec = (path.parent / "spec.md").read_text(encoding="utf-8")
    plan_path = path.parent / "plan.md"
    new = path.read_text(encoding="utf-8")
    if plan_path.is_file():
        plan = plan_path.read_text(encoding="utf-8")
        if not spec_lint.plan_signed(plan):
            return "", ["approve the plan first"]
        new = set_field(new, "Based on plan", spec_lint.fingerprint(plan))
        err = spec_lint.tasks_on_plan(plan, new)[0]
    else:
        err = []
    return new, err + spec_lint.lint_tasks(spec, new)[0]


def approve_tests(feature: Path, task: str, who: str, base_arg: str | None) -> tuple[str, list[str]]:
    path = feature / "tasks.md"
    text = path.read_text(encoding="utf-8")
    line = next((m for m in spec_lint.TEST_TASK.finditer(text) if m.group(1) == task), None)
    if line is None:
        return "", [f"{task}: no closed task with 'expected: red' in {path.as_posix()}"]
    base = diff_scope.base_ref(base_arg)
    if base is None:
        return "", ["not a git repository or no base ref found: use --base <ref>"]
    try:
        commits = diff_scope.branch_commits(diff_scope.merge_base(base))
    except RuntimeError as e:
        return "", [str(e)]
    shas = [sha for sha, lock, _ in commits if lock == task]
    if not shas:
        return "", [f"{task}: no commit with the trailer 'Test-Lock: {task}' in the branch (base: {base})"]
    approval = f"tests approved: {who}, {shas[-1][:7]}"  # who = "<name>, <yyyy-mm-dd>"
    whole = line.group(0)
    if spec_lint.APPROVED.search(whole):
        updated = spec_lint.APPROVED.sub(approval, whole, count=1)
    else:
        updated = whole.rstrip() + f" — {approval}"
    return text.replace(whole, updated, 1), []


def approve_review(feature: Path, who: str, diff_read: bool) -> tuple[str, list[str]]:
    path = feature / "review.md"
    if not path.is_file():
        return "", [f"{path.as_posix()} missing"]
    text = path.read_text(encoding="utf-8")
    outcome = spec_lint.clean(spec_lint.field(text, "Outcome"))
    if outcome not in OUTCOMES:
        return "", [f"review.md: Outcome missing or invalid ('{outcome}')"]
    new = set_field(text, "Decided by", who)
    if diff_read:
        new = set_field(new, "Human diff review", who, after="Decided by")
    return new, []


def commit(path: Path, message: str, trailers: list[str]) -> int:
    subprocess.run(["git", "add", "--", str(path)], check=False)
    args = ["git", "commit", "-q", "-m", message, *[x for t in trailers for x in ("-m", t)], "--", str(path)]
    return subprocess.run(args).returncode


def main(argv: list[str]) -> int:
    who_name = argv[argv.index("--by") + 1] if "--by" in argv and argv.index("--by") + 1 < len(argv) else None
    base_arg = argv[argv.index("--base") + 1] if "--base" in argv and argv.index("--base") + 1 < len(argv) else None
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i > 0 and argv[i - 1] in ("--by", "--base"))]
    if not pos or pos[0] not in KINDS or len(pos) < 2:
        print(__doc__)
        return 2
    kind, target = pos[0], Path(pos[1])
    if kind != "tasks" and (not who_name or not who_name.strip() or spec_lint.PLACEHOLDER.search(who_name)):
        print("[ERROR] --by \"<name>\" is required: the name the user selected")
        return 2
    who = f"{who_name.strip()}, {date.today().isoformat()}" if who_name else ""
    feature = target if target.is_dir() else target.parent
    if not (feature / "spec.md").is_file() or (kind in ("spec", "plan", "tasks") and not target.is_file()):
        print(f"[ERROR] file or spec folder not found: {target.as_posix()}")
        return 2
    if kind == "spec":
        path, (new, err) = target, approve_spec(target, who)
    elif kind == "plan":
        path, (new, err) = target, approve_plan(target, who)
    elif kind == "tasks":
        path, (new, err) = target, approve_tasks(target)
    elif kind == "tests":
        if len(pos) < 3 or not re.fullmatch(r"T-\d+", pos[2]):
            print("[ERROR] tests: give the task ID (T-nn)")
            return 2
        path, (new, err) = feature / "tasks.md", approve_tests(feature, pos[2], who, base_arg)
    else:
        path, (new, err) = feature / "review.md", approve_review(feature, who, "--diff-read" in argv)
    if err:
        for e in err:
            print(f"[ERROR] {e}")
        print("APPROVAL: NOT RECORDED (nothing written)")
        return 1
    path.write_text(new, encoding="utf-8")
    what = kind if kind != "tests" else f"tests {pos[2]}"
    print(f"APPROVAL: {what} recorded in {path.as_posix()}" + (f" by {who}" if who else ""))
    if "--commit" in argv:
        sid = spec_id((feature / "spec.md").read_text(encoding="utf-8"), feature)
        name = who_name.strip() if who_name else "checked"
        code = commit(path, f"{sid[len('SPEC-'):]}: approve {what} ({name})",
                      [f"Spec: {sid}"] + ([f"Approved-by: {who_name.strip()}"] if who_name else []))
        if code != 0:
            print("[ERROR] git commit failed: the approval is written but not committed")
            return 1
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # UTF-8 even with a cp1252 console (Windows)
        stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
