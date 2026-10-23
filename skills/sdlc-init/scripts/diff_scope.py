#!/usr/bin/env python3
"""Confronta i file modificati con il piano e con le zone vietate.

Uso:
  python scripts/diff_scope.py docs/specs/001-x [--base main] [--strict]

- Vietato: percorsi elencati in AGENTS.md alla riga "- Non modificare: a, b" -> errore (exit 1).
- Fuori piano: file modificati non elencati in plan.md ("Componenti e file da creare/modificare"),
  esclusi docs/specs/<questa spec>/, docs/system/, docs/bugs/, docs/adr/ -> avviso (errore con --strict).
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

SEMPRE_AMMESSI = ("docs/system/", "docs/bugs/", "docs/adr/")
PLACEHOLDER = re.compile(r"<[^<>\n]{1,100}>")


def git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip()


def corrisponde(percorso: str, pattern: str) -> bool:
    p, pat = percorso.replace("\\", "/"), pattern.replace("\\", "/").strip().lstrip("./")
    if not pat:
        return False
    if any(c in pat for c in "*?["):
        return fnmatch.fnmatch(p, pat)
    return p == pat or p.startswith(pat.rstrip("/") + "/")


def percorsi_piano(plan: str) -> list[str]:
    in_sez, out = False, []
    for r in plan.splitlines():
        if r.startswith("## "):
            in_sez = r.startswith("## Componenti e file")
            continue
        if in_sez:
            m = re.match(r"^\s*[-*]\s+`?([^`:\s][^`:]*?)`?\s*(?::|—|$)", r)
            if m and not PLACEHOLDER.fullmatch(m.group(1).strip()):
                out.append(m.group(1).strip())
    return out


def percorsi_vietati(agents: str) -> list[str]:
    m = re.search(r"^\s*[-*]\s+Non modificare\s*:\s*(.*)$", agents, re.M | re.I)
    if not m:
        return []
    voci = [v.strip().strip("`").strip() for v in re.split(r"[,;]", m.group(1))]
    return [v for v in voci if v and not PLACEHOLDER.search(v)]


def base_ref(esplicita: str | None) -> str | None:
    for ref in ([esplicita] if esplicita else ["main", "master", "origin/main", "origin/master"]):
        if git("rev-parse", "--verify", "--quiet", ref)[0] == 0:
            return ref
    return None


def file_modificati(base: str) -> list[str]:
    code, mb = git("merge-base", "HEAD", base)
    if code != 0:
        raise RuntimeError("impossibile calcolare il merge-base")
    _, diff = git("diff", "--name-only", mb)
    _, nuovi = git("ls-files", "--others", "--exclude-standard")
    return sorted({f for f in (diff + "\n" + nuovi).splitlines() if f.strip()})


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
        modificati = file_modificati(base)
    except RuntimeError as e:
        print(f"[ERRORE] {e}")
        return 2
    agents = Path("AGENTS.md").read_text(encoding="utf-8") if Path("AGENTS.md").is_file() else ""
    piano, violazioni, fuori, non_toccati = analizza(feature, modificati, agents)
    print(f"Base: {base}; file modificati: {len(modificati)}; percorsi nel piano: {len(piano)}")
    if not piano:
        print("[WARN] nessun percorso estratto da plan.md: il confronto con il piano non è affidabile")
    for f in violazioni:
        print(f"[ERRORE] file in zona vietata (AGENTS.md): {f}")
    for f in fuori:
        print(f"[{'ERRORE' if strict else 'WARN'}] file fuori piano: {f}")
    for p in non_toccati:
        print(f"[INFO] nel piano ma non toccato: {p}")
    ko = bool(violazioni) or (strict and bool(fuori))
    print("SCOPE: " + ("OK" if not ko else "VIOLAZIONI"))
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
