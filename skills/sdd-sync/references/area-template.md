# Area: <name>

- Last aligned: <yyyy-mm-dd>
- Linked specs: <SPEC-001, SPEC-002>

## Current behaviour
<2-3 paragraphs: what the area does today, for whom, with which rules; only what is true in the code>

## Diagrams
<!-- The area as built, redrawn from the code (not copied from the plan).
One Mermaid block per subsection (guide: diagrams.md of the sdd-plan skill); a diagram that does not apply is
replaced by "- n/a: <reason>". The flowchart always applies. -->

### Flowchart
<!-- flowchart TD: main flow, decisions and error paths -->
- <mermaid block>

### Sequence diagram
<!-- sequenceDiagram: calls between actors and components, in order, error replies included -->
- <mermaid block, or n/a: reason>

### State diagram
<!-- stateDiagram-v2: statuses and transitions of the entities with a lifecycle -->
- <mermaid block, or n/a: reason>

### Class diagram
<!-- classDiagram: types and modules with their relations and public members -->
- <mermaid block, or n/a: reason>

### ER diagram
<!-- erDiagram: persistent entities, keys and cardinalities -->
- <mermaid block, or n/a: reason>

## Constraints and delicate points
- <constraint, side effect, compatibility to preserve>

## Characterization tests
- <test path>: <current behaviour it pins>

## References
- <key files, ADRs, specs>
