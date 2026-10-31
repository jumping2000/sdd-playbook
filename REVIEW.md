# Critical review of sdlc-playbook 0.4.0

*Versione italiana: [REVIEW_IT.md](REVIEW_IT.md)*

> Historical document: it uses the names of 0.4.0 (`sdlc-*`, `SDLC_*`, Italian field names). Since 0.13.0 the plugin is
> called SDD Playbook (`sdd-*`, `SDD_*`, English field names).

- Date: 2026-10-23
- Subject: playbook (`docs/playbook-ai-software-lifecycle.md`), 14 skills, 2 hooks, subagent `sdlc-reviewer`, 10 scripts
- Reviewer: Claude (Opus 5.5) at the request of the repository owner
- Plugin code: **not modified**. The import commit contains the 0.4.0 zip as it is; this review lists the problems, it
  does not fix them.

## Summary

The design is good: mandatory non-scope, characterization tests in brownfield, "behaviour that must NOT change" in bugs,
objective stop criteria for the loop, limits honestly declared in the README. There are three serious problems:

1. **Only apparent guarantees.** Approvals, traceability and the loop stop are checked by scripts that verify the
   *presence* of text the agent itself can write.
2. **Conflicting mechanisms.** TDD requires red tests; the `Stop` hook and the loop prompt push the agent to make them
   green.
3. **Never tried end-to-end.** The README admits it (skills never run by a real agent, hooks never in a real session,
   loop never with `claude -p`). Moreover, on native Windows the plugin's suite fails and on a clean Linux the hooks do
   not start.

## Environments and results

| Environment | How | Plugin suite (61 tests) | Notes |
|---|---|---|---|
| Windows 11, Python 3.13, cp1252 console | `python -m unittest discover -s tests` | **3 errors** | Encoding: see B1 |
| Linux: Ubuntu 24.04 on WSL2, Python 3.12.3, ext4 filesystem | clone of the repository, same command | **OK** | Also with `LC_ALL=C` |
| GitHub Actions (`.github/workflows/ci.yml`) | push to `main` | see section "CI on GitHub" | |

The trials of the scripts (section B) were repeated on both platforms with the same outcome, except where stated: the
logic defects do not depend on the operating system.

## A. Process issues (playbook)

**A1. Human gates are not enforced.** "Approvata da / data" is a text field the agent fills in; the scripts only check
that it is not empty or a placeholder. The approval is not tied to a version: a spec changed after the ok stays
`approved`.
*Proposal:* approval as an act the agent cannot perform (PR review with CODEOWNERS on `docs/specs/**`, signed commit by
the human); as a minimal alternative, hash of the approved spec recorded in the plan and `spec_lint` failing if the file
changes.

**A2. TDD conflicts with automation.** Test tasks must end red ("atteso: rosso"), but:
- the `Stop` hook prevents stopping with `verify` red, so it pushes the agent to implement immediately or to weaken the
  tests;
- the loop `PROMPT.md` says "if it fails fix it, when green commit" and does not know the "atteso: rosso" tasks.

The rule "red tests are not committed alone" also removes the most useful checkpoint: with the tests committed before
the implementation one could verify that the implementation commit does not touch them.
*Proposal:* commit of the red tests (marked `xfail`/skip with the ID, or CI tolerant on the branch) and a check that the
test files do not change in the implementation commit without approval.

**A3. Traceability does not hold with several specs.** ACs restart from AC-001 in every spec, `trace_check` searches in
all the tests. A citation in a comment (`# TODO AC-003`) counts as a test. The script measures citations, not tests that
exist and pass (trial B4).
*Proposal:* qualified IDs (`SPEC-002/AC-001`) and, where possible, the report of the executed tests (JUnit XML).

**A4. The loop stop depends on what the agent declares.** It exits with `verify` green and boxes ticked, but the agent
ticks the boxes. *Proposal:* add `trace_check` and `diff_scope` to the exit criterion.

**A5. Review not very independent.** Same model in a fresh context: correlated errors. The "read-only" subagent has
`Bash`, so read-only is an instruction, not a constraint. Principle 5 ("you do not reread every line") leaves a
responsibility gap. *Proposal:* mandatory human review on sensitive areas, or a different model for the review; subagent
tools without writing.

**A6. Ceremony and gate fatigue.** About 7 documents and 4-5 gates per feature; the "small feature" threshold ("describe
the diff in one sentence") is vague. Duplicated documentation (spec, area page, README, ADR, map): T-SYNC risks becoming
a ritual. *Proposal:* explicit levels S/M/L with objective criteria (files touched, public APIs, sensitive areas); after
`implemented` the spec becomes an archive and the living source is the area page and the tests.

**A7. Security out of scope, yet it is the typical risk of generated code.** The `verify` template has neither a
dependency audit nor a secret scan; "new dependencies only with an ADR" is not checked by any script; the loop runs
unsupervised and prompt injection is not mentioned. *Proposal:* `diff_scope` reports changes to manifests and lockfiles;
gitleaks and dependency audit as `verify` steps.

**A8. Team work not foreseen.** `SPEC-NNN` numbers that collide between branches; `state.py` considers only the first
active spec; no flow to change an approved spec; the problems of the review do not become tasks (after a "non conforme"
`state.py` points to `sdlc-implement`, which finds no open task).

## B. Confirmed defects in scripts and hooks

| # | Where | Problem | Windows | Linux |
|---|---|---|---|---|
| B1 | all scripts | They print non-ASCII text ("è") with the console encoding. On Windows it is cp1252: whoever reads in UTF-8 (tests, agent) receives unreadable characters or `None`. `sys.stdout.reconfigure(encoding="utf-8")` is missing | 3 tests fail | OK |
| B2 | `hooks/hooks.json` | It launches `python ...`. On a clean Ubuntu `python` does not exist (only `python3`): the hook exits 127, which for Claude Code is a **non-blocking** error, so `SDLC_ENFORCE_VERIFY` and `SDLC_GUARD` have no effect and nobody notices. On Windows `python` may be missing from the PATH (that is why `tasks.json` uses `py -3`) | risk | **confirmed** (exit 127) |
| B3 | `diff_scope.py` | `lstrip("./")` removes all leading dots: `.github/` becomes `github/` and never matches. In a real git repo with `- Non modificare: .github/`, a change to `.github/workflows/ci.yml` gives only an "out of plan" warning and exit 0 | confirmed | confirmed |
| B4 | `trace_check.py` | Global search of the IDs: a SPEC-002 without tests of its own appears 100% covered by the tests of SPEC-001; a TODO comment counts as a test | confirmed | confirmed |
| B5 | `diff_scope.py` | It reads only the first `Non modificare:` line; `- src/a.py (nuovo): ...` becomes the path `src/a.py (nuovo)`; tests not listed in the plan produce "out of plan" noise | confirmed | confirmed |
| B6 | `spec_lint.py --tasks` | It accepts the template with the placeholders (`verifica: \`<comando test mirato>\``). It is intended: `test_coerenza` checks that the template passes the lint. But then the lint does not distinguish a filled-in `tasks.md` from a copied one | confirmed | confirmed |
| B7 | `spec_lint.py --plan` | Substring check: citing the ACs in any sentence is enough; `AC-1` is found inside `AC-10` | confirmed | confirmed |
| B8 | `loop.py` | Progress is computed from `git status --porcelain`, which reports only file names. Trial: an agent that adds one line per iteration to the same file (already changed, not yet committed) is stopped for "no progress" after 2 iterations with `--stall 2`, while the work was advancing. Also: no timeout per iteration, exit code of the agent ignored, green baseline not checked | — | **confirmed** |
| B9 | `stop_verify.py` | It blocks only once (`stop_hook_active`); it runs the full `verify` at every end of turn, even when the user only asks a question | by construction | by construction |
| B10 | `pretool_guard.py` | Bypassable: `rm -r -f`, `rm --recursive --force`, `git push origin +main`, `Remove-Item -Recurse`, `shutil.rmtree`, `Select-String .env`, `cp .env`, the Grep tool on the file all pass. `ENV_FILE` is case-sensitive (`.ENV` on Windows), does not handle NTFS streams (`.env::$DATA`), and with unreadable JSON it lets the call through (fail-open) | confirmed | confirmed |
| B11 | plugin repository | It has no `.gitattributes` of its own, which the playbook recommends: on Windows with `core.autocrlf=true` the scripts go to CRLF in the working copy | observed | — |

## C. Skills

- **`sdlc-loop`:** no permission configuration. `claude -p` without an allowlist either blocks (stall) or pushes towards
  `--dangerously-skip-permissions`. An example `settings.json` with allowlist and deny-list is needed.
- **`sdlc-init`:** copies the scripts into the project without a version header or update path: copies and plugin
  diverge over time.
- **`sdlc-spec`, `sdlc-plan`, `sdlc-review-diff`:** the agent writes the approver's name without knowing who it is (risk
  of "Approvata da: utente").
- **`sdlc-tests-from-ac` + `sdlc-implement`:** the same agent, and often the same session, writes tests and code; the
  human spot check before implementation is the only safeguard (see A2).
- **`sdlc-review-diff`:** a single review at the end of the feature on a large diff; the problems found do not become
  tasks.
- **Strengths:** `sdlc-characterize` (deliberate break and restore), `sdlc-bugfix` (mandatory reproduction, "must NOT
  change", 3 attempts), explicit STOPs, `sdlc-next` relying on the script and not on the conversation.

## D. Priorities

1. Approvals tied to PRs or hashes, not to a text field (A1).
2. Solve the TDD/hook/loop conflict; commit of the red tests and "untouched tests" check (A2).
3. AC IDs qualified per spec (A3, B4).
4. Make the hooks reliable: interpreter resolved portably (`python3`/`py -3`) and visible failure (B2).
5. Fix B1, B3, B5-B8.
6. Native agent permissions and sandbox instead of the regex guard; permission file ready for the loop (B10, C).
7. Dependency audit and secret scan in `verify` (A7).
8. End-to-end trial on a real greenfield and brownfield before distributing.

## CI on GitHub

Outcome of the `.github/workflows/ci.yml` workflow on the import commit `0e748d2`
([run #1](https://github.com/jumping2000/sdd-playbook/actions/runs/39994902377)):

| Job | Outcome | Notes |
|---|---|---|
| `test (ubuntu-latest)` | **success** | Consistent with the WSL trial |
| `test (windows-latest)` | **failed** in the step `python -m unittest discover -s tests -v` (exit 1, 25 s) | The log requires a GitHub login and was not read; the outcome is consistent with B1, reproduced locally |

Runner warning on both jobs: `actions/checkout@v4` and `actions/setup-python@v5` use Node.js 20, deprecated. The same
holds for the template `skills/sdlc-init/references/ci-github-actions.yml`, hence for the CI that `sdlc-init` generates
in projects: it must be updated to the current versions of the actions (pinned by SHA in regulated contexts).

Conclusion per platform: **Linux** is the platform on which the plugin works as declared, except for the hooks, which do
not start on a clean installation (B2). **Native Windows**, declared as supported, does not pass its own suite.

## Fix status (0.5.0-0.13.0)

| Point | Status | How |
|---|---|---|
| B1 | fixed | `reconfigure(encoding="utf-8")` in every script and hook; test with `PYTHONIOENCODING=cp1252` |
| B2 | fixed | `hooks/run.sh`: enablement checked before looking for Python, then `python3`/`python`/`py -3`; without Python a visible exit 1 |
| B3 | fixed | `normalizza()` removes only the `./` prefix |
| B4 | fixed (0.6.0) | citations attributed to the spec: `SPEC-nnn/AC-nnn`, declared file `# SPEC-nnn`, or short citation only with one spec in the project; ambiguous ones reported; `TODO`/`FIXME`/`XXX` lines ignored. It remains true that the script reads text and does not check that the tests pass |
| B5 | fixed | all the `Non modificare:` lines; path = first word or text in backticks; "Dove" column in the plan |
| B6 | fixed | placeholders in `T-nn` tasks = error; the template now shows as "to fill in" |
| B7 | fixed | ACs looked up by exact ID in the "Strategia di test" section |
| B8 | fixed | fingerprint with `git diff HEAD` and the content of untracked files; `--timeout`; exit code reported; baseline checked |
| B11 | fixed | `.gitattributes` with LF |
| A2 | fixed | `Test-Lock` commit of the red tests + check in `diff_scope.py`; red phase in the `Stop` hook and in `loop.py`; `PROMPT.md` and skills updated |
| A1 | fixed (0.7.0) | anti-drift hash on spec and plan; approval = merge of the design PR into protected `main` (`spec_lint.py --base`), with a separate identity for the agent; CODEOWNERS and PR templates. Branch protection must be configured on the platform |
| A4 | fixed (0.7.0) | the loop closes successfully only if `trace_check.py` and `diff_scope.py` also pass |
| B9 | partly fixed (0.7.0) | counter per session (`SDLC_STOP_MAX`); the full `verify` at every end of turn remains, reducible with `SDLC_VERIFY_ARGS` |
| A8 | largely fixed (0.8.0) | date + slug IDs (no collisions between branches), `in-revisione` state with the hash chain spec → plan → tasks, review problems as `T-R` tasks, `state.py` with several specs and association to the branch. The merge conflict of two changes to the same spec is still to be handled |
| A6 | fixed (0.9.0) | levels S/M/L in the spec (included in the hash); `diff_scope.py` reports an underestimated level (sensitive areas → L; dependencies or more than 3 production files → at least M); S without plan or `review.md`, L with ADR and human diff review. Public interfaces and data formats remain at the approver's judgement |
| A5 | partly fixed (0.9.0) | human diff review mandatory at level L (sensitive areas). The subagent tools remain |
| A3 | fixed (0.10.0) | with `--junit` `trace_check.py` and `sync_check.py` count only the tests executed and passed in the JUnit report (mandatory at level L) |
| C (`sdlc-tests-from-ac` + `sdlc-implement`) | fixed (0.10.0) | at levels M and L the locked tests are approved before implementation (`test approvati:`), checked by `state.py`, `loop.py` and `sync_check.py` |
| A5 | fixed (0.9.0, 0.11.0) | human diff review at level L; subagent with read-only tools; a different model is possible with `model:`. A model of the same family remains, unless the user chooses otherwise |
| A7 | fixed (0.11.0) | `secrets_check.py` in `verify` and in the loop; dependencies only in the plan or with an ADR (`diff_scope.py`); prompt injection in the playbook and `PROMPT.md`. The dependency audit is documented per stack, not included |
| B10 | largely fixed (0.11.0) | guard by segments and words, all the cases of table B blocked, fail-closed. It remains bypassable by purpose-built commands: the real control is native permissions |
| C (`sdlc-loop`, `sdlc-init`) | fixed (0.11.0) | example `settings.loop.json`; version in the copied scripts and update procedure |
| CI on GitHub (Node 20) | fixed (0.11.0) | `checkout@v6` and `setup-python@v6` in the CI and in the template |
| Critical review 0.9-0.11 (I1-I8) | fixed (0.11.1) | test approvals tied to the `Test-Lock` SHA; `AGENTS.md` and level read from the merge-base, renames counted; a new ADR for dependencies; JUnit attribution by path; generated files excluded; `loop.py` uses `spec_lint`; loop permissions without writes to the checks; process checks in the PR CI. I7 (compatibility with 0.8.0 projects) not applicable: the plugin is not in use yet |
| Name, language and agents (0.13.0) | done (0.13.0) | plugin renamed SDD Playbook (`sdd-*`, `SDD_*`), entirely in English, MIT license, GitHub Copilot support (CLI plugin, skills in `.github/skills/`, custom agent). Copilot not yet tried; hooks not ported to Copilot |
| A6 revisited (0.20.0) | changed (0.20.0) | the first real trial showed the opposite risk: too much ceremony for a small task. The level is now chosen by the user among options; `diff_scope.py` keeps as errors only sensitive areas (→ L) and dependencies (→ M), the size at level S is a warning and the process tooling does not count; `spec_lint.py` warns on too many ACs |
| A1 revisited (0.20.0) | changed (0.20.0) | approvals selected among options and written by `approve.py`; profiles: **team** keeps the merge of the design PR as the approval, **solo** lets the agent move `main` by fast-forward after a selected gate (in solo the evidence is the user's selection, see architecture, limits) |
| End-to-end trial (D.8) | partly done (0.17.0) | one trial by Claude Code on a small greenfield (Docker stack): it produced the 0.20.0 changes. Hooks and loop not yet run by a real agent; 0.20.0 not yet tried on a project |
