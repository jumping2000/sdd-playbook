---
name: sdlc-docs
description: Usa questa skill per eseguire la task T-DOC: aggiornare README, documentazione API e ADR dalla spec e dal codice reale, eseguendo gli esempi che si scrivono e controllando i link con docs_check.py.
---

# Documentazione (T-DOC)

Playbook §6 e §4 (fase 8). La fonte sono **spec e codice reale**, non la memoria.

## Precondizioni

- Task `T-nn` completate e `review.md` con esito valido e diverso da `non conforme`.
- `T-DOC` è aperta in `tasks.md`.

## Passi

1. **Leggi** spec, piano, codice modificato e la documentazione esistente (README, doc API, ADR).
2. **Aggiorna** solo ciò che la feature ha cambiato: setup e uso nel README, doc API, note di migrazione nel
   brownfield. Non riscrivere ciò che è ancora vero.
3. **ADR:** per ogni decisione di architettura emersa (alternative scartate nel piano, nuove dipendenze), proponi
   un ADR in `docs/adr/` e crealo solo dopo conferma.
4. **Esempi eseguibili:** ogni esempio che scrivi va eseguito.
   - Python: marca il blocco con `# docs-check: run` come prima riga e lancia
     `python scripts/docs_check.py --run-examples`.
   - Altri linguaggi: eseguili a mano e riporta l'esito per ciascuno.
5. **Link:** `python scripts/docs_check.py` deve passare (link e immagini relativi validi).
6. Spunta `T-DOC` in `tasks.md`; commit con trailer `Spec: SPEC-<nnn>` e `Agent: <nome e versione>`.

## STOP

Elenca i file documentali toccati e gli esempi eseguiti con esito. Chiedi una review.
Prossimo passo: `sdlc-sync`.
