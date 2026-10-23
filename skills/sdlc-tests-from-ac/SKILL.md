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
6. Spunta la task secondo la sua nota "atteso: rosso". **Non committare da solo** i test rossi: vanno nel
   commit della task di implementazione successiva (la CI non deve diventare rossa).

## Regole

- Non toccare il codice di produzione oltre lo scheletro del punto 3.
- Non indebolire o rimuovere test esistenti.
- A fine di tutte le task di test, `python scripts/trace_check.py <spec>` (senza `--warn-only`) deve passare
  una volta implementato il codice.

## STOP

Mostra l'elenco AC → test e i messaggi di fallimento. Chiedi uno spot check prima di implementare.
