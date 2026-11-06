"""Tests of verify, scan_repo, docs_check, secrets_check and of the plugin's maintenance rules."""
from __future__ import annotations

import json
import re
import sys
import unittest

from common import AREA_OK, ROOT, SCRIPTS, TmpDir, copy_scripts, git, git_repo, load, read, run, write

scan_repo = load("scan_repo")

# Fake tokens built in pieces, so this file contains no recognizable secret.
AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
GITHUB = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
KEY = "-----BEGIN " + "RSA PRIVATE KEY-----"


def cli(d, script: str, *args: str):
    return run([sys.executable, f"scripts/{script}.py", *args], d)


class TestVerify(unittest.TestCase):
    def attempt(self, steps: str, args: list[str]):
        text = (SCRIPTS / "verify.py").read_text(encoding="utf-8")
        start, end = text.index("STEPS = ["), text.index("def run_step")
        with TmpDir() as d:
            write(d, "scripts/verify.py", text[:start] + "STEPS = " + steps + "\n\n\n" + text[end:])
            return run([sys.executable, "scripts/verify.py", *args], d)

    OK, KO = '[sys.executable, "-c", "pass"]', '[sys.executable, "-c", "import sys; sys.exit(1)"]'

    def test_green_and_red(self):
        self.assertEqual(self.attempt(f'[("a", {self.OK}, True), ("b", {self.OK}, False)]', []).returncode, 0)
        r = self.attempt(f'[("a", {self.OK}, True), ("b", {self.KO}, False)]', [])
        self.assertEqual(r.returncode, 1)
        self.assertIn("RED -> b", r.stdout)

    def test_fast_and_selection(self):
        s = f'[("a", {self.OK}, True), ("b", {self.KO}, False)]'
        self.assertEqual(self.attempt(s, ["--fast"]).returncode, 0)
        self.assertEqual(self.attempt(s, ["a"]).returncode, 0)

    def test_missing_command(self):
        r = self.attempt('[("x", ["command-that-does-not-exist-xyz"], True)]', [])
        self.assertEqual(r.returncode, 1)
        self.assertIn("not found", r.stdout)


class TestScanRepo(unittest.TestCase):
    def test_inventory(self):
        with TmpDir() as d:
            write(d, "pyproject.toml")
            write(d, "src/main.py", "a\nb\nc\n")
            write(d, "src/util.py", "x\n")
            write(d, "tests/test_a.py")
            write(d, "README.md")
            write(d, ".github/workflows/ci.yml")
            write(d, "node_modules/x/index.js", "ignored\n")
            r = scan_repo.scan(d)
            self.assertEqual(r["stack"], ["Python"])
            self.assertEqual(r["languages"][0], {"name": "Python", "files": 3, "lines": 5})
            self.assertEqual(r["test_folders"], ["tests"])
            self.assertEqual(r["likely_entry_points"], ["src/main.py"])
            self.assertEqual(r["ci"], [".github/workflows/ci.yml"])
            self.assertEqual(r["documentation"], ["README.md"])

    def test_cli_json_and_missing_folder(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "a.py")
            self.assertIn('"total_files"', cli(d, "scan_repo", ".", "--json").stdout)
            self.assertEqual(cli(d, "scan_repo", "does-not-exist").returncode, 2)


class TestDocsCheck(unittest.TestCase):
    def test_links_and_examples(self):
        with TmpDir() as d:
            copy_scripts(d)
            write(d, "docs/b.md", "# B\n")
            write(d, "README.md", "[ok](docs/b.md) [web](https://x.y) [anc](#a)\n```\n[in code](broken.md)\n```\n"
                                  "`[inline](broken2.md)`\n")
            self.assertEqual(cli(d, "docs_check", "README.md", "docs").returncode, 0)
            write(d, "README.md", "[broken](docs/does-not-exist.md)\n")
            r = cli(d, "docs_check", "README.md")
            self.assertEqual(r.returncode, 1)
            self.assertIn("broken link -> docs/does-not-exist.md", r.stdout)

    def test_runnable_examples(self):
        with TmpDir() as d:
            copy_scripts(d)
            ok = "```python\n# docs-check: run\nprint(1 + 1)\n```\n"
            ko = "```python\n# docs-check: run\nraise SystemExit(3)\n```\n"
            not_run = "```python\nraise SystemExit(9)\n```\n"
            write(d, "README.md", ok + not_run)
            r = cli(d, "docs_check", "README.md", "--run-examples")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("1 examples run", r.stdout)
            write(d, "README.md", ok + ko)
            r = cli(d, "docs_check", "README.md", "--run-examples")
            self.assertEqual(r.returncode, 1)
            self.assertIn("example #2 failed (exit 3)", r.stdout)
            self.assertEqual(cli(d, "docs_check", "README.md").returncode, 0)  # without --run-examples nothing runs


    def test_mermaid_blocks_and_system_pages(self):
        with TmpDir() as d:
            copy_scripts(d)
            outer = "````markdown\n```mermaid\nnot a diagram\n```\n[in code](broken.md)\n````\n"  # nested fences
            write(d, "README.md", outer + "```mermaid\nsequenceDiagram\n    A->>B: hi\n```\n")
            self.assertEqual(cli(d, "docs_check", "README.md").returncode, 0)
            write(d, "README.md", "```mermaid\nflowchrt TD\n    A --> B\n```\n```mermaid\n%% only a comment\n```\n")
            r = cli(d, "docs_check", "README.md")
            self.assertEqual(r.returncode, 1)
            self.assertIn("block #1: unknown diagram type 'flowchrt'", r.stdout)
            self.assertIn("block #2: unknown diagram type 'empty'", r.stdout)
            write(d, "README.md", "# ok\n")
            write(d, "docs/system/export.md", AREA_OK)
            self.assertEqual(cli(d, "docs_check").returncode, 0)
            write(d, "docs/system/map.md", "# Codebase map\n")
            r = cli(d, "docs_check")
            self.assertEqual(r.returncode, 1)
            self.assertIn("docs/system/map.md: Section '## Diagrams' missing", r.stdout)
            write(d, "docs/other.md", "# no diagrams needed outside docs/system\n")
            self.assertEqual(cli(d, "docs_check", "docs/other.md").returncode, 0)


class TestSecretsCheck(unittest.TestCase):
    def test_explicit_paths(self):
        with TmpDir() as d:
            copy_scripts(d, ["secrets_check"])
            write(d, "src/config.py", f'KEY = "{AWS}"\ntoken = "{GITHUB}"\n')
            write(d, "src/key.pem", KEY + "\nxxx\n")
            write(d, "src/ok.py", f'KEY = "{AWS}"  # secrets-check: ignore\npassword = "changeme"\n')
            write(d, "src/suspect.py", 'db_password = "Sup3rS3cret0!"\n')
            r = cli(d, "secrets_check", "src")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("src/config.py:1: AWS access key", r.stdout)
            self.assertIn("src/config.py:2: GitHub token", r.stdout)
            self.assertIn("src/key.pem:1: private key", r.stdout)
            self.assertNotIn("src/ok.py", r.stdout)
            self.assertIn("[WARN] src/suspect.py:1: possible secret", r.stdout)
            self.assertNotIn(AWS, r.stdout)  # the value is never printed
            self.assertIn("SECRETS: 3 secrets", r.stdout)

    def test_env_files_and_branch_diff(self):
        with TmpDir() as d:
            copy_scripts(d, ["secrets_check"])
            git_repo(d, "main")
            write(d, "old.py", f'K = "{AWS}"\n')
            git(d, "add", "-A")
            git(d, "commit", "-qm", "base")
            git(d, "checkout", "-qb", "feature/x")
            write(d, ".env", "X=1\n")
            write(d, ".env.example", "X=\n")
            write(d, "new.py", "print('hello')\n")
            r = cli(d, "secrets_check")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn(".env: .env file in the repository", r.stdout)
            self.assertNotIn(".env.example", r.stdout)
            self.assertNotIn("old.py", r.stdout)  # only the files of the branch
            r = cli(d, "secrets_check", "--all")
            self.assertIn("old.py:1: AWS access key", r.stdout)

    def test_without_git(self):
        with TmpDir() as d:
            copy_scripts(d, ["secrets_check"])
            self.assertEqual(cli(d, "secrets_check").returncode, 2)

    def test_secrets_non_ascii_names_and_exclusions(self):
        token = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
        with TmpDir() as d:
            copy_scripts(d, ["secrets_check"])
            git_repo(d, "main")
            write(d, "src/configuración_è.py", f'T = "{token}"\n')
            write(d, ".env.local.example", "X=\n")
            write(d, ".env.development", "X=1\n")
            git(d, "add", "-A")
            git(d, "commit", "-qm", "base")
            r = cli(d, "secrets_check", "--all")
            self.assertIn("src/configuración_è.py:1: GitHub token", r.stdout)
            self.assertNotIn(".env.local.example", r.stdout)
            self.assertIn(".env.development: .env file", r.stdout)
            write(d, ".secrets-ignore", "# Vite convention\n.env.development\n")
            self.assertNotIn(".env.development", cli(d, "secrets_check", "--all").stdout)


class TestMaintenance(unittest.TestCase):
    def test_version_in_the_copied_scripts(self):
        version = json.loads(read(".claude-plugin/plugin.json"))["version"]
        for f in SCRIPTS.glob("*.py"):
            second = f.read_text(encoding="utf-8").splitlines()[1]
            self.assertEqual(second, f"# sdd-playbook: {version}", f.name)

    def test_reviewer_without_write_tools(self):
        fm = re.match(r"^---\n(.*?)\n---\n", read("agents/sdd-reviewer.md"), re.S).group(1)
        tools = {s.strip() for s in re.search(r"^tools:\s*(.*)$", fm, re.M).group(1).split(",")}
        self.assertFalse(tools & {"Bash", "Edit", "Write", "PowerShell", "NotebookEdit"}, tools)

    def test_copilot_reviewer_is_read_only(self):
        fm = re.match(r"^---\n(.*?)\n---\n", read("skills/sdd-start/references/copilot/sdd-reviewer.agent.md"),
                      re.S).group(1)
        tools = set(re.findall(r"'([^']+)'", re.search(r"^tools:\s*(.*)$", fm, re.M).group(1)))
        self.assertTrue(tools)
        self.assertTrue(tools <= {"read", "search"}, tools)

    def test_ci_actions_up_to_date(self):
        for rel in (".github/workflows/ci.yml", "skills/sdd-start/references/ci-github-actions.yml"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"actions/checkout@v[1-5]\b", rel)
            self.assertNotRegex(text, r"actions/setup-python@v[1-5]\b", rel)
            self.assertNotIn("ubuntu-latest", text, rel)  # pinned: the label moves to new Ubuntu releases


if __name__ == "__main__":
    unittest.main()
