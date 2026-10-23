---
name: sdlc-spec
description: Usa questa skill quando l'utente vuole passare da un'idea o una richiesta a una specifica approvabile (spec.md con requisiti, acceptance criteria e non-scope), prima di qualsiasi piano o codice; serve anche per completare o far approvare una spec in bozza.
---

# Spec

Playbook §3.3 e §4 (fase 2). Precondizione: progetto inizializzato (`scripts/spec_lint.py` esiste). Se manca,
indica `sdlc-init`.

Se la modifica si descrive con un diff di una frase, proponi una spec minima e di saltare piano e task
(playbook §2); l'utente decide.

## Passi

1. **Leggi** `AGENTS.md` e `docs/constitution.md`. Nel brownfield leggi anche `docs/system/mappa.md` e la pagina
   `docs/system/<area>.md` dell'area interessata. Se l'area non ha test di caratterizzazione, proponi
   `sdlc-characterize` **prima** di scrivere la spec.
2. **Chiarisci prima di scrivere.** Elenca all'utente domande aperte e assunzioni e **ponile**; non rispondere
   tu. Una domanda su una decisione che spetta a lui resta aperta finché non risponde.
3. **Scrivi** `docs/specs/<NNN>-<slug>/spec.md` con `references/spec-template.md`. Regole:
   - ogni requisito è una frase verificabile; ogni REQ ha almeno un AC in forma Dato/quando/allora, con un caso
     di errore dove ha senso;
   - il **non-scope** è obbligatorio e concreto (cosa non va fatto né toccato); nel brownfield descrivi solo il delta;
   - ogni assunzione è marcata `[ASSUNZIONE]`;
   - `Stato: draft`; i campi di approvazione restano vuoti.
4. **Controlla** con `python scripts/spec_lint.py docs/specs/<NNN>-<slug>/spec.md` e correggi finché non ci sono
   errori (gli avvisi vanno letti e riportati).
5. **Riassumi** all'utente: elenco dei REQ, assunzioni, non-scope, domande aperte residue.

## STOP

Chiedi l'approvazione esplicita. Solo dopo una conferma chiara **e** il nome dell'approvatore:
- compila `Approvata da / data` (nome e data di oggi) e imposta `Stato: approved`;
- chiudi o elimina le domande aperte risolte (la sezione deve contenere solo "nessuna");
- riesegui `spec_lint.py`: deve passare.

Non approvare di tua iniziativa e non inferire il consenso dal silenzio. Non avviare piano né codice.
Prossimo passo: `sdlc-plan`.
