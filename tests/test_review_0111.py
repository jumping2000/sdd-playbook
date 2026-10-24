"""Regressioni dai problemi della review critica sulla 0.11.0 (I1-I8 e minori)."""
from __future__ import annotations

import json
import os
import sys
import unittest

from common import (HOOKS, PLAN_OK, SPEC_OK, TASKS_OK, TmpDir, carica, copia_script, esegui, git, leggi, repo_git,
                    scrivi)

spec_lint = carica("spec_lint")
trace_check = carica("trace_check")
PY = os.path.basename(sys.executable)


def cli(d, script: str, *args: str):
    return esegui([sys.executable, f"scripts/{script}.py", *args], d)


def spec_con_livello(livello: str) -> str:
    testo = SPEC_OK.replace("- Stato: approved\n", f"- Stato: approved\n- Livello: {livello}\n")
    return testo.replace(spec_lint.campo(testo, "Hash"), spec_lint.impronta(testo))


def repo(d, agents="# A\n", spec=None, plan=PLAN_OK):
    copia_script(d)
    repo_git(d, "main")
    scrivi(d, "AGENTS.md", agents)
    scrivi(d, "src/old.py", "v1\n")
    if spec:
        scrivi(d, "docs/specs/001-x/spec.md", spec)
    git(d, "add", "-A")
    git(d, "commit", "-qm", "base")
    git(d, "checkout", "-qb", "feature/x")
    if plan:
        scrivi(d, "docs/specs/001-x/plan.md", plan)


class TestApprovazioneLegataAlloSha(unittest.TestCase):  # I1
    def test_nuovo_test_lock_dopo_l_approvazione(self):
        with TmpDir() as d:
            repo(d)
            scrivi(d, "tests/test_export.py", "def test_AC_001(): assert False\n")
            git(d, "add", "tests/test_export.py")
            git(d, "commit", "-qm", "test rossi", "-m", "Test-Lock: T-01")
            sha = git(d, "rev-parse", "--short=7", "HEAD")
            tasks = TASKS_OK.replace("[ ] T-01", "[x] T-01").replace("abc1234", sha)
            scrivi(d, "docs/specs/001-x/tasks.md", tasks)
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)
            scrivi(d, "tests/test_export.py", "def test_AC_001(): assert True\n")
            git(d, "add", "tests/test_export.py")
            git(d, "commit", "-qm", "test indeboliti", "-m", "Test-Lock: T-01")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("T-01: nuovo commit Test-Lock dopo l'approvazione", r.stdout)
            scrivi(d, "docs/specs/001-x/tasks.md", tasks.replace(sha, "1234567"))
            self.assertIn("non è un commit Test-Lock: T-01", cli(d, "diff_scope", "docs/specs/001-x").stdout)

    def test_formato_dell_approvazione(self):
        chiusa = "- [x] T-01 Test — verifica: `t` (Atteso: Rosso) — copre: AC-001 — test approvati: {}\n"
        for valore, valida in (("Anna, 2026-10-24, abc1234", True), ("Anna, 2026-10-24", False),
                               ("no, da rifare", False), ("Mario <data>, 2026-10-24, abc1234", False)):
            with self.subTest(valore):
                self.assertEqual(spec_lint.test_da_approvare(chiusa.format(valore)) == [], valida)


class TestLivelloNonAggirabile(unittest.TestCase):  # I2
    def test_rinomina_fuori_dall_area_sensibile(self):
        with TmpDir() as d:
            scrivi(d, "src/auth/login.py", "v1\n")  # già sulla base
            repo(d, agents="# A\n- Aree sensibili: `src/auth/`\n", spec=spec_con_livello("S"), plan=None)
            git(d, "mv", "src/auth/login.py", "src/login.py")
            r = cli(d, "diff_scope", "docs/specs/001-x", "--base", "main")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("area sensibile (AGENTS.md): src/auth/login.py", r.stdout)

    def test_agents_e_livello_letti_dalla_base(self):
        with TmpDir() as d:
            repo(d, agents="# A\n- Aree sensibili: src/auth/\n", spec=spec_con_livello("M"))
            scrivi(d, "AGENTS.md", "# A\n")  # il ramo prova a togliere l'area sensibile
            scrivi(d, "docs/specs/001-x/spec.md", spec_con_livello("L"))
            scrivi(d, "src/auth/login.py", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("AGENTS.md modificato nel ramo", r.stdout)
            self.assertIn("la spec dichiara M, il diff richiede almeno L", r.stdout)

    def test_voci_descrittive(self):
        with TmpDir() as d:
            repo(d, agents="# A\n- Aree sensibili: `src/auth/` (login), pagamenti\n", spec=spec_con_livello("M"))
            scrivi(d, "src/auth/login.py", "x\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertIn("il diff richiede almeno L", r.stdout)
            self.assertIn("non sembra un percorso, ignorata: 'pagamenti'", r.stdout)


class TestDipendenzeEAdr(unittest.TestCase):  # I3 e lockfile
    def prepara(self, d, plan=PLAN_OK):
        repo(d, plan=plan)
        scrivi(d, "docs/adr/README.md", "# ADR\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "adr readme")
        scrivi(d, "package.json", "{}\n")
        scrivi(d, "package-lock.json", "{}\n")

    def test_serve_un_adr_nuovo(self):
        with TmpDir() as d:
            self.prepara(d)
            scrivi(d, "docs/adr/README.md", "# ADR\naggiornato\n")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("dipendenze modificate senza piano né ADR: package.json", r.stdout)
            scrivi(d, "docs/adr/0001-nuova-dipendenza.md", "# ADR 1\n")
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)

    def test_lockfile_del_manifest_pianificato(self):
        piano = PLAN_OK.replace("- `tests/`: nuovi test", "- `tests/`: nuovi test\n- package.json: dipendenza x")
        with TmpDir() as d:
            self.prepara(d, plan=piano)
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)


class TestAttribuzioneJUnit(unittest.TestCase):  # I4
    def test_file_omonimi_in_cartelle_diverse(self):
        spec_a = SPEC_OK.replace("SPEC-001", "SPEC-002")
        with TmpDir() as d:
            scrivi(d, "tests/a/test_api.py", "# SPEC-001\ndef test_AC_001(): pass\n")
            scrivi(d, "tests/b/test_api.py", "# SPEC-002\ndef test_AC_001(): pass\n")
            report = d / "junit.xml"
            report.write_text('<testsuite><testcase classname="tests.a.test_api" name="test_AC_001"><skipped/>'
                              '</testcase><testcase classname="tests.b.test_api" name="test_AC_001"><failure/>'
                              '</testcase></testsuite>', encoding="utf-8")
            es1 = trace_check.esecuzioni(SPEC_OK, [d / "tests"], [report], spec_unica=False)
            self.assertEqual((es1["AC-001"]["passato"], es1["AC-001"]["fallito"]), ([], []))
            self.assertEqual(es1["AC-001"]["saltato"], ["tests.a.test_api::test_AC_001"])
            es2 = trace_check.esecuzioni(spec_a, [d / "tests"], [report], spec_unica=False)
            self.assertEqual(es2["AC-001"]["fallito"], ["tests.b.test_api::test_AC_001"])

    def test_convenzioni_go_e_java(self):
        with TmpDir() as d:
            scrivi(d, "src/test/java/com/acme/ExportTest.java", "// SPEC-001\n@Test void AC_001_esporta() {}\n")
            scrivi(d, "pkg/export_test.go", "// SPEC-001\nfunc TestAC002_Errore(t *testing.T) {}\n")
            trovati, _, _ = trace_check.raccogli([d / "src", d / "pkg"], "1", spec_unica=False)
            self.assertEqual(sorted(trovati), [1, 2])
            report = d / "junit.xml"
            report.write_text('<testsuite><testcase classname="com.acme.ExportTest" name="AC_001_esporta"/>'
                              '</testsuite>', encoding="utf-8")
            es = trace_check.esecuzioni(SPEC_OK, [d / "src"], [report], spec_unica=False)
            self.assertEqual(es["AC-001"]["passato"], ["com.acme.ExportTest::AC_001_esporta"])

    def test_junit_senza_valore(self):
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, "spec.md", SPEC_OK)
            scrivi(d, "tests/t.py", "def test_AC_001(): pass\ndef test_AC_002(): pass\n")
            self.assertEqual(cli(d, "trace_check", "spec.md", "--junit").returncode, 2)


class TestFileGenerati(unittest.TestCase):  # I5
    def test_pycache_e_report_non_contano(self):
        with TmpDir() as d:
            repo(d, spec=spec_con_livello("S"), plan=None)
            for i in range(3):
                scrivi(d, f"src/m{i}.py", "x\n")
            scrivi(d, "reports/junit.xml", "<testsuite/>")
            scrivi(d, "scripts/__pycache__/x.cpython-313.pyc", "x")
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertFalse((d / "scripts" / "__pycache__" / "spec_lint.cpython-313.pyc").exists())

    def test_report_che_cambia_non_e_progresso(self):
        agente = ("import sys, time\nsys.stdin.read()\nimport os\nos.makedirs('reports', exist_ok=True)\n"
                  "open('reports/junit.xml', 'w').write(str(time.time()))\n")
        with TmpDir() as d:
            copia_script(d, ["loop", "spec_lint"])
            scrivi(d, "scripts/verify.py", "import sys\nsys.exit(0)\n")
            scrivi(d, "docs/specs/001-x/tasks.md", "- [ ] T-01 a\n")
            scrivi(d, "docs/specs/001-x/PROMPT.md", "p\n")
            scrivi(d, "agent.py", agente)
            repo_git(d, "feature/x")
            env = {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]}
            r = esegui([sys.executable, "scripts/loop.py", "docs/specs/001-x", "--agent", f"{PY} agent.py",
                        "--stall", "2", "--max", "6"], d, env=env)
            self.assertIn("Nessun progresso per 2 iterazioni", r.stdout)


class TestLoopUsaSpecLint(unittest.TestCase):  # I6
    def test_livello_nelle_revisioni_non_conta(self):
        with TmpDir() as d:
            copia_script(d, ["loop", "spec_lint"])
            scrivi(d, "scripts/verify.py", "import sys\nsys.exit(1)\n")
            scrivi(d, "docs/specs/001-x/spec.md", "# SPEC-001: x\n\n- Livello: L\n\n## Revisioni\n- Livello: S (prima)\n")
            scrivi(d, "docs/specs/001-x/tasks.md", "- [x] T-01 t (atteso: rosso) — test approvati: Mario <data>\n"
                                                   "- [ ] T-02 i\n")
            scrivi(d, "docs/specs/001-x/PROMPT.md", "p\n")
            scrivi(d, "agent.py", "import sys\nsys.stdin.read()\n")
            repo_git(d, "feature/x")
            env = {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]}
            r = esegui([sys.executable, "scripts/loop.py", "docs/specs/001-x", "--agent", f"{PY} agent.py",
                        "--dry-run"], d, env=env)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("aspettano l'approvazione umana", r.stdout)


class TestPermessiDelLoop(unittest.TestCase):  # I8
    def test_controlli_e_regole_non_scrivibili(self):
        perm = json.loads(leggi("skills/sdlc-loop/references/settings.loop.json"))["permissions"]
        for protetto in ("./scripts/**", "./AGENTS.md", "./.github/**", "./docs/specs/*/spec.md"):
            self.assertIn(f"Edit({protetto})", perm["deny"])
            self.assertIn(f"Write({protetto})", perm["deny"])
        self.assertIn("Bash(python3 scripts/verify.py:*)", perm["allow"])


class TestMinori(unittest.TestCase):
    def test_secrets_nomi_non_ascii_ed_esclusioni(self):
        token = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
        with TmpDir() as d:
            copia_script(d, ["secrets_check"])
            repo_git(d, "main")
            scrivi(d, "src/configurazione_è.py", f'T = "{token}"\n')
            scrivi(d, ".env.local.example", "X=\n")
            scrivi(d, ".env.development", "X=1\n")
            git(d, "add", "-A")
            git(d, "commit", "-qm", "base")
            r = cli(d, "secrets_check", "--all")
            self.assertIn("src/configurazione_è.py:1: token GitHub", r.stdout)
            self.assertNotIn(".env.local.example", r.stdout)
            self.assertIn(".env.development: file .env", r.stdout)
            scrivi(d, ".secrets-ignore", "# convenzione di Vite\n.env.development\n")
            self.assertNotIn(".env.development", cli(d, "secrets_check", "--all").stdout)

    def test_guard_varianti(self):
        def guard(c):
            return esegui([sys.executable, str(HOOKS / "pretool_guard.py")], HOOKS,
                          stdin=json.dumps({"tool_name": "Bash", "tool_input": {"command": c}}),
                          env={"SDLC_GUARD": "1"}).returncode
        for c in ("git reset HEAD~1 --hard", "git -C . reset --hard", "git clean -d -f", "cat .env>out.txt",
                  "cat <.env", "python3 -c \"open('.env')\"", "find . -delete"):
            with self.subTest(c):
                self.assertEqual(guard(c), 2)
        for c in ("git rm -r --cached build/", "grep -n '\\.env' .gitignore", "git check-ignore -v .env",
                  "git commit -m 'rm -rf nel messaggio'"):
            with self.subTest(c):
                self.assertEqual(guard(c), 0)
        r = esegui([sys.executable, str(HOOKS / "pretool_guard.py")], HOOKS,
                   stdin=json.dumps({"tool_name": "Bash", "tool_input": "x"}), env={"SDLC_GUARD": "1"})
        self.assertEqual(r.returncode, 2)

    def test_sync_check_cartella_dopo_le_opzioni(self):
        with TmpDir() as d:
            copia_script(d)
            scrivi(d, "docs/specs/001-x/spec.md", SPEC_OK)
            scrivi(d, "r.xml", "<testsuite/>")
            r = cli(d, "sync_check", "--junit", "r.xml", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("Stato è 'approved'", r.stdout)


if __name__ == "__main__":
    unittest.main()
