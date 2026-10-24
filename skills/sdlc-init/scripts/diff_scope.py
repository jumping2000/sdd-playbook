#!/usr/bin/env python3
# sdlc-playbook: 0.11.1
"""Confronta i file modificati con il piano, con le zone vietate e con i test bloccati.

Uso:
  python scripts/diff_scope.py docs/specs/001-x [--base main] [--strict]

- Vietato: percorsi elencati in AGENTS.md alle righe "- Non modificare: a, b" -> errore (exit 1).
- Fuori piano: file modificati non elencati in plan.md ("Componenti e file da creare/modificare" e colonna
  "Dove" della "Strategia di test"), esclusi docs/specs/<questa spec>/, docs/system/, docs/bugs/, docs/adr/
  -> avviso (errore con --strict).
- Test bloccati: i file di test di un commit con trailer "Test-Lock: T-nn" (i test rossi scritti dagli AC)
  non possono cambiare in un commit successivo senza lo stesso trailer, né nelle modifiche non committate
  -> errore (exit 1). Una correzione voluta dei test va in un nuovo commit Test-Lock, motivata nella review.
- Test approvati: "test approvati: <nome, data, sha>" in tasks.md lega l'approvazione al commit Test-Lock sha; uno SHA
  che non è un commit Test-Lock del ramo per quella task, o un commit Test-Lock successivo per la stessa task, è un
  errore (exit 1): i test sono cambiati dopo l'approvazione e vanno riapprovati.
- Livello (playbook §2): il diff non deve superare il livello "- Livello:" della spec -> errore (exit 1).
  Richiede L un file nelle righe "- Aree sensibili: a, b" di AGENTS.md; richiede almeno M una modifica a un
  manifest o lockfile delle dipendenze, o più di 3 file di produzione (esclusi test, docs/, *.md e file generati come
  __pycache__/ e reports/). Una spec di livello S non ha piano: il confronto con il piano è saltato.
  AGENTS.md e il livello si leggono dal merge-base quando esistono lì: il ramo non può allentarli. Le voci di
  AGENTS.md valgono come percorsi (prima parola o testo tra backtick); le altre sono segnalate.
- Dipendenze (playbook §8): un manifest o lockfile modificato deve essere nel piano approvato (un lockfile vale se il
  piano elenca il suo manifest), oppure il diff deve aggiungere un ADR nuovo in docs/adr/ -> altrimenti errore.
- Pianificati ma non toccati: solo informativo.
Il diff è calcolato dal merge-base con --base (default: il primo tra main, master, origin/main,
origin/master) e include modifiche non committate e file non tracciati.
Exit code: 0 ok; 1 violazioni; 2 uso errato o git non utilizzabile. Solo stdlib + git.
"""
from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # niente __pycache__ nel progetto: altrimenti conterebbe come file modificato
sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_lint  # noqa: E402

SEMPRE_AMMESSI = ("docs/system/", "docs/bugs/", "docs/adr/")
PLACEHOLDER = re.compile(r"<[^<>\n]{1,100}>")
RIGA_PIANO = re.compile(r"^\s*[-*]\s+(?:`([^`]+)`|([^\s`:]+))")
TEST_LOCK = re.compile(r"^Test-Lock:\s*(\S+)", re.M)
RUMORE = re.compile(r"(^|/)(__pycache__|\.pytest_cache|reports)/|\.py[co]$")  # file generati dagli strumenti
LOCKFILE = {"package-lock.json": "package.json", "yarn.lock": "package.json", "pnpm-lock.yaml": "package.json",
            "uv.lock": "pyproject.toml", "poetry.lock": "pyproject.toml", "Pipfile.lock": "Pipfile", "go.sum": "go.mod",
            "Cargo.lock": "Cargo.toml", "Gemfile.lock": "Gemfile", "composer.lock": "composer.json"}
CARTELLE_TEST = {"tests", "test", "__tests__", "spec"}
NOME_TEST = re.compile(r"(^test_.*|.*_test|.*[._](test|spec)|.*Tests?)\.\w+$")
MANIFEST = {"package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "pyproject.toml", "uv.lock",
            "poetry.lock", "Pipfile", "Pipfile.lock", "setup.py", "setup.cfg", "go.mod", "go.sum", "Cargo.toml",
            "Cargo.lock", "pom.xml", "build.gradle", "build.gradle.kts", "packages.lock.json", "Directory.Packages.props",
            "Gemfile", "Gemfile.lock", "composer.json", "composer.lock"}
MANIFEST_GLOB = ("requirements*.txt", "*.csproj", "*.fsproj", "*.vbproj")
MAX_FILE_S = 3
ORDINE = {"S": 0, "M": 1, "L": 2}


def git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-c", "core.quotePath=false", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")  # quotePath: percorsi non ASCII così come sono
    return r.returncode, r.stdout.strip()


def normalizza(percorso: str) -> str:
    """Barre in avanti e senza il prefisso "./" (i punti iniziali di ".github/" restano)."""
    return re.sub(r"^(\./)+", "", percorso.replace("\\", "/").strip())


def corrisponde(percorso: str, pattern: str) -> bool:
    p, pat = normalizza(percorso), normalizza(pattern)
    if not pat:
        return False
    if any(c in pat for c in "*?["):
        return fnmatch.fnmatch(p, pat)
    return p == pat or p.startswith(pat.rstrip("/") + "/")


def sezioni(testo: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    corrente = None
    for r in testo.splitlines():
        if r.startswith("## "):
            corrente = r[3:].strip()
            out[corrente] = []
        elif corrente is not None:
            out[corrente].append(r)
    return out


def percorsi_dove(righe: list[str]) -> list[str]:
    """Percorsi della colonna "Dove" nella tabella della strategia di test."""
    out, colonna = [], None
    for r in righe:
        if not r.strip().startswith("|"):
            continue
        celle = [c.strip().strip("`").strip() for c in r.strip().strip("|").split("|")]
        if colonna is None:
            colonna = next((i for i, c in enumerate(celle) if c.lower() == "dove"), -1)
            continue
        if colonna < 0 or colonna >= len(celle) or set(celle[colonna]) <= set("-: "):
            continue
        v = celle[colonna].split("::")[0].strip()
        if v and not PLACEHOLDER.search(v) and " " not in v and ("/" in v or "." in v):
            out.append(v)
    return out


def percorsi_piano(plan: str) -> list[str]:
    out = []
    for titolo, righe in sezioni(plan).items():
        if titolo.startswith("Componenti e file"):
            for r in righe:
                m = RIGA_PIANO.match(r)
                if m:
                    v = (m.group(1) or m.group(2)).strip()
                    if v and not PLACEHOLDER.search(v):
                        out.append(v)
        elif titolo.startswith("Strategia di test"):
            out += percorsi_dove(righe)
    return list(dict.fromkeys(out))


def voci_grezze(agents: str, nome: str) -> list[str]:
    voci = []
    for m in re.finditer(rf"^\s*[-*]\s+{nome}\s*:\s*(.*)$", agents, re.M | re.I):
        voci += [v.strip() for v in re.split(r"[,;]", re.sub(r"<[^<>\n]*>", "", m.group(1)))]
    return [v for v in voci if v]


def percorso_voce(voce: str) -> str | None:
    """Percorso di una voce: testo tra backtick o prima parola, se ha l'aspetto di un percorso."""
    m = re.match(r"`([^`]+)`|(\S+)", voce)
    v = (m.group(1) or m.group(2)).strip() if m else ""
    return v if v and ("/" in v or "." in v or any(c in v for c in "*?[")) else None


def voci_agents(agents: str, nome: str) -> list[str]:
    """Percorsi di tutte le righe "- <nome>: a, b" di AGENTS.md (prima parola o testo tra backtick)."""
    return [p for v in voci_grezze(agents, nome) if (p := percorso_voce(v))]


def voci_non_percorsi(agents: str) -> list[str]:
    return [v for nome in ("Non modificare", "Aree sensibili") for v in voci_grezze(agents, nome)
            if percorso_voce(v) is None]


def percorsi_vietati(agents: str) -> list[str]:
    return voci_agents(agents, "Non modificare")


def e_un_manifest(percorso: str) -> bool:
    nome = normalizza(percorso).split("/")[-1]
    return nome in MANIFEST or any(fnmatch.fnmatch(nome, g) for g in MANIFEST_GLOB)


def di_produzione(percorso: str) -> bool:
    p = normalizza(percorso)
    return not (e_un_test(p) or p.startswith("docs/") or p.lower().endswith(".md") or RUMORE.search(p))


def livello_richiesto(modificati: list[str], agents: str) -> tuple[str, list[str]]:
    """Livello minimo che il diff richiede e i motivi (playbook §2)."""
    sensibili = voci_agents(agents, "Aree sensibili")
    toccati = [f for f in modificati if any(corrisponde(f, s) for s in sensibili)]
    if toccati:
        return "L", [f"area sensibile (AGENTS.md): {', '.join(toccati)}"]
    motivi = []
    manifest = [f for f in modificati if e_un_manifest(f)]
    if manifest:
        motivi.append(f"dipendenze modificate: {', '.join(manifest)}")
    produzione = [f for f in modificati if di_produzione(f)]
    if len(produzione) > MAX_FILE_S:
        motivi.append(f"{len(produzione)} file di produzione (S: al massimo {MAX_FILE_S})")
    return ("M" if motivi else "S"), motivi


def e_un_test(percorso: str) -> bool:
    parti = normalizza(percorso).split("/")
    return bool(CARTELLE_TEST & set(parti[:-1])) or bool(NOME_TEST.match(parti[-1]))


def base_ref(esplicita: str | None) -> str | None:
    for ref in ([esplicita] if esplicita else ["main", "master", "origin/main", "origin/master"]):
        if git("rev-parse", "--verify", "--quiet", ref)[0] == 0:
            return ref
    return None


def merge_base(base: str) -> str:
    code, mb = git("merge-base", "HEAD", base)
    if code != 0:
        raise RuntimeError("impossibile calcolare il merge-base")
    return mb


def non_tracciati() -> list[str]:
    _, nuovi = git("ls-files", "--others", "--exclude-standard")
    return [f for f in nuovi.splitlines() if f.strip() and not RUMORE.search(f)]


def non_committati() -> list[str]:
    _, diff = git("diff", "--name-only", "--no-renames", "HEAD")
    return [f for f in diff.splitlines() if f.strip()] + non_tracciati()


def file_modificati(mb: str) -> list[str]:
    """File toccati dal merge-base: --no-renames riporta anche il percorso di partenza di una rinomina."""
    _, diff = git("diff", "--name-only", "--no-renames", mb)
    return sorted({f for f in diff.splitlines() if f.strip()} | set(non_tracciati()))


def file_aggiunti(mb: str) -> list[str]:
    _, diff = git("diff", "--name-only", "--no-renames", "--diff-filter=A", mb)
    return [f for f in diff.splitlines() if f.strip()] + non_tracciati()


def da_base(mb: str, percorso: str) -> str | None:
    """Contenuto del file al merge-base, None se lì non esiste."""
    code, testo = git("show", f"{mb}:{normalizza(percorso)}")
    return testo if code == 0 else None


def commit_del_branch(mb: str) -> list[tuple[str, str | None, list[str]]]:
    """(sha, task del trailer Test-Lock o None, file toccati) dal più vecchio al più recente."""
    _, lista = git("rev-list", "--reverse", f"{mb}..HEAD")
    out = []
    for sha in lista.split():
        _, corpo = git("show", "-s", "--format=%B", sha)
        _, files = git("diff-tree", "--no-commit-id", "--name-only", "--no-renames", "-r", "--root", sha)
        m = TEST_LOCK.search(corpo)
        out.append((sha, m.group(1) if m else None, [f for f in files.splitlines() if f.strip()]))
    return out


def approvazioni_superate(commits: list[tuple[str, str | None, list[str]]], tasks: str) -> list[str]:
    """Approvazioni dei test che non corrispondono più all'ultimo commit Test-Lock della loro task."""
    err = []
    for tid, sha in spec_lint.approvazioni_test(tasks).items():
        if sha is None:
            continue
        pos = next((i for i, (c, lock, _) in enumerate(commits) if c.startswith(sha)), None)
        if pos is None or commits[pos][1] != tid:
            err.append(f"{tid}: lo SHA approvato {sha} non è un commit Test-Lock: {tid} di questo ramo (rebase o amend?)")
        elif any(lock == tid for _, lock, _ in commits[pos + 1:]):
            err.append(f"{tid}: nuovo commit Test-Lock dopo l'approvazione ({sha}): i test vanno riapprovati")
    return err


def test_bloccati(commits: list[tuple[str, bool, list[str]]], sporchi: list[str]):
    """Restituisce (file bloccati, violazioni, file non di test nei commit Test-Lock)."""
    bloccati: set[str] = set()
    violazioni, non_test = [], []
    for sha, lock, files in commits:
        if lock:
            for f in files:
                if e_un_test(f):
                    bloccati.add(f)
                else:
                    non_test.append(f"{f} ({sha[:7]})")
            continue
        violazioni += [f"{f} (commit {sha[:7]})" for f in files if f in bloccati]
    violazioni += [f"{f} (non committato)" for f in sporchi if f in bloccati]
    return sorted(bloccati), violazioni, non_test


def problemi_livello(feature: Path, modificati: list[str], agents: str, spec_base: str | None = None):
    """(livello dichiarato, errori se il diff richiede un livello più alto). Vale la spec al merge-base, se c'è."""
    spec = feature / "spec.md"
    testo = spec_base if spec_base is not None else (spec.read_text(encoding="utf-8") if spec.is_file() else "")
    dichiarato = spec_lint.livello(testo)
    richiesto, motivi = livello_richiesto(modificati, agents)
    if ORDINE[richiesto] > ORDINE[dichiarato]:
        return dichiarato, [f"livello sottostimato: la spec dichiara {dichiarato}, il diff richiede almeno "
                            f"{richiesto} ({'; '.join(motivi)}). Aggiorna il livello e fai riapprovare la spec"]
    return dichiarato, []


def adr_nuovi(aggiunti: list[str]) -> list[str]:
    return [f for f in aggiunti if normalizza(f).startswith("docs/adr/") and f.lower().endswith(".md")
            and not normalizza(f).split("/")[-1].lower().startswith(("readme", "index", "template"))]


def pianificato(f: str, piano: list[str]) -> bool:
    """Nel piano, o lockfile il cui manifest (nella stessa cartella) è nel piano."""
    if any(corrisponde(f, p) for p in piano):
        return True
    cartella, _, nome = normalizza(f).rpartition("/")
    manifest = LOCKFILE.get(nome)
    return bool(manifest) and any(corrisponde(f"{cartella}/{manifest}" if cartella else manifest, p) for p in piano)


def dipendenze_senza_decisione(modificati: list[str], piano: list[str], aggiunti: list[str] | None = None) -> list[str]:
    """Manifest modificati che il piano non elenca, se il diff non aggiunge un ADR."""
    if adr_nuovi(aggiunti or []):
        return []
    return [f for f in modificati if e_un_manifest(f) and not pianificato(f, piano)]


def analizza(feature: Path, modificati: list[str], agents: str):
    piano = percorsi_piano((feature / "plan.md").read_text(encoding="utf-8")) if (feature / "plan.md").is_file() else []
    vietati = percorsi_vietati(agents)
    ammessi = SEMPRE_AMMESSI + (f"docs/specs/{feature.name}/",)
    violazioni = [f for f in modificati if any(corrisponde(f, v) for v in vietati)]
    fuori = [f for f in modificati
             if f not in violazioni and not f.startswith(ammessi) and not any(corrisponde(f, p) for p in piano)]
    non_toccati = [p for p in piano if not any(corrisponde(f, p) for f in modificati)]
    return piano, violazioni, fuori, non_toccati


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    strict = "--strict" in argv
    base_arg = argv[argv.index("--base") + 1] if "--base" in argv else None
    if base_arg is not None and base_arg in args:
        args.remove(base_arg)
    feature = Path(args[0])
    if not feature.is_dir():
        print(f"[ERRORE] cartella non trovata: {feature}")
        return 2
    if git("rev-parse", "--is-inside-work-tree")[0] != 0:
        print("[ERRORE] non è un repository git")
        return 2
    base = base_ref(base_arg)
    if base is None:
        print("[ERRORE] nessun ref di base trovato: usa --base <ref>")
        return 2
    try:
        mb = merge_base(base)
    except RuntimeError as e:
        print(f"[ERRORE] {e}")
        return 2
    modificati = file_modificati(mb)
    agents = da_base(mb, "AGENTS.md")  # il ramo non può allentare zone vietate e aree sensibili
    if agents is None:
        agents = Path("AGENTS.md").read_text(encoding="utf-8") if Path("AGENTS.md").is_file() else ""
    piano, violazioni, fuori, non_toccati = analizza(feature, modificati, agents)
    livello, sottostimato = problemi_livello(feature, modificati, agents, da_base(mb, f"{feature.as_posix()}/spec.md"))
    if livello == "S" and not piano:
        fuori = []  # livello S: nessun piano con cui confrontare
    commits = commit_del_branch(mb)
    bloccati, test_toccati, non_test = test_bloccati(commits, non_committati())
    tasks_p = feature / "tasks.md"
    superate = approvazioni_superate(commits, tasks_p.read_text(encoding="utf-8")) if tasks_p.is_file() else []
    print(f"Base: {base}; livello: {livello}; file modificati: {len(modificati)}; percorsi nel piano: {len(piano)}; "
          f"test bloccati: {len(bloccati)}")
    if livello == "S" and not piano:
        print("[INFO] livello S senza piano: confronto con il piano saltato")
    elif not piano:
        print("[WARN] nessun percorso estratto da plan.md: il confronto con il piano non è affidabile")
    if "AGENTS.md" in modificati:
        print("[WARN] AGENTS.md modificato nel ramo: zone vietate e aree sensibili lette dalla versione di base")
    for v in voci_non_percorsi(agents):
        print(f"[WARN] voce di AGENTS.md che non sembra un percorso, ignorata: '{v}' (usa `percorso/` tra backtick)")
    for e in sottostimato:
        print(f"[ERRORE] {e}")
    dipendenze = dipendenze_senza_decisione(modificati, piano, file_aggiunti(mb))
    for f in dipendenze:
        print(f"[ERRORE] dipendenze modificate senza piano né ADR: {f} (nuove dipendenze solo nel piano approvato o "
              "con un ADR nuovo in docs/adr/)")
    for e in superate:
        print(f"[ERRORE] test approvati: {e}")
    for f in violazioni:
        print(f"[ERRORE] file in zona vietata (AGENTS.md): {f}")
    for f in test_toccati:
        print(f"[ERRORE] test bloccato (Test-Lock) modificato dopo il blocco: {f}")
    for f in non_test:
        print(f"[WARN] file non di test in un commit Test-Lock, non bloccato: {f}")
    for f in fuori:
        print(f"[{'ERRORE' if strict else 'WARN'}] file fuori piano: {f}")
    for p in non_toccati:
        print(f"[INFO] nel piano ma non toccato: {p}")
    ko = (bool(violazioni) or bool(test_toccati) or bool(sottostimato) or bool(dipendenze) or bool(superate)
          or (strict and bool(fuori)))
    print("SCOPE: " + ("OK" if not ko else "VIOLAZIONI"))
    return 1 if ko else 0


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
