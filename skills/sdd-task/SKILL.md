---
name: sdd-task
description: Use this skill to carry out one task of a merged plan: its own branch, tests written by the sdd-test-writer agent from the task's acceptance criteria and locked before the code, the implementation by the sdd-multitask agent, verify, the documentation the task changes, a PR reviewed by the independent sdd-reviewer and the question whether to merge it into main. The last task also closes the feature.
---

# One task, one PR

Playbook §4. Choices and the merge are asked as options (guide: search for `**/sdd-start/references/interaction.md`).

## Preconditions

- Spec and plan are on `main` (the design PR was merged) and `python scripts/spec_lint.py <spec> --plan <plan>`
  passes. Otherwise point to `sdd-plan`.
- The task is ready: open on `main` and its dependencies merged (`python scripts/state.py` names it). A task whose
  predecessor is not merged yet does not start: it would build on code that may still change.
- `python scripts/verify.py` on `main` gives the baseline: if it is already red, say so; it is not your fault and must
  not be hidden.
- **The mode, chosen by the user:** run `python scripts/state.py` and ask with options `Standard (T-nn)`, `Parallel
  (T-aa, T-bb)` when it lists a parallel group, `Stop here`; when it gives a `not parallel` reason, show it and offer
  `Standard` or `Stop here`. `Parallel` continues with `sdd-parallel`.

## Steps

1. **Branch** `task/<spec id>-T-nn` from an up-to-date `main`. Read the task line, its ACs in the spec, the plan's
   interfaces and review focus, the decision rights of `AGENTS.md`.
2. **Tests, by `sdd-test-writer`** (a subagent in Claude Code, a custom agent in GitHub Copilot). Give it the spec,
   the plan, the task ID, the folder and branch, and the report path `reports/tasks/<spec id>/T-nn-tests.md`. It writes
   the tests from the task's ACs (`references/test-conventions.md`), red for the right reason, and commits them alone
   with the trailer `Test-Lock: T-nn` (a minimal skeleton, if needed, in an earlier commit). From now on those tests do
   not change: `diff_scope.py` reports any later change as an error.
3. **Code, by `sdd-multitask`**, a different agent. Give it the spec, the plan, the task ID, the folder and branch, the
   SHA of the `Test-Lock` commit, the report path `reports/tasks/<spec id>/T-nn-code.md`, and whether it is the last
   task (step 6). It writes the smallest code that makes the locked tests pass (commits `Task: T-nn`), runs the checks,
   updates the documentation the task changes and ticks the task's box in `plan.md`. It decides alone only what
   "Decides alone" of `AGENTS.md` allows and lists those decisions in its report: copy them into the PR description.
4. **Handle the status** each agent returns, then relaunch it with the answer:
   - `NEEDS_DECISION`: ask the user its question with options;
   - `TEST_DISPUTE`: ask `Fix the test` (`sdd-test-writer` fixes it in a new `Test-Lock: T-nn` commit, explained in the
     PR), `Keep the test` (`sdd-multitask` goes on) or `Revise the spec`;
   - `BLOCKED`: the stop options below.
   Agents do not launch other agents and do not ask the user: you do. **Without subagents** (Codex, or a host that
   cannot delegate) do both phases yourself, one after the other, following `agents/sdd-test-writer.md` and then
   `agents/sdd-multitask.md` of the plugin: tests committed and locked before any code.
5. **Check again yourself:** `python scripts/verify.py` (full), `python scripts/trace_check.py <spec> --task T-nn`
   (with `--junit reports/junit.xml` when `verify` writes it), `python scripts/diff_scope.py <spec dir> --task T-nn`.
   The agents' reports are evidence; these checks are the proof. Fix with the agent that owns the problem.
6. **Last task of the feature** (every other task already merged): `sdd-multitask`, told it is the last one, also
   writes or updates the area page from `references/area-template.md` with the **five diagrams redrawn from the final
   code** (guide: `**/sdd-plan/references/diagrams.md`), adds the spec to its "Linked specs", sets
   `- Status: implemented` and runs `python scripts/trace_check.py <spec>` (every AC) and `python scripts/docs_check.py`.
   You propose for `AGENTS.md` (options `Apply`, `Skip`) one line in `## Areas` for the area page (path and what it
   covers) and the lessons the feature taught that apply to the whole project (a command, a trap, a convention).
7. **PR:** push the branch and open the PR with the body of `references/pr-body.md` (covered ACs, check results,
   `SENSITIVE` line of `diff_scope.py`, decisions taken alone, documentation touched). Without a remote, the branch
   plays the PR.
8. **Independent review:** Claude Code: the `sdd-reviewer` subagent; GitHub Copilot: the `sdd-reviewer` custom agent;
   other agents: a new session with the same instructions (`agents/sdd-reviewer.md` of the plugin). Give it the spec
   folder, the task ID, the output of `git diff main...HEAD` and of the checks: it has no shell. Put its verdict in
   the PR. A `high` or `medium` problem is fixed before the merge question (new commits, same branch).

## STOP: the merge question

Show in a few lines the covered ACs, the check results, the reviewer's verdict, the CI status (when there is a CI) and
the `SENSITIVE` files to read, then ask with options: `Merge into main`, `Change it` (they say what), `Leave it open`.
Merge only after `Merge into main`, as the guide says; then report what `python scripts/state.py` proposes next.

## Stop rules

- **Stop** when: a requirement is ambiguous or missing; the task needs a change the non-scope forbids; the task grows
  beyond its files or beyond a PR readable in 15-30 minutes; after **3 failed attempts** at the same problem (the
  cause is probably in the spec or the plan).
- Never weaken, skip or delete a test to make it pass; never declare a task done without a green `verify`; never edit
  spec or plan inside a task.
- **When you stop**, report in a few lines what fails, what you tried and what you think is wrong, write it in the PR
  description (or the branch's last commit message without a remote), then ask with options:
  - `Revise the spec`: a requirement or an AC is wrong or missing → follow "Revising a spec" of `sdd-start` (search
    for `**/sdd-start/SKILL.md`);
  - `Revise the plan`: the approach, the interfaces or the task split are wrong → follow "Revising a plan" of
    `sdd-plan` (search for `**/sdd-plan/SKILL.md`);
  - `Try another approach`: the user describes it; one more round of at most 3 attempts on the same task;
  - `Stop here`: the branch and its PR stay open as they are.
  Follow the chosen skill yourself in the same session, after the selection: skills do not call each other.
