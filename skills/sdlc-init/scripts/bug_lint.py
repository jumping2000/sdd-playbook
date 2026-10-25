#!/usr/bin/env python3
# sdlc-playbook: 0.12.0
"""Controlli sul file di un bug (docs/bugs/BUG-nnn-*.md) secondo il playbook.

Uso:  python scripts/bug_lint.py docs/bugs/BUG-001-esempio.md

I requisiti crescono con lo stato:
  aperto        riproduzione compilata
  diagnosticato + attuale/atteso, "da NON cambiare", causa radice, test rosso indicato
  corretto      + fix minimo e test di non-regressione indicati
  verificato    + tutte le voci di "Chiusura" spuntate
Exit code: 0 nessun errore; 1 errori; 2 uso errato. Solo stdlib, cross-platform.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

STATI = ("aperto", "diagnosticato", "corretto", "verificato")
SEZIONI = ("Riproduzione", "Comportamento attuale vs atteso", "Comportamento da NON cambiare",
           "Causa radice", "Fix e test", "Chiusura")
PLACEHOLDER = re.compile(r"<[^<>\n]{1,100}>")


def sezioni(testo: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    cur = None
    for r in testo.splitlines():
        m = re.match(r"^##\s+(.*?)\s*$", r)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur is not None:
            out[cur].append(r)
    return out


def vero(righe: list[str]) -> list[str]:
    """Righe con contenuto reale: tolti commenti, segnaposto ed etichette ("Attuale:") non resta nulla."""
    out = []
    for r in righe:
        t = PLACEHOLDER.sub("", re.sub(r"<!--.*?-->", "", r)).strip()
        if ":" in t:
            t = t.split(":", 1)[1]
        if re.sub(r"[\s\-*`.,;]+", "", t):
            out.append(r.strip())
    return out


def valore_riga(righe: list[str], etichetta: str) -> str:
    for r in righe:
        if etichetta.lower() in r.lower() and ":" in r:
            return r.split(":", 1)[1].strip()
    return ""


def percorso_valido(valore: str) -> bool:
    m = re.search(r"`([^`]+)`", valore)
    return bool(m) and not PLACEHOLDER.fullmatch(m.group(1).strip())


def lint(testo: str) -> list[str]:
    err: list[str] = []
    m = re.search(r"^\s*[-*]\s+Stato\s*:\s*(.*)$", testo, re.M)
    stato = re.sub(r"<!--.*?-->", "", m.group(1)).strip().split("|")[0].strip() if m else ""
    if stato not in STATI:
        return [f"Stato mancante o non valido (atteso: {', '.join(STATI)}); trovato '{stato}'"]
    sez = sezioni(testo)
    for s in SEZIONI:
        if s not in sez:
            err.append(f"Sezione mancante: '## {s}'")
    if err:
        return err
    livello = STATI.index(stato)
    if not vero(sez["Riproduzione"]):
        err.append("Riproduzione non compilata")
    if livello >= 1:
        if len(vero(sez["Comportamento attuale vs atteso"])) < 2:
            err.append("Servono sia il comportamento attuale sia quello atteso")
        if not vero(sez["Comportamento da NON cambiare"]):
            err.append("'Comportamento da NON cambiare' vuoto: è la rete di non-regressione")
        if not vero(sez["Causa radice"]):
            err.append("Causa radice non compilata")
        if not percorso_valido(valore_riga(sez["Fix e test"], "Test rosso")):
            err.append("Manca il test rosso (percorso tra backtick in 'Test rosso ...')")
    if livello >= 2:
        fix = valore_riga(sez["Fix e test"], "Fix minimo")
        if not fix or PLACEHOLDER.search(fix):
            err.append("Fix minimo non descritto")
        if not percorso_valido(valore_riga(sez["Fix e test"], "non-regressione")):
            err.append("Manca il test di non-regressione (percorso tra backtick)")
    if livello >= 3:
        voci = [r for r in sez["Chiusura"] if re.match(r"^\s*-\s+\[[ xX]\]", r)]
        aperte = [r for r in voci if re.match(r"^\s*-\s+\[ \]", r)]
        if not voci:
            err.append("'Chiusura' senza voci spuntabili")
        if aperte:
            err.append(f"'Chiusura': {len(aperte)} voci non spuntate")
    return err


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    err = lint(Path(argv[0]).read_text(encoding="utf-8"))
    for e in err:
        print(f"[ERRORE] {e}")
    print("BUG-LINT: " + ("OK" if not err else f"{len(err)} errori"))
    return 1 if err else 0


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
