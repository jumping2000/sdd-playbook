# Interaction: choices, confirmations and merges as options

Every time the user has to choose, confirm or decide a merge, give them options to select instead of asking for free
text. Fewer messages, fewer typos, and the decision stays theirs.

## How to ask

- **Tool:** the host's question tool when it has one (Claude Code: `AskUserQuestion`); otherwise one message with
  numbered questions and lettered options, answered in one line (`1b 2a 3c`).
- **Rounds:** up to 4 questions per round, 2-4 options per question. Group the questions you can already ask; ask a
  follow-up round only for what the answers opened.
- **Options:** the recommended one first, marked `(recommended)` with its reason in one line; the others with their
  trade-off. A free answer is always possible ("Other").
- **No jargon:** the user's words, not field names. Say why the question matters when it is not obvious.
- **Never** answer a question yourself, pre-select a confirmation, or read silence as consent.

## The three decisions of a feature

| Decision | When | Options | Effect of the first one |
|---|---|---|---|
| Spec | end of `sdd-start` | `Confirm the spec`, `Change it` (they say what), `Stop here` | `- Status: approved` in the spec |
| Plan | end of `sdd-plan` | `Confirm the plan`, `Change it`, `Stop here` | spec and plan go into the design PR, then the merge question |
| Merge | every PR (design PR, then one per task) | `Merge into main`, `Change it` (they say what), `Leave it open` | you merge (see below) |

Before each question, show in a few lines what is being decided: for the spec the REQs, ACs, non-scope, anti-goals and
open questions; for the plan the approach and the task list; for a PR the covered ACs, the check results, the
reviewer's verdict, the CI status and the `SENSITIVE` line of `diff_scope.py` when present.

## Merging

The merge of a PR into `main` is the only approval the process records: git history says who merged what and when.
- **With a remote:** push the branch and open the PR (body from `pr-body.md` of `sdd-task`) with the platform's CLI
  when it is installed (GitHub: `gh pr create`; GitLab: `glab mr create`), otherwise give the user the link the push
  prints. After `Merge into main` merge with rebase and delete the branch (GitHub: `gh pr merge --rebase
  --delete-branch`; GitLab: `glab mr merge --rebase --remove-source-branch`), so the commits, `Test-Lock` included,
  stay on `main`. If `main` is protected or your identity cannot merge, give the user the link.
- **Without a remote:** after `Merge into main`, `git switch main` then `git merge --ff-only <branch>` and
  `git branch -d <branch>`. If the fast-forward fails, `main` moved: offer `Rebase the branch on main` or `Stop here`.
- Never stash, cherry-pick or force-push. Never merge without the user selecting it.

## Limit

Nothing technical stops an agent from merging by itself: the evidence of the decision is the user's selection and the
merge that follows it. Who wants a guarantee protects `main` on the platform (required review), a setting outside the
plugin.
