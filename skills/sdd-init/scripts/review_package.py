#!/usr/bin/env python3
# sdd-playbook: 0.15.0
"""Review package: everything an independent reviewer needs for one task (or the whole branch), in one file.

Usage:
  python scripts/review_package.py docs/specs/001-x T-03 [--base main] [--out FILE]
  python scripts/review_package.py docs/specs/001-x [--base main] [--out FILE]       # whole branch

With a task: the commits of the branch whose message carries the trailer "Task: T-03" or "Test-Lock: T-03", the task
line, the text of the ACs it covers, the plan's "Interfaces" and "Review focus" sections and the rulings of that task in
progress.md. Without a task: every commit since the merge-base, all the ACs and the whole "Rulings" section.
Then the commit list, the files touched and the patches with extended context (generated files such as __pycache__/ and
reports/ excluded). The reviewer (sdd-reviewer, read-only) reads the file in one go instead of running git.
Default output: reports/review/<spec folder>/<task or "branch">.md (reports/ is ignored by git and by the checks).
The base is the first of main, master, origin/main, origin/master, or --base; uncommitted changes are not included.
Exit code: 0 package written; 2 wrong usage, git not usable or no commit for the task. Standard library + git only.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the project: it would count as a changed file
sys.path.insert(0, str(Path(__file__).resolve().parent))
import diff_scope  # noqa: E402
import spec_lint  # noqa: E402

TRAILER = r"^(?:Task|Test-Lock):\s*{}\s*$"
OPTIONS_WITH_VALUE = {"--base", "--out"}


def git_text(*args: str) -> str:
    r = subprocess.run(["git", "-c", "core.quotePath=false", *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.stdout if r.returncode == 0 else ""


def task_commits(mb: str, task: str | None) -> list[tuple[str, str]]:
    """(sha, subject) of the branch commits for the task (all of them without a task), oldest first."""
    out = []
    for sha in git_text("rev-list", "--reverse", f"{mb}..HEAD").split():
        body = git_text("show", "-s", "--format=%B", sha)
        if task is None or re.search(TRAILER.format(re.escape(task)), body, re.M):
            out.append((sha, body.splitlines()[0] if body else ""))
    return out


def section(text: str, prefix: str) -> list[str]:
    return next((lines for title, lines in spec_lint.sections(text).items() if title.lower().startswith(prefix)), [])


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def context(feature: Path, task: str | None) -> list[str]:
    """Task line, covered ACs, plan interfaces and review focus, rulings."""
    spec, plan = read(feature / "spec.md"), read(feature / "plan.md")
    tasks, progress = read(feature / "tasks.md"), read(feature / "progress.md")
    out = [f"# Review package: {feature.as_posix()}" + (f" {task}" if task else " (whole branch)"), ""]
    if task:
        line = next((t.strip() for t in tasks.splitlines() if re.search(rf"\b{re.escape(task)}\b", t)), "")
        out += ["## Task", line or f"(task {task} not found in tasks.md)", ""]
        covered = re.findall(r"AC-\d+", line.split("covers:")[-1]) if "covers:" in line else []
    else:
        covered = list(spec_lint.parse_spec(spec)[1])
    ac_lines = [t.strip() for t in spec.splitlines() if (m := spec_lint.AC_DEF.match(t)) and m.group(1) in covered]
    out += ["## Acceptance criteria", *(ac_lines or ["none"]), ""]
    for title in ("Interfaces", "Review focus"):
        lines = [x for x in section(plan, title.lower()) if x.strip()]
        if lines:
            out += [f"## {title} (plan)", *lines, ""]
    rulings = [x.strip() for x in section(progress, "rulings")
               if x.strip().startswith("-") and (task is None or re.search(rf"\b{re.escape(task)}\b", x))]
    out += ["## Rulings (progress.md)", *(rulings or ["none"]), ""]
    return out


def option(argv: list[str], name: str) -> str | None:
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def main(argv: list[str]) -> int:
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i > 0 and argv[i - 1] in OPTIONS_WITH_VALUE)]
    if not pos:
        print(__doc__)
        return 2
    feature = Path(pos[0])
    task = pos[1] if len(pos) > 1 else None
    if not feature.is_dir():
        print(f"[ERROR] folder not found: {feature}")
        return 2
    if task and not re.fullmatch(r"T-R?\d+", task):
        print(f"[ERROR] invalid task ID: {task} (expected T-nn or T-Rnn)")
        return 2
    base = diff_scope.base_ref(option(argv, "--base"))
    if base is None:
        print("[ERROR] not a git repository or no base ref found: use --base <ref>")
        return 2
    try:
        mb = diff_scope.merge_base(base)
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return 2
    commits = task_commits(mb, task)
    if not commits:
        what = f"with 'Task: {task}' or 'Test-Lock: {task}'" if task else "since the merge-base"
        print(f"[ERROR] no commit {what} in the branch (base: {base})")
        return 2
    out = context(feature, task)
    out += ["## Commits", *(f"- {sha[:7]} {subject}" for sha, subject in commits), ""]
    files: list[str] = []
    for sha, _ in commits:
        files += [f for f in git_text("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha).splitlines()
                  if f.strip() and not diff_scope.NOISE.search(f) and f not in files]
    out += ["## Files touched", *(f"- {f}" for f in files), "", "## Patches", ""]
    for sha, subject in commits:
        patch = git_text("show", "--format=", "--patch", "-U10", sha, "--", *files)
        out += [f"### {sha[:7]} {subject}", "```diff", patch.rstrip(), "```", ""]
    dest = Path(option(argv, "--out") or f"reports/review/{feature.name}/{task or 'branch'}.md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(out), encoding="utf-8")
    print(f"REVIEW PACKAGE: {dest.as_posix()} ({len(commits)} commits, {len(files)} files)")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # UTF-8 even with a cp1252 console (Windows)
        stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
