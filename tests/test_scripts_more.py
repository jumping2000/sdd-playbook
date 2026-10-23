"""Test di trace_check, bug_lint, diff_scope, scan_repo, docs_check, sync_check."""
from __future__ import annotations

import sys
import unittest

from common import (AREA_OK, BUG_OK, PLAN_OK, REVIEW_OK, SPEC_OK, TASKS_OK, TmpDir, carica, copia_script, esegui,
                    git, leggi, repo_git, scrivi)

bug_lint = carica("bug_lint")
trace_check = carica("trace_check")
diff_scope = carica("diff_scope")
scan_repo = carica("scan_repo")


def cli(d, script: str, *args: str):
    return esegui([sys.executable, f"scripts/{script}.py", *args], d)


class TestTraceCheck(unittest.TestCase):
    def test_copertura(self):
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, "spec.md", SPEC_OK)
            scrivi(d, "tests/test_a.py", "def test_AC_001_ok(): pass\n# AC-099 di un'altra spec\n")
            r = cli(d, "trace_check", "spec.md")
            self.assertEqual(r.returncode, 1)
            self.assertIn("AC-002: NESSUN TEST", r.stdout)
            self.assertIn("AC-099", r.stdout)
            self.assertEqual(cli(d, "trace_check", "spec.md", "--warn-only").returncode, 0)
            scrivi(d, "tests/test_b.py", "it('AC-002: errore chiaro')\n".replace("it(", "# ").replace("')", ""))
            self.assertEqual(cli(d, "trace_check", "spec.md").returncode, 0)

    def test_formati_dell_id(self):
        with TmpDir() as d:
            scrivi(d, "tests/t.py", "def test_AC001(): pass\ndef test_x_AC_002_y(): pass\n# ACCESS 12\n")
            trovati, _, _ = trace_check.raccogli([d / "tests"], 1, spec_unica=True)
            self.assertEqual(sorted(trovati), [1, 2])
            scrivi(d, "tests/q.py", "def test_SPEC001_AC003(): pass\ndef test_SPEC_001_AC_004(): pass\n"
                                    "it('SPEC-001/AC-005: x')\n# SPEC-001-AC-006\n# SPEC-002/AC-007\n")
            trovati, _, _ = trace_check.raccogli([d / "tests"], 1, spec_unica=False)
            self.assertEqual(sorted(trovati), [3, 4, 5, 6])

    def test_ac_qualificati_con_piu_spec(self):
        spec2 = SPEC_OK.replace("SPEC-001", "SPEC-002")
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, "docs/specs/001-a/spec.md", SPEC_OK)
            scrivi(d, "docs/specs/002-b/spec.md", spec2)
            # test di SPEC-001 senza dichiarazione: con due spec sono ambigui e non coprono SPEC-002
            scrivi(d, "tests/test_vecchi.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")
            r = cli(d, "trace_check", "docs/specs/002-b/spec.md")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("TRACE: 2 AC senza test: AC-001, AC-002", r.stdout)
            self.assertIn("2 citazioni AC senza spec", r.stdout)
            # un file dichiarato per SPEC-001 non copre SPEC-002
            scrivi(d, "tests/test_vecchi.py", "# SPEC-001\ndef test_AC_001(): pass\ndef test_AC_002(): pass\n")
            self.assertEqual(cli(d, "trace_check", "docs/specs/002-b/spec.md").returncode, 1)
            self.assertEqual(cli(d, "trace_check", "docs/specs/001-a/spec.md").returncode, 0)
            # file dichiarato per SPEC-002 e citazione qualificata in un file qualsiasi
            scrivi(d, "tests/test_b.py", "# SPEC-002\ndef test_AC_001(): pass\n")
            scrivi(d, "tests/test_c.py", "def test_SPEC002_AC002_errore(): pass\n")
            r = cli(d, "trace_check", "docs/specs/002-b/spec.md")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertNotIn("citazioni AC senza spec", r.stdout)

    def test_promemoria_non_contano(self):
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, "spec.md", SPEC_OK)
            scrivi(d, "tests/test_a.py", "def test_AC_001(): pass\n# TODO AC-002 da scrivere\n")
            r = cli(d, "trace_check", "spec.md")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("AC-002: NESSUN TEST", r.stdout)
            self.assertIn("1 citazioni su righe TODO/FIXME/XXX ignorate", r.stdout)

    def test_spec_senza_id_nel_titolo(self):
        senza_id = SPEC_OK.replace("# SPEC-001: Esempio", "# Esempio")
        with TmpDir() as d:
            scrivi(d, "tests/t.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")
            self.assertEqual(trace_check.analizza(senza_id, [d / "tests"], spec_unica=True).senza, [])
            esito = trace_check.analizza(senza_id, [d / "tests"], spec_unica=False)
            self.assertEqual(esito.senza, ["AC-001", "AC-002"])
            self.assertEqual(len(esito.ambigui), 2)

    def test_senza_cartella_di_test(self):
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, "spec.md", SPEC_OK)
            self.assertEqual(cli(d, "trace_check", "spec.md").returncode, 2)


class TestBugLint(unittest.TestCase):
    def test_bug_completo(self):
        self.assertEqual(bug_lint.lint(BUG_OK), [])

    def test_template_aperto_chiede_la_riproduzione(self):
        err = bug_lint.lint(leggi("skills/sdlc-bugfix/references/bugfix-template.md"))
        self.assertEqual(err, ["Riproduzione non compilata"])

    def test_requisiti_crescono_con_lo_stato(self):
        diag = BUG_OK.replace("Stato: verificato", "Stato: diagnosticato")
        self.assertEqual(bug_lint.lint(diag), [])
        senza_rosso = diag.replace("`tests/test_export.py::test_virgola`", "`<percorso>`")
        self.assertTrue(any("test rosso" in e.lower() for e in bug_lint.lint(senza_rosso)))
        senza_invariato = diag.replace("- Il separatore resta la virgola", "- <elenco>")
        self.assertTrue(any("NON cambiare" in e for e in bug_lint.lint(senza_invariato)))
        corretto = BUG_OK.replace("Stato: verificato", "Stato: corretto")
        self.assertEqual(bug_lint.lint(corretto), [])
        self.assertTrue(any("non-regressione" in e for e in bug_lint.lint(
            corretto.replace("`tests/test_export.py::test_separatore`", "`<x>`"))))
        self.assertTrue(any("non spuntate" in e for e in bug_lint.lint(BUG_OK.replace("[x] verify", "[ ] verify"))))

    def test_stato_non_valido(self):
        self.assertTrue(bug_lint.lint(BUG_OK.replace("Stato: verificato", "Stato: boh")))


class TestDiffScope(unittest.TestCase):
    def prepara(self, d, agents="- Non modificare: legacy/\n"):
        repo_git(d, "main")
        scrivi(d, "AGENTS.md", "# A\n" + agents)
        scrivi(d, "legacy/a.py", "v1\n")
        scrivi(d, "src/old.py", "v1\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feature/x")
        scrivi(d, "docs/specs/001-x/plan.md", PLAN_OK)

    def test_violazioni_e_fuori_piano(self):
        with TmpDir() as d:
            copia_script(d)
            self.prepara(d)
            scrivi(d, "src/export.py", "nuovo\n")
            scrivi(d, "legacy/a.py", "v2\n")
            scrivi(d, "altro.py", "x\n")
            scrivi(d, "docs/system/export.md", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x", "--base", "main")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("zona vietata (AGENTS.md): legacy/a.py", r.stdout)
            self.assertIn("[WARN] file fuori piano: altro.py", r.stdout)
            self.assertNotIn("src/export.py\n[WARN]", r.stdout)
            self.assertNotIn("fuori piano: docs/system", r.stdout)
            self.assertNotIn("fuori piano: src/export.py", r.stdout)
            self.assertIn("nel piano ma non toccato: tests/", r.stdout)

    def test_ok_e_strict(self):
        with TmpDir() as d:
            copia_script(d)
            self.prepara(d)
            scrivi(d, "src/export.py", "nuovo\n")
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)
            scrivi(d, "altro.py", "x\n")
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x", "--strict").returncode, 1)

    def test_senza_git_o_base(self):
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, "docs/specs/001-x/plan.md", PLAN_OK)
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 2)

    def test_percorsi(self):
        self.assertTrue(diff_scope.corrisponde("src/a/b.py", "src/"))
        self.assertTrue(diff_scope.corrisponde("src/a/b.py", "src/a"))
        self.assertTrue(diff_scope.corrisponde("src/a/b.py", "src/**/*.py"))
        self.assertFalse(diff_scope.corrisponde("srcx/b.py", "src"))
        self.assertEqual(diff_scope.percorsi_piano(PLAN_OK), ["src/export.py", "tests/"])
        self.assertEqual(diff_scope.percorsi_vietati("- Non modificare: `a/`, b.py; <x>\n"), ["a/", "b.py"])

    def test_percorsi_con_punto_iniziale(self):
        self.assertTrue(diff_scope.corrisponde(".github/workflows/ci.yml", ".github/"))
        self.assertTrue(diff_scope.corrisponde(".github/workflows/ci.yml", "./.github"))
        self.assertTrue(diff_scope.corrisponde(".env", ".env"))
        self.assertFalse(diff_scope.corrisponde("github/x.yml", ".github/"))

    def test_piano_annotazioni_e_colonna_dove(self):
        plan = ("## Componenti e file da creare/modificare\n- src/a.py (nuovo): x\n- `src/b c.py`: y\n"
                "- <percorso>: <cosa cambia>\n\n## Strategia di test (mappata sugli AC)\n"
                "| AC | Livello | Dove | Note |\n|---|---|---|---|\n| AC-001 | unit | `tests/test_a.py::test_x` | n |\n"
                "| AC-002 | e2e | manuale | n |\n| AC-003 | unit | tests/<file> | n |\n")
        self.assertEqual(diff_scope.percorsi_piano(plan), ["src/a.py", "src/b c.py", "tests/test_a.py"])
        agents = "- Non modificare: legacy/\n- Testo\n- Non modificare: .github/; migrations/\n"
        self.assertEqual(diff_scope.percorsi_vietati(agents), ["legacy/", ".github/", "migrations/"])

    def test_zone_vietate_con_punto_su_repo_reale(self):
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, ".github/workflows/ci.yml", "on: push\n")
            self.prepara(d, agents="- Non modificare: legacy/\n- Non modificare: .github/\n")
            scrivi(d, ".github/workflows/ci.yml", "on: [push, pull_request]\n")
            r = cli(d, "diff_scope", "docs/specs/001-x", "--base", "main")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("zona vietata (AGENTS.md): .github/workflows/ci.yml", r.stdout)

    def test_riconosce_i_file_di_test(self):
        for p in ("tests/x.py", "src/a.test.ts", "pkg/foo_test.go", "src/FooTest.java", "web/b.spec.js", "test_a.py"):
            self.assertTrue(diff_scope.e_un_test(p), p)
        for p in ("src/export.py", "src/latest.py", "docs/specs/001-x/spec.md", "src/contest.py"):
            self.assertFalse(diff_scope.e_un_test(p), p)


class TestTestLock(unittest.TestCase):
    """Test rossi bloccati con il trailer Test-Lock: l'implementazione non li può modificare."""

    def prepara(self, d):
        copia_script(d)
        repo_git(d, "main")
        scrivi(d, "AGENTS.md", "# A\n")
        scrivi(d, "src/old.py", "v1\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feature/x")
        scrivi(d, "docs/specs/001-x/plan.md", PLAN_OK)
        scrivi(d, "src/export.py", "def esporta(): raise NotImplementedError\n")
        scrivi(d, "tests/test_export.py", "def test_AC_001(): assert False\n")
        git(d, "add", "src/export.py", "tests/test_export.py")
        git(d, "commit", "-qm", "test rossi per AC-001", "-m", "Test-Lock: T-01")
        scrivi(d, "src/export.py", "def esporta(): return 'csv'\n")
        git(d, "add", "src/export.py")
        git(d, "commit", "-qm", "implementa T-02")

    def test_implementazione_senza_toccare_i_test(self):
        with TmpDir() as d:
            self.prepara(d)
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("test bloccati: 1", r.stdout)
            self.assertIn("file non di test in un commit Test-Lock, non bloccato: src/export.py", r.stdout)

    def test_modifica_ai_test_bloccati(self):
        with TmpDir() as d:
            self.prepara(d)
            scrivi(d, "tests/test_export.py", "def test_AC_001(): assert True\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("tests/test_export.py (non committato)", r.stdout)
            git(d, "commit", "-qam", "indebolisce il test")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("test bloccato (Test-Lock) modificato dopo il blocco: tests/test_export.py (commit", r.stdout)

    def test_correzione_esplicita_con_nuovo_blocco(self):
        with TmpDir() as d:
            self.prepara(d)
            scrivi(d, "tests/test_export.py", "def test_AC_001(): assert esporta() == 'csv'\n")
            git(d, "commit", "-qam", "corregge il test, approvato", "-m", "Test-Lock: T-01")
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)


class TestScanRepo(unittest.TestCase):
    def test_inventario(self):
        with TmpDir() as d:
            scrivi(d, "pyproject.toml")
            scrivi(d, "src/main.py", "a\nb\nc\n")
            scrivi(d, "src/util.py", "x\n")
            scrivi(d, "tests/test_a.py")
            scrivi(d, "README.md")
            scrivi(d, ".github/workflows/ci.yml")
            scrivi(d, "node_modules/x/index.js", "ignorato\n")
            r = scan_repo.scansiona(d)
            self.assertEqual(r["stack"], ["Python"])
            self.assertEqual(r["linguaggi"][0], {"nome": "Python", "file": 3, "righe": 5})
            self.assertEqual(r["cartelle_test"], ["tests"])
            self.assertEqual(r["entry_point_probabili"], ["src/main.py"])
            self.assertEqual(r["ci"], [".github/workflows/ci.yml"])
            self.assertEqual(r["documentazione"], ["README.md"])

    def test_cli_json_e_cartella_inesistente(self):
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, "a.py")
            self.assertIn('"file_totali"', cli(d, "scan_repo", ".", "--json").stdout)
            self.assertEqual(cli(d, "scan_repo", "non-esiste").returncode, 2)


class TestDocsCheck(unittest.TestCase):
    def test_link_ed_esempi(self):
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, "docs/b.md", "# B\n")
            scrivi(d, "README.md", "[ok](docs/b.md) [web](https://x.y) [anc](#a)\n```\n[nel codice](rotto.md)\n```\n`[inline](rotto2.md)`\n")
            self.assertEqual(cli(d, "docs_check", "README.md", "docs").returncode, 0)
            scrivi(d, "README.md", "[rotto](docs/non-esiste.md)\n")
            r = cli(d, "docs_check", "README.md")
            self.assertEqual(r.returncode, 1)
            self.assertIn("link rotto -> docs/non-esiste.md", r.stdout)

    def test_esempi_eseguibili(self):
        with TmpDir() as d:
            copia_script(d)
            ok = "```python\n# docs-check: run\nprint(1 + 1)\n```\n"
            ko = "```python\n# docs-check: run\nraise SystemExit(3)\n```\n"
            non_eseguito = "```python\nraise SystemExit(9)\n```\n"
            scrivi(d, "README.md", ok + non_eseguito)
            r = cli(d, "docs_check", "README.md", "--run-examples")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("1 esempi eseguiti", r.stdout)
            scrivi(d, "README.md", ok + ko)
            r = cli(d, "docs_check", "README.md", "--run-examples")
            self.assertEqual(r.returncode, 1)
            self.assertIn("esempio #2 fallito (exit 3)", r.stdout)
            self.assertEqual(cli(d, "docs_check", "README.md").returncode, 0)  # senza --run-examples non esegue


class TestSyncCheck(unittest.TestCase):
    def prepara(self, d):
        copia_script(d)
        f = "docs/specs/001-x/"
        scrivi(d, f + "spec.md", SPEC_OK.replace("Stato: approved", "Stato: implemented"))
        scrivi(d, f + "tasks.md", TASKS_OK.replace("[ ]", "[x]"))
        scrivi(d, f + "review.md", REVIEW_OK)
        scrivi(d, "docs/system/export.md", AREA_OK)
        scrivi(d, "tests/test_export.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")

    def test_allineato(self):
        with TmpDir() as d:
            self.prepara(d)
            r = cli(d, "sync_check", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_errori(self):
        casi = {
            "Stato è 'approved'": lambda d: scrivi(d, "docs/specs/001-x/spec.md", SPEC_OK),
            "task ancora aperte: T-SYNC": lambda d: scrivi(d, "docs/specs/001-x/tasks.md", TASKS_OK.replace("[ ] T-0", "[x] T-0").replace("[ ] T-DOC", "[x] T-DOC")),
            "review.md mancante": lambda d: (d / "docs/specs/001-x/review.md").unlink(),
            "Esito 'non conforme'": lambda d: scrivi(d, "docs/specs/001-x/review.md", REVIEW_OK.replace("Esito: conforme", "Esito: non conforme")),
            "'Decisione di' non compilata": lambda d: scrivi(d, "docs/specs/001-x/review.md", REVIEW_OK.replace("Anna Rossi, 2026-10-19", "<nome>")),
            "nessuna pagina d'area": lambda d: (d / "docs/system/export.md").unlink(),
            "'Ultimo allineamento' non compilato": lambda d: scrivi(d, "docs/system/export.md", AREA_OK.replace("2026-10-19\n- Spec", "<aaaa-mm-gg>\n- Spec")),
            "sezione mancante '## Vincoli e punti delicati'": lambda d: scrivi(d, "docs/system/export.md", AREA_OK.replace("## Vincoli e punti delicati", "## Altro")),
            "AC senza test: AC-002": lambda d: scrivi(d, "tests/test_export.py", "def test_AC_001(): pass\n"),
        }
        for atteso, rompi in casi.items():
            with self.subTest(atteso):
                with TmpDir() as d:
                    self.prepara(d)
                    rompi(d)
                    r = cli(d, "sync_check", "docs/specs/001-x")
                    self.assertEqual(r.returncode, 1, r.stdout)
                    self.assertIn(atteso, r.stdout)

    def test_test_di_un_altra_spec_non_bastano(self):
        with TmpDir() as d:
            self.prepara(d)
            scrivi(d, "docs/specs/002-y/spec.md", SPEC_OK.replace("SPEC-001", "SPEC-002"))
            scrivi(d, "tests/test_export.py", "# SPEC-002\ndef test_AC_001(): pass\ndef test_AC_002(): pass\n")
            r = cli(d, "sync_check", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("AC senza test: AC-001, AC-002", r.stdout)
            scrivi(d, "tests/test_export.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")
            self.assertIn("citazioni ambigue: usa SPEC-001/AC-nnn", cli(d, "sync_check", "docs/specs/001-x").stdout)
            scrivi(d, "tests/test_export.py", "def test_SPEC001_AC001(): pass\ndef test_SPEC001_AC002(): pass\n")
            self.assertEqual(cli(d, "sync_check", "docs/specs/001-x").returncode, 0)

    def test_output_utf8_anche_con_console_cp1252(self):
        with TmpDir() as d:
            self.prepara(d)
            scrivi(d, "docs/specs/001-x/spec.md", SPEC_OK)
            r = esegui([sys.executable, "scripts/sync_check.py", "docs/specs/001-x"], d,
                       env={"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"})
            self.assertIsNotNone(r.stdout)
            self.assertIn("Stato è 'approved'", r.stdout)


if __name__ == "__main__":
    unittest.main()
