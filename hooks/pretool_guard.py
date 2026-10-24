#!/usr/bin/env python3
"""Hook PreToolUse (Claude Code), opt-in: blocca comandi e letture ad alto rischio.

Attivo solo con SDLC_GUARD=1. Legge da stdin il JSON dell'evento (tool_name, tool_input). Esce 2 con un
messaggio su stderr per bloccare la chiamata, 0 altrimenti; con un JSON illeggibile blocca (fail-closed). È una
rete di sicurezza minima, non un sandbox: non sostituisce permessi nativi dell'agente, allowlist e isolamento
dell'ambiente (playbook §1.2), e un comando abbastanza contorto la aggira sempre.
Bloccati in Bash e PowerShell: push forzati o distruttivi (--force, -f, --force-with-lease, +refspec, --delete, --mirror),
reset --hard, clean -f (anche con opzioni globali di git, come -C), cancellazioni ricorsive (rm -r in qualsiasi
forma, git rm -r senza --cached, find -delete, Remove-Item -Recurse, rd /s, del /s, shutil.rmtree),
download-ed-esegui, qualsiasi riferimento a un file .env anche dentro una parola (cat .env>x, open('.env')), tranne
.env.example, .sample, .template e i comandi su .gitignore (aggiunta, git check-ignore). Strumenti Read e Grep: file .env, anche in maiuscolo o con uno stream NTFS
(.env::$DATA). Solo stdlib, cross-platform.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

REGOLE = [
    (r"\bRemove-Item\b.*\s-r(e(c(u(r(s(e)?)?)?)?)?)?\b", "cancellazione ricorsiva (Remove-Item -Recurse)"),
    (r"\b(rd|rmdir)\s+/s\b|\bdel\s+/[sfq]\b", "cancellazione ricorsiva (cmd)"),
    (r"\bshutil\s*\.\s*rmtree\b", "cancellazione ricorsiva (shutil.rmtree)"),
    (r"\b(curl|wget)\b[^|;&]*\|\s*(sudo\s+)?(sh|bash|zsh|python3?)\b", "download ed esecuzione"),
    (r"\b(iwr|Invoke-WebRequest|irm|Invoke-RestMethod)\b[^|;&]*\|\s*(iex|Invoke-Expression)\b", "download ed esecuzione"),
]
# .env con suffisso facoltativo (non example/sample/template) e stream NTFS facoltativo (.env::$DATA, .env:x)
ENV_FILE = re.compile(r"(^|[\\/])\.env(\.(?!example\b|sample\b|template\b)[\w-]+)*(::?\$?\w*)?$", re.I)
SEPARATORI = re.compile(r"&&|\|\||[;|&\n]")
DENTRO_PAROLA = re.compile(r"[<>=()'\",]")  # .env attaccato a redirezioni, chiamate, assegnazioni
SU_IGNORE = re.compile(r"\.(git|docker)ignore\b|\bcheck-ignore\b", re.I)
PREFISSI = {"sudo", "xargs", "command", "exec", "nohup", "env", "time", "doas"}
GIT_CON_VALORE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def sottocomando_git(p: list[str], nomi: list[str]) -> tuple[str, list[str]] | None:
    """(sottocomando, argomenti) di git, saltando le opzioni globali (-C dir, -c chiave=valore)."""
    if "git" not in nomi:
        return None
    i = nomi.index("git") + 1
    while i < len(p) and p[i].startswith("-"):
        i += 2 if p[i] in GIT_CON_VALORE else 1
    return (p[i], p[i + 1:]) if i < len(p) else None


def flag_corti(argomenti: list[str], lettera: str) -> bool:
    return any(re.fullmatch(r"-[A-Za-z]+", x) and lettera in x for x in argomenti)


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
    for i, n in enumerate(nomi):
        if n == "rm" and (i == 0 or nomi[i - 1] in PREFISSI):
            opzioni = [x for x in p[i + 1:] if x.startswith("-")]
            if "--recursive" in opzioni or flag_corti(opzioni, "r") or flag_corti(opzioni, "R"):
                return "cancellazione ricorsiva (rm -r)"
    if "find" in nomi and ("-delete" in p or ("-exec" in p and "rm" in nomi)):
        return "cancellazione ricorsiva (find -delete)"
    git = sottocomando_git(p, nomi)
    if git:
        sotto, arg = git
        if sotto == "reset" and "--hard" in arg:
            return "git reset --hard"
        if sotto == "clean" and ("--force" in arg or flag_corti(arg, "f")):
            return "git clean -f"
        if sotto == "rm" and "--cached" not in arg and ("--recursive" in arg or flag_corti(arg, "r")):
            return "cancellazione ricorsiva (git rm -r)"
        if sotto == "push" and any(x in ("--force", "--mirror", "--delete") or x.startswith(("--force", "+", ":"))
                                   for x in arg) or sotto == "push" and (flag_corti(arg, "f") or flag_corti(arg, "d")):
            return "push forzato o distruttivo"
    if SU_IGNORE.search(segmento):
        return None
    grezze = segmento.split()  # shlex toglie le barre rovesciate dei percorsi Windows
    pezzi = [x for parola in p + grezze for x in DENTRO_PAROLA.split(parola)]
    if any(ENV_FILE.search(x) for x in pezzi):
        return "riferimento a un file .env"
    return None


def motivo(evento: dict) -> str | None:
    tool = evento.get("tool_name", "")
    inp = evento.get("tool_input") or {}
    if not isinstance(inp, dict):
        return "evento malformato (tool_input non è un oggetto)"
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
