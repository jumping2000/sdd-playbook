#!/usr/bin/env python3
# sdlc-playbook: 0.12.0
"""Verifica unica del progetto: format, lint, type-check, test.

Exit code 0 = tutto verde. Solo stdlib; gira uguale su Windows, Linux, macOS.
Uso:  python scripts/verify.py            # tutti gli step, si ferma al primo rosso
      python scripts/verify.py --fast     # solo gli step marcati fast
      python scripts/verify.py test lint  # solo gli step indicati
      python scripts/verify.py --keep-going
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

# Adatta questa lista al progetto: (nome, comando, fast?)
STEPS = [
    ("format", ["uv", "run", "ruff", "format", "--check", "."], True),
    ("lint", ["uv", "run", "ruff", "check", "."], True),
    ("types", ["uv", "run", "mypy", "src"], False),
    ("test", ["uv", "run", "pytest", "-q", "--junitxml=reports/junit.xml"], False),  # report per trace_check --junit
    ("secrets", [sys.executable, "scripts/secrets_check.py", "--all"], True),
    # ("audit", ["uv", "run", "pip-audit"], False),  # audit delle dipendenze: richiede rete, vedi stacks.md
]


def run_step(name: str, cmd: list[str]) -> bool:
    exe = shutil.which(cmd[0])  # su Windows risolve .exe/.cmd via PATHEXT
    if exe is None:
        print(f"[FAIL] {name}: comando non trovato: {cmd[0]}")
        return False
    start = time.monotonic()
    env = {**os.environ, "PYTHONUTF8": "1"}
    ok = subprocess.run([exe, *cmd[1:]], env=env).returncode == 0
    print(f"[{'OK' if ok else 'FAIL'}] {name} ({time.monotonic() - start:.1f}s)")
    return ok


def main(argv: list[str]) -> int:
    fast = "--fast" in argv
    keep_going = "--keep-going" in argv
    wanted = [a for a in argv if not a.startswith("--")]
    steps = [s for s in STEPS if (not wanted or s[0] in wanted) and (s[2] or not fast)]
    if not steps:
        print("Nessuno step selezionato")
        return 2
    failed = []
    for name, cmd, _ in steps:
        if not run_step(name, cmd):
            failed.append(name)
            if not keep_going:
                break
    print("VERIFY: " + ("VERDE" if not failed else "ROSSO -> " + ", ".join(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
