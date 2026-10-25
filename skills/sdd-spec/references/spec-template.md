# SPEC-<yyyy-mm-dd-slug, equal to the folder name>: <title>

- Status: draft
- Level: <S | M | L: criteria in playbook §2.1>
- Owner: <name>
- Approved by / date: <name, yyyy-mm-dd>
- Hash: <to compute after approval with spec_lint.py --hash>

## Problem and goal
<why this feature exists; measurable success criterion>

## Users / actors
- <actor>: <what they want to achieve>

## Scope
- Included: <...>
- **Non-scope (explicit):** <what must NOT be done or touched>
- **Anti-goals:** <what would make this a failure even if it technically works>

## Use cases
- UC-001 <name>: actor, preconditions, main flow, alternative/error flows

## Requirements
- REQ-001 (functional): <verifiable sentence>
- REQ-101 (non-functional): <e.g. p95 latency < 200 ms, logs without personal data>

## Acceptance criteria
- AC-001 [REQ-001]: Given <context>, when <action>, then <observable result>
- AC-002 [REQ-001]: Given <invalid input>, when <action>, then <expected error>
- AC-003 [REQ-101]: Given <load or condition>, when <action>, then <measurable threshold>

## Constraints and assumptions
- <mark every assumption as [ASSUMPTION] to validate>

## Open questions
- <to close before the plan>

## Revisions
- none <!-- spec in-revision: yyyy-mm-dd, what changes and why -->
