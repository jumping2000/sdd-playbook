# Quick guide

*Versione italiana: [quick-guide_IT.md](quick-guide_IT.md)*

How to use SDD Playbook on a new or an existing project. The method is in the
[playbook](playbook-ai-software-lifecycle.md); here only the steps.

## In one sentence

You decide **what** to build and **whether to merge it**, always by selecting an option; the agent writes spec, plan,
tests and code; the scripts check that every step was really done. At any time `sdd-next` (or
`python scripts/state.py`) tells you the next step.

## Before you start

| What | Why |
|---|---|
| Install the plugin (README, "Installation") | Makes the 7 skills available |
| Python 3.8+ and git on the machine, whatever the project's language | The playbook scripts are Python, standard library only; `sdd-start` checks it first and tells how to install it |
| Optional: a GitHub remote | One PR per task, and a CI that runs `verify` on every PR |

You invoke a skill by asking the agent, for example *"use sdd-start for a CSV export of the reports"*.

## A feature, from the idea to `main`

| # | Skill | What you get | Your decision (options) |
|---|---|---|---|
| 1 | `sdd-start` | The first time: scripts in `scripts/`, `AGENTS.md`, `verify.py` adapted to your commands. Then: questions in rounds of options and `docs/specs/<date-slug>/spec.md` with requirements, acceptance criteria, non-scope, anti-goals | `Confirm the spec` |
| 2 | `sdd-plan` | `plan.md`: approach, interfaces, flowchart, 3 to 8 vertical tasks (each with its ACs, files, dependencies and verify command); the design PR | `Confirm the plan`, then `Merge into main` for the design PR |
| 3 | `sdd-task` (one per task) | Branch, tests from the task's ACs locked by a `Test-Lock` commit, the code, `verify` green, the documentation it changes, a PR reviewed by `sdd-reviewer` | `Merge into main`, `Change it` or `Leave it open` |
| — | `sdd-parallel` (when proposed) | Independent tasks with different files run together, one worktree and one PR each | `Run them in parallel`, then each merge |
| 4 | the last `sdd-task` | Also the area page in `docs/system/` with the five diagrams from the final code, and the spec `implemented` | `Merge into main` |

Before every merge question you see the covered ACs, the check results, the reviewer's verdict, the CI status and the
**sensitive files** (`SENSITIVE` in `diff_scope.py`): read the diff of those before merging. A task whose predecessor
is not merged does not start. To change spec or plan after the design PR: a new spec/plan PR, never an edit inside a
task.

## Existing code

1. **`sdd-start`** initializes the project; with existing code it proposes the map first.
2. **`sdd-map`** (read-only on the code): inventory, real commands tried, **baseline** (a red one is declared, not your
   fault), `docs/system/map.md` with its diagrams, and the `Do not modify` and `Sensitive areas` lines for
   `AGENTS.md`:
   ```
   - Do not modify: `migrations/applied/`, `src/generated/`
   - Sensitive areas: `src/auth/`, `src/payments/`
   ```
   "Do not modify" zones are never touched (error); "Sensitive areas" are flagged in every PR that touches them.
3. **`sdd-map`, part 2**, on the area you want to change: characterization tests that pin the current behaviour and
   are proven able to fail.
4. The feature flow above, with a spec that describes **only the change**.

## Bugs

`sdd-bugfix`: reproduction (no reproduction, no fix), expected behaviour and **behaviour that must NOT change** (you
confirm both), red test locked, verified root cause, minimal fix, PR and merge question. A trivial bug (obvious cause,
one line) needs only a red test, the fix and `verify`.

## Commands you will use most

| Command | When |
|---|---|
| `python scripts/state.py` | Where am I, what is the next step, which tasks are ready |
| `python scripts/verify.py` | Format, lint, types, tests and secrets: the definition of "done" |
| `python scripts/spec_lint.py <spec> --plan <plan>` | Spec and plan valid, tasks well formed |
| `python scripts/trace_check.py <spec> --task T-01 --junit reports/junit.xml` | The task's ACs have executed, passing tests |
| `python scripts/diff_scope.py docs/specs/<id> --task T-01` | Forbidden zones, locked tests, files outside the task, sensitive files |

## Safety hooks (Claude Code only, optional)

Not available in Codex and GitHub Copilot: there, the safety net is the CI and the agent's permissions.

| Variable | Effect |
|---|---|
| `SDD_ENFORCE_VERIFY=1` | The agent cannot declare the work finished with `verify` red (except right after a `Test-Lock` commit) |
| `SDD_GUARD=1` | Blocks forced pushes, `reset --hard`, recursive deletes, download-and-execute, reading `.env` |

They are a safety net, not a sandbox.

## Common problems

| Symptom | What to do |
|---|---|
| `state.py` says `choose` | Several active specs: work on the branch whose name contains the spec, or use `--spec <id>` |
| `state.py`: "spec and plan not on main yet" | Open and merge the design PR: it is the approval |
| `state.py`: "no task ready" | Merge the open PRs: the next tasks depend on them |
| `spec_lint.py`: "blocking open questions" | Answer them, or mark `blocking: no` those whose answer would not change a REQ or an AC |
| `spec_lint.py`: "N tasks (usually at most 8)" | Split the feature into two specs, or merge tasks into vertical slices |
| `diff_scope.py`: "locked test changed after locking" | The tests were changed after the `Test-Lock` commit: undo it, or fix the test in a new `Test-Lock` commit explained in the PR |
| `diff_scope.py`: "file outside the task" | Expected? Say it in the PR. Otherwise move the change to its own task |
| `verify` red right after the tests | It is the **red phase**, expected until the implementation is done |
| The agent stopped on a task after 3 attempts | Choose `Revise the spec`, `Revise the plan`, `Try another approach` or `Stop here`; a revision goes through a revision PR |

## Recommended trial path

1. **Toy greenfield:** one small feature (the Langfuse Docker stack tried with 0.17.0 is a good benchmark), everything
   interactive, one PR per task.
2. **Two independent tasks** with `sdd-parallel`.
3. **Brownfield:** a real but non-critical repository, one mapped and characterized area, one change.

Write down every point where the agent misreads a skill: those are the most valuable corrections for the plugin.
