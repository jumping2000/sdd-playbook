#!/usr/bin/env python3
# sdlc-playbook: 0.11.0
"""Scansione dei segreti nei file: chiavi e token con formato riconoscibile, file .env versionati.

Uso:
  python scripts/secrets_check.py                 # file modificati dal merge-base con main (o --base <ref>)
  python scripts/secrets_check.py --all           # tutti i file tracciati da git
  python scripts/secrets_check.py src config.yml  # file e cartelle indicati

- Errore (exit 1): chiavi private, token con prefisso noto (AWS, GitHub, GitLab, Slack, Stripe, Google, Anthropic,
  OpenAI), file .env versionati o modificati (non .env.example, .env.sample, .env.template).
- Avviso: assegnazioni di password, secret, token o chiavi a una stringa letterale di almeno 8 caratteri.
Una riga con "secrets-check: ignore" non viene controllata (falso positivo, motivato nella review). Il valore trovato
non viene mai stampato. È una rete minima e veloce: per la storia completa del repository usa uno strumento dedicato
(per esempio gitleaks) in CI. Exit code: 0 nessun segreto; 1 segreti trovati; 2 uso errato o git non utilizzabile.
Solo stdlib + git, cross-platform.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

CERTI = [
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-----"), "chiave privata"),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "chiave di accesso AWS"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b"), "token GitHub"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), "token GitLab"),
    (re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b"), "token Slack"),
    (re.compile(r"\b[sr]k_live_[0-9A-Za-z]{20,}\b"), "chiave Stripe live"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "chiave API Google"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), "chiave API Anthropic"),
    (re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}\b"), "chiave API OpenAI"),
]
GENERICO = re.compile(r"(?i)(?<![a-z])(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|"
                      r"client[_-]?secret)(?![a-z])[\"']?\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']")
SEGNAPOSTO = re.compile(r"(?i)^(<.*>|\$\{.*\}|\{\{.*\}\}|x{4,}|\*{4,}|changeme|change_me|example\w*|dummy\w*|"
                        r"placeholder|your[_-].*|test\w*|fake\w*|secret|password)$")
ENV_FILE = re.compile(r"(?i)(^|/)\.env(\.(?!example$|sample$|template$)[\w.-]+)?$")
IGNORA = "secrets-check: ignore"
SALTA = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", "bin", "obj"}
MAX_BYTE = 1_000_000


def git(*args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return 1, ""
    return r.returncode, r.stdout.strip()


def file_da_git(tutti: bool, base: str | None) -> list[str] | None:
    """File da controllare secondo git; None se git o il ref di base non sono utilizzabili."""
    if git("rev-parse", "--is-inside-work-tree")[0] != 0:
        return None
    if tutti:
        return git("ls-files")[1].splitlines()
    for ref in ([base] if base else ["main", "master", "origin/main", "origin/master"]):
        if git("rev-parse", "--verify", "--quiet", ref)[0] == 0:
            code, mb = git("merge-base", "HEAD", ref)
            if code != 0:
                return None
            diff = git("diff", "--name-only", "--diff-filter=d", mb)[1]
            nuovi = git("ls-files", "--others", "--exclude-standard")[1]
            return sorted({f for f in (diff + "\n" + nuovi).splitlines() if f.strip()})
    return None


def espandi(percorsi: list[str]) -> list[str]:
    out = []
    for p in map(Path, percorsi):
        if p.is_dir():
            out += [f.as_posix() for f in sorted(p.rglob("*")) if f.is_file() and not SALTA & set(f.parts)]
        else:
            out.append(p.as_posix())
    return out


def controlla_file(percorso: str) -> tuple[list[str], list[str]]:
    """(errori, avvisi) per un file, senza riportare il valore trovato."""
    err: list[str] = []
    avv: list[str] = []
    if ENV_FILE.search(percorso.replace("\\", "/")):
        err.append(f"{percorso}: file .env nel repository (i segreti stanno fuori dal repo)")
    p = Path(percorso)
    if not p.is_file() or p.stat().st_size > MAX_BYTE:
        return err, avv
    dati = p.read_bytes()
    if b"\0" in dati[:8192]:
        return err, avv  # binario
    for n, riga in enumerate(dati.decode("utf-8", "replace").splitlines(), 1):
        if IGNORA in riga:
            continue
        for regola, nome in CERTI:
            if regola.search(riga):
                err.append(f"{percorso}:{n}: {nome}")
        for m in GENERICO.finditer(riga):
            if not SEGNAPOSTO.match(m.group(2)):
                avv.append(f"{percorso}:{n}: possibile segreto assegnato a '{m.group(1)}'")
    return err, avv


def main(argv: list[str]) -> int:
    base = argv[argv.index("--base") + 1] if "--base" in argv and argv.index("--base") + 1 < len(argv) else None
    percorsi = [a for a in argv if not a.startswith("--") and a != base]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 2
    if percorsi:
        file = espandi(percorsi)
    else:
        file = file_da_git("--all" in argv, base)
        if file is None:
            print("[ERRORE] git non utilizzabile o nessun ref di base: usa --base <ref>, --all o indica i percorsi")
            return 2
    errori: list[str] = []
    avvisi: list[str] = []
    for f in file:
        e, a = controlla_file(f)
        errori += e
        avvisi += a
    for a in avvisi:
        print(f"[WARN] {a}")
    for e in errori:
        print(f"[ERRORE] {e}")
    print(f"SECRETS: {'OK' if not errori else f'{len(errori)} segreti'} ({len(file)} file controllati)")
    return 1 if errori else 0


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
