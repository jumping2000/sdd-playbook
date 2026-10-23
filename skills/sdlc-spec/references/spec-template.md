# SPEC-<aaaa-mm-gg-slug, uguale al nome della cartella>: <titolo>

- Stato: draft
- Livello: <S | M | L: criteri nel playbook §2>
- Proprietario: <nome>
- Approvata da / data: <nome, aaaa-mm-gg>
- Hash: <da calcolare dopo l'approvazione con spec_lint.py --hash>

## Problema e obiettivo
<perché esiste questa feature; criterio di successo misurabile>

## Utenti / attori
- <attore>: <cosa vuole ottenere>

## Scope
- Incluso: <...>
- **Non-scope (esplicito):** <cosa NON deve essere fatto né toccato>

## Use case
- UC-001 <nome>: attore, precondizioni, flusso principale, flussi alternativi/errore

## Requisiti
- REQ-001 (funzionale): <frase verificabile>
- REQ-101 (non funzionale): <es. latenza p95 < 200 ms, log senza dati personali>

## Acceptance criteria
- AC-001 [REQ-001]: Dato <contesto>, quando <azione>, allora <risultato osservabile>
- AC-002 [REQ-001]: Dato <input non valido>, quando <azione>, allora <errore atteso>
- AC-003 [REQ-101]: Dato <carico o condizione>, quando <azione>, allora <soglia misurabile>

## Vincoli e assunzioni
- <marca ogni assunzione come [ASSUNZIONE] da validare>

## Domande aperte
- <da chiudere prima del piano>

## Revisioni
- nessuna <!-- spec in-revisione: aaaa-mm-gg, cosa cambia e perché -->
