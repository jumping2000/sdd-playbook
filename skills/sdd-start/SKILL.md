---
name: sdd-start
description: Use this skill to start any new feature from an idea or a request: it initializes the project the first time (scripts, AGENTS.md, verify), explores and clarifies the request with the user through rounds of options, and writes the spec (requirements, acceptance criteria, non-scope) to confirm. Use it before any plan or code.
---

# Start: from the idea to the confirmed spec

Playbook §1-§3. Choices and the confirmation are asked as options (guide: `references/interaction.md`).

## 1. Initialize, only the first time

If `AGENTS.md` and `scripts/verify.py` both exist, skip to step 2. Otherwise, without overwriting existing files (show
the difference and ask):
1. **Python first.** The playbook scripts need Python 3.8+: try `python3 --version`, `python --version`, `py -3
   --version` (Windows) and keep the first that answers 3.8 or later. If none does, stop and give the install command
   for the user's system (Windows: `winget install Python.Python.3.12`; macOS: `brew install python`; Debian/Ubuntu:
   `sudo apt install python3`; Fedora: `sudo dnf install python3`). In the skills `python` stands for that interpreter.
2. **Detect** (read-only): operating system, git and remote (`git remote -v`), stack and package manager
   (`references/stacks.md`), existing code, infrastructure included (Dockerfile, Compose, Helm). With existing code,
   after this step propose `sdd-map` before the spec.
3. **One round of options** for what you cannot detect: the real format/lint/type/test commands, whether anyone
   develops on Windows, which agents are used (Claude Code, Codex, GitHub Copilot), and, with a GitHub remote, whether
   to add the CI that runs `verify` on every PR (recommended).
4. **Copy** the skill's `scripts/` into the project's `scripts/` (`verify.py`, `spec_lint.py`, `trace_check.py`,
   `diff_scope.py`, `state.py`, `docs_check.py`, `secrets_check.py`, `scan_repo.py`); line 2 of each carries the plugin
   version. Adapt `STEPS` in `scripts/verify.py`, running every command by hand first; never invent a step.
5. **Create:** `AGENTS.md` from `references/AGENTS.md.tmpl` (under 100 lines, with the Python interpreter found; the
   user gives the `Do not modify` and `Sensitive areas` paths, the `Test files` and `Dependency manifests` the scripts do
   not recognize, and reviews the decision rights), `CLAUDE.md` with the line `@AGENTS.md`,
   `.gitattributes` from `references/gitattributes.tmpl`, `reports/` and `__pycache__/` in `.gitignore`,
   `.vscode/tasks.json` from `references/vscode-tasks.json`, `docs/constitution.md` from
   `references/constitution.md.tmpl`, the folders `docs/specs/`, `docs/system/`, `docs/bugs/`, `docs/adr/`, and, if
   chosen, `.github/workflows/verify.yml` from `references/ci-github-actions.yml`. GitHub Copilot outside the CLI
   plugin: copy the plugin's `skills/` folders into `.github/skills/` and `references/copilot/sdd-reviewer.agent.md`
   into `.github/agents/`.
6. **Run** `python scripts/verify.py` and report the result as it is; ask to confirm `AGENTS.md` and the `verify` steps
   (options), then commit the initialization on `main` (it is the starting point, not a feature).

**Updating** an initialized project: compare line 2 of every `scripts/*.py` with the skill's; copy the newer ones after
confirmation, in one commit, never overwriting the `STEPS` of `verify.py`; read the plugin CHANGELOG for format
changes.

## 2. Explore the request

1. **Look before you ask.** Read `AGENTS.md` (its `## Areas` index says where each area is documented),
   `docs/constitution.md` and the material the user pointed to. Never ask what the project already answers.
2. **Impact analysis, when the request changes existing code** (an app built with the playbook or not):
   - the area pages `docs/system/<area>.md` and the specs they link, `docs/system/map.md`, the ADRs involved;
   - the code the request touches and its callers, read from the entry points down;
   - the tests that protect that behaviour today (run them: they must be green before you start);
   - `git log` of the files involved: recent changes and their reasons.
   Show the result in a few lines: **what exists today, what changes, what must not change, which tests protect it**.
   If no test protects a behaviour that must not change, propose characterization tests first (`sdd-map`, part 2). If
   the code has never been mapped, propose `sdd-map` before the spec.
3. **Play it back.** In a short message restate what the user wants, for whom and why, and what it would touch; say
   plainly if you found a constraint, a conflict or a cheaper path.

## 3. Brainstorm in rounds of options

One round of up to 4 questions, each with 2-4 options (the recommended one first, with its reason) and a free answer;
a follow-up round only for what the answers opened. A simple request needs one or two rounds. Cover: goal and success
criterion, users, really different outcomes for the user, non-scope, **anti-goals** (what would make it a failure even
if it works), constraints, error cases. Do not answer the questions yourself. Then ask to **confirm the understanding**
in a few lines (options: `That's it`, `Correct it`).

## 4. Write the spec

`docs/specs/<id>/spec.md` from `references/spec-template.md`, on a branch `spec/<id>`. The `<id>` is today's date plus
a short lower-case slug (`2026-10-24-export-csv`): folder name and title (`# SPEC-2026-10-24-export-csv: Export CSV`).
- every requirement is a verifiable sentence; every REQ has at least one AC in Given/when/then form, with an error case
  where it makes sense; keep only the ACs that would catch a real defect;
- the **non-scope** is mandatory and concrete; in an existing codebase describe only the change, and fill in
  `## Current behaviour and impact` from the impact analysis (`- none (new area)` for new code);
- the **anti-goals** record what the user said would make the feature a failure;
- every assumption is marked `[ASSUMPTION]`; vague words ("fast", "appropriate", "etc") are replaced;
- open questions: `- <question> — blocking: yes|no`; blocking means the answer would change a REQ or an AC.

Check with `python scripts/spec_lint.py docs/specs/<id>/spec.md` until there are no errors; report the warnings.

## STOP

Summarize REQs, ACs, non-scope, anti-goals and open questions, and ask the spec decision with options (`Confirm the
spec`, `Change it`, `Stop here`). Only blocking-free specs can be confirmed. On `Confirm the spec`, set
`- Status: approved`, rerun `spec_lint.py` and commit the spec on its branch. Do not write the plan or code here.
Next step: `sdd-plan`.

## Revising a spec already on `main`

When a task got stuck on a requirement (`sdd-task`, option `Revise the spec`) or the user asks for it:
1. Branch `revise/<spec id>` from an up-to-date `main`; the change plus an entry in `## Revisions` (date, what, why).
   Questions about the change in rounds of options, as in step 3; no blocking question may remain.
2. If REQs or ACs changed, the plan must follow on the same branch ("Revising a plan" of `sdd-plan`): an AC of a merged
   task that changes needs a new task.
3. The spec decision (`Confirm the spec`), then the **revision PR** with the merge question (with the plan, if revised).
