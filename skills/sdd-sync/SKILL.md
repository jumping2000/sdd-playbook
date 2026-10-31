---
name: sdd-sync
description: Use this skill to carry out the T-SYNC task at the end of a feature: reconcile the spec and the area page docs/system/<area>.md with the real behaviour, set the spec status to implemented and run sync_check.py; it proposes the lessons for AGENTS.md and ADRs.
---

# Spec ↔ code reconciliation (T-SYNC)

Playbook §3.7 and §4 (phase 9). A spec not reconciled with the code stops being the source of truth.

## Preconditions

- Valid `review.md`, with "Decided by" filled in by the user (level L: also "Human diff review"). Level S: no
  `review.md`, but `python scripts/diff_scope.py <spec-dir>` and `python scripts/trace_check.py <spec>` must pass.
- `T-DOC` completed. `T-SYNC` is the last open task.

## Steps

1. **Read** the spec, the final code and, if it exists, `docs/system/<area>.md`.
2. **Compare the spec with the real behaviour.** Every gap is either a code defect (new bug: `sdd-bugfix`) or a
   requirement change (update the spec **with the user's approval**, then update `Approved by / date` and `- Hash:`
   with `python scripts/spec_lint.py <spec> --hash`; the change ends up in the implementation PR and whoever merges it
   approves it). Never erase a discrepancy silently.
3. **Area page** (optional at level S): create or update `docs/system/<area>.md` from `references/area-template.md`:
   current behaviour (only what is true in the code), the five Mermaid diagrams **redrawn from the final code** (the
   plan's diagrams are the design, the area page shows what was built; guide: search for
   `**/sdd-plan/references/diagrams.md`), constraints, characterization tests, references. Add the spec to "Linked
   specs" and set "Last aligned" to today's date. `python scripts/docs_check.py` checks the diagram section.
4. **Close:** set `Status: implemented` in the spec and tick `T-SYNC` in `tasks.md`. Non-blocking open questions still
   in the spec (`spec_lint.py` warns) are reported to the user: answered with a revision, or moved to a new spec or to
   the issue tracker; never removed silently.
5. **Check:** `python scripts/sync_check.py <spec-dir> --junit <report>` (JUnit report from `verify`, mandatory at level
   L). Fix until it passes; if an error depends on a user decision, report it without forcing.
6. **Lessons:** propose, without applying them, the changes for `AGENTS.md` and ADRs that emerged from the work.
7. Commit with the `Spec:` and `Agent:` trailers.

## STOP

Report the `sync_check.py` result, the gaps found and the proposed lessons. Then the PR belongs to the user.
