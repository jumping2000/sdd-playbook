# Skill reference

*Versione italiana: [skills_IT.md](skills_IT.md)*

Each skill is a folder `skills/<name>/` with a `SKILL.md` (frontmatter `name` and `description`, then the instructions)
and, when needed, `references/` with templates. The instructions are short (under 150 lines): the method is in the
[playbook](playbook-ai-software-lifecycle.md), which every skill cites by section. Skills and templates are in
English, like every part of the plugin.

**Common conventions**
- Scripts are called as `python scripts/<name>.py` from the project root: `sdd-start` copies them there.
- Every choice, confirmation and merge is asked as **options to select** (guide
  `skills/sdd-start/references/interaction.md`): rounds of up to 4 questions, the recommended option first, always a
  free answer. The three decisions of a feature: `Confirm the spec`, `Confirm the plan`, `Merge into main` for every PR.
- The agent works on branches (`spec/<id>`, `task/<id>-T-nn`, `fix/BUG-nnn`), never commits on `main`, never merges
  without the user's selection. The merge is the only approval the process records.
- When a requirement is ambiguous, the skills stop and ask: they do not assume.

**Order:** `sdd-start` → `sdd-plan` → `sdd-task` per task (or `sdd-parallel` for independent tasks) → the last task
closes the feature. Existing code: `sdd-map` first. Bugs: `sdd-bugfix`. Anytime: `sdd-next`.

| Skill | Playbook | Produces | Checks | Your decision (options) |
|---|---|---|---|---|
| `sdd-next` | §3 | nothing (read-only) | `state.py` | which skill to run |
| `sdd-start` | §1-§3 | first time: scripts, `AGENTS.md`, `verify.py`; then `spec.md` | `verify.py`, `spec_lint.py` | confirm the spec |
| `sdd-plan` | §2, §4 | `plan.md` with the tasks, design PR | `spec_lint.py --plan` | confirm the plan, merge the design PR |
| `sdd-task` | §4 | locked tests, code, docs, PR; the last task closes the feature | `verify.py`, `trace_check.py --task`, `diff_scope.py --task`, `docs_check.py` | merge the PR |
| `sdd-parallel` | §5 | several `sdd-task` in worktrees, one PR each | as `sdd-task`, rerun after every merge | run in parallel, then each merge |
| `sdd-map` | §6 | `docs/system/map.md`, characterization tests, area page | `scan_repo.py`, `verify.py`, `docs_check.py` | map spot check, merge |
| `sdd-bugfix` | §7 | `docs/bugs/BUG-nnn.md`, red test, fix, PR | `verify.py` | expected and unchanged behaviour, merge |

---

### sdd-start

- **When:** at the start of every feature, from an idea or a request.
- **First time only:** detects stack, remote and existing code; one round of options for the real commands, Windows,
  the agents in use and the optional CI (`verify` on every PR); copies the scripts into `scripts/`, adapts `STEPS` of
  `verify.py` trying every command, creates `AGENTS.md`, `CLAUDE.md`, `.gitattributes`, `.gitignore` entries,
  `.vscode/tasks.json`, `docs/constitution.md` and the `docs/*` folders; for GitHub Copilot copies skills and reviewer
  into `.github/`. Never overwrites existing files. Also updates the scripts of an initialized project.
- **Then:** reads the code and the material before asking; plays the request back; brainstorms in rounds of options
  (goal, users, outcomes, non-scope, anti-goals, constraints, errors); asks to confirm the understanding; writes
  `spec.md` on a branch `spec/<id>` with verifiable REQs, Given/when/then ACs (only those that would catch a real
  defect), non-scope, anti-goals, assumptions marked, open questions `blocking: yes|no`; `spec_lint.py` must pass.
- **Decision:** `Confirm the spec` sets `- Status: approved` (only without blocking questions).

### sdd-plan

- **Precondition:** spec `approved`, lint green.
- **What it does:** read-only on the code; `plan.md` with the approach and a discarded alternative, the interfaces
  between components, the mandatory **flowchart**, 3 to 8 **vertical tasks** (`covers`, `files`, `depends`,
  `verify`), the review focus and the risks; self-review against the spec; `spec_lint.py --plan` must pass. Proposes
  ADRs for new dependencies or architecture decisions.
- **Decision:** `Confirm the plan`, then the **design PR** (spec and plan together) and its merge question: the merge
  approves both.

### sdd-task

- **Precondition:** spec and plan on `main`; the task ready (dependencies merged).
- **What it does:** branch `task/<id>-T-nn`; tests from the task's ACs, red for the right reason, committed alone with
  `Test-Lock: T-nn`; the code with `Task: T-nn`; `verify`, `trace_check.py --task`, `diff_scope.py --task`; the
  documentation the task changes; the task's box ticked; the PR (`references/pr-body.md`); the review of
  `sdd-reviewer`. The **last task** also writes the area page with the five diagrams from the final code and sets the
  spec to `implemented`.
- **Decision:** `Merge into main` (or `Change it`, `Leave it open`), with the checks, the reviewer's verdict, the CI
  status and the sensitive files in front of you.
- **Rules:** never weaken a test; a change to spec or plan is a new design PR; a task that outgrows its files or a
  readable PR is split.

### sdd-parallel

- **When:** `state.py` names two or more ready tasks with disjoint files.
- **What it does:** one worktree, branch and agent per task (at most 3), each following `sdd-task` up to the review;
  merges one at a time, rebasing and rechecking the others after each merge; a conflict stops the task and leads to a
  plan correction.

### sdd-map

- **When:** at the start of work on an existing codebase, and before changing an area.
- **What it does:** inventory with `scan_repo.py`, baseline as it is, the map with the five diagrams of the existing
  system, tried commands, 5 statements spot-checked, `Do not modify` and `Sensitive areas` proposed for `AGENTS.md`;
  then characterization tests of the area to change, proven able to fail, recorded in the area page.

### sdd-bugfix

- **What it does:** bug file, reproduction (no fix by intuition), expected and unchanged behaviour confirmed by the
  user, red test locked with `Test-Lock: BUG-nnn`, verified root cause (`references/debugging.md`), minimal fix,
  non-regression, PR with review and merge question. A one-line bug with an obvious cause needs no bug file.

### sdd-next

- **What it does:** runs `state.py` and reports infrastructure, specs, tasks merged and the `NEXT` step; asks which spec
  when there are several; reports open bugs; does not change anything.

## Reviewer agent: sdd-reviewer

Independent reviewer, read-only by construction (Claude Code subagent with Read, Grep, Glob; GitHub Copilot custom
agent with `read` and `search`; Codex: a new session with the same instructions). It reviews **one PR**: ACs of the
task implemented and tested by tests that could fail, tests derived from the ACs and locked before the code, no
anti-patterns, nothing outside the task, decisions within the decision rights, diagrams matching the code in the last
task. Verdict `pass` or `fix needed`, problems with file and line, what the human should read before the merge.
