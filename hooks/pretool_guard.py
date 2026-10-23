#!/usr/bin/env python3
"""Hook PreToolUse (Claude Code), opt-in: blocca comandi e letture ad alto rischio.

Attivo solo con SDLC_GUARD=1. Legge da stdin il JSON dell'evento (tool_name, tool_input). Esce 2 con un
messaggio su stderr per bloccare la chiamata, 0 altrimenti. È una rete di sicurezza minima, non un
sandbox: non sostituisce permessi, allowlist e isolamento dell'ambiente (playbook §1.2).
Bloccati: force push, reset --hard, cancellazioni ricorsive, download-ed-esegui, lettura di file .env
(non .env.example). Solo stdlib, cross-platform.
"""
from __future__ import annotations

import json
import os
import re
import sys

REGOLE = [
    (r"\bgit\s+push\b.*(\s--force\b|\s-f\b)", "force push"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard"),
    (r"\brm\s+-[a-zA-Z]*(rf|fr)[a-zA-Z]*\b", "cancellazione ricorsiva (rm -rf)"),
    (r"\bRemove-Item\b.*-Recurse.*-Force|\bRemove-Item\b.*-Force.*-Recurse", "cancellazione ricorsiva (Remove-Item)"),
    (r"\b(rd|rmdir)\s+/s\b|\bdel\s+/[sfq]\b", "cancellazione ricorsiva (cmd)"),
    (r"\b(curl|wget)\b[^|;&]*\|\s*(sudo\s+)?(sh|bash|zsh|python3?)\b", "download ed esecuzione"),
    (r"\b(iwr|Invoke-WebRequest|irm|Invoke-RestMethod)\b[^|;&]*\|\s*(iex|Invoke-Expression)\b", "download ed esecuzione"),
    (r"\b(cat|type|Get-Content|gc|less|more|head|tail|bat)\s+[^|;&]*\.env(?![\w.-])", "lettura di .env"),
]
ENV_FILE = re.compile(r"(^|[\\/])\.env(\.(?!example$|sample$|template$)[\w-]+)?$")


def motivo(evento: dict) -> str | None:
    tool = evento.get("tool_name", "")
    inp = evento.get("tool_input") or {}
    if tool in ("Bash", "PowerShell"):
        cmd = str(inp.get("command", ""))
        for pattern, nome in REGOLE:
            if re.search(pattern, cmd, re.I):
                return nome
    if tool == "Read" and ENV_FILE.search(str(inp.get("file_path", ""))):
        return "lettura di un file .env"
    return None


def main() -> int:
    if os.environ.get("SDLC_GUARD") != "1":
        return 0
    try:
        evento = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    m = motivo(evento)
    if m:
        sys.stderr.write(f"Bloccato dal guard del plugin sdlc-playbook: {m}. Chiedi conferma all'utente.\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
