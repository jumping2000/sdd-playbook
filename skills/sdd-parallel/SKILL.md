---
name: sdd-parallel
description: Use this skill when the user chose the parallel mode for two or more ready tasks that touch different files: one sdd-test-writer locks the tests of every task, then one sdd-multitask per task writes the code in parallel, each in its own git worktree, branch and PR; merges one at a time, keeping the other PRs up to date.
---

# Tasks in parallel

Playbook §5. Parallel agents save time only on independent tasks; on the others they produce conflicts and wasted
work. The plan decides which tasks are independent; this skill does not guess.

## Preconditions

- `python scripts/state.py` proposes `sdd-parallel` and names the tasks: open on `main`, dependencies merged, files
  pairwise disjoint in the plan. At most **3** at a time: beyond that the bottleneck is the human review of the PRs.
- Every task's interfaces with the others are fixed in the plan (`## Interfaces`). If two tasks need a name the plan
  does not fix, stop and ask: it is a plan change.
- The user chose `Parallel` in the mode question (`sdd-task`, guide: search for
  `**/sdd-start/references/interaction.md`). If the group changed since then, ask again.

## Steps

1. **One worktree per task**, from an up-to-date `main`, in a folder outside the repository (e.g. next to it):
   `git worktree add <folder>/<repo>-T-nn -b task/<spec id>-T-nn main`.
2. **Tests first, by one `sdd-test-writer`** for all the tasks of the group: give it every task ID with its worktree,
   branch and report path (`reports/tasks/<spec id>/T-nn-tests.md`). It locks the tests of each task with a
   `Test-Lock: T-nn` commit in that task's branch. One writer for the group keeps the tests consistent and costs little:
   tests are smaller than code.
3. **Code, by N `sdd-multitask` in parallel**, one per worktree, each with its task, the SHA of its `Test-Lock` commit
   and its report path (`reports/tasks/<spec id>/T-nn-code.md`), launched in the same message so that they run
   together. Handle every status as `sdd-task` step 4 says (search for `**/sdd-task/SKILL.md`), then, per task, the
   checks, PR and review of `sdd-task` steps 5, 7 and 8. Agents never merge and never launch other agents.
   - GitHub Copilot: the same custom agents if the host can delegate; otherwise the coding agent on one issue per task,
     or separate CLI sessions;
   - Codex and other agents: separate sessions, one per worktree, each doing tests then code.
4. **Merges one at a time**, in plan order: for each PR ask the merge question of `sdd-task` (options). After every
   merge, update the other open branches on the new `main` (`git rebase main` in their worktree), rerun `verify`,
   `trace_check --task` and `diff_scope --task`, and only then ask their merge. A conflict means the plan's files or
   interfaces were wrong: stop that task, report it, and propose the plan correction.
5. **Clean up** the merged worktrees: `git worktree remove <folder>/<repo>-T-nn`.

## STOP

Report the merged PRs, the ones left open with the reason, and what `python scripts/state.py` proposes next. Never
merge two PRs without rerunning the checks of the second on the new `main`.
