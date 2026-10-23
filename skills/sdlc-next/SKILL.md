---
name: sdlc-next
description: Usa questa skill quando l'utente non sa da dove ripartire o chiede "a che punto siamo", "qual è il prossimo passo" nel ciclo di sviluppo guidato da spec; legge lo stato del repository e indica la fase e la skill successive, senza modificare nulla.
---

# Prossimo passo

Sola lettura: questa skill **non modifica file** e non avvia la fase successiva.

1. Esegui `python scripts/state.py` dalla radice del repository.
   - Se `scripts/state.py` non esiste, il progetto non è inizializzato: indica `sdlc-init` e fermati.
2. Riporta all'utente, in poche righe:
   - infrastruttura presente o mancante (AGENTS.md, verify, CI) e se c'è codice esistente senza mappa;
   - per ogni spec: livello, stato, approvazioni, avanzamento delle task, esito della review e il suo passo (`-> skill`);
   - la riga `PROSSIMO` con il motivo.
   - Con più spec attive `PROSSIMO` vale per la spec del branch corrente (il nome della cartella compare nel nome
     del branch). Se riporta `scegli`, chiedi all'utente su quale spec lavorare e rilancia
     `python scripts/state.py --spec <id>`; non scegliere tu.
3. Se compaiono **bug non verificati** (`BUG NON VERIFICATI`), segnalali: la priorità tra bug e feature la decide
   l'utente, non l'agente. La skill per i bug è `sdlc-bugfix`.
4. Le fasi seguono il playbook: init → (map-codebase, characterize nel brownfield) → spec → plan → tasks →
   implement (o loop) → review-diff → docs → sync. Il livello della spec (playbook §2.1) decide quali: S salta piano e
   `review.md`, L chiede la revisione umana del diff. Per saltare una fase si abbassa il livello nella spec, con una
   nuova approvazione: non si salta in conversazione.
5. Chiedi se procedere con la skill indicata. Non invocarla da solo.

Non dedurre lo stato dalla conversazione: vale solo l'output dello script.
