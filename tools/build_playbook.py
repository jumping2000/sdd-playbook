#!/usr/bin/env python3
"""Generate the playbook, in English and Italian, from the sources in docs/.

  tools/playbook-src/playbook.src.md     -> docs/playbook-ai-software-lifecycle.md      (English)
  tools/playbook-src/playbook_IT.src.md  -> docs/playbook-ai-software-lifecycle_IT.md   (Italian)

The sources live outside docs/ so that docs/ holds one playbook per language: the one to read.

The `{{FILE path language}}` lines of the sources are replaced with the exact content of the plugin file, in a code
block. This way the scripts and templates shown in the playbook are identical to the plugin's.

Usage: python tools/build_playbook.py          # regenerates the files
       python tools/build_playbook.py --check  # exit 1 if a generated file is not up to date
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SRC = ROOT / "tools" / "playbook-src"
PAIRS = [(SRC / "playbook.src.md", DOCS / "playbook-ai-software-lifecycle.md"),
         (SRC / "playbook_IT.src.md", DOCS / "playbook-ai-software-lifecycle_IT.md")]
MARKER = re.compile(r"^\{\{FILE\s+(\S+)(?:\s+(\S+))?\}\}\s*$")


def build(source: Path) -> str:
    lines = []
    for line in source.read_text(encoding="utf-8").splitlines():
        m = MARKER.match(line)
        if not m:
            lines.append(line)
            continue
        content = (ROOT / m.group(1)).read_text(encoding="utf-8").strip("\n")
        fence = "````" if "```" in content else "```"
        lines += [f"{fence}{m.group(2) or ''}", content, fence]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    stale = []
    for source, target in PAIRS:
        new = build(source)
        if "--check" in argv:
            if not (target.is_file() and target.read_text(encoding="utf-8") == new):
                stale.append(target.relative_to(ROOT).as_posix())
            continue
        target.write_text(new, encoding="utf-8")
        print(f"written {target.relative_to(ROOT).as_posix()}")
    if "--check" in argv:
        print("playbooks up to date" if not stale
              else "playbooks NOT up to date: run tools/build_playbook.py (" + ", ".join(stale) + ")")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
