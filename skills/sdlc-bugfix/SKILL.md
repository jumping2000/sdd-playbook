---
name: sdlc-bugfix
description: Usa questa skill quando c'è un difetto da correggere: segue riproduzione, definizione del comportamento atteso e da non cambiare, test rosso, diagnosi, fix minimo e non-regressione, con docs/bugs/BUG-nnn.md controllato da bug_lint.py. Non usarla per nuove funzionalità.
---

# Bug fixing

Playbook §6.1. Un bug non è una feature in miniatura. Un bug, un branch, un commit di fix.
Se la causa è evidente e il diff è di una riga, basta: test rosso, fix, `verify` (senza file del bug).

## Passi (aggiorna `Stato` a ogni transizione e lancia `python scripts/bug_lint.py <file>`)

1. **Riproduzione** (`aperto`). Crea `docs/bugs/BUG-<nnn>-<slug>.md` da `references/bugfix-template.md`.
   Riproduci con passi minimi. **Se non ci riesci, fermati e chiedi dati**: nessun fix a intuito.
2. **Definizione.** Compila comportamento attuale e atteso (con riferimento a REQ/AC; se la spec non lo
   copriva, proponi un nuovo AC) e **"Comportamento da NON cambiare"**, che è la rete di non-regressione.
   **STOP:** l'utente conferma atteso e invariato. Se la spec era silente o sbagliata, dillo: è anche un bug di spec.
3. **Test rosso.** Scrivi un test che fallisce per il motivo del bug e indicane il percorso in "Fix e test".
   Eseguilo e mostra il fallimento.
4. **Diagnosi** (`diagnosticato`). Sola lettura finché la causa non è chiara: log, debugger, `git bisect`.
   Scrivi la causa radice verificata, non un'ipotesi.
5. **Fix minimo** (`corretto`). Solo ciò che serve. Niente refactoring nello stesso commit. Aggiungi il test sul
   comportamento invariato e indicalo.
6. **Non-regressione:** `python scripts/verify.py` completo verde e test del bug verde.
7. **Chiusura** (`verificato`). Se il bug rivelava un requisito mancante, aggiorna spec/AC e `docs/system/<area>.md`.
   Spunta le voci di "Chiusura", registra la lezione in `AGENTS.md`/ADR (proposta all'utente).
   Commit: messaggio con `Bug: BUG-<nnn>` e `Agent: <nome e versione>`.

## Se la diagnosi coinvolge molte aree

Fai la diagnosi in una sessione separata (o con un subagent) che consegna solo il file del bug; la correzione
parte in un'altra sessione con quel file come unico contesto.

## Regole

- Non correggere altri difetti incontrati: annotali come nuovi bug.
- Non indebolire test esistenti per far passare il fix.
- Dopo 3 tentativi falliti di fix, fermati e riporta cosa hai provato.
