---
name: sdd-bugfix
description: Use this skill when there is a defect to fix: it follows reproduction, definition of the expected and unchanged behaviour, red test, diagnosis, minimal fix and non-regression, with docs/bugs/BUG-nnn.md checked by bug_lint.py. Do not use it for new features.
---

# Bug fixing

Playbook §6.1. A bug is not a miniature feature. One bug, one branch, one fix commit.
If the cause is obvious and the diff is one line, that is enough: red test, fix, `verify` (no bug file).

## Steps (update `Status` at every transition and run `python scripts/bug_lint.py <file>`)

1. **Reproduction** (`open`). Create `docs/bugs/BUG-<nnn>-<slug>.md` from `references/bugfix-template.md`. Reproduce
   with minimal steps. **If you cannot, stop and ask for data**: no fix by intuition.
2. **Definition.** Fill in actual and expected behaviour (with reference to REQ/AC; if the spec did not cover it,
   propose a new AC) and **"Behaviour that must NOT change"**, which is the non-regression net. **STOP:** the user
   confirms expected and unchanged behaviour. If the spec was silent or wrong, say so: it is also a spec bug.
3. **Red test.** Write a test that fails for the bug's reason and give its path in "Fix and tests". Run it and show the
   failure.
4. **Diagnosis** (`diagnosed`). Read-only until the cause is clear, with the techniques of `references/debugging.md`:
   trace the bad value back to its source, one hypothesis and one experiment at a time, bisect history, input or test
   suite, make flaky failures reproducible. Write the verified root cause, not a hypothesis, and the refuted hypotheses.
5. **Minimal fix** (`fixed`). Only what is needed. No refactoring in the same commit. Add the test on the unchanged
   behaviour and give its path.
6. **Non-regression:** full `python scripts/verify.py` green and the bug's test green.
7. **Closure** (`verified`). If the bug revealed a missing requirement, update spec/ACs and `docs/system/<area>.md`.
   Tick the "Closure" items, record the lesson in `AGENTS.md`/ADR (proposed to the user).
   Commit: message with `Bug: BUG-<nnn>` and `Agent: <name and version>`.

## If the diagnosis spans many areas

Do the diagnosis in a separate session (or with a subagent) that delivers only the bug file; the fix starts in another
session with that file as its only context.

## Rules

- Do not fix other defects you come across: record them as new bugs.
- Do not weaken existing tests to make the fix pass.
- After 3 failed fix attempts, stop and report what you tried: the cause is probably in the design
  (`references/debugging.md`, section 5).
