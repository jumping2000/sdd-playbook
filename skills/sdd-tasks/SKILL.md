---
name: sdd-tasks
description: Use this skill when spec and plan are approved and the work must be broken down into tasks.md: small steps, each with a verification command and the acceptance criteria it covers, tests before code, plus T-DOC and T-SYNC.
---

# Tasks

Playbook §3.5 and §4 (phase 4).

## Preconditions

- Spec `approved` and plan with `Approved by / date` filled in (check with
  `python scripts/spec_lint.py <spec> --plan <plan>`: no errors and no warning about the plan). Otherwise stop and point
  to the missing skill.
- **Level S** (playbook §2.1): no plan. `python scripts/spec_lint.py <spec>` without errors is enough, with few tasks
  ("expected: red" test, implementation, `T-SYNC`; `T-DOC` only if needed) and no `- Based on plan:`.

## Steps

1. **Write** `tasks.md` in the spec folder; the format is in `references/tasks-template.md`:

   ```
   - [ ] T-nn <small action> — verify: `<command>` — covers: AC-nnn, AC-mmm
   ```

2. Rules:
   - **One task = one unit that a command can declare passed or failed.** If you cannot write the verification
     command, the task is too vague: split it or clarify.
   - **Tests before code:** for each group of ACs, a task that writes the tests (run with `sdd-tests-from-ac`;
     verification: the test fails for the right reason, marked "expected: red"), then the task that implements. Use
     "expected: red" **only** on tasks that write tests: the `Stop` hook and `loop.py` read it to recognize the red
     phase.
   - No `<...>` placeholders in `T-nn` tasks: `spec_lint.py --tasks` reports them as errors.
   - At the top of the file `- Based on plan:` with the value of `- Hash:` of the approved plan: if the plan changes,
     `spec_lint.py <spec> --plan <plan> --tasks <tasks>` and `state.py` ask to review the tasks.
   - `T-Rnn` tasks are not written here: `sdd-review-diff` adds them after a non-compliant review.
   - Every AC is covered by at least one task; no task touches what is in the non-scope.
   - The tests of the plan's **Review focus** go into the test task of the component that owns the case (they cite no
     AC: name them after the case).
   - Always include `T-DOC` (documentation, executed examples: `sdd-docs`; optional at level S) and `T-SYNC`
     (reconciliation of spec and `docs/system/`, then `Status: implemented`: `sdd-sync`). They have no `covers:`: they
     run after the review.
   - If the spec is small, few tasks: do not inflate the plan.
3. **Check** with `python scripts/spec_lint.py <spec> --tasks <tasks>`: it must pass.
4. After the user's go-ahead, spec, plan and tasks go into the **design PR** (playbook §1.2): commit them on a dedicated
   branch. If the agent has no push rights, the user pushes it; in any case only the user merges it.

## STOP

Show the list and ask the user for a quick check. Do not start the implementation without their go-ahead.
Next step: `sdd-implement` (or `sdd-loop` if the tasks are many and independent).
