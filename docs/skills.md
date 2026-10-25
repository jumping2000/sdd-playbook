# Skill reference

*Versione italiana: [skills_IT.md](skills_IT.md)*

Each skill is a folder `skills/<name>/` with a `SKILL.md` (frontmatter `name` and `description`, then the instructions)
and, when needed, `references/` with the templates. The instructions are deliberately short (under 150 lines): the
process details live in the [playbook](playbook-ai-software-lifecycle.md), which every skill cites by section. Skills and
templates are in English, like every part of the plugin.

**Common conventions**
- Scripts are called as `python scripts/<name>.py` from the project root: `sdd-init` copies them there.
  If a project was initialized with an earlier version, copy the missing script from `skills/sdd-init/scripts/`.
- Every skill that produces a document to approve ends with a **STOP**: it asks for approval with name and date,
  records the hash of the approved content (`spec_lint.py --hash`) and does not start the next phase. Spec, plan and
  tasks then go into the design PR: the merge into `main`, which only the human performs, is the approval (playbook §1.2).
- Skills never commit without the user's authorization and never on `main`/`master`.
- When a requirement is ambiguous, they stop and ask: they do not assume.

**Typical order:** `sdd-init` → (`sdd-map-codebase` → `sdd-characterize`) → `sdd-spec` → `sdd-plan` →
`sdd-tasks` → `sdd-implement` (or `sdd-loop`) → `sdd-review-diff` → `sdd-docs` → `sdd-sync`. The spec level
(playbook §2.1) shortens or strengthens it: S skips `sdd-plan` and `review.md`, L adds an ADR and a human reading of
the diff.

| Skill | Playbook | Produces | Check | Human gate |
|---|---|---|---|---|
| `sdd-next` | all | nothing (read-only) | `state.py` | — |
| `sdd-init` | §1 | scripts, `AGENTS.md`, `docs/`, VS Code task, CI | `verify.py` | principles and stack |
| `sdd-map-codebase` | §5 | `docs/system/map.md` | `scan_repo.py`, `verify.py` | map spot check |
| `sdd-characterize` | §5 | characterization tests, area page | `verify.py` + failure proof | spot check |
| `sdd-spec` | §3.3 | `spec.md` | `spec_lint.py` | spec approval |
| `sdd-plan` | §3.4 | `plan.md` | `spec_lint.py --plan` | plan approval |
| `sdd-tasks` | §3.5 | `tasks.md` | `spec_lint.py --tasks` | quick check |
| `sdd-tests-from-ac` | §6 | red tests from the ACs | `trace_check.py` | approval of the locked tests (M, L) |
| `sdd-implement` | §4, phase 6 | code and commits | `verify.py` | PR review |
| `sdd-bugfix` | §6.1 | `docs/bugs/BUG-nnn.md`, test, fix | `bug_lint.py`, `verify.py` | expected and "must NOT change" |
| `sdd-review-diff` | §4, phase 7 | `review.md` | `diff_scope.py`, `trace_check.py`, `secrets_check.py` | review decision |
| `sdd-docs` | §6 | updated documentation | `docs_check.py` | review |
| `sdd-sync` | §4, phase 9 | area page, spec `implemented` | `sync_check.py` | review, then PR |
| `sdd-loop` | §7 | `PROMPT.md`, `progress.md`, command | `loop.py --dry-run` | permissions, cap, launch |

---

### sdd-next

- **When:** you do not know where to restart, or want to know where you are.
- **What it does:** runs `state.py`, reports infrastructure, specs (level, state, approvals, tasks, review and the next
  step of each), unverified bugs and the `NEXT` (next) line with its reason; asks whether to proceed. With several
  active specs and none tied to the branch (`choose`), it asks the user which one to work on and reruns with `--spec <id>`.
- **Does not:** modify files, start the next phase, or infer the state from the conversation.

### sdd-init

- **When:** once per project, before specs or code.
- **What it does:** detects operating system, stack and existing code; asks in a single message for what it cannot
  detect (real commands, Windows yes/no, CI provider); copies the 11 scripts into `scripts/` (each with the plugin
  version on line 2, for updates); adapts `STEPS` in `verify.py`, trying every command; creates `AGENTS.md`, `CLAUDE.md`
  (`@AGENTS.md`), `.gitattributes`, `.gitignore` entries, `.vscode/tasks.json`, `docs/constitution.md`, the `docs/*`
  folders, the CI workflow (with the PR "process checks" step), `CODEOWNERS` and the PR template; runs `verify` and
  `state`. It also explains how to update an already initialized project.
- **Rules:** never overwrites existing files (shows the difference, merges `tasks.json`); does not invent steps or
  tests; reports a red `verify` as it is.
- **Gate:** approval of `AGENTS.md`, constitution and `verify` steps.
- **Declared limits:** the generated CI has never been run; the hooks are not enabled.

### sdd-map-codebase

- **When:** at the start of work on existing code (brownfield).
- **What it does:** `scan_repo.py` for the inventory; baseline with `verify`; reads the code to fill in the map
  (modules, entry points, dependencies, zones not to touch, risks); every command in the table is executed; at least 5
  statements spot-checked in the code; proposes updates to `AGENTS.md`.
- **Writes only:** `docs/system/map.md` and, after confirmation, `AGENTS.md`.
- **Gate:** the user spot-checks the map.

### sdd-characterize

- **When:** before changing an existing area.
- **What it does:** tests that pin the **current** behaviour (even if wrong, marked as such); they must pass on the
  unmodified code; proves they can fail with a deliberate break and restore (`git restore`, empty `git diff`); records
  the tests in the area page.
- **Does not:** modify production code or fix the defects it finds.
- **Precondition:** clean `git status` on the area's files.

### sdd-spec

- **When:** from an idea to an approvable specification; also to complete a draft.
- **What it does:** reads `AGENTS.md`, constitution, the code involved and (brownfield) map and area page before asking
  anything; plays the request back in its own words; **asks** one question per message, the one that would most change
  what gets built; offers 2-3 options when the request admits really different outcomes for the user; writes `spec.md`
  with a proposed level (S, M, L with the criteria of playbook §2.1), verifiable requirements, Given/when/then ACs,
  mandatory non-scope, anti-goals, assumptions marked `[ASSUMPTION]`; `spec_lint.py` must pass; in brownfield it
  proposes `sdd-characterize` if the area has no tests.
- **Approval:** only with explicit confirmation **and** the approver's name; then `Status: approved` and the hash.

### sdd-plan

- **Precondition:** spec `approved` and lint green, level M or L (there is no plan at level S).
- **What it does:** read-only; `plan.md` with at least one discarded alternative, files in the format
  `- path: what changes` (including any dependency manifest), interfaces between components (produces / consumes), all
  ACs in the test strategy, the **review focus** (input classes no AC exercises, each with its test), risks, release and
  rollback; self-review against the spec (coverage, names, proportion); `spec_lint.py --plan` must pass. Flags ADR
  candidates without creating them.

### sdd-tasks

- **Precondition:** spec and plan approved (level S: spec only).
- **What it does:** `tasks.md` with one line per task in the format described in playbook §3.5 (action, `verify:`,
  `covers:`), tests before code, every AC covered, `T-SYNC` always present and `T-DOC` except at level S;
  `spec_lint.py --tasks` must pass.

### sdd-tests-from-ac

- **When:** for the tasks that write tests (called by `sdd-implement`) or on request.
- **What it does:** tests from the ACs, not from the code, with the ID in the name (`references/test-conventions.md`),
  plus the error cases and the plan's review focus cases; checks the test quality against the anti-patterns of the
  conventions (assertions on mocks, weak assertions, production methods only for tests); a minimal skeleton if needed;
  the tests must be **red for the right reason** (not import or syntax errors), with the failure message reported;
  `trace_check.py --warn-only`.
- **Rule:** red tests are committed alone, with the trailer `Test-Lock: T-nn` (the skeleton, if any, in an earlier
  commit). `diff_scope.py` reports any later change to those tests. At levels M and L the user reads the locked tests and
  only then the agent writes `tests approved: <name, date, sha>` on the task line; a new `Test-Lock` commit for the same
  task voids the approval.

### sdd-implement

- **Preconditions:** spec, plan and tasks valid and already merged into `main` (`spec_lint.py ... --base main`); feature
  branch; `verify` run before starting (baseline); at levels M and L the test task carries `tests approved:`.
- **Cycle:** first open `T-nn` or `T-Rnn` task → implement only that → `verify:` command and full `verify` → green:
  tick, commit with `Spec:` and `Agent:` trailers; red: at most 3 attempts, then stop and ask. Never modifies tests
  locked by a `Test-Lock` commit; stops if the change would exceed the spec level or needs an unplanned dependency.
- **Rulings:** every decision taken within the latitude of spec and plan goes into `progress.md` (`- T-nn: what — why —
  cost if wrong`); an ambiguous requirement is not a ruling, it stops the work.
- **Review findings (`T-Rnn`):** verified on the code before any change; a wrong finding is not fixed but recorded with
  its evidence in "Disputed review findings".
- **End:** when only `T-DOC` and `T-SYNC` remain, moves on to `sdd-review-diff`; does not declare the feature done.

### sdd-bugfix

- **When:** a defect to fix (not for new features). Trivial bugs: red test, fix, `verify`, no file.
- **What it does:** `docs/bugs/BUG-nnn-slug.md` with states `open → diagnosed → fixed → verified`, checked by
  `bug_lint.py` at every transition; reproduction (if it does not reproduce, it stops), definition of expected and "must
  NOT change" behaviour, red test, read-only diagnosis with the techniques of `references/debugging.md` (trace back to
  the source, one hypothesis at a time, bisect, flaky tests), minimal fix, non-regression test, closure.
- **Gate:** the user confirms expected and unchanged behaviour (step 2).
- **Rules:** one bug, one branch, one commit; no refactoring in the same commit; other defects found = new bugs.

### sdd-review-diff

- **Preconditions:** no open `T-nn` task, `verify` green, work committed. At level S the deterministic checks are enough,
  reported in the PR.
- **What it does:** `diff_scope.py` (including underestimated level, dependencies without a decision and approvals
  voided by new `Test-Lock` commits), `trace_check.py --junit` and `secrets_check.py`; independent review (Claude Code:
  subagent `sdd-reviewer`, without Bash, that receives diff and outputs in the message; GitHub Copilot: the same agent as
  the custom agent `.github/agents/sdd-reviewer.agent.md`; otherwise a new session with spec, plan, script outputs and
  diff); writes `review.md` with outcome, problems with file and line, refutation attempts.
- **Gate:** the **decision belongs to the user** (`Decided by`; at level L also `Human diff review`, after the
  user has read the diff); with `non-compliant` every `high`/`medium` problem becomes a `T-Rnn` task in `tasks.md`,
  executed by `sdd-implement` or the loop; once the `T-R` tasks are closed, the review is repeated.
- **Does not:** modify code.

### sdd-docs

- **Preconditions:** `T-nn` tasks closed, review valid and not `non-compliant`.
- **What it does:** updates README, API documentation and migration notes from the spec and the real code; proposes ADRs
  (creates them after confirmation); runs the examples (Python blocks marked `# docs-check: run` with
  `docs_check.py --run-examples`, others by hand); `docs_check.py` checks the links; ticks `T-DOC`.

### sdd-sync

- **Preconditions:** review with `Decided by` filled in (level S: `diff_scope.py` and `trace_check.py` green), `T-DOC`
  closed.
- **What it does:** compares spec and real behaviour: every gap is either a bug (`sdd-bugfix`) or a requirement change to
  approve, never hidden; creates/updates `docs/system/<area>.md` (optional at level S); sets `Status: implemented`; ticks
  `T-SYNC`; `sync_check.py --junit` must pass; proposes lessons for `AGENTS.md` and ADRs.

### sdd-loop

- **When:** many small, independent tasks. For few or tightly coupled tasks, `sdd-implement` is better.
- **What it does:** prepares `PROMPT.md` and `progress.md`, proposes the example permissions (`settings.loop.json`:
  no writes to `scripts/`, `AGENTS.md`, `.github/`, spec, plan and review; no push, no network), agrees on `--max`,
  `--stall` and `--timeout`, runs `loop.py --dry-run`, shows the safety checklist and the command.
- **Does not:** **launch the loop**: the user launches it in an isolated terminal, after explicit approval.
