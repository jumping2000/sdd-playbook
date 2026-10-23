#!/usr/bin/env python3
"""Stato del progetto secondo il playbook e prossima fase suggerita.

Uso:  python scripts/state.py [--json] [radice]
Sola lettura. Il suggerimento segue il flusso del playbook: init -> (map-codebase) -> spec -> plan ->
tasks -> implement -> review-diff -> docs -> sync. Bug aperti e sdlc-loop sono segnalati a parte.
Solo stdlib, cross-platform.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"<[^<>\n]{1,100}>")
ESITI = ("conforme", "conforme con riserve", "non conforme")
SORGENTI = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".cs", ".go", ".rb", ".php", ".rs", ".c", ".cpp", ".swift"}
IGNORA = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", "bin", "obj",
          "scripts", "docs", ".github", ".vscode"}


def _campo(testo: str, nome: str) -> str:
    m = re.search(rf"^\s*[-*]\s+{re.escape(nome)}\s*:\s*(.*)$", testo, re.M)
    return re.sub(r"<!--.*?-->", "", m.group(1)).strip() if m else ""


def _compilato(testo: str, nome: str) -> bool:
    v = _campo(testo, nome)
    return bool(v) and not PLACEHOLDER.search(v)


def _leggi(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def ha_codice(radice: Path, soglia: int = 3) -> bool:
    n = 0
    for dp, dn, fn in os.walk(radice):
        dn[:] = [d for d in dn if d not in IGNORA]
        n += sum(1 for f in fn if Path(f).suffix in SORGENTI)
        if n >= soglia:
            return True
    return False


def analizza_spec(d: Path) -> dict:
    spec, plan, tasks, review = (_leggi(d / n) for n in ("spec.md", "plan.md", "tasks.md", "review.md"))
    aperte = re.findall(r"^\s*-\s+\[ \]\s+(T-[A-Z0-9]+)", tasks, re.M)
    chiuse = re.findall(r"^\s*-\s+\[[xX]\]\s+(T-[A-Z0-9]+)", tasks, re.M)
    numerate = [t for t in aperte if re.fullmatch(r"T-\d+", t)]
    return {
        "id": d.name,
        "spec": bool(spec),
        "stato": (_campo(spec, "Stato").split("|")[0].strip() if spec else "") or "n/d",
        "spec_approvata": _compilato(spec, "Approvata da / data"),
        "plan": bool(plan),
        "plan_approvato": _compilato(plan, "Approvato da / data"),
        "tasks": bool(tasks),
        "task_chiuse": len(chiuse),
        "task_totali": len(chiuse) + len(aperte),
        "task_numerate_aperte": len(numerate),
        "prossima_task": numerate[0] if numerate else None,
        "doc_aperta": "T-DOC" in aperte,
        "sync_aperta": "T-SYNC" in aperte,
        "review": _campo(review, "Esito") if review else None,
        "review_valida": _campo(review, "Esito") in ESITI if review else False,
    }


def analizza(radice: Path) -> dict:
    infra = {
        "AGENTS.md": (radice / "AGENTS.md").is_file(),
        "scripts/verify.py": (radice / "scripts" / "verify.py").is_file(),
        "scripts/spec_lint.py": (radice / "scripts" / "spec_lint.py").is_file(),
        "ci": any((radice / ".github" / "workflows").glob("*.y*ml")) if (radice / ".github" / "workflows").is_dir() else False,
        "docs/": (radice / "docs").is_dir(),
    }
    base = radice / "docs" / "specs"
    specs = [analizza_spec(d) for d in sorted(p for p in base.glob("*") if p.is_dir())] if base.is_dir() else []
    bugs_dir = radice / "docs" / "bugs"
    bug_aperti = []
    if bugs_dir.is_dir():
        for p in sorted(bugs_dir.glob("*.md")):
            stato = _campo(_leggi(p), "Stato").split("|")[0].strip()
            if stato != "verificato":
                bug_aperti.append({"file": p.name, "stato": stato or "n/d"})
    mappa = (radice / "docs" / "system" / "mappa.md").is_file()
    codice = ha_codice(radice)
    return {"infra": infra, "codice_esistente": codice, "mappa": mappa, "specs": specs,
            "bug_aperti": bug_aperti, "prossimo": prossimo(infra, codice, mappa, specs)}


def prossimo(infra: dict, codice: bool, mappa: bool, specs: list[dict]) -> dict:
    if not (infra["AGENTS.md"] and infra["scripts/verify.py"]):
        return {"skill": "sdlc-init", "motivo": "mancano AGENTS.md e/o scripts/verify.py"}
    attive = [s for s in specs if s["stato"] not in ("implemented", "superseded")]
    if codice and not mappa and not specs:
        return {"skill": "sdlc-map-codebase", "motivo": "codice esistente senza docs/system/mappa.md (brownfield)"}
    if not attive:
        return {"skill": "sdlc-spec", "motivo": "nessuna spec attiva: parti da una nuova"}
    s = attive[0]
    i = s["id"]
    if not s["spec"] or s["stato"] == "draft" or not s["spec_approvata"]:
        return {"skill": "sdlc-spec", "spec": i, "motivo": "spec da completare e far approvare"}
    if not s["plan"] or not s["plan_approvato"]:
        return {"skill": "sdlc-plan", "spec": i, "motivo": "piano mancante o da approvare"}
    if not s["tasks"]:
        return {"skill": "sdlc-tasks", "spec": i, "motivo": "task mancanti"}
    if s["task_numerate_aperte"]:
        return {"skill": "sdlc-implement", "spec": i,
                "motivo": f"task T-nn aperte: {s['task_numerate_aperte']}, prossima {s['prossima_task']} "
                          "(per molte task indipendenti valuta sdlc-loop)"}
    if not s["review_valida"]:
        return {"skill": "sdlc-review-diff", "spec": i, "motivo": "task T-nn completate: manca la review valida (review.md)"}
    if s["review"] == "non conforme":
        return {"skill": "sdlc-implement", "spec": i, "motivo": "review 'non conforme': correggi i problemi trovati, poi ripeti la review"}
    if s["doc_aperta"]:
        return {"skill": "sdlc-docs", "spec": i, "motivo": "T-DOC aperta"}
    return {"skill": "sdlc-sync", "spec": i, "motivo": "riconcilia spec e docs/system (T-SYNC) e imposta Stato = implemented"}


def stampa(st: dict) -> None:
    print("INFRASTRUTTURA")
    for k, v in st["infra"].items():
        print(f"  [{'x' if v else ' '}] {k}")
    print(f"CODICE ESISTENTE: {'si' if st['codice_esistente'] else 'no'}; MAPPA (docs/system/mappa.md): {'si' if st['mappa'] else 'no'}")
    print("SPEC")
    if not st["specs"]:
        print("  (nessuna)")
    for s in st["specs"]:
        piano = "approvato" if s["plan_approvato"] else ("da approvare" if s["plan"] else "no")
        print(f"  {s['id']}: stato={s['stato']} approvata={'si' if s['spec_approvata'] else 'no'} piano={piano} "
              f"task={s['task_chiuse']}/{s['task_totali']} review={s['review'] or 'no'}")
    if st["bug_aperti"]:
        print("BUG NON VERIFICATI: " + ", ".join(f"{b['file']} ({b['stato']})" for b in st["bug_aperti"]) + "  -> sdlc-bugfix")
    p = st["prossimo"]
    print(f"PROSSIMO: {p['skill']}{' su ' + p['spec'] if 'spec' in p else ''} - {p['motivo']}")


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    st = analizza(Path(args[0]) if args else Path("."))
    print(json.dumps(st, ensure_ascii=False, indent=2)) if "--json" in argv else stampa(st)
    return 0


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
