---
name: sdlc-tasks
description: Usa questa skill quando spec e piano sono approvati e serve scomporre il lavoro in tasks.md: passi piccoli, ognuno con un comando di verifica e gli acceptance criteria che copre, test prima del codice, più T-DOC e T-SYNC.
---

# Task

Playbook §3.5 e §4 (fase 4).

## Precondizioni

- Spec `approved` e piano con `Approvato da / data` compilato (controlla con
  `python scripts/spec_lint.py <spec> --plan <plan>`: nessun errore e nessun avviso sul piano). Altrimenti
  fermati e indica la skill mancante.

## Passi

1. **Scrivi** `tasks.md` nella cartella della spec; il formato è in `references/tasks-template.md`:

   ```
   - [ ] T-nn <azione piccola> — verifica: `<comando>` — copre: AC-nnn, AC-mmm
   ```

2. Regole:
   - **Una task = un'unità che un comando può dichiarare riuscita o fallita.** Se non riesci a scrivere il
     comando di verifica, la task è troppo vaga: spezzala o chiarisci.
   - **Test prima del codice:** per ogni gruppo di AC, una task che scrive i test (si esegue con
     `sdlc-tests-from-ac`; verifica: il test fallisce per il motivo giusto, annotato "atteso: rosso"), poi la
     task che implementa.
   - Ogni AC è coperto da almeno una task; nessuna task tocca ciò che è nel non-scope.
   - Includi sempre `T-DOC` (documentazione, esempi eseguiti: `sdlc-docs`) e `T-SYNC` (riconciliazione spec e
     `docs/system/`, poi `Stato: implemented`: `sdlc-sync`). Non hanno `copre:`: si eseguono dopo la review.
   - Se la spec è piccola, poche task: non gonfiare il piano.
3. **Controlla** con `python scripts/spec_lint.py <spec> --tasks <tasks>`: deve passare.

## STOP

Mostra l'elenco e chiedi un controllo rapido all'utente. Non iniziare l'implementazione senza il suo via.
Prossimo passo: `sdlc-implement` (o `sdlc-loop` se le task sono molte e indipendenti).
