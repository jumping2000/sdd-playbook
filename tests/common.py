"""Fixture e utilità condivise dai test. Solo stdlib."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "sdlc-init" / "scripts"
HOOKS = ROOT / "hooks"


def carica(nome: str):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(nome, SCRIPTS / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def leggi(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def scrivi(root: Path, rel: str, testo: str = "x") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(testo, encoding="utf-8")
    return p


def esegui(args: list[str], cwd: Path, stdin: str | None = None, env: dict | None = None):
    return subprocess.run(args, cwd=cwd, input=stdin, capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, **(env or {})})


def git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                       cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, f"git {' '.join(args)}: {r.stderr}"
    return r.stdout.strip()


def repo_git(root: Path, branch: str = "main") -> None:
    git(root, "init", "-q")
    git(root, "symbolic-ref", "HEAD", f"refs/heads/{branch}")


def copia_script(dest: Path, nomi: list[str] | None = None) -> None:
    (dest / "scripts").mkdir(parents=True, exist_ok=True)
    for f in SCRIPTS.glob("*.py"):
        if nomi is None or f.stem in nomi:
            (dest / "scripts" / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")


class TmpDir:
    def __enter__(self) -> Path:
        self._t = tempfile.TemporaryDirectory()
        return Path(self._t.name)

    def __exit__(self, *a):
        self._t.cleanup()


SPEC_OK = """# SPEC-001: Esempio

- Stato: approved
- Proprietario: Anna
- Approvata da / data: Anna Rossi, 2026-10-19

## Problema e obiettivo
Esportare il report in CSV.

## Scope
- Incluso: export CSV
- **Non-scope (esplicito):** nessuna modifica al formato PDF

## Requisiti
- REQ-001 (funzionale): il report si esporta in CSV

## Acceptance criteria
- AC-001 [REQ-001]: Dato un report, quando esporto, allora ottengo un CSV valido
- AC-002 [REQ-001, errore]: Dato un report vuoto, quando esporto, allora ricevo un errore chiaro

## Domande aperte
- nessuna
"""
PLAN_OK = """# PLAN per SPEC-001

- Approvato da / data: Anna Rossi, 2026-10-19

## Componenti e file da creare/modificare
- src/export.py: nuova funzione di export
- `tests/`: nuovi test

## Strategia di test (mappata sugli AC)
| AC-001 | unit |
| AC-002 | unit |
"""
_spec_lint = carica("spec_lint")
APPROVATA = "- Approvata da / data: Anna Rossi, 2026-10-19\n"
SPEC_OK = SPEC_OK.replace(APPROVATA, APPROVATA + f"- Hash: {_spec_lint.impronta(SPEC_OK)}\n")
APPROVATO = "- Approvato da / data: Anna Rossi, 2026-10-19\n"
PLAN_OK = PLAN_OK.replace(APPROVATO, APPROVATO + f"- Basato su spec: {_spec_lint.impronta(SPEC_OK)}\n"
                          f"- Hash: {_spec_lint.impronta(PLAN_OK)}\n")
TASKS_OK = """- [ ] T-01 Test — verifica: `pytest -k AC_001` (atteso: rosso) — copre: AC-001, AC-002 — test approvati: Anna Rossi, 2026-10-19, abc1234
- [ ] T-02 Implementa — verifica: `pytest` — copre: AC-001, AC-002
- [ ] T-DOC Documentazione
- [ ] T-SYNC Riconciliazione
"""
REVIEW_OK = """# Review di SPEC-001

- Esito: conforme
- Data: 2026-10-19
- Base del diff: main

## Decisione umana
- Decisione di: Anna Rossi, 2026-10-19
"""
AREA_OK = """# Area: export

- Ultimo allineamento: 2026-10-19
- Specifiche collegate: SPEC-001

## Comportamento attuale
Esporta in CSV.

## Vincoli e punti delicati
- nessuno

## Test di caratterizzazione
- tests/test_char.py: formato CSV attuale
"""
BUG_OK = """# BUG-001: Export rotto

- Stato: verificato
- Gravità / impatto: media
- Spec o area interessata: SPEC-001

## Riproduzione
Esporta un report con una virgola nel nome.

## Comportamento attuale vs atteso
- Attuale: il CSV è malformato
- Atteso: il campo è racchiuso tra virgolette

## Comportamento da NON cambiare
- Il separatore resta la virgola

## Causa radice
Manca l'escaping nel writer.

## Fix e test
- Test rosso che riproduce il bug: `tests/test_export.py::test_virgola`
- Fix minimo: usa csv.writer in src/export.py
- Test di non-regressione sul comportamento invariato: `tests/test_export.py::test_separatore`

## Chiusura
- [x] verify verde
- [x] spec aggiornata
- [x] lezione registrata
"""
