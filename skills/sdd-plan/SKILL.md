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
   - **Interfaces:** for every component the tasks build, what it produces (exact names and signatures) and what it
     consumes; a task, or a loop iteration, sees only its own part and learns the neighbours' names from here;
   - **Review focus:** the input classes or failure modes the spec implies but no AC exercises (empty input, very large
     input, concurrency, encoding, permissions...), at most 5, most likely first, each with the test that pins it and
     where. A spec's silence on an input is not permission to break on it. Write `- none` only after checking;
   - **Diagrams:** the five Mermaid diagrams of the change (flowchart, sequence, state, class, ER) with the names of
     "Interfaces", following `references/diagrams.md`; a diagram that does not apply becomes `- n/a: <reason>`, never
     the flowchart;
   - risks with the way to verify them; release and rollback;
   - do not introduce anything the spec does not require: if it is needed, it is a question for the user;
   - every manifest or lockfile to change (new dependencies) goes into "Components and files": `diff_scope.py` accepts
     a dependency change only if it is in the approved plan or comes with an ADR;
   - `- Based on spec:` with the value of `- Hash:` of the approved spec.
3. **Self-review** with the spec in front of you, and fix inline:
   - coverage: every REQ and AC has a place in the plan;
   - consistency: the same component, function and field names in every section, diagrams included;
   - review focus: filled in, each case with a test;
   - proportion: the plan records decisions, it does not transcribe the code. A plan longer than the code it describes
     has written the code instead; a line that decides nothing ("handle errors", "TBD") is a gap.
4. **Check** with `python scripts/spec_lint.py <spec> --plan <plan>`: it must pass. The warning about the plan not being
   approved is expected at this point.
5. If the plan requires a new dependency or an architecture decision, flag it as an ADR candidate (`docs/adr/`); do not
   create it without confirmation. At level L an ADR is due for every decision taken.
6. If you find that the change exceeds the spec level (more files, a sensitive area, a dependency), stop: the level is
   changed in the spec, with a new approval.

## STOP

Summarize the plan in a few lines and ask for the approval as a gate with options (guide: search for
`**/sdd-init/references/interaction.md`). Only after the user selects an approval, record it with
`python scripts/approve.py plan <plan> --by "<selected name>" --commit` (name, date, `Based on spec`, hash, lint
checked). If the spec changes, the plan lapses and must be re-approved. Do not write tasks or code without this step.
Next step: `sdd-tasks`.
