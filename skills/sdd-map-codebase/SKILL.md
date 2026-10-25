---
name: sdd-map-codebase
description: Use this skill at the start of work on an existing codebase (brownfield) to produce, read-only, the system map (docs/system/map.md) with real tried commands and the test baseline, before writing specs or touching code.
---

# Codebase map (brownfield)

Precondition: project initialized (`scripts/scan_repo.py` and `scripts/verify.py` exist). If they are missing, point to
`sdd-init` (if only the scripts are missing, copy them from `../sdd-init/scripts/`).

**Read-only on the code.** The only files you write are `docs/system/map.md` and, after confirmation, `AGENTS.md`.
Playbook §5, steps 1-3.

## Steps

1. **Inventory:** `python scripts/scan_repo.py`. It is a list of facts (stack, languages, folders, tests, CI, likely
   entry points), not understanding.
2. **Baseline:** run `python scripts/verify.py` and, if `STEPS` does not cover the project yet, the real build and test
   commands. Note the result **as it is**: if it is already red, it is not your fault and must be declared.
3. **Read the code** starting from the entry points and the largest modules. Fill in `docs/system/map.md` from
   `references/map-template.md`: modules and responsibilities, entry points, external dependencies, zones not to touch,
   risks and known debt.
4. **Real commands:** every command in the table was run by you, with its result. Do not write inferred commands.
5. **Spot check:** pick at least 5 statements of the map and check them in the code; list them with file and line in
   "How this map was verified". Fix the false ones.
6. **Propose** to update `AGENTS.md` with the tried commands, the zones not to touch ("Do not modify:" line used by
   `diff_scope.py`) and the sensitive areas ("Sensitive areas:"), paths in backticks. Show the difference and ask for
   confirmation.

## STOP

Present the map and the baseline result. Ask the user to spot-check it. Do not write specs.
Next step: `sdd-characterize` on the area to change, then `sdd-spec`.
