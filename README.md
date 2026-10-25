# sdlc-playbook (version 0.12.0)

*Versione italiana: [README_IT.md](README_IT.md)*

> **Status: in design.** The plugin has not yet been used on a real project: skills, hooks and loop are tested only with
> automated tests and fake agents. Formats and contracts may still change without compatibility.

A plugin for Claude Code and Codex that guides the developer through the whole software lifecycle described in the
[playbook](docs/playbook-ai-software-lifecycle.md): spec, plan, tasks, tests, implementation, review, documentation,
reconciliation, bug fixing and autonomous loop, with explicit human gates and deterministic checks.

**Core idea:** the instructions to the agent (skills) say *what to do and where to stop*; the scripts check *that it was
really done*. A check that runs is worth more than a prose rule.

**Start here:** [Quick guide](docs/quick-guide.md) — how to use it on a new or an existing project.

## Goal

Make software built with a coding agent **as trustworthy as software built by a disciplined team**, without asking the
developer to reread every line. In practice the plugin aims to ensure that:

1. the agent builds **what was decided**, written in an approved spec, and not what it guessed;
2. "done" means **verified by a command** (tests, lint, types, traceability), not "looks done";
3. the tests that define "done" are **written from the requirements and approved by a human** before the code;
4. the agent **does not touch what it must not touch**, especially in existing code;
5. the human decides at the **few points that matter**, with effort proportional to the risk of the change;
6. specs and documentation **stay aligned** with the real behaviour after every feature;
7. all of this works the same in **Claude Code and Codex**, on **native Windows and Linux**, and remains verifiable in CI
   even without the plugin.

## Rationale: why this set of skills

Coding agents fail in recurring ways. Each skill and script exists to counter one of them:

| Typical failure of a coding agent | Answer in the plugin | Where |
|---|---|---|
| It guesses requirements and fills gaps with assumptions | Spec with requirements, acceptance criteria and explicit non-scope; open questions asked, not answered by the agent; assumptions marked | `sdlc-spec`, `spec_lint.py` |
| It declares "done" without evidence | One verification command as the definition of "done"; the `Stop` hook blocks a red stop; the loop ends only on objective checks | `verify.py`, `Stop` hook, `loop.py` |
| It writes tests that confirm its own bugs | Tests from the ACs, red for the right reason, locked by a `Test-Lock` commit and approved by a human; traceability AC → executed test | `sdlc-tests-from-ac`, `trace_check.py --junit`, `diff_scope.py` |
| It changes or "improves" things outside the scope | Approved plan with the files to touch; forbidden zones and sensitive areas in `AGENTS.md`; diff checked against plan and level | `sdlc-plan`, `diff_scope.py` |
| It breaks existing behaviour in a legacy codebase | Map and baseline first, characterization tests that can fail, spec of the delta only | `sdlc-map-codebase`, `sdlc-characterize` |
| It approves its own work (approvals are just text) | Hash of the approved content; the real approval is a merge into protected `main` by a separate identity; process checks in CI on the PR | `spec_lint.py --base`, CI template, `CODEOWNERS` |
| Same heavy process for one line and for a migration | Levels S, M, L declared in the spec, part of its hash, checked against the real diff | playbook §2.1, `diff_scope.py` |
| Review by the same session that wrote the code | Fresh-context reviewer, read-only by construction, that tries to refute; the human decides | `sdlc-review-diff`, `sdlc-reviewer` |
| Specs that rot after delivery | Closing task that reconciles spec, area page and code | `sdlc-sync`, `sync_check.py` |
| Bugs fixed "by intuition", breaking something else | Reproduction, behaviour that must NOT change, red test, minimal fix | `sdlc-bugfix`, `bug_lint.py` |
| Long autonomous runs that drift, stall or leak | Outer loop with cap, stall detection, timeout, pause for test approval, example permissions, isolation | `sdlc-loop`, `loop.py`, `settings.loop.json` |
| Secrets and unreviewed dependencies slipping in | Secret scan in `verify`; dependencies only in the approved plan or with an ADR | `secrets_check.py`, `diff_scope.py` |
| Losing track of where the work is | One state machine read from files, not from the chat | `sdlc-next`, `state.py` |

**Design choices behind it**
- **Skills for the process, scripts for the checks.** Skills are short instructions with a STOP at every approval point;
  scripts are deterministic, standard-library Python, copied into the project so that CI and VS Code use them without
  the plugin.
- **The human approves, the platform enforces.** Every text field can be written by the agent; a merge into a protected
  branch, done by a separate identity, cannot. That is why the approval is the merge of the design PR, and why the CI
  template runs the process checks on PRs.
- **Proportional, not uniform.** Levels S/M/L remove ceremony from small changes and add attention to risky ones.
- **State in files.** Specs, plans, tasks and reviews are versioned files; the chat is not a source of truth.
- **One content, two agents, two operating systems.** The Agent Skills format is shared by Claude Code and Codex; the
  scripts avoid shell commands so that native Windows works like Linux.

**What it deliberately does not do:** approve on behalf of the human, launch the loop from inside a session, configure
the agent's permissions (it provides an example), cover release, infrastructure security and operations (playbook §8).

## What it contains

| Part | Content | Details |
|---|---|---|
| 14 skills | `sdlc-next`, `sdlc-init`, `sdlc-map-codebase`, `sdlc-characterize`, `sdlc-spec`, `sdlc-plan`, `sdlc-tasks`, `sdlc-tests-from-ac`, `sdlc-implement`, `sdlc-bugfix`, `sdlc-review-diff`, `sdlc-docs`, `sdlc-sync`, `sdlc-loop` | [docs/skills.md](docs/skills.md) |
| 11 Python scripts | `verify`, `state`, `spec_lint`, `trace_check`, `bug_lint`, `diff_scope`, `scan_repo`, `docs_check`, `sync_check`, `loop`, `secrets_check` | [docs/scripts.md](docs/scripts.md) |
| 2 optional hooks | `Stop` (verify mandatory) and `PreToolUse` (guard), Claude Code only | [docs/scripts.md](docs/scripts.md#optional-hooks-claude-code-only) |
| 1 subagent | `sdlc-reviewer`, independent reviewer with read-only tools, Claude Code only | [docs/architecture.md](docs/architecture.md) |
| Playbook | The process, with templates and scripts identical to the plugin's | [docs/playbook-ai-software-lifecycle.md](docs/playbook-ai-software-lifecycle.md) |

## Flow

```
sdlc-init → [sdlc-map-codebase → sdlc-characterize]* → sdlc-spec → sdlc-plan → sdlc-tasks
          → sdlc-implement (or sdlc-loop) → sdlc-review-diff → sdlc-docs → sdlc-sync → PR
sdlc-bugfix: for defects, alongside the flow.   sdlc-next: at any time.   * brownfield only
```

The process is proportional to risk: the spec declares a **level** S, M or L (playbook §2.1). S skips plan and
`review.md`; L adds an ADR and the human reading of the diff; `diff_scope.py` reports a diff that exceeds the declared
level. Tests written from the ACs are locked by a `Test-Lock` commit and, at levels M and L, approved by the human before
implementation, with the SHA of the approved commit; with the JUnit report from `verify`, `trace_check.py --junit` counts
only executed, passing tests. Basic security: `secrets_check.py` as a `verify` step, new dependencies only in the plan or
with an ADR (`diff_scope.py`), example permissions for the loop (`skills/sdlc-loop/references/settings.loop.json`).

Every skill that produces a document to approve ends with a **STOP**: the agent does not move on and does not approve by
itself. Approvals (spec, plan, tests, review decision) carry name and date and are checked by the scripts.

## Quick start

1. Install the plugin (below).
2. In the project repository, ask the agent to use `sdlc-init`. It copies the scripts into `scripts/` and creates
   `AGENTS.md`, `docs/`, the VS Code task and the CI.
3. `python scripts/state.py` (or the `sdlc-next` skill) tells you where you are and what the next step is.
4. Continue with `sdlc-spec` (greenfield) or `sdlc-map-codebase` (existing code).

The full walkthrough, greenfield and brownfield, is in the [quick guide](docs/quick-guide.md).

The scripts stay **in the project**: verification in CI and from VS Code works even without the plugin. Each carries the
plugin version on line 2; to update them, ask `sdlc-init` to compare them (it does not touch the `STEPS` of `verify.py`).

## Documentation

| Document | English | Italiano |
|---|---|---|
| Quick guide | [docs/quick-guide.md](docs/quick-guide.md) | [docs/quick-guide_IT.md](docs/quick-guide_IT.md) |
| Playbook (the process) | [docs/playbook-ai-software-lifecycle.md](docs/playbook-ai-software-lifecycle.md) | [docs/playbook-ai-software-lifecycle_IT.md](docs/playbook-ai-software-lifecycle_IT.md) |
| Skill reference | [docs/skills.md](docs/skills.md) | [docs/skills_IT.md](docs/skills_IT.md) |
| Script and hook reference | [docs/scripts.md](docs/scripts.md) | [docs/scripts_IT.md](docs/scripts_IT.md) |
| Architecture, contracts, limits | [docs/architecture.md](docs/architecture.md) | [docs/architecture_IT.md](docs/architecture_IT.md) |
| Change history | [CHANGELOG.md](CHANGELOG.md) (Italian) | |
| Critical review and fix status | [REVIEW.md](REVIEW.md) (Italian) | |

**Language.** The documentation exists in English and Italian. Skills, templates and script messages are in Italian; the
field names they use (`- Stato:`, `- Livello:`, `test approvati:`, `atteso: rosso`, ...) are file contracts read by the
scripts and must not be translated.

## Installation

**Claude Code**
- Local trial: `claude --plugin-dir <path>/sdlc-playbook`
- Marketplace: fill in `owner` in `.claude-plugin/marketplace.json`, publish the repository, then
  `/plugin marketplace add <repo>` and `/plugin install sdlc-playbook@sdlc-playbook-marketplace`.
- Skills are invoked with the plugin prefix; hooks and subagent load with the plugin.

**Codex**
- The manifest is `.codex-plugin/plugin.json`. A Codex marketplace file is not included: its format must be checked
  against the documentation.
- Documented alternative for the skills only: copy the folders of `skills/` into `.agents/skills/` of the repository or of
  the home directory. Skills that cite `../sdlc-init/scripts/` and `../sdlc-sync/references/` require the folders to stay
  siblings.
- Hooks and subagent are not provided for Codex: the independent review happens in a new session (see `sdlc-review-diff`).

## Configuration

| Variable | Effect | Default |
|---|---|---|
| `SDLC_ENFORCE_VERIFY=1` | Enables the `Stop` hook: the agent cannot stop with `verify` red | off |
| `SDLC_VERIFY_ARGS` | Arguments of `verify.py` for the `Stop` hook (e.g. `--fast`) | empty (full verification) |
| `SDLC_STOP_MAX` | How many times in a row the `Stop` hook blocks in the same session before letting the agent stop | 3 |
| `SDLC_GUARD=1` | Enables the `PreToolUse` hook: blocks risky commands and reads (fail-closed) | off |

**Approvals.** For a control the agent cannot bypass, give it a separate identity (no push rights, or a bot account or
token without merge rights) and protect `main` with required PRs, code-owner review and CI. `sdlc-init` creates
`.github/CODEOWNERS`, the PR template and the CI with process checks on PRs; you set the branch rules. Details:
playbook §1.2.

The hooks start from `hooks/run.sh`, which uses the first of `python3`, `python` and `py -3` and requires `sh` (on Windows,
the one from Git for Windows). In the red phase (last closed task "atteso: rosso") the `Stop` hook does not block.

## Changing the plugin

- The playbook is edited in `docs/playbook.src.md` (English) and `docs/playbook_IT.src.md` (Italian), with the same
  section numbering; `python tools/build_playbook.py` regenerates both. The `{{FILE ...}}` blocks embed the plugin's
  scripts and templates, so they cannot diverge.
- Tests: `python -m unittest discover -s tests -v`. They include the **coherence tests** between skills, scripts,
  playbooks and documentation in both languages (§ references, skill and script names, no version references in the
  playbook, every document in two languages, links).
- CI: `.github/workflows/ci.yml` runs the tests on Ubuntu and Windows.

## Verification status

| What | Result |
|---|---|
| Test suite | Passes on Linux (includes loop with fake agent, hooks and `run.sh` launcher, scripts on temporary git repositories). On Windows 11 verified up to 0.8.0; from 0.9.0 only the `windows-latest` CI matrix covers it, and its result must be checked |
| `claude plugin validate .` | Passed on 0.4.0 (Claude Code 2.1.303, warnings on `author`); **not rerun** since 0.5.0 with the new `hooks.json` |
| Codex manifest | **Not validated** with a Codex tool |
| Skills run by a real agent on a project | **Not done**: to be tried on a sample greenfield and brownfield |
| Hooks in a real Claude Code session | **Not done**: tested only as scripts with the expected JSON input |
| `loop.py` with a real `claude -p` | **Not done**: tested with a fake agent |
| CI workflow generated by `sdlc-init` | **Not run** (YAML validated, process-check step never executed on a real PR) |

Details and known limits: [docs/architecture.md](docs/architecture.md). Change history: [CHANGELOG.md](CHANGELOG.md).

## To complete before distribution

- Fill in `owner` in the marketplace and add `author` in `plugin.json` (they were not invented).
- Try the skills on a sample repository (greenfield and brownfield) and fix what a real agent misreads: the trial path is
  at the end of the [quick guide](docs/quick-guide.md).
- Verify on Codex: marketplace format, explicit skill invocation, possible subagent support.
