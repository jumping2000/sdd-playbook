#!/usr/bin/env python3
"""Hook Stop (Claude Code), opt-in: impedisce all'agente di fermarsi se `verify` è rosso.

Attivo solo con la variabile d'ambiente SDLC_ENFORCE_VERIFY=1. Altrimenti non fa nulla.
Legge da stdin il JSON dell'evento. Esce 0 (via libera) se: non attivo, il progetto non ha scripts/verify.py,
verify è verde, o una spec è in **fase rossa** (l'ultima task T-nn chiusa è marcata "atteso: rosso" e la
successiva è aperta: i test rossi sono il risultato atteso).
Se verify è rosso esce 2 e scrive l'esito su stderr, che Claude Code restituisce all'agente.
Blocca fino a SDLC_STOP_MAX volte di fila per sessione (default 3, contatore per `session_id` in una cartella
privata dell'utente: %LOCALAPPDATA%\\sdlc-playbook o ~/.cache/sdlc-playbook; azzerato quando verify torna verde); poi lascia fermare l'agente con un avviso per l'utente. Senza `session_id` blocca una volta
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
            if precedente and re.search(r"atteso:\s*rosso", precedente[1], re.I):
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


def cartella_stato() -> Path:
    """Cartella privata dell'utente (0700), non la temp condivisa: nessuno può prepararvi file o link."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or (str(Path.home() / ".cache") if os.environ.get("HOME") else None)
    d = Path(base or tempfile.gettempdir()) / "sdlc-playbook"
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    return d


def file_contatore(session_id: str) -> Path:
    return cartella_stato() / f"stop-{re.sub(r'[^A-Za-z0-9_-]', '', session_id)[:80]}.txt"


def leggi_contatore(p: Path) -> int:
    if p.is_symlink():
        return 0
    try:
        return int(p.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def scrivi_contatore(p: Path, valore: int) -> None:
    if p.is_symlink():
        p.unlink()
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(p, flags, 0o600), "w", encoding="utf-8") as f:
        f.write(str(valore))


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
        scrivi_contatore(contatore, blocchi)
    coda = "\n".join((r.stdout + r.stderr).strip().splitlines()[-30:])
    sys.stderr.write(f"verify è ROSSO (blocco {blocchi}/{massimo}): non dichiarare il lavoro completato. "
                     "Correggi e riesegui.\n" + coda + "\n")
    return 2


if __name__ == "__main__":
    for flusso in (sys.stdin, sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
