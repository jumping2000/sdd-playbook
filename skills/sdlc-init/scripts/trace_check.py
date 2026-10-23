#!/usr/bin/env python3
"""Tracciabilità AC -> test: ogni acceptance criterion della spec deve comparire in almeno un test.

Uso:
  python scripts/trace_check.py docs/specs/001-x/spec.md
  python scripts/trace_check.py docs/specs/001-x/spec.md --tests tests integration
  python scripts/trace_check.py docs/specs/001-x/spec.md --warn-only

Un test "cita" un AC se nel nome, in un commento o in una stringa compare AC-001, AC_001 o AC001.
Cartelle di test cercate di default: tests, test, __tests__, spec, src/test.
Exit code: 0 tutti gli AC citati; 1 AC senza test; 2 uso errato.
Solo stdlib, cross-platform.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_lint  # noqa: E402

ESTENSIONI = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".cs", ".go", ".rb", ".php",
              ".rs", ".feature", ".robot", ".cpp", ".c", ".swift"}
CARTELLE = ("tests", "test", "__tests__", "spec", "src/test")
SALTA = {"node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build", "target", "bin", "obj"}
AC_REF = re.compile(r"(?<![A-Za-z0-9])AC[-_]?0*(\d+)(?!\d)")


def raccogli(cartelle: list[Path]) -> dict[int, list[str]]:
    """Numero AC -> posizioni (file:riga) in cui è citato."""
    trovati: dict[int, list[str]] = {}
    for base in cartelle:
        for f in sorted(base.rglob("*")):
            if not f.is_file() or f.suffix not in ESTENSIONI or SALTA & set(f.parts):
                continue
            for n, riga in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                for m in AC_REF.finditer(riga):
                    trovati.setdefault(int(m.group(1)), []).append(f"{f.as_posix()}:{n}")
    return trovati


def analizza(spec_text: str, cartelle: list[Path]):
    _, acs = spec_lint.parse_spec(spec_text)
    trovati = raccogli(cartelle)
    coperti = {ac: trovati.get(int(ac[3:]), []) for ac in acs}
    senza = [ac for ac, pos in coperti.items() if not pos]
    orfani = sorted(n for n in trovati if f"AC-{n:03d}" not in acs and not any(int(a[3:]) == n for a in acs))
    req_coperti: dict[str, bool] = {}
    for ac, refs in acs.items():
        for r in refs:
            req_coperti[r] = req_coperti.get(r, False) or bool(coperti[ac])
    return acs, coperti, senza, orfani, req_coperti


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("--"):
        print(__doc__)
        return 2
    spec_path, opts = argv[0], argv[1:]
    warn_only = "--warn-only" in opts
    dirs: list[str] = []
    if "--tests" in opts:
        for o in opts[opts.index("--tests") + 1:]:
            if o.startswith("--"):
                break
            dirs.append(o)
    cartelle = [Path(d) for d in dirs] if dirs else [Path(c) for c in CARTELLE if Path(c).is_dir()]
    cartelle = [c for c in cartelle if c.is_dir()]
    if not cartelle:
        print("[ERRORE] nessuna cartella di test trovata: usa --tests <cartella>")
        return 2
    acs, coperti, senza, orfani, req_coperti = analizza(Path(spec_path).read_text(encoding="utf-8"), cartelle)
    for ac in acs:
        pos = coperti[ac]
        print(f"{ac}: " + (f"{len(pos)} riferimenti (es. {pos[0]})" if pos else "NESSUN TEST"))
    for req, ok in req_coperti.items():
        if not ok:
            print(f"[ERRORE] {req}: nessuno dei suoi AC ha test")
    if orfani:
        print("[WARN] ID citati nei test ma assenti dalla spec: " + ", ".join(f"AC-{n:03d}" for n in orfani)
              + " (possono appartenere ad altre spec)")
    print("TRACE: " + ("OK" if not senza else f"{len(senza)} AC senza test: {', '.join(senza)}"))
    return 0 if (not senza or warn_only) else 1


if __name__ == "__main__":
    for flusso in (sys.stdout, sys.stderr):  # UTF-8 anche con console cp1252 (Windows)
        flusso.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
