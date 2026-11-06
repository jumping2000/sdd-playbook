---
name: sdd-next
description: Use this skill when the user does not know where to restart or asks "where are we", "what is the next step" in the spec-driven development cycle; it reads the repository state and points to the next skill, without changing anything.
---

# Next step

Read-only: this skill **does not modify files** and does not start the next step.

1. Run `python scripts/state.py` from the repository root. If `scripts/state.py` does not exist, the project is not
   initialized: point to `sdd-start` and stop.
2. Report in a few lines: infrastructure, existing code without a map, for each spec its status, whether spec and plan
   are on `main`, the tasks merged out of the total, and the `NEXT` line with its reason. When it names several tasks,
   they can run in parallel (`sdd-parallel`).
3. If it reports `choose`, ask the user which spec to work on (options) and rerun
   `python scripts/state.py --spec <id>`; do not choose yourself.
4. Open bugs (`OPEN BUGS`) are reported: the priority between bugs and features belongs to the user (`sdd-bugfix`).
5. The flow (playbook §3): `sdd-start` (spec) → `sdd-plan` (plan with tasks, design PR) → `sdd-task` per task, or
   `sdd-parallel` for independent ones → the last task closes the feature. Existing code: `sdd-map` first.
6. Ask with options whether to proceed with the indicated skill (guide: search for
   `**/sdd-start/references/interaction.md`). Do not invoke it by yourself.

Do not infer the state from the conversation: only the script output counts.
