---
name: sdd-next
description: Use this skill when the user does not know where to restart or asks "where are we", "what is the next step" in the spec-driven development cycle; it reads the repository state and points to the next phase and skill, without changing anything.
---

# Next step

Read-only: this skill **does not modify files** and does not start the next phase.

1. Run `python scripts/state.py` from the repository root.
   - If `scripts/state.py` does not exist, the project is not initialized: point to `sdd-init` and stop.
2. Report to the user, in a few lines:
   - infrastructure present or missing (AGENTS.md, verify, CI) and whether there is existing code without a map;
   - for each spec: level, status, approvals, task progress, review outcome and its step (`-> skill`);
   - the `NEXT` line with its reason.
   - With several active specs `NEXT` refers to the spec of the current branch (the folder name appears in the branch
     name). If it reports `choose`, ask the user which spec to work on and rerun `python scripts/state.py --spec <id>`;
     do not choose yourself.
3. If **unverified bugs** appear (`UNVERIFIED BUGS`), report them: the priority between bugs and features belongs to
   the user, not the agent. The skill for bugs is `sdd-bugfix`.
4. The phases follow the playbook: init → (map-codebase, characterize in brownfield) → spec → plan → tasks →
   implement (or loop) → review-diff → docs → sync. The spec level (playbook §2.1) decides which ones: S skips plan and
   `review.md`, L asks for the human reading of the diff. A phase is skipped by lowering the level in the spec, with a
   new approval: never in the conversation.
5. Ask whether to proceed with the indicated skill. Do not invoke it by yourself.

Do not infer the state from the conversation: only the script output counts.
