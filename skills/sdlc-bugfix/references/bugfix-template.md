# BUG-001: <titolo>

- Stato: aperto
- Gravità / impatto: <...>
- Spec o area interessata: <SPEC-xxx / docs/system/<area>.md>

## Riproduzione
<passi minimi, dati di input, ambiente; se non si riproduce, fermati qui>

## Comportamento attuale vs atteso
- Attuale: <...>
- Atteso (con riferimento a REQ/AC, o nuovo AC se la spec non lo copriva): <...>

## Comportamento da NON cambiare
- <elenco esplicito: è la rete di non-regressione>

## Causa radice
<ipotesi verificata, non intuizione>

## Fix e test
- Test rosso che riproduce il bug: `<percorso/nome>`
- Fix minimo: <file, descrizione>
- Test di non-regressione sul comportamento invariato: `<percorso/nome>`

## Chiusura
- [ ] `verify` completo verde e test del bug che passa
- [ ] Spec/AC/`docs/system/` aggiornati se il bug rivelava un requisito mancante
- [ ] Lezione registrata in `AGENTS.md` o in un ADR, se c'è
