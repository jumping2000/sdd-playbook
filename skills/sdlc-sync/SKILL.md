---
name: sdlc-sync
description: Usa questa skill per eseguire la task T-SYNC a fine feature: riconciliare spec e pagina d'area docs/system/<area>.md con il comportamento reale, impostare lo stato della spec a implemented e lanciare sync_check.py; propone le lezioni per AGENTS.md e gli ADR.
---

# Riconciliazione spec ↔ codice (T-SYNC)

Playbook §3.7 e §4 (fase 9). Una spec non riconciliata smette di essere fonte di verità.

## Precondizioni

- `review.md` valido, con "Decisione di" compilata dall'utente.
- `T-DOC` completata. `T-SYNC` è l'ultima task aperta.

## Passi

1. **Leggi** spec, codice finale e, se esiste, `docs/system/<area>.md`.
2. **Confronta la spec con il comportamento reale.** Ogni scostamento è o un difetto del codice (nuovo bug:
   `sdlc-bugfix`) o un cambio di requisito (aggiorna la spec **con l'approvazione dell'utente**, poi aggiorna
   `Approvata da / data` e `- Hash:` con `python scripts/spec_lint.py <spec> --hash`; la modifica finisce nella PR
   di implementazione e la approva chi la unisce). Non cancellare la discrepanza in silenzio.
3. **Pagina d'area:** crea o aggiorna `docs/system/<area>.md` da `references/area-template.md`: comportamento
   attuale (solo ciò che è vero nel codice), vincoli, test di caratterizzazione, riferimenti. Aggiungi la spec
   in "Specifiche collegate" e imposta "Ultimo allineamento" alla data di oggi.
4. **Chiudi:** imposta `Stato: implemented` nella spec e spunta `T-SYNC` in `tasks.md`.
5. **Controllo:** `python scripts/sync_check.py <spec-dir>`. Correggi finché passa; se un errore dipende da una
   decisione dell'utente, riportalo senza forzare.
6. **Lezioni:** proponi, senza applicarle, le modifiche per `AGENTS.md` e per gli ADR emerse dal lavoro.
7. Commit con trailer `Spec:` e `Agent:`.

## STOP

Riporta l'esito di `sync_check.py`, gli scostamenti trovati e le lezioni proposte. Poi la PR spetta all'utente.
