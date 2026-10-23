#!/usr/bin/env python3
# sdlc-playbook: 0.11.0
"""Controlli sulla documentazione: link relativi validi ed esempi Python eseguibili.

Uso:
  python scripts/docs_check.py [percorsi...] [--run-examples]

Percorsi di default: README.md e la cartella docs/. Controlla i link e le immagini relativi dei file
Markdown (esclude i blocchi di codice, gli URL esterni e le ancore pure). Con --run-examples esegue i
blocchi ```python la cui prima riga non vuota è `# docs-check: run` (timeout 60 s, cartella corrente
= radice del progetto): devono terminare con exit code 0. Gli altri blocchi non vengono eseguiti:
gli esempi in altri linguaggi vanno provati a mano dall'agente.
Exit code: 0 ok; 1 link rotti o esempi falliti; 2 uso errato. Solo stdlib, cross-platform.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w+-]*)\s*$")


def file_md(percorsi: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in percorsi:
        path = Path(p)
        if path.is_dir():
            out += sorted(path.rglob("*.md"))
        elif path.is_file():
            out.append(path)
    return out


def scomponi(testo: str):
    """Restituisce (righe_di_testo_fuori_dai_blocchi, blocchi[(lingua, codice)])."""
    fuori: list[tuple[int, str]] = []
    blocchi: list[tuple[str, str]] = []
    in_blocco, marcatore, lingua, buf = False, "", "", []
    for n, riga in enumerate(testo.splitlines(), 1):
        m = FENCE.match(riga)
        if not in_blocco and m:
            in_blocco, marcatore, lingua, buf = True, m.group(2)[0] * 3, m.group(3), []
        elif in_blocco and riga.strip().startswith(marcatore):
            blocchi.append((lingua, "\n".join(buf)))
            in_blocco = False
        elif in_blocco:
            buf.append(riga)
        else:
            fuori.append((n, riga))
    return fuori, blocchi


def link_rotti(f: Path) -> list[str]:
    errori = []
    fuori, _ = scomponi(f.read_text(encoding="utf-8", errors="ignore"))
    for n, riga in fuori:
        riga = re.sub(r"`[^`]*`", "", riga)  # ignora il codice inline
        for m in LINK.finditer(riga):
            dest = m.group(1)
            if re.match(r"^(https?:|mailto:|#|/)", dest):
                continue
            target = (f.parent / dest.split("#")[0]).resolve()
            if not target.exists():
                errori.append(f"{f.as_posix()}:{n}: link rotto -> {dest}")
    return errori


def esegui_esempi(f: Path) -> tuple[list[str], int]:
    errori, eseguiti = [], 0
    _, blocchi = scomponi(f.read_text(encoding="utf-8", errors="ignore"))
    for i, (lingua, codice) in enumerate(blocchi, 1):
        prima = next((r.strip() for r in codice.splitlines() if r.strip()), "")
        if lingua != "python" or prima != "# docs-check: run":
            continue
        eseguiti += 1
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as t:
            t.write(codice)
            nome = t.name
        try:
            r = subprocess.run([sys.executable, nome], capture_output=True, text=True, timeout=60,
                               encoding="utf-8", errors="replace")
            if r.returncode != 0:
                errori.append(f"{f.as_posix()}: esempio #{i} fallito (exit {r.returncode}): {(r.stderr or r.stdout).strip()[-200:]}")
        except subprocess.TimeoutExpired:
            errori.append(f"{f.as_posix()}: esempio #{i} oltre il timeout di 60 s")
        finally:
            Path(nome).unlink(missing_ok=True)
    return errori, eseguiti


def main(argv: list[str]) -> int:
    run = "--run-examples" in argv
    percorsi = [a for a in argv if not a.startswith("--")] or ["README.md", "docs"]
    files = file_md(percorsi)
    if not files:
        print("[ERRORE] nessun file Markdown trovato")
        return 2
    errori, eseguiti = [], 0
    for f in files:
        errori += link_rotti(f)
        if run:
            e, n = esegui_esempi(f)
            errori += e
            eseguiti += n
    for e in errori:
        print(f"[ERRORE] {e}")
    print(f"DOCS: {len(files)} file" + (f", {eseguiti} esempi eseguiti" if run else "") + " - "
          + ("OK" if not errori else f"{len(errori)} errori"))
    return 1 if errori else 0


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
