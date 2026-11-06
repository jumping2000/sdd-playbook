# SPEC-<yyyy-mm-dd-slug, equal to the folder name>: <title>

- Status: draft
- Owner: <name>

## Problem and goal
<why this feature exists; measurable success criterion>

## Users / actors
- <actor>: <what they want to achieve>

## Scope
- Included: <...>
- **Non-scope (explicit):** <what must NOT be done or touched>
- **Anti-goals:** <what would make this a failure even if it technically works>

## Current behaviour and impact
<!-- From the impact analysis of sdd-start. "- none (new area)" for new code. -->
- Today: <what the affected area does now, with its area page or spec>
- Changes: <what this spec changes>
- Must not change: <behaviour to preserve>, protected by <test paths>

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
<!-- One per line: - <question> — blocking: yes|no. Blocking: the answer would change a requirement or an AC. An
approved spec keeps only non-blocking questions. "- none" when there are none. -->
- <question> — blocking: <yes | no>

## Revisions
- none <!-- after approval: yyyy-mm-dd, what changes and why (the change goes through a PR like any other) -->
