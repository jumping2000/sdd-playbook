"""Test di coerenza tra skill, script, hook, template, playbook e documentazione."""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

from common import ROOT, SCRIPTS, carica, esegui, leggi

spec_lint = carica("spec_lint")
SKILLS = sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir())
SCRIPT_NOMI = sorted(p.stem for p in SCRIPTS.glob("*.py"))
PLAYBOOK = leggi("docs/playbook-ai-software-lifecycle_IT.md")  # le skill, in italiano, citano questo per §
PLAYBOOK_EN = leggi("docs/playbook-ai-software-lifecycle.md")
# Ogni documento esiste in inglese (senza suffisso) e in italiano (_IT).
LINGUE = {"README": ("README.md", "README_IT.md"), "skills": ("docs/skills.md", "docs/skills_IT.md"),
          "scripts": ("docs/scripts.md", "docs/scripts_IT.md"),
          "architecture": ("docs/architecture.md", "docs/architecture_IT.md"),
          "quick-guide": ("docs/quick-guide.md", "docs/quick-guide_IT.md")}


def entrambe(nome: str) -> list[str]:
    return [leggi(f) for f in LINGUE[nome]]
NON_SKILL = {"sdlc-playbook", "sdlc-reviewer", "sdlc-playbook-marketplace"}


def testi_md(escludi_playbook=False) -> dict[str, str]:
    out = {}
    for p in [ROOT / "README.md", ROOT / "README_IT.md", ROOT / "CHANGELOG.md", *sorted((ROOT / "docs").glob("*.md")),
              *sorted((ROOT / "skills").rglob("*.md")), ROOT / "agents" / "sdlc-reviewer.md"]:
        if escludi_playbook and p.name.startswith("playbook"):
            continue
        out[p.relative_to(ROOT).as_posix()] = p.read_text(encoding="utf-8")
    return out


def tutti_i_testi() -> dict[str, str]:
    out = {}
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if (not p.is_file() or ".git" in rel.parts or "tests" in rel.parts or "__pycache__" in rel.parts
                or p.suffix in (".zip", ".pyc")):
            continue
        out[rel.as_posix()] = p.read_text(encoding="utf-8")
    return out


class TestMetadati(unittest.TestCase):
    def test_skill(self):
        self.assertEqual(len(SKILLS), 14)
        for nome in SKILLS:
            f = ROOT / "skills" / nome / "SKILL.md"
            self.assertTrue(f.is_file(), nome)
            testo = f.read_text(encoding="utf-8")
            m = re.match(r"^---\n(.*?)\n---\n", testo, re.S)
            self.assertIsNotNone(m, f"{nome}: frontmatter mancante")
            fm = dict(re.findall(r"^(\w+):\s*(.+)$", m.group(1), re.M))
            self.assertEqual(fm.get("name"), nome)
            self.assertGreater(len(fm.get("description", "")), 40, nome)
            self.assertLess(len(testo.splitlines()), 150, nome)

    def test_riferimenti_ai_template_esistono(self):
        for nome in SKILLS:
            testo = (ROOT / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
            for rel in re.findall(r"`((?:\.\./sdlc-[a-z-]+/)?references/[\w.\-]+)`", testo):
                self.assertTrue((ROOT / "skills" / nome / rel).resolve().is_file(), f"{nome}: {rel}")

    def test_manifest_e_versioni(self):
        claude = json.loads(leggi(".claude-plugin/plugin.json"))
        codex = json.loads(leggi(".codex-plugin/plugin.json"))
        json.loads(leggi(".claude-plugin/marketplace.json"))
        self.assertEqual(claude["name"], codex["name"])
        self.assertEqual(claude["version"], codex["version"])
        self.assertTrue((ROOT / codex["skills"]).is_dir())
        prima = re.search(r"^## (\d+\.\d+\.\d+)", leggi("CHANGELOG.md"), re.M).group(1)
        self.assertEqual(prima, claude["version"])
        for en, it in (LINGUE["README"], LINGUE["architecture"]):
            self.assertIn(f"version {claude['version']}", leggi(en), en)
            self.assertIn(f"versione {claude['version']}", leggi(it), it)

    def test_agente_hook_e_json(self):
        fm = re.match(r"^---\n(.*?)\n---\n", leggi("agents/sdlc-reviewer.md"), re.S).group(1)
        for campo in ("name", "description", "tools"):
            self.assertRegex(fm, rf"(?m)^{campo}:", f"agente: {campo}")
        json.loads(leggi("skills/sdlc-init/references/vscode-tasks.json"))
        hooks = json.loads(leggi("hooks/hooks.json"))["hooks"]
        for evento in hooks.values():
            for blocco in evento:
                for h in blocco["hooks"]:
                    self.assertIn("hooks/run.sh", h["command"])
                    nome = re.search(r"(\w+\.py)", h["command"]).group(1)
                    self.assertTrue((ROOT / "hooks" / nome).is_file(), nome)


class TestRiferimenti(unittest.TestCase):
    def test_script_citati_esistono_e_flag_validi(self):
        for rel, testo in {**testi_md(), "playbook": PLAYBOOK, "playbook_en": PLAYBOOK_EN}.items():
            for nome in re.findall(r"scripts/(\w+)\.py", testo):
                self.assertIn(nome, SCRIPT_NOMI, f"{rel}: script inesistente {nome}")
            for nome, coda in re.findall(r"python scripts/(\w+)\.py([^`\n]*)", testo):
                if nome not in SCRIPT_NOMI:
                    continue
                sorgente = (SCRIPTS / f"{nome}.py").read_text(encoding="utf-8")
                for flag in re.findall(r"--[a-z][a-z-]*", coda):
                    self.assertIn(flag, sorgente, f"{rel}: {nome}.py non conosce {flag}")

    def test_script_documentati(self):
        for nome in SCRIPT_NOMI:
            for scripts_md, readme, arch, playbook in zip(entrambe("scripts"), entrambe("README"),
                                                          entrambe("architecture"), (PLAYBOOK_EN, PLAYBOOK)):
                self.assertIn(f"### {nome}.py", scripts_md)
                self.assertIn(f"`{nome}`", readme)
                self.assertIn(f"`{nome}.py`", playbook, f"playbook non cita {nome}.py")
                self.assertIn(f"`{nome}.py`", arch + scripts_md)

    def test_skill_documentate_e_citate_esistenti(self):
        for nome in SKILLS:
            for skills_md, readme, guida, playbook in zip(entrambe("skills"), entrambe("README"),
                                                          entrambe("quick-guide"), (PLAYBOOK_EN, PLAYBOOK)):
                self.assertIn(f"### {nome}", skills_md)
                self.assertIn(f"`{nome}`", readme)
                self.assertIn(f"`{nome}`", playbook, f"playbook non cita {nome}")
                self.assertIn(f"`{nome}`", guida, f"guida rapida non cita {nome}")
        for rel, testo in {**testi_md(), "playbook": PLAYBOOK, "playbook_en": PLAYBOOK_EN}.items():
            for citata in set(re.findall(r"\bsdlc-[a-z]+(?:-[a-z]+)*\b", testo)):
                self.assertTrue(citata in SKILLS or citata in NON_SKILL, f"{rel}: skill inesistente {citata}")
        stato = (SCRIPTS / "state.py").read_text(encoding="utf-8")
        for s in re.findall(r'"skill": "(sdlc-[a-z-]+)"', stato):
            self.assertIn(s, SKILLS)

    def test_paragrafi_e_fasi_del_playbook(self):
        titoli = set(re.findall(r"^#{2,3} (\d+(?:\.\d+)?)[. ]", PLAYBOOK, re.M))
        titoli_en = set(re.findall(r"^#{2,3} (\d+(?:\.\d+)?)[. ]", PLAYBOOK_EN, re.M))
        self.assertEqual(titoli, titoli_en, "i due playbook devono avere la stessa numerazione dei §")
        fasi = set(re.findall(r"^\| (\d+)\. ", PLAYBOOK.split("## 4.")[1].split("## 5.")[0], re.M))
        passi = set(re.findall(r"^(\d+)\. \*\*", PLAYBOOK.split("## 5.")[1].split("## 6.")[0], re.M))
        self.assertTrue({"1.1", "1.2", "3.8", "6.1", "7.3", "11"} <= titoli)
        for rel, testo in {**testi_md(), "playbook": PLAYBOOK, "playbook_en": PLAYBOOK_EN}.items():
            for n in re.findall(r"§\s?(\d+(?:\.\d+)?)", testo):
                self.assertIn(n, titoli, f"{rel}: §{n} non esiste nel playbook")
            for n in re.findall(r"§4 \(fase (\d+)\)", testo):
                self.assertIn(n, fasi, f"{rel}: fase {n} inesistente")
            for lista in re.findall(r"§5(?: \(passo |, passi? |\)?,? passo )(\d+)(?:-(\d+))?", testo):
                for n in lista:
                    if n:
                        self.assertIn(n, passi, f"{rel}: passo {n} inesistente")

    def test_variabili_ambiente_documentate(self):
        for var in ("SDLC_ENFORCE_VERIFY", "SDLC_VERIFY_ARGS", "SDLC_GUARD"):
            for testo in entrambe("README") + entrambe("scripts"):
                self.assertIn(var, testo)
            self.assertIn(var, "".join(p.read_text(encoding="utf-8") for p in (ROOT / "hooks").glob("*.py")))
        self.assertIn("SDLC_GUARD", PLAYBOOK)
        self.assertIn("SDLC_GUARD", PLAYBOOK_EN)


class TestPlaybook(unittest.TestCase):
    def test_aggiornato_rispetto_ai_file_incorporati(self):
        r = esegui([sys.executable, "tools/build_playbook.py", "--check"], ROOT)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_nessun_riferimento_a_versioni_del_playbook(self):
        vietato = re.compile(r"\[v\d\]|\bv[12]\b|playbook v\d|versione [12]\b", re.I)
        for rel, testo in tutti_i_testi().items():
            if rel.startswith(".github/") or rel.endswith(".json"):
                continue
            self.assertIsNone(vietato.search(testo), f"{rel}: riferimento a versione {vietato.search(testo)}")
        self.assertTrue(PLAYBOOK.startswith("# Playbook: ciclo di vita software con coding agent\n"))
        self.assertTrue(PLAYBOOK_EN.startswith("# Playbook: software lifecycle with coding agents\n"))

    def test_ogni_documento_in_due_lingue(self):
        for en, it in LINGUE.values():
            self.assertTrue((ROOT / en).is_file(), en)
            self.assertTrue((ROOT / it).is_file(), it)
        for f in ("README.md", "README_IT.md"):  # ogni README rimanda all'altra lingua
            self.assertIn("README_IT.md" if f == "README.md" else "README.md", leggi(f))

    def test_template_coerenti_con_gli_script(self):
        spec = leggi("skills/sdlc-spec/references/spec-template.md")
        err, _ = spec_lint.lint_tasks(spec, leggi("skills/sdlc-tasks/references/tasks-template.md"))
        self.assertTrue(err)  # il template va compilato: restano solo i segnaposto
        self.assertTrue(all("segnaposto non compilato" in e for e in err), err)
        err, avv = spec_lint.lint_plan(spec, leggi("skills/sdlc-plan/references/plan-template.md"))
        self.assertEqual(err, [])
        self.assertTrue(avv)
        area = leggi("skills/sdlc-sync/references/area-template.md")
        for campo in ("Ultimo allineamento", "Specifiche collegate", "## Comportamento attuale",
                      "## Vincoli e punti delicati", "## Test di caratterizzazione"):
            self.assertIn(campo, area)
        review = leggi("skills/sdlc-review-diff/references/review-template.md")
        for campo in ("- Esito:", "- Decisione di:"):
            self.assertIn(campo, review)
        for s in ("conforme", "conforme con riserve", "non conforme"):
            self.assertIn(s, review)
        plan = leggi("skills/sdlc-plan/references/plan-template.md")
        self.assertIn("## Componenti e file da creare/modificare", plan)
        self.assertIn("- Approvato da / data:", plan)


class TestDocumentazione(unittest.TestCase):
    def test_link_relativi_validi(self):
        r = esegui([sys.executable, str(SCRIPTS / "docs_check.py"), "README.md", "README_IT.md", "docs", "CHANGELOG.md"],
                   ROOT)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
