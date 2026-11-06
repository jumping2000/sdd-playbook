## SPEC-<id> T-<nn>: <goal>

**Covers:** <AC-nnn: one line each, as written in the spec>

**Sensitive areas touched:** <none | paths from AGENTS.md: read the diff of these files>

### Checks
- `python scripts/verify.py`: <ok | output of the failure>
- `python scripts/trace_check.py <spec> --task T-<nn>`: <ok>
- `python scripts/diff_scope.py <spec dir> --task T-<nn>`: <ok, warnings listed>
- CI: <green | red | none>

### Review (sdd-reviewer)
<verdict: pass | fix needed; problems with file:line; how the tests derive from the ACs>

### Decisions taken alone
<!-- Only what "Decides alone" in AGENTS.md allows; one line each: what, why, what it costs if wrong. "none" otherwise -->
- none

### Documentation
<spec, area page or README touched; "none" if the task changes no documented behaviour>
