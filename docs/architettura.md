# Architettura del plugin

Documento di progetto **come costruito** (versione 0.5.0): scelte, struttura, contratti tra i file e limiti.

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
| Dove vivono gli script | In `skills/sdlc-init/scripts/`, copiati nel progetto da `sdlc-init` | Percorso fisso (`python scripts/...`) uguale in entrambi gli agenti; il progetto resta verificabile senza il plugin |
| Portabilità | Solo libreria standard, nessun comando di shell, liste di argomenti | Windows nativo incluso |
| Contesto | `SKILL.md` sotto le 150 righe; template in `references/` | Il contesto è una risorsa scarsa |
| Gate umani | Ogni skill che produce un documento da approvare termina con **STOP**; le approvazioni portano nome e data e sono controllate dagli script | Principio 5 del playbook |
| Skill con effetti | `sdlc-loop` prepara ma non lancia; i commit solo se autorizzati, mai su `main` | Limitare i danni di un agente autonomo |
| Parti per singolo agente | Claude Code: subagent `sdlc-reviewer` e hook opt-in. Codex: nessuna (review in sessione nuova) | Le skill restano uguali; cambia solo l'orchestrazione |
| Coerenza documentale | Il playbook è **generato** dai file del plugin (`tools/build_playbook.py`) e i test controllano riferimenti incrociati | Script, template e documentazione non possono divergere in silenzio |

## Struttura del repository

```
sdlc-playbook/
├── .claude-plugin/        plugin.json, marketplace.json
├── .codex-plugin/         plugin.json
├── skills/
│   ├── sdlc-init/         SKILL.md, scripts/ (10 script), references/ (template, CI, tasks.json, stack)
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
│   ├── sdlc-loop/         SKILL.md, references/PROMPT.md.tmpl, progress.md.tmpl
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
spec in bozza o non approvata ........................... sdlc-spec
piano mancante o non approvato .......................... sdlc-plan
tasks.md mancante ....................................... sdlc-tasks
task T-nn aperte ........................................ sdlc-implement   (valuta sdlc-loop)
review.md mancante o senza esito valido ................. sdlc-review-diff
review "non conforme" ................................... sdlc-implement
T-DOC aperta ............................................ sdlc-docs
altrimenti (T-SYNC aperta o stato non implemented) ...... sdlc-sync
```

Una spec con `Stato: implemented` o `superseded` non è più attiva. I bug non verificati sono segnalati a parte
(`sdlc-bugfix`): la priorità la decide l'umano.

## Contratti sui file

Gli script leggono pochi campi con convenzioni fisse. Se si cambia un template va cambiato anche lo script che lo legge
(i test lo verificano).

| File | Campi e strutture lette | Script |
|---|---|---|
| `spec.md` | titolo `# SPEC-nnn: ...`; `- Stato:` (`draft`, `approved`, `implemented`, `superseded`); `- Approvata da / data:`; sezioni `## Problema e obiettivo`, `Scope`, `Requisiti`, `Acceptance criteria`, `Domande aperte`; riga `**Non-scope (esplicito):**`; `- REQ-nnn`; `- AC-nnn [REQ-nnn]`; marcatore `[ASSUNZIONE]` | `spec_lint`, `state`, `trace_check`, `sync_check` |
| `plan.md` | `- Approvato da / data:`; sezione `## Componenti e file da creare/modificare` con righe `- percorso: ...` (percorso = prima parola o testo tra backtick); sezione `## Strategia di test ...` con gli ID AC esatti e, se c'è, la colonna `Dove` | `spec_lint`, `state`, `diff_scope` |
| `tasks.md` | righe `- [ ] T-nn ...` con i campi `verifica:` (comando tra backtick) e `copre:` (ID degli AC), senza segnaposto; `T-DOC`, `T-SYNC`; la marcatura `atteso: rosso` sulle task di test definisce la **fase rossa** (ultima task `T-nn` chiusa con la marcatura, successiva aperta) | `spec_lint`, `state`, `loop`, `sync_check`, hook `Stop` |
| commit git | trailer `Test-Lock: T-nn` sul commit dei test rossi: blocca i suoi file di test | `diff_scope` |
| `review.md` | `- Esito:` (`conforme`, `conforme con riserve`, `non conforme`); `- Decisione di:` | `state`, `sync_check` |
| `docs/bugs/BUG-*.md` | `- Stato:` (`aperto`, `diagnosticato`, `corretto`, `verificato`); sezioni di `bugfix-template.md`; voci spuntabili in `## Chiusura` | `bug_lint`, `state` |
| `docs/system/<area>.md` | `- Ultimo allineamento:`; `- Specifiche collegate:`; sezioni `## Comportamento attuale`, `Vincoli e punti delicati`, `Test di caratterizzazione` | `sync_check` |
| `docs/system/mappa.md` | solo la presenza | `state` |
| `AGENTS.md` | riga `- Non modificare: a, b` | `diff_scope` |
| `PROMPT.md`, `progress.md` | `PROMPT.md` letto per intero e passato da stdin | `loop` |
| `scripts/verify.py` | lista `STEPS` | (modificata da `sdlc-init`) |

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
- Gli hook sono inattivi di default e non sono un sandbox. Il loop richiede ambiente isolato, permessi configurati a parte e un
  branch di feature; non fa push.
- La CI generata da `sdlc-init` usa action fissate per tag: in contesti regolati fissale per SHA.

## Limiti e punti non verificati

- **Windows:** suite eseguita su Windows 11 (Python 3.13, console cp1252) e nella matrice CI; i test di `run.sh` con PATH
  minimo e interpreti finti girano solo su POSIX.
- **Agenti reali:** le skill non sono state eseguite da un agente reale su un progetto; i controlli deterministici sì (test su repository
  temporanei, loop con agente finto, hook con l'input JSON atteso).
- **Codex:** manifest e invocazione delle skill non validati con strumenti Codex; supporto dei subagent non verificato.
- **Hook di Claude Code:** codice di uscita 2 come blocco e formato del JSON sono quelli attesi, non osservati in una sessione.
  Il comando passa da `sh hooks/run.sh`: su Windows richiede che Claude Code esegua gli hook con una shell che trovi `sh`
  (Git for Windows); non verificato in una sessione reale.
- **Fase rossa e `Test-Lock`:** si basano su convenzioni (marcatura nelle task, trailer nei commit) che l'agente potrebbe
  usare a sproposito; la review umana resta il controllo finale.
- **`claude -p` da stdin:** la lettura del prompt da stdin con `-p` va verificata sulla versione in uso.
- **Euristiche:** `diff_scope.py` dipende dal formato `- percorso: ...` del piano; `trace_check.py` trova gli ID per testo, non
  capisce la semantica dei test; `scan_repo.py` è un inventario; nessuno sostituisce la lettura del codice.
- **Perimetro:** il plugin non copre rilascio, sicurezza dell'infrastruttura, osservabilità e operazione (§8 del playbook), non
  configura i permessi dell'agente, non approva al posto dell'umano.

## Test e coerenza

`python -m unittest discover -s tests -v`. Oltre ai test degli script (su repository git temporanei), del loop (con un agente
finto che spunta una task per esecuzione) e degli hook, i **test di coerenza** verificano che:
- ogni `SKILL.md` abbia frontmatter valido, `name` uguale alla cartella e meno di 150 righe;
- ogni `python scripts/<x>.py` citato esista e ogni script sia documentato;
- ogni skill sia in README, riferimento delle skill e playbook, e ogni skill citata esista;
- ogni `§` citato esista come titolo del playbook;
- il playbook sia aggiornato rispetto ai file incorporati (`tools/build_playbook.py --check`) e non contenga riferimenti a versioni;
- le versioni di manifest, changelog e README coincidano;
- i link relativi della documentazione siano validi (`docs_check.py`).

## Evoluzioni possibili

Rilascio e operazione (§8 del playbook), integrazione con i tracker, un file di marketplace per Codex, un'analisi multi-repository.
Non sono documentate né implementate in questa versione.
