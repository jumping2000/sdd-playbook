---
name: sdlc-implement
description: Usa questa skill per implementare le task T-nn di tasks.md una alla volta, con verifica a ogni passo (scripts/verify.py), commit su branch di feature quando verde e aggiornamento dello stato; da usare dopo spec, piano e task approvati.
---

# Implementazione

Playbook §4 (fase 6) e §6. Lavora sulle sole task numerate `T-nn`: `T-DOC` e `T-SYNC` hanno skill dedicate.

## Precondizioni

- Spec approvata, piano approvato, `tasks.md` valido
  (`python scripts/spec_lint.py <spec> --plan <plan> --tasks <tasks>`: nessun errore).
- Sei su un **branch di feature**, non su `main`/`master`/un branch protetto. Altrimenti proponi di crearlo e
  attendi conferma.
- Esegui `python scripts/verify.py` **prima di iniziare**: serve una baseline. Se è già rossa, segnalalo
  all'utente: non è colpa delle tue modifiche e non va nascosto.

## Ciclo (una task per volta)

1. Prendi la **prima task `T-nn` aperta** (`- [ ]`). Leggi gli AC che copre nella spec.
2. Se la task **scrive test dagli AC**, applica la procedura di `sdlc-tests-from-ac` (leggila). Altrimenti
   implementa **solo quella task**: non toccare il non-scope e non fare refactoring non richiesti.
3. Esegui il comando di `verifica:` della task, poi `python scripts/verify.py` completo
   (`--fast` è ammesso solo durante il lavoro, mai come criterio di fatto).
4. **Rosso:** leggi l'errore, correggi, riprova. Dopo **3 tentativi** sulla stessa task, fermati: descrivi cosa
   hai provato e chiedi indicazioni (task troppo grande o spec ambigua).
5. **Verde:** spunta la task in `tasks.md`. Fai commit con messaggio chiaro e i trailer `Spec: SPEC-<NNN>` e
   `Agent: <nome e versione>`. Se l'utente non ha autorizzato i commit, proponi il messaggio e non committare.
   Una task di test "atteso: rosso" non si committa da sola: va nel commit della task di implementazione successiva.
6. Se esiste `progress.md` nella cartella della spec, aggiornalo: fatto, imparato, blocchi.
7. Passa alla task successiva solo se l'utente ha chiesto di procedere in sequenza; altrimenti fermati e riporta.

## Regole di arresto

- Requisito ambiguo o mancante: **fermati e chiedi**, non assumere (scrivi la domanda in `progress.md` se esiste).
- Serve modificare qualcosa nel non-scope: fermati e chiedi.
- Non dichiarare mai una task o la feature completata senza aver eseguito `verify` e senza mostrare l'esito.

## Fine

Quando non restano task `T-nn` aperte: riporta l'esito finale di `verify`, l'elenco dei commit, e passa a
`sdlc-review-diff` (poi `sdlc-docs` e `sdlc-sync`). Non dichiarare la feature conclusa: mancano review,
documentazione e riconciliazione.
