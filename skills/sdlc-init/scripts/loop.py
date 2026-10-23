#!/usr/bin/env python3
"""Loop esterno: rilancia l'agente finché verify è verde e non restano task numerate aperte (T-nn e T-Rnn).

Uso:
  python scripts/loop.py docs/specs/001-x [--max 15] [--stall 3] [--timeout 1800] [--agent "claude -p"]
                                          [--allow-main] [--allow-red-baseline] [--dry-run]

Legge PROMPT.md dalla cartella della spec e lo passa all'agente da stdin (evita i limiti di
lunghezza della riga di comando su Windows). Si ferma quando:
  - verify è verde, non ci sono task T-nn o T-Rnn aperte e i controlli finali passano -> exit 0
    (controlli finali: trace_check.py sulla spec e diff_scope.py sulla cartella, se presenti in scripts/;
    le caselle le spunta l'agente, questi controlli no. Se diff_scope non può calcolare il diff è un avviso)
  - raggiunto il tetto --max di iterazioni                  -> exit 1
  - nessun progresso per --stall iterazioni consecutive     -> exit 1
    (progresso = cambia tasks.md, l'HEAD di git o il contenuto dell'albero di lavoro)
Ogni iterazione ha un tempo massimo (--timeout secondi): oltre, l'agente viene terminato e il loop prosegue.
Rifiuta di partire su main/master (--allow-main solo in ambienti isolati) e con verify già rosso, salvo
fase rossa (l'ultima task T-nn chiusa è "atteso: rosso": i test rossi sono attesi) o --allow-red-baseline.
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
OPZIONI_CON_VALORE = {"--max", "--stall", "--timeout", "--agent"}
TASK_APERTA = re.compile(r"^\s*-\s+\[ \]\s+T-R?\d+\b", re.M)  # T-nn dal piano e T-Rnn dalla review
TASK = re.compile(r"^\s*-\s+\[([ xX])\]\s+(T-\d+)\b(.*)$", re.M)


def git(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.stdout.strip() if r.returncode == 0 else ""
    except OSError:
        return ""


def task_aperte(feature: Path) -> bool:
    return bool(TASK_APERTA.search((feature / "tasks.md").read_text(encoding="utf-8")))


def fase_rossa(feature: Path) -> str | None:
    """ID della task di test "atteso: rosso" appena chiusa, se la task successiva è ancora aperta."""
    precedente = None
    for stato, tid, resto in TASK.findall((feature / "tasks.md").read_text(encoding="utf-8")):
        if stato == " ":
            return precedente[0] if precedente and "atteso: rosso" in precedente[1] else None
        precedente = (tid, resto)
    return None


def impronta(feature: Path) -> str:
    """Hash di tasks.md, HEAD e contenuto delle modifiche (tracciate e non tracciate)."""
    h = hashlib.sha256()
    for parte in ((feature / "tasks.md").read_text(encoding="utf-8"), git("rev-parse", "HEAD"),
                  git("status", "--porcelain"), git("diff", "HEAD")):
        h.update(parte.encode("utf-8"))
    for nome in git("ls-files", "--others", "--exclude-standard").splitlines():
        p = Path(nome)
        if p.is_file():
            h.update(nome.encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()


def verify_verde() -> bool:
    return subprocess.run([sys.executable, "scripts/verify.py"]).returncode == 0


def controlli_finali(feature: Path) -> list[str]:
    """Controlli che non dipendono da ciò che dichiara l'agente. Restituisce i controlli falliti."""
    falliti = []
    controlli = [("trace_check", [str(feature / "spec.md")]), ("diff_scope", [str(feature)])]
    for nome, args in controlli:
        script = Path("scripts") / f"{nome}.py"
        if not script.is_file() or (nome == "trace_check" and not (feature / "spec.md").is_file()):
            print(f"[WARN] controllo finale saltato: {nome} (script o spec mancante)", flush=True)
            continue
        codice = subprocess.run([sys.executable, str(script), *args]).returncode
        if codice == 1 or (codice != 0 and nome == "trace_check"):
            falliti.append(nome)
        elif codice != 0:
            print(f"[WARN] {nome} non ha potuto completare il controllo (exit {codice})", flush=True)
    return falliti


def opzione(argv: list[str], nome: str, default: str) -> str:
    return argv[argv.index(nome) + 1] if nome in argv and argv.index(nome) + 1 < len(argv) else default


def esegui_agente(comando: list[str], prompt: str, timeout: int) -> None:
    try:
        r = subprocess.run(comando, input=prompt, text=True, encoding="utf-8", timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"[WARN] l'agente ha superato il timeout di {timeout} s ed è stato terminato", flush=True)
        return
    if r.returncode != 0:
        print(f"[WARN] l'agente è uscito con codice {r.returncode}", flush=True)


def main(argv: list[str]) -> int:
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i > 0 and argv[i - 1] in OPZIONI_CON_VALORE)]
    if not pos:
        print(__doc__)
        return 2
    feature = Path(pos[0])
    massimo = int(opzione(argv, "--max", "15"))
    stallo = int(opzione(argv, "--stall", "3"))
    timeout = int(opzione(argv, "--timeout", "1800"))
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
    rossa = fase_rossa(feature)
    if dry:
        print(f"DRY-RUN OK: spec={feature.as_posix()} max={massimo} stall={stallo} timeout={timeout}s "
              f"agente={' '.join(agente)} branch={branch or '?'}; task T-nn aperte: "
              f"{'si' if task_aperte(feature) else 'no'}; fase rossa: {rossa or 'no'}")
        return 0

    prompt = (feature / "PROMPT.md").read_text(encoding="utf-8")
    if not task_aperte(feature):
        print("Nessuna task T-nn aperta: controllo verify e controlli finali")
        return 0 if verify_verde() and not controlli_finali(feature) else 1
    if not verify_verde():
        if rossa:
            print(f"Baseline rossa attesa: fase rossa dopo {rossa}")
        elif "--allow-red-baseline" not in argv:
            print("[ERRORE] verify è rosso prima di iniziare e non c'è una fase rossa: sistema la baseline "
                  "(o usa --allow-red-baseline se il rosso è noto e documentato)")
            return 2
    precedente, fermi = impronta(feature), 0
    for i in range(1, massimo + 1):
        print(f"== iterazione {i}/{massimo} ==", flush=True)
        esegui_agente([eseguibile, *agente[1:]], prompt, timeout)
        if verify_verde() and not task_aperte(feature):
            falliti = controlli_finali(feature)
            if not falliti:
                print("OK: verify verde, nessuna task T-nn aperta, controlli finali superati. "
                      "Prossimi passi: review, T-DOC, T-SYNC")
                return 0
            print(f"Task chiuse ma controlli finali non superati: {', '.join(falliti)}", flush=True)
        attuale = impronta(feature)
        fermi = fermi + 1 if attuale == precedente else 0
        precedente = attuale
        if fermi >= stallo:
            print(f"Nessun progresso per {stallo} iterazioni: serve revisione umana")
            return 1
    print("Tetto raggiunto: serve revisione umana")
    return 1


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
