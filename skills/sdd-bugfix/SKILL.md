---
name: sdd-bugfix
description: Use this skill when there is a defect to fix: reproduction, expected and unchanged behaviour confirmed by the user, red test, diagnosis, minimal fix and non-regression, in one branch and one PR with the merge question. Do not use it for new features.
---

# Bug fixing

Playbook §7. A bug is not a miniature feature: **reproduce, pin with a red test, diagnose, fix the minimum, check that
nothing else changed.** One bug, one branch (`fix/BUG-<nnn>`), one PR. Choices as options (guide: search for
`**/sdd-start/references/interaction.md`).

If the cause is obvious and the fix is one line: red test, fix, `verify`, PR; no bug file.

## Steps

1. **Reproduction.** Create `docs/bugs/BUG-<nnn>-<slug>.md` from `references/bugfix-template.md` (`- Status: open`) and
   reproduce with minimal steps. **If you cannot, stop and ask for data**: no fix by intuition.
2. **Definition.** Actual and expected behaviour (with the REQ or AC; if the spec did not cover it, propose a new AC)
   and the **behaviour that must NOT change**, the non-regression net. **STOP:** the user confirms them with options
   (`Confirm`, `Correct it`, `Stop here`). If the spec was silent or wrong, say so: it is also a spec bug.
3. **Red test** that fails for the bug's reason; commit it alone with the trailer `Test-Lock: BUG-<nnn>`.
4. **Diagnosis** (`- Status: diagnosed`), read-only until the cause is clear, with the techniques of
   `references/debugging.md`: trace the bad value back to its source, one hypothesis and one experiment at a time,
   bisect history or input, make flaky failures reproducible. Write the verified root cause and the refuted hypotheses.
5. **Minimal fix** (`- Status: fixed`). Only what is needed, no refactoring; add the test on the unchanged behaviour.
6. **Non-regression:** full `python scripts/verify.py` green and the bug's test green; if the bug revealed a missing
   requirement, update spec, ACs and the area page in the same PR.
7. **PR** with the bug file, the review of `sdd-reviewer` (as in `sdd-task`, step 8) and the merge question of
   `sdd-task`. After the merge: `- Status: verified` and the "Closure" items ticked.

## If the diagnosis spans many areas

Do the diagnosis in a separate session (or a subagent) that delivers only the bug file; the fix starts in another
session with that file as its only context.

## Rules

- Do not fix other defects you come across: record them as new bugs.
- Do not weaken existing tests to make the fix pass.
- After 3 failed fix attempts, stop and report what you tried: the cause is probably in the design
  (`references/debugging.md`, section 5).
