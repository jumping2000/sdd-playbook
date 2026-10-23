# Changelog

## 0.4.0
- Skill `sdlc-docs` (T-DOC) e `sdlc-sync` (T-SYNC); script `docs_check.py` e `sync_check.py`.
- `sync_check.py` richiede anche la decisione umana nella review.
- Documentazione completa del plugin (`docs/skills.md`, `docs/scripts.md`, `docs/architettura.md`) e playbook generato
  dai file del plugin (`tools/build_playbook.py`).
- Test di coerenza tra skill, script, playbook e documentazione; CI su Ubuntu e Windows.

## 0.3.0
- Skill `sdlc-review-diff` e `sdlc-loop`; subagent `sdlc-reviewer` (Claude Code).
- Script `diff_scope.py` e `loop.py` (tetto, rilevamento dello stallo, rifiuto di main/master, dry run, stop sulle sole task `T-nn`).
- Hook opzionali `Stop` (`SDLC_ENFORCE_VERIFY`) e `PreToolUse` (`SDLC_GUARD`).
- `state.py`: fasi review-diff, docs e sync.

## 0.2.0
- Skill `sdlc-map-codebase`, `sdlc-characterize`, `sdlc-tests-from-ac`, `sdlc-bugfix`.
- Script `scan_repo.py`, `trace_check.py`, `bug_lint.py`.
- `state.py`: rilevamento del brownfield (codice esistente senza mappa) e dei bug non verificati.

## 0.1.0
- Skill `sdlc-next`, `sdlc-init`, `sdlc-spec`, `sdlc-plan`, `sdlc-tasks`, `sdlc-implement`.
- Script `verify.py`, `spec_lint.py` (spec, piano, task), `state.py`.
- Manifest per Claude Code e Codex.
