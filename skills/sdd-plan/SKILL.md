---
name: sdd-plan
description: Use this skill when a spec is confirmed and the technical plan is needed: approach and discarded alternative, interfaces, the flowchart of the feature and 3 to 8 vertical tasks with their acceptance criteria, files, dependencies and verify command. It works read-only on the code and ends with the design PR.
---

# Plan with vertical tasks

Playbook §2 and §4. Read-only on the code: the only files you write are `plan.md` and, after the decision, the
design PR.

## Preconditions

`docs/specs/<id>/spec.md` exists with `Status: approved` and `python scripts/spec_lint.py <spec>` passes. Otherwise
point to `sdd-start`.

## Steps

1. **Read** the spec, `AGENTS.md`, `docs/constitution.md`, the area page `docs/system/<area>.md` if it exists, and the
   code involved.
2. **Write** `docs/specs/<id>/plan.md` from `references/plan-template.md`, on the spec's branch:
   - **Approach:** the chosen approach in a few lines and at least one discarded alternative with the reason;
   - **Interfaces:** for every component the tasks build, what it produces (exact names and signatures) and what it
     consumes: a task, or a parallel agent, sees only its part and learns its neighbours' names from here;
   - **Flowchart** (mandatory): the main flow of the feature with its decisions and error paths, in Mermaid
     (`references/diagrams.md`). Other diagrams only when they help the tasks: the complete set of five belongs to the
     final documentation (area page), drawn from the real code;
   - **Tasks:** 3 to 8 **vertical** tasks. Each delivers a behaviour someone can observe end to end (not a layer: no
     "models", then "API", then "UI"), covers its ACs, and fits one PR readable in 15-30 minutes. One line each:
     `- [ ] T-nn <goal> — covers: AC-nnn — files: `path`, `path` — depends: T-nn | none — verify: `<command>``.
     "files" lists the main files the task creates or changes, tests included: tasks with disjoint files and no
     dependency between them can run in parallel (`sdd-parallel`). More than 8 tasks means two features: propose the
     split;
   - **Review focus:** the input classes or failure modes the spec implies but no AC exercises (empty or huge input,
     encoding, concurrency, permissions), at most 5, each with the task whose tests pin it; `- none` only after
     checking;
   - **Risks:** what could go wrong and how it is checked; rollback if it matters;
   - do not introduce anything the spec does not require: if it is needed, it is a question for the user.
3. **Self-review** with the spec in front of you: every AC in a task, the same names in every section, no task that is
   a horizontal layer, no line that decides nothing ("handle errors", "TBD").
4. **Check** with `python scripts/spec_lint.py <spec> --plan <plan>` until there are no errors.
5. A new dependency or an architecture decision is an ADR candidate (`docs/adr/`): propose it, create it only after
   confirmation.

## STOP

Summarize the approach and the task list (with what can run in parallel) and ask the plan decision with options
(`Confirm the plan`, `Change it`, `Stop here`; guide: search for `**/sdd-start/references/interaction.md`). On
`Confirm the plan`, commit the plan on the spec's branch, open the **design PR** (spec and plan together) and ask the
merge question. The merge is the approval of both: do not start any task before it.
Next step: `sdd-task` (or `sdd-parallel` when `python scripts/state.py` proposes it).
