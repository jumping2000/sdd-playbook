#!/usr/bin/env python3
# sdd-playbook: 0.17.0
"""Project state according to the playbook and suggested next phase.

Usage: python scripts/state.py [--json] [--spec <id>] [root]
Read-only. The suggestion follows the playbook flow: init -> (map-codebase) -> spec -> plan -> tasks -> implement ->
review-diff -> docs -> sync. Open bugs and sdd-loop are reported separately.
With several active specs each one has its own next step; the NEXT line refers to the spec given with --spec, the one
whose folder name appears in the current branch, or the only active one. Otherwise it asks to choose.
Levels (playbook §2.1): a level-S spec skips plan and review.md; a level-L spec also requires the human reading of the
diff ("- Human diff review:" in review.md). At levels M and L the locked tests of a closed "expected: red" task must be
approved by the human ("tests approved:" on the task line) before moving on. At level L (or M with "- Task review: on"
in progress.md) every closed T-nn task needs a passed task review in progress.md before the final review. When the
next open T-nn task covers an AC named by a non-blocking open question of the spec, the next step is sdd-spec (the
answer enters the spec with a revision).
Standard library only (+ git for the branch name, if present), cross-platform.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the project: it would count as a changed file
sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_lint  # noqa: E402

PLACEHOLDER = re.compile(r"<[^<>\n]{1,100}>")
OUTCOMES = ("compliant", "compliant with reservations", "non-compliant")
SOURCES = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".cs", ".go", ".rb", ".php", ".rs", ".c", ".cpp",
           ".swift"}
IGNORE = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", "bin", "obj",
          "scripts", "docs", ".github", ".vscode"}
CLOSED = ("implemented", "superseded")


def _field(text: str, name: str) -> str:
    m = re.search(rf"^\s*[-*]\s+{re.escape(name)}\s*:\s*(.*)$", text, re.M)
    return re.sub(r"<!--.*?-->", "", m.group(1)).strip() if m else ""


def _filled(text: str, name: str) -> bool:
    v = _field(text, name)
    return bool(v) and not PLACEHOLDER.search(v)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def has_code(root: Path, threshold: int = 3) -> bool:
    n = 0
    for _, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE]
        n += sum(1 for f in files if Path(f).suffix in SOURCES)
        if n >= threshold:
            return True
    return False


def current_branch(root: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(root), "branch", "--show-current"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def analyze_spec(d: Path) -> dict:
    spec, plan, tasks, review, progress = (_read(d / n) for n in ("spec.md", "plan.md", "tasks.md", "review.md",
                                                                  "progress.md"))
    open_tasks = re.findall(r"^\s*-\s+\[ \]\s+(T-[A-Z0-9]+)", tasks, re.M)
    closed_tasks = re.findall(r"^\s*-\s+\[[xX]\]\s+(T-[A-Z0-9]+)", tasks, re.M)
    numbered = [t for t in open_tasks if re.fullmatch(r"T-R?\d+", t)]
    waiting = spec_lint.waiting_acs(spec) if spec else set()
    waiting_tasks = {m.group(1): sorted(set(re.findall(r"AC-\d+", m.group(2))) & waiting)
                     for m in re.finditer(r"^\s*-\s+\[ \]\s+(T-\d+)\b.*?covers:(.*)$", tasks, re.M)}
    spec_signed = _filled(spec, "Approved by / date")
    plan_signed = _filled(plan, "Approved by / date")
    state = (_field(spec, "Status").split("|")[0].strip() if spec else "") or "n/a"
    spec_lapsed = state != "in-revision" and spec_signed and bool(spec_lint.hash_problems(spec, "Spec"))
    plan_lapsed = plan_signed and bool(spec_lint.plan_approval_problems(spec, plan))
    task_base = _field(tasks, "Based on plan")
    sid = spec_lint.spec_id(spec)
    return {
        "id": d.name,
        "title_id": f"SPEC-{sid}" if sid else None,
        "spec": bool(spec),
        "status": state,
        "level": spec_lint.level(spec),
        "spec_approved": spec_signed and not spec_lapsed and state != "in-revision",
        "spec_approval_lapsed": spec_lapsed,
        "plan": bool(plan),
        "plan_approved": plan_signed and not plan_lapsed,
        "plan_approval_lapsed": plan_lapsed,
        "tasks": bool(tasks),
        "tasks_on_other_plan": bool(plan and task_base and not PLACEHOLDER.search(task_base)
                                    and task_base != spec_lint.fingerprint(plan)),
        "tasks_closed": len(closed_tasks),
        "tasks_total": len(closed_tasks) + len(open_tasks),
        "numbered_tasks_open": len(numbered),
        "next_task": numbered[0] if numbered else None,
        "next_task_waits_for": (waiting_tasks.get(numbered[0]) or []) if numbered else [],
        "tests_to_approve": spec_lint.tests_to_approve(tasks),
        "task_reviews_missing": spec_lint.task_reviews_missing(spec, tasks, progress),
        "review_tasks": len([t for t in open_tasks + closed_tasks if t.startswith("T-R")]),
        "doc_open": "T-DOC" in open_tasks,
        "sync_open": "T-SYNC" in open_tasks,
        "review": _field(review, "Outcome") if review else None,
        "review_valid": _field(review, "Outcome") in OUTCOMES if review else False,
        "human_diff_review": _filled(review, "Human diff review"),
    }


def next_for_spec(s: dict) -> dict:
    i = s["id"]
    if s["status"] == "in-revision":
        return {"skill": "sdd-spec", "spec": i,
                "reason": "spec in revision: complete the changes (Revisions section) and get it re-approved"}
    if s["spec_approval_lapsed"]:
        return {"skill": "sdd-spec", "spec": i,
                "reason": "spec approval without a valid Hash (missing or content changed): it must be re-approved"}
    if not s["spec"] or s["status"] == "draft" or not s["spec_approved"]:
        return {"skill": "sdd-spec", "spec": i, "reason": "spec to complete and get approved"}
    if s["level"] == "S":
        return next_level_s(s)
    if s["plan_approval_lapsed"]:
        return {"skill": "sdd-plan", "spec": i,
                "reason": "plan approval not valid (Hash missing or changed, or different spec): it must be re-approved"}
    if not s["plan"] or not s["plan_approved"]:
        return {"skill": "sdd-plan", "spec": i, "reason": "plan missing or to approve"}
    if not s["tasks"]:
        return {"skill": "sdd-tasks", "spec": i, "reason": "tasks missing"}
    if s["tasks_on_other_plan"]:
        return {"skill": "sdd-tasks", "spec": i, "reason": "tasks based on another version of the plan: review them"}
    if s["tests_to_approve"]:
        return {"skill": "sdd-tests-from-ac", "spec": i,
                "reason": f"locked tests of {', '.join(s['tests_to_approve'])} to be approved by the human "
                          "('tests approved:' on the task line) before implementation"}
    if s["next_task_waits_for"]:
        return waiting_task(s)
    if s["numbered_tasks_open"]:
        return {"skill": "sdd-implement", "spec": i,
                "reason": f"open tasks: {s['numbered_tasks_open']}, next {s['next_task']} "
                          "(for many independent tasks consider sdd-loop)"}
    if s["task_reviews_missing"]:
        return {"skill": "sdd-implement", "spec": i,
                "reason": f"task reviews missing for {', '.join(s['task_reviews_missing'])} "
                          "(review_package.py and the reviewer agent; '- T-nn: pass' in progress.md)"}
    if not s["review_valid"]:
        return {"skill": "sdd-review-diff", "spec": i, "reason": "T-nn tasks done: a valid review is missing (review.md)"}
    if s["review"] == "non-compliant":
        return non_compliant_review(s)
    if s["level"] == "L" and not s["human_diff_review"]:
        return {"skill": "sdd-review-diff", "spec": i,
                "reason": "level L: the human reading of the diff is missing ('Human diff review' in review.md)"}
    return closing(s)


def non_compliant_review(s: dict) -> dict:
    if s["review_tasks"]:
        return {"skill": "sdd-review-diff", "spec": s["id"], "reason": "T-R fixes done: repeat the review"}
    return {"skill": "sdd-review-diff", "spec": s["id"],
            "reason": "review 'non-compliant': turn the problems into T-R tasks in tasks.md"}


def closing(s: dict) -> dict:
    if s["doc_open"]:
        return {"skill": "sdd-docs", "spec": s["id"], "reason": "T-DOC open"}
    return {"skill": "sdd-sync", "spec": s["id"],
            "reason": "reconcile spec and docs/system (T-SYNC) and set Status = implemented"}


def waiting_task(s: dict) -> dict:
    return {"skill": "sdd-spec", "spec": s["id"],
            "reason": f"{s['next_task']} covers {', '.join(s['next_task_waits_for'])}, named by a non-blocking open "
                      "question: get it answered and put the answer into the spec with a revision"}


def next_level_s(s: dict) -> dict:
    """Level S: no plan; the review is the PR review, review.md counts only if present."""
    i = s["id"]
    if not s["tasks"]:
        return {"skill": "sdd-tasks", "spec": i, "reason": "level S: minimal tasks, without a plan"}
    if s["next_task_waits_for"]:
        return waiting_task(s)
    if s["numbered_tasks_open"]:
        return {"skill": "sdd-implement", "spec": i,
                "reason": f"open tasks: {s['numbered_tasks_open']}, next {s['next_task']}"}
    if s["review"] == "non-compliant":
        return non_compliant_review(s)
    return closing(s)


def choose_spec(active: list[dict], choice: str | None, branch: str) -> dict | None:
    if choice:
        k = spec_lint.id_key(choice[5:] if choice.startswith("SPEC-") else choice)
        for s in active:
            title = s["title_id"][5:] if s["title_id"] else ""
            if choice == s["id"] or (title and spec_lint.id_key(title) == k):
                return s
        return None
    in_branch = [s for s in active if s["id"].lower() in branch.lower()] if branch else []
    if in_branch:
        return max(in_branch, key=lambda s: len(s["id"]))
    return active[0] if len(active) == 1 else None


def analyze(root: Path, choice: str | None = None) -> dict:
    workflows = root / ".github" / "workflows"
    infra = {
        "AGENTS.md": (root / "AGENTS.md").is_file(),
        "scripts/verify.py": (root / "scripts" / "verify.py").is_file(),
        "scripts/spec_lint.py": (root / "scripts" / "spec_lint.py").is_file(),
        "ci": any(workflows.glob("*.y*ml")) if workflows.is_dir() else False,
        "docs/": (root / "docs").is_dir(),
    }
    base = root / "docs" / "specs"
    specs = [analyze_spec(d) for d in sorted(p for p in base.glob("*") if p.is_dir())] if base.is_dir() else []
    for s in specs:
        if s["status"] not in CLOSED:
            s["next"] = next_for_spec(s)
    bugs_dir = root / "docs" / "bugs"
    open_bugs = []
    if bugs_dir.is_dir():
        for p in sorted(bugs_dir.glob("*.md")):
            state = _field(_read(p), "Status").split("|")[0].strip()
            if state != "verified":
                open_bugs.append({"file": p.name, "status": state or "n/a"})
    has_map = (root / "docs" / "system" / "map.md").is_file()
    code = has_code(root)
    branch = current_branch(root)
    return {"infra": infra, "existing_code": code, "map": has_map, "branch": branch, "specs": specs,
            "open_bugs": open_bugs, "next": next_step(infra, code, has_map, specs, choice, branch)}


def next_step(infra: dict, code: bool, has_map: bool, specs: list[dict], choice: str | None = None,
              branch: str = "") -> dict:
    if not (infra["AGENTS.md"] and infra["scripts/verify.py"]):
        return {"skill": "sdd-init", "reason": "AGENTS.md and/or scripts/verify.py missing"}
    active = [s for s in specs if s["status"] not in CLOSED]
    if code and not has_map and not specs:
        return {"skill": "sdd-map-codebase", "reason": "existing code without docs/system/map.md (brownfield)"}
    if not active:
        return {"skill": "sdd-spec", "reason": "no active spec: start a new one"}
    s = choose_spec(active, choice, branch)
    if s is None and choice:
        return {"skill": "choose", "reason": f"no active spec matches '{choice}'"}
    if s is None:
        listing = ", ".join(f"{a['id']} ({a['next']['skill']})" for a in active)
        return {"skill": "choose", "reason": f"{len(active)} active specs and none in the branch name: {listing}. "
                                             "Switch to the spec's branch or use --spec <id>"}
    return s["next"]


def show(st: dict) -> None:
    print("INFRASTRUCTURE")
    for k, v in st["infra"].items():
        print(f"  [{'x' if v else ' '}] {k}")
    print(f"EXISTING CODE: {'yes' if st['existing_code'] else 'no'}; "
          f"MAP (docs/system/map.md): {'yes' if st['map'] else 'no'}")
    if st["branch"]:
        print(f"BRANCH: {st['branch']}")
    print("SPECS")
    if not st["specs"]:
        print("  (none)")
    for s in st["specs"]:
        plan = "approved" if s["plan_approved"] else ("to approve" if s["plan"] else "no")
        then = f" -> {s['next']['skill']}" if "next" in s else ""
        print(f"  {s['id']}: level={s['level']} status={s['status']} approved={'yes' if s['spec_approved'] else 'no'} "
              f"plan={plan} tasks={s['tasks_closed']}/{s['tasks_total']} review={s['review'] or 'no'}{then}")
    if st["open_bugs"]:
        print("UNVERIFIED BUGS: " + ", ".join(f"{b['file']} ({b['status']})" for b in st["open_bugs"])
              + "  -> sdd-bugfix")
    p = st["next"]
    print(f"NEXT: {p['skill']}{' on ' + p['spec'] if 'spec' in p else ''} - {p['reason']}")


def main(argv: list[str]) -> int:
    choice = argv[argv.index("--spec") + 1] if "--spec" in argv and argv.index("--spec") + 1 < len(argv) else None
    args = [a for a in argv if not a.startswith("--") and a != choice]
    st = analyze(Path(args[0]) if args else Path("."), choice)
    print(json.dumps(st, ensure_ascii=False, indent=2)) if "--json" in argv else show(st)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # UTF-8 even with a cp1252 console (Windows)
        stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
