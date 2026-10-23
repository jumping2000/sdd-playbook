#!/usr/bin/env python3
"""Hook Stop (Claude Code), opt-in: impedisce all'agente di fermarsi se `verify` è rosso.

Attivo solo con la variabile d'ambiente SDLC_ENFORCE_VERIFY=1. Altrimenti non fa nulla.
Legge da stdin il JSON dell'evento. Esce 0 (via libera) se: non attivo, `stop_hook_active` è vero (evita
cicli infiniti), il progetto non ha scripts/verify.py, o una spec è in **fase rossa** (l'ultima task T-nn
chiusa è marcata "atteso: rosso" e la successiva è aperta: i test rossi sono il risultato atteso).
Se verify è rosso esce 2 e scrive l'esito su stderr, che Claude Code restituisce all'agente.
SDLC_VERIFY_ARGS (es. "--fast") restringe la verifica. Solo stdlib, cross-platform.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

TASK = re.compile(r"^\s*-\s+\[([ xX])\]\s+(T-\d+)\b(.*)$", re.M)


def fase_rossa(tasks: str) -> str | None:
    """ID della task di test "atteso: rosso" appena chiusa, se la task successiva è ancora aperta."""
    precedente = None
    for stato, tid, resto in TASK.findall(tasks):
        if stato == " ":
            if precedente and "atteso: rosso" in precedente[1]:
                return precedente[0]
            return None
        precedente = (tid, resto)
    return None


def specs_in_fase_rossa(radice: Path) -> list[str]:
    out = []
    for t in sorted((radice / "docs" / "specs").glob("*/tasks.md")):
        tid = fase_rossa(t.read_text(encoding="utf-8", errors="replace"))
        if tid:
            out.append(f"{t.parent.name} ({tid})")
    return out


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
                       encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
    if r.returncode == 0:
        return 0
    rosse = specs_in_fase_rossa(radice)
    if rosse:
        print("verify rosso atteso: fase rossa in " + ", ".join(rosse))
        return 0
    coda = "\n".join((r.stdout + r.stderr).strip().splitlines()[-30:])
    sys.stderr.write("verify è ROSSO: non dichiarare il lavoro completato. Correggi e riesegui.\n" + coda + "\n")
    return 2


if __name__ == "__main__":
    for flusso in (sys.stdin, sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
