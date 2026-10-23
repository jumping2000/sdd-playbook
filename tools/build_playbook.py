#!/usr/bin/env python3
"""Genera docs/playbook-ai-software-lifecycle.md da docs/playbook.src.md.

Le righe `{{FILE percorso lingua}}` del sorgente vengono sostituite con il contenuto esatto del file del
plugin, in un blocco di codice. Così script e template citati nel playbook sono identici a quelli del plugin.

Uso:  python tools/build_playbook.py          # rigenera il file
      python tools/build_playbook.py --check  # exit 1 se il file generato non è aggiornato
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "playbook.src.md"
OUT = ROOT / "docs" / "playbook-ai-software-lifecycle.md"
MARCATORE = re.compile(r"^\{\{FILE\s+(\S+)(?:\s+(\S+))?\}\}\s*$")


def costruisci() -> str:
    righe = []
    for riga in SRC.read_text(encoding="utf-8").splitlines():
        m = MARCATORE.match(riga)
        if not m:
            righe.append(riga)
            continue
        contenuto = (ROOT / m.group(1)).read_text(encoding="utf-8").strip("\n")
        fence = "````" if "```" in contenuto else "```"
        righe += [f"{fence}{m.group(2) or ''}", contenuto, fence]
    return "\n".join(righe) + "\n"


def main(argv: list[str]) -> int:
    nuovo = costruisci()
    if "--check" in argv:
        ok = OUT.is_file() and OUT.read_text(encoding="utf-8") == nuovo
        print("playbook aggiornato" if ok else "playbook NON aggiornato: esegui tools/build_playbook.py")
        return 0 if ok else 1
    OUT.write_text(nuovo, encoding="utf-8")
    print(f"scritto {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
