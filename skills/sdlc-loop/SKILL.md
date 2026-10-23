---
name: sdlc-loop
description: Usa questa skill per preparare un loop autonomo che implementa le task T-nn finché verify è verde: crea PROMPT.md e progress.md, imposta tetto di iterazioni e criteri di stop, esegue un dry run e consegna all'utente il comando da lanciare. Il loop non parte senza approvazione di permessi e tetto.
---

# Loop di correzione

Playbook §7. Il loop lancia un **altro** processo agente: non lanciarlo dall'interno di questa sessione.
Lo prepari e lo lanci l'utente, in un terminale e in un ambiente isolato.

## Precondizioni

- Spec, piano e task validi: `python scripts/spec_lint.py <spec> --plan <plan> --tasks <tasks>` senza errori.
- Sei su un **branch di feature** (il loop rifiuta main/master) e `verify` è verde sulla baseline.
- Task piccole e indipendenti. Se sono poche o molto accoppiate, consiglia `sdlc-implement` interattivo.

## Passi

1. **Crea** `progress.md` da `references/progress.md.tmpl` e `PROMPT.md` da `references/PROMPT.md.tmpl`
   (sostituisci `<id>`) nella cartella della spec.
2. **Concorda con l'utente** il tetto `--max` (default 15) e `--stall` (default 3, iterazioni senza progresso).
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
python scripts/loop.py docs/specs/<id> --max <N> --stall <K>
```

Il loop termina con exit 0 quando `verify` è verde e non restano task `T-nn`. Restano poi review, `T-DOC` e
`T-SYNC`: prossimo passo `sdlc-review-diff`. Exit 1 significa tetto o stallo: serve revisione umana di spec e
piano (playbook §7.4), non un rilancio.
