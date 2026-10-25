# Script and hook reference

*Versione italiana: [scripts_IT.md](scripts_IT.md)*

All scripts live in `skills/sdd-init/scripts/` and `sdd-init` copies them into the project's `scripts/`. They are
Python, standard library only, with no shell commands, and behave the same on Windows, Linux and macOS. Run them from the
**project root**. Line 2 of every script carries the plugin version (`# sdd-playbook: <version>`), to know which copies
to update (`sdd-init`, section "Updating an already initialized project"). Exit codes: `0` ok, `1` check failed, `2` wrong usage or
missing precondition. Output is always UTF-8, even on a Windows console in cp1252. Messages are in English.

The file formats the scripts read are described in [architecture.md](architecture.md#file-contracts).

| Script | Used by | Purpose |
|---|---|---|
| `verify.py` | all | the project's definition of "done" |
| `state.py` | `sdd-next` | state and next phase |
| `spec_lint.py` | spec, plan, tasks, implement, loop | lint of spec, plan and tasks |
| `trace_check.py` | tests-from-ac, review-diff | AC → test traceability |
| `bug_lint.py` | bugfix | completeness of a bug file |
| `diff_scope.py` | review-diff, sync, loop | changes vs plan, forbidden zones, locked tests and level |
| `scan_repo.py` | map-codebase | inventory of a codebase |
| `docs_check.py` | docs | links and examples |
| `sync_check.py` | sync | closure of a feature |
| `secrets_check.py` | review-diff, loop, `verify` | secrets in files |
| `loop.py` | loop | external autonomous loop |

---

### verify.py

Runs the `STEPS` (format, lint, types, tests, secrets) and prints one line per step plus `VERIFY: GREEN|RED -> ...`
(green/red). The project adapts it: each command is a list of arguments, tried by hand before being registered. The
template's test step also writes a JUnit report (`reports/junit.xml`) for `trace_check.py --junit`.

```
python scripts/verify.py                 # all steps, stops at the first red
python scripts/verify.py --fast          # only the steps marked fast (format, lint, secrets)
python scripts/verify.py test lint       # only the listed steps
python scripts/verify.py --keep-going    # does not stop at the first red
```

Exit: `0` green, `1` at least one step red or command not found, `2` no step selected. Sets `PYTHONUTF8=1`.

### state.py

Read-only. Reports infrastructure (`AGENTS.md`, `verify.py`, CI, `docs/`), presence of existing code and of the map,
state and level of every spec with its next step (`-> skill`), unverified bugs, current branch and the `NEXT`
(next) line. Order of the suggestion for a spec: `sdd-spec` (draft, `in-revision`, lapsed approval) → `sdd-plan`
(missing, to approve or lapsed) → `sdd-tasks` (missing or based on another plan) → `sdd-implement` (open `T-nn`/`T-Rnn`
tasks) → `sdd-review-diff` (missing review; with `non-compliant`: create the `T-R` tasks, or repeat the review once they
are closed) → `sdd-docs` (`T-DOC` open) → `sdd-sync`. First of all `sdd-init` and, in brownfield without map or specs,
`sdd-map-codebase`. `scripts/`, `docs/`, `.github/` and `.vscode/` do not count as existing code.

**Levels** (playbook §2.1). Level S: after the approved spec `sdd-tasks` (no plan), then `sdd-implement`, `sdd-docs`
if `T-DOC` is open and `sdd-sync`; `review.md` counts only if present and `non-compliant`. Levels M and L: a closed
"expected: red" test task without `tests approved:` leads to `sdd-tests-from-ac` before implementation. Level L: after
an accepted review, `- Human diff review:` is also required in `review.md`, otherwise `sdd-review-diff`. Without
the `- Level:` field the spec counts as M.

**Several active specs.** `NEXT` refers to the spec given with `--spec <id>` (folder name or title ID), the one whose
folder name appears in the current branch (`feat/2026-10-24-export-csv`), or the only active one. Otherwise it reports
`choose` (choose) with the list of specs and their step: the choice belongs to the user.

```
python scripts/state.py [--json] [--spec <id>] [root]
```

### spec_lint.py

```
python scripts/spec_lint.py <spec.md> [--plan <plan.md>] [--tasks <tasks.md>] [--base <ref>]
python scripts/spec_lint.py <file.md> --hash
```

**Approval.** `--hash` prints the hash of the file body (from the first `## ` section on, line endings and trailing
spaces normalized, plus the level if the spec declares one: lowering it after approval voids the approval), to write in
`- Hash:` after approval. An `approved`/`implemented` spec without a hash, or with a hash that no longer matches the
content, is an error. An approved plan must have a valid `- Hash:` and `- Based on spec:` equal to the current hash of
the spec: if the spec changes, the plan lapses. With `--base <ref>` spec and plan must exist on `<ref>` and be identical
to the working copy: merging the design PR into a protected branch is the approval the agent cannot give itself
(playbook §1.2).

| Mode | Errors detected |
|---|---|
| spec | invalid state (`draft`, `approved`, `in-revision`, `implemented`, `superseded`); level other than S, M, L (warning if missing: counts as M); title without ID `# SPEC-<id>:`, invalid date or ID different from the folder name; `in-revision` without an entry in `## Revisions`; missing sections; duplicate REQ/AC IDs; REQ without AC; AC citing a non-existent REQ; non-scope missing or a placeholder; if `approved`/`implemented`: missing approver, missing or mismatching hash, open questions (warning if `[ASSUMPTION]` remain) |
| `--plan` | missing `## Test strategy` section; spec ACs missing from that section (exact ID: `AC-001` does not match `AC-0011`); approved plan with invalid hash or based on another version of the spec; warning if the plan is not approved |
| `--base` | spec or plan missing on `<ref>` or different from the version on `<ref>` |
| `--tasks` | no tasks; `T-nn` tasks without `verify:` or `covers:` or with `<...>` placeholders; `T-Rnn` tasks without `verify:` or with placeholders (`covers:` optional); duplicate IDs; missing `T-SYNC`, or missing `T-DOC` except at level S; AC not covered by any task |
| `--plan` and `--tasks` together | tasks whose `- Based on plan:` differs from the plan hash (warning if the field is missing) |

The approval of locked tests (`tests approved: <name, yyyy-mm-dd, sha>`) is valid only with name, date and the SHA of the
`Test-Lock` commit; "expected: red" is matched case-insensitively.

### trace_check.py

```
python scripts/trace_check.py <spec.md> [--tests DIR ...] [--junit FILE|DIR ...] [--warn-only]
```

Looks for AC citations in test files (default folders: `tests`, `test`, `__tests__`, `spec`, `src/test`; extensions of
the most common languages) and attributes them to a spec, because ACs restart from AC-001 in every spec. The spec ID comes
from the title `# SPEC-<id>: ...` (date + slug, or a number in older projects) and is compared in normalized form (`_` as
`-`, numbers without leading zeros): `SPEC-2026-10-24-export` does not match `SPEC-2026-10-24-export-csv`.
- `SPEC-2026-10-24-export-csv/AC-001` (in function names `SPEC_2026_10_24_export_csv_AC_001`; for numbers also
  `SPEC-001-AC-001`, `SPEC001_AC001`) counts for that spec;
- `AC-001`, `AC_001`, `AC001` (also Go's `TestAC001`) in a file that names a single spec (e.g. `# SPEC-2026-10-24-export-csv`
  at the top) counts for that spec: it is the recommended way with date IDs;
- `AC-001` in a file that names no spec counts only if `docs/specs/` contains a single spec; otherwise it is
  **ambiguous**, does not count and is reported as a warning;
- citations on lines with `TODO`, `FIXME` or `XXX` do not count and are reported.

For every AC it prints the number of references or `NO TEST`, reports REQs with no tested AC and, as
warnings, ACs attributed to the spec but missing from it, ambiguous citations and ignored ones. Exit `1` if an AC has no
test (unless `--warn-only`), `2` if no test folder is found.

**`--junit`: executed tests, not just cited ones.** With one or more JUnit XML reports (files, or folders whose `*.xml`
are all read) every AC needs at least one test case **executed and passed** and none failed; skipped cases do not count.
A case counts for an AC if it cites it in qualified form in the name or `classname`, or in short form when it belongs to
a test file attributed to the spec or the project has a single spec. The file of a case is the one whose path matches
`file` or `classname` the longest (`tests.a.test_api` ↔ `tests/a/test_api.py`, `com.acme.ExportTest` ↔
`.../com/acme/ExportTest.java`): files with the same name in different folders are not confused, and on a tie between
files of different specs the case does not count. Unreadable report or `--junit` without a value: exit `2`. `verify`
writes the report (see `references/stacks.md` in `sdd-init`).

### bug_lint.py

```
python scripts/bug_lint.py docs/bugs/BUG-001-example.md
```

Requirements grow with the state: `open` (open) → reproduction filled in; `diagnosed` (diagnosed) → expected and
actual, "must NOT change", root cause, path of the red test; `fixed` (fixed) → minimal fix described and
non-regression test indicated; `verified` (verified) → all "Closure" items ticked. `<...>` placeholders and
empty labels do not count as content.

### diff_scope.py

```
python scripts/diff_scope.py docs/specs/001-x [--base main] [--strict]
```

Computes the files changed since the merge-base with the base ref (default: the first existing among `main`, `master`,
`origin/main`, `origin/master`), including uncommitted and untracked files. Renames count with both the source and the
target path (`--no-renames`); generated files (`__pycache__/`, `*.pyc`, `reports/`) do not count. `AGENTS.md` and the spec
level are read **from the merge-base** when they exist there: the branch cannot loosen them (if the branch changes
`AGENTS.md` there is a warning). `AGENTS.md` entries count as paths (text in backticks or first word); entries that do not
look like paths are reported and ignored. It reports:
- **error** (exit 1): files in the zones of the `- Do not modify:` lines of `AGENTS.md` (all of them, not just the first);
- **error** (exit 1): locked test files changed after locking. A commit with the trailer `Test-Lock: T-nn` locks its test
  files (folders `tests`, `test`, `__tests__`, `spec` or names like `test_*.py`, `*_test.go`, `*.test.ts`,
  `*Test.java`); a later change in a commit without the same trailer, or uncommitted, is a violation. Non-test files of a
  `Test-Lock` commit (e.g. a skeleton) are not locked and are reported as a warning;
- **warning** (error with `--strict`): files outside the plan (excluding `docs/specs/<this spec>/`, `docs/system/`,
  `docs/bugs/`, `docs/adr/`). The plan includes the lines of "Componenti e file" (path = first word or text in backticks,
  so `- src/a.py (new): ...` means `src/a.py`) and the "Where" column of the test strategy;
- **error** (exit 1): **underestimated level** (playbook §2.1). A file in the `- Sensitive areas:` lines of `AGENTS.md`
  requires L; a change to a dependency manifest or lockfile (`package.json`, `pyproject.toml`, `requirements*.txt`,
  `go.mod`, `*.csproj`, the lockfiles, ...) or more than 3 production files (tests, `docs/` and `*.md` excluded) require
  at least M. The declared level comes from the spec's `- Level:` (M if missing); at level S without a plan, the plan
  comparison is skipped;
- **error** (exit 1): **dependencies without a decision**: a changed manifest or lockfile that the plan does not list (a
  lockfile counts if the plan lists its manifest in the same folder), in a diff that does not **add** an ADR in
  `docs/adr/` (README and index files do not count). Playbook §8: new dependencies only with an ADR or in the approved plan;
- **error** (exit 1): **voided test approvals**: the SHA in `tests approved: <name, date, sha>` is not a `Test-Lock`
  commit of the branch for that task (rebase, amend), or another `Test-Lock` commit for the same task follows it;
- **info**: planned paths not touched.

Paths: exact, folders (prefix) or globs; the `./` prefix is ignored, leading dots (`.github/`) are kept. Exit `2` if it is
not a git repository or the base ref is missing.

### scan_repo.py

```
python scripts/scan_repo.py [root] [--json]
```

Read-only inventory: manifests and stack, languages (files and lines), top-level structure, test folders, CI, likely
entry points, documentation. Uses `git ls-files` when available. It is an inventory, not understanding.

### docs_check.py

```
python scripts/docs_check.py [paths...] [--run-examples]
```

Default: `README.md` and `docs/`. Checks relative links and images (ignores code, external URLs, pure anchors). With
`--run-examples` it runs the Python blocks whose first non-empty line is `# docs-check: run` (60 s timeout, must exit
0). Other blocks are not run.

### sync_check.py

```
python scripts/sync_check.py docs/specs/001-x [--area docs/system/<area>.md] [--tests DIR ...] [--junit FILE|DIR ...]
```

Checks that: the spec is valid with `Status: implemented`; no task is open; `review.md` has a valid outcome other than
`non-compliant` and `Decided by` filled in; an area page exists (or the one given) with the required sections,
"Ultimo allineamento" filled in and the spec among the "Specifiche collegate"; every AC is cited in a test **of this
spec**, with the rules of `trace_check.py` (if tests are missing and there are ambiguous citations, the error says so).
Level S: `review.md` and area page optional (if `review.md` exists, it is checked). Level L: `review.md` must also have
`- Human diff review:` filled in. At levels M and L closed test tasks ("expected: red") carry `tests approved:`.
With `--junit` ACs must be verified by the report of executed tests, as in `trace_check.py`; at level L the report is
mandatory. The spec folder may also follow the options.

### secrets_check.py

```
python scripts/secrets_check.py [--base <ref>]     # branch files: changed since the merge-base, plus untracked
python scripts/secrets_check.py --all              # all tracked files (the "secrets" step of verify)
python scripts/secrets_check.py <file or folder> ...
```

Error (exit 1): private keys (`-----BEGIN ... PRIVATE KEY-----`), tokens with a recognizable format (AWS, GitHub, GitLab,
Slack, Stripe live, Google, Anthropic, OpenAI) and `.env` files in the repository (not `.env.example`, `.sample`,
`.template`, nor `.env.local.example` and similar). Warning: passwords, secrets, tokens or keys assigned to a literal
string of at least 8 characters, obvious placeholders excluded. The value found is never printed. A line with
`secrets-check: ignore` is not checked (justify the false positive in the review); files that cannot be annotated (PEM
fixtures, a `.env.development` versioned by convention) go into `.secrets-ignore`, one glob per line. Non-ASCII paths are
read correctly (`core.quotePath=false`). Skips binary files and files over 1 MB. Exit `2` without git or base ref (use
`--base`, `--all` or paths). It is a fast net, not a history scan: for that, use a dedicated tool in CI.

### loop.py

```
python scripts/loop.py docs/specs/001-x [--max 15] [--stall 3] [--timeout 1800] [--agent "claude -p"]
                                        [--junit reports/junit.xml] [--allow-main] [--allow-red-baseline] [--dry-run]
```

Reads `PROMPT.md` from the spec folder and passes it to the agent on stdin. After every iteration it runs `verify`. It
stops with exit `0` if `verify` is green, no `T-nn` or `T-Rnn` task is open (`T-DOC` and `T-SYNC` stay out) **and the
final checks pass**: `spec_lint.py` on spec, plan and tasks, `trace_check.py` on the spec, `diff_scope.py` on the folder
and `secrets_check.py`, when present in `scripts/`. The agent ticks the boxes; these checks do not depend on it. If
`diff_scope` cannot compute the diff (exit `2`, e.g. no base ref) it is a warning. It stops with exit `1` at the `--max`
cap or after `--stall` iterations without changes (tasks.md, git HEAD, **content** of tracked and untracked changes,
excluding generated files such as `__pycache__/` and `reports/`: an agent working on the same file is not stalled, a
report that changes at every `verify` is not progress). With `--junit` it warns if the report is not ignored by git. Each
iteration lasts at most `--timeout` seconds: beyond that the agent is terminated and the loop continues; a non-zero exit
code is reported as a warning. It refuses to start (exit `2`) on `main`/`master` (unless `--allow-main` in isolated
environments) and with `verify` already red, except in the red phase (the last closed `T-nn` task is "expected: red") or
with `--allow-red-baseline`.
**Tests to approve** (levels M and L): if after an iteration an "expected: red" test task is closed without
`tests approved:`, the loop stops with exit `1` so that the human can read the locked tests; with an approval already
pending it does not start (exit `2`). With `--junit` the final `trace_check.py` uses the report of executed tests.
`--dry-run` checks the preconditions without launching the agent and shows whether there is a red phase. It never pushes.
Agent permissions and non-interactive mode are configured separately: `skills/sdd-loop/references/settings.loop.json` is
an example allowlist and deny-list for Claude Code (it also denies writes to `scripts/`, `AGENTS.md`, `.github/`, spec,
plan and review: the loop's own checks and rules), passed with `--agent "claude -p --settings <file>"` (verify the flag on
your version).

---

## Optional hooks (Claude Code only)

They are not ported to Codex and GitHub Copilot (Copilot hooks use a different format and have no blocking stop event).

They load with the plugin (`hooks/hooks.json`) but stay **inactive** until you set the environment variable. They are a
minimal safety net, not a sandbox: they do not replace permissions, allowlists and isolation.

Both start from `hooks/run.sh` (`sh run.sh <script.py> <variable>`). The launcher exits `0` immediately if the variable is
not `1`, so an inactive hook does not need Python. When active it uses the first of `python3`, `python` and `py -3` that
really is Python 3.8+ (it discards the Microsoft Store aliases and Python 2): on a clean Ubuntu only `python3` exists.
Without Python 3 it exits `1` with a message, i.e. a visible but non-blocking error.

### `Stop` hook — `hooks/stop_verify.py`

Enabled with `SDD_ENFORCE_VERIFY=1`. If `scripts/verify.py` exists and is red, it exits with code 2 and returns the last
30 lines to the agent, which cannot declare the work finished. It blocks up to `SDD_STOP_MAX` times in a row per session
(default 3; counter per `session_id` in a private user folder, `%LOCALAPPDATA%\sdd-playbook` or
`~/.cache/sdd-playbook`, opened without following symbolic links and reset when `verify` turns green), then lets the
agent stop with a warning for the user (`systemMessage`). Without `session_id` it blocks only once (`stop_hook_active`).
It does nothing if the project has no `verify.py`, or if a spec is in the **red phase** (in `docs/specs/*/tasks.md` the last
closed `T-nn` task is marked "expected: red" and the next one is open): there, red tests are the expected result.
`SDD_VERIFY_ARGS` narrows the verification (e.g. `--fast`).

### `PreToolUse` hook — `hooks/pretool_guard.py`

Enabled with `SDD_GUARD=1`. It analyses every Bash and PowerShell command by segments (`;`, `&&`, `||`, `|`) and words,
not with a single regular expression. It blocks:
- forced or destructive pushes: `--force`, `-f` (also inside `-uf`), `--force-with-lease`, refspecs with `+` (`+main`),
  `--delete`/`-d`, `:branch` refspecs, `--mirror`;
- `git reset --hard`, `git clean -f`, also with global options (`git -C . reset --hard`) or in another order
  (`git reset HEAD~1 --hard`, `git clean -d -f`);
- recursive deletes: `rm` with `-r`/`-R`/`--recursive` in any form (`rm -r -f`, `rm --recursive --force`), `git rm -r`
  without `--cached`, `find -delete`, `Remove-Item -Recurse` (also abbreviated), `rd /s`, `del /s|/f|/q`,
  `shutil.rmtree`;
- download-and-execute (`curl|wget ... | sh`, `iwr ... | iex`);
- any reference to a `.env` file, even attached to something else (`cat .env>x`, `cat <.env`, `open('.env')`, `cp`,
  `Select-String`; upper case and NTFS streams such as `.env::$DATA`), except `.env.example`, `.sample`, `.template` and
  commands on `.gitignore` (appending, `grep` in the file, `git check-ignore`).
For the Read and Grep tools it blocks `.env` files (also `glob: .env*`). With unreadable JSON or a `tool_input` that is not
an object it **blocks** (fail-closed). It exits with code 2 and a message. It remains a minimal net: a sufficiently
convoluted command bypasses it, which is why the real control is the agent's native permissions and isolation.

**Not verified:** the behaviour in a real Claude Code session (exit code 2 as a block, format of the input JSON, shell
used for the command on Windows). The scripts and `run.sh` are tested with the expected input on Linux and Windows (with
the `sh` of Git for Windows); if Claude Code on Windows cannot find `sh`, the hooks do not start.
