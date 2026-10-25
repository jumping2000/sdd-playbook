#!/usr/bin/env python3
"""Genera il playbook, in inglese e in italiano, dai sorgenti in docs/.

  docs/playbook.src.md     -> docs/playbook-ai-software-lifecycle.md      (inglese)
  docs/playbook_IT.src.md  -> docs/playbook-ai-software-lifecycle_IT.md   (italiano)

Le righe `{{FILE percorso lingua}}` dei sorgenti vengono sostituite con il contenuto esatto del file del
plugin, in un blocco di codice. Così script e template citati nel playbook sono identici a quelli del plugin.

Uso:  python tools/build_playbook.py          # rigenera i file
      python tools/build_playbook.py --check  # exit 1 se un file generato non è aggiornato
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
COPPIE = [(DOCS / "playbook.src.md", DOCS / "playbook-ai-software-lifecycle.md"),
          (DOCS / "playbook_IT.src.md", DOCS / "playbook-ai-software-lifecycle_IT.md")]
MARCATORE = re.compile(r"^\{\{FILE\s+(\S+)(?:\s+(\S+))?\}\}\s*$")


def costruisci(sorgente: Path) -> str:
    righe = []
    for riga in sorgente.read_text(encoding="utf-8").splitlines():
        m = MARCATORE.match(riga)
        if not m:
            righe.append(riga)
            continue
        contenuto = (ROOT / m.group(1)).read_text(encoding="utf-8").strip("\n")
        fence = "````" if "```" in contenuto else "```"
        righe += [f"{fence}{m.group(2) or ''}", contenuto, fence]
    return "\n".join(righe) + "\n"


def main(argv: list[str]) -> int:
    ko = []
    for sorgente, uscita in COPPIE:
        nuovo = costruisci(sorgente)
        if "--check" in argv:
            if not (uscita.is_file() and uscita.read_text(encoding="utf-8") == nuovo):
                ko.append(uscita.relative_to(ROOT).as_posix())
            continue
        uscita.write_text(nuovo, encoding="utf-8")
        print(f"scritto {uscita.relative_to(ROOT).as_posix()}")
    if "--check" in argv:
        print("playbook aggiornati" if not ko else "playbook NON aggiornati: esegui tools/build_playbook.py (" + ", ".join(ko) + ")")
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
