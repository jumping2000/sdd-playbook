---
name: sdlc-init
description: Usa questa skill per preparare un repository al ciclo di sviluppo con coding agent: crea AGENTS.md, gli script del playbook (verify cross-platform per Windows e VS Code, lint di spec, tracciabilità, stato, loop), la struttura docs/ e la CI. Da usare una sola volta per progetto, prima di scrivere spec o codice.
---

# Inizializzazione del progetto

I file in `scripts/` e `references/` di **questa skill** sono relativi alla cartella della skill. Gli script
vanno copiati nel progetto, non letti da qui a ogni uso: il progetto deve restare verificabile in CI e da
VS Code anche senza il plugin. Playbook §1, §1.1, §3.1, §3.2.

**Regola assoluta:** non sovrascrivere mai file esistenti. Se esistono, mostra la differenza e chiedi;
per `.vscode/tasks.json` fai il merge dei task, senza sostituire il file.

## Passi

1. **Rileva** (sola lettura): sistema operativo, se è un repo git, linguaggio e gestore dei pacchetti (vedi
   `references/stacks.md`), se c'è già codice. Se c'è codice sorgente è un **brownfield**: dopo l'init il
   passo successivo è `sdlc-map-codebase`; prima di toccare qualsiasi cosa esegui i test esistenti e annota
   l'esito come baseline.
2. **Chiedi in un solo messaggio** ciò che non puoi rilevare: conferma dello stack, comandi reali di
   format/lint/tipi/test, se il team sviluppa anche su Windows (decide la matrice CI), provider CI
   (default GitHub Actions). Non assumere.
3. **Copia gli script** da `scripts/` della skill a `scripts/` del progetto: `verify.py`, `state.py`,
   `spec_lint.py`, `trace_check.py`, `bug_lint.py`, `diff_scope.py`, `docs_check.py`, `sync_check.py`,
   `scan_repo.py`, `loop.py`, `secrets_check.py`. Le altre skill si aspettano `python scripts/<nome>.py`. Ogni script
   porta in seconda riga la versione del plugin (`# sdlc-playbook: <versione>`).
4. **Adatta `STEPS` in `scripts/verify.py`** ai comandi reali. Esegui a mano ogni comando prima di
   registrarlo. Non registrare step che il progetto non ha e non inventare test: se non ci sono, dillo.
5. **Crea** (solo se mancano):
   - `AGENTS.md` da `references/AGENTS.md.tmpl`, compilato con ciò che hai verificato (sotto le 100 righe); le
     `Aree sensibili` (livello L, playbook §2.1) le indica l'utente;
   - `CLAUDE.md` con la sola riga `@AGENTS.md` (niente symlink: su Windows richiedono privilegi);
   - `.gitattributes` da `references/gitattributes.tmpl`; `reports/` in `.gitignore` (report JUnit dei test, vedi
     `references/stacks.md`);
   - `.vscode/tasks.json` da `references/vscode-tasks.json`;
   - `docs/constitution.md` da `references/constitution.md.tmpl`, e le cartelle `docs/specs/`, `docs/system/`,
     `docs/bugs/`, `docs/adr/` (con `.gitkeep`);
   - il workflow CI da `references/ci-github-actions.yml`, completando il setup del toolchain; togli
     `windows-latest` se il team non sviluppa su Windows;
   - `.github/CODEOWNERS` da `references/CODEOWNERS.tmpl` (chiedi chi approva; l'identità dell'agente non va
     elencata) e `.github/pull_request_template.md` da `references/pull_request_template.md`.
6. **Esegui** `python scripts/verify.py` e riporta l'esito così com'è. Se è rosso perché mancano i test,
   non è un errore dell'inizializzazione: segnalalo.
7. **Esegui** `python scripts/state.py` per mostrare lo stato risultante.

## Aggiornare un progetto già inizializzato

Se l'utente chiede di aggiornare gli script: confronta la riga `# sdlc-playbook:` di ogni `scripts/<nome>.py` con quella
della skill. Per ogni script più vecchio o mancante mostra la differenza e copialo dopo conferma, in un commit dedicato.
`verify.py` non si sovrascrive: contiene gli `STEPS` del progetto, quindi riporta solo le righe nuove del template
(per esempio lo step `secrets`) e lascia decidere all'utente. Poi esegui `verify` e `state.py`, e leggi il CHANGELOG del
plugin per i cambi di formato (campi nuovi in spec, task e review).

## STOP

Presenta all'utente `AGENTS.md`, `docs/constitution.md` e gli step di `verify` e chiedi l'approvazione di
principi e stack. Non creare spec, non committare e non proseguire senza risposta.

Segnala anche due limiti: la CI generata non è stata eseguita (il primo run va controllato) e gli hook
opzionali del plugin (Claude Code) non sono attivati da questa skill.

Chiedi infine quale configurazione di identità adotta l'utente (playbook §1.2: agente senza push, oppure account bot
o token senza diritti di merge) e ricordagli cosa deve impostare lui sulla piattaforma: protezione di `main` con PR,
review dei code owner e CI obbligatorie. Non puoi farlo tu e non devi chiedere credenziali.
