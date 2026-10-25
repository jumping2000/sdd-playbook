## PR type
- [ ] **Design**: spec, plan and tasks (the merge is the approval)
- [ ] **Implementation**: code and tests of a spec already merged into main
- [ ] **Bug**: `docs/bugs/BUG-...`

Spec: `docs/specs/<id>/`

## Evidence (pasted output, not a summary)
- `python scripts/verify.py`:
- `python scripts/spec_lint.py <spec> --plan <plan> --tasks <tasks> --base main`:
- `python scripts/trace_check.py <spec> --junit reports/junit.xml`:
- `python scripts/diff_scope.py <spec-dir>`:

## For the approver
- [ ] Design: verifiable ACs, concrete non-scope, no open questions
- [ ] Implementation: I read the `Test-Lock` commits (the tests that pin the ACs) before the rest of the diff, and the test tasks carry `tests approved:`
- [ ] No file in a forbidden zone and no locked test changed (`diff_scope.py`)
- [ ] `review.md` present with outcome and decision
