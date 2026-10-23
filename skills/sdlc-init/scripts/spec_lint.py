#!/usr/bin/env python3
"""Controlli deterministici su spec, piano e task del playbook.

Uso:
  python scripts/spec_lint.py docs/specs/001-x/spec.md
  python scripts/spec_lint.py docs/specs/001-x/spec.md --plan docs/specs/001-x/plan.md
  python scripts/spec_lint.py docs/specs/001-x/spec.md --tasks docs/specs/001-x/tasks.md
  python scripts/spec_lint.py docs/specs/001-x/spec.md --plan docs/specs/001-x/plan.md --base main
  python scripts/spec_lint.py docs/specs/001-x/spec.md --hash      # stampa l'hash da scrivere in "- Hash:"

Approvazione (playbook §1.2):
  - hash anti-deriva: una spec approved/implemented e un piano approvato riportano "- Hash: sha256:..." del proprio
    corpo (dalla prima sezione "## " in poi); se il corpo cambia, l'approvazione decade. Il piano riporta anche
    "- Basato su spec: sha256:..." e decade se la spec cambia.
  - --base <ref>: spec (e piano) devono esistere su <ref> ed essere identici: il merge della PR di design su un
    branch protetto è l'approvazione, e l'agente non può farlo da solo.
  - con --plan e --tasks insieme: tasks.md riporta "- Basato su piano: sha256:..." e decade se il piano cambia.
ID e stati (playbook §3.3): titolo "# SPEC-aaaa-mm-gg-slug: ..." con l'ID uguale al nome della cartella (il vecchio
"# SPEC-NNN: ..." resta valido). Stato in-revisione: spec approvata che si sta modificando, con una voce in
"## Revisioni"; torna approved solo con nuova approvazione e nuovo hash.
Task: T-nn dal piano (verifica: e copre: obbligatori), T-Rnn dai problemi della review (copre: facoltativo).
Exit code 0 = nessun errore (gli avvisi non bloccano). Solo stdlib + git (per --base), cross-platform.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

STATI = ("draft", "approved", "in-revisione", "implemented", "superseded")
SEZIONI = ("Problema e obiettivo", "Scope", "Requisiti", "Acceptance criteria", "Domande aperte")
# ID di una spec: data + slug (2026-10-24-export-csv, uguale al nome della cartella) o il vecchio numero (001).
ID_DATA = r"\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*"
TITOLO = re.compile(rf"^#\s+SPEC-({ID_DATA}|\d+)\s*:", re.M)
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


def id_spec(testo: str) -> str | None:
    """ID dal titolo "# SPEC-<id>: ...": data + slug oppure numero."""
    m = TITOLO.search(testo)
    return m.group(1) if m else None


def chiave_id(valore: str) -> str:
    """Forma confrontabile di un ID: numeri senza zeri iniziali, slug in minuscolo con "-"."""
    v = valore.replace("_", "-").lower()
    return str(int(v)) if v.isdigit() else v


def problemi_id(testo: str, cartella: str | None) -> list[str]:
    sid = id_spec(testo)
    if sid is None:
        return ["Titolo senza ID: atteso '# SPEC-aaaa-mm-gg-slug: titolo' (o il vecchio '# SPEC-NNN: titolo')"]
    if not sid.isdigit():
        try:
            date.fromisoformat(sid[:10])
        except ValueError:
            return [f"ID {sid}: la data iniziale non è valida (atteso aaaa-mm-gg)"]
        if cartella is not None and cartella != sid:
            return [f"ID del titolo ({sid}) diverso dal nome della cartella ({cartella}): devono coincidere"]
    elif cartella is not None and (m := re.match(r"^(\d+)-", cartella)) and int(m.group(1)) != int(sid):
        return [f"ID del titolo (SPEC-{sid}) diverso dal numero della cartella ({cartella})"]
    return []


def impronta(testo: str) -> str:
    """Hash del corpo (dalla prima sezione "## "): l'intestazione con stato, approvatore e hash non conta."""
    righe = testo.replace("\r\n", "\n").split("\n")
    inizio = next((i for i, r in enumerate(righe) if r.startswith("## ")), len(righe))
    corpo = "\n".join(r.rstrip() for r in righe[inizio:]).strip("\n")
    return "sha256:" + hashlib.sha256(corpo.encode("utf-8")).hexdigest()


def problemi_hash(testo: str, cosa: str) -> list[str]:
    registrato = pulisci(campo(testo, "Hash"))
    if not registrato or PLACEHOLDER.search(registrato):
        return [f"{cosa}: approvazione senza '- Hash:' (calcolalo con: python scripts/spec_lint.py <file> --hash)"]
    if registrato != impronta(testo):
        return [f"{cosa}: contenuto modificato dopo l'approvazione (Hash non corrisponde): torna in bozza e fai riapprovare"]
    return []


def approvazione_piano(spec: str, plan: str) -> list[str]:
    """Problemi dell'approvazione di un piano già marcato come approvato."""
    err = problemi_hash(plan, "Piano")
    base = pulisci(campo(plan, "Basato su spec"))
    if not base or PLACEHOLDER.search(base):
        err.append("Piano approvato senza '- Basato su spec: sha256:...'")
    elif base != impronta(spec):
        err.append("Piano basato su un'altra versione della spec ('Basato su spec' diverso): riapprova il piano")
    return err


def piano_approvato(plan: str) -> bool:
    appr = pulisci(campo(plan, "Approvato da / data"))
    return bool(appr) and not PLACEHOLDER.search(appr)


def su_base(percorso: str, ref: str) -> list[str]:
    """Il file deve esistere su <ref> ed essere identico alla copia di lavoro (fine riga a parte)."""
    p = Path(percorso)
    try:
        r = subprocess.run(["git", "-C", str(p.parent), "show", f"{ref}:./{p.name}"], capture_output=True)
    except OSError:
        return ["git non disponibile: impossibile verificare --base"]
    if r.returncode != 0:
        return [f"{p.as_posix()} non è su {ref}: l'approvazione passa dal merge della PR di design"]
    su_ref = r.stdout.decode("utf-8", "replace").replace("\r\n", "\n").strip()
    if su_ref != p.read_text(encoding="utf-8").replace("\r\n", "\n").strip():
        return [f"{p.as_posix()} è diverso dalla versione su {ref}: le modifiche vanno riapprovate con una PR"]
    return []


def parse_spec(testo: str):
    reqs = [m.group(1) for r in testo.splitlines() if (m := REQ_DEF.match(r))]
    acs: dict[str, list[str]] = {}
    for r in testo.splitlines():
        if (m := AC_DEF.match(r)):
            acs[m.group(1)] = re.findall(r"REQ-\d+", m.group(2))
    return reqs, acs


def voci_compilate(righe: list[str]) -> list[str]:
    """Voci di elenco con contenuto reale (non segnaposto, non "nessuna")."""
    return [r.strip() for r in righe if r.strip().startswith(("-", "*")) and not PLACEHOLDER.search(r)
            and not re.match(r"^[-*]\s*(nessuna|none)\b", r.strip(), re.I)]


def lint_spec(testo: str, cartella: str | None = None) -> tuple[list[str], list[str]]:
    """cartella: nome della cartella della spec, che per gli ID con data deve coincidere con l'ID."""
    err: list[str] = []
    avv: list[str] = []
    stato = pulisci(campo(testo, "Stato")).split("|")[0].strip()
    if stato not in STATI:
        err.append(f"Stato mancante o non valido (atteso uno tra: {', '.join(STATI)}); trovato '{stato}'")
    err += problemi_id(testo, cartella)
    sez = sezioni(testo)
    if stato == "in-revisione" and not voci_compilate(sez.get("Revisioni", [])):
        err.append("Spec in revisione senza una voce in '## Revisioni' (data, cosa cambia e perché)")
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
        err += problemi_hash(testo, "Spec")
        aperte = [
            r.strip() for r in sez.get("Domande aperte", [])
            if r.strip().startswith(("-", "*")) and not re.match(r"^[-*]\s*(nessuna|none)\b", r.strip(), re.I)
        ]  # qui anche un segnaposto conta come domanda aperta
        if aperte:
            err.append(f"Spec approvata con {len(aperte)} domande aperte")
        if "[ASSUNZIONE]" in testo:
            avv.append("Restano assunzioni marcate [ASSUNZIONE]: validale o riformulale")
    return err, avv


def lint_plan(spec: str, plan: str) -> tuple[list[str], list[str]]:
    _, acs = parse_spec(spec)
    strategia = next((r for t, r in sezioni(plan).items() if t.startswith("Strategia di test")), None)
    if strategia is None:
        err = ["Sezione '## Strategia di test' mancante nel piano"]
    else:
        nel_piano = set(re.findall(r"\bAC-\d+\b", "\n".join(strategia)))
        err = [f"{ac} non compare nel piano (strategia di test)" for ac in acs if ac not in nel_piano]
    avv = []
    if piano_approvato(plan):
        err += approvazione_piano(spec, plan)
    else:
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
        if re.fullmatch(r"T-R?\d+", tid):  # T-nn dal piano, T-Rnn dai problemi della review
            if (m := PLACEHOLDER.search(r)):
                err.append(f"{tid}: segnaposto non compilato {m.group(0)}")
            if not re.search(r"verifica:\s*`[^`]+`", r):
                err.append(f"{tid}: manca 'verifica: `<comando>`'")
            if tid.startswith("T-R"):
                continue  # una correzione può non toccare un AC: copre: è facoltativo
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


def tasks_su_piano(plan: str, tasks: str) -> tuple[list[str], list[str]]:
    """Le task registrano l'hash del piano da cui derivano: se il piano cambia vanno riviste."""
    base = pulisci(campo(tasks, "Basato su piano"))
    if not base or PLACEHOLDER.search(base):
        return [], ["Task senza '- Basato su piano: sha256:...': non si accorgono se il piano cambia"]
    if base != impronta(plan):
        return ["Task basate su un'altra versione del piano ('Basato su piano' diverso): rivedile e aggiornalo"], []
    return [], []


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("--"):
        print(__doc__)
        return 2
    spec_path, opts = argv[0], argv[1:]
    spec = leggi(spec_path)
    if "--hash" in opts:
        print(impronta(spec))
        return 0
    err, avv = lint_spec(spec, Path(spec_path).resolve().parent.name)
    da_confrontare = [spec_path]
    plan = tasks = None
    for i, o in enumerate(opts):
        if o == "--plan" and i + 1 < len(opts):
            plan = leggi(opts[i + 1])
            e, a = lint_plan(spec, plan)
            err += e
            avv += a
            da_confrontare.append(opts[i + 1])
        if o == "--tasks" and i + 1 < len(opts):
            tasks = leggi(opts[i + 1])
            e, a = lint_tasks(spec, tasks)
            err += e
            avv += a
    if plan is not None and tasks is not None:
        e, a = tasks_su_piano(plan, tasks)
        err += e
        avv += a
    if "--base" in opts and opts.index("--base") + 1 < len(opts):
        ref = opts[opts.index("--base") + 1]
        for f in da_confrontare:
            err += su_base(f, ref)
    for a in avv:
        print(f"[WARN] {a}")
    for e in err:
        print(f"[ERRORE] {e}")
    print("LINT: " + ("OK" if not err else f"{len(err)} errori"))
    return 1 if err else 0


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
