# Script and hook reference

*Versione italiana: [scripts_IT.md](scripts_IT.md)*

All scripts live in `skills/sdd-start/scripts/` and `sdd-start` copies them into the project's `scripts/`. They are
Python, standard library only, with no shell commands, and behave the same on Windows, Linux and macOS. Run them from
the **project root**. Line 2 of every script carries the plugin version (`# sdd-playbook: <version>`), to know which
copies to update (`sdd-start`, "Updating"). Exit codes: `0` ok, `1` check failed, `2` wrong usage or missing
precondition. Output is always UTF-8, even on a Windows console in cp1252. Messages are in English.

The file formats the scripts read are described in [architecture.md](architecture.md#file-contracts).

| Script | Used by | Purpose |
|---|---|---|
| `verify.py` | all | the project's definition of "done" |
| `spec_lint.py` | start, plan, task | lint of the spec and of the plan with its tasks |
| `trace_check.py` | task, bugfix | AC → test traceability, per task or for the whole feature |
| `diff_scope.py` | task, parallel | the task branch: forbidden zones, locked tests, scope, sensitive areas, size |
| `state.py` | next, task, parallel | the next step and the ready tasks |
| `docs_check.py` | task, map | links, Mermaid diagrams, the five diagrams of `docs/system/`, examples |
| `secrets_check.py` | `verify` | secrets in files |
| `scan_repo.py` | map | inventory of a codebase |

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

### spec_lint.py

```
python scripts/spec_lint.py <spec.md> [--plan <plan.md>]
```

| Mode | Errors | Warnings |
|---|---|---|
| spec | `- Status:` not one of `draft`, `approved`, `implemented`, `superseded`; title without `# SPEC-<id>:`, invalid date or ID different from the folder name; missing sections (Problem and goal, Scope, Requirements, Acceptance criteria, Open questions); duplicate REQ or AC IDs; REQ without AC; AC citing a REQ that does not exist; non-scope missing or a placeholder; an `approved` or `implemented` spec with blocking open questions (or without `blocking: yes|no`) | anti-goals or `## Current behaviour and impact` missing; vague words in REQs and ACs ("fast", "appropriate", "should", "etc", ...); non-blocking open questions and `[ASSUMPTION]` left in an approved spec |
| `--plan` | `## Flowchart` missing or without a ```` ```mermaid ```` flowchart; `## Tasks` missing or empty; a task line with a placeholder, without `covers:` (or covering an AC not in the spec), without `files:`, `verify: `<command>`` or `depends:`, depending on a task that does not exist, or in a dependency cycle; duplicate task IDs; an AC of the spec covered by no task; `## Review focus` missing or not filled in (`- none` is valid) | `## Approach` missing; more than 8 tasks (split the feature) |

There is no field to sign: the approval of spec and plan is the merge of the design PR, recorded by git. The same
module checks the `## Diagrams` section of the documentation pages for `docs_check.py` (five diagrams, each a Mermaid
block of its type or `- n/a: <reason>`; the flowchart always applies).

### trace_check.py

```
python scripts/trace_check.py <spec.md> [--task T-nn] [--tests DIR ...] [--junit FILE|DIR ...] [--warn-only]
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
writes the report (see `references/stacks.md` in `sdd-start`).

**Other languages and declared test files.** Test files are searched in the test folders with the common extensions
(Python, JavaScript/TypeScript, Java, Kotlin, Scala, C#, F#, Go, Ruby, PHP, Rust, C/C++, Swift, Dart, Elixir, shell,
bats, PowerShell, Gherkin, Robot, HCL, YAML), plus the paths or globs of `- Test files:` in `AGENTS.md`. The short
citation also accepts `ac_001` (Rust and other snake_case names) and the qualified one is case-insensitive.

**`--task T-nn`: the check of a task's PR.** Only the ACs the task covers (`covers:` in the `plan.md` next to the spec)
must have tests (executed and passed with `--junit`); the ACs of later tasks are not reported. Without `--task` every
AC of the spec, and every REQ needs a tested AC: the check of the whole feature, run by its last task. An unknown task:
exit `2`.

### diff_scope.py

```
python scripts/diff_scope.py docs/specs/<id> --task T-nn [--base main] [--strict]
python scripts/diff_scope.py docs/specs/<id> [--base main] [--strict]        # the whole branch
```

Computes the files changed since the merge-base with the base ref (default: the first of `main`, `master`,
`origin/main`, `origin/master`), uncommitted and untracked files included; generated files (`__pycache__/`, `*.pyc`,
`reports/`) do not count. `AGENTS.md` is read **from the merge-base** when it exists there: the branch cannot loosen
it. It reports:
- **error** (exit 1): files in the `- Do not modify:` zones of `AGENTS.md`;
- **error** (exit 1): **locked tests** changed after locking. A commit with the trailer `Test-Lock: T-nn` locks its
  test files (folders `tests`, `test`, `__tests__`, `spec` or names like `test_*.py`, `*_test.go`, `*.test.ts`,
  `*Test.java`); a later change in a commit without the same trailer, or uncommitted, is a violation. Non-test files of
  a `Test-Lock` commit are not locked (warning);
- **warning** (error with `--strict`): files outside the task's `files:` (all the tasks without `--task`), excluding
  the spec folder, `docs/system/`, `docs/bugs/`, `docs/adr/` and the process tooling (the playbook scripts in
  `scripts/`, `AGENTS.md`, `CLAUDE.md`, `.github/`, `.vscode/`, git files);
- **warning**: a dependency manifest or lockfile changed (a new dependency is asked first, and said in the PR);
- **warning**: more than 400 changed lines outside tests and docs (the PR is hard to read: consider splitting);
- **`SENSITIVE:` line**: files in the `- Sensitive areas:` of `AGENTS.md`, to copy into the PR description: the human
  reads their diff before the merge. Not an error.

Test files are recognized by folder (`tests`, `test`, `__tests__`, `spec`) and by name (`test_*`, `*_test.*`,
`*.test.*`, `*.spec.*`, `*Test.*`, `*Tests.*`, `*.bats`, `*.tftest.hcl`); manifests by name, for the common ecosystems
(npm, pip, uv, Poetry, Go, Cargo, Maven, Gradle, NuGet, Bundler, Composer, Mix, Pub, SwiftPM, Deno, Bun, conda,
Terraform, Helm, Conan, vcpkg). A project adds its own with `- Test files: a, b` and `- Dependency manifests: a, b` in
`AGENTS.md`.

Paths: exact, folders (prefix) or globs (`**/` also matches no folder); the `./` prefix is ignored, leading dots
(`.github/`) are kept. Exit `2` if it is not a git repository, the base ref is missing or the task does not exist.

### state.py

```
python scripts/state.py [--json] [--spec <id>] [root]
```

Read-only. It reads `AGENTS.md` and `scripts/verify.py` (initialization), the specs in `docs/specs/`, and, from git,
the version of spec and plan on `main` (or `master`; without git the working copy counts as `main`). The next step:

```
no AGENTS.md or scripts/verify.py ................... sdd-start (initialization)
existing code, no map and no spec ................... sdd-map
no active spec ...................................... sdd-start (next idea)
several active specs, no choice ..................... choose (--spec <id>, or the spec's branch)
--- for the chosen spec ---
Status draft (or missing) ........................... sdd-start (confirm the spec)
no plan.md .......................................... sdd-plan
spec or plan not on main yet ........................ sdd-plan (open and merge the design PR)
spec revised outside a task branch .................. sdd-start (confirm, revise the plan, merge the revision PR)
plan revised outside a task branch .................. sdd-plan (confirm and merge the revision PR)
two or more ready tasks with disjoint files ......... sdd-parallel (at most 3, named)
one ready task ...................................... sdd-task (named)
open tasks, none ready .............................. sdd-task (merge the open PRs first)
all tasks merged, Status not implemented ............ sdd-task (close the feature)
```

A task is **done** when its box is ticked in the plan **on `main`** (its PR was merged), **ready** when it is not done
and all its dependencies are done. A spec with `Status: implemented` or `superseded` is no longer active. Open bugs
(`docs/bugs/*.md` not `fixed` or `verified`) are listed for `sdd-bugfix`. `--json` prints the whole state.

### docs_check.py

```
python scripts/docs_check.py [paths...] [--run-examples]
```

Default: `README.md` and `docs/`. Checks relative links and images (ignores code, external URLs, pure anchors). With
`--run-examples` it runs the Python blocks whose first non-empty line is `# docs-check: run` (60 s timeout, must exit
0). Other blocks are not run.

**Diagrams.** Every ```` ```mermaid ```` block must start with a known Mermaid diagram type (after `%%` comments and
the `---` front matter) and have a body; the rest of the syntax is not checked: preview the diagram (GitHub, GitLab,
VS Code with a Mermaid extension). Every page of `docs/system/` (area pages and map) needs the `## Diagrams` section with
the five diagrams, each drawn or `- n/a: <reason>` (the flowchart always applies).
Code fences close only on a fence of the same character at least as long as the opening one, so a template shown in a
```` ```` ```` block keeps its inner blocks.

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

### scan_repo.py

```
python scripts/scan_repo.py [root] [--json]
```

Read-only inventory: manifests and stack, languages (files and lines), top-level structure, test folders, CI, likely
entry points, documentation. Uses `git ls-files` when available. It is an inventory, not understanding.

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
It does nothing if the project has no `verify.py`, or in the **red phase** of a task: the last commit of the branch
carries the trailer `Test-Lock: T-nn` (the red tests were just locked and the implementation has not started): there,
red tests are the expected result.
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
