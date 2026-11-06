---
name: sdd-task
description: Use this skill to carry out one task of a merged plan: its own branch, tests written from the task's acceptance criteria and locked before the code, the implementation, verify, the documentation the task changes, a PR reviewed by the independent sdd-reviewer and the question whether to merge it into main. The last task also closes the feature.
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

## Steps

1. **Branch** `task/<spec id>-T-nn` from an up-to-date `main`. Read the task line, its ACs in the spec, the plan's
   interfaces and review focus, the decision rights of `AGENTS.md`.
2. **Tests first, from the ACs** (`references/test-conventions.md`): one or more tests per covered AC, with the error
   cases and the review focus cases assigned to the task; the ID in the name or a declared file. They must be **red
   for the right reason** (an assertion, not an import or syntax error): run the task's `verify:` command and show the
   failure. Check the anti-patterns of the conventions, then commit the test files alone with the trailer
   `Test-Lock: T-nn` (a minimal skeleton, if needed to run them, goes in an earlier commit). From now on those tests
   do not change: `diff_scope.py` reports any later change as an error. A test that turns out wrong is fixed in a new
   `Test-Lock: T-nn` commit, explained in the PR.
3. **Implement** the smallest code that makes the tests pass, within the task's files and the plan's interfaces.
   Commit with the trailer `Task: T-nn`. Decide alone only what "Decides alone" allows and write each such decision
   in the PR description; for "Asks first", or a decision no line names, stop and ask with options; never do what
   "Never" lists.
4. **Verify:** `python scripts/verify.py` green (full, not only the new tests);
   `python scripts/trace_check.py <spec> --task T-nn` (with `--junit reports/junit.xml` when `verify` writes it);
   `python scripts/diff_scope.py <spec dir> --task T-nn`. Fix until there are no errors; read the warnings.
5. **Documentation in the same PR:** if the task changes documented behaviour, update README, API docs or the area
   page `docs/system/<area>.md`; run the examples you write (`python scripts/docs_check.py --run-examples` for marked
   Python blocks). Tick the task's box in `plan.md`.
6. **Last task of the feature** (every other task already merged): also write or update the area page from
   `references/area-template.md` with the **five diagrams redrawn from the final code** (guide: search for
   `**/sdd-plan/references/diagrams.md`), add the spec to its "Linked specs", set `- Status: implemented` in the spec,
   and run `python scripts/trace_check.py <spec>` (every AC of the feature) and `python scripts/docs_check.py`.
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

- Ambiguous or missing requirement, or a change the non-scope forbids: stop and ask; a change to spec or plan is a new
  design PR, never an edit inside a task.
- A task that grows beyond its files or beyond a PR readable in 15-30 minutes: stop and propose to split it.
- Never weaken, skip or delete a test to make it pass; never declare a task done without a green `verify`.
- After 3 failed attempts at the same problem, stop and report: the cause is probably in the plan.
