---
name: sdlc-review-diff
description: Usa questa skill a implementazione finita (task T-nn completate) per rileggere il diff contro spec, piano e non-scope con contesto fresco, cercando di confutare il risultato; produce review.md con un esito e la decisione umana.
---

# Review del diff contro la spec

Playbook §4 (fase 7), §5 (passo 8) e §3.8. Serve un **contesto indipendente** da chi ha implementato.

## Precondizioni

- Nessuna task `T-nn` aperta in `tasks.md` e `python scripts/verify.py` verde (eseguilo, mostra l'esito).
- Sei su un branch di feature con il lavoro committato.

## Passi

1. **Controlli deterministici:**
   - `python scripts/diff_scope.py <spec-dir>`: zone vietate e test bloccati (`Test-Lock`) modificati dopo il
     blocco (errori), file fuori piano (avviso);
   - `python scripts/trace_check.py <spec>`: ogni AC ha un test.
2. **Revisione indipendente.**
   - Claude Code: delega al subagent `sdlc-reviewer`, passando cartella della spec, ref di base e output del punto 1.
   - Altri agenti (Codex incluso): apri una **sessione nuova** e dai solo spec, piano, output del punto 1 e
     il diff; non portare la conversazione dell'implementazione. Usa le stesse istruzioni dell'agente
     `agents/sdlc-reviewer.md` del plugin.
   Il revisore prova a **confutare** il risultato, non a confermarlo.
3. **Scrivi** `review.md` nella cartella della spec da `references/review-template.md`: esito proposto
   (`conforme`, `conforme con riserve`, `non conforme`), problemi con file e riga, tentativi di confutazione.
4. Se l'esito è `non conforme`: elenca cosa correggere e torna a `sdlc-implement`; dopo la correzione la review si ripete.

## STOP

Presenta il report. **La decisione è dell'utente:** chiedi nome e conferma e compila "Decisione di". Senza
questa decisione `sync_check.py` non passerà. Non modificare codice in questa skill.
Prossimo passo se l'esito è accettato: `sdlc-docs`, poi `sdlc-sync`.
