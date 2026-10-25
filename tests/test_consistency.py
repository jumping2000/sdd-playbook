"""Consistency tests between skills, scripts, hooks, templates, playbook, manifests and documentation."""
from __future__ import annotations

import json
import re
import sys
import unittest

from common import ROOT, SCRIPTS, load, read, run

spec_lint = load("spec_lint")
SKILLS = sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir())
SCRIPT_NAMES = sorted(p.stem for p in SCRIPTS.glob("*.py"))
PLAYBOOK = read("docs/playbook-ai-software-lifecycle.md")  # the skills, in English, cite this one by §
PLAYBOOK_IT = read("docs/playbook-ai-software-lifecycle_IT.md")
# Every document exists in English (no suffix) and in Italian (_IT).
LANGUAGES = {"README": ("README.md", "README_IT.md"), "skills": ("docs/skills.md", "docs/skills_IT.md"),
             "scripts": ("docs/scripts.md", "docs/scripts_IT.md"),
             "architecture": ("docs/architecture.md", "docs/architecture_IT.md"),
             "quick-guide": ("docs/quick-guide.md", "docs/quick-guide_IT.md"),
             "CHANGELOG": ("CHANGELOG.md", "CHANGELOG_IT.md"), "REVIEW": ("REVIEW.md", "REVIEW_IT.md")}
HISTORY = ("CHANGELOG", "REVIEW")  # historical records: they keep the names of their time
NON_SKILL = {"sdd-playbook", "sdd-reviewer", "sdd-playbook-marketplace"}
ENV_VARS = ("SDD_ENFORCE_VERIFY", "SDD_VERIFY_ARGS", "SDD_STOP_MAX", "SDD_GUARD")


def both(name: str) -> list[str]:
    return [read(f) for f in LANGUAGES[name]]


def md_texts(history=True) -> dict[str, str]:
    out = {}
    for p in [*sorted(ROOT.glob("*.md")), *sorted((ROOT / "docs").glob("*.md")), *sorted((ROOT / "skills").rglob("*.md")),
              *sorted((ROOT / "agents").glob("*.md"))]:
        if not history and p.name.startswith(HISTORY):
            continue
        out[p.relative_to(ROOT).as_posix()] = p.read_text(encoding="utf-8")
    return out


def all_texts() -> dict[str, str]:
    out = {}
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if (not p.is_file() or ".git" in rel.parts or "tests" in rel.parts or "__pycache__" in rel.parts
                or p.suffix in (".zip", ".pyc") or p.name == "LICENSE"):
            continue
        out[rel.as_posix()] = p.read_text(encoding="utf-8")
    return out


def frontmatter(text: str) -> str:
    return re.match(r"^---\n(.*?)\n---\n", text, re.S).group(1)


class TestMetadata(unittest.TestCase):
    def test_skills(self):
        self.assertEqual(len(SKILLS), 14)
        for name in SKILLS:
            self.assertTrue(name.startswith("sdd-"), name)
            f = ROOT / "skills" / name / "SKILL.md"
            self.assertTrue(f.is_file(), name)
            text = f.read_text(encoding="utf-8")
            fm = dict(re.findall(r"^(\w+):\s*(.+)$", frontmatter(text), re.M))
            self.assertEqual(fm.get("name"), name)
            self.assertGreater(len(fm.get("description", "")), 40, name)
            self.assertLess(len(text.splitlines()), 150, name)

    def test_template_references_exist(self):
        for name in SKILLS:
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            for rel in re.findall(r"`((?:\.\./sdd-[a-z-]+/)?references/[\w./\-]+\.[\w]+)`", text):
                self.assertTrue((ROOT / "skills" / name / rel).resolve().is_file(), f"{name}: {rel}")

    def test_manifests_and_versions(self):
        claude = json.loads(read(".claude-plugin/plugin.json"))
        codex = json.loads(read(".codex-plugin/plugin.json"))
        copilot = json.loads(read("plugin.json"))
        market = json.loads(read(".claude-plugin/marketplace.json"))
        for m in (codex, copilot):
            self.assertEqual((m["name"], m["version"]), (claude["name"], claude["version"]))
        self.assertEqual(claude["name"], "sdd-playbook")
        self.assertEqual(market["plugins"][0]["name"], claude["name"])
        self.assertNotIn("<", json.dumps(market))  # no placeholder left
        self.assertTrue((ROOT / codex["skills"]).is_dir())
        self.assertIn("agent-plugins.org", copilot["$schema"])
        self.assertTrue((ROOT / copilot["skills"]).is_dir())
        self.assertTrue(list((ROOT / copilot["agents"]).glob("*.agent.md")))
        self.assertEqual(claude["license"], "MIT")
        self.assertEqual(copilot["license"], "MIT")
        self.assertIn("MIT License", read("LICENSE"))
        version = claude["version"]
        for f in LANGUAGES["CHANGELOG"]:
            self.assertEqual(re.search(r"^## (\d+\.\d+\.\d+)", read(f), re.M).group(1), version, f)
        for en, it in (LANGUAGES["README"], LANGUAGES["architecture"]):
            self.assertIn(f"version {version}", read(en), en)
            self.assertIn(f"versione {version}", read(it), it)
        for f in LANGUAGES["README"]:
            self.assertIn(f"version-{version}-", read(f), f"{f}: version badge")

    def test_readme_badges(self):
        for f in LANGUAGES["README"]:
            text = read(f)
            self.assertTrue(text.startswith("# SDD Playbook"), f)
            badges = re.findall(r"!\[[^\]]*\]\((https://[^)]+)\)", text)
            self.assertGreaterEqual(len(badges), 8, f)
            for needle in ("license-MIT", "actions/workflows/ci.yml/badge.svg", "python-3.8", "Claude%20Code",
                           "Codex", "GitHub%20Copilot", "last-commit"):
                self.assertTrue(any(needle in b for b in badges), f"{f}: badge {needle}")

    def test_agents_hooks_and_json(self):
        for rel in ("agents/sdd-reviewer.md", "skills/sdd-init/references/copilot/sdd-reviewer.agent.md"):
            fm = frontmatter(read(rel))
            for field in ("name", "description", "tools"):
                self.assertRegex(fm, rf"(?m)^{field}:", f"{rel}: {field}")
            self.assertRegex(fm, r"(?m)^name:\s*sdd-reviewer\s*$", rel)
        json.loads(read("skills/sdd-init/references/vscode-tasks.json"))
        hooks = json.loads(read("hooks/hooks.json"))["hooks"]
        for event in hooks.values():
            for block in event:
                for h in block["hooks"]:
                    self.assertIn("hooks/run.sh", h["command"])
                    name = re.search(r"(\w+\.py)", h["command"]).group(1)
                    self.assertTrue((ROOT / "hooks" / name).is_file(), name)


class TestReferences(unittest.TestCase):
    def test_cited_scripts_exist_and_flags_are_valid(self):
        for rel, text in {**md_texts(history=False), "playbook_it": PLAYBOOK_IT}.items():
            for name in re.findall(r"scripts/(\w+)\.py", text):
                self.assertIn(name, SCRIPT_NAMES, f"{rel}: missing script {name}")
            for name, tail in re.findall(r"python scripts/(\w+)\.py([^`\n]*)", text):
                if name not in SCRIPT_NAMES:
                    continue
                source = (SCRIPTS / f"{name}.py").read_text(encoding="utf-8")
                for flag in re.findall(r"--[a-z][a-z-]*", tail):
                    self.assertIn(flag, source, f"{rel}: {name}.py does not know {flag}")

    def test_scripts_documented(self):
        for name in SCRIPT_NAMES:
            for scripts_md, readme, arch, playbook in zip(both("scripts"), both("README"), both("architecture"),
                                                          (PLAYBOOK, PLAYBOOK_IT)):
                self.assertIn(f"### {name}.py", scripts_md)
                self.assertIn(f"`{name}`", readme)
                self.assertIn(f"`{name}.py`", playbook, f"playbook does not cite {name}.py")
                self.assertIn(f"`{name}.py`", arch + scripts_md)

    def test_skills_documented_and_cited_skills_exist(self):
        for name in SKILLS:
            for skills_md, readme, guide, playbook in zip(both("skills"), both("README"), both("quick-guide"),
                                                          (PLAYBOOK, PLAYBOOK_IT)):
                self.assertIn(f"### {name}", skills_md)
                self.assertIn(f"`{name}`", readme)
                self.assertIn(f"`{name}`", playbook, f"playbook does not cite {name}")
                self.assertIn(f"`{name}`", guide, f"quick guide does not cite {name}")
        for rel, text in {**md_texts(history=False), "playbook_it": PLAYBOOK_IT}.items():
            self.assertNotRegex(text, r"\bsdlc-[a-z]", f"{rel}: old sdlc- name")
            for cited in set(re.findall(r"\bsdd-[a-z]+(?:-[a-z]+)*\b", text)):
                self.assertTrue(cited in SKILLS or cited in NON_SKILL, f"{rel}: missing skill {cited}")
        state = (SCRIPTS / "state.py").read_text(encoding="utf-8")
        for s in re.findall(r'"skill": "(sdd-[a-z-]+)"', state):
            self.assertIn(s, SKILLS)

    def test_playbook_sections_and_phases(self):
        titles = set(re.findall(r"^#{2,3} (\d+(?:\.\d+)?)[. ]", PLAYBOOK, re.M))
        titles_it = set(re.findall(r"^#{2,3} (\d+(?:\.\d+)?)[. ]", PLAYBOOK_IT, re.M))
        self.assertEqual(titles, titles_it, "the two playbooks must have the same § numbering")
        phases = set(re.findall(r"^\| (\d+)\. ", PLAYBOOK.split("## 4.")[1].split("## 5.")[0], re.M))
        steps = set(re.findall(r"^(\d+)\. \*\*", PLAYBOOK.split("## 5.")[1].split("## 6.")[0], re.M))
        self.assertTrue({"1.1", "1.2", "3.8", "6.1", "7.3", "11"} <= titles)
        for rel, text in {**md_texts(), "playbook_it": PLAYBOOK_IT}.items():
            for n in re.findall(r"§\s?(\d+(?:\.\d+)?)", text):
                self.assertIn(n, titles, f"{rel}: §{n} does not exist in the playbook")
            for n in re.findall(r"§4 \((?:phase|fase) (\d+)\)", text):
                self.assertIn(n, phases, f"{rel}: missing phase {n}")
            for group in re.findall(r"§5(?: \((?:step|passo) |, (?:steps?|passi?) |\)?,? (?:step|passo) )(\d+)(?:-(\d+))?",
                                    text):
                for n in group:
                    if n:
                        self.assertIn(n, steps, f"{rel}: missing step {n}")

    def test_environment_variables_documented(self):
        hooks = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "hooks").glob("*.py"))
        for var in ENV_VARS:
            for text in both("README") + both("scripts"):
                self.assertIn(var, text)
            self.assertIn(var, hooks)
        for text in (PLAYBOOK, PLAYBOOK_IT):
            self.assertIn("SDD_GUARD", text)
        for rel, text in {**all_texts(), **md_texts(history=False)}.items():
            if not rel.startswith(HISTORY):
                self.assertNotIn("SDLC_", text, rel)


class TestPlaybook(unittest.TestCase):
    def test_up_to_date_with_the_embedded_files(self):
        r = run([sys.executable, "tools/build_playbook.py", "--check"], ROOT)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_no_reference_to_playbook_versions(self):
        forbidden = re.compile(r"\[v\d\]|\bv[12]\b|playbook v\d|versione? [12]\b", re.I)
        for rel, text in all_texts().items():
            if rel.startswith(".github/") or rel.endswith(".json"):
                continue
            self.assertIsNone(forbidden.search(text), f"{rel}: version reference {forbidden.search(text)}")
        self.assertTrue(PLAYBOOK.startswith("# SDD Playbook: software lifecycle with coding agents\n"))
        self.assertTrue(PLAYBOOK_IT.startswith("# SDD Playbook: ciclo di vita software con coding agent\n"))

    def test_every_document_in_two_languages(self):
        for en, it in LANGUAGES.values():
            self.assertTrue((ROOT / en).is_file(), en)
            self.assertTrue((ROOT / it).is_file(), it)
            self.assertIn(it.split("/")[-1], read(en), f"{en} does not link {it}")
            self.assertIn(en.split("/")[-1], read(it), f"{it} does not link {en}")

    def test_plugin_files_are_in_english(self):
        italian = re.compile(r"\b(della|degli|delle|perché|anche|questo|quando|sono|senza|nella|oppure)\b", re.I)
        for p in [*(ROOT / "skills").rglob("*"), *(ROOT / "agents").rglob("*"), *(ROOT / "hooks").rglob("*"),
                  *(ROOT / "tools").rglob("*"), *(ROOT / "tests").rglob("*.py"), ROOT / "plugin.json",
                  *(ROOT / ".claude-plugin").glob("*.json"), ROOT / ".codex-plugin" / "plugin.json"]:
            if p.is_file() and "__pycache__" not in p.parts and p.name != "test_consistency.py":
                m = italian.search(p.read_text(encoding="utf-8"))
                self.assertIsNone(m, f"{p.relative_to(ROOT)}: Italian text '{m and m.group(0)}'")

    def test_templates_consistent_with_the_scripts(self):
        spec = read("skills/sdd-spec/references/spec-template.md")
        err, _ = spec_lint.lint_tasks(spec, read("skills/sdd-tasks/references/tasks-template.md"))
        self.assertTrue(err)  # the template must be filled in: only the placeholders remain
        self.assertTrue(all("placeholder not filled in" in e for e in err), err)
        err, warn = spec_lint.lint_plan(spec, read("skills/sdd-plan/references/plan-template.md"))
        self.assertEqual(err, [])
        self.assertTrue(warn)
        area = read("skills/sdd-sync/references/area-template.md")
        for field in ("Last aligned", "Linked specs", "## Current behaviour", "## Constraints and delicate points",
                      "## Characterization tests"):
            self.assertIn(field, area)
        review = read("skills/sdd-review-diff/references/review-template.md")
        for field in ("- Outcome:", "- Decided by:"):
            self.assertIn(field, review)
        for s in ("compliant", "compliant with reservations", "non-compliant"):
            self.assertIn(s, review)
        plan = read("skills/sdd-plan/references/plan-template.md")
        self.assertIn("## Components and files to create/modify", plan)
        self.assertIn("- Approved by / date:", plan)


class TestDocumentation(unittest.TestCase):
    def test_relative_links_valid(self):
        docs = [f for pair in LANGUAGES.values() for f in pair if not f.startswith("docs/")]
        r = run([sys.executable, str(SCRIPTS / "docs_check.py"), *docs, "docs"], ROOT)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
