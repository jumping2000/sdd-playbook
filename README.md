# sdlc-playbook (versione 0.10.0)

Plugin per Claude Code e Codex che accompagna lo sviluppatore lungo tutto il ciclo di vita descritto nel
[playbook](docs/playbook-ai-software-lifecycle.md): spec, piano, task, test, implementazione, review,
documentazione, riconciliazione, bug fixing e loop autonomo, con gate umani espliciti e controlli deterministici.

**Idea di fondo:** le istruzioni all'agente (skill) dicono *cosa fare e dove fermarsi*; gli script verificano *che
sia stato fatto davvero*. Un check che gira vale più di una regola in prosa.

## Cosa contiene

| Parte | Contenuto | Dettaglio |
|---|---|---|
| 14 skill | `sdlc-next`, `sdlc-init`, `sdlc-map-codebase`, `sdlc-characterize`, `sdlc-spec`, `sdlc-plan`, `sdlc-tasks`, `sdlc-tests-from-ac`, `sdlc-implement`, `sdlc-bugfix`, `sdlc-review-diff`, `sdlc-docs`, `sdlc-sync`, `sdlc-loop` | [docs/skills.md](docs/skills.md) |
| 10 script Python | `verify`, `state`, `spec_lint`, `trace_check`, `bug_lint`, `diff_scope`, `scan_repo`, `docs_check`, `sync_check`, `loop` | [docs/scripts.md](docs/scripts.md) |
| 2 hook opzionali | `Stop` (verify obbligatorio) e `PreToolUse` (guard), solo Claude Code | [docs/scripts.md](docs/scripts.md#hook-opzionali-solo-claude-code) |
| 1 subagent | `sdlc-reviewer`, revisore indipendente in sola lettura, solo Claude Code | [docs/architettura.md](docs/architettura.md) |
| Playbook | Il processo, con template e script identici a quelli del plugin | [docs/playbook-ai-software-lifecycle.md](docs/playbook-ai-software-lifecycle.md) |

## Flusso

```
sdlc-init → [sdlc-map-codebase → sdlc-characterize]* → sdlc-spec → sdlc-plan → sdlc-tasks
          → sdlc-implement (o sdlc-loop) → sdlc-review-diff → sdlc-docs → sdlc-sync → PR
sdlc-bugfix: per i difetti, in parallelo al flusso.   sdlc-next: in ogni momento.   * solo nel brownfield
```

Il processo è proporzionato al rischio: la spec dichiara un **livello** S, M o L (playbook §2.1). S salta piano e
`review.md`; L aggiunge ADR e revisione umana del diff; `diff_scope.py` segnala un diff che supera il livello dichiarato.
I test scritti dagli AC si bloccano con un commit `Test-Lock` e, nei livelli M e L, li approva l'umano prima
dell'implementazione; con il report JUnit di `verify`, `trace_check.py --junit` conta solo i test eseguiti e passati.

Ogni skill che produce un documento da approvare termina con uno **STOP**: l'agente non avanza e non approva
da solo. Le approvazioni (spec, piano, decisione sulla review) portano nome e data e sono controllate dagli script.

## Avvio rapido

1. Installa il plugin (sotto).
2. Nel repository del progetto: chiedi all'agente di usare `sdlc-init`. Copia gli script in `scripts/`, crea
   `AGENTS.md`, `docs/`, il task VS Code e la CI.
3. `python scripts/state.py` (o la skill `sdlc-next`) dice a che punto sei e qual è il passo successivo.
4. Prosegui con `sdlc-spec` (greenfield) oppure `sdlc-map-codebase` (codice esistente).

Gli script restano **nel progetto**: la verifica in CI e da VS Code funziona anche senza il plugin.

## Installazione

**Claude Code**
- Prova locale: `claude --plugin-dir <percorso>/sdlc-playbook`
- Marketplace: compila `owner` in `.claude-plugin/marketplace.json`, pubblica il repository, poi
  `/plugin marketplace add <repo>` e `/plugin install sdlc-playbook@sdlc-playbook-marketplace`.
- Le skill sono richiamabili con il prefisso del plugin; gli hook e il subagent si caricano con il plugin.

**Codex**
- Il manifest è `.codex-plugin/plugin.json`. Il file di marketplace per Codex non è incluso: il formato va
  verificato sulla documentazione.
- Alternativa documentata per le sole skill: copia le cartelle di `skills/` in `.agents/skills/` del repository
  o della home. Le skill che citano `../sdlc-init/scripts/` e `../sdlc-sync/references/` richiedono che le
  cartelle restino sorelle.
- Hook e subagent non sono previsti per Codex: la review indipendente si fa in una sessione nuova (vedi `sdlc-review-diff`).

## Configurazione

| Variabile | Effetto | Default |
|---|---|---|
| `SDLC_ENFORCE_VERIFY=1` | Abilita l'hook `Stop`: l'agente non può fermarsi con `verify` rosso | spento |
| `SDLC_VERIFY_ARGS` | Argomenti di `verify.py` per l'hook `Stop` (es. `--fast`) | vuoto (verifica completa) |
| `SDLC_STOP_MAX` | Quante volte di fila l'hook `Stop` blocca nella stessa sessione prima di lasciar fermare l'agente | 3 |
| `SDLC_GUARD=1` | Abilita l'hook `PreToolUse`: blocca comandi e letture a rischio | spento |

**Approvazioni.** Per un controllo che l'agente non può aggirare, dagli un'identità separata (nessun diritto di push,
oppure un account bot o token senza diritti di merge) e proteggi `main` con PR, review dei code owner e CI obbligatorie.
`sdlc-init` crea `.github/CODEOWNERS` e il template della PR; le regole del branch le imposti tu. Dettagli: playbook §1.2.

Gli hook partono da `hooks/run.sh`, che usa il primo tra `python3`, `python` e `py -3` e richiede `sh` (su Windows quello
di Git for Windows). In fase rossa (ultima task chiusa "atteso: rosso") l'hook `Stop` non blocca.

## Modificare il plugin

- Il playbook si modifica in `docs/playbook.src.md`; poi `python tools/build_playbook.py` rigenera il file. I blocchi
  `{{FILE ...}}` incorporano script e template del plugin: così non possono divergere.
- Test: `python -m unittest discover -s tests -v`. Includono i **test di coerenza** tra skill, script, playbook
  e documentazione (riferimenti a §, nomi di skill e script, assenza di riferimenti a versioni nel playbook, link).
- CI: `.github/workflows/ci.yml` esegue i test su Ubuntu e Windows.

## Stato della verifica

| Cosa | Esito |
|---|---|
| Suite di test | Passa su Linux (Ubuntu 24.04 su WSL2) e su Windows 11 (comprende loop con agente finto, hook e launcher `run.sh`, script su repository git temporanei) |
| `claude plugin validate .` | Passava sulla 0.4.0 (Claude Code 2.1.303, avvisi su `author`); **non rieseguito** sulla 0.5.0 con il nuovo `hooks.json` |
| Esecuzione su Windows | Suite locale e CI `windows-latest` |
| Manifest Codex | **Non validato** con uno strumento Codex |
| Skill eseguite da un agente reale su un progetto | **Non fatto**: va provato su un greenfield e su un brownfield di esempio |
| Hook in una sessione reale di Claude Code | **Non fatto**: provati solo come script con l'input JSON atteso; lo schema è accettato dal validatore |
| `loop.py` con `claude -p` reale | **Non fatto**: provato con un agente finto |
| Workflow CI generato da `sdlc-init` | **Non eseguito** |

Dettagli e limiti noti: [docs/architettura.md](docs/architettura.md). Storia delle modifiche: [CHANGELOG.md](CHANGELOG.md).

## Da completare prima di distribuirlo

- Compilare `owner` nel marketplace e aggiungere `author` in `plugin.json` (non sono stati inventati).
- Provare le skill su un repository di esempio (greenfield e brownfield) e correggere ciò che un agente reale interpreta male.
- Verificare su Codex: formato del marketplace, invocazione esplicita delle skill, eventuale supporto di subagent.
