---
name: sdd-tests-from-ac
description: Use this skill to write tests from the spec's acceptance criteria (not from the code), citing the AC IDs, and to check that they fail for the right reason before implementation; it applies to the test tasks of tasks.md.
---

# Tests from acceptance criteria

Playbook §6. Preconditions: spec and plan approved (`python scripts/spec_lint.py <spec> --plan <plan>` without errors);
the test task is listed in `tasks.md`. Naming conventions: `references/test-conventions.md`.

## Steps

1. **Start from the ACs the task covers**, not from the implementation. In brownfield read only the interfaces to call;
   do not copy the existing logic into the tests.
2. **One test per AC, plus the error cases** present in the ACs. ACs restart from AC-001 in every spec: declare the spec
   at the top of the test file (`# SPEC-2026-10-24-export-csv`) and cite the AC in the name or a comment (`AC-001`), or
   use the qualified form `SPEC-<id>/AC-001`, so that `trace_check.py` attributes it to the right spec. A
   `TODO AC-001` does not count as a test. Do not invent requirements: a case not covered by the spec is a question for
   the user.
3. **Minimal skeleton** of the code under test, only if needed to run the tests (a signature raising a "not
   implemented" error): the goal is that the tests fail on behaviour, not on an import.
4. **Check the test quality** against "What makes a test worth locking" in `references/test-conventions.md`: assertions
   on the observable outcome with exact values from the ACs, mocks only at the boundaries. Include the plan's Review
   focus cases assigned to this task.
5. **Run the task's tests:** they must be **red for the right reason**. Report the failure message of each one. A
   syntax, import or name error is not the right reason: fix the test.
6. **Check traceability:** `python scripts/trace_check.py <spec> --warn-only` (the ACs of later tasks will still show
   no tests).
7. **Lock the tests with a commit.** If you wrote a skeleton, commit it first, separately. Then commit **only the test
   files** with the trailers `Test-Lock: T-<nn>`, `Spec: SPEC-<id>` and `Agent: <name and version>`, and tick the
   task. From now on `diff_scope.py` reports as an error any later change to those tests: the implementation must make
   them pass without touching them. The branch CI stays red until the implementation task: it is expected, and the
   "red phase" (last closed task marked "expected: red") is recognized by the `Stop` hook and by `loop.py`. If the user
   has not authorized commits, propose the messages and do not commit.

## Rules

- Do not touch production code beyond the skeleton of step 3.
- Do not weaken or remove existing tests.
- A locked test that turns out to be wrong is fixed only with the user's agreement, in a new `Test-Lock` commit, and
  the fix must be justified in `review.md`.
- At the end of all the test tasks, `python scripts/trace_check.py <spec>` (without `--warn-only`) must pass once the
  code is implemented.

## STOP

Show the AC → test list, the failure messages and the SHA of the `Test-Lock` commit. When the task review applies
(level L, or M with `- Task review: on`), run it first on the `Test-Lock` commit (`review_package.py <spec-dir> T-<nn>`,
see `sdd-implement`): the reviewer checks that the tests derive from the ACs and avoid the anti-patterns, and its
verdict goes to the user together with the tests. At levels M and L ask the user to
**read the locked tests** (the diff of that commit), with the approval checklist of `references/test-conventions.md`:
they define "done" for the implementation. Ask it as a gate with options (guide: search for
`**/sdd-init/references/interaction.md`); only after the user selects an approval, record it with
`python scripts/approve.py tests <spec-dir> T-<nn> --by "<selected name>" --commit`, which appends
`— tests approved: <name, yyyy-mm-dd, sha>` with the SHA of the task's last `Test-Lock` commit (a new `Test-Lock`
commit for the same task voids the approval: `diff_scope.py`); until then `state.py` does not point to implementation
and `loop.py` stops. Never record it on your own initiative. At level S a spot check is enough.
