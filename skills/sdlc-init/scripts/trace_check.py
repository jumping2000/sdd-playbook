#!/usr/bin/env python3
# sdlc-playbook: 0.12.0
"""Tracciabilità AC -> test: ogni acceptance criterion della spec deve comparire in almeno un test.

Uso:
  python scripts/trace_check.py docs/specs/2026-10-24-export-csv/spec.md
  python scripts/trace_check.py docs/specs/2026-10-24-export-csv/spec.md --tests tests integration
  python scripts/trace_check.py docs/specs/2026-10-24-export-csv/spec.md --warn-only
  python scripts/trace_check.py docs/specs/2026-10-24-export-csv/spec.md --junit reports/junit.xml

Gli AC ripartono da AC-001 in ogni spec, quindi una citazione vale per una spec precisa:
  1. qualificata: SPEC-2026-10-24-export-csv/AC-001 (nei nomi di funzione SPEC_2026_10_24_export_csv_AC_001;
     per i vecchi ID anche SPEC-002-AC-001, SPEC002_AC001) -> vale per quella spec;
  2. breve (AC-001, AC_001, AC001) in un file che nomina una sola spec (es. "# SPEC-2026-10-24-export-csv" in
     testa) -> vale per quella. È il modo consigliato con gli ID con data;
  3. breve in un file che non nomina spec -> vale solo se il progetto ha una sola spec in docs/specs/; altrimenti è
     ambigua, non conta ed è segnalata.
Le citazioni su righe con TODO, FIXME o XXX non contano: un promemoria non è un test.
--junit FILE|DIR ...: report JUnit XML dei test eseguiti (una cartella vale per tutti i suoi *.xml). Ogni AC deve
avere almeno un caso di test eseguito e passato, e nessuno fallito: citare l'AC non basta più. Un caso vale per un AC
se lo cita in forma qualificata (nome o classname), oppure in forma breve quando appartiene a un file di test
attribuito alla spec o il progetto ha una sola spec. Il file di un caso è quello il cui percorso coincide più a lungo
con l'attributo file o con il classname (tests.a.test_api -> tests/a/test_api.py; com.acme.ExportTest ->
.../com/acme/ExportTest.java); a pari merito tra file di spec diverse il caso non conta. I casi saltati non contano.
L'ID della spec si legge dal titolo "# SPEC-<id>: ..." (data + slug in minuscolo, o numero).
Cartelle di test cercate di default: tests, test, __tests__, spec, src/test.
Exit code: 0 tutti gli AC citati (e, con --junit, verificati); 1 AC senza test; 2 uso errato o report illeggibile.
Solo stdlib, cross-platform.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NamedTuple

sys.dont_write_bytecode = True  # niente __pycache__ nel progetto: altrimenti conterebbe come file modificato
sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_lint  # noqa: E402

ESTENSIONI = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".cs", ".go", ".rb", ".php",
              ".rs", ".feature", ".robot", ".cpp", ".c", ".swift"}
CARTELLE = ("tests", "test", "__tests__", "spec", "src/test")
SALTA = {"node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build", "target", "bin", "obj"}
AC_REF = re.compile(r"(?:(?<=Test)|(?<![A-Za-z0-9]))AC[-_]?0*(\d+)(?!\d)")  # anche TestAC001 (Go)
# ID della spec: data + slug in minuscolo (anche con "_" al posto di "-", per i nomi di funzione) o numero.
ID_RIF = r"(\d{4}[-_]\d{2}[-_]\d{2}[-_][a-z0-9]+(?:[-_][a-z0-9]+)*|\d+)"
SPEC_REF = re.compile(rf"(?<![A-Za-z0-9])SPEC[-_]?{ID_RIF}(?!\d)")
QUALIFICATO = re.compile(rf"(?<![A-Za-z0-9])SPEC[-_]?{ID_RIF}[-_/:. ]{{0,3}}AC[-_]?0*(\d+)(?!\d)")
PROMEMORIA = re.compile(r"\b(TODO|FIXME|XXX)\b")


class Esito(NamedTuple):
    acs: dict[str, list[str]]
    coperti: dict[str, list[str]]
    senza: list[str]
    orfani: list[int]
    req_coperti: dict[str, bool]
    ambigui: list[str]
    ignorati: list[str]


def chiave_spec(spec_text: str) -> str | None:
    """Chiave dell'ID della spec letto dal titolo (forma normalizzata, vedi spec_lint.chiave_id)."""
    sid = spec_lint.id_spec(spec_text)
    return spec_lint.chiave_id(sid) if sid else None


def spec_nel_progetto() -> int:
    base = Path("docs/specs")
    return sum(1 for p in base.glob("*/spec.md")) if base.is_dir() else 0


def file_di_test(cartelle: list[Path]):
    for base in cartelle:
        for f in sorted(base.rglob("*")):
            if f.is_file() and f.suffix in ESTENSIONI and not SALTA & set(f.parts):
                yield f


def brevi_nel_file(testo: str, spec: str | None, spec_unica: bool) -> str:
    """Come contano le citazioni brevi in un file: "valide", "ambigue" o "altrui"."""
    dichiarate = {spec_lint.chiave_id(n) for n in SPEC_REF.findall(testo)}
    if spec is not None and dichiarate == {spec}:
        return "valide"
    if not dichiarate:
        return "valide" if spec_unica else "ambigue"
    if spec in dichiarate:
        return "ambigue"  # il file nomina più spec: una citazione breve non dice di quale
    return "altrui"  # il file appartiene ad altre spec


def raccogli(cartelle: list[Path], spec: str | None, spec_unica: bool):
    """(numero AC -> posizioni per la spec indicata, citazioni ambigue, citazioni ignorate perché promemoria)."""
    trovati: dict[int, list[str]] = {}
    ambigui: list[str] = []
    ignorati: list[str] = []
    for f in file_di_test(cartelle):
        testo = f.read_text(encoding="utf-8", errors="ignore")
        brevi = brevi_nel_file(testo, spec, spec_unica)
        for n, riga in enumerate(testo.splitlines(), 1):
            pos = f"{f.as_posix()}:{n}"
            if not (QUALIFICATO.search(riga) or AC_REF.search(riga)):
                continue
            if PROMEMORIA.search(riga):
                ignorati.append(pos)
                continue
            for m in QUALIFICATO.finditer(riga):
                if spec_lint.chiave_id(m.group(1)) == spec:
                    trovati.setdefault(int(m.group(2)), []).append(pos)
            for m in AC_REF.finditer(QUALIFICATO.sub(" ", riga)):
                if brevi == "valide":
                    trovati.setdefault(int(m.group(1)), []).append(pos)
                elif brevi == "ambigue":
                    ambigui.append(pos)
    return trovati, ambigui, ignorati


def analizza(spec_text: str, cartelle: list[Path], spec_unica: bool | None = None) -> Esito:
    _, acs = spec_lint.parse_spec(spec_text)
    unica = spec_nel_progetto() <= 1 if spec_unica is None else spec_unica
    trovati, ambigui, ignorati = raccogli(cartelle, chiave_spec(spec_text), unica)
    coperti = {ac: trovati.get(int(ac[3:]), []) for ac in acs}
    senza = [ac for ac, pos in coperti.items() if not pos]
    numeri = {int(a[3:]) for a in acs}
    orfani = sorted(n for n in trovati if n not in numeri)
    req_coperti: dict[str, bool] = {}
    for ac, refs in acs.items():
        for r in refs:
            req_coperti[r] = req_coperti.get(r, False) or bool(coperti[ac])
    return Esito(acs, coperti, senza, orfani, req_coperti, ambigui, ignorati)


def file_report(percorsi: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in map(Path, percorsi):
        out += sorted(p.rglob("*.xml")) if p.is_dir() else [p]
    return out


def casi_junit(report: list[Path]) -> list[tuple[str, str, str, str]]:
    """(nome, classname, file, esito) di ogni testcase; esito: passato, fallito o saltato. ValueError se illeggibile."""
    casi = []
    for f in report:
        try:
            radice = ET.parse(f).getroot()
        except (ET.ParseError, OSError) as e:
            raise ValueError(f"report JUnit illeggibile: {f.as_posix()} ({e})") from e
        for c in radice.iter("testcase"):
            figli = {x.tag for x in c}
            esito = "fallito" if figli & {"failure", "error"} else "saltato" if "skipped" in figli else "passato"
            casi.append((c.get("name", ""), c.get("classname", ""), c.get("file", ""), esito))
    return casi


def componenti(percorso: str) -> list[str]:
    return [c for c in re.split(r"[./:\\]+", percorso) if c]


def coincidenza(file_test: str, file: str, classe: str) -> int:
    """Quante parti del percorso del file di test coincidono con l'attributo file o con il classname del caso."""
    parti = componenti(file_test.rsplit(".", 1)[0])
    if file:
        f = componenti(file.replace("\\", "/").rsplit(".", 1)[0])
        n = next((k for k in range(min(len(f), len(parti)), 0, -1) if f[-k:] == parti[-k:]), 0)
        if n:
            return n
    c = componenti(classe)
    # il classname comincia con una coda del percorso (tests.a.test_api[.Classe], com.acme.ExportTest)
    return next((len(parti) - i for i in range(len(parti)) if c[:len(parti) - i] == parti[i:]), 0)


def file_del_caso(file: str, classe: str, validi: dict[str, bool]) -> bool:
    """Il caso appartiene a un file valido per la spec: il più coincidente, senza pari merito con file di altre spec."""
    punti = {f: coincidenza(f, file, classe) for f in validi}
    migliore = max(punti.values(), default=0)
    if not migliore:
        return False
    return all(validi[f] for f, n in punti.items() if n == migliore)


def esecuzioni(spec_text: str, cartelle: list[Path], report: list[Path],
               spec_unica: bool | None = None) -> dict[str, dict[str, list[str]]]:
    """AC -> {"passato": [...], "fallito": [...], "saltato": [...]} dai casi del report attribuiti a questa spec."""
    _, acs = spec_lint.parse_spec(spec_text)
    spec = chiave_spec(spec_text)
    unica = spec_nel_progetto() <= 1 if spec_unica is None else spec_unica
    validi = {f.as_posix(): brevi_nel_file(f.read_text(encoding="utf-8", errors="ignore"), spec, unica) == "valide"
              for f in file_di_test(cartelle)}
    out: dict[str, dict[str, list[str]]] = {ac: {"passato": [], "fallito": [], "saltato": []} for ac in acs}
    for nome, classe, file, esito in casi_junit(report):
        testo = f"{classe} {nome}"
        numeri = {int(m.group(2)) for m in QUALIFICATO.finditer(testo) if spec_lint.chiave_id(m.group(1)) == spec}
        if unica or file_del_caso(file, classe, validi):
            numeri |= {int(m.group(1)) for m in AC_REF.finditer(QUALIFICATO.sub(" ", testo))}
        for ac in acs:
            if int(ac[3:]) in numeri:
                out[ac][esito].append(f"{classe}::{nome}" if classe else nome)
    return out


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("--"):
        print(__doc__)
        return 2
    spec_path, opts = argv[0], argv[1:]
    warn_only = "--warn-only" in opts
    dirs = valori(opts, "--tests")
    junit = valori(opts, "--junit")
    if "--junit" in opts and not junit:
        print("[ERRORE] --junit senza report: indica il file o la cartella del report JUnit")
        return 2
    cartelle = [Path(d) for d in dirs] if dirs else [Path(c) for c in CARTELLE if Path(c).is_dir()]
    cartelle = [c for c in cartelle if c.is_dir()]
    if not cartelle:
        print("[ERRORE] nessuna cartella di test trovata: usa --tests <cartella>")
        return 2
    testo = Path(spec_path).read_text(encoding="utf-8")
    e = analizza(testo, cartelle)
    if chiave_spec(testo) is None:
        print("[WARN] la spec non ha un titolo '# SPEC-<id>: ...': valgono solo le citazioni brevi, e solo con una spec")
    for ac in e.acs:
        pos = e.coperti[ac]
        print(f"{ac}: " + (f"{len(pos)} riferimenti (es. {pos[0]})" if pos else "NESSUN TEST"))
    for req, ok in e.req_coperti.items():
        if not ok:
            print(f"[ERRORE] {req}: nessuno dei suoi AC ha test")
    if e.orfani:
        print("[WARN] AC attribuiti a questa spec nei test ma assenti dalla spec: "
              + ", ".join(f"AC-{n:03d}" for n in e.orfani))
    if e.ambigui:
        print(f"[WARN] {len(e.ambigui)} citazioni AC senza spec in file che non dichiarano una sola spec (es. "
              f"{', '.join(e.ambigui[:3])}): non contano. Usa SPEC-<id>/AC-nnn o dichiara la spec nel file")
    if e.ignorati:
        print(f"[WARN] {len(e.ignorati)} citazioni su righe TODO/FIXME/XXX ignorate (es. {', '.join(e.ignorati[:3])})")
    non_verificati: list[str] = []
    if junit:
        try:
            eseguiti = esecuzioni(testo, cartelle, file_report(junit))
        except ValueError as err:
            print(f"[ERRORE] {err}")
            return 2
        for ac, esiti in eseguiti.items():
            if esiti["fallito"]:
                print(f"[ERRORE] {ac}: test falliti nel report: {', '.join(esiti['fallito'][:3])}")
            elif not esiti["passato"]:
                print(f"[ERRORE] {ac}: nessun test eseguito e passato nel report"
                      + (f" ({len(esiti['saltato'])} saltati)" if esiti["saltato"] else ""))
            else:
                continue
            non_verificati.append(ac)
    ko = sorted(set(e.senza) | set(non_verificati))
    if not ko:
        print("TRACE: OK" + (" (verificato sul report dei test eseguiti)" if junit else ""))
    else:
        print(f"TRACE: {len(e.senza)} AC senza test" + (f": {', '.join(e.senza)}" if e.senza else "")
              + (f"; {len(non_verificati)} AC non verificati dal report: {', '.join(non_verificati)}" if junit else ""))
    return 0 if (not ko or warn_only) else 1


def valori(opts: list[str], nome: str) -> list[str]:
    """Argomenti che seguono l'opzione fino alla successiva."""
    out: list[str] = []
    if nome in opts:
        for o in opts[opts.index(nome) + 1:]:
            if o.startswith("--"):
                break
            out.append(o)
    return out


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
