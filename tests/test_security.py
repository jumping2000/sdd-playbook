"""Security and maintenance tests: secrets_check, dependencies in diff_scope, guard, loop permissions, versions."""
from __future__ import annotations

import json
import re
import sys
import unittest

from common import HOOKS, PLAN_OK, ROOT, SCRIPTS, TmpDir, copy_scripts, git, git_repo, read, run, write

# Fake tokens built in pieces, so this file contains no recognizable secret.
AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
GITHUB = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
KEY = "-----BEGIN " + "RSA PRIVATE KEY-----"


def cli(d, script: str, *args: str):
    return run([sys.executable, f"scripts/{script}.py", *args], d)


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


class TestDependencies(unittest.TestCase):
    def prepare(self, d, plan=PLAN_OK):
        copy_scripts(d)
        git_repo(d, "main")
        write(d, "AGENTS.md", "# A\n")
        write(d, "pyproject.toml", "[project]\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "base")
        git(d, "checkout", "-qb", "feature/x")
        write(d, "docs/specs/001-x/plan.md", plan)
        write(d, "pyproject.toml", "[project]\ndependencies = ['requests']\n")

    def test_dependency_without_plan_or_adr(self):
        with TmpDir() as d:
            self.prepare(d)
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("dependencies changed without plan or ADR: pyproject.toml", r.stdout)
            write(d, "docs/adr/0001-requests.md", "# ADR\n")
            self.assertEqual(cli(d, "diff_scope", "docs/specs/001-x").returncode, 0)

    def test_dependency_in_the_plan(self):
        plan = PLAN_OK.replace("- `tests/`: new tests", "- `tests/`: new tests\n- pyproject.toml: adds requests")
        with TmpDir() as d:
            self.prepare(d, plan)
            r = cli(d, "diff_scope", "docs/specs/001-x")
            self.assertEqual(r.returncode, 0, r.stdout)


class TestGuard(unittest.TestCase):
    def guard(self, event) -> int:
        stdin = event if isinstance(event, str) else json.dumps(event)
        return run([sys.executable, str(HOOKS / "pretool_guard.py")], HOOKS, stdin=stdin,
                   env={"SDD_GUARD": "1"}).returncode

    def test_review_bypasses(self):
        blocked = ["rm -r -f build", "rm --recursive --force x", "git push origin +main", "git push --force-with-lease",
                   "git push origin --delete x", "git clean -fdx", "Remove-Item -Recurse .\\x",
                   "python -c \"import shutil; shutil.rmtree('x')\"", "Select-String .env -Pattern K", "cp .env /tmp",
                   "cat .ENV", "type C:\\p\\.env::$DATA", "git status && cat .env.local"]
        for c in blocked:
            with self.subTest(c):
                self.assertEqual(self.guard({"tool_name": "Bash", "tool_input": {"command": c}}), 2)
        allowed = ["rm a.txt", "git push -u origin feature", "echo .env >> .gitignore", "cat .env.example", "ls src"]
        for c in allowed:
            with self.subTest(c):
                self.assertEqual(self.guard({"tool_name": "Bash", "tool_input": {"command": c}}), 0)

    def test_tools_and_fail_closed(self):
        self.assertEqual(self.guard({"tool_name": "Read", "tool_input": {"file_path": "C:\\p\\.ENV"}}), 2)
        self.assertEqual(self.guard({"tool_name": "Grep", "tool_input": {"pattern": "K", "path": ".env"}}), 2)
        self.assertEqual(self.guard({"tool_name": "Grep", "tool_input": {"pattern": "K", "glob": ".env*"}}), 2)
        self.assertEqual(self.guard({"tool_name": "Grep", "tool_input": {"pattern": "K", "path": "src"}}), 0)
        self.assertEqual(self.guard("not json"), 2)


class TestMaintenance(unittest.TestCase):
    def test_version_in_the_copied_scripts(self):
        version = json.loads(read(".claude-plugin/plugin.json"))["version"]
        for f in SCRIPTS.glob("*.py"):
            second = f.read_text(encoding="utf-8").splitlines()[1]
            self.assertEqual(second, f"# sdd-playbook: {version}", f.name)

    def test_loop_permissions(self):
        perm = json.loads(read("skills/sdd-loop/references/settings.loop.json"))["permissions"]
        self.assertIn("Bash(git push:*)", perm["deny"])
        self.assertTrue(any("verify.py" in a for a in perm["allow"]))
        self.assertFalse(set(perm["allow"]) & set(perm["deny"]))

    def test_reviewer_without_write_tools(self):
        fm = re.match(r"^---\n(.*?)\n---\n", read("agents/sdd-reviewer.md"), re.S).group(1)
        tools = {s.strip() for s in re.search(r"^tools:\s*(.*)$", fm, re.M).group(1).split(",")}
        self.assertFalse(tools & {"Bash", "Edit", "Write", "PowerShell", "NotebookEdit"}, tools)

    def test_copilot_reviewer_is_read_only(self):
        fm = re.match(r"^---\n(.*?)\n---\n", read("skills/sdd-init/references/copilot/sdd-reviewer.agent.md"),
                      re.S).group(1)
        tools = set(re.findall(r"'([^']+)'", re.search(r"^tools:\s*(.*)$", fm, re.M).group(1)))
        self.assertTrue(tools)
        self.assertTrue(tools <= {"read", "search"}, tools)

    def test_ci_actions_up_to_date(self):
        for rel in (".github/workflows/ci.yml", "skills/sdd-init/references/ci-github-actions.yml"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"actions/checkout@v[1-5]\b", rel)
            self.assertNotRegex(text, r"actions/setup-python@v[1-5]\b", rel)


if __name__ == "__main__":
    unittest.main()
