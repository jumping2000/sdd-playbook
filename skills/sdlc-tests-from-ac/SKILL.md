---
name: sdlc-tests-from-ac
description: Usa questa skill per scrivere i test dagli acceptance criteria della spec (non dal codice), citando gli ID degli AC, e verificare che falliscano per il motivo giusto prima dell'implementazione; si applica alle task di test di tasks.md.
---

# Test dagli acceptance criteria

Playbook §6. Precondizioni: spec e piano approvati (`python scripts/spec_lint.py <spec> --plan <plan>` senza
errori); la task di test è indicata in `tasks.md`. Convenzioni di nome: `references/convenzioni-test.md`.

## Passi

1. **Parti dagli AC che la task copre**, non dall'implementazione. Nel brownfield leggi solo le interfacce da
   chiamare; non copiare la logica esistente nei test.
2. **Un test per AC, più i casi di errore** presenti negli AC. Cita l'ID (`AC-001`) nel nome o in un commento,
   così `trace_check.py` lo trova. Non inventare requisiti: un caso non coperto dalla spec è una domanda
   per l'utente.
3. **Scheletro minimo** del codice da testare, solo se serve a far girare i test (firma che lancia un errore
   "non implementato"): lo scopo è che i test falliscano sul comportamento, non su un import.
4. **Esegui i test della task:** devono essere **rossi per il motivo giusto**. Riporta il messaggio di
   fallimento di ciascuno. Un errore di sintassi, di import o di nome non è il motivo giusto: correggi il test.
5. **Controlla la tracciabilità:** `python scripts/trace_check.py <spec> --warn-only` (gli AC delle task
   successive risulteranno ancora senza test).
6. **Blocca i test con un commit.** Se hai scritto uno scheletro, committalo prima, a parte. Poi committa **solo i
   file di test** con i trailer `Test-Lock: T-<nn>`, `Spec: SPEC-<nnn>` e `Agent: <nome e versione>`, e spunta la
   task. Da qui `diff_scope.py` segnala come errore ogni modifica successiva a quei test: l'implementazione deve
   farli passare senza toccarli. La CI del branch resta rossa fino alla task di implementazione: è atteso, e la
   "fase rossa" (ultima task chiusa marcata "atteso: rosso") è riconosciuta dall'hook `Stop` e da `loop.py`.
   Se l'utente non ha autorizzato i commit, proponi i messaggi e non committare.

## Regole

- Non toccare il codice di produzione oltre lo scheletro del punto 3.
- Non indebolire o rimuovere test esistenti.
- Un test bloccato che si rivela sbagliato si corregge solo con l'accordo dell'utente, in un nuovo commit
  `Test-Lock`, e la correzione va motivata in `review.md`.
- A fine di tutte le task di test, `python scripts/trace_check.py <spec>` (senza `--warn-only`) deve passare
  una volta implementato il codice.

## STOP

Mostra l'elenco AC → test e i messaggi di fallimento. Chiedi uno spot check prima di implementare.
