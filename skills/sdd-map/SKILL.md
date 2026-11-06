---
name: sdd-map
description: Use this skill at the start of work on an existing codebase (brownfield): it produces, read-only, the system map (docs/system/map.md) with its diagrams, the real tried commands and the test baseline, then pins the current behaviour of the area to change with characterization tests that can fail, before any spec or code.
---

# Map and characterize an existing codebase

Playbook §6. Precondition: the project is initialized (`scripts/scan_repo.py` and `scripts/verify.py` exist);
otherwise point to `sdd-start`. Choices and confirmations as options (guide: search for
`**/sdd-start/references/interaction.md`).

**Read-only on the production code.** You write `docs/system/map.md`, characterization tests, the area page and, after
confirmation, `AGENTS.md`.

## Part 1: the map (once per codebase)

1. **Inventory:** `python scripts/scan_repo.py`. It is a list of facts, not understanding.
2. **Baseline:** `python scripts/verify.py` and the real build and test commands. Note the result **as it is**: a red
   baseline is not your fault and must be declared.
3. **Read the code** from the entry points and the largest modules, and fill in `docs/system/map.md` from
   `references/map-template.md`: modules and responsibilities, the five Mermaid diagrams of the existing system
   (guide: search for `**/sdd-plan/references/diagrams.md`; `- n/a: <reason>` where nothing applies), entry points,
   external dependencies, zones not to touch, risks and known debt. `python scripts/docs_check.py docs/system` must
   pass.
4. **Real commands:** every command in the table was run by you, with its result.
5. **Spot check:** check at least 5 statements of the map in the code and list them with file and line.
6. **Propose** for `AGENTS.md` the tried commands, the `- Do not modify:` zones and the `- Sensitive areas:`, paths in
   backticks; show the difference and ask (options).

Ask the user to spot-check the map (options: `Map is right`, `Correct it`, `Stop here`).

## Part 2: characterization tests (per area, before changing it)

Only where the user is about to work: there is no need to document everything upfront.
1. **Identify** the behaviours of the area to preserve (code, callers, existing tests) and list what you plan to pin.
2. **Write tests of the current behaviour**, even when it is odd or wrong: a behaviour that looks like a bug is pinned
   and marked as such in the test, not fixed. Prefix `char` (`test_char_...`).
3. **They must pass on the unmodified code**: if one fails, fix the test, not the code. `verify` stays as the baseline.
4. **Prove they can fail:** a deliberate, minimal break in the area, the tests turn red, then `git restore <file>` and
   an empty `git diff` on the production files. A test that stays green is useless: strengthen it.
5. **Record** them in the area page `docs/system/<area>.md` ("Characterization tests"), created if needed from the area
   template of `sdd-task` (search for `**/sdd-task/references/area-template.md`).
6. Commit on a branch and ask the merge question like any PR (map and characterization tests change no behaviour).

## STOP

Report the baseline, the map, the tests and the failure proof, and the defects noted (they become bugs, not fixes).
Next step: `sdd-start` with a spec that describes **only the change**.
