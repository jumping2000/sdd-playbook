---
name: sdlc-characterize
description: Usa questa skill nel brownfield, prima di modificare un'area, per scrivere test di caratterizzazione che fissano il comportamento attuale (anche imperfetto) e registrarli nella pagina d'area; è la rete di sicurezza prima della spec e del codice.
---

# Test di caratterizzazione

Playbook §5, passo 4. **Non modifichi codice di produzione** e non correggi i difetti che trovi: li annoti.

## Precondizioni

- Esiste `docs/system/mappa.md` (altrimenti `sdlc-map-codebase`) e la baseline è nota.
- L'utente ha indicato l'area o i file che intende modificare.
- Lavoro committato per i file dell'area: `git status` pulito su di essi (serve al punto 5).

## Passi

1. **Individua** i comportamenti dell'area da preservare: leggi codice, chiamanti e test esistenti.
   Elenca all'utente cosa pensi di fissare e cosa lasci fuori.
2. **Scrivi i test** che descrivono il comportamento **attuale**, anche quando è strano o sbagliato: se un
   comportamento è un bug, il test lo fissa e lo annoti come tale nel test. Nome con prefisso
   `char`/`characterization` (es. `test_char_...`).
3. **Eseguili sul codice non modificato: devono passare.** Se uno fallisce hai capito male il comportamento:
   correggi il test, non il codice.
4. **Esegui `python scripts/verify.py`**: deve restare verde (o come la baseline).
5. **Prova che i test sanno fallire:** introduci una rottura deliberata e minima in un punto dell'area,
   esegui i test e verifica che diventino rossi, poi ripristina con `git restore <file>` e controlla che
   `git diff` sia vuoto sui file di produzione. Mostra l'evidenza. Se un test resta verde, è inutile: rafforzalo.
6. **Registra** i test in `docs/system/<area>.md` (sezione "Test di caratterizzazione"); se la pagina non esiste
   creala da `../sdlc-sync/references/area-template.md`.

## STOP

Riporta test scritti, comportamenti fissati, difetti annotati e prova di fallimento. Chiedi uno spot check.
Prossimo passo: `sdlc-spec` per descrivere solo il delta.
