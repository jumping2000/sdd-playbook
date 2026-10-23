"""Test di sicurezza e manutenzione: secrets_check, dipendenze in diff_scope, guard, permessi del loop, versioni."""
from __future__ import annotations

import json
import re
import sys
import unittest

from common import HOOKS, PLAN_OK, ROOT, SCRIPTS, TmpDir, copia_script, esegui, git, leggi, repo_git, scrivi

# Token finti costruiti a pezzi, così questo file non contiene segreti riconoscibili.
AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
GITHUB = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
CHIAVE = "-----BEGIN " + "RSA PRIVATE KEY-----"


def cli(d, script: str, *args: str):
    return esegui([sys.executable, f"scripts/{script}.py", *args], d)


class TestSecretsCheck(unittest.TestCase):
    def test_percorsi_espliciti(self):
        with TmpDir() as d:
            copia_script(d, ["secrets_check"])
            scrivi(d, "src/config.py", f'KEY = "{AWS}"\ntoken = "{GITHUB}"\n')
            scrivi(d, "src/key.pem", CHIAVE + "\nxxx\n")
            scrivi(d, "src/ok.py", f'KEY = "{AWS}"  # secrets-check: ignore\npassword = "changeme"\n')
            scrivi(d, "src/sospetto.py", 'db_password = "Sup3rSegret0!"\n')
            r = cli(d, "secrets_check", "src")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("src/config.py:1: chiave di accesso AWS", r.stdout)
            self.assertIn("src/config.py:2: token GitHub", r.stdout)
            self.assertIn("src/key.pem:1: chiave privata", r.stdout)
            self.assertNotIn("src/ok.py", r.stdout)
            self.assertIn("[WARN] src/sospetto.py:1: possibile segreto", r.stdout)
            self.assertNotIn(AWS, r.stdout)  # il valore non viene mai stampato
            self.assertIn("SECRETS: 3 segreti", r.stdout)

    def test_file_env_e_diff_dal_ramo(self):
        with TmpDir() as d:
            copia_script(d, ["secrets_check"])
            repo_git(d, "main")
            scrivi(d, "vecchio.py", f'K = "{AWS}"\n')
            git(d, "add", "-A")
            git(d, "commit", "-qm", "base")
            git(d, "checkout", "-qb", "feature/x")
            scrivi(d, ".env", "X=1\n")
            scrivi(d, ".env.example", "X=\n")
            scrivi(d, "nuovo.py", "print('ciao')\n")
            r = cli(d, "secrets_check")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn(".env: file .env nel repository", r.stdout)
            self.assertNotIn(".env.example", r.stdout)
            self.assertNotIn("vecchio.py", r.stdout)  # solo i file del ramo
            r = cli(d, "secrets_check", "--all")
            self.assertIn("vecchio.py:1: chiave di accesso AWS", r.stdout)

    def test_senza_git(self):
        with TmpDir() as d:
            copia_script(d, ["secrets_check"])
            self.assertEqual(cli(d, "secrets_check").returncode, 2)


class TestDipendenze(unittest.TestCase):
    def prepara(self, d, plan=PLAN_OK):
        copia_script(d)
        repo_git(d, "main")
        scrivi(d, "AGENTS.md", "# A\n")
        scrivi(d, "pyproject.toml", "[project]\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feature/x")
        scrivi(d, "docs/specs/001-x/plan.md", plan)
        scrivi(d, "pyproject.toml", "[project]\ndependencies = ['requests']\n")

    def test_dipendenza_senza_piano_ne_adr(self):
        with TmpDir() as d:
            self.prepara(d)
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("dipendenze modificate senza piano né ADR: pyproject.toml", r.stdout)
            scrivi(d, "docs/adr/0001-requests.md", "# ADR\n")
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)

    def test_dipendenza_nel_piano(self):
        piano = PLAN_OK.replace("- `tests/`: nuovi test", "- `tests/`: nuovi test\n- pyproject.toml: aggiunge requests")
        with TmpDir() as d:
            self.prepara(d, piano)
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)


class TestGuard(unittest.TestCase):
    def guard(self, evento) -> int:
        stdin = evento if isinstance(evento, str) else json.dumps(evento)
        return esegui([sys.executable, str(HOOKS / "pretool_guard.py")], HOOKS, stdin=stdin,
                      env={"SDLC_GUARD": "1"}).returncode

    def test_aggiramenti_della_review(self):
        bloccati = ["rm -r -f build", "rm --recursive --force x", "git push origin +main", "git push --force-with-lease",
                    "git push origin --delete x", "git clean -fdx", "Remove-Item -Recurse .\\x",
                    "python -c \"import shutil; shutil.rmtree('x')\"", "Select-String .env -Pattern K", "cp .env /tmp",
                    "cat .ENV", "type C:\\p\\.env::$DATA", "git status && cat .env.local"]
        for c in bloccati:
            with self.subTest(c):
                self.assertEqual(self.guard({"tool_name": "Bash", "tool_input": {"command": c}}), 2)
        ammessi = ["rm a.txt", "git push -u origin feature", "echo .env >> .gitignore", "cat .env.example", "ls src"]
        for c in ammessi:
            with self.subTest(c):
                self.assertEqual(self.guard({"tool_name": "Bash", "tool_input": {"command": c}}), 0)

    def test_strumenti_e_fail_closed(self):
        self.assertEqual(self.guard({"tool_name": "Read", "tool_input": {"file_path": "C:\\p\\.ENV"}}), 2)
        self.assertEqual(self.guard({"tool_name": "Grep", "tool_input": {"pattern": "K", "path": ".env"}}), 2)
        self.assertEqual(self.guard({"tool_name": "Grep", "tool_input": {"pattern": "K", "glob": ".env*"}}), 2)
        self.assertEqual(self.guard({"tool_name": "Grep", "tool_input": {"pattern": "K", "path": "src"}}), 0)
        self.assertEqual(self.guard("non è json"), 2)


class TestManutenzione(unittest.TestCase):
    def test_versione_negli_script_copiati(self):
        versione = json.loads(leggi(".claude-plugin/plugin.json"))["version"]
        for f in SCRIPTS.glob("*.py"):
            seconda = f.read_text(encoding="utf-8").splitlines()[1]
            self.assertEqual(seconda, f"# sdlc-playbook: {versione}", f.name)

    def test_permessi_del_loop(self):
        perm = json.loads(leggi("skills/sdlc-loop/references/settings.loop.json"))["permissions"]
        self.assertIn("Bash(git push:*)", perm["deny"])
        self.assertTrue(any("verify.py" in a for a in perm["allow"]))
        self.assertFalse(set(perm["allow"]) & set(perm["deny"]))

    def test_revisore_senza_strumenti_di_scrittura(self):
        fm = re.match(r"^---\n(.*?)\n---\n", leggi("agents/sdlc-reviewer.md"), re.S).group(1)
        strumenti = {s.strip() for s in re.search(r"^tools:\s*(.*)$", fm, re.M).group(1).split(",")}
        self.assertFalse(strumenti & {"Bash", "Edit", "Write", "PowerShell", "NotebookEdit"}, strumenti)

    def test_action_ci_aggiornate(self):
        for rel in (".github/workflows/ci.yml", "skills/sdlc-init/references/ci-github-actions.yml"):
            testo = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotRegex(testo, r"actions/checkout@v[1-5]\b", rel)
            self.assertNotRegex(testo, r"actions/setup-python@v[1-5]\b", rel)


if __name__ == "__main__":
    unittest.main()
