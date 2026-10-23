#!/usr/bin/env python3
"""Hook Stop (Claude Code), opt-in: impedisce all'agente di fermarsi se `verify` è rosso.

Attivo solo con la variabile d'ambiente SDLC_ENFORCE_VERIFY=1. Altrimenti non fa nulla.
Legge da stdin il JSON dell'evento. Esce 0 (via libera) se: non attivo, `stop_hook_active` è vero (evita
cicli infiniti), o il progetto non ha scripts/verify.py. Se verify è rosso esce 2 e scrive l'esito su
stderr, che Claude Code restituisce all'agente. SDLC_VERIFY_ARGS (es. "--fast") restringe la verifica.
Solo stdlib, cross-platform.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if os.environ.get("SDLC_ENFORCE_VERIFY") != "1":
        return 0
    try:
        evento = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        evento = {}
    if evento.get("stop_hook_active"):
        return 0
    radice = Path(evento.get("cwd") or os.getcwd())
    verify = radice / "scripts" / "verify.py"
    if not verify.is_file():
        return 0
    args = os.environ.get("SDLC_VERIFY_ARGS", "").split()
    r = subprocess.run([sys.executable, str(verify), *args], cwd=radice, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode == 0:
        return 0
    coda = "\n".join((r.stdout + r.stderr).strip().splitlines()[-30:])
    sys.stderr.write("verify è ROSSO: non dichiarare il lavoro completato. Correggi e riesegui.\n" + coda + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
