---
name: sdlc-spec
description: Usa questa skill quando l'utente vuole passare da un'idea o una richiesta a una specifica approvabile (spec.md con requisiti, acceptance criteria e non-scope), prima di qualsiasi piano o codice; serve anche per completare o far approvare una spec in bozza.
---

# Spec

Playbook §3.3 e §4 (fase 2). Precondizione: progetto inizializzato (`scripts/spec_lint.py` esiste). Se manca,
indica `sdlc-init`.

Il processo dipende dal **livello** della modifica (playbook §2.1): S salta piano e `review.md`, L aggiunge ADR e
revisione umana del diff. Lo proponi tu con i criteri, lo decide l'utente.

## Passi

1. **Leggi** `AGENTS.md` e `docs/constitution.md`. Nel brownfield leggi anche `docs/system/mappa.md` e la pagina
   `docs/system/<area>.md` dell'area interessata. Se l'area non ha test di caratterizzazione, proponi
   `sdlc-characterize` **prima** di scrivere la spec.
2. **Chiarisci prima di scrivere.** Elenca all'utente domande aperte e assunzioni e **ponile**; non rispondere
   tu. Una domanda su una decisione che spetta a lui resta aperta finché non risponde.
3. **Scrivi** `docs/specs/<id>/spec.md` con `references/spec-template.md`. L'`<id>` è la data di oggi più uno
   slug breve in minuscolo (`2026-10-24-export-csv`): è il nome della cartella e compare nel titolo
   (`# SPEC-2026-10-24-export-csv: Export CSV`), così due persone o due branch non scelgono lo stesso ID. Regole:
   - ogni requisito è una frase verificabile; ogni REQ ha almeno un AC in forma Dato/quando/allora, con un caso
     di errore dove ha senso;
   - il **non-scope** è obbligatorio e concreto (cosa non va fatto né toccato); nel brownfield descrivi solo il delta;
   - ogni assunzione è marcata `[ASSUNZIONE]`;
   - `- Livello:` S, M o L con i criteri del playbook §2.1: S solo se **tutti** veri (al massimo 3 file di
     produzione, nessuna interfaccia pubblica o formato dati cambiato, nessuna area sensibile di `AGENTS.md`,
     nessuna dipendenza); L se tocca un'area sensibile, un'interfaccia pubblica o una migrazione di dati. Nel dubbio
     il più alto. `diff_scope.py` segnalerà un diff che supera il livello;
   - `Stato: draft`; i campi di approvazione restano vuoti.
4. **Controlla** con `python scripts/spec_lint.py docs/specs/<id>/spec.md` e correggi finché non ci sono
   errori (gli avvisi vanno letti e riportati).
5. **Riassumi** all'utente: livello proposto con il motivo, elenco dei REQ, assunzioni, non-scope, domande aperte residue.

## STOP

Chiedi l'approvazione esplicita. Solo dopo una conferma chiara **e** il nome dell'approvatore:
- compila `Approvata da / data` (nome e data di oggi) e imposta `Stato: approved`;
- chiudi o elimina le domande aperte risolte (la sezione deve contenere solo "nessuna");
- calcola l'hash con `python scripts/spec_lint.py <spec> --hash` e scrivilo in `- Hash:`;
- riesegui `spec_lint.py`: deve passare.

Da qui ogni modifica al corpo della spec fa decadere l'approvazione (l'hash non corrisponde più).

**Modificare una spec già approvata:** imposta `Stato: in-revisione` e aggiungi in `## Revisioni` una voce con data,
cosa cambia e perché; fai le modifiche e chiedi di nuovo l'approvazione come sopra (nuovo nome, data e hash). Il
piano, che registra l'hash della spec, decade da solo e va riapprovato; le task, che registrano l'hash del piano,
vanno riviste se il piano cambia. L'approvazione vera è il merge della PR di design su `main` (playbook §1.2): spec, piano e task vanno
insieme in quella PR, che apre l'utente o l'identità bot dell'agente, mai unita dall'agente.

Non approvare di tua iniziativa e non inferire il consenso dal silenzio. Non avviare piano né codice.
Prossimo passo: `sdlc-plan` (livello S: `sdlc-tasks`).
