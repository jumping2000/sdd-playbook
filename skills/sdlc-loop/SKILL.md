---
name: sdlc-loop
description: Usa questa skill per preparare un loop autonomo che implementa le task T-nn finché verify è verde: crea PROMPT.md e progress.md, imposta tetto di iterazioni e criteri di stop, esegue un dry run e consegna all'utente il comando da lanciare. Il loop non parte senza approvazione di permessi e tetto.
---

# Loop di correzione

Playbook §7. Il loop lancia un **altro** processo agente: non lanciarlo dall'interno di questa sessione.
Lo prepari e lo lanci l'utente, in un terminale e in un ambiente isolato.

## Precondizioni

- Spec, piano (non nel livello S) e task validi e approvati con la PR di design:
  `python scripts/spec_lint.py <spec> --plan <plan> --tasks <tasks> --base main` senza errori.
- Il loop chiude con successo solo se, oltre a `verify` verde e task chiuse, passano `trace_check.py` e `diff_scope.py`.
- Sei su un **branch di feature** (il loop rifiuta main/master) e `verify` è verde sulla baseline, oppure sei in
  fase rossa (l'ultima task chiusa è "atteso: rosso"). Con una baseline rossa per altri motivi il loop rifiuta di
  partire, salvo `--allow-red-baseline` deciso dall'utente.
- Task piccole e indipendenti. Se sono poche o molto accoppiate, consiglia `sdlc-implement` interattivo.

## Passi

1. **Crea** `progress.md` da `references/progress.md.tmpl` e `PROMPT.md` da `references/PROMPT.md.tmpl`
   (sostituisci `<id>`) nella cartella della spec.
2. **Concorda con l'utente** il tetto `--max` (default 15), `--stall` (default 3, iterazioni senza progresso) e
   `--timeout` (default 1800 secondi per iterazione).
3. **Dry run:** `python scripts/loop.py <spec-dir> --dry-run` (aggiungi `--agent "<comando>"` se non usa
   `claude -p`). Deve riportare `DRY-RUN OK`.
4. **Checklist di sicurezza da mostrare all'utente** (non puoi configurarla tu):
   - ambiente isolato (container, worktree o macchina dedicata), nessun accesso a produzione né a segreti;
   - permessi dell'agente non interattivo definiti a parte (allowlist e deny-list);
   - branch protetto lato server e CI attiva; il loop non fa push;
   - opzionale, solo Claude Code: hook `SDLC_ENFORCE_VERIFY=1` e `SDLC_GUARD=1` (vedi docs del plugin).

## STOP

Mostra il comando, `--max`, `--stall` e la checklist, e chiedi l'**approvazione esplicita**. Il comando è:

```
python scripts/loop.py docs/specs/<id> --max <N> --stall <K> --timeout <secondi>
```

Il loop termina con exit 0 quando `verify` è verde e non restano task `T-nn`. Restano poi review, `T-DOC` e
`T-SYNC`: prossimo passo `sdlc-review-diff`. Exit 1 significa tetto o stallo: serve revisione umana di spec e
piano (playbook §7.4), non un rilancio.
