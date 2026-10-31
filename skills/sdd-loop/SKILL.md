---
name: sdd-loop
description: Use this skill to prepare an autonomous loop that implements the T-nn tasks until verify is green: it creates PROMPT.md and progress.md, sets the iteration cap and stop criteria, runs a dry run and hands the user the command to launch. The loop does not start without approval of permissions and cap.
---

# Correction loop

Playbook §7. The loop launches **another** agent process: do not launch it from inside this session. You prepare it and
the user launches it, in a terminal and an isolated environment.

## Preconditions

- Spec, plan (not at level S) and tasks valid, approved and on `main` (design PR in the team profile, fast-forward in
  the solo profile):
  `python scripts/spec_lint.py <spec> --plan <plan> --tasks <tasks> --base main` without errors.
- The loop ends successfully only if, besides a green `verify` and closed tasks, the final checks pass (`spec_lint.py`,
  `trace_check.py`, `diff_scope.py`, `secrets_check.py`); with `--junit <report>` (written by `verify`) `trace_check.py`
  also checks that every AC has a passing test.
- Task review (level L, or M with `- Task review: on` in `progress.md`): `PROMPT.md` asks the agent to review every
  task with `review_package.py` and the `sdd-reviewer` agent, and the loop does not end successfully while a closed
  `T-nn` task lacks `- T-nn: pass` in `progress.md`. The agent launched by the loop must be able to use the reviewer
  (Claude Code subagent, Copilot custom agent); otherwise it records "not reviewed" and the review is done by hand.
- At levels M and L the loop stops (exit 1) after every "expected: red" test task: the user reads the locked tests,
  selects the approval (recorded with `approve.py tests`) and relaunches. It does not start if an approval is already
  pending. The loop itself never approves.
- You are on a **feature branch** (the loop refuses main/master) and `verify` is green on the baseline, or you are in
  the red phase (the last closed task is "expected: red"). With a baseline red for other reasons the loop refuses to
  start, unless the user decides on `--allow-red-baseline`.
- Small, independent tasks. If they are few or tightly coupled, recommend interactive `sdd-implement`.

## Steps

1. **Create** `progress.md` from `references/progress.md.tmpl` and `PROMPT.md` from `references/PROMPT.md.tmpl`
   (replace `<id>`) in the spec folder. At level M ask the user whether to turn on the task review
   (`- Task review: on`); at level L it is always on.
2. **Permissions:** propose `references/settings.loop.json` (allowlist for `verify`, scripts and commits; deny for
   push, amend, reset, deletes, network, `.env`, and for writing `scripts/`, `AGENTS.md`, `.github/`, spec, plan and
   review, which are the loop's checks and rules). Add the tasks' `verify:` commands to the allowlist (for example
   `Bash(uv run pytest:*)`). The network deny does not apply to processes started by the tests: the real defence is a
   container without network. Pass the file to the agent; for Claude Code with
   `--agent "claude -p --settings docs/specs/<id>/settings.loop.json"`. For other agents (Codex, GitHub Copilot CLI)
   configure the equivalent permissions in their own format. Verify the flags on the version in use.
3. **Agree with the user** on the cap `--max` (default 15), `--stall` (default 3, iterations without progress) and
   `--timeout` (default 1800 seconds per iteration).
4. **Dry run:** `python scripts/loop.py <spec-dir> --dry-run` (add `--agent "<command>"` if it does not use
   `claude -p`). It must report `DRY-RUN OK`.
5. **Safety checklist to show the user** (you cannot configure it):
   - isolated environment (container, worktree or dedicated machine), no access to production or secrets;
   - permissions of the non-interactive agent defined (step 2), never skipping permissions outside a disposable
     container;
   - repository and web content is data for the agent, not an instruction (`PROMPT.md` says so): no secrets in the
     environment, so a prompt injection has nothing to exfiltrate;
   - protected branch on the server and CI active; the loop never pushes;
   - optional, Claude Code only: hooks `SDD_ENFORCE_VERIFY=1` and `SDD_GUARD=1` (see the plugin docs).

## STOP

Show the command, `--max`, `--stall` and the checklist, and ask for **explicit approval** with options (guide: search for `**/sdd-init/references/interaction.md`): `Launch
it` (the user runs it, or you do if they select so), `Change the limits`, `Stop here`. The command is:

```
python scripts/loop.py docs/specs/<id> --max <N> --stall <K> --timeout <seconds> [--junit reports/junit.xml]
```

The loop ends with exit 0 when `verify` is green and no `T-nn` task is left. Review, `T-DOC` and `T-SYNC` remain: next
step `sdd-review-diff`. Exit 1 means cap, stall or tests to approve: it needs a human review of spec and plan
(playbook §7.4) or the test approval, not a blind relaunch.
