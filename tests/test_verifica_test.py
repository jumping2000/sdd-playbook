"""Test della verifica dei test: report JUnit (trace_check, sync_check, loop) e approvazione dei test bloccati."""
from __future__ import annotations

import os
import sys
import unittest

from common import PLAN_OK, REVIEW_OK, SPEC_OK, TASKS_OK, TmpDir, carica, copia_script, esegui, repo_git, scrivi

spec_lint = carica("spec_lint")
trace_check = carica("trace_check")
state = carica("state")
PY = os.path.basename(sys.executable)


def junit(*casi: tuple[str, str, str]) -> str:
    """Report JUnit con casi (classname, nome, esito: passato | fallito | saltato)."""
    figlio = {"passato": "", "fallito": "<failure message='x'/>", "saltato": "<skipped/>"}
    righe = "".join(f'<testcase classname="{c}" name="{n}">{figlio[e]}</testcase>' for c, n, e in casi)
    return f'<?xml version="1.0"?><testsuites><testsuite name="s">{righe}</testsuite></testsuites>'


def cli(d, script: str, *args: str):
    return esegui([sys.executable, f"scripts/{script}.py", *args], d)


class TestJUnit(unittest.TestCase):
    def prepara(self, d, report: str):
        copia_script(d)
        scrivi(d, "spec.md", SPEC_OK)
        scrivi(d, "tests/test_export.py", "def test_AC_001_ok(): pass\ndef test_AC_002_errore(): pass\n")
        scrivi(d, "reports/junit.xml", report)

    def test_ac_verificati_dal_report(self):
        with TmpDir() as d:
            self.prepara(d, junit(("tests.test_export", "test_AC_001_ok", "passato"),
                                  ("tests.test_export", "test_AC_002_errore", "passato")))
            r = cli(d, "trace_check", "spec.md", "--junit", "reports")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("verificato sul report", r.stdout)

    def test_citato_ma_fallito_saltato_o_non_eseguito(self):
        with TmpDir() as d:
            self.prepara(d, junit(("tests.test_export", "test_AC_001_ok", "fallito"),
                                  ("tests.test_export", "test_AC_002_errore", "saltato")))
            r = cli(d, "trace_check", "spec.md", "--junit", "reports/junit.xml")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("AC-001: test falliti nel report", r.stdout)
            self.assertIn("AC-002: nessun test eseguito e passato nel report (1 saltati)", r.stdout)
            self.assertEqual(cli(d, "trace_check", "spec.md").returncode, 0)  # senza report basta la citazione
            scrivi(d, "reports/junit.xml", junit(("tests.test_export", "test_AC_001_ok", "passato")))
            r = cli(d, "trace_check", "spec.md", "--junit", "reports/junit.xml")
            self.assertIn("AC-002: nessun test eseguito e passato nel report\n", r.stdout)

    def test_report_illeggibile(self):
        with TmpDir() as d:
            self.prepara(d, "<testsuite><rotto")
            r = cli(d, "trace_check", "spec.md", "--junit", "reports/junit.xml")
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("report JUnit illeggibile", r.stdout)

    def test_attribuzione_con_piu_spec(self):
        spec2 = SPEC_OK.replace("SPEC-001", "SPEC-002")
        with TmpDir() as d:
            scrivi(d, "tests/test_uno.py", "# SPEC-001\ndef test_AC_001(): pass\n")
            scrivi(d, "tests/test_due.py", "# SPEC-002\ndef test_AC_001(): pass\n")
            report = d / "junit.xml"
            report.write_text(junit(("tests.test_due", "test_AC_001", "passato"),
                                    ("", "SPEC-001/AC-002 errore chiaro", "passato"),
                                    ("com.acme.test_uno", "test_AC_001", "fallito")), encoding="utf-8")
            es = trace_check.esecuzioni(SPEC_OK, [d / "tests"], [report], spec_unica=False)
            self.assertEqual(es["AC-001"]["fallito"], ["com.acme.test_uno::test_AC_001"])
            self.assertEqual(es["AC-001"]["passato"], [])  # il caso di test_due è di SPEC-002
            self.assertEqual(es["AC-002"]["passato"], ["SPEC-001/AC-002 errore chiaro"])
            es2 = trace_check.esecuzioni(spec2, [d / "tests"], [report], spec_unica=False)
            self.assertEqual(es2["AC-001"]["passato"], ["tests.test_due::test_AC_001"])


class TestApprovazioneDeiTest(unittest.TestCase):
    CHIUSA = TASKS_OK.replace("[ ] T-01", "[x] T-01")

    def test_test_da_approvare(self):
        self.assertEqual(spec_lint.test_da_approvare(self.CHIUSA), [])
        senza = self.CHIUSA.replace(" — test approvati: Anna Rossi, 2026-10-19", "")
        self.assertEqual(spec_lint.test_da_approvare(senza), ["T-01"])
        self.assertEqual(spec_lint.test_da_approvare(senza.replace("— copre", "— test approvati: <nome> — copre")),
                         ["T-01"])
        self.assertEqual(spec_lint.test_da_approvare(TASKS_OK.replace(" — test approvati: Anna Rossi, 2026-10-19", "")),
                         [])  # task ancora aperta: niente da approvare

    def test_state_chiede_l_approvazione(self):
        senza = self.CHIUSA.replace(" — test approvati: Anna Rossi, 2026-10-19", "")
        with TmpDir() as d:
            scrivi(d, "AGENTS.md")
            scrivi(d, "scripts/verify.py")
            scrivi(d, "docs/specs/001-x/spec.md", SPEC_OK)
            scrivi(d, "docs/specs/001-x/plan.md", PLAN_OK)
            scrivi(d, "docs/specs/001-x/tasks.md", senza)
            p = state.analizza(d)["prossimo"]
            self.assertEqual(p["skill"], "sdlc-tests-from-ac")
            self.assertIn("T-01 da far approvare", p["motivo"])
            scrivi(d, "docs/specs/001-x/tasks.md", self.CHIUSA)
            self.assertEqual(state.analizza(d)["prossimo"]["skill"], "sdlc-implement")

    def test_sync_check_e_livello_s(self):
        senza = TASKS_OK.replace(" — test approvati: Anna Rossi, 2026-10-19", "").replace("[ ]", "[x]")
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, "docs/specs/001-x/spec.md", SPEC_OK.replace("Stato: approved", "Stato: implemented"))
            scrivi(d, "docs/specs/001-x/tasks.md", senza)
            scrivi(d, "docs/specs/001-x/review.md", REVIEW_OK)
            r = cli(d, "sync_check", "docs/specs/001-x")
            self.assertIn("test bloccati senza approvazione umana ('test approvati:'): T-01", r.stdout)


AGENTE_TEST_ROSSI = (
    "import sys\n"
    "sys.stdin.read()\n"
    "p = 'docs/specs/001-x/tasks.md'\n"
    "t = open(p, encoding='utf-8').read()\n"
    "open(p, 'w', encoding='utf-8').write(t.replace('[ ] T-01', '[x] T-01', 1))\n"
)


class TestLoopApprovazione(unittest.TestCase):
    def progetto(self, d, tasks: str, spec: str | None = None):
        copia_script(d, ["loop"])
        scrivi(d, "scripts/verify.py", "import sys\nsys.exit(1)\n")
        scrivi(d, "docs/specs/001-x/tasks.md", tasks)
        scrivi(d, "docs/specs/001-x/PROMPT.md", "prompt\n")
        if spec:
            scrivi(d, "docs/specs/001-x/spec.md", spec)
        scrivi(d, "agent.py", AGENTE_TEST_ROSSI)
        repo_git(d, "feature/x")

    def loop(self, d, *extra: str):
        env = {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]}
        return esegui([sys.executable, "scripts/loop.py", "docs/specs/001-x", "--agent", f"{PY} agent.py", *extra],
                      d, env=env)

    TASKS = "- [ ] T-01 Test — verifica: `t` (atteso: rosso) — copre: AC-001\n- [ ] T-02 Implementa\n"

    def test_pausa_dopo_i_test_rossi(self):
        with TmpDir() as d:
            self.progetto(d, self.TASKS)
            r = self.loop(d, "--allow-red-baseline", "--max", "5")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("Pausa: i test bloccati di T-01 vanno approvati", r.stdout)
            r = self.loop(d, "--dry-run")
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("aspettano l'approvazione umana", r.stdout)

    def test_livello_s_non_si_ferma(self):
        with TmpDir() as d:
            self.progetto(d, self.TASKS, spec="# SPEC-001: x\n\n- Livello: S\n")
            r = self.loop(d, "--allow-red-baseline", "--max", "2")
            self.assertNotIn("Pausa", r.stdout)
            self.assertIn("Tetto raggiunto", r.stdout)


if __name__ == "__main__":
    unittest.main()
