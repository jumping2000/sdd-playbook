- Based on plan: <hash of the approved plan>

- [ ] T-01 Write the tests for AC-001 and AC-002 — verify: `<targeted test command>` (expected: red for the right reason) — covers: AC-001, AC-002, AC-003
- [ ] T-02 Implement <small unit> — verify: `<targeted test command>` — covers: AC-001, AC-002, AC-003
- [ ] T-DOC Update README/API docs and run the examples written — verify: `<command, if any>`
- [ ] T-SYNC Reconcile spec and docs/system/<area>.md with the real behaviour; then set Status = implemented in the spec

<!-- Levels M and L: after the Test-Lock commit of an "expected: red" task, and only after the human has read the tests,
append to its line: — tests approved: <name, yyyy-mm-dd, sha of the Test-Lock commit> -->

## Fixes from review
<!-- Only after a "non-compliant" review: one task per high/medium problem, for example
- [ ] T-R01 <problem from review.md> — verify: `<command>` — covers: AC-nnn (optional) -->
