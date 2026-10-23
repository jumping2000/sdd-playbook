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
   - per ogni spec: stato, approvazioni, avanzamento delle task, esito della review;
   - la riga `PROSSIMO` con il motivo.
3. Se compaiono **bug non verificati** (`BUG NON VERIFICATI`), segnalali: la priorità tra bug e feature la decide
   l'utente, non l'agente. La skill per i bug è `sdlc-bugfix`.
4. Le fasi seguono il playbook: init → (map-codebase, characterize nel brownfield) → spec → plan → tasks →
   implement (o loop) → review-diff → docs → sync. Se l'utente vuole saltare una fase, ricordagli cosa si
   perde (playbook §2: per modifiche banali basta una spec minima).
5. Chiedi se procedere con la skill indicata. Non invocarla da solo.

Non dedurre lo stato dalla conversazione: vale solo l'output dello script.
