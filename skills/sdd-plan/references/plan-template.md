# PLAN for SPEC-001

- Approved by / date: <name, yyyy-mm-dd>
- Based on spec: <hash of the approved spec>
- Hash: <to compute after approval with spec_lint.py --hash>

## Chosen approach and discarded alternatives
<approach, and at least one discarded alternative with the reason>

## Components and files to create/modify
- <path>: <what changes>

## Interfaces (APIs, schemas, contracts)
- External: <signatures, schemas, formats; "none" if there are none>
- <component built by the tasks>: produces <exact names and signatures later tasks rely on>; consumes <what it uses>

## Test strategy (mapped to ACs)
| AC | Level (unit / integration / e2e) | Where | Notes |
|---|---|---|---|
| AC-001 | unit | tests/<file> | <...> |
| AC-002 | unit | tests/<file> | <...> |
| AC-003 | <level> | <where> | <...> |

## Review focus
<!-- Input classes or failure modes the spec implies but no AC exercises (at most 5, most likely first), each with the
test that pins it; write "- none" if you checked and found none -->
| Case | Expected behaviour | Where |
|---|---|---|
| <input or condition> | <what a reasonable user expects> | tests/<file> |

## Risks and points to validate
- <risk>: <how it is verified>

## Release and rollback
<how it is released, how to roll back>

## Documentation impact
<README, API docs, ADRs, docs/system/<area>.md>
