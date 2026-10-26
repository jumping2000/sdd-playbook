---
name: sdd-implement
description: Use this skill to implement the T-nn tasks of tasks.md one at a time, with verification at every step (scripts/verify.py), commits on a feature branch when green and state updates; use it after spec, plan and tasks are approved.
---

# Implementation

Playbook §4 (phase 6) and §6. Work only on numbered `T-nn` tasks: `T-DOC` and `T-SYNC` have dedicated skills.

## Preconditions

- Spec approved, plan approved (there is none at level S), `tasks.md` valid, and spec and plan **already merged into
  `main`** with the design PR (`python scripts/spec_lint.py <spec> --plan <plan> --tasks <tasks> --base main`: no
  errors). If `--base` fails, the approval is not there yet: stop. Without a design PR (a project that does not use
  it), the user says so explicitly and `--base` is omitted.
- You are on a **feature branch**, not on `main`/`master`/a protected branch. Otherwise propose to create one and wait
  for confirmation.
- Run `python scripts/verify.py` **before starting**: a baseline is needed. If it is already red, tell the user: it is
  not caused by your changes and must not be hidden. The exception is the **red phase** (the last closed task is
  "expected: red"): there the red tests are the starting point of the implementation task.
- At levels M and L the closed test task carries `tests approved:` (the human read the locked tests). If it is missing,
  stop and point to `sdd-tests-from-ac`.

## Cycle (one task at a time)

1. Take the **first open `T-nn` or `T-Rnn` task** (`- [ ]`). For `T-nn` tasks read the ACs in the spec and the plan's
   interfaces for the component. `T-Rnn` tasks come from review problems (`review.md`): a finding is a hypothesis, not
   an order. **Verify it on the code first**; if it is right, fix it (with a test when it changes behaviour); if it is
   wrong, do not change the code: record the evidence (file:line) in `progress.md`, section "Disputed review findings",
   and tell the user. No agreement for show, one finding at a time.
2. If the task **writes tests from the ACs**, apply the `sdd-tests-from-ac` procedure (read it). Otherwise implement
   **only that task**: do not touch the non-scope and do no unrequested refactoring. Tests you add after the code
   (integration, end-to-end, fixes) follow "Tests written after the code" in the test conventions of
   `sdd-tests-from-ac` (search for `**/sdd-tests-from-ac/references/test-conventions.md`): the spec is the oracle, and a
   test that disagrees with code outside the task stays failing and is reported.
3. Run the task's `verify:` command, then the full `python scripts/verify.py` (`--fast` is allowed only while working,
   never as the definition of done).
4. **Red:** read the error, fix, retry. After **3 attempts** on the same task, stop: describe what you tried and ask
   for guidance (task too big or ambiguous spec).
5. **Green:** tick the task in `tasks.md`. Commit with a clear message and the trailers `Task: T-<nn>`,
   `Spec: SPEC-<id>` and `Agent: <name and version>` (`review_package.py` finds the task's commits by `Task:`). If the user has not authorized commits, propose the message and do not commit. An
   "expected: red" test task is closed with the `Test-Lock` commit of the tests only (see `sdd-tests-from-ac`). In later
   tasks **do not modify the locked test files**: if a test looks wrong, stop and ask.
6. **Task review** (playbook §4): mandatory at level L, at level M when `progress.md` says `- Task review: on` (ask the
   user at the start of the feature; never at level S). Run `python scripts/review_package.py <spec-dir> T-<nn>` and give
   **only the package path** to an independent reviewer: the `sdd-reviewer` agent in task review mode (Claude Code
   subagent, Copilot custom agent) or a new session with the same instructions. `high` and `medium` problems are fixed in
   the same task (new commits with `Task: T-<nn>`) and the package is reviewed again; after 2 rounds still failing, stop
   and ask. Record the verdict in `progress.md`, section `## Task reviews`: `- T-<nn>: pass — <reviewer>` or
   `- T-<nn>: fix needed — <problems>`. `state.py`, `sync_check.py` and `loop.py` require `pass` for every closed
   `T-nn` task when the review applies.
7. Update `progress.md` in the spec folder (create it from the template of the `sdd-loop` skill, found with a search
   for `**/sdd-loop/references/progress.md.tmpl`, if it is missing): done, learned, blockers, and the **rulings**:
   every decision you took alone under "Decides alone" of the decision rights, one per line as `- T-nn: <what> —
   <why> — <what it costs if wrong>`. The review checks them. An ambiguous requirement is not a ruling: stop and ask.
8. Move to the next task only if the user asked to proceed in sequence; otherwise stop and report.

## Stop rules

- **Decision rights** (section of `AGENTS.md`, read from `main` when the branch changed it): decide alone only what
  "Decides alone" lists, and record it as a ruling; for "Asks first", or a decision no line names, stop and ask; never
  do what "Never" lists, even when a request implies it: report what would have to change and who changes it. These
  plugin rules are "Never" whatever `AGENTS.md` says: changing spec, plan, review or `AGENTS.md`, writing an approval,
  changing a test to make it pass, pushing or merging.
- Ambiguous or missing requirement: **stop and ask**, do not assume (write the question in `progress.md`).
- Something in the non-scope needs to change: stop and ask.
- The task covers an AC named by a non-blocking open question of the spec (`spec_lint.py --tasks` warns): stop and ask;
  the answer goes into the spec with a revision before the task.
- A new or different dependency the plan does not list is needed: stop and ask (an ADR or an updated plan is needed;
  `diff_scope.py` reports a changed manifest without either as an error).
- The change exceeds the spec level (more than 3 production files at S, a sensitive area of `AGENTS.md` below L, a
  dependency at S): stop and ask; `diff_scope.py` would report it as an error.
- Never declare a task or the feature completed without having run `verify` and shown the result.

## End

When no `T-nn` task is open: report the final `verify` result and the list of commits, and move on to
`sdd-review-diff` (then `sdd-docs` and `sdd-sync`; at level S directly `sdd-sync`, with `diff_scope.py` and
`trace_check.py` green and the review in the PR). Do not declare the feature done: review, documentation and
reconciliation are still missing.
