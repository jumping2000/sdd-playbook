---
name: sdlc-plan
description: Usa questa skill quando esiste una spec approvata e serve il piano tecnico (plan.md): approccio e alternative, file coinvolti, interfacce, strategia di test mappata sugli acceptance criteria, rischi e rollback. Lavora in sola lettura sul codice.
---

# Piano

Playbook §3.4 e §4 (fase 3).

## Precondizioni (controlla prima di tutto)

- `docs/specs/<NNN>-<slug>/spec.md` esiste, `Stato: approved`, e `python scripts/spec_lint.py <spec>` passa.
  Altrimenti fermati e indica `sdlc-spec`.

## Passi

1. **Sola lettura e ragionamento:** non modificare codice. Leggi spec, `AGENTS.md`, `docs/constitution.md`,
   `docs/system/<area>.md` se esiste, e il codice rilevante.
2. **Scrivi** `plan.md` nella stessa cartella della spec con `references/plan-template.md`:
   - almeno **un'alternativa scartata** con il motivo;
   - file da creare/modificare nella sezione "Componenti e file", **uno per riga nel formato
     `- percorso: cosa cambia`** (`diff_scope.py` li usa per la review) e i chiamanti toccati; nel brownfield
     anche migrazioni e compatibilità all'indietro;
   - la tabella della strategia di test deve contenere **tutti** gli AC della spec;
   - rischi con il modo di verificarli; rilascio e rollback;
   - non introdurre nulla che la spec non richieda: se serve, è una domanda per l'utente;
   - `- Basato su spec:` con il valore di `- Hash:` della spec approvata.
3. **Controlla** con `python scripts/spec_lint.py <spec> --plan <plan>`: deve passare. L'avviso sul piano non
   approvato è atteso a questo punto.
4. Se il piano richiede una nuova dipendenza o una decisione di architettura, segnalala come candidato ADR
   (`docs/adr/`); non crearlo senza conferma.

## STOP

Riassumi il piano e chiedi l'approvazione esplicita con il nome dell'approvatore. Solo dopo, compila
`Approvato da / data`, scrivi in `- Hash:` l'output di `python scripts/spec_lint.py <plan> --hash` e riesegui il lint
con `--plan` (l'avviso deve sparire). Se la spec cambia, il piano decade e va riapprovato. Non scrivere task né codice
senza questo passo.
Prossimo passo: `sdlc-tasks`.
