---
name: sdd-init
description: Use this skill to prepare a repository for the coding-agent development cycle: it creates AGENTS.md, the playbook scripts (cross-platform verify for Windows and VS Code, spec lint, traceability, state, loop), the docs/ structure and CI. Use it once per project, before writing specs or code.
---

# Project initialization

The files in `scripts/` and `references/` of **this skill** are relative to the skill folder. The scripts must be
copied into the project, not read from here at every use: the project must stay verifiable in CI and from VS Code even
without the plugin. Playbook §1, §1.1, §3.1, §3.2.

**Absolute rule:** never overwrite existing files. If they exist, show the difference and ask; for
`.vscode/tasks.json` merge the tasks, without replacing the file.

## Steps

1. **Detect** (read-only): operating system, whether it is a git repo, language and package manager (see
   `references/stacks.md`), whether there is already code. If there is source code it is a **brownfield**: after init
   the next step is `sdd-map-codebase`; before touching anything run the existing tests and note the result as the
   baseline.
2. **Ask in a single message** what you cannot detect: confirmation of the stack, real format/lint/type/test commands,
   whether the team also develops on Windows (decides the CI matrix), CI provider (default GitHub Actions), which agents
   the team uses (Claude Code, Codex, GitHub Copilot). Do not assume.
3. **Copy the scripts** from the skill's `scripts/` to the project's `scripts/`: `verify.py`, `state.py`,
   `spec_lint.py`, `trace_check.py`, `bug_lint.py`, `diff_scope.py`, `docs_check.py`, `sync_check.py`, `scan_repo.py`,
   `loop.py`, `secrets_check.py`, `review_package.py`. The other skills expect `python scripts/<name>.py`. Every
   script carries the plugin version on line 2 (`# sdd-playbook: <version>`).
4. **Adapt `STEPS` in `scripts/verify.py`** to the real commands. Run every command by hand before registering it. Do
   not register steps the project does not have and do not invent tests: if there are none, say so.
5. **Create** (only if missing):
   - `AGENTS.md` from `references/AGENTS.md.tmpl`, filled in with what you verified (under 100 lines); the user gives
     the `Sensitive areas` (level L, playbook §2.1) and reviews the **Decision rights** (the defaults are a starting
     point; the team may move lines between "Decides alone" and "Asks first", while "Never" only grows);
   - `CLAUDE.md` with the single line `@AGENTS.md` (no symlinks: on Windows they need privileges);
   - `.gitattributes` from `references/gitattributes.tmpl`; `reports/` and `__pycache__/` in `.gitignore` (JUnit
     report of the tests, see `references/stacks.md`; otherwise the loop mistakes them for progress);
   - `.vscode/tasks.json` from `references/vscode-tasks.json`;
   - `docs/glossary.md` from `references/glossary.md.tmpl`, only if the user wants to fix the domain terms (optional;
     `spec_lint.py` then warns on the synonyms to avoid);
   - `docs/constitution.md` from `references/constitution.md.tmpl`, and the folders `docs/specs/`, `docs/system/`,
     `docs/bugs/`, `docs/adr/` (with `.gitkeep`);
   - the CI workflow from `references/ci-github-actions.yml`, completing the toolchain setup; remove `windows-latest`
     if the team does not develop on Windows. The "Process checks" step runs `spec_lint`, `diff_scope`,
     `trace_check --junit` and `secrets_check` on PRs: it is the check the agent cannot bypass;
   - `.github/CODEOWNERS` from `references/CODEOWNERS.tmpl` (ask who approves; the agent's identity must not be
     listed) and `.github/pull_request_template.md` from `references/pull_request_template.md`.
6. **GitHub Copilot** (only if the team uses it outside the Copilot CLI plugin, e.g. cloud agent, VS Code, Visual
   Studio): copy the plugin's `skills/` folders into the project's `.github/skills/` (same folder names), and
   `references/copilot/sdd-reviewer.agent.md` into `.github/agents/`. Copilot reads `AGENTS.md` directly.
7. **Run** `python scripts/verify.py` and report the result as it is. If it is red because tests are missing, it is not
   an initialization error: say so.
8. **Run** `python scripts/state.py` to show the resulting state.

## Updating an already initialized project

If the user asks to update the scripts: compare the `# sdd-playbook:` line of every `scripts/<name>.py` with the
skill's. For every older or missing script show the difference and copy it after confirmation, in a dedicated commit.
`verify.py` is never overwritten: it contains the project's `STEPS`, so bring over only the new template lines (for
example the `secrets` step) and let the user decide. Also update `.gitignore` (`reports/`, `__pycache__/`), the CI
workflow ("Process checks" step of the template) and, for Copilot, `.github/skills/` and `.github/agents/`. Then run
`verify` and `state.py`, and read the plugin CHANGELOG for format changes (new fields in spec, tasks and review).

## STOP

Present `AGENTS.md`, `docs/constitution.md` and the `verify` steps to the user and ask for approval of principles and
stack. Do not create specs, do not commit and do not proceed without an answer.

Also report two limits: the generated CI has not been run (the first run must be checked) and the plugin's optional
hooks (Claude Code) are not enabled by this skill.

Finally ask which identity setup the user adopts (playbook §1.2: agent without push, or bot account or token without
merge rights) and remind them what they must set on the platform: protection of `main` with required PRs, code-owner
review and CI. You cannot do it and you must not ask for credentials.
