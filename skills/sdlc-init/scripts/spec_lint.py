#!/usr/bin/env python3
"""Controlli deterministici su spec, piano e task del playbook.

Uso:
  python scripts/spec_lint.py docs/specs/001-x/spec.md
  python scripts/spec_lint.py docs/specs/001-x/spec.md --plan docs/specs/001-x/plan.md
  python scripts/spec_lint.py docs/specs/001-x/spec.md --tasks docs/specs/001-x/tasks.md

Exit code 0 = nessun errore (gli avvisi non bloccano). Solo stdlib, cross-platform.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

STATI = ("draft", "approved", "implemented", "superseded")
SEZIONI = ("Problema e obiettivo", "Scope", "Requisiti", "Acceptance criteria", "Domande aperte")
REQ_DEF = re.compile(r"^\s*[-*]\s+(REQ-\d+)\b")
AC_DEF = re.compile(r"^\s*[-*]\s+(AC-\d+)\s*\[([^\]]*)\]")
PLACEHOLDER = re.compile(r"<[^<>\n]{1,80}>")


def leggi(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def sezioni(testo: str) -> dict[str, list[str]]:
    """Mappa titolo '## ...' -> righe della sezione."""
    out: dict[str, list[str]] = {}
    corrente = None
    for riga in testo.splitlines():
        m = re.match(r"^##\s+(.*?)\s*$", riga)
        if m:
            corrente = m.group(1)
            out[corrente] = []
        elif corrente is not None:
            out[corrente].append(riga)
    return out


def campo(testo: str, nome: str) -> str | None:
    m = re.search(rf"^\s*[-*]\s+{re.escape(nome)}\s*:\s*(.*)$", testo, re.M)
    return m.group(1).strip() if m else None


def pulisci(valore: str | None) -> str:
    """Valore del campo senza commenti HTML."""
    return re.sub(r"<!--.*?-->", "", valore or "").strip()


def parse_spec(testo: str):
    reqs = [m.group(1) for r in testo.splitlines() if (m := REQ_DEF.match(r))]
    acs: dict[str, list[str]] = {}
    for r in testo.splitlines():
        if (m := AC_DEF.match(r)):
            acs[m.group(1)] = re.findall(r"REQ-\d+", m.group(2))
    return reqs, acs


def lint_spec(testo: str) -> tuple[list[str], list[str]]:
    err: list[str] = []
    avv: list[str] = []
    stato = pulisci(campo(testo, "Stato")).split("|")[0].strip()
    if stato not in STATI:
        err.append(f"Stato mancante o non valido (atteso uno tra: {', '.join(STATI)}); trovato '{stato}'")
    sez = sezioni(testo)
    for s in SEZIONI:
        if s not in sez:
            err.append(f"Sezione mancante: '## {s}'")

    reqs, acs = parse_spec(testo)
    if len(reqs) != len(set(reqs)):
        err.append("ID REQ duplicati")
    if not reqs:
        err.append("Nessun requisito (REQ-nnn) trovato")
    for req in reqs:
        if not any(req in refs for refs in acs.values()):
            err.append(f"{req} non ha nessun acceptance criterion")
    righe_ac = [m.group(1) for r in testo.splitlines() if (m := AC_DEF.match(r))]
    if len(righe_ac) != len(set(righe_ac)):
        err.append("ID AC duplicati")
    for ac, refs in acs.items():
        if not refs:
            err.append(f"{ac} non cita nessun REQ")
        for ref in refs:
            if ref not in reqs:
                err.append(f"{ac} cita {ref}, che non esiste")

    scope = "\n".join(sez.get("Scope", []))
    m = re.search(r"Non-scope[^:\n]*:\**\s*(.*)", scope, re.I)
    nonscope = m.group(1).strip() if m else ""
    if not m or not nonscope or PLACEHOLDER.fullmatch(nonscope):
        err.append("Non-scope assente o non compilato")

    if stato in ("approved", "implemented"):
        appr = pulisci(campo(testo, "Approvata da / data"))
        if not appr or PLACEHOLDER.search(appr):
            err.append("Spec approvata ma 'Approvata da / data' non compilato")
        aperte = [
            r.strip() for r in sez.get("Domande aperte", [])
            if r.strip().startswith(("-", "*")) and not re.match(r"^[-*]\s*(nessuna|none)\b", r.strip(), re.I)
        ]
        if aperte:
            err.append(f"Spec approvata con {len(aperte)} domande aperte")
        if "[ASSUNZIONE]" in testo:
            avv.append("Restano assunzioni marcate [ASSUNZIONE]: validale o riformulale")
    return err, avv


def lint_plan(spec: str, plan: str) -> tuple[list[str], list[str]]:
    _, acs = parse_spec(spec)
    err = [f"{ac} non compare nel piano (strategia di test)" for ac in acs if ac not in plan]
    avv = []
    appr = pulisci(campo(plan, "Approvato da / data"))
    if not appr or PLACEHOLDER.search(appr):
        avv.append("Piano non ancora approvato ('Approvato da / data' vuoto)")
    return err, avv


def lint_tasks(spec: str, tasks: str) -> tuple[list[str], list[str]]:
    _, acs = parse_spec(spec)
    err: list[str] = []
    righe = [r for r in tasks.splitlines() if re.match(r"^\s*-\s+\[[ xX]\]\s+T-", r)]
    if not righe:
        return ["Nessuna task (- [ ] T-...) trovata"], []
    coperti: set[str] = set()
    ids: list[str] = []
    for r in righe:
        tid = re.search(r"\bT-[A-Z0-9]+\b", r).group(0)
        ids.append(tid)
        coperti.update(re.findall(r"AC-\d+", r.split("copre:")[-1] if "copre:" in r else ""))
        if re.fullmatch(r"T-\d+", tid):
            if not re.search(r"verifica:\s*`[^`]+`", r):
                err.append(f"{tid}: manca 'verifica: `<comando>`'")
            if "copre:" not in r or not re.search(r"AC-\d+", r.split("copre:")[-1]):
                err.append(f"{tid}: manca 'copre: AC-nnn'")
    if len(ids) != len(set(ids)):
        err.append("ID task duplicati")
    for tag in ("T-DOC", "T-SYNC"):
        if tag not in ids:
            err.append(f"Manca la task {tag}")
    for ac in acs:
        if ac not in coperti:
            err.append(f"{ac} non è coperto da nessuna task")
    return err, []


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("--"):
        print(__doc__)
        return 2
    spec_path, opts = argv[0], argv[1:]
    spec = leggi(spec_path)
    err, avv = lint_spec(spec)
    for i, o in enumerate(opts):
        if o == "--plan" and i + 1 < len(opts):
            e, a = lint_plan(spec, leggi(opts[i + 1]))
            err += e
            avv += a
        if o == "--tasks" and i + 1 < len(opts):
            e, a = lint_tasks(spec, leggi(opts[i + 1]))
            err += e
            avv += a
    for a in avv:
        print(f"[WARN] {a}")
    for e in err:
        print(f"[ERRORE] {e}")
    print("LINT: " + ("OK" if not err else f"{len(err)} errori"))
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
