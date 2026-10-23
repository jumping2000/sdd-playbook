"""Test dei livelli S/M/L (playbook §2): spec_lint, diff_scope, state, sync_check."""
from __future__ import annotations

import sys
import unittest

from common import (AREA_OK, PLAN_OK, REVIEW_OK, SPEC_OK, TASKS_OK, TmpDir, carica, copia_script, esegui, git,
                    repo_git, scrivi)

spec_lint = carica("spec_lint")
diff_scope = carica("diff_scope")
state = carica("state")


def con_livello(spec: str, livello: str) -> str:
    """Spec approvata con il livello indicato e l'hash ricalcolato."""
    testo = spec.replace("- Stato: approved\n", f"- Stato: approved\n- Livello: {livello}\n")
    vecchio = spec_lint.campo(testo, "Hash")
    return testo.replace(vecchio, spec_lint.impronta(testo))


def piano_per(spec: str) -> str:
    """PLAN_OK approvato sulla versione indicata della spec."""
    return PLAN_OK.replace(spec_lint.campo(PLAN_OK, "Basato su spec"), spec_lint.impronta(spec))


def cli(d, script: str, *args: str):
    return esegui([sys.executable, f"scripts/{script}.py", *args], d)


class TestSpecLintLivelli(unittest.TestCase):
    def test_livello_mancante_vale_m(self):
        err, avv = spec_lint.lint_spec(SPEC_OK)
        self.assertEqual(err, [])
        self.assertTrue(any("Livello non indicato" in a for a in avv))
        self.assertEqual(spec_lint.livello(SPEC_OK), "M")

    def test_livello_valido_e_non_valido(self):
        for liv in ("S", "M", "L"):
            err, avv = spec_lint.lint_spec(con_livello(SPEC_OK, liv))
            self.assertEqual(err, [], liv)
            self.assertFalse(any("Livello" in a for a in avv))
        err, _ = spec_lint.lint_spec(con_livello(SPEC_OK, "XL"))
        self.assertTrue(any("Livello non valido 'XL'" in e for e in err), err)

    def test_abbassare_il_livello_fa_decadere_l_approvazione(self):
        l = con_livello(SPEC_OK, "L")
        self.assertEqual(spec_lint.lint_spec(l)[0], [])
        err, _ = spec_lint.lint_spec(l.replace("- Livello: L", "- Livello: S"))
        self.assertTrue(any("Hash non corrisponde" in e for e in err), err)
        # le spec scritte prima dei livelli mantengono il loro hash
        self.assertEqual(spec_lint.problemi_hash(SPEC_OK, "Spec"), [])

    def test_livello_s_senza_t_doc(self):
        senza_doc = TASKS_OK.replace("- [ ] T-DOC Documentazione\n", "")
        self.assertEqual(spec_lint.lint_tasks(con_livello(SPEC_OK, "S"), senza_doc)[0], [])
        self.assertIn("Manca la task T-DOC", spec_lint.lint_tasks(SPEC_OK, senza_doc)[0])


class TestDiffScopeLivelli(unittest.TestCase):
    def prepara(self, d, livello: str, plan: bool = True):
        copia_script(d)
        repo_git(d, "main")
        scrivi(d, "AGENTS.md", "# A\n- Aree sensibili: src/auth/, migrations/\n")
        scrivi(d, "src/old.py", "v1\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feature/x")
        scrivi(d, "docs/specs/001-x/spec.md", con_livello(SPEC_OK, livello))
        if plan:
            scrivi(d, "docs/specs/001-x/plan.md", PLAN_OK)

    def test_livello_richiesto(self):
        self.assertEqual(diff_scope.livello_richiesto(["src/a.py", "tests/test_a.py", "README.md"], ""), ("S", []))
        liv, motivi = diff_scope.livello_richiesto([f"src/m{i}.py" for i in range(4)], "")
        self.assertEqual(liv, "M")
        self.assertIn("4 file di produzione", motivi[0])
        liv, motivi = diff_scope.livello_richiesto(["requirements-dev.txt", "web/package-lock.json"], "")
        self.assertEqual(liv, "M")
        self.assertIn("dipendenze modificate", motivi[0])
        liv, motivi = diff_scope.livello_richiesto(["src/auth/login.py"], "- Aree sensibili: `src/auth/`\n")
        self.assertEqual(liv, "L")
        self.assertIn("src/auth/login.py", motivi[0])

    def test_s_senza_piano_entro_i_limiti(self):
        with TmpDir() as d:
            self.prepara(d, "S", plan=False)
            scrivi(d, "src/export.py", "x\n")
            scrivi(d, "tests/test_export.py", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("livello: S", r.stdout)
            self.assertIn("confronto con il piano saltato", r.stdout)
            self.assertNotIn("fuori piano", r.stdout)

    def test_s_sottostimato(self):
        with TmpDir() as d:
            self.prepara(d, "S", plan=False)
            for i in range(4):
                scrivi(d, f"src/m{i}.py", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("livello sottostimato: la spec dichiara S, il diff richiede almeno M", r.stdout)

    def test_area_sensibile_richiede_l(self):
        with TmpDir() as d:
            self.prepara(d, "M")
            scrivi(d, "src/auth/login.py", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("il diff richiede almeno L (area sensibile (AGENTS.md): src/auth/login.py)", r.stdout)
            scrivi(d, "docs/specs/001-x/spec.md", con_livello(SPEC_OK, "L"))
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)


class TestStateLivelli(unittest.TestCase):
    def prossimo(self, livello: str, plan=False, tasks=None, review=None) -> dict:
        with TmpDir() as r:
            scrivi(r, "AGENTS.md")
            scrivi(r, "scripts/verify.py")
            spec = con_livello(SPEC_OK, livello)
            scrivi(r, "docs/specs/001-x/spec.md", spec)
            if plan:
                scrivi(r, "docs/specs/001-x/plan.md", piano_per(spec))
            if tasks is not None:
                scrivi(r, "docs/specs/001-x/tasks.md", tasks)
            if review is not None:
                scrivi(r, "docs/specs/001-x/review.md", review)
            return state.analizza(r)["prossimo"]

    def test_livello_s_salta_piano_e_review(self):
        p = self.prossimo("S")
        self.assertEqual((p["skill"], "senza piano" in p["motivo"]), ("sdlc-tasks", True))
        self.assertEqual(self.prossimo("S", tasks=TASKS_OK)["skill"], "sdlc-implement")
        fatte = TASKS_OK.replace("[ ] T-01", "[x] T-01").replace("[ ] T-02", "[x] T-02")
        self.assertEqual(self.prossimo("S", tasks=fatte)["skill"], "sdlc-docs")
        senza_doc = fatte.replace("- [ ] T-DOC Documentazione\n", "")
        self.assertEqual(self.prossimo("S", tasks=senza_doc)["skill"], "sdlc-sync")
        nc = REVIEW_OK.replace("Esito: conforme", "Esito: non conforme")
        self.assertEqual(self.prossimo("S", tasks=senza_doc, review=nc)["skill"], "sdlc-review-diff")
        self.assertEqual(self.prossimo("M")["skill"], "sdlc-plan")

    def test_livello_l_richiede_la_revisione_umana(self):
        fatte = TASKS_OK.replace("[ ] T-01", "[x] T-01").replace("[ ] T-02", "[x] T-02")
        p = self.prossimo("L", plan=True, tasks=fatte, review=REVIEW_OK)
        self.assertEqual((p["skill"], "revisione umana del diff" in p["motivo"]), ("sdlc-review-diff", True))
        umana = REVIEW_OK + "- Revisione umana del diff: Anna Rossi, 2026-10-20\n"
        self.assertEqual(self.prossimo("L", plan=True, tasks=fatte, review=umana)["skill"], "sdlc-docs")
        self.assertEqual(self.prossimo("M", plan=True, tasks=fatte, review=REVIEW_OK)["skill"], "sdlc-docs")


class TestSyncCheckLivelli(unittest.TestCase):
    def prepara(self, d, livello: str):
        copia_script(d)
        f = "docs/specs/001-x/"
        scrivi(d, f + "spec.md", con_livello(SPEC_OK, livello).replace("Stato: approved", "Stato: implemented"))
        scrivi(d, f + "tasks.md", TASKS_OK.replace("[ ]", "[x]"))
        scrivi(d, "tests/test_export.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")

    def test_s_senza_review_ne_pagina_d_area(self):
        with TmpDir() as d:
            self.prepara(d, "S")
            r = cli(d, "sync_check", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_l_richiede_la_revisione_umana(self):
        with TmpDir() as d:
            self.prepara(d, "L")
            scrivi(d, "docs/specs/001-x/review.md", REVIEW_OK)
            scrivi(d, "docs/system/export.md", AREA_OK)
            r = cli(d, "sync_check", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("livello L senza 'Revisione umana del diff'", r.stdout)
            scrivi(d, "docs/specs/001-x/review.md", REVIEW_OK + "- Revisione umana del diff: Anna Rossi, 2026-10-20\n")
            self.assertEqual(cli(d, "sync_check", "docs/specs/001-x").returncode, 0)


if __name__ == "__main__":
    unittest.main()
