---
name: sdd-docs
description: Use this skill to carry out the T-DOC task: update README, API documentation and ADRs from the spec and the real code, running the examples you write and checking links with docs_check.py.
---

# Documentation (T-DOC)

Playbook §6 and §4 (phase 8). The source is **the spec and the real code**, not memory.

## Preconditions

- `T-nn` tasks completed and `review.md` with a valid outcome other than `non-compliant`.
- `T-DOC` is open in `tasks.md`.

## Steps

1. **Read** spec, plan, changed code and the existing documentation (README, API docs, ADRs).
2. **Update** only what the feature changed: setup and usage in the README, API docs, migration notes in brownfield.
   Do not rewrite what is still true.
3. **ADR:** for every architecture decision that emerged (alternatives discarded in the plan, new dependencies),
   propose an ADR in `docs/adr/` and create it only after confirmation.
4. **Runnable examples:** every example you write must be run.
   - Python: mark the block with `# docs-check: run` as its first line and run
     `python scripts/docs_check.py --run-examples`.
   - Other languages: run them by hand and report the result of each.
5. **Links:** `python scripts/docs_check.py` must pass (valid relative links and images).
6. Tick `T-DOC` in `tasks.md`; commit with the trailers `Spec: SPEC-<id>` and `Agent: <name and version>`.

## STOP

List the documentation files touched and the examples run with their results. Ask for a review.
Next step: `sdd-sync`.
