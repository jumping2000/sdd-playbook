# PLAN for SPEC-<id>

## Approach
<chosen approach in a few lines, and at least one discarded alternative with the reason>

## Interfaces
- External: <signatures, schemas, formats; "none" if there are none>
- <component>: produces <exact names and signatures other tasks rely on>; consumes <what it uses>

## Flowchart
<!-- Mandatory: the main flow of the feature with its decisions and error paths (guide: diagrams.md of this skill).
Other diagrams (sequence, state, class, ER) go under "## Other diagrams" only when they help the tasks. -->
- <mermaid block>

## Tasks
<!-- 3 to 8 vertical tasks: each delivers a behaviour a user or a caller can observe, with its ACs, and fits one PR
readable in 15-30 minutes. One line per task:
- [ ] T-nn <goal> — covers: AC-nnn — files: `path`, `path` — depends: T-nn | none — verify: `<command>`
"files" lists the main files the task creates or changes, tests included: tasks with disjoint files and no
dependency between them can run in parallel. The box is ticked by the task's own PR. -->
- [ ] T-01 <goal> — covers: AC-001, AC-002 — files: `<path>`, `<test path>` — depends: none — verify: `<command>`
- [ ] T-02 <goal> — covers: AC-003 — files: `<path>`, `<test path>` — depends: T-01 — verify: `<command>`

## Review focus
<!-- Input classes or failure modes the spec implies but no AC exercises (at most 5), each with the task whose tests
pin it; "- none" if you checked and found none -->
- <input or condition>: <expected behaviour> (T-nn)

## Risks
- <risk>: <how it is checked; rollback if it matters>

## Revisions
- none <!-- yyyy-mm-dd, what changes and why, which task got stuck -->
