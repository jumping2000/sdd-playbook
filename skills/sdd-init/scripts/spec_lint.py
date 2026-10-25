#!/usr/bin/env python3
# sdd-playbook: 0.14.0
"""Deterministic checks on the playbook's spec, plan and tasks.

Usage:
  python scripts/spec_lint.py docs/specs/001-x/spec.md
  python scripts/spec_lint.py docs/specs/001-x/spec.md --plan docs/specs/001-x/plan.md
  python scripts/spec_lint.py docs/specs/001-x/spec.md --tasks docs/specs/001-x/tasks.md
  python scripts/spec_lint.py docs/specs/001-x/spec.md --plan docs/specs/001-x/plan.md --base main
  python scripts/spec_lint.py docs/specs/001-x/spec.md --hash      # prints the hash to write in "- Hash:"

Approval (playbook §1.2):
  - anti-drift hash: an approved/implemented spec and an approved plan carry "- Hash: sha256:..." of their own body
    (from the first "## " section on); if the body changes, the approval lapses. The plan also carries
    "- Based on spec: sha256:..." and lapses if the spec changes.
  - --base <ref>: spec (and plan) must exist on <ref> and be identical: merging the design PR into a protected branch
    is the approval, and the agent cannot do it by itself.
  - with --plan and --tasks together: tasks.md carries "- Based on plan: sha256:..." and lapses if the plan changes.
IDs and states (playbook §3.3): title "# SPEC-yyyy-mm-dd-slug: ..." with the ID equal to the folder name (the old
"# SPEC-NNN: ..." is still valid). State in-revision: an approved spec being changed, with an entry in "## Revisions";
it goes back to approved only with a new approval and a new hash.
Spec content: requirements with ACs, a filled-in non-scope (error) and anti-goals (warning if missing).
Plan content: every AC in the test strategy; a "## Review focus" section listing the input classes or failure modes the
spec implies but no AC exercises, each with the test that pins it, or "- none" (placeholders: warning before approval,
error once the plan is approved).
Tasks: T-nn from the plan (verify: and covers: mandatory), T-Rnn from review problems (covers: optional).
Level (playbook §2.1): "- Level: S | M | L" in the spec header; without the field it counts as M (warning). The level
is part of the hash: lowering it after approval voids the approval. Level S: no plan, T-DOC optional.
Approved tests (playbook §6): at levels M and L a closed "expected: red" test task carries "tests approved: <name,
yyyy-mm-dd, sha>", written after the human has read the locked tests; sha is the approved Test-Lock commit (diff_scope
reports any later Test-Lock commit for the same task). tests_to_approve() lists the tasks without it.
Exit code 0 = no errors (warnings do not block). Standard library + git (for --base) only, cross-platform.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

STATES = ("draft", "approved", "in-revision", "implemented", "superseded")
LEVELS = ("S", "M", "L")
SECTIONS = ("Problem and goal", "Scope", "Requirements", "Acceptance criteria", "Open questions")
# Spec ID: date + slug (2026-10-24-export-csv, equal to the folder name) or the old number (001).
ID_DATE = r"\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*"
TITLE = re.compile(rf"^#\s+SPEC-({ID_DATE}|\d+)\s*:", re.M)
REQ_DEF = re.compile(r"^\s*[-*]\s+(REQ-\d+)\b")
AC_DEF = re.compile(r"^\s*[-*]\s+(AC-\d+)\s*\[([^\]]*)\]")
PLACEHOLDER = re.compile(r"<[^<>\n]{1,80}>")
NONE_ITEM = re.compile(r"^[-*]\s*(none|n/a)\b", re.I)
TEST_TASK = re.compile(r"^\s*-\s+\[[xX]\]\s+(T-\d+)\b(.*expected:\s*red.*)$", re.M | re.I)
# "tests approved: Anna Smith, 2026-10-24, abc1234": name, date and SHA (7-40 hex digits) of the Test-Lock commit
APPROVED = re.compile(r"tests approved:\s*([^,—\n<>]*\w[^,—\n<>]*),\s*(\d{4}-\d{2}-\d{2}),\s*([0-9a-f]{7,40})\b", re.I)


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def sections(text: str) -> dict[str, list[str]]:
    """Map '## ...' heading -> lines of the section."""
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


def field(text: str, name: str) -> str | None:
    m = re.search(rf"^\s*[-*]\s+{re.escape(name)}\s*:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else None


def clean(value: str | None) -> str:
    """Field value without HTML comments."""
    return re.sub(r"<!--.*?-->", "", value or "").strip()


def spec_id(text: str) -> str | None:
    """ID from the title "# SPEC-<id>: ...": date + slug or number."""
    m = TITLE.search(text)
    return m.group(1) if m else None


def id_key(value: str) -> str:
    """Comparable form of an ID: numbers without leading zeros, slug in lower case with "-"."""
    v = value.replace("_", "-").lower()
    return str(int(v)) if v.isdigit() else v


def id_problems(text: str, folder: str | None) -> list[str]:
    sid = spec_id(text)
    if sid is None:
        return ["Title without ID: expected '# SPEC-yyyy-mm-dd-slug: title' (or the old '# SPEC-NNN: title')"]
    if not sid.isdigit():
        try:
            date.fromisoformat(sid[:10])
        except ValueError:
            return [f"ID {sid}: the leading date is not valid (expected yyyy-mm-dd)"]
        if folder is not None and folder != sid:
            return [f"Title ID ({sid}) differs from the folder name ({folder}): they must match"]
    elif folder is not None and (m := re.match(r"^(\d+)-", folder)) and int(m.group(1)) != int(sid):
        return [f"Title ID (SPEC-{sid}) differs from the folder number ({folder})"]
    return []


def header(text: str) -> str:
    """Text before the first "## " section: state, level, approvals."""
    m = re.search(r"^## ", text, re.M)
    return text[:m.start()] if m else text


def declared_level(text: str) -> str | None:
    """Value of "- Level:" in the header (S, M, L, or the text found if invalid); None if missing."""
    v = clean(field(header(text), "Level"))
    if not v or PLACEHOLDER.search(v):
        return None
    return v.split()[0].upper()


def level(text: str) -> str:
    """Level of the spec: without the field it counts as M."""
    v = declared_level(text)
    return v if v in LEVELS else "M"


def fingerprint(text: str) -> str:
    """Hash of the body (from the first "## " section): state, approver and hash do not count, the level does.

    The level counts only when declared, so specs written without it keep their hash.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
    body = "\n".join(line.rstrip() for line in lines[start:]).strip("\n")
    if (lvl := declared_level(text)) is not None:
        body = f"Level: {lvl}\n{body}"
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def hash_problems(text: str, what: str) -> list[str]:
    recorded = clean(field(text, "Hash"))
    if not recorded or PLACEHOLDER.search(recorded):
        return [f"{what}: approval without '- Hash:' (compute it with: python scripts/spec_lint.py <file> --hash)"]
    if recorded != fingerprint(text):
        return [f"{what}: content changed after approval (Hash does not match): back to draft and get it re-approved"]
    return []


def plan_approval_problems(spec: str, plan: str) -> list[str]:
    """Problems with the approval of a plan already marked as approved."""
    err = hash_problems(plan, "Plan")
    base = clean(field(plan, "Based on spec"))
    if not base or PLACEHOLDER.search(base):
        err.append("Approved plan without '- Based on spec: sha256:...'")
    elif base != fingerprint(spec):
        err.append("Plan based on another version of the spec ('Based on spec' differs): re-approve the plan")
    return err


def plan_signed(plan: str) -> bool:
    approved = clean(field(plan, "Approved by / date"))
    return bool(approved) and not PLACEHOLDER.search(approved)


def on_base(path: str, ref: str) -> list[str]:
    """The file must exist on <ref> and be identical to the working copy (line endings aside)."""
    p = Path(path)
    try:
        r = subprocess.run(["git", "-C", str(p.parent), "show", f"{ref}:./{p.name}"], capture_output=True)
    except OSError:
        return ["git not available: cannot check --base"]
    if r.returncode != 0:
        return [f"{p.as_posix()} is not on {ref}: approval goes through merging the design PR"]
    on_ref = r.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()
    if on_ref != p.read_text(encoding="utf-8").replace("\r\n", "\n").strip():
        return [f"{p.as_posix()} differs from the version on {ref}: the changes must be re-approved with a PR"]
    return []


def parse_spec(text: str):
    reqs = [m.group(1) for line in text.splitlines() if (m := REQ_DEF.match(line))]
    acs: dict[str, list[str]] = {}
    for line in text.splitlines():
        if (m := AC_DEF.match(line)):
            acs[m.group(1)] = re.findall(r"REQ-\d+", m.group(2))
    return reqs, acs


def filled_items(lines: list[str]) -> list[str]:
    """List items with real content (not placeholders, not "none")."""
    return [line.strip() for line in lines if line.strip().startswith(("-", "*")) and not PLACEHOLDER.search(line)
            and not NONE_ITEM.match(line.strip())]


def lint_spec(text: str, folder: str | None = None) -> tuple[list[str], list[str]]:
    """folder: name of the spec folder, which for date IDs must match the ID."""
    err: list[str] = []
    warn: list[str] = []
    state = clean(field(text, "Status")).split("|")[0].strip()
    if state not in STATES:
        err.append(f"Status missing or invalid (expected one of: {', '.join(STATES)}); found '{state}'")
    err += id_problems(text, folder)
    lvl = declared_level(text)
    if lvl is None:
        warn.append("Level not set ('- Level: S | M | L', playbook §2.1): counts as M")
    elif lvl not in LEVELS:
        err.append(f"Invalid level '{lvl}' (expected S, M or L)")
    sec = sections(text)
    if state == "in-revision" and not filled_items(sec.get("Revisions", [])):
        err.append("Spec in revision without an entry in '## Revisions' (date, what changes and why)")
    for s in SECTIONS:
        if s not in sec:
            err.append(f"Missing section: '## {s}'")

    reqs, acs = parse_spec(text)
    if len(reqs) != len(set(reqs)):
        err.append("Duplicate REQ IDs")
    if not reqs:
        err.append("No requirement (REQ-nnn) found")
    for req in reqs:
        if not any(req in refs for refs in acs.values()):
            err.append(f"{req} has no acceptance criterion")
    ac_lines = [m.group(1) for line in text.splitlines() if (m := AC_DEF.match(line))]
    if len(ac_lines) != len(set(ac_lines)):
        err.append("Duplicate AC IDs")
    for ac, refs in acs.items():
        if not refs:
            err.append(f"{ac} cites no REQ")
        for ref in refs:
            if ref not in reqs:
                err.append(f"{ac} cites {ref}, which does not exist")

    scope = "\n".join(sec.get("Scope", []))
    m = re.search(r"Non-scope[^:\n]*:\**[ \t]*(.*)", scope, re.I)
    nonscope = m.group(1).strip() if m else ""
    if not m or not nonscope or PLACEHOLDER.fullmatch(nonscope):
        err.append("Non-scope missing or not filled in")
    m = re.search(r"Anti-goals[^:\n]*:\**[ \t]*(.*)", scope, re.I)
    if not m or not m.group(1).strip() or PLACEHOLDER.fullmatch(m.group(1).strip()):
        warn.append("Anti-goals missing or not filled in (what would make the feature a failure even if it works)")

    if state in ("approved", "implemented"):
        approved = clean(field(text, "Approved by / date"))
        if not approved or PLACEHOLDER.search(approved):
            err.append("Spec approved but 'Approved by / date' not filled in")
        err += hash_problems(text, "Spec")
        still_open = [line.strip() for line in sec.get("Open questions", [])
                      if line.strip().startswith(("-", "*")) and not NONE_ITEM.match(line.strip())]
        # here a placeholder also counts as an open question
        if still_open:
            err.append(f"Spec approved with {len(still_open)} open questions")
        if "[ASSUMPTION]" in text:
            warn.append("Assumptions marked [ASSUMPTION] remain: validate or rephrase them")
    return err, warn


def review_focus_problems(plan: str) -> list[str]:
    """Problems of the "## Review focus" section: filled-in table rows or "- none", without placeholders."""
    lines = next((lines for title, lines in sections(plan).items() if title.lower().startswith("review focus")), None)
    if lines is None:
        return ["Section '## Review focus' missing from the plan (uncovered input classes with their test, or '- none')"]
    rows = [line for line in lines if line.strip().startswith("|") and not re.fullmatch(r"[|\s:-]+", line.strip())]
    pending = [row for row in rows[1:] if PLACEHOLDER.search(row)]
    none = any(NONE_ITEM.match(line.strip()) for line in lines)
    if pending or (len(rows) < 2 and not none):
        return ["Review focus not filled in: list the uncovered input classes with their test, or write '- none'"]
    return []


def lint_plan(spec: str, plan: str) -> tuple[list[str], list[str]]:
    _, acs = parse_spec(spec)
    strategy = next((lines for title, lines in sections(plan).items() if title.startswith("Test strategy")), None)
    if strategy is None:
        err = ["Section '## Test strategy' missing from the plan"]
    else:
        in_plan = set(re.findall(r"\bAC-\d+\b", "\n".join(strategy)))
        err = [f"{ac} does not appear in the plan (test strategy)" for ac in acs if ac not in in_plan]
    warn = []
    focus = review_focus_problems(plan)
    if plan_signed(plan):
        err += plan_approval_problems(spec, plan)
        err += focus
    else:
        warn.append("Plan not approved yet ('Approved by / date' empty)")
        missing = [f for f in focus if "missing" in f]
        err += missing
        warn += [f for f in focus if f not in missing]
    return err, warn


def lint_tasks(spec: str, tasks: str) -> tuple[list[str], list[str]]:
    _, acs = parse_spec(spec)
    err: list[str] = []
    lines = [line for line in tasks.splitlines() if re.match(r"^\s*-\s+\[[ xX]\]\s+T-", line)]
    if not lines:
        return ["No task (- [ ] T-...) found"], []
    covered: set[str] = set()
    ids: list[str] = []
    for line in lines:
        tid = re.search(r"\bT-[A-Z0-9]+\b", line).group(0)
        ids.append(tid)
        covered.update(re.findall(r"AC-\d+", line.split("covers:")[-1] if "covers:" in line else ""))
        if re.fullmatch(r"T-R?\d+", tid):  # T-nn from the plan, T-Rnn from review problems
            if (m := PLACEHOLDER.search(line)):
                err.append(f"{tid}: placeholder not filled in {m.group(0)}")
            if not re.search(r"verify:\s*`[^`]+`", line):
                err.append(f"{tid}: missing 'verify: `<command>`'")
            if tid.startswith("T-R"):
                continue  # a fix may not touch an AC: covers: is optional
            if "covers:" not in line or not re.search(r"AC-\d+", line.split("covers:")[-1]):
                err.append(f"{tid}: missing 'covers: AC-nnn'")
    if len(ids) != len(set(ids)):
        err.append("Duplicate task IDs")
    for tag in ("T-DOC", "T-SYNC") if level(spec) != "S" else ("T-SYNC",):  # S: T-DOC optional
        if tag not in ids:
            err.append(f"Task {tag} missing")
    for ac in acs:
        if ac not in covered:
            err.append(f"{ac} is not covered by any task")
    return err, []


def test_approvals(tasks: str) -> dict[str, str | None]:
    """Closed "expected: red" test tasks -> SHA of the approved Test-Lock commit (None if not approved)."""
    out: dict[str, str | None] = {}
    for tid, rest in TEST_TASK.findall(tasks):
        m = APPROVED.search(rest)
        out[tid] = m.group(3).lower() if m else None
    return out


def tests_to_approve(tasks: str) -> list[str]:
    """Closed "expected: red" test tasks without a valid "tests approved: <name, yyyy-mm-dd, sha>"."""
    return [tid for tid, sha in test_approvals(tasks).items() if sha is None]


def tasks_on_plan(plan: str, tasks: str) -> tuple[list[str], list[str]]:
    """Tasks record the hash of the plan they derive from: if the plan changes they must be reviewed."""
    base = clean(field(tasks, "Based on plan"))
    if not base or PLACEHOLDER.search(base):
        return [], ["Tasks without '- Based on plan: sha256:...': they will not notice if the plan changes"]
    if base != fingerprint(plan):
        return ["Tasks based on another version of the plan ('Based on plan' differs): review them and update it"], []
    return [], []


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("--"):
        print(__doc__)
        return 2
    spec_path, opts = argv[0], argv[1:]
    spec = read(spec_path)
    if "--hash" in opts:
        print(fingerprint(spec))
        return 0
    err, warn = lint_spec(spec, Path(spec_path).resolve().parent.name)
    to_compare = [spec_path]
    plan = tasks = None
    for i, o in enumerate(opts):
        if o == "--plan" and i + 1 < len(opts):
            plan = read(opts[i + 1])
            e, w = lint_plan(spec, plan)
            err += e
            warn += w
            to_compare.append(opts[i + 1])
        if o == "--tasks" and i + 1 < len(opts):
            tasks = read(opts[i + 1])
            e, w = lint_tasks(spec, tasks)
            err += e
            warn += w
    if plan is not None and tasks is not None:
        e, w = tasks_on_plan(plan, tasks)
        err += e
        warn += w
    if "--base" in opts and opts.index("--base") + 1 < len(opts):
        ref = opts[opts.index("--base") + 1]
        for f in to_compare:
            err += on_base(f, ref)
    for w in warn:
        print(f"[WARN] {w}")
    for e in err:
        print(f"[ERROR] {e}")
    print("LINT: " + ("OK" if not err else f"{len(err)} errors"))
    return 1 if err else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # UTF-8 even with a cp1252 console (Windows)
        stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
