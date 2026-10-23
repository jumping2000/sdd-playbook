---
name: sdlc-map-codebase
description: Usa questa skill all'inizio di un lavoro su una codebase esistente (brownfield) per produrre in sola lettura la mappa del sistema (docs/system/mappa.md) con comandi reali provati e baseline dei test, prima di scrivere spec o toccare codice.
---

# Mappa della codebase (brownfield)

Precondizione: progetto inizializzato (`scripts/scan_repo.py` e `scripts/verify.py` esistono). Se mancano,
indica `sdlc-init` (se mancano solo gli script, copiali da `../sdlc-init/scripts/`).

**Sola lettura sul codice.** Gli unici file che scrivi sono `docs/system/mappa.md` e, previa conferma,
`AGENTS.md`. Playbook §5, passi 1-3.

## Passi

1. **Inventario:** `python scripts/scan_repo.py`. È un elenco di fatti (stack, linguaggi, cartelle,
   test, CI, entry point probabili), non comprensione.
2. **Baseline:** esegui `python scripts/verify.py` e, se `STEPS` non copre ancora il progetto, i comandi reali di
   build e test. Annota l'esito **così com'è**: se è già rosso, non è colpa tua e va dichiarato.
3. **Leggi il codice** a partire dagli entry point e dai moduli più grandi. Compila `docs/system/mappa.md` da
   `references/mappa-template.md`: moduli e responsabilità, entry point, dipendenze esterne, zone da non toccare,
   rischi e debito noto.
4. **Comandi reali:** ogni comando nella tabella è stato eseguito da te, con l'esito. Non scrivere comandi dedotti.
5. **Verifica a campione:** scegli almeno 5 affermazioni della mappa e controllale nel codice; elencale con
   file e riga in "Come è stata verificata questa mappa". Correggi quelle false.
6. **Proponi** di aggiornare `AGENTS.md` con i comandi provati e le zone da non toccare (riga "Non modificare:"
   usata da `diff_scope.py`). Mostra la differenza e chiedi conferma.

## STOP

Presenta la mappa e l'esito della baseline. Chiedi all'utente di verificarla a campione. Non scrivere spec.
Prossimo passo: `sdlc-characterize` sull'area da modificare, poi `sdlc-spec`.
