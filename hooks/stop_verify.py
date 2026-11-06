#!/usr/bin/env python3
"""Stop hook (Claude Code), opt-in: prevents the agent from stopping while `verify` is red.

Active only with the environment variable SDD_ENFORCE_VERIFY=1. Otherwise it does nothing.
Reads the event JSON from stdin. Exits 0 (go ahead) if: not active, the project has no scripts/verify.py, verify is
green, or the branch is in the **red phase**: its last commit carries the trailer "Test-Lock: T-nn" (the red tests of a
task were just locked and the implementation has not started: red tests are the expected result).
If verify is red it exits 2 and writes the result on stderr, which Claude Code returns to the agent.
It blocks up to SDD_STOP_MAX times in a row per session (default 3, counter per `session_id` in a private user folder:
%LOCALAPPDATA%\\sdd-playbook or ~/.cache/sdd-playbook; reset when verify turns green); then it lets the agent stop with
a warning for the user. Without `session_id` it blocks only once (`stop_hook_active`). SDD_VERIFY_ARGS (e.g. "--fast")
narrows the verification. Standard library only, cross-platform.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TEST_LOCK = re.compile(r"^Test-Lock:\s*(T-\d+)", re.M)


def red_phase(root: Path) -> str | None:
    """Task of the Test-Lock trailer of the last commit, if the branch is in the red phase."""
    try:
        r = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%B"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = TEST_LOCK.search(r.stdout) if r.returncode == 0 else None
    return m.group(1) if m else None


def state_dir() -> Path:
    """Private user folder (0700), not the shared temp: nobody can plant files or links there."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or (str(Path.home() / ".cache") if os.environ.get("HOME") else None)
    d = Path(base or tempfile.gettempdir()) / "sdd-playbook"
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    return d


def counter_file(session_id: str) -> Path:
    return state_dir() / f"stop-{re.sub(r'[^A-Za-z0-9_-]', '', session_id)[:80]}.txt"


def read_counter(p: Path) -> int:
    if p.is_symlink():
        return 0
    try:
        return int(p.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def write_counter(p: Path, value: int) -> None:
    if p.is_symlink():
        p.unlink()
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(p, flags, 0o600), "w", encoding="utf-8") as f:
        f.write(str(value))


def notice(message: str) -> None:
    """Message for the user with exit 0 (systemMessage field of the hook JSON output)."""
    print(json.dumps({"systemMessage": message}, ensure_ascii=False))


def main() -> int:
    if os.environ.get("SDD_ENFORCE_VERIFY") != "1":
        return 0
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        event = {}
    session = str(event.get("session_id") or "")
    if not session and event.get("stop_hook_active"):
        return 0
    root = Path(event.get("cwd") or os.getcwd())
    verify = root / "scripts" / "verify.py"
    if not verify.is_file():
        return 0
    counter = counter_file(session) if session else None
    args = os.environ.get("SDD_VERIFY_ARGS", "").split()
    r = subprocess.run([sys.executable, str(verify), *args], cwd=root, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
    if r.returncode == 0:
        if counter:
            counter.unlink(missing_ok=True)
        return 0
    red = red_phase(root)
    if red:
        notice(f"verify red as expected: red phase of {red} (tests locked, implementation not started)")
        return 0
    try:
        cap = max(1, int(os.environ.get("SDD_STOP_MAX", "3")))
    except ValueError:
        cap = 3
    blocks = 1
    if counter:
        blocks = read_counter(counter) + 1
        if blocks > cap:
            counter.unlink(missing_ok=True)
            notice(f"verify is still RED after {cap} blocks: the agent stops, a human review is needed")
            return 0
        write_counter(counter, blocks)
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-30:])
    sys.stderr.write(f"verify is RED (block {blocks}/{cap}): do not declare the work completed. Fix it and run it "
                     "again.\n" + tail + "\n")
    return 2


if __name__ == "__main__":
    for stream in (sys.stdin, sys.stdout, sys.stderr):  # UTF-8 even with a cp1252 console (Windows)
        stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
