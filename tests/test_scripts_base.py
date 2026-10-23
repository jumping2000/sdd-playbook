"""Test di verify.py, spec_lint.py e state.py."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

from common import (AREA_OK, PLAN_OK, REVIEW_OK, ROOT, SCRIPTS, SPEC_OK, TASKS_OK, TmpDir, carica, copia_script,
                    esegui, leggi, scrivi)

spec_lint = carica("spec_lint")
state = carica("state")


class TestSpecLint(unittest.TestCase):
    def test_spec_valida(self):
        self.assertEqual(spec_lint.lint_spec(SPEC_OK)[0], [])

    def test_template_in_bozza_segnala_il_non_scope(self):
        err, _ = spec_lint.lint_spec(leggi("skills/sdlc-spec/references/spec-template.md"))
        self.assertTrue(any("Non-scope" in e for e in err))

    def test_approvata_senza_approvatore(self):
        err, _ = spec_lint.lint_spec(SPEC_OK.replace("Anna Rossi, 2026-10-19", "<nome, aaaa-mm-gg>"))
        self.assertTrue(any("Approvata da" in e for e in err))

    def test_req_senza_ac(self):
        t = SPEC_OK.replace("- REQ-001 (funzionale): il report si esporta in CSV",
                            "- REQ-001 (funzionale): a\n- REQ-002 (funzionale): b")
        self.assertTrue(any("REQ-002" in e for e in spec_lint.lint_spec(t)[0]))

    def test_ac_con_req_inesistente(self):
        err, _ = spec_lint.lint_spec(SPEC_OK.replace("AC-002 [REQ-001, errore]", "AC-002 [REQ-009]"))
        self.assertTrue(any("REQ-009" in e for e in err))

    def test_domande_aperte_su_spec_approvata(self):
        err, _ = spec_lint.lint_spec(SPEC_OK.replace("- nessuna", "- Quale separatore?"))
        self.assertTrue(any("domande aperte" in e for e in err))

    def test_non_scope_vuoto(self):
        err, _ = spec_lint.lint_spec(SPEC_OK.replace("nessuna modifica al formato PDF", ""))
        self.assertTrue(any("Non-scope" in e for e in err))

    def test_piano(self):
        self.assertEqual(spec_lint.lint_plan(SPEC_OK, PLAN_OK)[0], [])
        err, _ = spec_lint.lint_plan(SPEC_OK, PLAN_OK.replace("AC-002", "AC-XXX"))
        self.assertTrue(any("AC-002" in e for e in err))
        _, avv = spec_lint.lint_plan(SPEC_OK, PLAN_OK.replace("Anna Rossi, 2026-10-19", "<nome>"))
        self.assertTrue(avv)

    def test_piano_cerca_gli_id_esatti_nella_strategia_di_test(self):
        citato_altrove = PLAN_OK.replace("| AC-002 | unit |\n", "") + "\n## Rischi\n- AC-002 da valutare\n"
        self.assertTrue(any("AC-002" in e for e in spec_lint.lint_plan(SPEC_OK, citato_altrove)[0]))
        self.assertTrue(any("AC-001" in e for e in spec_lint.lint_plan(SPEC_OK, PLAN_OK.replace("| AC-001 |", "| AC-0011 |"))[0]))
        senza = PLAN_OK.replace("## Strategia di test (mappata sugli AC)", "## Note")
        self.assertTrue(any("Strategia di test" in e for e in spec_lint.lint_plan(SPEC_OK, senza)[0]))

    def test_task(self):
        self.assertEqual(spec_lint.lint_tasks(SPEC_OK, TASKS_OK)[0], [])
        err, _ = spec_lint.lint_tasks(SPEC_OK, TASKS_OK.replace("- [ ] T-DOC Documentazione\n", ""))
        self.assertTrue(any("T-DOC" in e for e in err))
        err, _ = spec_lint.lint_tasks(SPEC_OK, TASKS_OK.replace("— verifica: `pytest` ", ""))
        self.assertTrue(any("T-02" in e and "verifica" in e for e in err))
        err, _ = spec_lint.lint_tasks(SPEC_OK, TASKS_OK.replace("copre: AC-001, AC-002", "copre: AC-001"))
        self.assertTrue(any("AC-002" in e and "coperto" in e for e in err))
        err, _ = spec_lint.lint_tasks(SPEC_OK, TASKS_OK.replace("`pytest`", "`<comando test mirato>`"))
        self.assertIn("T-02: segnaposto non compilato <comando test mirato>", err)

    def test_cli(self):
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, "spec.md", SPEC_OK)
            self.assertEqual(esegui([sys.executable, "scripts/spec_lint.py", "spec.md"], d).returncode, 0)
            scrivi(d, "spec.md", SPEC_OK.replace("- nessuna", "- Quale separatore?"))
            self.assertEqual(esegui([sys.executable, "scripts/spec_lint.py", "spec.md"], d).returncode, 1)
            self.assertEqual(esegui([sys.executable, "scripts/spec_lint.py"], d).returncode, 2)


class TestVerify(unittest.TestCase):
    def prova(self, steps: str, args: list[str]):
        testo = (SCRIPTS / "verify.py").read_text(encoding="utf-8")
        ini, fin = testo.index("STEPS = ["), testo.index("def run_step")
        with TmpDir() as d:
            scrivi(d, "scripts/verify.py", testo[:ini] + "STEPS = " + steps + "\n\n\n" + testo[fin:])
            return esegui([sys.executable, "scripts/verify.py", *args], d)

    OK, KO = '[sys.executable, "-c", "pass"]', '[sys.executable, "-c", "import sys; sys.exit(1)"]'

    def test_verde_e_rosso(self):
        self.assertEqual(self.prova(f'[("a", {self.OK}, True), ("b", {self.OK}, False)]', []).returncode, 0)
        r = self.prova(f'[("a", {self.OK}, True), ("b", {self.KO}, False)]', [])
        self.assertEqual(r.returncode, 1)
        self.assertIn("ROSSO -> b", r.stdout)

    def test_fast_e_selezione(self):
        s = f'[("a", {self.OK}, True), ("b", {self.KO}, False)]'
        self.assertEqual(self.prova(s, ["--fast"]).returncode, 0)
        self.assertEqual(self.prova(s, ["a"]).returncode, 0)

    def test_comando_mancante(self):
        r = self.prova('[("x", ["comando-che-non-esiste-xyz"], True)]', [])
        self.assertEqual(r.returncode, 1)
        self.assertIn("non trovato", r.stdout)


class TestState(unittest.TestCase):
    def prossimo(self, setup) -> dict:
        with TmpDir() as d:
            setup(d)
            return state.analizza(d)["prossimo"]

    @staticmethod
    def init(r: Path):
        scrivi(r, "AGENTS.md")
        scrivi(r, "scripts/verify.py")

    def con_spec(self, r: Path, plan=True, tasks=None, review=None, stato="approved"):
        self.init(r)
        scrivi(r, "docs/specs/001-x/spec.md", SPEC_OK.replace("approved", stato))
        if plan:
            scrivi(r, "docs/specs/001-x/plan.md", PLAN_OK)
        if tasks is not None:
            scrivi(r, "docs/specs/001-x/tasks.md", tasks)
        if review is not None:
            scrivi(r, "docs/specs/001-x/review.md", review)

    def test_progressione(self):
        self.assertEqual(self.prossimo(lambda r: None)["skill"], "sdlc-init")
        self.assertEqual(self.prossimo(self.init)["skill"], "sdlc-spec")
        self.assertEqual(self.prossimo(lambda r: self.con_spec(r, plan=False))["skill"], "sdlc-plan")
        self.assertEqual(self.prossimo(lambda r: self.con_spec(r))["skill"], "sdlc-tasks")
        p = self.prossimo(lambda r: self.con_spec(r, tasks=TASKS_OK))
        self.assertEqual(p["skill"], "sdlc-implement")
        self.assertIn("T-01", p["motivo"])
        fatte = TASKS_OK.replace("[ ] T-01", "[x] T-01").replace("[ ] T-02", "[x] T-02")
        self.assertEqual(self.prossimo(lambda r: self.con_spec(r, tasks=fatte))["skill"], "sdlc-review-diff")
        self.assertEqual(self.prossimo(lambda r: self.con_spec(r, tasks=fatte, review=REVIEW_OK))["skill"], "sdlc-docs")
        senza_doc = fatte.replace("[ ] T-DOC", "[x] T-DOC")
        self.assertEqual(self.prossimo(lambda r: self.con_spec(r, tasks=senza_doc, review=REVIEW_OK))["skill"], "sdlc-sync")
        nc = REVIEW_OK.replace("Esito: conforme", "Esito: non conforme")
        self.assertEqual(self.prossimo(lambda r: self.con_spec(r, tasks=fatte, review=nc))["skill"], "sdlc-implement")
        tutte = fatte.replace("[ ]", "[x]")
        self.assertEqual(self.prossimo(lambda r: self.con_spec(r, tasks=tutte, review=REVIEW_OK, stato="implemented"))["skill"], "sdlc-spec")

    def test_piano_non_approvato(self):
        def setup(r):
            self.con_spec(r)
            scrivi(r, "docs/specs/001-x/plan.md", PLAN_OK.replace("Anna Rossi, 2026-10-19", "<nome>"))
        self.assertEqual(self.prossimo(setup)["skill"], "sdlc-plan")

    def test_brownfield_suggerisce_la_mappa(self):
        def setup(r):
            self.init(r)
            for i in range(4):
                scrivi(r, f"src/m{i}.py")
        self.assertEqual(self.prossimo(setup)["skill"], "sdlc-map-codebase")

        def con_mappa(r):
            setup(r)
            scrivi(r, "docs/system/mappa.md")
        self.assertEqual(self.prossimo(con_mappa)["skill"], "sdlc-spec")

    def test_script_e_docs_non_contano_come_codice(self):
        def setup(r):
            self.init(r)
            for i in range(5):
                scrivi(r, f"scripts/s{i}.py")
        self.assertEqual(self.prossimo(setup)["skill"], "sdlc-spec")

    def test_bug_non_verificati(self):
        with TmpDir() as d:
            self.init(d)
            scrivi(d, "docs/bugs/BUG-001.md", "- Stato: aperto\n")
            scrivi(d, "docs/bugs/BUG-002.md", "- Stato: verificato\n")
            self.assertEqual([b["file"] for b in state.analizza(d)["bug_aperti"]], ["BUG-001.md"])

    def test_cli_json(self):
        with TmpDir() as d:
            copia_script(d)
            r = esegui([sys.executable, "scripts/state.py", "--json"], d)
            self.assertEqual(r.returncode, 0)
            self.assertIn("sdlc-init", r.stdout)


if __name__ == "__main__":
    unittest.main()
