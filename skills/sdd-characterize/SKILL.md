---
name: sdd-characterize
description: Use this skill in brownfield, before changing an area, to write characterization tests that pin the current behaviour (even if imperfect) and record them in the area page; it is the safety net before the spec and the code.
---

# Characterization tests

Playbook §5, step 4. **You do not modify production code** and you do not fix the defects you find: you note them.

## Preconditions

- `docs/system/map.md` exists (otherwise `sdd-map-codebase`) and the baseline is known.
- The user has indicated the area or the files they intend to change.
- Work committed for the area's files: clean `git status` on them (needed for step 5).

## Steps

1. **Identify** the behaviours of the area to preserve: read the code, its callers and the existing tests. List to the
   user what you plan to pin and what you leave out.
2. **Write the tests** that describe the **current** behaviour, even when it is odd or wrong: if a behaviour is a bug,
   the test pins it and you mark it as such in the test. Name with the `char`/`characterization` prefix (e.g.
   `test_char_...`).
3. **Run them on the unmodified code: they must pass.** If one fails you misunderstood the behaviour: fix the test, not
   the code.
4. **Run `python scripts/verify.py`**: it must stay green (or as the baseline).
5. **Prove that the tests can fail:** introduce a deliberate, minimal break at one point of the area, run the tests and
   check that they turn red, then restore with `git restore <file>` and check that `git diff` is empty on the
   production files. Show the evidence. If a test stays green, it is useless: strengthen it.
6. **Record** the tests in `docs/system/<area>.md` ("Characterization tests" section); if the page does not exist
   create it from `../sdd-sync/references/area-template.md`.

## STOP

Report tests written, behaviours pinned, defects noted and the failure proof. Ask for a spot check.
Next step: `sdd-spec` to describe only the delta.
