---
name: sdd-review-diff
description: Use this skill once implementation is done (T-nn tasks completed) to reread the diff against spec, plan and non-scope with fresh context, trying to refute the result; it produces review.md with an outcome and the human decision.
---

# Diff review against the spec

Playbook §4 (phase 7), §5 (step 8) and §3.8. A context **independent** of the implementer is needed.

## Preconditions

- No open `T-nn` task in `tasks.md` and `python scripts/verify.py` green (run it, show the result).
- You are on a feature branch with the work committed.
- Level M or L (playbook §2.1). At level S step 1 is enough: report the result to the user for the PR, without
  `review.md` (unless the user asks for it).

## Steps

1. **Deterministic checks:**
   - `python scripts/diff_scope.py <spec-dir>`: forbidden zones, locked tests (`Test-Lock`) changed after locking,
     voided test approvals, underestimated level and dependencies without a decision (errors), out-of-plan files
     (warning);
   - `python scripts/trace_check.py <spec> --junit <report>`: every AC has a test, executed and passed in the JUnit
     report written by `verify` (without a report it checks only the citations: say so in the report);
   - `python scripts/secrets_check.py`: no secrets in the branch files.
2. **Independent review.**
   - Claude Code: delegate to the `sdd-reviewer` subagent, passing in the message the spec folder, the full diff
     (`git diff <merge-base>` plus the untracked files) and the output of `verify` and of step 1: the subagent has no
     Bash, so it cannot run commands or modify files. For errors less correlated with the implementer's, the user can
     set a different model than the session's in the agent frontmatter (`model:`).
   - GitHub Copilot: the same agent as a Copilot custom agent (`.github/agents/sdd-reviewer.agent.md`, copied by
     `sdd-init`), with only read and search tools.
   - Other agents (Codex included): open a **new session** and give only spec, plan, step 1 output and the diff; do not
     bring the implementation conversation. Use the same instructions as the plugin's `agents/sdd-reviewer.md`.
   The reviewer tries to **refute** the result, not to confirm it.
3. **Write** `review.md` in the spec folder from `references/review-template.md`: proposed outcome (`compliant`,
   `compliant with reservations`, `non-compliant`), problems with file and line, refutation attempts.
4. If the outcome is `non-compliant`: turn every `high` or `medium` problem into a task in `tasks.md`, section
   `## Fixes from review`, with continuing numbering (`- [ ] T-R01 <problem> — verify: \`<command>\``, `covers:` if it
   touches an AC). `spec_lint.py --tasks` checks them, `sdd-implement` and the loop execute them, `state.py` asks to
   repeat the review when they are all closed. The repeated review updates `review.md`.

## STOP

Present the report. **The decision belongs to the user:** ask for their name and confirmation and fill in "Decided by".
Without this decision `sync_check.py` will not pass. **Level L:** the user also reads the diff (the files of the
sensitive areas first); fill in `- Human diff review:` only when they confirm they did it, with name and date. Do not
modify code in this skill.
Next step if the outcome is accepted: `sdd-docs`, then `sdd-sync`.
