#!/usr/bin/env python3
# sdlc-playbook: 0.11.1
"""Stato del progetto secondo il playbook e prossima fase suggerita.

Uso:  python scripts/state.py [--json] [--spec <id>] [radice]
Sola lettura. Il suggerimento segue il flusso del playbook: init -> (map-codebase) -> spec -> plan ->
tasks -> implement -> review-diff -> docs -> sync. Bug aperti e sdlc-loop sono segnalati a parte.
Con più spec attive ognuna ha il suo passo successivo; la riga PROSSIMO riguarda la spec indicata con --spec, quella
il cui nome di cartella compare nel branch corrente, o l'unica attiva. Altrimenti chiede di scegliere.
Livelli (playbook §2): una spec S salta piano e review.md; una spec L richiede anche la revisione umana del diff
("- Revisione umana del diff:" in review.md). Nei livelli M e L i test bloccati di una task "atteso: rosso" chiusa
vanno approvati dall'umano ("test approvati:" sulla riga della task) prima di proseguire.
Solo stdlib (+ git per il nome del branch, se c'è), cross-platform.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # niente __pycache__ nel progetto: altrimenti conterebbe come file modificato
sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_lint  # noqa: E402

PLACEHOLDER = re.compile(r"<[^<>\n]{1,100}>")
ESITI = ("conforme", "conforme con riserve", "non conforme")
SORGENTI = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".cs", ".go", ".rb", ".php", ".rs", ".c", ".cpp", ".swift"}
IGNORA = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", "bin", "obj",
          "scripts", "docs", ".github", ".vscode"}
CONCLUSE = ("implemented", "superseded")


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


def branch_corrente(radice: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(radice), "branch", "--show-current"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def analizza_spec(d: Path) -> dict:
    spec, plan, tasks, review = (_leggi(d / n) for n in ("spec.md", "plan.md", "tasks.md", "review.md"))
    aperte = re.findall(r"^\s*-\s+\[ \]\s+(T-[A-Z0-9]+)", tasks, re.M)
    chiuse = re.findall(r"^\s*-\s+\[[xX]\]\s+(T-[A-Z0-9]+)", tasks, re.M)
    numerate = [t for t in aperte if re.fullmatch(r"T-R?\d+", t)]
    spec_firmata = _compilato(spec, "Approvata da / data")
    plan_firmato = _compilato(plan, "Approvato da / data")
    stato = (_campo(spec, "Stato").split("|")[0].strip() if spec else "") or "n/d"
    spec_decaduta = stato != "in-revisione" and spec_firmata and bool(spec_lint.problemi_hash(spec, "Spec"))
    plan_decaduto = plan_firmato and bool(spec_lint.approvazione_piano(spec, plan))
    base_task = _campo(tasks, "Basato su piano")
    sid = spec_lint.id_spec(spec)
    return {
        "id": d.name,
        "id_titolo": f"SPEC-{sid}" if sid else None,
        "spec": bool(spec),
        "stato": stato,
        "livello": spec_lint.livello(spec),
        "spec_approvata": spec_firmata and not spec_decaduta and stato != "in-revisione",
        "spec_approvazione_decaduta": spec_decaduta,
        "plan": bool(plan),
        "plan_approvato": plan_firmato and not plan_decaduto,
        "plan_approvazione_decaduta": plan_decaduto,
        "tasks": bool(tasks),
        "tasks_su_altro_piano": bool(plan and base_task and not PLACEHOLDER.search(base_task)
                                     and base_task != spec_lint.impronta(plan)),
        "task_chiuse": len(chiuse),
        "task_totali": len(chiuse) + len(aperte),
        "task_numerate_aperte": len(numerate),
        "prossima_task": numerate[0] if numerate else None,
        "test_da_approvare": spec_lint.test_da_approvare(tasks),
        "task_review": len([t for t in aperte + chiuse if t.startswith("T-R")]),
        "doc_aperta": "T-DOC" in aperte,
        "sync_aperta": "T-SYNC" in aperte,
        "review": _campo(review, "Esito") if review else None,
        "review_valida": _campo(review, "Esito") in ESITI if review else False,
        "revisione_umana": _compilato(review, "Revisione umana del diff"),
    }


def prossimo_della_spec(s: dict) -> dict:
    i = s["id"]
    if s["stato"] == "in-revisione":
        return {"skill": "sdlc-spec", "spec": i,
                "motivo": "spec in revisione: completa le modifiche (sezione Revisioni) e falla riapprovare"}
    if s["spec_approvazione_decaduta"]:
        return {"skill": "sdlc-spec", "spec": i, "motivo": "approvazione della spec senza Hash valido (mancante o contenuto cambiato): va riapprovata"}
    if not s["spec"] or s["stato"] == "draft" or not s["spec_approvata"]:
        return {"skill": "sdlc-spec", "spec": i, "motivo": "spec da completare e far approvare"}
    if s["livello"] == "S":
        return prossimo_livello_s(s)
    if s["plan_approvazione_decaduta"]:
        return {"skill": "sdlc-plan", "spec": i,
                "motivo": "approvazione del piano non valida (Hash mancante o cambiato, o spec diversa): va riapprovato"}
    if not s["plan"] or not s["plan_approvato"]:
        return {"skill": "sdlc-plan", "spec": i, "motivo": "piano mancante o da approvare"}
    if not s["tasks"]:
        return {"skill": "sdlc-tasks", "spec": i, "motivo": "task mancanti"}
    if s["tasks_su_altro_piano"]:
        return {"skill": "sdlc-tasks", "spec": i, "motivo": "task basate su un'altra versione del piano: rivedile"}
    if s["test_da_approvare"]:
        return {"skill": "sdlc-tests-from-ac", "spec": i,
                "motivo": f"test bloccati di {', '.join(s['test_da_approvare'])} da far approvare all'umano "
                          "('test approvati:' sulla riga della task) prima dell'implementazione"}
    if s["task_numerate_aperte"]:
        return {"skill": "sdlc-implement", "spec": i,
                "motivo": f"task aperte: {s['task_numerate_aperte']}, prossima {s['prossima_task']} "
                          "(per molte task indipendenti valuta sdlc-loop)"}
    if not s["review_valida"]:
        return {"skill": "sdlc-review-diff", "spec": i, "motivo": "task T-nn completate: manca la review valida (review.md)"}
    if s["review"] == "non conforme":
        return review_non_conforme(s)
    if s["livello"] == "L" and not s["revisione_umana"]:
        return {"skill": "sdlc-review-diff", "spec": i,
                "motivo": "livello L: manca la revisione umana del diff ('Revisione umana del diff' in review.md)"}
    return chiusura(s)


def review_non_conforme(s: dict) -> dict:
    if s["task_review"]:
        return {"skill": "sdlc-review-diff", "spec": s["id"], "motivo": "correzioni T-R completate: ripeti la review"}
    return {"skill": "sdlc-review-diff", "spec": s["id"],
            "motivo": "review 'non conforme': trasforma i problemi in task T-R in tasks.md"}


def chiusura(s: dict) -> dict:
    if s["doc_aperta"]:
        return {"skill": "sdlc-docs", "spec": s["id"], "motivo": "T-DOC aperta"}
    return {"skill": "sdlc-sync", "spec": s["id"],
            "motivo": "riconcilia spec e docs/system (T-SYNC) e imposta Stato = implemented"}


def prossimo_livello_s(s: dict) -> dict:
    """Livello S: niente piano; la review è quella della PR, review.md conta solo se c'è."""
    i = s["id"]
    if not s["tasks"]:
        return {"skill": "sdlc-tasks", "spec": i, "motivo": "livello S: task minime, senza piano"}
    if s["task_numerate_aperte"]:
        return {"skill": "sdlc-implement", "spec": i,
                "motivo": f"task aperte: {s['task_numerate_aperte']}, prossima {s['prossima_task']}"}
    if s["review"] == "non conforme":
        return review_non_conforme(s)
    return chiusura(s)


def scegli_spec(attive: list[dict], scelta: str | None, branch: str) -> dict | None:
    if scelta:
        k = spec_lint.chiave_id(scelta[5:] if scelta.startswith("SPEC-") else scelta)
        for s in attive:
            titolo = s["id_titolo"][5:] if s["id_titolo"] else ""
            if scelta == s["id"] or (titolo and spec_lint.chiave_id(titolo) == k):
                return s
        return None
    nel_branch = [s for s in attive if s["id"].lower() in branch.lower()] if branch else []
    if nel_branch:
        return max(nel_branch, key=lambda s: len(s["id"]))
    return attive[0] if len(attive) == 1 else None


def analizza(radice: Path, scelta: str | None = None) -> dict:
    infra = {
        "AGENTS.md": (radice / "AGENTS.md").is_file(),
        "scripts/verify.py": (radice / "scripts" / "verify.py").is_file(),
        "scripts/spec_lint.py": (radice / "scripts" / "spec_lint.py").is_file(),
        "ci": any((radice / ".github" / "workflows").glob("*.y*ml")) if (radice / ".github" / "workflows").is_dir() else False,
        "docs/": (radice / "docs").is_dir(),
    }
    base = radice / "docs" / "specs"
    specs = [analizza_spec(d) for d in sorted(p for p in base.glob("*") if p.is_dir())] if base.is_dir() else []
    for s in specs:
        if s["stato"] not in CONCLUSE:
            s["prossimo"] = prossimo_della_spec(s)
    bugs_dir = radice / "docs" / "bugs"
    bug_aperti = []
    if bugs_dir.is_dir():
        for p in sorted(bugs_dir.glob("*.md")):
            stato = _campo(_leggi(p), "Stato").split("|")[0].strip()
            if stato != "verificato":
                bug_aperti.append({"file": p.name, "stato": stato or "n/d"})
    mappa = (radice / "docs" / "system" / "mappa.md").is_file()
    codice = ha_codice(radice)
    branch = branch_corrente(radice)
    return {"infra": infra, "codice_esistente": codice, "mappa": mappa, "branch": branch, "specs": specs,
            "bug_aperti": bug_aperti, "prossimo": prossimo(infra, codice, mappa, specs, scelta, branch)}


def prossimo(infra: dict, codice: bool, mappa: bool, specs: list[dict], scelta: str | None = None,
             branch: str = "") -> dict:
    if not (infra["AGENTS.md"] and infra["scripts/verify.py"]):
        return {"skill": "sdlc-init", "motivo": "mancano AGENTS.md e/o scripts/verify.py"}
    attive = [s for s in specs if s["stato"] not in CONCLUSE]
    if codice and not mappa and not specs:
        return {"skill": "sdlc-map-codebase", "motivo": "codice esistente senza docs/system/mappa.md (brownfield)"}
    if not attive:
        return {"skill": "sdlc-spec", "motivo": "nessuna spec attiva: parti da una nuova"}
    s = scegli_spec(attive, scelta, branch)
    if s is None and scelta:
        return {"skill": "scegli", "motivo": f"nessuna spec attiva corrisponde a '{scelta}'"}
    if s is None:
        elenco = ", ".join(f"{a['id']} ({a['prossimo']['skill']})" for a in attive)
        return {"skill": "scegli", "motivo": f"{len(attive)} spec attive e nessuna nel nome del branch: {elenco}. "
                                             "Passa al branch della spec o usa --spec <id>"}
    return s["prossimo"]


def stampa(st: dict) -> None:
    print("INFRASTRUTTURA")
    for k, v in st["infra"].items():
        print(f"  [{'x' if v else ' '}] {k}")
    print(f"CODICE ESISTENTE: {'si' if st['codice_esistente'] else 'no'}; MAPPA (docs/system/mappa.md): {'si' if st['mappa'] else 'no'}")
    if st["branch"]:
        print(f"BRANCH: {st['branch']}")
    print("SPEC")
    if not st["specs"]:
        print("  (nessuna)")
    for s in st["specs"]:
        piano = "approvato" if s["plan_approvato"] else ("da approvare" if s["plan"] else "no")
        dopo = f" -> {s['prossimo']['skill']}" if "prossimo" in s else ""
        print(f"  {s['id']}: livello={s['livello']} stato={s['stato']} approvata={'si' if s['spec_approvata'] else 'no'} piano={piano} "
              f"task={s['task_chiuse']}/{s['task_totali']} review={s['review'] or 'no'}{dopo}")
    if st["bug_aperti"]:
        print("BUG NON VERIFICATI: " + ", ".join(f"{b['file']} ({b['stato']})" for b in st["bug_aperti"]) + "  -> sdlc-bugfix")
    p = st["prossimo"]
    print(f"PROSSIMO: {p['skill']}{' su ' + p['spec'] if 'spec' in p else ''} - {p['motivo']}")


def main(argv: list[str]) -> int:
    scelta = argv[argv.index("--spec") + 1] if "--spec" in argv and argv.index("--spec") + 1 < len(argv) else None
    args = [a for a in argv if not a.startswith("--") and a != scelta]
    st = analizza(Path(args[0]) if args else Path("."), scelta)
    print(json.dumps(st, ensure_ascii=False, indent=2)) if "--json" in argv else stampa(st)
    return 0


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
