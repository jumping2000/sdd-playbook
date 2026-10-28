# Changelog

*Versione italiana: [CHANGELOG_IT.md](CHANGELOG_IT.md)*

Entries before 0.13.0 use the names of their time (`sdlc-*`, `SDLC_*`, Italian field names).

## 0.16.0
Ideas from the AI Unified Process marketplace (S2, S3, S4, S5, S8 of the comparative analysis), adapted to SDD Playbook.
- **Portable skills (S2):** no skill reads another skill's files through `../`; it finds them by search
  (`**/sdd-sync/references/area-template.md`), so skills also work when installed one by one or with a host prefix.
  Coherence tests: no `../` in skill files, every cited path exists, `name` and `description` within the limits of the
  Agent Skills format.
- **Decision rights (S3):** new `## Decision rights` section in the `AGENTS.md` template (`Decides alone`, `Asks
  first`, `Never`); `sdd-implement` and the loop prompt follow it, rulings record only "Decides alone" decisions, a
  decision no line names is asked first, "Never" only grows; the reviewer checks the rulings against it.
- **Open questions with `blocking` (S4):** `- <question> — blocking: yes|no — about: REQ-nnn, AC-nnn`. An approved spec
  may keep non-blocking questions (warning); unmarked ones count as blocking; `about:` IDs must exist;
  `spec_lint.py --tasks` warns when an open task covers an AC named by a non-blocking question, and the implementation
  stops on it.
- **Language (S5):** `spec_lint.py` warns on vague words in REQs and ACs and, when `docs/glossary.md` exists (new
  optional template in `sdd-init`), on the synonyms its "Avoid" column lists.
- **Tests written after the code (S8):** new section of the test conventions: the spec is the oracle, expected values
  from the ACs, a test that disagrees with code outside the task stays failing and is reported; characterization tests
  are the exception.
- **Distribution:** `version`, `author`, `license` and `repository` in the plugin entry of
  `.claude-plugin/marketplace.json` (a coherence test keeps the version equal to the manifests); git tags `vX.Y.Z` from
  0.13.0 on, to pin a version; README with the installation commands tried with Claude Code.
- `state.py` points to `sdd-spec` when the next task covers an AC named by a non-blocking open question;
  `sdd-tasks` places those ACs in tasks of their own, last; `sdd-sync` reports the non-blocking questions left at
  closure; `docs/glossary.md` does not count as out of plan in `diff_scope.py`; `sdd-init` explains how to bring an
  existing project to these formats.
- Playbook §3.1, §3.3, §6, skill and script references, architecture, quick guide updated; new tests.

## 0.15.0
Review per task, from superpowers' "subagent-driven development", without a new agent.
- **When:** mandatory at level L; at level M when `progress.md` says `- Task review: on` (asked at the start of the
  feature); never at level S.
- **How:** implementation commits carry the trailer `Task: T-nn`. After every task (also after the `Test-Lock` commit of
  a test task, before the human approval) the agent runs the new `review_package.py <spec-dir> T-nn`, which writes in one
  file the task line, the covered ACs, the plan's interfaces and review focus, the task's rulings and the patches of its
  commits, and gives only that path to `sdd-reviewer` in the new **task review mode** (`Task verdict: pass | fix
  needed`). High and medium problems are fixed in the same task, at most 2 rounds; the verdict goes into
  `## Task reviews` of `progress.md`.
- **Checks:** `spec_lint.task_reviews_missing()`; `state.py` points back to `sdd-implement` while a closed `T-nn` task
  lacks `- T-nn: pass`; `sync_check.py` and the final checks of `loop.py` fail on it. The loop prompt runs the task
  review and records "not reviewed" when no reviewer is available.
- **Final review:** `sdd-review-diff` gives the reviewer the package of the whole branch (`review_package.py <spec-dir>`)
  and, after task reviews, focuses on integration, non-scope, overall coverage and rulings.
- `sdd-init` copies 12 scripts; playbook §2.1, §4, §11, skill and script references, architecture updated; new
  `tests/test_task_review.py`.

## 0.14.0
Practices taken from the superpowers plugin, adapted to the governance of SDD Playbook: better specs and plans, better
tests, decisions made visible. Prose and templates, plus one new check in `spec_lint.py`.
- **Spec (`sdd-spec`):** the agent reads code and material before asking, plays the request back, asks one question per
  message (the one that would most change what gets built), offers 2-3 options when the outcomes for the user really
  differ; new `- **Anti-goals:**` line in the spec template (`spec_lint.py` warns if missing).
- **Plan (`sdd-plan`):** interfaces between components (produces / consumes, exact names); new `## Review focus` section
  with at most 5 input classes no AC exercises, each with its test (`spec_lint.py --plan`: section required, placeholders
  are a warning before approval and an error after; `- none` is valid); self-review against the spec (coverage,
  consistent names, proportion). `diff_scope.py` also reads the "Where" column of the review focus as planned paths.
- **Test quality (`sdd-tests-from-ac`):** anti-pattern table and approval checklist in the test conventions; the
  reviewer agent judges the tests with them.
- **Rulings:** decisions taken within the latitude of spec and plan go into `progress.md` (`## Rulings`: what, why, cost
  if wrong); `sdd-implement` creates `progress.md` when missing; the reviewer checks that no ruling changes a requirement.
- **Receiving a review:** `T-Rnn` findings are verified on the code first; wrong ones are recorded in
  `## Disputed review findings` instead of being "fixed"; the user decides which findings become tasks.
- **Debugging (`sdd-bugfix`):** new `references/debugging.md` (trace back to the source, one hypothesis at a time,
  bisect history, input and test suite, flaky tests, stop after three failed fixes).
- Playbook §3.3, §3.4, §6, §6.1, §7.2 updated; new tests for anti-goals, review focus and the loop prompt sections.

## 0.13.0
The plugin is called **SDD Playbook**, is entirely in English and also supports GitHub Copilot. No compatibility with the
previous names: the plugin is in design and has never been used on a project.
- **Name:** identifier `sdd-playbook` in every manifest and in the marketplace (`sdd-playbook-marketplace`, owner
  `jumping2000`); skills `sdlc-*` → `sdd-*`, subagent `sdd-reviewer`, environment variables `SDLC_*` → `SDD_*`
  (`SDD_ENFORCE_VERIFY`, `SDD_VERIFY_ARGS`, `SDD_STOP_MAX`, `SDD_GUARD`), header of the copied scripts
  `# sdd-playbook: <version>`, folder of the `Stop` hook counter `sdd-playbook`.
- **Plugin in English:** skills, templates, scripts (comments, docstrings, messages), hooks, agent and tests. The file
  contracts change accordingly: `- Status:`, `- Level:`, `- Owner:`, `- Approved by / date:`, `- Based on spec:`,
  `- Based on plan:`, `verify:`, `covers:`, `expected: red`, `tests approved:`, `- Outcome:` (`compliant`,
  `compliant with reservations`, `non-compliant`), `- Decided by:`, `- Human diff review:`, `Last aligned`,
  `Linked specs`, bug states `open`/`diagnosed`/`fixed`/`verified`, `- Do not modify:` and `- Sensitive areas:` in
  `AGENTS.md`, `in-revision`, output `VERIFY: GREEN`/`RED` and `NEXT:`. `docs/system/mappa.md` → `docs/system/map.md`.
- **GitHub Copilot:** root `plugin.json` (Agent Plugins format) for the Copilot CLI, with the skills and the reviewer
  agent; `sdd-init` asks which agents the team uses and, for Copilot, copies the skills into `.github/skills/` and the
  custom agent `sdd-reviewer.agent.md` (tools `read` and `search`) into `.github/agents/`. The hooks are not ported:
  declared limit. No Copilot path has been tried yet.
- **MIT license** (`LICENSE`), author and repository in the manifests; README with the typical GitHub badges (version,
  license, CI, Python, dependencies, platforms, agents, status, languages, last commit, stars).
- **Complete bilingual documentation:** changelog and review also have an English version (no suffix) and an Italian
  one (`_IT`); the playbook is titled "SDD Playbook" and describes Copilot.
- CI of the repository and template generated by `sdd-init`: Linux runner pinned to `ubuntu-24.04` instead of
  `ubuntu-latest`, which moves to Ubuntu 26 from 2026-10-19.
- Tests rewritten in English and renamed (`test_consistency`, `test_levels`, `test_test_verification`,
  `test_security`, `test_review_fixes`); new checks: three manifests with the same version, version badge, license,
  read-only Copilot agent, no Italian text in the plugin files, no `sdlc-`/`SDLC_` name outside the history.

## 0.12.0
Complete documentation in English and Italian. No change to the behaviour of skills and scripts.
- `README.md` in English and `README_IT.md` in Italian, with the goal of the plugin and the rationale of the set of
  skills (typical failure of a coding agent → answer of the plugin → where).
- New quick guide, `docs/quick-guide.md` and `docs/quick-guide_IT.md`: preparation, greenfield, brownfield, cycle per
  feature, levels, bugs, loop, most used commands, frequent problems and trial path.
- Every document in `docs/` in two languages, with the README convention (English without suffix, Italian `_IT`):
  `architettura.md` → `architecture_IT.md` (new `architecture.md`), `skills.md` → `skills_IT.md`, `scripts.md` →
  `scripts_IT.md`, playbook generated from two sources (`playbook.src.md`, `playbook_IT.src.md`) with the same §
  numbering.
- `tools/build_playbook.py` generates both playbooks; the coherence tests check both languages (same §, every skill
  and script documented, every document present in two languages, valid links).
- Italian documents aligned with the content of 0.11.1 (process checks in CI, test approval with SHA, "in design"
  status).

## 0.11.1
Fixes from the critical review of versions 0.9.0-0.11.0. The plugin is still in design and never used on a project: no
compatibility rule added for existing projects.
- **Approved tests tied to the SHA:** the format is `test approvati: <nome, aaaa-mm-gg, sha>`; `diff_scope.py` reports a
  SHA that is not the `Test-Lock` commit of the task, or a new `Test-Lock` commit after the approval. Before, a second
  `Test-Lock` commit could weaken the approved tests without anyone noticing.
- **Level not bypassable from the branch:** `diff_scope.py` counts renames with the source path (`--no-renames`), reads
  `AGENTS.md` and the spec level from the merge-base, reads the `AGENTS.md` entries as paths (backticks or first word)
  and reports those that are not. `loop.py` also runs `spec_lint.py` among the final checks.
- **Dependencies:** a **new** ADR in `docs/adr/` is needed (README and indexes do not count); a lockfile counts if the
  plan lists its manifest.
- **JUnit:** a case is attributed to the file with the most matching path (`tests.a.test_api` ↔ `tests/a/test_api.py`),
  not to the name alone; the Go convention `TestAC001_` is recognized; Java convention with the ID in the method name;
  `--junit` without a value is an error.
- **Generated files:** `__pycache__/`, `*.pyc` and `reports/` count neither as loop progress nor as production files;
  the scripts no longer write bytecode into the project; `loop.py` warns if the report is not ignored.
- **`loop.py` uses `spec_lint`** for level and approvals instead of duplicated regexes (the level in the Revisions no
  longer counts); "atteso: rosso" case-insensitive, also in the `Stop` hook.
- **Loop permissions:** `settings.loop.json` denies writes to `scripts/`, `AGENTS.md`, `.github/`, spec, plan and
  review, and `git commit --amend`; it also allows `python3`.
- **Generated CI:** "Controlli di processo" step on PRs (`spec_lint --base`, `diff_scope`, `trace_check --junit`,
  `secrets_check`), the check the agent cannot bypass.
- Minor: non-ASCII paths in `secrets_check.py`, `diff_scope.py` and `loop.py` (`core.quotePath=false`);
  `.secrets-ignore` and `.env.*.example`; guard on `git reset ... --hard`, `git -C . reset --hard`, `git clean -d -f`,
  `.env` inside a word, `find -delete`, without false positives on `git rm -r --cached` and `git check-ignore`, and
  fail-closed on a malformed `tool_input`; `sync_check.py` accepts the spec folder after the options.

## 0.11.0
Fifth and last release of the plan on the process issues: security and maintenance (A5, A7, B10, C).
- New script `secrets_check.py`: private keys, tokens with a known format (AWS, GitHub, GitLab, Slack, Stripe, Google,
  Anthropic, OpenAI) and `.env` files in the branch files, or in the whole repository with `--all`; it never prints the
  value. It is a `secrets` step of the `verify.py` template and a final check of `loop.py`.
- `diff_scope.py`: a changed manifest or lockfile must be in the approved plan or accompanied by an ADR in `docs/adr/`
  (A7: "new dependencies only with an ADR" is now checked).
- `PreToolUse` guard (B10): analysis by segments and words; blocks `rm -r -f`, `rm --recursive --force`, `+refspec`,
  `--force-with-lease`, `--delete`, `git clean -f`, `Remove-Item -Recurse`, `shutil.rmtree`, every reference to `.env`
  (also `cp`, `Select-String`, upper case, NTFS streams), the Grep tool on `.env` files; with unreadable JSON it blocks.
- Subagent `sdlc-reviewer` with read-only tools (A5): it receives the diff and the check outputs in the message; the
  repository content is data, not an instruction.
- Loop: example permissions `settings.loop.json` (allowlist and deny-list for Claude Code); `PROMPT.md` against prompt
  injection and unplanned dependencies.
- Maintenance: every copied script carries the plugin version on line 2; `sdlc-init` explains how to update a project.
  Actions of the CI and of the template updated to `checkout@v6` and `setup-python@v6` (Node 24).
- Documentation: counter of the `Stop` hook described in its real folder; playbook §1.2, §7.2, §8, §11.

## 0.10.0
Fourth release of the plan on the process issues: verification of the tests (remaining A3, tests written and
implemented by the same agent).
- `trace_check.py --junit FILE|DIR`: with the JUnit XML report of the executed tests every AC must have at least one
  executed and passing case, and none failed; skipped cases do not count. Cases are attributed to the spec with the same
  rules as citations (qualified, or declared file recognized from `file` and `classname`). Unreadable report: exit 2.
- `sync_check.py --junit`, mandatory at level L; `loop.py --junit` passes it to the final check.
- Approved tests: at levels M and L the closed "atteso: rosso" test task carries `— test approvati: <nome, data>`,
  written after the human has read the locked tests. `state.py` points to `sdlc-tests-from-ac` until it is there,
  `loop.py` stops (exit 1) and does not restart with an approval pending (exit 2), `sync_check.py` requires it.
- `verify.py` template with `--junitxml=reports/junit.xml`; table of JUnit reporters per stack; task, `PROMPT.md` and PR
  templates updated; skills `sdlc-tests-from-ac`, `sdlc-implement`, `sdlc-loop`, `sdlc-review-diff`, `sdlc-sync`,
  `sdlc-init` updated. Playbook: principle 5, §3.5, §4, §6, §7, §9.

## 0.9.0
Third release of the plan on the process issues: process proportional to risk (A6, and the part of A5 on sensitive
areas).
- Levels S, M, L (playbook §2.1): field `- Livello:` in the spec, checked by `spec_lint.py` (warning if missing: it
  counts as M) and included in the hash, so lowering it after the approval voids it. The hashes of specs without the
  field do not change.
- `diff_scope.py` reports an **underestimated level** as an error: a file in the new `- Aree sensibili:` lines of
  `AGENTS.md` requires L; a dependency manifest or lockfile, or more than 3 production files, require at least M. At
  level S without a plan the plan comparison is skipped.
- Level S: no plan and no `review.md`, optional `T-DOC`, optional area page (`state.py`, `spec_lint.py`,
  `sync_check.py`).
- Level L: `review.md` requires `- Revisione umana del diff:` (`state.py`, `sync_check.py`); ADRs for the decisions
  taken.
- Spec, review and `AGENTS.md` templates updated; skills `sdlc-spec`, `sdlc-plan`, `sdlc-tasks`, `sdlc-implement`,
  `sdlc-review-diff`, `sdlc-sync`, `sdlc-next`, `sdlc-init`, `sdlc-loop` updated. Playbook: principle 5 and new §2.1.

## 0.8.0
Second release of the plan on the process issues: spec ID and lifecycle, team work (A8).
- Spec ID = date + slug (`docs/specs/2026-10-24-export-csv/`, title `# SPEC-2026-10-24-export-csv: ...`):
  `spec_lint.py` checks that title and folder match and that the date is valid. The old `SPEC-NNN` stay valid.
  `trace_check.py` and `sync_check.py` recognize the new IDs (also in the `_` form of function names) and compare them
  by exact ID: `SPEC-2026-10-24-export` does not count for `SPEC-2026-10-24-export-csv`.
- State `in-revisione` to change an approved spec, with a mandatory entry in `## Revisioni`. The tasks record
  `- Basato su piano:`; with `--plan` and `--tasks` together `spec_lint.py` reports them if the plan has changed.
- `T-Rnn` tasks from the problems of the review: checked by `spec_lint.py` (`copre:` optional), executed by
  `sdlc-implement` and by the loop; `state.py` asks to create them after a `non conforme` and to repeat the review when
  they are closed.
- `state.py`: next step for every active spec; `PROSSIMO` for the spec of `--spec`, of the current branch or the only
  active one, otherwise `scegli`.
- `Stop` hook: the block counter lives in a private user folder (0700) and is opened without following symbolic links
  (finding of the automatic security review on 0.7.0).

## 0.7.0
First release of the plan on the process issues (`REVIEW.md`): trust in attestations (A1, A4, B9).
- Anti-drift hash: an approved spec and an approved plan carry `- Hash:` of their own body; the plan also carries
  `- Basato su spec:`. `spec_lint.py` reports missing or mismatching hashes, `--hash` computes it; `state.py` treats
  invalid approvals as lapsed and says so in the reason.
- Approval through merge: `spec_lint.py --base <ref>` requires spec and plan to be on `<ref>` and identical. Playbook
  §1.2: separate identity for the agent (no push, or a bot or token without merge rights), design PR, protection of
  `main` with code-owner review. New templates `CODEOWNERS.tmpl` and `pull_request_template.md`, created by
  `sdlc-init`.
- `loop.py`: closes successfully only if `trace_check.py` and `diff_scope.py` also pass (final checks).
- `Stop` hook: blocks up to `SDLC_STOP_MAX` times in a row per session (default 3), then lets the agent stop with a
  warning; the counter resets when `verify` turns green again.
- Skills `sdlc-spec`, `sdlc-plan`, `sdlc-tasks`, `sdlc-implement`, `sdlc-sync`, `sdlc-loop`, `sdlc-init` updated.

## 0.6.0
Fix of point B4 of the review (`REVIEW.md`): AC traceability per spec.
- `trace_check.py` attributes every citation to a spec: `SPEC-nnn/AC-nnn` (or `SPEC001_AC001`) counts for that spec;
  `AC-nnn` counts for the spec declared in the file (`# SPEC-nnn`), or, in an undeclared file, only if the project has a
  single spec. Ambiguous citations do not count and are reported. Before, the tests of SPEC-001 also covered SPEC-002.
- Citations on `TODO`/`FIXME`/`XXX` lines no longer count as tests.
- `sync_check.py` uses the same rules and, if tests are missing, points out the ambiguous citations.
- Test conventions and skill `sdlc-tests-from-ac` updated to qualified IDs.
- Compatibility: a project with a single spec keeps working with short citations.

## 0.5.0
Fixes from the review of 2026-10-23 (`REVIEW.md`, points B1-B3, B5-B8, B11 and the TDD/hook/loop conflict of A2).
- UTF-8 output in all scripts and hooks: the suite now passes on Windows with a cp1252 console too (B1).
- Hooks started from `hooks/run.sh`: it exits immediately if the hook is not enabled, looks for `python3`, `python`,
  `py -3`; without Python 3 the error is visible and non-blocking. Before, on a clean Ubuntu, the hooks did not start and
  gave no warning (B2).
- `diff_scope.py`: forbidden zones with a leading dot (`.github/`) now trigger (B3); all the `Non modificare:` lines are
  read; plan path = first word or text in backticks; "Dove" column of the test strategy included in the plan (B5).
- `spec_lint.py`: `<...>` placeholders in `T-nn` tasks are errors (B6); ACs looked up by exact ID in the "Strategia di
  test" section only (B7).
- `loop.py`: stall also computed on the content of the changes; `--timeout` per iteration; exit code of the agent
  reported; a red baseline is refused except in the red phase or with `--allow-red-baseline` (B8).
- TDD: red tests are committed with the trailer `Test-Lock: T-nn` and `diff_scope.py` reports every later change; "red
  phase" recognized by the `Stop` hook and `loop.py`; loop `PROMPT.md` and skills updated (A2).
- Repository `.gitattributes` with LF (B11).

## 0.4.0
- Skills `sdlc-docs` (T-DOC) and `sdlc-sync` (T-SYNC); scripts `docs_check.py` and `sync_check.py`.
- `sync_check.py` also requires the human decision in the review.
- Complete documentation of the plugin (`docs/skills.md`, `docs/scripts.md`, `docs/architettura.md`) and playbook
  generated from the plugin files (`tools/build_playbook.py`).
- Coherence tests between skills, scripts, playbook and documentation; CI on Ubuntu and Windows.

## 0.3.0
- Skills `sdlc-review-diff` and `sdlc-loop`; subagent `sdlc-reviewer` (Claude Code).
- Scripts `diff_scope.py` and `loop.py` (cap, stall detection, refusal of main/master, dry run, stop on `T-nn` tasks
  only).
- Optional hooks `Stop` (`SDLC_ENFORCE_VERIFY`) and `PreToolUse` (`SDLC_GUARD`).
- `state.py`: review-diff, docs and sync phases.

## 0.2.0
- Skills `sdlc-map-codebase`, `sdlc-characterize`, `sdlc-tests-from-ac`, `sdlc-bugfix`.
- Scripts `scan_repo.py`, `trace_check.py`, `bug_lint.py`.
- `state.py`: detection of brownfield (existing code without a map) and of unverified bugs.

## 0.1.0
- Skills `sdlc-next`, `sdlc-init`, `sdlc-spec`, `sdlc-plan`, `sdlc-tasks`, `sdlc-implement`.
- Scripts `verify.py`, `spec_lint.py` (spec, plan, tasks), `state.py`.
- Manifests for Claude Code and Codex.
