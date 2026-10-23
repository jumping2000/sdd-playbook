#!/usr/bin/env python3
"""Inventario deterministico di una codebase esistente (punto di partenza per la mappa, brownfield).

Uso:  python scripts/scan_repo.py [radice] [--json]

Sola lettura. Elenca: manifest e stack rilevati, linguaggi (file e righe), struttura di primo livello,
cartelle di test, configurazioni CI, entry point probabili, documentazione presente.
È un inventario, non una comprensione: i moduli e le responsabilità vanno letti nel codice.
Usa `git ls-files` se disponibile, altrimenti visita le cartelle. Solo stdlib, cross-platform.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

SALTA = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", "bin", "obj",
         ".idea", ".vscode", ".mypy_cache", ".pytest_cache", ".gradle"}
LINGUAGGI = {".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
             ".java": "Java", ".kt": "Kotlin", ".cs": "C#", ".go": "Go", ".rb": "Ruby", ".php": "PHP",
             ".rs": "Rust", ".c": "C", ".cpp": "C++", ".h": "C/C++", ".swift": "Swift", ".sql": "SQL",
             ".sh": "Shell", ".ps1": "PowerShell"}
MANIFEST = {"pyproject.toml": "Python", "requirements.txt": "Python", "setup.py": "Python", "uv.lock": "Python (uv)",
            "package.json": "Node", "pnpm-lock.yaml": "Node (pnpm)", "yarn.lock": "Node (yarn)",
            "go.mod": "Go", "pom.xml": "Java (Maven)", "build.gradle": "Java/Kotlin (Gradle)",
            "build.gradle.kts": "Java/Kotlin (Gradle)", "Cargo.toml": "Rust", "composer.json": "PHP",
            "Gemfile": "Ruby", "Dockerfile": "Docker", "docker-compose.yml": "Docker Compose",
            "Makefile": "make"}
ESTENSIONI_MANIFEST = {".sln": ".NET", ".csproj": ".NET", ".tf": "Terraform"}
ENTRY = {"main.py", "app.py", "manage.py", "__main__.py", "index.js", "index.ts", "server.js", "server.ts",
         "main.go", "Program.cs", "Main.java", "Application.java", "main.rs", "lib.rs"}
TEST_DIRS = {"tests", "test", "__tests__", "spec", "e2e"}


def elenco_file(root: Path) -> list[str]:
    r = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode == 0 and r.stdout.strip():
        return sorted(f for f in r.stdout.splitlines() if not SALTA & set(Path(f).parts))
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                  if p.is_file() and not SALTA & set(p.relative_to(root).parts))


def righe(p: Path) -> int:
    try:
        if p.stat().st_size > 2_000_000:
            return 0
        with p.open(encoding="utf-8", errors="ignore") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def scansiona(root: Path) -> dict:
    files = elenco_file(root)
    ling_file, ling_righe = Counter(), Counter()
    stack, entry, test_dirs, ci, docs, top = set(), [], set(), [], [], Counter()
    for f in files:
        p = Path(f)
        nome, ext = p.name, p.suffix.lower()
        top[p.parts[0] if len(p.parts) > 1 else "(radice)"] += 1
        if nome in MANIFEST:
            stack.add(MANIFEST[nome])
        if ext in ESTENSIONI_MANIFEST:
            stack.add(ESTENSIONI_MANIFEST[ext])
        if ext in LINGUAGGI:
            ling_file[LINGUAGGI[ext]] += 1
            ling_righe[LINGUAGGI[ext]] += righe(root / f)
        if nome in ENTRY:
            entry.append(f)
        test_dirs.update(part for part in p.parts[:-1] if part in TEST_DIRS)
        if f.startswith(".github/workflows/") or nome in ("Jenkinsfile", ".gitlab-ci.yml", "azure-pipelines.yml"):
            ci.append(f)
        if ext == ".md" and (len(p.parts) == 1 or p.parts[0] == "docs"):
            docs.append(f)
    return {
        "file_totali": len(files),
        "stack": sorted(stack),
        "linguaggi": [{"nome": n, "file": ling_file[n], "righe": ling_righe[n]} for n, _ in ling_righe.most_common()],
        "primo_livello": [{"percorso": k, "file": v} for k, v in top.most_common()],
        "cartelle_test": sorted(test_dirs),
        "ci": ci,
        "entry_point_probabili": entry[:20],
        "documentazione": docs[:30],
    }


def stampa(r: dict) -> None:
    print(f"File totali: {r['file_totali']}")
    print("Stack rilevato: " + (", ".join(r["stack"]) or "(nessun manifest riconosciuto)"))
    print("Linguaggi: " + (", ".join(f"{x['nome']} ({x['file']} file, {x['righe']} righe)" for x in r["linguaggi"]) or "(nessuno)"))
    print("Primo livello: " + ", ".join(f"{x['percorso']} ({x['file']})" for x in r["primo_livello"][:15]))
    print("Cartelle di test: " + (", ".join(r["cartelle_test"]) or "(nessuna)"))
    print("CI: " + (", ".join(r["ci"]) or "(nessuna)"))
    print("Entry point probabili: " + (", ".join(r["entry_point_probabili"]) or "(nessuno)"))
    print("Documentazione: " + (", ".join(r["documentazione"]) or "(nessuna)"))


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    root = Path(args[0]) if args else Path(".")
    if not root.is_dir():
        print(f"[ERRORE] cartella non trovata: {root}")
        return 2
    r = scansiona(root)
    print(json.dumps(r, ensure_ascii=False, indent=2)) if "--json" in argv else stampa(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
