# Architettura del plugin

*English version: [architecture.md](architecture.md)*

Documento di progetto **come costruito** (versione 0.16.0): scelte, struttura, contratti tra i file e limiti.

## Obiettivo e criterio di successo

Accompagnare lo sviluppatore lungo il ciclo del [playbook](playbook-ai-software-lifecycle_IT.md), trasformando ogni fase in
una skill con gate umano esplicito e, dove possibile, con un controllo eseguibile al posto di un'istruzione in prosa.
Il plugin è fatto bene se:
1. su un repository vuoto `sdd-init` produce `AGENTS.md`, `scripts/verify.py`, task VS Code, struttura `docs/` e CI;
2. ogni skill produce un artefatto verificabile (file, test, esito di script), non solo testo in chat;
3. lo stesso contenuto funziona in Claude Code, Codex e GitHub Copilot, su Windows nativo e Linux;
4. lavorare con le skill non richiede di ripetere il playbook all'agente.

## Scelte di architettura

| Tema | Scelta | Motivo |
|---|---|---|
| Unità di contenuto | **Skill** (`SKILL.md` con `name` e `description`) | Il formato Agent Skills è comune a Claude Code, Codex e GitHub Copilot |
| Packaging | Un repository, **tre manifest** (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `plugin.json` nella radice in formato Agent Plugins per la Copilot CLI) sulle stesse skill | Un solo corpo di contenuti, tre porte d'ingresso |
| Controlli | **Script Python deterministici** nel `scripts/` del progetto | Un check che gira vale più di una regola in prosa; CI e VS Code li usano senza il plugin |
| Dove vivono gli script | In `skills/sdd-init/scripts/`, copiati nel progetto da `sdd-init`, con la versione del plugin in seconda riga | Percorso fisso (`python scripts/...`) uguale in entrambi gli agenti; il progetto resta verificabile senza il plugin |
| Portabilità | Solo libreria standard, nessun comando di shell, liste di argomenti; le skill non leggono mai i file di un'altra skill con `../` ma li trovano con una ricerca | Windows nativo incluso |
| Contesto | `SKILL.md` sotto le 150 righe; template in `references/` | Il contesto è una risorsa scarsa |
| Gate umani | Ogni skill che produce un documento da approvare termina con **STOP**; le approvazioni portano nome, data e hash del contenuto approvato (che decade se il contenuto cambia); l'approvazione vera è il merge della PR di design su `main` protetto, che l'agente non può fare con un'identità separata | Principio 5 del playbook; i campi testuali li può scrivere l'agente, il merge no |
| Proporzionalità | Livelli **S/M/L** dichiarati nella spec (e nel suo hash), con criteri in parte controllati sul diff (`diff_scope.py`) | Lo stesso processo per una riga e per una migrazione genera cerimonia sulle prime e poca attenzione sulle seconde (REVIEW A6) |
| Controllo esterno | La CI generata da `sdd-init` esegue sulle PR i controlli di processo (`spec_lint --base`, `diff_scope`, `trace_check --junit`, `secrets_check`) con script e `AGENTS.md` protetti da CODEOWNERS | Ogni input del ramo è modificabile dall'agente; la CI sulla PR gira fuori dalla sua portata |
| Review indipendente | Per task nel livello L (facoltativa nel livello M, `- Task review: on`) e per feature, sempre con lo stesso `sdd-reviewer` in sola lettura; `review_package.py` mette in un solo file ciò che serve al revisore; le review per task superate sono controllate da `state.py`, `sync_check.py` e `loop.py` | Una sola review alla fine di un diff grande trova gli errori tardi e perde i dettagli (REVIEW, sezione C); una review per task li ferma prima che la task successiva ci costruisca sopra, senza aggiungere un secondo agente da mantenere |
| Skill con effetti | `sdd-loop` prepara ma non lancia; i commit solo se autorizzati, mai su `main` | Limitare i danni di un agente autonomo |
| Parti per singolo agente | Claude Code: subagent `sdd-reviewer` (solo strumenti di lettura) e hook opt-in. GitHub Copilot: lo stesso revisore come custom agent (`*.agent.md`, strumenti `read` e `search`), skill copiate in `.github/skills/` da `sdd-init` per il cloud agent e gli IDE. Codex: nessuna (review in sessione nuova) | Le skill restano uguali; cambia solo l'orchestrazione |
| Coerenza documentale | Il playbook è **generato** dai file del plugin (`tools/build_playbook.py`), in inglese e in italiano; i test controllano i riferimenti incrociati in entrambe le lingue | Script, template e documentazione non possono divergere in silenzio |
| Lingua | Documentazione, changelog e review in inglese e in italiano (suffisso `_IT`); il plugin (skill, template, script, hook, agente, test) interamente in inglese | Una sola lingua per i contratti sui file (nomi dei campi letti dagli script), indipendente dalla lingua della documentazione |

## Struttura del repository

```
sdd-playbook/
├── README.md, README_IT.md, CHANGELOG.md, CHANGELOG_IT.md, REVIEW.md, REVIEW_IT.md, LICENSE (MIT)
├── .claude-plugin/        plugin.json, marketplace.json
├── .codex-plugin/         plugin.json
├── plugin.json            manifest per la Copilot CLI (formato Agent Plugins)
├── skills/
│   ├── sdd-init/         SKILL.md, scripts/ (12 script), references/ (template, CI, tasks.json, stack, copilot/)
│   ├── sdd-map-codebase/ SKILL.md, references/map-template.md
│   ├── sdd-characterize/ SKILL.md
│   ├── sdd-spec/         SKILL.md, references/spec-template.md
│   ├── sdd-plan/         SKILL.md, references/plan-template.md
│   ├── sdd-tasks/        SKILL.md, references/tasks-template.md
│   ├── sdd-tests-from-ac/ SKILL.md, references/test-conventions.md
│   ├── sdd-implement/    SKILL.md
│   ├── sdd-bugfix/       SKILL.md, references/bugfix-template.md
│   ├── sdd-review-diff/  SKILL.md, references/review-template.md
│   ├── sdd-docs/         SKILL.md
│   ├── sdd-sync/         SKILL.md, references/area-template.md
│   ├── sdd-loop/         SKILL.md, references/PROMPT.md.tmpl, progress.md.tmpl, settings.loop.json
│   └── sdd-next/         SKILL.md
├── agents/sdd-reviewer.md       subagent (Claude Code); copia per Copilot in skills/sdd-init/references/copilot/
├── hooks/                        hooks.json, run.sh (launcher), stop_verify.py, pretool_guard.py (Claude Code, opt-in)
├── docs/                         in inglese e in italiano (_IT): guida rapida, playbook (sorgente e generato),
│                                 skill, script, architettura
├── tools/build_playbook.py       genera i due playbook dai file del plugin
├── tests/                        test degli script, degli hook, del loop e di coerenza
└── .github/workflows/ci.yml      test su Ubuntu e Windows
```

Una skill legge i propri file con percorsi relativi alla sua cartella e trova i file di un'altra skill con una ricerca
(`**/sdd-sync/references/area-template.md`), mai con `../`: un host può installare le skill una per una o aggiungere un
prefisso al nome della cartella. I test di coerenza rifiutano `../` nei file delle skill e controllano ogni percorso
citato.

## Macchina a stati (`state.py`)

```
senza AGENTS.md / verify.py ............................ sdd-init
codice esistente, senza mappa e senza spec .............. sdd-map-codebase
nessuna spec attiva ..................................... sdd-spec
più spec attive, nessuna scelta (branch o --spec) ....... choose (lo decide l'utente)
--- per la spec scelta ---
spec in-revision ....................................... sdd-spec
spec in bozza, non approvata o con hash non valido ...... sdd-spec
--- livello S: niente piano né review.md -----------------
tasks.md mancante ....................................... sdd-tasks
task T-nn o T-Rnn aperte ................................ sdd-implement
review.md "non-compliant" (se c'è) ....................... sdd-review-diff
T-DOC aperta, altrimenti ................................ sdd-docs, sdd-sync
--- livelli M (default) e L ------------------------------
piano mancante, non approvato o decaduto ................ sdd-plan
tasks.md mancante o basato su un altro piano ............ sdd-tasks
task di test chiusa senza "tests approved:" ............. sdd-tests-from-ac
task T-nn o T-Rnn aperte ................................ sdd-implement   (valuta sdd-loop)
review.md mancante o senza esito valido ................. sdd-review-diff
review "non-compliant" senza T-R ......................... sdd-review-diff (crea le T-R)
review "non-compliant" con T-R tutte chiuse .............. sdd-review-diff (ripeti la review)
livello L senza "Human diff review" .............. sdd-review-diff
T-DOC aperta ............................................ sdd-docs
altrimenti (T-SYNC aperta o stato non implemented) ...... sdd-sync
```

La spec scelta è quella di `--spec`, quella il cui nome di cartella compare nel branch corrente, o l'unica attiva. Una
spec con `Status: implemented` o `superseded` non è più attiva. I bug non verificati sono segnalati a parte
(`sdd-bugfix`): la priorità la decide l'umano.

## Contratti sui file

Gli script leggono pochi campi con convenzioni fisse. I nomi dei campi sono in inglese e fanno parte del contratto. Se si cambia un template va cambiato anche lo script che lo legge
(i test lo verificano).

| File | Campi e strutture lette | Script |
|---|---|---|
| `spec.md` | titolo `# SPEC-<id>: ...` (data + slug uguale alla cartella, o numero); `- Level:` (`S`, `M`, `L`; M se manca; letto solo dall'intestazione; entra nell'hash); `- Status:` (`draft`, `approved`, `in-revision`, `implemented`, `superseded`); sezione `## Revisions` (obbligatoria con voce se `in-revision`); `- Approved by / date:`; `- Hash: sha256:...` del corpo (dalla prima sezione `## `); sezioni `## Problem and goal`, `Scope`, `Requirements`, `Acceptance criteria`, `Open questions`; riga `**Non-scope (explicit):**`; riga `**Anti-goals:**` (avviso se manca); `- REQ-nnn`; `- AC-nnn [REQ-nnn]`; marcatore `[ASSUMPTION]`; domande aperte `- <domanda> — blocking: yes|no — about: REQ-nnn, AC-nnn` | `spec_lint`, `state`, `trace_check`, `sync_check`, `diff_scope` |
| `plan.md` | `- Approved by / date:`; `- Based on spec:` (hash della spec); `- Hash:` del corpo; sezione `## Components and files to create/modify` con righe `- path: ...` (percorso = prima parola o testo tra backtick); sezione `## Test strategy ...` con gli ID AC esatti e, se c'è, la colonna `Where`; sezione `## Review focus` (tabella con colonna `Where`, oppure `- none`) | `spec_lint`, `state`, `diff_scope` |
| `tasks.md` | `- Based on plan:` (hash del piano); righe `- [ ] T-nn ...` con i campi `verify:` (comando tra backtick) e `covers:` (ID degli AC), senza segnaposto; righe `- [ ] T-Rnn ...` dai problemi della review (`verify:`, `covers:` facoltativo); `T-DOC`, `T-SYNC`; `— tests approved: <name, yyyy-mm-dd, sha>` sulle task di test chiuse (livelli M e L; sha = commit `Test-Lock` approvato); la marcatura `expected: red` (senza distinzione di maiuscole) sulle task di test definisce la **fase rossa** (ultima task `T-nn` chiusa con la marcatura, successiva aperta) | `spec_lint`, `state`, `loop`, `sync_check`, `diff_scope`, hook `Stop` |
| commit git | trailer `Test-Lock: T-nn` sul commit dei test rossi: blocca i suoi file di test e ancora l'approvazione; trailer `Task: T-nn` sui commit di implementazione | `diff_scope`, `review_package` |
| file di test | `# SPEC-<id>` nel file più `AC-nnn`, oppure citazioni `SPEC-<id>/AC-nnn` (nei nomi di funzione `SPEC_<id con _>_AC_nnn`); righe `TODO`/`FIXME`/`XXX` ignorate | `trace_check`, `sync_check` |
| cartelle `docs/specs/<id>/` | `<id>` = data + slug (`2026-10-24-export-csv`), uguale all'ID del titolo; i vecchi `NNN-slug` restano validi | `spec_lint`, `state` (associazione al branch) |
| report JUnit XML (`reports/junit.xml`) | `testcase` con `name`, `classname`, `file` e figli `failure`, `error`, `skipped` | `trace_check --junit`, `sync_check --junit`, `loop --junit` |
| `review.md` | `- Outcome:` (`compliant`, `compliant with reservations`, `non-compliant`); `- Decided by:`; `- Human diff review:` (livello L) | `state`, `sync_check` |
| `docs/bugs/BUG-*.md` | `- Status:` (`open`, `diagnosed`, `fixed`, `verified`); sezioni di `bugfix-template.md`; voci spuntabili in `## Closure` | `bug_lint`, `state` |
| `docs/system/<area>.md` | `- Last aligned:`; `- Linked specs:`; sezioni `## Current behaviour`, `Constraints and delicate points`, `Characterization tests` | `sync_check` |
| `docs/system/map.md` | solo la presenza | `state` |
| `AGENTS.md` | righe `- Do not modify: a, b` e `- Sensitive areas: a, b` (richiedono il livello L), percorsi tra backtick o prima parola; lette dal merge-base. Sezione `## Decision rights` con `### Decides alone`, `### Asks first`, `### Never` (letta dagli agenti, non dagli script) | `diff_scope`; `sdd-implement`, loop, `sdd-reviewer` |
| `docs/glossary.md` (facoltativo) | tabella con le colonne `Term` e `Avoid` (sinonimi separati da virgola) | `spec_lint` |
| `PROMPT.md`, `progress.md` | `PROMPT.md` letto per intero e passato da stdin; in `progress.md`: `- Task review: on` (livello M), `## Task reviews` con `- T-nn: pass` per ogni task chiusa (livello L, o M se attiva), `## Rulings` e `## Disputed review findings` lette dal revisore | `loop`, `state`, `sync_check`, `review_package`, `sdd-reviewer` |
| `scripts/verify.py` | lista `STEPS` | (modificata da `sdd-init`) |
| `scripts/*.py` | seconda riga `# sdd-playbook: <versione>` | `sdd-init` (aggiornamento), test di coerenza |
| manifest e lockfile (`package.json`, `pyproject.toml`, `*.csproj`, ...) | solo il nome del file | `diff_scope` (livello, dipendenze senza piano né ADR) |
| `.secrets-ignore` | un glob per riga, `#` per i commenti | `secrets_check` |

Un campo con segnaposto `<...>` o vuoto vale come **non compilato**.

## Differenze tra Claude Code, Codex e GitHub Copilot

| Aspetto | Claude Code | Codex | GitHub Copilot |
|---|---|---|---|
| Skill | sì, richiamabili con il prefisso del plugin | sì (formato Agent Skills); manifest in `.codex-plugin/` | Copilot CLI: plugin dal `plugin.json` nella radice; cloud agent e IDE: `.github/skills/` copiate da `sdd-init` |
| Revisore `sdd-reviewer` | subagent | no: la review si fa in una sessione nuova con le stesse istruzioni | custom agent `.github/agents/sdd-reviewer.agent.md` (strumenti `read`, `search`) |
| Hook `Stop` e `PreToolUse` | sì, opt-in con variabili d'ambiente | non previsti | non portati (formato diverso, nessun evento di stop bloccante) |
| Loop | `claude -p` di default | `--agent "<comando>"`: modalità non interattiva e permessi da verificare | `--agent "<comando della Copilot CLI>"`: non verificato |
| Contesto del progetto | `CLAUDE.md` con `@AGENTS.md` | legge `AGENTS.md` | legge `AGENTS.md` |

## Sicurezza e supply chain

- Le skill istruiscono l'agente e gli script girano con i permessi dell'utente: distribuisci il plugin da un repository interno,
  con review obbligatoria, versione fissata per progetto e aggiornamenti via PR.
- Nessuno script scarica o esegue codice da rete. `docs_check.py --run-examples` esegue solo blocchi Python esplicitamente marcati.
- Gli hook sono inattivi di default e non sono un sandbox. Il guard blocca anche con un evento illeggibile (fail-closed). Il loop
  richiede ambiente isolato, permessi configurati a parte (esempio: `settings.loop.json`) e un branch di feature; non fa push.
- Sicurezza del codice prodotto (REVIEW A7): `secrets_check.py` come step di `verify` e controllo finale del loop; nuove dipendenze
  solo nel piano approvato o con un ADR (`diff_scope.py`); audit delle dipendenze per stack documentato, non incluso (richiede rete).
- Prompt injection: `PROMPT.md` e il revisore trattano il contenuto del repository come dato; la difesa vera è l'assenza di segreti
  e di permessi di rete e push nell'ambiente dell'agente.
- La CI generata da `sdd-init` usa action fissate per tag major (`checkout@v6`, `setup-python@v6`, su Node 24): in contesti
  regolati fissale per SHA.

## Limiti e punti non verificati

- **Stato:** il plugin è in progettazione e non è stato usato su un progetto reale; formati e contratti possono ancora
  cambiare senza compatibilità.
- **Windows:** suite eseguita su Windows 11 (Python 3.13, console cp1252) fino alla 0.8.0, poi solo nella matrice CI; i test di `run.sh` con PATH
  minimo e interpreti finti girano solo su POSIX.
- **Agenti reali:** le skill non sono state eseguite da un agente reale su un progetto; i controlli deterministici sì (test su repository
  temporanei, loop con agente finto, hook con l'input JSON atteso).
- **Codex:** manifest e invocazione delle skill non validati con strumenti Codex; supporto dei subagent non verificato.
- **GitHub Copilot:** `plugin.json` nella radice, skill in `.github/skills/` e custom agent costruiti dalla documentazione
  pubblica e da esempi (il sito di documentazione di GitHub non era raggiungibile dall'ambiente di build); nessuno è stato
  provato con Copilot. Se la Copilot CLI legge anche `hooks/hooks.json`, i comandi girerebbero senza `CLAUDE_PLUGIN_ROOT`
  e gli hook non partirebbero: non verificato.
- **Hook di Claude Code:** codice di uscita 2 come blocco e formato del JSON sono quelli attesi, non osservati in una sessione.
  Il comando passa da `sh hooks/run.sh`: su Windows richiede che Claude Code esegua gli hook con una shell che trovi `sh`
  (Git for Windows); non verificato in una sessione reale.
- **Approvazioni:** l'hash ferma la deriva involontaria, non un agente che ricalcola l'hash e riscrive il campo. Contro
  questo servono il merge su `main` protetto con un'identità separata (`spec_lint.py --base`) e i controlli di processo in CI: la protezione del branch e
  CODEOWNERS vanno configurati sulla piattaforma, il plugin fornisce solo i template.
- **Fase rossa, `Test-Lock` e `tests approved:`:** si basano su convenzioni (marcatura nelle task, trailer nei commit) che
  l'agente potrebbe usare a sproposito; `diff_scope.py` lega l'approvazione allo SHA `Test-Lock`, ma `tests approved:` resta
  testo che l'agente può scrivere: il controllo che non può aggirare è la review dei code owner su `tests/` nella PR di implementazione.
- **Report JUnit:** dice quali test sono stati eseguiti e con che esito, non che il report sia di quel commit: va
  generato da `verify` nello stesso passaggio (in CI, da un job che l'agente non controlla). L'attribuzione dei casi
  ai file usa `file` e `classname`: con reporter che non li valorizzano servono le citazioni qualificate.
- **`claude -p` da stdin:** la lettura del prompt da stdin con `-p` va verificata sulla versione in uso.
- **Euristiche:** `diff_scope.py` dipende dal formato `- path: ...` del piano, e per il livello conta file e riconosce i manifest per nome: non capisce se un'interfaccia pubblica è cambiata; `trace_check.py` trova gli ID per testo
  (qualificati per spec) e non capisce la semantica dei test; senza `--junit` non controlla che siano eseguiti e passino; `scan_repo.py` è un inventario; nessuno sostituisce la lettura del codice.
- **Guard e segreti:** il guard analizza i comandi per parole e segmenti, ma un comando costruito apposta (variabili, `eval`,
  script scritti su file) lo aggira; `secrets_check.py` riconosce solo formati noti e non legge la storia di git.
- **Revisore:** senza Bash non può eseguire test né comandi; riceve diff e output nel messaggio, quindi giudica ciò che gli
  viene passato. Stesso modello di chi implementa salvo `model:` diverso nel frontmatter (non verificato in una sessione).
- **Perimetro:** il plugin non copre rilascio, sicurezza dell'infrastruttura, osservabilità e operazione (§8 del playbook), non
  configura i permessi dell'agente (ne fornisce un esempio per il loop), non approva al posto dell'umano.

## Test e coerenza

`python -m unittest discover -s tests -v`. Oltre ai test degli script (su repository git temporanei), del loop (con un agente
finto che spunta una task per esecuzione) e degli hook, i **test di coerenza** verificano che:
- ogni `SKILL.md` abbia frontmatter valido, `name` uguale alla cartella e meno di 150 righe;
- ogni `python scripts/<x>.py` citato esista e ogni script sia documentato, in entrambe le lingue;
- ogni skill sia nei due README, nei due riferimenti delle skill, nelle due guide rapide e nei due playbook, e ogni skill
  citata esista;
- ogni `§` citato esista come titolo del playbook, e i due playbook abbiano la stessa numerazione;
- i due playbook siano aggiornati rispetto ai file incorporati (`tools/build_playbook.py --check`) e non contengano riferimenti a versioni;
- ogni documento (changelog e review compresi) esista in inglese e in italiano, e ognuno rimandi all'altra lingua;
- i file del plugin (skill, agente, hook, tools, test, manifest) non contengano testo italiano;
- i tre manifest, i due changelog e i due README abbiano la stessa versione (badge del README compreso), ogni script la
  riporti in seconda riga, e la licenza sia MIT;
- il revisore (Claude Code e Copilot) non abbia strumenti di scrittura, i permessi d'esempio del loop neghino il push e la scrittura dei controlli,
  e le action della CI non usino
  versioni su Node 20;
- i link relativi della documentazione siano validi (`docs_check.py`).

## Evoluzioni possibili

Rilascio e operazione (§8 del playbook), integrazione con i tracker, un file di marketplace per Codex, gli hook per Copilot,
un'analisi multi-repository.
Non sono documentate né implementate in questa versione.
