#!/usr/bin/env python3
"""Hook Stop (Claude Code), opt-in: impedisce all'agente di fermarsi se `verify` è rosso.

Attivo solo con la variabile d'ambiente SDLC_ENFORCE_VERIFY=1. Altrimenti non fa nulla.
Legge da stdin il JSON dell'evento. Esce 0 (via libera) se: non attivo, il progetto non ha scripts/verify.py,
verify è verde, o una spec è in **fase rossa** (l'ultima task T-nn chiusa è marcata "atteso: rosso" e la
successiva è aperta: i test rossi sono il risultato atteso).
Se verify è rosso esce 2 e scrive l'esito su stderr, che Claude Code restituisce all'agente.
Blocca fino a SDLC_STOP_MAX volte di fila per sessione (default 3, contatore per `session_id`, azzerato quando
verify torna verde); poi lascia fermare l'agente con un avviso per l'utente. Senza `session_id` blocca una volta
sola (`stop_hook_active`). SDLC_VERIFY_ARGS (es. "--fast") restringe la verifica. Solo stdlib, cross-platform.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
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


def file_contatore(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"sdlc-stop-{re.sub(r'[^A-Za-z0-9_-]', '', session_id)[:80]}.txt"


def leggi_contatore(p: Path) -> int:
    try:
        return int(p.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def avviso(messaggio: str) -> None:
    """Messaggio per l'utente con exit 0 (campo systemMessage dell'output JSON degli hook)."""
    print(json.dumps({"systemMessage": messaggio}, ensure_ascii=False))


def main() -> int:
    if os.environ.get("SDLC_ENFORCE_VERIFY") != "1":
        return 0
    try:
        evento = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        evento = {}
    sessione = str(evento.get("session_id") or "")
    if not sessione and evento.get("stop_hook_active"):
        return 0
    radice = Path(evento.get("cwd") or os.getcwd())
    verify = radice / "scripts" / "verify.py"
    if not verify.is_file():
        return 0
    contatore = file_contatore(sessione) if sessione else None
    args = os.environ.get("SDLC_VERIFY_ARGS", "").split()
    r = subprocess.run([sys.executable, str(verify), *args], cwd=radice, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
    if r.returncode == 0:
        if contatore:
            contatore.unlink(missing_ok=True)
        return 0
    rosse = specs_in_fase_rossa(radice)
    if rosse:
        avviso("verify rosso atteso: fase rossa in " + ", ".join(rosse))
        return 0
    try:
        massimo = max(1, int(os.environ.get("SDLC_STOP_MAX", "3")))
    except ValueError:
        massimo = 3
    blocchi = 1
    if contatore:
        blocchi = leggi_contatore(contatore) + 1
        if blocchi > massimo:
            contatore.unlink(missing_ok=True)
            avviso(f"verify è ancora ROSSO dopo {massimo} blocchi: l'agente si ferma, serve una revisione umana")
            return 0
        contatore.write_text(str(blocchi), encoding="utf-8")
    coda = "\n".join((r.stdout + r.stderr).strip().splitlines()[-30:])
    sys.stderr.write(f"verify è ROSSO (blocco {blocchi}/{massimo}): non dichiarare il lavoro completato. "
                     "Correggi e riesegui.\n" + coda + "\n")
    return 2


if __name__ == "__main__":
    for flusso in (sys.stdin, sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
