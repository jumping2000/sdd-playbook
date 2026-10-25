---
name: sdd-plan
description: Use this skill when an approved spec exists and the technical plan (plan.md) is needed: approach and alternatives, files involved, interfaces, test strategy mapped to the acceptance criteria, risks and rollback. It works read-only on the code.
---

# Plan

Playbook §3.4 and §4 (phase 3).

## Preconditions (check them first)

- `docs/specs/<id>/spec.md` exists, `Status: approved`, and `python scripts/spec_lint.py <spec>` passes. Otherwise stop
  and point to `sdd-spec`.
- Level M or L (playbook §2.1). A level-S spec has no plan: point to `sdd-tasks`.

## Steps

1. **Read-only and reasoning:** do not modify code. Read the spec, `AGENTS.md`, `docs/constitution.md`,
   `docs/system/<area>.md` if it exists, and the relevant code.
2. **Write** `plan.md` in the spec folder with `references/plan-template.md`:
   - at least **one discarded alternative** with the reason;
   - files to create/modify in the "Components and files" section, **one per line in the format
     `- path: what changes`** (`diff_scope.py` uses them for the review) and the callers touched; in brownfield also
     migrations and backward compatibility;
   - the test strategy table must contain **all** the ACs of the spec;
   - risks with the way to verify them; release and rollback;
   - do not introduce anything the spec does not require: if it is needed, it is a question for the user;
   - every manifest or lockfile to change (new dependencies) goes into "Components and files": `diff_scope.py` accepts
     a dependency change only if it is in the approved plan or comes with an ADR;
   - `- Based on spec:` with the value of `- Hash:` of the approved spec.
3. **Check** with `python scripts/spec_lint.py <spec> --plan <plan>`: it must pass. The warning about the plan not being
   approved is expected at this point.
4. If the plan requires a new dependency or an architecture decision, flag it as an ADR candidate (`docs/adr/`); do not
   create it without confirmation. At level L an ADR is due for every decision taken.
5. If you find that the change exceeds the spec level (more files, a sensitive area, a dependency), stop: the level is
   changed in the spec, with a new approval.

## STOP

Summarize the plan and ask for explicit approval with the approver's name. Only then fill in `Approved by / date`, write
in `- Hash:` the output of `python scripts/spec_lint.py <plan> --hash` and rerun the lint with `--plan` (the warning must
disappear). If the spec changes, the plan lapses and must be re-approved. Do not write tasks or code without this step.
Next step: `sdd-tasks`.
