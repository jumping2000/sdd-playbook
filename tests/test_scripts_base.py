"""Test di verify.py, spec_lint.py e state.py."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

from common import (AREA_OK, PLAN_OK, REVIEW_OK, ROOT, SCRIPTS, SPEC_OK, TASKS_OK, TmpDir, carica, copia_script,
                    esegui, git, leggi, repo_git, scrivi)

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

    def test_id_con_data_e_cartella(self):
        con_data = SPEC_OK.replace("# SPEC-001: Esempio", "# SPEC-2026-10-24-export-csv: Esempio")
        self.assertEqual(spec_lint.id_spec(con_data), "2026-10-24-export-csv")
        self.assertEqual(spec_lint.lint_spec(con_data, "2026-10-24-export-csv")[0], [])
        self.assertTrue(any("diverso dal nome della cartella" in e
                            for e in spec_lint.lint_spec(con_data, "2026-10-24-export")[0]))
        data_errata = con_data.replace("2026-10-24", "2026-13-40")
        self.assertTrue(any("data iniziale non è valida" in e for e in spec_lint.lint_spec(data_errata)[0]))
        senza_id = SPEC_OK.replace("# SPEC-001: Esempio", "# Esempio")
        self.assertTrue(any("Titolo senza ID" in e for e in spec_lint.lint_spec(senza_id)[0]))
        self.assertEqual(spec_lint.lint_spec(SPEC_OK, "001-x")[0], [])  # i vecchi ID restano validi
        self.assertTrue(any("numero della cartella" in e for e in spec_lint.lint_spec(SPEC_OK, "002-x")[0]))
        self.assertEqual(spec_lint.chiave_id("SPEC_2026_10_24_Export_csv"[5:]), "2026-10-24-export-csv")
        self.assertEqual(spec_lint.chiave_id("007"), "7")

    def test_spec_in_revisione(self):
        rev = SPEC_OK.replace("Stato: approved", "Stato: in-revisione").replace("Esportare il report in CSV.",
                                                                              "Esportare il report in CSV e XLSX.")
        self.assertTrue(any("Revisioni" in e for e in spec_lint.lint_spec(rev)[0]))
        con_voce = rev + "\n## Revisioni\n- 2026-10-24: aggiunto XLSX, richiesto dal cliente\n"
        self.assertEqual(spec_lint.lint_spec(con_voce)[0], [])  # in revisione l'hash vecchio non conta

    def test_task_dalla_review_e_task_legate_al_piano(self):
        con_r = TASKS_OK + "- [ ] T-R01 Gestire il file vuoto — verifica: `pytest -k vuoto`\n"
        self.assertEqual(spec_lint.lint_tasks(SPEC_OK, con_r)[0], [])
        senza_verifica = TASKS_OK + "- [ ] T-R01 Gestire il file vuoto\n"
        self.assertTrue(any("T-R01" in e and "verifica" in e for e in spec_lint.lint_tasks(SPEC_OK, senza_verifica)[0]))
        self.assertTrue(spec_lint.tasks_su_piano(PLAN_OK, TASKS_OK)[1])  # senza 'Basato su piano': avviso
        legate = f"- Basato su piano: {spec_lint.impronta(PLAN_OK)}\n" + TASKS_OK
        self.assertEqual(spec_lint.tasks_su_piano(PLAN_OK, legate), ([], []))
        nuovo_piano = PLAN_OK.replace("nuova funzione di export", "export riscritto")
        self.assertTrue(spec_lint.tasks_su_piano(nuovo_piano, legate)[0])

    def test_hash_anti_deriva_della_spec(self):
        self.assertEqual(spec_lint.lint_spec(SPEC_OK.replace("Stato: approved", "Stato: implemented"))[0], [])
        modificata = SPEC_OK.replace("Esportare il report in CSV.", "Esportare il report in CSV e XLSX.")
        self.assertTrue(any("modificato dopo l'approvazione" in e for e in spec_lint.lint_spec(modificata)[0]))
        senza = "\n".join(r for r in SPEC_OK.splitlines() if not r.startswith("- Hash:"))
        self.assertTrue(any("senza '- Hash:'" in e for e in spec_lint.lint_spec(senza)[0]))
        bozza = senza.replace("Stato: approved", "Stato: draft")
        self.assertEqual(spec_lint.lint_spec(bozza)[0], [])
        self.assertEqual(spec_lint.impronta(SPEC_OK), spec_lint.impronta(SPEC_OK.replace("\n", "\r\n")))

    def test_piano_decade_se_cambia_la_spec(self):
        self.assertEqual(spec_lint.lint_plan(SPEC_OK, PLAN_OK)[0], [])
        nuova = SPEC_OK.replace("Esportare il report in CSV.", "Esportare il report.")
        self.assertTrue(any("altra versione della spec" in e for e in spec_lint.lint_plan(nuova, PLAN_OK)[0]))
        piano = PLAN_OK.replace("nuova funzione di export", "funzione di export riscritta")
        self.assertTrue(any("Piano: contenuto modificato" in e for e in spec_lint.lint_plan(SPEC_OK, piano)[0]))

    def test_hash_e_base_da_riga_di_comando(self):
        with TmpDir() as d:
            copia_script(d)
            repo_git(d, "main")
            scrivi(d, "docs/specs/001-x/spec.md", SPEC_OK)
            scrivi(d, "docs/specs/001-x/plan.md", PLAN_OK)
            r = esegui([sys.executable, "scripts/spec_lint.py", "docs/specs/001-x/spec.md", "--hash"], d)
            self.assertEqual(r.stdout.strip(), spec_lint.impronta(SPEC_OK))
            args = [sys.executable, "scripts/spec_lint.py", "docs/specs/001-x/spec.md", "--plan",
                    "docs/specs/001-x/plan.md", "--base", "main"]
            r = esegui(args, d)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("non è su main", r.stdout)
            git(d, "add", "-A")
            git(d, "commit", "-qm", "design approvato")
            git(d, "checkout", "-qb", "feature/x")
            self.assertEqual(esegui(args, d).returncode, 0)
            scrivi(d, "docs/specs/001-x/plan.md", PLAN_OK + "\n")
            self.assertEqual(esegui(args, d).returncode, 0)  # differenze di spazi finali non contano
            scrivi(d, "docs/specs/001-x/plan.md", PLAN_OK.replace("Anna Rossi", "Agente"))
            r = esegui(args, d)
            self.assertEqual(r.returncode, 1)
            self.assertIn("diverso dalla versione su main", r.stdout)

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
        p = self.prossimo(lambda r: self.con_spec(r, tasks=fatte, review=nc))
        self.assertEqual((p["skill"], "T-R" in p["motivo"]), ("sdlc-review-diff", True))
        con_r = fatte + "- [ ] T-R01 Correggi — verifica: `pytest`\n"
        self.assertEqual(self.prossimo(lambda r: self.con_spec(r, tasks=con_r, review=nc))["skill"], "sdlc-implement")
        r_fatte = con_r.replace("[ ] T-R01", "[x] T-R01")
        p = self.prossimo(lambda r: self.con_spec(r, tasks=r_fatte, review=nc))
        self.assertEqual((p["skill"], "ripeti la review" in p["motivo"]), ("sdlc-review-diff", True))
        tutte = fatte.replace("[ ]", "[x]")
        self.assertEqual(self.prossimo(lambda r: self.con_spec(r, tasks=tutte, review=REVIEW_OK, stato="implemented"))["skill"], "sdlc-spec")

    def test_piano_non_approvato(self):
        def setup(r):
            self.con_spec(r)
            scrivi(r, "docs/specs/001-x/plan.md", PLAN_OK.replace("Anna Rossi, 2026-10-19", "<nome>"))
        self.assertEqual(self.prossimo(setup)["skill"], "sdlc-plan")

    def test_revisione_e_task_su_altro_piano(self):
        def in_revisione(r):
            self.con_spec(r, tasks=TASKS_OK, stato="in-revisione")
        p = self.prossimo(in_revisione)
        self.assertEqual((p["skill"], "revisione" in p["motivo"]), ("sdlc-spec", True))

        def task_vecchie(r):
            self.con_spec(r, tasks="- Basato su piano: sha256:vecchio\n" + TASKS_OK)
        p = self.prossimo(task_vecchie)
        self.assertEqual((p["skill"], "altra versione del piano" in p["motivo"]), ("sdlc-tasks", True))

    def test_piu_spec_attive(self):
        def due(r):
            self.con_spec(r, tasks=TASKS_OK)
            data = SPEC_OK.replace("# SPEC-001: Esempio", "# SPEC-2026-10-24-export-csv: Export")
            scrivi(r, "docs/specs/2026-10-24-export-csv/spec.md", data)
        with TmpDir() as d:
            due(d)
            st = state.analizza(d)
            self.assertEqual(st["prossimo"]["skill"], "scegli")
            self.assertIn("001-x (sdlc-implement)", st["prossimo"]["motivo"])
            self.assertIn("2026-10-24-export-csv (sdlc-plan)", st["prossimo"]["motivo"])
            self.assertEqual(state.analizza(d, "SPEC-2026-10-24-export-csv")["prossimo"]["skill"], "sdlc-plan")
            self.assertEqual(state.analizza(d, "001-x")["prossimo"]["skill"], "sdlc-implement")
            self.assertEqual(state.analizza(d, "inesistente")["prossimo"]["skill"], "scegli")
            repo_git(d, "feat/2026-10-24-export-csv")
            self.assertEqual(state.analizza(d)["prossimo"]["spec"], "2026-10-24-export-csv")
            copia_script(d)
            r = esegui([sys.executable, "scripts/state.py", "--spec", "001-x"], d)
            self.assertIn("PROSSIMO: sdlc-implement su 001-x", r.stdout)
            self.assertIn("BRANCH: feat/2026-10-24-export-csv", r.stdout)

    def test_approvazioni_decadute(self):
        def spec_cambiata(r):
            self.con_spec(r, tasks=TASKS_OK)
            scrivi(r, "docs/specs/001-x/spec.md", SPEC_OK.replace("Esportare il report in CSV.", "Altro."))
        p = self.prossimo(spec_cambiata)
        self.assertEqual(p["skill"], "sdlc-spec")
        self.assertIn("Hash", p["motivo"])

        def piano_cambiato(r):
            self.con_spec(r, tasks=TASKS_OK)
            scrivi(r, "docs/specs/001-x/plan.md", PLAN_OK.replace("nuova funzione di export", "altro"))
        p = self.prossimo(piano_cambiato)
        self.assertEqual(p["skill"], "sdlc-plan")
        self.assertIn("va riapprovato", p["motivo"])

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
