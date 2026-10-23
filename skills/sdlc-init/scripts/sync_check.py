#!/usr/bin/env python3
"""Controllo di chiusura di una feature: spec, task, review, pagina d'area e tracciabilità allineate.

Uso:
  python scripts/sync_check.py docs/specs/001-x [--area docs/system/<area>.md] [--tests DIR ...]

Verifica:
  1. spec valida e con Stato = implemented
  2. nessuna task aperta in tasks.md
  3. review.md presente con Esito valido, diverso da "non conforme", e con la decisione umana compilata
  4. pagina d'area (--area, o la prima in docs/system/ che cita la spec) con le sezioni richieste,
     "Ultimo allineamento" compilato e la spec tra le "Specifiche collegate"
  5. ogni AC citato in almeno un test di questa spec (trace_check: ID qualificati SPEC-nnn/AC-nnn)
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
    m = re.search(r"^#\s+(SPEC-\d+)", spec, re.M)
    return m.group(1) if m else feature.name


def trova_area(feature: Path, spec_id: str, esplicita: str | None) -> Path | None:
    if esplicita:
        return Path(esplicita) if Path(esplicita).is_file() else None
    for p in sorted(Path("docs/system").glob("*.md")) if Path("docs/system").is_dir() else []:
        if p.name != "mappa.md" and spec_id in p.read_text(encoding="utf-8"):
            return p
    return None


def controlla(feature: Path, area_arg: str | None, tests: list[Path]) -> list[str]:
    err: list[str] = []
    spec_p = feature / "spec.md"
    if not spec_p.is_file():
        return [f"{spec_p.as_posix()} non trovato"]
    spec = spec_p.read_text(encoding="utf-8")
    spec_id = id_spec(spec, feature)

    e, _ = spec_lint.lint_spec(spec)
    err += [f"spec: {x}" for x in e]
    stato = spec_lint.pulisci(spec_lint.campo(spec, "Stato")).split("|")[0].strip()
    if stato != "implemented":
        err.append(f"spec: Stato è '{stato}', atteso 'implemented'")

    tasks_p = feature / "tasks.md"
    if tasks_p.is_file():
        aperte = re.findall(r"^\s*-\s+\[ \]\s+(T-[A-Z0-9]+)", tasks_p.read_text(encoding="utf-8"), re.M)
        if aperte:
            err.append("task ancora aperte: " + ", ".join(aperte))
    else:
        err.append("tasks.md non trovato")

    rev_p = feature / "review.md"
    if not rev_p.is_file():
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

    area = trova_area(feature, spec_id, area_arg)
    if area is None:
        err.append(f"nessuna pagina d'area in docs/system/ che citi {spec_id} (usa --area)")
    else:
        t = area.read_text(encoding="utf-8")
        for s in SEZIONI_AREA:
            if not re.search(rf"^##\s+{re.escape(s)}\s*$", t, re.M):
                err.append(f"{area.as_posix()}: sezione mancante '## {s}'")
        agg = campo(t, "Ultimo allineamento")
        if not agg or PLACEHOLDER.search(agg):
            err.append(f"{area.as_posix()}: 'Ultimo allineamento' non compilato")
        if spec_id not in campo(t, "Specifiche collegate"):
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
    return err


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    area = argv[argv.index("--area") + 1] if "--area" in argv else None
    tests: list[Path] = []
    if "--tests" in argv:
        for o in argv[argv.index("--tests") + 1:]:
            if o.startswith("--"):
                break
            tests.append(Path(o))
    feature = Path(args[0])
    if area and area in args:
        args.remove(area)
        feature = Path(args[0])
    err = controlla(feature, area, [t for t in tests if str(t) != args[0]])
    for e in err:
        print(f"[ERRORE] {e}")
    print("SYNC: " + ("OK" if not err else f"{len(err)} errori"))
    return 1 if err else 0


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
