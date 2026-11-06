---
name: sdd-parallel
description: Use this skill when two or more tasks of a merged plan are ready at the same time and touch different files: it runs them with several agents in parallel, each in its own git worktree and branch with its own PR, then asks the merges one at a time and keeps the other PRs up to date.
---

# Tasks in parallel

Playbook §5. Parallel agents save time only on independent tasks; on the others they produce conflicts and wasted
work. The plan decides which tasks are independent; this skill does not guess.

## Preconditions

- `python scripts/state.py` proposes `sdd-parallel` and names the tasks: open on `main`, dependencies merged, files
  pairwise disjoint in the plan. At most **3** at a time: beyond that the bottleneck is the human review of the PRs.
- Every task's interfaces with the others are fixed in the plan (`## Interfaces`). If two tasks need a name the plan
  does not fix, stop and ask: it is a plan change.
- Ask the user to confirm the parallel run with options (`Run them in parallel`, `One at a time`, `Stop here`;
  guide: search for `**/sdd-start/references/interaction.md`).

## Steps

1. **One worktree per task**, from an up-to-date `main`, in a folder outside the repository (e.g. next to it):
   `git worktree add <folder>/<repo>-T-nn -b task/<spec id>-T-nn main`.
2. **One agent per worktree**, each following the `sdd-task` skill from step 2 to step 8 (tests locked, code, verify,
   documentation, PR, review), with only that task in its instructions:
   - Claude Code: subagents with worktree isolation, launched in the same message so that they run together;
   - GitHub Copilot: the coding agent on one issue per task, or separate CLI sessions;
   - Codex and other agents: separate sessions, one per worktree.
   Each agent reports its PR, the check results and the reviewer's verdict. It does not merge.
3. **Merges one at a time**, in plan order: for each PR ask the merge question of `sdd-task` (options). After every
   merge, update the other open branches on the new `main` (`git rebase main` in their worktree), rerun `verify`,
   `trace_check --task` and `diff_scope --task`, and only then ask their merge. A conflict means the plan's files or
   interfaces were wrong: stop that task, report it, and propose the plan correction.
4. **Clean up** the merged worktrees: `git worktree remove <folder>/<repo>-T-nn`.

## STOP

Report the merged PRs, the ones left open with the reason, and what `python scripts/state.py` proposes next. Never
merge two PRs without rerunning the checks of the second on the new `main`.
