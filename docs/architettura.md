# Architettura del plugin

Documento di progetto **come costruito** (versione 0.11.0): scelte, struttura, contratti tra i file e limiti.

## Obiettivo e criterio di successo

Accompagnare lo sviluppatore lungo il ciclo del [playbook](playbook-ai-software-lifecycle.md), trasformando ogni fase in
una skill con gate umano esplicito e, dove possibile, con un controllo eseguibile al posto di un'istruzione in prosa.
Il plugin è fatto bene se:
1. su un repository vuoto `sdlc-init` produce `AGENTS.md`, `scripts/verify.py`, task VS Code, struttura `docs/` e CI;
2. ogni skill produce un artefatto verificabile (file, test, esito di script), non solo testo in chat;
3. lo stesso contenuto funziona in Claude Code e in Codex, su Windows nativo e Linux;
4. lavorare con le skill non richiede di ripetere il playbook all'agente.

## Scelte di architettura

| Tema | Scelta | Motivo |
|---|---|---|
| Unità di contenuto | **Skill** (`SKILL.md` con `name` e `description`) | Il formato Agent Skills è comune a Claude Code e Codex |
| Packaging | Un repository, **due manifest** (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`) sulle stesse skill | Un solo corpo di contenuti, due porte d'ingresso |
| Controlli | **Script Python deterministici** nel `scripts/` del progetto | Un check che gira vale più di una regola in prosa; CI e VS Code li usano senza il plugin |
| Dove vivono gli script | In `skills/sdlc-init/scripts/`, copiati nel progetto da `sdlc-init`, con la versione del plugin in seconda riga | Percorso fisso (`python scripts/...`) uguale in entrambi gli agenti; il progetto resta verificabile senza il plugin |
| Portabilità | Solo libreria standard, nessun comando di shell, liste di argomenti | Windows nativo incluso |
| Contesto | `SKILL.md` sotto le 150 righe; template in `references/` | Il contesto è una risorsa scarsa |
| Gate umani | Ogni skill che produce un documento da approvare termina con **STOP**; le approvazioni portano nome, data e hash del contenuto approvato (che decade se il contenuto cambia); l'approvazione vera è il merge della PR di design su `main` protetto, che l'agente non può fare con un'identità separata | Principio 5 del playbook; i campi testuali li può scrivere l'agente, il merge no |
| Proporzionalità | Livelli **S/M/L** dichiarati nella spec (e nel suo hash), con criteri in parte controllati sul diff (`diff_scope.py`) | Lo stesso processo per una riga e per una migrazione genera cerimonia sulle prime e poca attenzione sulle seconde (REVIEW A6) |
| Skill con effetti | `sdlc-loop` prepara ma non lancia; i commit solo se autorizzati, mai su `main` | Limitare i danni di un agente autonomo |
| Parti per singolo agente | Claude Code: subagent `sdlc-reviewer` (solo strumenti di lettura) e hook opt-in. Codex: nessuna (review in sessione nuova) | Le skill restano uguali; cambia solo l'orchestrazione |
| Coerenza documentale | Il playbook è **generato** dai file del plugin (`tools/build_playbook.py`) e i test controllano riferimenti incrociati | Script, template e documentazione non possono divergere in silenzio |

## Struttura del repository

```
sdlc-playbook/
├── .claude-plugin/        plugin.json, marketplace.json
├── .codex-plugin/         plugin.json
├── skills/
│   ├── sdlc-init/         SKILL.md, scripts/ (11 script), references/ (template, CI, tasks.json, stack)
│   ├── sdlc-map-codebase/ SKILL.md, references/mappa-template.md
│   ├── sdlc-characterize/ SKILL.md
│   ├── sdlc-spec/         SKILL.md, references/spec-template.md
│   ├── sdlc-plan/         SKILL.md, references/plan-template.md
│   ├── sdlc-tasks/        SKILL.md, references/tasks-template.md
│   ├── sdlc-tests-from-ac/ SKILL.md, references/convenzioni-test.md
│   ├── sdlc-implement/    SKILL.md
│   ├── sdlc-bugfix/       SKILL.md, references/bugfix-template.md
│   ├── sdlc-review-diff/  SKILL.md, references/review-template.md
│   ├── sdlc-docs/         SKILL.md
│   ├── sdlc-sync/         SKILL.md, references/area-template.md
│   ├── sdlc-loop/         SKILL.md, references/PROMPT.md.tmpl, progress.md.tmpl, settings.loop.json
│   └── sdlc-next/         SKILL.md
├── agents/sdlc-reviewer.md       subagent (Claude Code)
├── hooks/                        hooks.json, run.sh (launcher), stop_verify.py, pretool_guard.py (Claude Code, opt-in)
├── docs/                         playbook (sorgente e generato), skills.md, scripts.md, architettura.md
├── tools/build_playbook.py       genera il playbook dai file del plugin
├── tests/                        test degli script, degli hook, del loop e di coerenza
└── .github/workflows/ci.yml      test su Ubuntu e Windows
```

Alcune skill leggono file di altre skill con percorso relativo (`../sdlc-init/scripts/`, `../sdlc-sync/references/`):
le cartelle delle skill devono restare sorelle.

## Macchina a stati (`state.py`)

```
senza AGENTS.md / verify.py ............................ sdlc-init
codice esistente, senza mappa e senza spec .............. sdlc-map-codebase
nessuna spec attiva ..................................... sdlc-spec
più spec attive, nessuna scelta (branch o --spec) ....... scegli (lo decide l'utente)
--- per la spec scelta ---
spec in-revisione ....................................... sdlc-spec
spec in bozza, non approvata o con hash non valido ...... sdlc-spec
--- livello S: niente piano né review.md -----------------
tasks.md mancante ....................................... sdlc-tasks
task T-nn o T-Rnn aperte ................................ sdlc-implement
review.md "non conforme" (se c'è) ....................... sdlc-review-diff
T-DOC aperta, altrimenti ................................ sdlc-docs, sdlc-sync
--- livelli M (default) e L ------------------------------
piano mancante, non approvato o decaduto ................ sdlc-plan
tasks.md mancante o basato su un altro piano ............ sdlc-tasks
task di test chiusa senza "test approvati:" ............. sdlc-tests-from-ac
task T-nn o T-Rnn aperte ................................ sdlc-implement   (valuta sdlc-loop)
review.md mancante o senza esito valido ................. sdlc-review-diff
review "non conforme" senza T-R ......................... sdlc-review-diff (crea le T-R)
review "non conforme" con T-R tutte chiuse .............. sdlc-review-diff (ripeti la review)
livello L senza "Revisione umana del diff" .............. sdlc-review-diff
T-DOC aperta ............................................ sdlc-docs
altrimenti (T-SYNC aperta o stato non implemented) ...... sdlc-sync
```

La spec scelta è quella di `--spec`, quella il cui nome di cartella compare nel branch corrente, o l'unica attiva. Una
spec con `Stato: implemented` o `superseded` non è più attiva. I bug non verificati sono segnalati a parte
(`sdlc-bugfix`): la priorità la decide l'umano.

## Contratti sui file

Gli script leggono pochi campi con convenzioni fisse. Se si cambia un template va cambiato anche lo script che lo legge
(i test lo verificano).

| File | Campi e strutture lette | Script |
|---|---|---|
| `spec.md` | titolo `# SPEC-<id>: ...` (data + slug uguale alla cartella, o numero); `- Livello:` (`S`, `M`, `L`; M se manca; entra nell'hash); `- Stato:` (`draft`, `approved`, `in-revisione`, `implemented`, `superseded`); sezione `## Revisioni` (obbligatoria con voce se `in-revisione`); `- Approvata da / data:`; `- Hash: sha256:...` del corpo (dalla prima sezione `## `); sezioni `## Problema e obiettivo`, `Scope`, `Requisiti`, `Acceptance criteria`, `Domande aperte`; riga `**Non-scope (esplicito):**`; `- REQ-nnn`; `- AC-nnn [REQ-nnn]`; marcatore `[ASSUNZIONE]` | `spec_lint`, `state`, `trace_check`, `sync_check`, `diff_scope` |
| `plan.md` | `- Approvato da / data:`; `- Basato su spec:` (hash della spec); `- Hash:` del corpo; sezione `## Componenti e file da creare/modificare` con righe `- percorso: ...` (percorso = prima parola o testo tra backtick); sezione `## Strategia di test ...` con gli ID AC esatti e, se c'è, la colonna `Dove` | `spec_lint`, `state`, `diff_scope` |
| `tasks.md` | `- Basato su piano:` (hash del piano); righe `- [ ] T-nn ...` con i campi `verifica:` (comando tra backtick) e `copre:` (ID degli AC), senza segnaposto; righe `- [ ] T-Rnn ...` dai problemi della review (`verifica:`, `copre:` facoltativo); `T-DOC`, `T-SYNC`; `— test approvati: <nome, data>` sulle task di test chiuse (livelli M e L); la marcatura `atteso: rosso` sulle task di test definisce la **fase rossa** (ultima task `T-nn` chiusa con la marcatura, successiva aperta) | `spec_lint`, `state`, `loop`, `sync_check`, hook `Stop` |
| commit git | trailer `Test-Lock: T-nn` sul commit dei test rossi: blocca i suoi file di test | `diff_scope` |
| file di test | `# SPEC-<id>` nel file più `AC-nnn`, oppure citazioni `SPEC-<id>/AC-nnn` (nei nomi di funzione `SPEC_<id con _>_AC_nnn`); righe `TODO`/`FIXME`/`XXX` ignorate | `trace_check`, `sync_check` |
| cartelle `docs/specs/<id>/` | `<id>` = data + slug (`2026-10-24-export-csv`), uguale all'ID del titolo; i vecchi `NNN-slug` restano validi | `spec_lint`, `state` (associazione al branch) |
| report JUnit XML (`reports/junit.xml`) | `testcase` con `name`, `classname`, `file` e figli `failure`, `error`, `skipped` | `trace_check --junit`, `sync_check --junit`, `loop --junit` |
| `review.md` | `- Esito:` (`conforme`, `conforme con riserve`, `non conforme`); `- Decisione di:`; `- Revisione umana del diff:` (livello L) | `state`, `sync_check` |
| `docs/bugs/BUG-*.md` | `- Stato:` (`aperto`, `diagnosticato`, `corretto`, `verificato`); sezioni di `bugfix-template.md`; voci spuntabili in `## Chiusura` | `bug_lint`, `state` |
| `docs/system/<area>.md` | `- Ultimo allineamento:`; `- Specifiche collegate:`; sezioni `## Comportamento attuale`, `Vincoli e punti delicati`, `Test di caratterizzazione` | `sync_check` |
| `docs/system/mappa.md` | solo la presenza | `state` |
| `AGENTS.md` | righe `- Non modificare: a, b` e `- Aree sensibili: a, b` (richiedono il livello L) | `diff_scope` |
| `PROMPT.md`, `progress.md` | `PROMPT.md` letto per intero e passato da stdin | `loop` |
| `scripts/verify.py` | lista `STEPS` | (modificata da `sdlc-init`) |
| `scripts/*.py` | seconda riga `# sdlc-playbook: <versione>` | `sdlc-init` (aggiornamento), test di coerenza |
| manifest e lockfile (`package.json`, `pyproject.toml`, `*.csproj`, ...) | solo il nome del file | `diff_scope` (livello, dipendenze senza piano né ADR) |

Un campo con segnaposto `<...>` o vuoto vale come **non compilato**.

## Differenze tra Claude Code e Codex

| Aspetto | Claude Code | Codex |
|---|---|---|
| Skill | sì, richiamabili con il prefisso del plugin | sì (formato Agent Skills); manifest in `.codex-plugin/` |
| Subagent `sdlc-reviewer` | sì | no: la review si fa in una sessione nuova con le stesse istruzioni |
| Hook `Stop` e `PreToolUse` | sì, opt-in con variabili d'ambiente | non previsti |
| Loop | `claude -p` di default | `--agent "<comando>"`: modalità non interattiva e permessi da verificare |
| Contesto del progetto | `CLAUDE.md` con `@AGENTS.md` | legge `AGENTS.md` |

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
- La CI generata da `sdlc-init` usa action fissate per tag major (`checkout@v6`, `setup-python@v6`, su Node 24): in contesti
  regolati fissale per SHA.

## Limiti e punti non verificati

- **Windows:** suite eseguita su Windows 11 (Python 3.13, console cp1252) e nella matrice CI; i test di `run.sh` con PATH
  minimo e interpreti finti girano solo su POSIX.
- **Agenti reali:** le skill non sono state eseguite da un agente reale su un progetto; i controlli deterministici sì (test su repository
  temporanei, loop con agente finto, hook con l'input JSON atteso).
- **Codex:** manifest e invocazione delle skill non validati con strumenti Codex; supporto dei subagent non verificato.
- **Hook di Claude Code:** codice di uscita 2 come blocco e formato del JSON sono quelli attesi, non osservati in una sessione.
  Il comando passa da `sh hooks/run.sh`: su Windows richiede che Claude Code esegua gli hook con una shell che trovi `sh`
  (Git for Windows); non verificato in una sessione reale.
- **Approvazioni:** l'hash ferma la deriva involontaria, non un agente che ricalcola l'hash e riscrive il campo. Contro
  questo serve il merge su `main` protetto con un'identità separata (`spec_lint.py --base`): la protezione del branch e
  CODEOWNERS vanno configurati sulla piattaforma, il plugin fornisce solo i template.
- **Fase rossa e `Test-Lock`:** si basano su convenzioni (marcatura nelle task, trailer nei commit) che l'agente potrebbe
  usare a sproposito; la review umana resta il controllo finale. Anche `test approvati:` è testo che l'agente può
  scrivere: il controllo che non può aggirare è la review dei code owner su `tests/` nella PR di implementazione.
- **Report JUnit:** dice quali test sono stati eseguiti e con che esito, non che il report sia di quel commit: va
  generato da `verify` nello stesso passaggio (in CI, da un job che l'agente non controlla). L'attribuzione dei casi
  ai file usa `file` e `classname`: con reporter che non li valorizzano servono le citazioni qualificate.
- **`claude -p` da stdin:** la lettura del prompt da stdin con `-p` va verificata sulla versione in uso.
- **Euristiche:** `diff_scope.py` dipende dal formato `- percorso: ...` del piano, e per il livello conta file e riconosce i manifest per nome: non capisce se un'interfaccia pubblica è cambiata; `trace_check.py` trova gli ID per testo
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
- ogni `python scripts/<x>.py` citato esista e ogni script sia documentato;
- ogni skill sia in README, riferimento delle skill e playbook, e ogni skill citata esista;
- ogni `§` citato esista come titolo del playbook;
- il playbook sia aggiornato rispetto ai file incorporati (`tools/build_playbook.py --check`) e non contenga riferimenti a versioni;
- le versioni di manifest, changelog e README coincidano, e ogni script riporti la stessa versione in seconda riga;
- il revisore non abbia strumenti di scrittura, i permessi d'esempio del loop neghino il push e le action della CI non usino
  versioni su Node 20;
- i link relativi della documentazione siano validi (`docs_check.py`).

## Evoluzioni possibili

Rilascio e operazione (§8 del playbook), integrazione con i tracker, un file di marketplace per Codex, un'analisi multi-repository.
Non sono documentate né implementate in questa versione.
