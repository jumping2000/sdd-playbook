# Codebase map

- Date: <yyyy-mm-dd>
- Baseline: <green | red: list of the failures already present>

## Modules and responsibilities
| Module / folder | Responsibility | Depends on |
|---|---|---|
| <path> | <what it does> | <modules> |

## Diagrams
<!-- The existing system as read in the code: modules and dependencies in the flowchart,
the existing schema in the ER diagram.
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

## Entry points
- <path>: <what it starts>

## External dependencies and integrations
- <service / library / database>: <how it is used>

## Real commands (tried)
| Purpose | Command | Result |
|---|---|---|
| Build | `<command>` | <ok / error> |
| Test | `<command>` | <ok / error> |
| Local run | `<command>` | <ok / error> |

## Zones not to touch
- <path>: <reason>

## Risks and known debt
- <risk>

## How this map was verified
- <statements spot-checked in the code, with file and line>
