# Riferimento delle skill

*English version: [skills.md](skills.md)*

Ogni skill è una cartella `skills/<nome>/` con un `SKILL.md` (frontmatter `name` e `description`, poi le istruzioni)
e, quando serve, `references/` con i template. Le istruzioni sono brevi (meno di 150 righe): il metodo sta nel
[playbook](playbook-ai-software-lifecycle_IT.md), che ogni skill cita per paragrafo. Skill e template sono in inglese,
come ogni parte del plugin.

**Convenzioni comuni**
- Gli script si chiamano come `python scripts/<nome>.py` dalla radice del progetto: li copia `sdd-start`.
- Ogni scelta, conferma e merge si chiede come **opzioni da selezionare** (guida
  `skills/sdd-start/references/interaction.md`): giri di massimo 4 domande, prima l'opzione consigliata, sempre una
  risposta libera. Le tre decisioni di una feature: `Confirm the spec`, `Confirm the plan`, `Merge into main` per ogni
  PR.
- L'agente lavora sui branch (`spec/<id>`, `task/<id>-T-nn`, `fix/BUG-nnn`), non committa mai su `main`, non unisce mai
  senza la selezione dell'utente. Il merge è l'unica approvazione che il processo registra.
- Quando un requisito è ambiguo, le skill si fermano e chiedono: non assumono.

**Ordine:** `sdd-start` → `sdd-plan` → `sdd-task` per ogni task (o `sdd-parallel` per i task indipendenti) → l'ultimo
task chiude la feature. Codice esistente: prima `sdd-map`. Bug: `sdd-bugfix`. In ogni momento: `sdd-next`.

| Skill | Playbook | Produce | Controlli | La tua decisione (opzioni) |
|---|---|---|---|---|
| `sdd-next` | §3 | niente (sola lettura) | `state.py` | quale skill eseguire |
| `sdd-start` | §1-§3 | la prima volta: script, `AGENTS.md`, `verify.py`; poi `spec.md` | `verify.py`, `spec_lint.py` | confermi la spec |
| `sdd-plan` | §2, §4 | `plan.md` con i task, PR di design | `spec_lint.py --plan` | confermi il piano, unisci la PR di design |
| `sdd-task` | §4 | test bloccati, codice, docs, PR; l'ultimo task chiude la feature | `verify.py`, `trace_check.py --task`, `diff_scope.py --task`, `docs_check.py` | unisci la PR |
| `sdd-parallel` | §5 | più `sdd-task` in worktree, una PR ciascuno | come `sdd-task`, rieseguiti dopo ogni merge | parallelo, poi ogni merge |
| `sdd-map` | §6 | `docs/system/map.md`, test di caratterizzazione, pagina d'area | `scan_repo.py`, `verify.py`, `docs_check.py` | verifica a campione della mappa, merge |
| `sdd-bugfix` | §7 | `docs/bugs/BUG-nnn.md`, test rosso, correzione, PR | `verify.py` | comportamento atteso e invariato, merge |

---

### sdd-start

- **Quando:** all'inizio di ogni feature, da un'idea o una richiesta.
- **Solo la prima volta:** rileva stack, remote e codice esistente; un giro di opzioni per i comandi reali, Windows,
  gli agenti in uso e la CI facoltativa (`verify` su ogni PR); copia gli script in `scripts/`, adatta `STEPS` di
  `verify.py` provando ogni comando, crea `AGENTS.md`, `CLAUDE.md`, `.gitattributes`, le voci di `.gitignore`,
  `.vscode/tasks.json`, `docs/constitution.md` e le cartelle `docs/*`; per GitHub Copilot copia skill e revisore in
  `.github/`. Non sovrascrive mai file esistenti. Aggiorna anche gli script di un progetto già inizializzato.
- **Poi:** legge il materiale prima di chiedere; per una modifica a codice esistente, un'**analisi d'impatto**
  (pagine d'area e spec collegate, codice e chiamanti, i test che lo proteggono eseguiti e verdi, `git log`) mostrata
  come cosa esiste, cosa cambia, cosa non deve cambiare e quali test lo proteggono; riformula la richiesta; fa brainstorming a giri di opzioni
  (obiettivo, utenti, esiti, non-scope, anti-goal, vincoli, errori); chiede conferma della comprensione; scrive
  `spec.md` su un branch `spec/<id>` con `## Current behaviour and impact`, REQ verificabili, AC Dato/quando/allora (solo quelli che scoprirebbero un
  difetto reale), non-scope, anti-goal, assunzioni marcate, domande aperte `blocking: yes|no`; `spec_lint.py` deve
  passare.
- **Decisione:** `Confirm the spec` imposta `- Status: approved` (solo senza domande bloccanti).
- **Revisione di una spec su `main`:** branch `revise/<id>`, voce in `## Revisions`, anche il piano rivisto se cambiano
  gli AC, la stessa decisione, PR di revisione.

### sdd-plan

- **Precondizione:** spec `approved`, lint verde.
- **Cosa fa:** in sola lettura sul codice; `plan.md` con l'approccio e un'alternativa scartata, le interfacce tra
  componenti, il **flowchart** obbligatorio, da 3 a 8 **task verticali** (`covers`, `files`, `depends`, `verify`), il
  review focus e i rischi; autoverifica contro la spec; `spec_lint.py --plan` deve passare. Propone ADR per nuove
  dipendenze o decisioni di architettura.
- **Decisione:** `Confirm the plan`, poi l'aggiornamento proposto di `AGENTS.md` (solo fatti durevoli; `Apply` o
  `Skip`), poi la **PR di design** (spec e piano insieme) e la sua domanda di merge: il merge
  approva entrambi.
- **Revisione di un piano su `main`:** branch `revise/<id>`, voce in `## Revisions`, task uniti mantenuti, quelli aperti
  cambiati o sostituiti, la PR del task bloccato chiusa o tenuta (opzioni), PR di revisione.

### sdd-task

- **Precondizione:** spec e piano su `main`; il task pronto (dipendenze unite).
- **Cosa fa:** branch `task/<id>-T-nn`; test dagli AC del task, rossi per il motivo giusto, committati da soli con
  `Test-Lock: T-nn`; il codice con `Task: T-nn`; `verify`, `trace_check.py --task`, `diff_scope.py --task`; la
  documentazione che il task cambia; la casella del task spuntata; la PR (`references/pr-body.md`); la review di
  `sdd-reviewer`. L'**ultimo task** scrive anche la pagina d'area con i cinque diagrammi dal codice finale e porta la
  spec a `implemented`, e propone per `AGENTS.md` la riga di `## Areas` e le lezioni valide per tutto il progetto.
- **Decisione:** `Merge into main` (oppure `Change it`, `Leave it open`), con davanti controlli, verdetto del revisore,
  stato della CI e file sensibili.
- **Regole:** mai indebolire un test; mai modificare spec o piano dentro un task. **Quando si ferma** (requisito
  ambiguo, non-scope, task troppo grande, 3 tentativi falliti) riporta cosa fallisce e chiede `Revise the spec`,
  `Revise the plan`, `Try another approach` o `Stop here`, poi segue la procedura di revisione della skill scelta.

### sdd-parallel

- **Quando:** `state.py` indica due o più task pronti con file disgiunti.
- **Cosa fa:** un worktree, un branch e un agente per task (al massimo 3), ognuno segue `sdd-task` fino alla review;
  merge uno alla volta, con rebase e ricontrollo degli altri dopo ogni merge; un conflitto ferma il task e porta a una
  correzione del piano.

### sdd-map

- **Quando:** all'inizio di un lavoro su una codebase esistente, e prima di modificare un'area.
- **Cosa fa:** inventario con `scan_repo.py`, baseline così com'è, la mappa con i cinque diagrammi del sistema
  esistente, comandi provati, 5 affermazioni verificate a campione, `Do not modify` e `Sensitive areas` proposte per
  `AGENTS.md`; poi test di caratterizzazione dell'area da modificare, di cui si prova che possono fallire, registrati
  nella pagina d'area.

### sdd-bugfix

- **Cosa fa:** prima legge (pagina d'area, spec, test dell'area, `git log`/`git blame` dei file sospetti); file del
  bug, riproduzione (niente correzioni a intuito), comportamento atteso e invariato confermati
  dall'utente, test rosso bloccato con `Test-Lock: BUG-nnn`, causa radice verificata (`references/debugging.md`),
  correzione minima, non regressione, PR con review e domanda di merge. Un bug di una riga con causa evidente non
  richiede il file del bug.

### sdd-next

- **Cosa fa:** esegue `state.py` e riporta infrastruttura, spec, task uniti e il passo `NEXT`; chiede quale spec quando
  ce ne sono più di una; segnala i bug aperti; non modifica nulla.

## Agente revisore: sdd-reviewer

Revisore indipendente, in sola lettura per costruzione (subagent di Claude Code con Read, Grep, Glob; custom agent di
GitHub Copilot con `read` e `search`; Codex: una nuova sessione con le stesse istruzioni). Rivede **una PR**: AC del
task implementati e verificati da test che potrebbero fallire, test derivati dagli AC e bloccati prima del codice,
niente anti-pattern, niente fuori dal task, decisioni dentro i diritti decisionali, diagrammi coerenti con il codice
nell'ultimo task. Verdetto `pass` o `fix needed`, problemi con file e riga, cosa l'umano deve leggere prima del merge.
