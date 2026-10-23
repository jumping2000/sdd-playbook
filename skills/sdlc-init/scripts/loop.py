#!/usr/bin/env python3
"""Loop esterno: rilancia l'agente finché verify è verde e non restano task numerate (T-nn) aperte.

Uso:
  python scripts/loop.py docs/specs/001-x [--max 15] [--stall 3] [--agent "claude -p"]
                                          [--allow-main] [--dry-run]

Legge PROMPT.md dalla cartella della spec e lo passa all'agente da stdin (evita i limiti di
lunghezza della riga di comando su Windows). Si ferma quando:
  - verify è verde e non ci sono task T-nn aperte          -> exit 0
  - raggiunto il tetto --max di iterazioni                  -> exit 1
  - nessun progresso per --stall iterazioni consecutive     -> exit 1
    (progresso = cambia tasks.md, l'HEAD di git o lo stato dell'albero di lavoro)
Rifiuta di partire su main/master (--allow-main solo in ambienti isolati).
--dry-run controlla le precondizioni e non lancia l'agente.
Le task T-DOC e T-SYNC non fanno parte del loop: si eseguono dopo la review (sdlc-docs, sdlc-sync).
Exit code: 0 completato; 1 tetto o stallo; 2 uso errato o precondizioni non rispettate.
Permessi e allowlist dell'agente vanno configurati a parte. Solo stdlib, cross-platform.
"""
from __future__ import annotations

import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

PROTETTI = {"main", "master"}
OPZIONI_CON_VALORE = {"--max", "--stall", "--agent"}
TASK_APERTA = re.compile(r"^\s*-\s+\[ \]\s+T-\d+\b", re.M)


def git(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.stdout.strip() if r.returncode == 0 else ""
    except OSError:
        return ""


def task_aperte(feature: Path) -> bool:
    return bool(TASK_APERTA.search((feature / "tasks.md").read_text(encoding="utf-8")))


def impronta(feature: Path) -> str:
    h = hashlib.sha256()
    for parte in ((feature / "tasks.md").read_text(encoding="utf-8"), git("rev-parse", "HEAD"),
                  git("status", "--porcelain")):
        h.update(parte.encode("utf-8"))
    return h.hexdigest()


def verify_verde() -> bool:
    return subprocess.run([sys.executable, "scripts/verify.py"]).returncode == 0


def opzione(argv: list[str], nome: str, default: str) -> str:
    return argv[argv.index(nome) + 1] if nome in argv and argv.index(nome) + 1 < len(argv) else default


def main(argv: list[str]) -> int:
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i > 0 and argv[i - 1] in OPZIONI_CON_VALORE)]
    if not pos:
        print(__doc__)
        return 2
    feature = Path(pos[0])
    massimo = int(opzione(argv, "--max", "15"))
    stallo = int(opzione(argv, "--stall", "3"))
    agente = shlex.split(opzione(argv, "--agent", "claude -p"), posix=(os.name != "nt"))
    dry = "--dry-run" in argv

    for f in (feature / "PROMPT.md", feature / "tasks.md", Path("scripts/verify.py")):
        if not f.is_file():
            print(f"[ERRORE] file necessario non trovato: {f.as_posix()}")
            return 2
    branch = git("branch", "--show-current")
    if not branch:
        print("[WARN] branch non rilevabile (git assente o HEAD staccato): controlla a mano di non essere su main")
    elif branch in PROTETTI and "--allow-main" not in argv:
        print(f"[ERRORE] sei sul branch '{branch}': crea un branch di feature (o usa --allow-main in ambiente isolato)")
        return 2
    eseguibile = shutil.which(agente[0])
    if eseguibile is None:
        print(f"[ERRORE] agente non trovato nel PATH: {agente[0]}")
        return 2
    if dry:
        print(f"DRY-RUN OK: spec={feature.as_posix()} max={massimo} stall={stallo} agente={' '.join(agente)} "
              f"branch={branch or '?'}; task T-nn aperte: {'si' if task_aperte(feature) else 'no'}")
        return 0

    prompt = (feature / "PROMPT.md").read_text(encoding="utf-8")
    if not task_aperte(feature):
        print("Nessuna task T-nn aperta: controllo solo verify")
        return 0 if verify_verde() else 1
    precedente, fermi = impronta(feature), 0
    for i in range(1, massimo + 1):
        print(f"== iterazione {i}/{massimo} ==", flush=True)
        subprocess.run([eseguibile, *agente[1:]], input=prompt, text=True, encoding="utf-8")
        if verify_verde() and not task_aperte(feature):
            print("OK: verify verde e nessuna task T-nn aperta. Prossimi passi: review, T-DOC, T-SYNC")
            return 0
        attuale = impronta(feature)
        fermi = fermi + 1 if attuale == precedente else 0
        precedente = attuale
        if fermi >= stallo:
            print(f"Nessun progresso per {stallo} iterazioni: serve revisione umana")
            return 1
    print("Tetto raggiunto: serve revisione umana")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
