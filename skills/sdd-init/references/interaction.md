# Interaction: choices and gates as options

Every time the user has to choose or approve, give them options to select instead of asking for free text. Fewer
messages, fewer typos, and the decision stays theirs.

## How to ask

- **Tool:** the host's question tool when it has one (Claude Code: `AskUserQuestion`); otherwise one message with
  numbered questions and lettered options, answered in one line (`1b 2a 3c`).
- **Rounds:** up to 4 questions per round, 2-4 options per question. Group the questions you can already ask; ask a
  follow-up round only for what the answers opened.
- **Options:** the recommended one first, marked `(recommended)` with its reason in one line; the others with their
  trade-off. A free answer is always possible ("Other").
- **No jargon:** the user's words, not field names. Say why the question matters when it is not obvious.
- **Never** answer a question yourself, pre-select an approval, or read silence as consent.

## Gates (approvals and decisions)

A gate is an approval the process records with a name: spec, plan, locked tests, review decision, human diff review,
and the confirmations of `sdd-init` and `sdd-map-codebase`. Present it as one question:

| Option | Effect |
|---|---|
| `Approve as <name>` (one per name of `- Approvers:` in `AGENTS.md`) | you record the approval with `python scripts/approve.py ... --by "<name>" --commit` |
| `Approve as another person` (they type the name) | as above, with the typed name; propose adding it to `- Approvers:` |
| `Request changes` (they say what) | change the document and ask again |
| `Stop here` | nothing is recorded; report the state |

Before the question, show what is being approved in a few lines (for a spec: level with its reason, REQs, non-scope,
anti-goals, open questions). Write an approval only with `approve.py`, in the turn where the user selected it, with the
name they selected: never on your own initiative, never inside the autonomous loop.

## Git after a gate, by profile (`- Profile:` in `AGENTS.md`)

- **solo** (one person, with or without a remote): you do the git steps. Work on `feat/<spec id>`; `approve.py --commit`
  commits the approval with a standard message. After the design gate (spec, and plan and tasks at levels M and L) and
  after `sdd-sync`, move `main` forward with `git fetch . HEAD:main` (fast-forward only: it fails if `main` moved; then
  stop and offer the options "rebase the branch on main" or "stop here"). At the end switch to `main`
  (`git switch main`) and delete the branch (`git branch -d feat/<spec id>`). No stash, no cherry-pick, no merge
  commits, no push unless the user selects it.
- **team:** the approval is the merge of the PR into protected `main` (playbook §1.2). Offer the options
  `Open the PR` (with `gh pr create` or the platform's CLI, when available), `Merge now, I approve as <name>` (only if
  your identity has the permission: the platform still enforces reviews and CI), `I will merge it myself` (give the
  link or the command).

## Limit

In the solo profile nothing technical stops an agent from running `approve.py` by itself: the evidence of the approval
is the user's selection in the host's question tool and the commit that follows it. In the team profile the merge on
protected `main` remains the gate the agent cannot pass.
