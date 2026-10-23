## Tipo di PR
- [ ] **Design**: spec, piano e task (il merge è l'approvazione)
- [ ] **Implementazione**: codice e test di una spec già unita su main
- [ ] **Bug**: `docs/bugs/BUG-...`

Spec: `docs/specs/<id>/`

## Evidenze (output incollato, non riassunto)
- `python scripts/verify.py`:
- `python scripts/spec_lint.py <spec> --plan <plan> --tasks <tasks> --base main`:
- `python scripts/trace_check.py <spec> --junit reports/junit.xml`:
- `python scripts/diff_scope.py <spec-dir>`:

## Per chi approva
- [ ] Design: AC verificabili, non-scope concreto, nessuna domanda aperta
- [ ] Implementazione: ho riletto i commit `Test-Lock` (i test che fissano gli AC) prima del resto del diff, e le task di test riportano `test approvati:`
- [ ] Nessun file in zona vietata né test bloccato modificato (`diff_scope.py`)
- [ ] `review.md` presente con esito e decisione
