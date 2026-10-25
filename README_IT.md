# SDD Playbook (versione 0.15.0)

[![Version](https://img.shields.io/badge/version-0.15.0-blue)](CHANGELOG_IT.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/jumping2000/sdd-playbook/actions/workflows/ci.yml/badge.svg)](https://github.com/jumping2000/sdd-playbook/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)](docs/scripts_IT.md)
[![Dependencies](https://img.shields.io/badge/dependencies-none%20%28stdlib%29-brightgreen)](docs/architecture_IT.md)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](docs/architecture_IT.md)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-D97757)](#installazione)
[![Codex](https://img.shields.io/badge/Codex-plugin-412991)](#installazione)
[![GitHub Copilot](https://img.shields.io/badge/GitHub%20Copilot-skills%20%2B%20agent-000000?logo=githubcopilot)](#installazione)
[![Stato](https://img.shields.io/badge/stato-in%20progettazione-orange)](#stato-della-verifica)
[![Docs](https://img.shields.io/badge/docs-EN%20%7C%20IT-informational)](#documentazione)
[![Last commit](https://img.shields.io/github/last-commit/jumping2000/sdd-playbook)](https://github.com/jumping2000/sdd-playbook/commits/main)
[![Stars](https://img.shields.io/github/stars/jumping2000/sdd-playbook?style=social)](https://github.com/jumping2000/sdd-playbook)

*English version: [README.md](README.md)*

> **Stato: in progettazione.** Il plugin non è ancora stato usato su un progetto reale: skill, hook e loop sono
> provati solo con test automatici e agenti finti. Formati e contratti possono ancora cambiare senza compatibilità.

**SDD Playbook** (`sdd-playbook`) è un plugin di spec-driven development per Claude Code, Codex e GitHub Copilot che accompagna lo sviluppatore lungo tutto il ciclo di vita descritto nel
[playbook](docs/playbook-ai-software-lifecycle_IT.md): spec, piano, task, test, implementazione, review,
documentazione, riconciliazione, bug fixing e loop autonomo, con gate umani espliciti e controlli deterministici.

**Idea di fondo:** le istruzioni all'agente (skill) dicono *cosa fare e dove fermarsi*; gli script verificano *che
sia stato fatto davvero*. Un check che gira vale più di una regola in prosa.

**Si parte da qui:** [Guida rapida](docs/quick-guide_IT.md): come usarlo su un progetto nuovo o esistente.

## Obiettivo

Rendere il software costruito con un coding agent **affidabile come quello di un team disciplinato**, senza chiedere
allo sviluppatore di rileggere ogni riga. In pratica il plugin vuole garantire che:

1. l'agente costruisca **ciò che è stato deciso**, scritto in una spec approvata, e non ciò che ha indovinato;
2. "fatto" significhi **verificato da un comando** (test, lint, tipi, tracciabilità), non "sembra fatto";
3. i test che definiscono "fatto" siano **scritti dai requisiti e approvati da una persona** prima del codice;
4. l'agente **non tocchi ciò che non deve**, soprattutto nel codice esistente;
5. l'umano decida nei **pochi punti che contano**, con uno sforzo proporzionato al rischio della modifica;
6. spec e documentazione **restino allineate** al comportamento reale dopo ogni feature;
7. tutto questo funzioni allo stesso modo in **Claude Code, Codex e GitHub Copilot**, su **Windows nativo e Linux**, e resti verificabile
   in CI anche senza il plugin.

## Razionale: perché questo insieme di skill

I coding agent sbagliano in modi ricorrenti. Ogni skill e ogni script esiste per contrastarne uno:

| Errore tipico di un coding agent | Risposta del plugin | Dove |
|---|---|---|
| Indovina i requisiti e riempie i vuoti con assunzioni | Spec con requisiti, acceptance criteria e non-scope esplicito; domande aperte poste, non risolte dall'agente; assunzioni marcate | `sdd-spec`, `spec_lint.py` |
| Dichiara "fatto" senza evidenze | Un solo comando di verifica come definizione di "fatto"; l'hook `Stop` blocca la chiusura con `verify` rosso; il loop termina solo su controlli oggettivi | `verify.py`, hook `Stop`, `loop.py` |
| Scrive test che confermano i propri bug | Test dagli AC, rossi per il motivo giusto, bloccati da un commit `Test-Lock` e approvati da una persona; tracciabilità AC → test eseguito | `sdd-tests-from-ac`, `trace_check.py --junit`, `diff_scope.py` |
| Modifica o "migliora" ciò che è fuori scope | Piano approvato con i file da toccare; zone vietate e aree sensibili in `AGENTS.md`; diff confrontato con piano e livello | `sdd-plan`, `diff_scope.py` |
| Rompe comportamenti esistenti in un codice legacy | Prima mappa e baseline, test di caratterizzazione che sanno fallire, spec del solo delta | `sdd-map-codebase`, `sdd-characterize` |
| Si approva da solo (le approvazioni sono testo) | Hash del contenuto approvato; l'approvazione vera è un merge su `main` protetto da parte di un'identità separata; controlli di processo in CI sulla PR | `spec_lint.py --base`, template CI, `CODEOWNERS` |
| Stesso processo pesante per una riga e per una migrazione | Livelli S, M, L dichiarati nella spec, inclusi nel suo hash, controllati sul diff reale | playbook §2.1, `diff_scope.py` |
| Review fatta dalla stessa sessione che ha scritto il codice | Revisore a contesto fresco, in sola lettura per costruzione, che prova a confutare; decide l'umano | `sdd-review-diff`, `sdd-reviewer` |
| Spec che invecchiano dopo la consegna | Task di chiusura che riconcilia spec, pagina d'area e codice | `sdd-sync`, `sync_check.py` |
| Bug corretti "a intuito", rompendo altro | Riproduzione, comportamento da NON cambiare, test rosso, fix minimo | `sdd-bugfix`, `bug_lint.py` |
| Esecuzioni autonome lunghe che derivano, si bloccano o espongono dati | Loop esterno con tetto, rilevamento dello stallo, timeout, pausa per l'approvazione dei test, permessi d'esempio, isolamento | `sdd-loop`, `loop.py`, `settings.loop.json` |
| Segreti e dipendenze non riviste che entrano nel codice | Scansione dei segreti in `verify`; dipendenze solo nel piano approvato o con un ADR | `secrets_check.py`, `diff_scope.py` |
| Non sapere più a che punto è il lavoro | Una macchina a stati che legge i file, non la chat | `sdd-next`, `state.py` |

**Le scelte di progetto alla base**
- **Skill per il processo, script per i controlli.** Le skill sono istruzioni brevi con uno STOP a ogni punto di
  approvazione; gli script sono Python deterministico con sola libreria standard, copiati nel progetto perché CI e VS Code
  li usino senza il plugin.
- **L'umano approva, la piattaforma fa rispettare.** Ogni campo di testo può scriverlo l'agente; un merge su un branch
  protetto, fatto da un'identità separata, no. Per questo l'approvazione è il merge della PR di design, e per questo il
  template della CI esegue i controlli di processo sulle PR.
- **Proporzionato, non uniforme.** I livelli S/M/L tolgono cerimonia alle modifiche piccole e aggiungono attenzione a
  quelle rischiose.
- **Stato su file.** Spec, piani, task e review sono file versionati; la chat non è una fonte di verità.
- **Un contenuto, tre agenti, due sistemi operativi.** Il formato Agent Skills è comune a Claude Code, Codex e GitHub
  Copilot; gli script evitano i comandi di shell, così Windows nativo funziona come Linux.

**Cosa non fa, per scelta:** non approva al posto dell'umano, non lancia il loop da dentro una sessione, non configura i
permessi dell'agente (ne fornisce un esempio), non copre rilascio, sicurezza dell'infrastruttura e operazione
(playbook §8).

## Cosa contiene

| Parte | Contenuto | Dettaglio |
|---|---|---|
| 14 skill | `sdd-next`, `sdd-init`, `sdd-map-codebase`, `sdd-characterize`, `sdd-spec`, `sdd-plan`, `sdd-tasks`, `sdd-tests-from-ac`, `sdd-implement`, `sdd-bugfix`, `sdd-review-diff`, `sdd-docs`, `sdd-sync`, `sdd-loop` | [docs/skills_IT.md](docs/skills_IT.md) |
| 12 script Python | `verify`, `state`, `spec_lint`, `trace_check`, `bug_lint`, `diff_scope`, `scan_repo`, `docs_check`, `sync_check`, `loop`, `secrets_check`, `review_package` | [docs/scripts_IT.md](docs/scripts_IT.md) |
| 2 hook opzionali | `Stop` (verify obbligatorio) e `PreToolUse` (guard), solo Claude Code | [docs/scripts_IT.md](docs/scripts_IT.md#hook-opzionali-solo-claude-code) |
| 1 agente revisore | `sdd-reviewer`, revisore indipendente con soli strumenti di lettura: subagent di Claude Code e custom agent di GitHub Copilot | [docs/architecture_IT.md](docs/architecture_IT.md) |
| Playbook | Il processo, con template e script identici a quelli del plugin | [docs/playbook-ai-software-lifecycle_IT.md](docs/playbook-ai-software-lifecycle_IT.md) |

## Flusso

```
sdd-init → [sdd-map-codebase → sdd-characterize]* → sdd-spec → sdd-plan → sdd-tasks
          → sdd-implement (o sdd-loop) → sdd-review-diff → sdd-docs → sdd-sync → PR
sdd-bugfix: per i difetti, in parallelo al flusso.   sdd-next: in ogni momento.   * solo nel brownfield
```

Il processo è proporzionato al rischio: la spec dichiara un **livello** S, M o L (playbook §2.1). S salta piano e
`review.md`; L aggiunge ADR e revisione umana del diff; `diff_scope.py` segnala un diff che supera il livello dichiarato.
I test scritti dagli AC si bloccano con un commit `Test-Lock` e, nei livelli M e L, li approva l'umano prima
dell'implementazione, con lo SHA del commit approvato; con il report JUnit di `verify`, `trace_check.py --junit` conta
solo i test eseguiti e passati. Sicurezza di base: `secrets_check.py` come step di `verify`, dipendenze nuove solo nel
piano o con un ADR (`diff_scope.py`), permessi d'esempio per il loop (`skills/sdd-loop/references/settings.loop.json`).

Ogni skill che produce un documento da approvare termina con uno **STOP**: l'agente non avanza e non approva da solo.
Le approvazioni (spec, piano, test, decisione sulla review) portano nome e data e sono controllate dagli script.

## Avvio rapido

1. Installa il plugin (sotto).
2. Nel repository del progetto chiedi all'agente di usare `sdd-init`. Copia gli script in `scripts/` e crea
   `AGENTS.md`, `docs/`, il task VS Code e la CI.
3. `python scripts/state.py` (o la skill `sdd-next`) dice a che punto sei e qual è il passo successivo.
4. Prosegui con `sdd-spec` (greenfield) oppure `sdd-map-codebase` (codice esistente).

Il percorso completo, greenfield e brownfield, è nella [guida rapida](docs/quick-guide_IT.md).

Gli script restano **nel progetto**: la verifica in CI e da VS Code funziona anche senza il plugin. Ognuno porta la
versione del plugin in seconda riga; per aggiornarli chiedi a `sdd-init` di confrontarli (non tocca gli `STEPS` di
`verify.py`).

## Documentazione

| Documento | English | Italiano |
|---|---|---|
| Guida rapida | [docs/quick-guide.md](docs/quick-guide.md) | [docs/quick-guide_IT.md](docs/quick-guide_IT.md) |
| Playbook (il processo) | [docs/playbook-ai-software-lifecycle.md](docs/playbook-ai-software-lifecycle.md) | [docs/playbook-ai-software-lifecycle_IT.md](docs/playbook-ai-software-lifecycle_IT.md) |
| Riferimento delle skill | [docs/skills.md](docs/skills.md) | [docs/skills_IT.md](docs/skills_IT.md) |
| Riferimento di script e hook | [docs/scripts.md](docs/scripts.md) | [docs/scripts_IT.md](docs/scripts_IT.md) |
| Architettura, contratti, limiti | [docs/architecture.md](docs/architecture.md) | [docs/architecture_IT.md](docs/architecture_IT.md) |
| Storia delle modifiche | [CHANGELOG.md](CHANGELOG.md) | [CHANGELOG_IT.md](CHANGELOG_IT.md) |
| Review critica e stato delle correzioni | [REVIEW.md](REVIEW.md) | [REVIEW_IT.md](REVIEW_IT.md) |

**Lingua.** Documentazione, changelog e review esistono in inglese e in italiano (suffisso `_IT`). Il plugin vero e
proprio (skill, template, script, hook, agente, test) è interamente in inglese; i nomi dei campi che usa (`- Status:`,
`- Level:`, `tests approved:`, `expected: red`, ...) sono contratti sui file letti dagli script e non vanno tradotti.

## Installazione

**Claude Code**
- Prova locale: `claude --plugin-dir <percorso>/sdd-playbook`
- Marketplace: `/plugin marketplace add jumping2000/sdd-playbook`, poi
  `/plugin install sdd-playbook@sdd-playbook-marketplace`.
- Le skill sono richiamabili con il prefisso del plugin; gli hook e il subagent si caricano con il plugin.

**Codex**
- Il manifest è `.codex-plugin/plugin.json`. Il file di marketplace per Codex non è incluso: il formato va
  verificato sulla documentazione.
- Alternativa documentata per le sole skill: copia le cartelle di `skills/` in `.agents/skills/` del repository
  o della home. Le skill che citano `../sdd-init/scripts/` e `../sdd-sync/references/` richiedono che le
  cartelle restino sorelle.
- Hook e subagent non sono previsti per Codex: la review indipendente si fa in una sessione nuova (vedi `sdd-review-diff`).

**GitHub Copilot**
- **Copilot CLI (plugin):** il `plugin.json` nella radice (formato Agent Plugins) dichiara le skill e l'agente revisore.
  Installazione con `copilot plugin install jumping2000/sdd-playbook`, oppure aggiungendo il marketplace con
  `copilot plugin marketplace add jumping2000/sdd-playbook` (la CLI legge anche `.claude-plugin/marketplace.json`).
- **Cloud agent, VS Code, Visual Studio (file di progetto):** `sdd-init` chiede quali agenti usa il team e, per Copilot,
  copia le skill in `.github/skills/` e il revisore in `.github/agents/sdd-reviewer.agent.md` (solo strumenti `read` e
  `search`). Copilot legge direttamente `AGENTS.md`, quindi le regole del progetto e il comando `verify` valgono così come
  sono.
- **Limiti:** gli hook `Stop` e `PreToolUse` non sono portati su Copilot (gli hook di Copilot hanno un formato diverso e
  nessun evento di stop bloccante): la rete di sicurezza è la CI, la protezione dei branch e i permessi dell'agente. Loop
  con `--agent` impostato sulla Copilot CLI: non verificato. Nessuno dei percorsi Copilot è ancora stato provato (vedi lo
  stato sotto).

## Configurazione

| Variabile | Effetto | Default |
|---|---|---|
| `SDD_ENFORCE_VERIFY=1` | Abilita l'hook `Stop`: l'agente non può fermarsi con `verify` rosso | spento |
| `SDD_VERIFY_ARGS` | Argomenti di `verify.py` per l'hook `Stop` (es. `--fast`) | vuoto (verifica completa) |
| `SDD_STOP_MAX` | Quante volte di fila l'hook `Stop` blocca nella stessa sessione prima di lasciar fermare l'agente | 3 |
| `SDD_GUARD=1` | Abilita l'hook `PreToolUse`: blocca comandi e letture a rischio (fail-closed) | spento |

**Approvazioni.** Per un controllo che l'agente non può aggirare, dagli un'identità separata (nessun diritto di push,
oppure un account bot o token senza diritti di merge) e proteggi `main` con PR, review dei code owner e CI obbligatorie.
`sdd-init` crea `.github/CODEOWNERS`, il template della PR e la CI con i controlli di processo sulle PR; le regole del
branch le imposti tu. Dettagli: playbook §1.2.

Gli hook partono da `hooks/run.sh`, che usa il primo tra `python3`, `python` e `py -3` e richiede `sh` (su Windows quello
di Git for Windows). In fase rossa (ultima task chiusa "expected: red") l'hook `Stop` non blocca.

## Modificare il plugin

- Il playbook si modifica in `docs/playbook.src.md` (inglese) e `docs/playbook_IT.src.md` (italiano), con la stessa
  numerazione dei paragrafi; `python tools/build_playbook.py` rigenera entrambi. I blocchi `{{FILE ...}}` incorporano
  script e template del plugin: così non possono divergere.
- Test: `python -m unittest discover -s tests -v`. Includono i **test di coerenza** tra skill, script, playbook e
  documentazione in entrambe le lingue (riferimenti a §, nomi di skill e script, assenza di riferimenti a versioni nel
  playbook, ogni documento in due lingue, link).
- CI: `.github/workflows/ci.yml` esegue i test su Ubuntu e Windows.

## Stato della verifica

| Cosa | Esito |
|---|---|
| Suite di test | Passa su Linux (comprende loop con agente finto, hook e launcher `run.sh`, script su repository git temporanei). Su Windows 11 verificata fino alla 0.8.0; dalla 0.9.0 la copre solo la matrice CI `windows-latest`, il cui esito va controllato |
| `claude plugin validate .` | Passava sulla 0.4.0 (Claude Code 2.1.303, avvisi su `author`); **non rieseguito** dalla 0.5.0 con il nuovo `hooks.json` |
| Manifest Codex | **Non validato** con uno strumento Codex |
| GitHub Copilot (`plugin.json`, `.github/skills/`, custom agent) | **Non provato**: costruito dalla documentazione pubblica e da esempi (il sito di documentazione di GitHub non era raggiungibile dall'ambiente di build) |
| Versione di Python | 3.8+ dall'analisi del codice (solo libreria standard); la CI usa la 3.12 |
| Skill eseguite da un agente reale su un progetto | **Non fatto**: va provato su un greenfield e su un brownfield di esempio |
| Hook in una sessione reale di Claude Code | **Non fatto**: provati solo come script con l'input JSON atteso |
| `loop.py` con `claude -p` reale | **Non fatto**: provato con un agente finto |
| Workflow CI generato da `sdd-init` | **Non eseguito** (YAML validato, step dei controlli di processo mai eseguito su una PR reale) |

Dettagli e limiti noti: [docs/architecture_IT.md](docs/architecture_IT.md). Storia delle modifiche: [CHANGELOG_IT.md](CHANGELOG_IT.md).

## Da completare prima di distribuirlo

- Provare le skill su un repository di esempio (greenfield e brownfield) e correggere ciò che un agente reale interpreta
  male: il percorso di prova è in fondo alla [guida rapida](docs/quick-guide_IT.md).
- Verificare su Codex: formato del marketplace, invocazione esplicita delle skill, eventuale supporto di subagent.
- Verificare su GitHub Copilot: installazione del plugin dalla CLI, skill in `.github/skills/`, custom agent
  `sdd-reviewer`, `loop.py` con la Copilot CLI come `--agent`.

## Licenza

[MIT](LICENSE) © 2026 jumping2000
