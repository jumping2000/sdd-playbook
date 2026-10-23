#!/usr/bin/env python3
"""Controllo di chiusura di una feature: spec, task, review, pagina d'area e tracciabilità allineate.

Uso:
  python scripts/sync_check.py docs/specs/001-x [--area docs/system/<area>.md] [--tests DIR ...] [--junit FILE ...]

Verifica:
  1. spec valida e con Stato = implemented
  2. nessuna task aperta in tasks.md
  3. review.md presente con Esito valido, diverso da "non conforme", e con la decisione umana compilata
  4. pagina d'area (--area, o la prima in docs/system/ che cita la spec) con le sezioni richieste,
     "Ultimo allineamento" compilato e la spec tra le "Specifiche collegate"
  5. ogni AC citato in almeno un test di questa spec (trace_check: ID qualificati SPEC-nnn/AC-nnn)
Livelli (playbook §2): S non richiede review.md (la review è quella della PR) né la pagina d'area; L richiede in
review.md anche "- Revisione umana del diff:" compilato. Nei livelli M e L le task di test chiuse riportano
"test approvati:". Con --junit FILE|DIR gli AC devono essere verificati dal report dei test eseguiti (vedi
trace_check); nel livello L il report è obbligatorio.
Exit code: 0 allineato; 1 errori; 2 uso errato. Solo stdlib, cross-platform.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_lint  # noqa: E402
import trace_check  # noqa: E402

PLACEHOLDER = re.compile(r"<[^<>\n]{1,100}>")
ESITI = ("conforme", "conforme con riserve", "non conforme")
SEZIONI_AREA = ("Comportamento attuale", "Vincoli e punti delicati", "Test di caratterizzazione")


def campo(testo: str, nome: str) -> str:
    m = re.search(rf"^\s*[-*]\s+{re.escape(nome)}\s*:\s*(.*)$", testo, re.M)
    return re.sub(r"<!--.*?-->", "", m.group(1)).strip() if m else ""


def id_spec(spec: str, feature: Path) -> str:
    sid = spec_lint.id_spec(spec)
    return f"SPEC-{sid}" if sid else feature.name


def cita(testo: str, spec_id: str) -> bool:
    """Il testo cita esattamente questa spec (SPEC-2026-10-24-x non vale per SPEC-2026-10-24-x-y)."""
    chiave = spec_lint.chiave_id(spec_id[5:] if spec_id.startswith("SPEC-") else spec_id)
    return chiave in {spec_lint.chiave_id(n) for n in trace_check.SPEC_REF.findall(testo)}


def trova_area(feature: Path, spec_id: str, esplicita: str | None) -> Path | None:
    if esplicita:
        return Path(esplicita) if Path(esplicita).is_file() else None
    for p in sorted(Path("docs/system").glob("*.md")) if Path("docs/system").is_dir() else []:
        if p.name != "mappa.md" and cita(p.read_text(encoding="utf-8"), spec_id):
            return p
    return None


def controlla(feature: Path, area_arg: str | None, tests: list[Path], junit: list[str] | None = None) -> list[str]:
    err: list[str] = []
    spec_p = feature / "spec.md"
    if not spec_p.is_file():
        return [f"{spec_p.as_posix()} non trovato"]
    spec = spec_p.read_text(encoding="utf-8")
    spec_id = id_spec(spec, feature)
    livello = spec_lint.livello(spec)

    e, _ = spec_lint.lint_spec(spec, feature.resolve().name)
    err += [f"spec: {x}" for x in e]
    stato = spec_lint.pulisci(spec_lint.campo(spec, "Stato")).split("|")[0].strip()
    if stato != "implemented":
        err.append(f"spec: Stato è '{stato}', atteso 'implemented'")

    tasks_p = feature / "tasks.md"
    if tasks_p.is_file():
        aperte = re.findall(r"^\s*-\s+\[ \]\s+(T-[A-Z0-9]+)", tasks_p.read_text(encoding="utf-8"), re.M)
        if aperte:
            err.append("task ancora aperte: " + ", ".join(aperte))
        senza = spec_lint.test_da_approvare(tasks_p.read_text(encoding="utf-8")) if livello != "S" else []
        if senza:
            err.append(f"test bloccati senza approvazione umana ('test approvati:'): {', '.join(senza)}")
    else:
        err.append("tasks.md non trovato")

    rev_p = feature / "review.md"
    if not rev_p.is_file():
        if livello != "S":
            err.append("review.md mancante (esegui sdlc-review-diff)")
    else:
        esito = campo(rev_p.read_text(encoding="utf-8"), "Esito")
        if esito not in ESITI:
            err.append(f"review.md: Esito non valido '{esito}' (atteso: {', '.join(ESITI)})")
        elif esito == "non conforme":
            err.append("review.md: Esito 'non conforme'")
        dec = campo(rev_p.read_text(encoding="utf-8"), "Decisione di")
        if not dec or PLACEHOLDER.search(dec):
            err.append("review.md: 'Decisione di' non compilata (la decisione sulla review è dell'umano)")
        umana = campo(rev_p.read_text(encoding="utf-8"), "Revisione umana del diff")
        if livello == "L" and (not umana or PLACEHOLDER.search(umana)):
            err.append("review.md: livello L senza 'Revisione umana del diff' (chi ha riletto il diff, e quando)")

    area = trova_area(feature, spec_id, area_arg)
    if area is None and livello == "S":
        pass  # livello S: la pagina d'area è facoltativa
    elif area is None:
        err.append(f"nessuna pagina d'area in docs/system/ che citi {spec_id} (usa --area)")
    else:
        t = area.read_text(encoding="utf-8")
        for s in SEZIONI_AREA:
            if not re.search(rf"^##\s+{re.escape(s)}\s*$", t, re.M):
                err.append(f"{area.as_posix()}: sezione mancante '## {s}'")
        agg = campo(t, "Ultimo allineamento")
        if not agg or PLACEHOLDER.search(agg):
            err.append(f"{area.as_posix()}: 'Ultimo allineamento' non compilato")
        if not cita(campo(t, "Specifiche collegate"), spec_id):
            err.append(f"{area.as_posix()}: {spec_id} non è tra le 'Specifiche collegate'")

    cartelle = [d for d in (tests or [Path(c) for c in trace_check.CARTELLE]) if d.is_dir()]
    if not cartelle:
        err.append("nessuna cartella di test trovata (usa --tests)")
    else:
        esito = trace_check.analizza(spec, cartelle)
        if esito.senza:
            nota = (f" ({len(esito.ambigui)} citazioni ambigue: usa {spec_id}/AC-nnn o dichiara la spec nel file)"
                    if esito.ambigui else "")
            err.append("AC senza test: " + ", ".join(esito.senza) + nota)
        if junit:
            try:
                eseguiti = trace_check.esecuzioni(spec, cartelle, trace_check.file_report(junit))
            except ValueError as e:
                return err + [str(e)]
            ko = [ac for ac, x in eseguiti.items() if x["fallito"] or not x["passato"]]
            if ko:
                err.append("AC non verificati dal report dei test eseguiti (falliti o non eseguiti): " + ", ".join(ko))
    if livello == "L" and not junit:
        err.append("livello L: serve il report dei test eseguiti (--junit)")
    return err


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    area = argv[argv.index("--area") + 1] if "--area" in argv else None
    tests = [Path(t) for t in trace_check.valori(argv, "--tests")]
    junit = trace_check.valori(argv, "--junit")
    args = [a for a in args if a != area and a not in junit and Path(a) not in tests]
    feature = Path(args[0])
    err = controlla(feature, area, tests, junit)
    for e in err:
        print(f"[ERRORE] {e}")
    print("SYNC: " + ("OK" if not err else f"{len(err)} errori"))
    return 1 if err else 0


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
