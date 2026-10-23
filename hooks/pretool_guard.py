#!/usr/bin/env python3
"""Hook PreToolUse (Claude Code), opt-in: blocca comandi e letture ad alto rischio.

Attivo solo con SDLC_GUARD=1. Legge da stdin il JSON dell'evento (tool_name, tool_input). Esce 2 con un
messaggio su stderr per bloccare la chiamata, 0 altrimenti; con un JSON illeggibile blocca (fail-closed). È una
rete di sicurezza minima, non un sandbox: non sostituisce permessi nativi dell'agente, allowlist e isolamento
dell'ambiente (playbook §1.2), e un comando abbastanza contorto la aggira sempre.
Bloccati in Bash e PowerShell: push forzati o distruttivi (--force, -f, --force-with-lease, +refspec, --delete, --mirror),
reset --hard, clean -f, cancellazioni ricorsive (rm -r in qualsiasi forma, Remove-Item -Recurse, rd /s, del /s,
shutil.rmtree), download-ed-esegui, qualsiasi riferimento a un file .env (non .env.example, .sample, .template),
salvo l'aggiunta a .gitignore. Strumenti Read e Grep: file .env, anche in maiuscolo o con uno stream NTFS
(.env::$DATA). Solo stdlib, cross-platform.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

REGOLE = [
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard"),
    (r"\bgit\s+clean\s+(-\w*f|--force)", "git clean -f"),
    (r"\bRemove-Item\b.*\s-r(e(c(u(r(s(e)?)?)?)?)?)?\b", "cancellazione ricorsiva (Remove-Item -Recurse)"),
    (r"\b(rd|rmdir)\s+/s\b|\bdel\s+/[sfq]\b", "cancellazione ricorsiva (cmd)"),
    (r"\bshutil\s*\.\s*rmtree\b", "cancellazione ricorsiva (shutil.rmtree)"),
    (r"\b(curl|wget)\b[^|;&]*\|\s*(sudo\s+)?(sh|bash|zsh|python3?)\b", "download ed esecuzione"),
    (r"\b(iwr|Invoke-WebRequest|irm|Invoke-RestMethod)\b[^|;&]*\|\s*(iex|Invoke-Expression)\b", "download ed esecuzione"),
]
# .env con suffisso facoltativo (non example/sample/template) e stream NTFS facoltativo (.env::$DATA, .env:x)
ENV_FILE = re.compile(r"(^|[\\/])\.env(\.(?!example\b|sample\b|template\b)[\w-]+)*(::?\$?\w*)?$", re.I)
SEPARATORI = re.compile(r"&&|\|\||[;|&\n]")
IGNORE_FILE = re.compile(r">>?\s*['\"]?[^\s'\"]*\.(git|docker)ignore['\"]?\s*$", re.I)


def parole(segmento: str) -> list[str]:
    try:
        return shlex.split(segmento, posix=True)
    except ValueError:
        return segmento.split()


def motivo_segmento(segmento: str) -> str | None:
    p = parole(segmento)
    if not p:
        return None
    nomi = [os.path.basename(x).lower() for x in p]
    if "rm" in nomi:
        opzioni = [x for x in p[nomi.index("rm") + 1:] if x.startswith("-")]
        if any(x in ("--recursive", "-R") or (not x.startswith("--") and "r" in x.lower()) for x in opzioni):
            return "cancellazione ricorsiva (rm -r)"
    if "git" in nomi and "push" in p[nomi.index("git") + 1:]:
        resto = p[p.index("push") + 1:]
        if any(x in ("-f", "--force", "--mirror", "--delete", "-d") or x.startswith(("--force", "+", ":"))
               or (re.fullmatch(r"-[a-z]+", x) and "f" in x) for x in resto):
            return "push forzato o distruttivo"
    grezze = segmento.split()  # shlex toglie le barre rovesciate dei percorsi Windows
    if not IGNORE_FILE.search(segmento) and any(ENV_FILE.search(x.strip("'\"")) for x in p + grezze):
        return "riferimento a un file .env"
    return None


def motivo(evento: dict) -> str | None:
    tool = evento.get("tool_name", "")
    inp = evento.get("tool_input") or {}
    if tool in ("Bash", "PowerShell"):
        cmd = str(inp.get("command", ""))
        for pattern, nome in REGOLE:
            if re.search(pattern, cmd, re.I):
                return nome
        for segmento in SEPARATORI.split(cmd):
            if (m := motivo_segmento(segmento)):
                return m
    if tool == "Read" and ENV_FILE.search(str(inp.get("file_path", ""))):
        return "lettura di un file .env"
    if tool == "Grep" and any(ENV_FILE.search(str(inp.get(k, ""))) or re.search(r"\.env\*?$", str(inp.get(k, "")), re.I)
                              for k in ("path", "glob")):
        return "ricerca in un file .env"
    return None


def main() -> int:
    if os.environ.get("SDLC_GUARD") != "1":
        return 0
    try:
        evento = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.stderr.write("Bloccato dal guard del plugin sdlc-playbook: evento illeggibile (fail-closed).\n")
        return 2
    m = motivo(evento if isinstance(evento, dict) else {})
    if m:
        sys.stderr.write(f"Bloccato dal guard del plugin sdlc-playbook: {m}. Chiedi conferma all'utente.\n")
        return 2
    return 0


if __name__ == "__main__":
    for flusso in (sys.stdin, sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
