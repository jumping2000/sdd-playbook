# Quick guide

*Versione italiana: [quick-guide_IT.md](quick-guide_IT.md)*

How to use `sdd-playbook` on a new project (greenfield) or an existing one (brownfield). This guide tells you **what to
do and in which order**; the reasons and the details are in the [playbook](playbook-ai-software-lifecycle.md), each skill
in the [skill reference](skills.md), the scripts in the [script reference](scripts.md).

> The plugin is **in design** and has not yet been used on a real project. Before trusting it with an important project,
> follow the trial path at the end of this page.
>
> Skills, templates and script messages are in English. Field names such as `- Status:`, `- Level:`,
> `tests approved:` or `expected: red` are part of the file contracts read by the scripts: keep them as they are.

## In one sentence

You decide **what** to build and approve the key points; the agent writes spec, plan, tests and code; the scripts check
that every step was really done. At any time `sdd-next` (or `python scripts/state.py`) tells you where you are and which
skill comes next.

## Before you start (once)

| What | Why |
|---|---|
| Install the plugin: `claude --plugin-dir <path>/sdd-playbook` to try it (Codex and GitHub Copilot: see the README) | Makes the 14 skills available |
| Python 3 and git on the machine | The scripts are Python, standard library only |
| A **separate identity** for the agent: the simplest setup is that the agent commits only locally and you push the branches | Approvals are text the agent can write; a merge into `main` is not |
| On the platform: protected `main` with required PRs, required CI, required code-owner review | It is the only control the agent cannot bypass. The plugin creates the templates, you set the rules |

You invoke a skill by asking the agent to use it, for example *"use sdd-spec for a CSV export feature"*.

## Greenfield (empty repository)

1. **`sdd-init`**. The agent detects the environment and asks, in a single message, for the stack, the real
   format/lint/type/test commands and whether the team uses Windows. It copies the scripts into `scripts/` and creates
   `AGENTS.md`, `CLAUDE.md`, `docs/`, `.gitignore`, `.gitattributes`, the VS Code task, CI, `CODEOWNERS` and the PR
   template. **Gate:** you approve principles, stack and `verify` steps.
2. Configure branch protection for `main` on the platform (see above) and list the approvers in `.github/CODEOWNERS`.
3. For every feature, the **feature cycle** below.

## Brownfield (existing code)

1. **`sdd-init`**, as above. If it finds code, the next step is the map.
2. **`sdd-map-codebase`** (read-only). Starting from the `scan_repo.py` inventory, it reads the code and writes
   `docs/system/map.md` with real, tried commands and the **baseline**: which tests already pass and which do not. A
   pre-existing red is not the agent's fault. **Gate:** you spot-check the map.
3. **Complete `AGENTS.md`** with two lines the scripts enforce, paths in backticks:
   ```
   - Do not modify: `migrations/applied/`, `src/generated/`
   - Sensitive areas: `src/auth/`, `src/payments/`
   ```
   "Non modificare" (do not modify) zones are never touched; "Aree sensibili" (sensitive areas) require level L.
4. **`sdd-characterize`** on the area you want to change: tests that pin the current behaviour (even if wrong) and
   proof that they can fail. **Gate:** spot check.
5. The **feature cycle**, with a spec that describes **only the change**, not the whole system.

Repeat steps 2-4 one area at a time, only where you are about to work: there is no need to document everything upfront.

## Feature cycle (greenfield and brownfield)

| # | Skill | What you get | Your role |
|---|---|---|---|
| 1 | `sdd-spec` | `docs/specs/<date-slug>/spec.md`: requirements, acceptance criteria, non-scope, **level** | Answer the open questions, then **approve** (name and date) |
| 2 | `sdd-plan` (not at level S) | `plan.md`: files to touch, test strategy, dependencies, risks | **Approve** |
| 3 | `sdd-tasks` | `tasks.md`: small tasks, each with a verification command | Quick check |
| — | **Design PR** | spec, plan and tasks on a branch | **Your merge into `main` is the approval** |
| 4 | `sdd-tests-from-ac` (called by `sdd-implement`) | Red tests written from the ACs, locked by a `Test-Lock` commit | **Read the tests** and approve: `tests approved: <name, date, sha>` (levels M and L) |
| 5 | `sdd-implement`, or `sdd-loop` for many independent tasks | The code that makes the tests pass without changing them | — |
| 6 | `sdd-review-diff` (not at level S) | `review.md`, from a fresh-context reviewer that tries to refute the result | **Decide**; at level L also read the diff |
| 7 | `sdd-docs` | README, API docs, executed examples | Review |
| 8 | `sdd-sync` | Spec `implemented`, area page in `docs/system/` | Review, then the **implementation PR** |

If the review is `non-compliant` (not compliant), the problems become tasks `T-R01`, `T-R02`… implemented like the others;
then the review is repeated. `sdd-next` tells you so.

### Choosing the level

| Level | When | What changes |
|---|---|---|
| **S** | All true: at most 3 production files, no sensitive area, no dependency, no public interface | No plan and no `review.md`; the review is the PR review |
| **M** | The normal case | The full cycle |
| **L** | Sensitive areas, public interfaces, data migrations | Plus an ADR for the decisions and your **reading of the diff** |

The level is approved with the spec and is part of its hash. If the real diff exceeds it, `diff_scope.py` reports an
error. When in doubt, pick the higher level.

## Bugs

`sdd-bugfix`, alongside the cycle: reproduction (if it does not reproduce, the agent stops), expected behaviour and
**behaviour that must NOT change** (you confirm both), red test, diagnosis, minimal fix, non-regression. For a trivial bug
(obvious cause, one line) a red test, the fix and `verify` are enough.

## The autonomous loop (optional)

`sdd-loop` prepares everything but **launches nothing**: you launch it, in a separate terminal and an isolated
environment (container without network, no secrets). You agree on iteration cap, stall limit and timeout; the agent runs
the dry run and shows you the command:

```
python scripts/loop.py docs/specs/<id> --max 15 --stall 3 --timeout 1800 --junit reports/junit.xml
```

The loop pauses after every test task (levels M and L) so that you can approve the tests, and ends successfully only if
`verify` and the final checks pass (`spec_lint`, `trace_check`, `diff_scope`, `secrets_check`). Use the example
permissions file `skills/sdd-loop/references/settings.loop.json`.

## Commands you will use most

| Command | When |
|---|---|
| `python scripts/state.py` | Where am I, what is the next step |
| `python scripts/verify.py` | Format, lint, types, tests and secrets: the definition of "done" |
| `python scripts/spec_lint.py <spec> --plan <plan> --tasks <tasks> --base main` | Spec, plan and tasks valid and already approved by the merge |
| `python scripts/spec_lint.py <file> --hash` | The hash to write in `- Hash:` after an approval |
| `python scripts/trace_check.py <spec> --junit reports/junit.xml` | Every AC has an executed, passing test |
| `python scripts/diff_scope.py docs/specs/<id>` | Forbidden zones, locked tests, level, dependencies, out-of-plan files |
| `python scripts/sync_check.py docs/specs/<id> --junit reports/junit.xml` | Feature closed and reconciled |

## Safety hooks (Claude Code only, optional)

Not available in Codex and GitHub Copilot: there, the safety net is CI, branch protection and the agent's permissions.


| Variable | Effect |
|---|---|
| `SDD_ENFORCE_VERIFY=1` | The agent cannot declare the work finished with `verify` red (except in the red phase) |
| `SDD_GUARD=1` | Blocks forced pushes, recursive deletes, `reset --hard`, access to `.env` |

They are a safety net, not a sandbox: the real defence is permissions, isolation and CI.

## Common problems

| Symptom | What to do |
|---|---|
| `state.py` says `choose` (choose) | Several active specs: work on the branch whose name contains the spec, or use `--spec <id>` |
| An approval "lapses" | The content changed after the approval (the hash no longer matches): get it re-approved and recompute the hash |
| `diff_scope.py`: "level underestimated" | The change is bigger than the declared level: raise the level in the spec and get it re-approved |
| `diff_scope.py`: "dependencies changed without plan or ADR" | List the manifest in the approved plan or add an ADR in `docs/adr/` |
| `diff_scope.py`: "tests approved: ... new Test-Lock commit after the approval" | The tests changed after your approval: read them again and approve the new `Test-Lock` commit |
| `verify` red after the tests | It is the **red phase**, expected until the implementation task is done |
| The loop stops right away | Read the reason: cap, stall or tests to approve. Do not relaunch blindly: review spec and plan |

## Recommended trial path

1. **Toy greenfield:** one level-S feature, then one level-M feature, everything interactive.
2. **Brownfield:** a real but non-critical repository, one mapped and characterized area, one level-M change.
3. **The loop last**, in a container without network and with `settings.loop.json`.

Write down every point where the agent misreads a skill: those are the most valuable corrections for the plugin.
