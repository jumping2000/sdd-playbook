# Playbook: ciclo di vita software con coding agent

Valido per greenfield e brownfield. Agenti di riferimento: Claude Code, Codex, o qualsiasi agente che legga `AGENTS.md`.
Ambienti di sviluppo supportati: Linux, macOS, **Windows nativo (VS Code, PowerShell)** e WSL.

Questo documento descrive il processo. Il plugin **`sdlc-playbook`** ne automatizza i passi con skill e script
(§11); script e template riportati qui sono **identici** a quelli del plugin, perché il documento è generato da
essi (`tools/build_playbook.py`).

> **Stato di questo documento.** È una sintesi di pratiche emergenti (spec-driven development, `AGENTS.md`, loop di verifica), non uno standard. Nessun set di documenti è "obbligatorio" per norma: i documenti marcati *Sì* sotto sono il minimo che raccomando. I tool cambiano versione di frequente: verifica sempre sulle fonti ufficiali elencate in fondo.

Convenzione: **`verify`** significa `python scripts/verify.py` (§1.1).

---

## 0. Principi

1. **La spec è la fonte di verità, il codice è un derivato.** L'agente non deve indovinare i requisiti.
2. **Ogni compito ha un controllo eseguibile** (test, lint, tipi, build). Senza, l'unico segnale è "sembra fatto" e il verificatore sei tu.
3. **Piccoli passi verificabili.** Una task = un'unità che un comando può dichiarare riuscita o fallita.
4. **Il contesto è una risorsa scarsa.** `AGENTS.md` breve, spec focalizzate, stato su file e non nella chat.
5. **Gate umani ai punti giusti:** approvi spec e piano, decidi sulla review, non rileggi ogni riga di codice.
6. **Se il risultato è sbagliato, correggi spec o test, non il prompt.**
7. **Le spec vanno mantenute.** Una spec non riconciliata con il codice smette di essere fonte di verità: ogni PR che cambia comportamento aggiorna la spec o la pagina d'area.
8. **Dove si può, il controllo è uno script, non una regola in prosa.** Un check che gira (ID presenti, non-scope compilato, test tracciati) vale più di un'istruzione all'agente.

---

## 1. Setup dell'ambiente (una tantum)

| Passo | Cosa fare |
|---|---|
| Repo e git | Repo git con branch protetto; un branch per feature; commit piccoli |
| Un comando di verifica | Uno script nel linguaggio del progetto (`scripts/verify.py`) che lancia format, lint, type-check, test. È il criterio di "fatto" per l'agente. Vedi §1.1 per template, alias e integrazione VS Code |
| CI | Stessa verifica in CI: controllo esterno che l'agente non può aggirare. Se si sviluppa su Windows, matrice `windows-latest` + `ubuntu-latest` |
| File di contesto | `AGENTS.md` come fonte; `CLAUDE.md` con `@AGENTS.md` in prima riga (evita i symlink: su Windows richiedono privilegi) |
| Controlli sui documenti | Gli script di `scripts/` (§11): lint di spec, piano e task, tracciabilità, scope del diff, stato del progetto |
| Permessi e audit | Vedi §1.2 |
| Struttura docs | `docs/` come sotto |
| Segreti | Fuori dal repo; `.env` ignorato; mai nel contesto dell'agente |
| Line ending | `.gitattributes` che forza LF sugli script (§1.1): i file con CRLF rompono gli script bash |

Struttura consigliata:

```
repo/
├── AGENTS.md                 # regole per agenti (breve)
├── CLAUDE.md                 # contiene @AGENTS.md
├── .gitattributes            # line ending
├── .vscode/
│   └── tasks.json            # task "verify" (default test task)
├── .github/workflows/        # CI: stessa verifica
├── scripts/                  # verify.py, spec_lint.py, state.py, ... (§11)
├── Makefile                  # facoltativo: alias `make verify` per Unix
├── docs/
│   ├── constitution.md       # principi non negoziabili del progetto
│   ├── specs/
│   │   └── 001-nome-feature/
│   │       ├── spec.md       # PRD + use case + requisiti + acceptance criteria
│   │       ├── plan.md       # design tecnico
│   │       ├── tasks.md      # checklist di task
│   │       ├── review.md     # esito della review del diff
│   │       ├── PROMPT.md     # solo se usi il loop (§7)
│   │       └── progress.md   # solo se usi il loop (§7)
│   ├── system/               # mappa.md e una pagina per area funzionale
│   ├── bugs/                 # un file per bug non banale (§6.1)
│   └── adr/                  # decisioni architetturali
└── tests/
```

### 1.1 Verifica su Windows e VS Code

**Principio:** un solo script, nessun bash-ismo, stessa logica ovunque. Tutto il resto (task VS Code, `make`, CI, hook) lo richiama.

**Perché uno script Python e non un Makefile.** GNU make e gli script `.sh` non sono affidabili su Windows nativo. Python è già nello stack di molti progetti; se il tuo progetto è Node o .NET, scrivi lo stesso script nel linguaggio del progetto (`verify.mjs`, `verify.ps1`) mantenendo identico il contratto: stesso exit code, stesso output di riepilogo. Gli altri script del plugin (§11) richiedono comunque Python.

**`scripts/verify.py`** (adatta la lista `STEPS`; ogni comando va provato a mano prima di registrarlo)

{{FILE skills/sdlc-init/scripts/verify.py python}}

Note di progetto:
- Il comando è una **lista**, senza shell: nessun problema di quoting tra PowerShell, cmd e Git Bash.
- `shutil.which` risolve anche gli shim Windows (`npm.cmd`, `uv.exe`). Se usi `uv`, gli step possono essere `uv run ...` e il comando di `verify` resta `python scripts/verify.py`.
- `--fast` (format + lint) è per il ciclo interattivo; il criterio di "fatto" è sempre `verify` completo.
- L'output è volutamente breve (una riga per step): l'agente legge meno rumore.

**Integrazione con VS Code: `.vscode/tasks.json`**

{{FILE skills/sdlc-init/references/vscode-tasks.json json}}

Uso: `Ctrl+Shift+P` → *Tasks: Run Test Task* lancia `verify`. `"type": "process"` evita la shell e quindi le differenze tra terminali; l'override `windows` usa il launcher `py` quando `python` non è nel PATH.

**`.gitattributes`**

{{FILE skills/sdlc-init/references/gitattributes.tmpl}}

**Alias facoltativo per Unix (`Makefile`)**

```make
verify:
	python scripts/verify.py
```

**CI (GitHub Actions)**

{{FILE skills/sdlc-init/references/ci-github-actions.yml yaml}}

**Dove gira `verify`, e chi lo lancia**

| Contesto | Comando | Nota |
|---|---|---|
| Tu, in VS Code | Task `verify` (o terminale integrato) | Funziona in PowerShell, cmd, Git Bash, WSL |
| Agente (Claude Code, Codex) | `python scripts/verify.py`, indicato in `AGENTS.md` | Secondo la documentazione di Claude Code consultata a ottobre 2026, su Windows nativo usa Git Bash se presente, altrimenti PowerShell: lo script è indipendente dalla shell |
| Hook dell'agente (facoltativo) | Hook `Stop` del plugin con `SDLC_ENFORCE_VERIFY=1` (§11) | Mai l'unico controllo |
| CI | `python scripts/verify.py`, su `ubuntu-latest` e `windows-latest` | Il controllo che l'agente non può aggirare |

**Trappole tipiche su Windows**

| Trappola | Contromisura |
|---|---|
| Fine riga CRLF negli script `.sh` | `.gitattributes` con `eol=lf` |
| Percorsi con `\` o con spazi | `pathlib` nel codice; liste di argomenti, mai stringhe concatenate |
| `rm`, `grep`, `sed`, `cp` non disponibili | Nessun comando Unix negli script di progetto: usa Python |
| Agente in WSL e verifica in Windows (o viceversa) | Stesso ambiente per agente e `verify`; due ambienti = due toolchain e due risultati diversi |
| Percorsi molto lunghi (`node_modules`, venv) | `git config core.longpaths true`; repo vicino alla radice del disco |
| Codifica console non UTF-8 | `PYTHONUTF8=1` (già impostato dallo script) |
| Il test passa solo su Linux | Matrice CI Windows + Linux |

### 1.2 Permessi, governance e audit

| Livello | Cosa fare |
|---|---|
| Permessi | Allowlist di comandi **e** deny-list esplicita (cancellazioni ricorsive, `git push --force`, download-ed-esegui, lettura di `.env`) |
| Ambiente | Container, worktree o macchina isolata per i loop autonomi; niente accesso a produzione né a segreti |
| Gate tecnici | Branch protetto, PR obbligatoria, CI obbligatoria. Opzionali (Claude Code, plugin §11): hook `Stop` che impedisce di dichiarare completato senza `verify` verde, hook `PreToolUse` che blocca i comandi a rischio. Sono una rete di sicurezza, non un sandbox |
| Tracciabilità | Commit con trailer `Spec: SPEC-001` e `Agent: <nome/versione>`; PR template con link alla spec, output di `verify`, elenco degli AC coperti |
| Approvazioni | Spec, piano e decisione sulla review portano nome e data dell'approvatore (campi nei template, §3); in contesti regolati l'approvatore è il product owner o l'analista, non lo sviluppatore che lancia l'agente |
| Log delle azioni | `progress.md` per i loop; per audit formale usa i log dell'agente e della CI, non la chat |

---

## 2. Documenti: minimo raccomandato

| Documento | Scopo | Minimo? | Formato |
|---|---|---|---|
| `AGENTS.md` | Comandi, convenzioni, cosa non toccare | **Sì** | Markdown, breve |
| `constitution.md` | Principi stabili (stack, sicurezza, test obbligatori) | Consigliato (se già in AGENTS.md, omettibile) | Markdown |
| `spec.md` | Problema, scope, **non-scope**, use case, requisiti, acceptance criteria | **Sì** | Markdown con ID |
| `plan.md` | Architettura, interfacce, file coinvolti, rischi | **Sì** (per feature non banali) | Markdown |
| `tasks.md` | Task piccole e verificabili | **Sì** | Checklist |
| `review.md` | Esito della review del diff e decisione umana | **Sì** (per feature non banali) | Markdown |
| Definition of Done | Comando unico + criteri | **Sì** | `scripts/verify.py` + sezione in AGENTS.md |
| ADR | Decisioni con motivazione | Consigliato | Markdown |
| `progress.md`, `PROMPT.md` | Memoria e istruzioni tra iterazioni | Solo per loop | Markdown |
| `bugfix.md` | Diagnosi e non-regressione di un bug | Per bug non banali | Markdown |
| `docs/system/mappa.md` | Mappa della codebase | **Sì** nel brownfield | Markdown |
| `docs/system/<area>.md` | Comportamento attuale per area, riconciliato dopo ogni feature | Consigliato (obbligatorio nel brownfield) | Markdown breve |

Regola per le feature piccole: se descrivi il diff in una frase, salta piano e task e vai diretto con spec minima e test. Regola per i bug banali (causa evidente, una riga di diff): test rosso, fix, `verify`, senza `bugfix.md`.

---

## 3. Template

### 3.1 `AGENTS.md` (tienilo sotto ~100 righe)

{{FILE skills/sdlc-init/references/AGENTS.md.tmpl markdown}}

### 3.2 `constitution.md`

{{FILE skills/sdlc-init/references/constitution.md.tmpl markdown}}

### 3.3 `spec.md`

{{FILE skills/sdlc-spec/references/spec-template.md markdown}}

Qualità minima di una spec: nomina file/interfacce coinvolti, dichiara il non-scope, chiude con un controllo end-to-end che dimostra la feature. Lo stato `approved` richiede approvatore e data compilati e nessuna domanda aperta (`spec_lint.py` lo controlla).

### 3.4 `plan.md`

{{FILE skills/sdlc-plan/references/plan-template.md markdown}}

I file nella sezione "Componenti e file" vanno **uno per riga nel formato `- percorso: cosa cambia`** (il percorso è la prima parola, o il testo tra backtick); anche i percorsi della colonna "Dove" della strategia di test contano come pianificati: `diff_scope.py` li usa per rilevare le modifiche fuori piano. Gli AC si cercano per ID esatto nella sola sezione "Strategia di test".

### 3.5 `tasks.md`

{{FILE skills/sdlc-tasks/references/tasks-template.md markdown}}

Le task `T-nn` hanno `verifica:` e `copre:` e nessun segnaposto `<...>`; `T-DOC` e `T-SYNC` sono obbligatorie e si eseguono dopo la review. La marcatura "atteso: rosso" va solo sulle task che scrivono test: quando l'ultima task chiusa la porta e la successiva è aperta, la spec è in **fase rossa** (i test rossi sono il risultato atteso) e l'hook `Stop` e `loop.py` lo tengono in conto.

### 3.6 `bugfix.md`

{{FILE skills/sdlc-bugfix/references/bugfix-template.md markdown}}

### 3.7 Mappa della codebase e pagina d'area

La **mappa** (`docs/system/mappa.md`) si scrive una volta, all'inizio del lavoro su una codebase esistente:

{{FILE skills/sdlc-map-codebase/references/mappa-template.md markdown}}

La **pagina d'area** (`docs/system/<area>.md`) cresce area per area e si riconcilia dopo ogni feature:

{{FILE skills/sdlc-sync/references/area-template.md markdown}}

### 3.8 `review.md`

{{FILE skills/sdlc-review-diff/references/review-template.md markdown}}

L'esito è uno tra `conforme`, `conforme con riserve`, `non conforme`. La decisione finale è dell'umano.

---

## 4. Flusso greenfield

| Fase | Attività | Skill del plugin | Gate umano |
|---|---|---|---|
| 1. Fondamenta | Setup (§1), `AGENTS.md`, `constitution.md` scritte con l'agente in conversazione e riviste da te | `sdlc-init` | Approvi principi e stack |
| 2. Spec | Dall'idea al `spec.md`. Fai elencare all'agente domande aperte e assunzioni, rispondi, poi congela | `sdlc-spec` | **Approvi la spec** (nome e data nel documento) |
| 3. Piano | `plan.md` in sola lettura | `sdlc-plan` | **Approvi il piano** |
| 4. Task | `tasks.md` in passi piccoli, ognuno con comando di verifica | `sdlc-tasks` | Controllo rapido |
| 5. Test prima | Dagli AC, l'agente scrive i test; devono fallire per il motivo giusto | `sdlc-tests-from-ac` (via `sdlc-implement`) | Spot check |
| 6. Implementazione | Task per task, `verify` a ogni passo; commit a ogni task verde | `sdlc-implement`, oppure `sdlc-loop` (§7) | — |
| 7. Review del diff | Contesto fresco, che prova a confutare; `review.md` | `sdlc-review-diff` | **Decidi sulla review** |
| 8. Documentazione | T-DOC: esempi eseguiti, link validi | `sdlc-docs` | Review |
| 9. Riconciliazione | T-SYNC: spec e `docs/system/` allineate al comportamento reale; stato spec = `implemented` | `sdlc-sync` | Review, poi PR |
| 10. Replan | Tra una feature e l'altra aggiorna `constitution.md`/`AGENTS.md` con ciò che hai imparato | — | — |

`sdlc-next` indica in ogni momento la fase corrente e il passo successivo.

---

## 5. Flusso brownfield

Il rischio principale è che l'agente modifichi o "migliori" ciò che non doveva toccare. Ordine consigliato:

1. **Mappa.** In sola lettura, parti da un inventario deterministico (`scan_repo.py`) e fai produrre all'agente la mappa della codebase: moduli, entry point, dipendenze, comandi reali di build e test. Verifica a campione che sia vera. *(`sdlc-map-codebase`)*
2. **`AGENTS.md` reale.** Con i comandi che funzionano davvero (provati, non dedotti) e le zone da non toccare (riga `- Non modificare: ...`). *(`sdlc-map-codebase`, `sdlc-init`)*
3. **Baseline verde.** Esegui test e build prima di qualsiasi modifica, **anche su Windows se è un ambiente di sviluppo del team**. Se falliscono già, annotalo: non è colpa dell'agente. *(`sdlc-map-codebase`)*
4. **Test di caratterizzazione.** Dove manca copertura sull'area da modificare, scrivi test che fissano il comportamento attuale (anche se imperfetto) e provane il fallimento con una rottura deliberata. Sono la rete di sicurezza. *(`sdlc-characterize`)*
5. **Spec solo del delta.** Non documentare l'intero sistema: descrivi solo la modifica, con **non-scope esplicito** (cosa non toccare). *(`sdlc-spec`)*
6. **Piano con impatto.** `plan.md` elenca file toccati, chiamanti, migrazioni, compatibilità all'indietro. *(`sdlc-plan`)*
7. **Modifiche piccole e reversibili.** Una task per commit; `verify` completo ogni volta, non solo i test nuovi. *(`sdlc-implement`)*
8. **Review del diff contro la spec.** Un subagent o una seconda sessione con contesto fresco verifica che nulla fuori scope sia cambiato; `diff_scope.py` segnala file fuori piano e zone vietate. *(`sdlc-review-diff`)*
9. **Documentazione di ritorno.** Per ogni area toccata crea o aggiorna `docs/system/<area>.md`: comportamento attuale in 2-3 paragrafi, vincoli scoperti, link alle spec. Così la conoscenza del sistema cresce area per area senza dover documentare tutto in anticipo. Aggiorna `AGENTS.md`/ADR con ciò che hai scoperto. *(`sdlc-docs`, `sdlc-sync`)*

Differenze rispetto al greenfield: più tempo in lettura/caratterizzazione, spec più piccole, rete di test prima del codice, review più attenta al "diff inatteso".

---

## 6. Test e documentazione

**Test**
- Genera i test **dagli acceptance criteria**, non dal codice: altrimenti l'agente scrive test che confermano i propri bug. *(`sdlc-tests-from-ac`)*
- **Test bloccati:** i test rossi si committano da soli con il trailer `Test-Lock: T-nn` (lo scheletro del codice, se serve, in un commit precedente). Da lì l'implementazione deve farli passare senza toccarli: `diff_scope.py` segnala come errore ogni modifica successiva a quei file fuori da un nuovo commit `Test-Lock`, che va motivato nella review. La CI del branch resta rossa fino alla task di implementazione.
- Tracciabilità: nel nome o commento del test cita l'ID dell'AC **qualificato con la spec** (`SPEC-001/AC-001`, o `test_SPEC001_AC001_...` nei nomi di funzione), perché gli AC ripartono da AC-001 in ogni spec; in alternativa dichiara la spec in testa al file (`# SPEC-001`) e cita `AC-001`. `trace_check.py` verifica che ogni AC compaia in almeno un test della sua spec, segnala i requisiti senza test e le citazioni ambigue, e ignora quelle nei `TODO`.
- Livelli: unit per la logica, integrazione per i confini, almeno un e2e per il flusso principale.
- Verifica che i test sappiano fallire: rompi di proposito il codice (o fai una mutation test) e controlla che qualcosa diventi rosso.
- Se il team sviluppa su Windows, almeno la suite di integrazione gira anche su Windows in CI.

**Documentazione**
- Task finale esplicita (`T-DOC`), non un'aggiunta casuale. *(`sdlc-docs`)*
- Fonte: spec e codice reale. L'agente deve eseguire gli esempi che scrive: `docs_check.py --run-examples` esegue i blocchi Python marcati `# docs-check: run` e controlla i link relativi; gli esempi in altri linguaggi si provano a mano.
- Cosa generare: README (setup, uso), doc API, ADR delle decisioni prese, note di migrazione nel brownfield.

### 6.1 Bug fixing

Un bug non è una feature in miniatura: la sequenza obbligata è **riproduci, fissa con un test rosso, diagnostica, correggi il minimo, verifica che il resto non sia cambiato**. *(`sdlc-bugfix`, controllato da `bug_lint.py`)*

| Fase | Attività | Stato nel file | Gate umano |
|---|---|---|---|
| 1. Riproduzione | L'agente riproduce il bug con passi minimi. Se non ci riesce, si ferma e chiede dati: nessun fix "a intuito" | `aperto` | — |
| 2. Definizione | `bugfix.md`: attuale vs atteso (con riferimento a REQ/AC), e **comportamento da NON cambiare** | `aperto` | Confermi l'atteso: se la spec era silente o sbagliata, il bug è anche un bug di spec |
| 3. Test rosso | Un test che fallisce per il motivo giusto (quello del bug) | `aperto` | Spot check |
| 4. Diagnosi | Causa radice verificata (log, debugger, bisect); in sola lettura finché non è chiara | `diagnosticato` | — |
| 5. Fix minimo | Solo ciò che serve; niente refactoring nello stesso commit; test sul comportamento invariato | `corretto` | Review PR |
| 6. Non-regressione | `verify` completo + test sul comportamento invariato | `corretto` | — |
| 7. Chiusura | Aggiorna AC/`docs/system/` se il bug rivelava un requisito mancante; lezione in `AGENTS.md`/ADR | `verificato` | — |

Isolamento: **una sessione, un branch e un commit per bug**. Se la diagnosi coinvolge molte aree, un subagent o una sessione fresca fa la diagnosi e consegna solo `bugfix.md`; la correzione parte in un'altra sessione, con quel file come unico contesto.

---

## 7. Loop di correzione

### 7.1 Schema

```
ripeti (max N volte):
  1. l'agente legge spec, task corrente e progress.md
  2. implementa o corregge una task T-nn
     (task "atteso: rosso": scrive i test, li vede fallire, commit Test-Lock, passa oltre)
  3. esegue `verify`
  4. verde  → commit, aggiorna progress.md, passa alla task successiva
     rosso  → legge l'errore, corregge senza toccare i test bloccati, riprova
fermati se: verify verde E nessuna task T-nn aperta | N raggiunto | nessun progresso per K iterazioni
```

L'idea è il cosiddetto "Ralph loop": un ciclo esterno che riesegue l'agente finché un controllo oggettivo non passa. Esiste un plugin ufficiale per Claude Code; il plugin `sdlc-playbook` fornisce uno script equivalente, indipendente dall'agente (`loop.py`, §7.3).

### 7.2 Regole

- **Criteri di stop oggettivi:** `verify` verde **e** nessuna task `T-nn` aperta in `tasks.md`, non "mi sembra a posto". Un `verify` verde da solo non basta: dopo la prima task il codice può essere verde con tutto il resto ancora da fare.
- **Il loop copre solo le task `T-nn`.** `T-DOC` e `T-SYNC` si eseguono dopo la review, con il gate umano in mezzo.
- **Tetto di iterazioni** sempre impostato (es. 10-20): senza, il loop consuma token a vuoto.
- **Rilevamento dello stallo:** se per K iterazioni consecutive non cambia nulla (task, commit, contenuto dell'albero di lavoro), il loop si ferma.
- **Tempo massimo per iterazione** (`--timeout`): un agente bloccato viene terminato e il loop prosegue; un codice di uscita diverso da zero viene riportato.
- **Baseline:** il loop parte solo con `verify` verde, oppure in fase rossa.
- **Stato su file** (`progress.md`), non nella chat: le sessioni lunghe derivano e la compattazione perde dettagli.
- **Una task per iterazione**, con contesto fresco quando possibile.
- **Branch di feature:** il loop rifiuta di partire su `main`/`master`.
- **Isolamento:** worktree o container, niente accesso a produzione né a segreti.
- **Controllo esterno:** la stessa verifica gira in CI.
- **Il loop lo lancia l'umano**, in un terminale separato: l'agente prepara i file e fa il dry run (`sdlc-loop`), non avvia un altro agente da dentro la propria sessione.

### 7.3 Script del loop

**`scripts/loop.py`**

{{FILE skills/sdlc-init/scripts/loop.py python}}

Il prompt passa da stdin, così si evitano i limiti di lunghezza della riga di comando su Windows. Il comando dell'agente è `claude -p` per default: con `--agent` si usa un altro agente, ma **la modalità non interattiva e i permessi vanno configurati e verificati a parte** (versione dell'agente, allowlist, deny-list). Il loop non fa push.

**`PROMPT.md`** (nella cartella della spec)

{{FILE skills/sdlc-loop/references/PROMPT.md.tmpl markdown}}

**`progress.md`**

{{FILE skills/sdlc-loop/references/progress.md.tmpl markdown}}

### 7.4 Se il risultato non è soddisfacente

| Sintomo | Causa probabile | Azione |
|---|---|---|
| Passa i test ma il comportamento è sbagliato | Acceptance criteria deboli o mancanti | Rafforza gli AC e i test, non il prompt |
| L'agente "completa" senza verificare | Nessun controllo eseguibile | Rendi `verify` obbligatorio (regola in AGENTS.md, hook `Stop`, CI) |
| Fa cose fuori scope | Non-scope assente | Aggiungilo alla spec; `diff_scope.py` con `--strict`; elenca le zone in "Non modificare:" |
| Gira in cerchio sullo stesso errore | Task troppo grande o spec ambigua | Spezza la task, chiarisci la spec, riparti con contesto fresco |
| Qualità cala nelle sessioni lunghe | Contesto saturo | Nuova sessione, stato letto da `progress.md` |
| Ignora le istruzioni | `AGENTS.md` troppo lungo | Pota: tieni solo ciò che non è deducibile dal codice |
| Non converge entro N, o il loop si ferma per stallo | Problema di spec o design, non di esecuzione | Fermati, rivedi spec/piano, poi rilancia |
| Verde in locale su Windows, rosso in CI Linux (o viceversa) | Script o test dipendenti dalla piattaforma | Matrice CI; rimuovi comandi di shell dagli script; controlla line ending e maiuscole nei percorsi |
| L'agente "corregge" un bug e ne rompe un altro | Comportamento invariato non dichiarato | Compila la sezione "da NON cambiare" in `bugfix.md` e aggiungi i test relativi |

Un secondo livello di verifica: un subagent con contesto fresco che prova a **confutare** il risultato rispetto a spec e piano (`sdlc-review-diff`).

---

## 8. Oltre la CI: rilascio e operazione

Il flusso sopra termina con codice verificato, rivisto e documentato. Per un ciclo di vita completo servono quattro attività, da dimensionare in base alla criticità del sistema. **Il plugin non le automatizza**: sono fuori dal suo perimetro.

| Attività | Minimo raccomandato |
|---|---|
| Sicurezza | Scansione segreti, audit delle dipendenze e analisi statica come step di `verify` o della CI; nuove dipendenze solo con ADR |
| Rilascio | Pipeline di deploy con gate umano su produzione; `plan.md` include rollback; release notes derivate da spec e AC coperti |
| Osservabilità | Ogni requisito non funzionale (es. latenza p95) ha una metrica o un log che lo rende osservabile dopo il rilascio |
| Feedback | Incidenti e segnalazioni diventano `bugfix.md` e, se rivelano una lacuna, nuovi AC; le lezioni confluiscono in `AGENTS.md`/ADR |

L'esecuzione di deploy e operazioni da parte di un agente è un argomento a parte: per default l'agente prepara e verifica, l'umano approva ed esegue.

---

## 9. Checklist finale per feature

- [ ] Spec approvata (nome e data), non-scope esplicito, domande aperte chiuse
- [ ] Ogni REQ ha almeno un AC e almeno un test tracciato (`trace_check.py`)
- [ ] `verify` verde in locale (anche su Windows, se è un ambiente del team) e in CI
- [ ] Diff riletto contro la spec e il piano (`diff_scope.py`, `review.md` con decisione umana)
- [ ] Documentazione aggiornata, esempi eseguiti, link validi (`docs_check.py`)
- [ ] Spec e `docs/system/<area>.md` riconciliate; stato spec = `implemented` (`sync_check.py`)
- [ ] `AGENTS.md`/ADR aggiornati con le lezioni apprese
- [ ] Nel brownfield: baseline verde prima e dopo, test di caratterizzazione presenti
- [ ] Per ogni bug: test rosso prima del fix, comportamento invariato dichiarato e testato (`bug_lint.py`)

---

## 10. Anti-pattern

- Prompt lunghi al posto di una spec versionata.
- `AGENTS.md` enciclopedico.
- Test generati dal codice invece che dai requisiti.
- Loop senza tetto o senza stop oggettivo; loop che esce alla prima verifica verde con task ancora aperte.
- Spec per l'intero sistema nel brownfield (basta il delta, più la pagina d'area).
- Applicare il processo completo a modifiche banali.
- Fidarsi del "fatto" dell'agente senza evidenza (output di test, diff).
- `verify` scritto in bash/make e basta, su un team che sviluppa anche su Windows.
- Fix di un bug senza test rosso che lo riproduca.
- Spec approvate e mai più riconciliate con il codice.
- Agente in WSL e `verify` in Windows nativo (o viceversa).
- Review fatta dalla stessa sessione che ha implementato, senza contesto fresco.
- Approvare spec, piano o review "al posto dell'umano": le approvazioni le dà una persona, con nome e data.

---

## 11. Automazione con il plugin `sdlc-playbook`

Il plugin implementa i passi di questo playbook come **skill** (istruzioni per l'agente, con un gate umano esplicito
a ogni punto di approvazione) e **script** (controlli deterministici copiati nel `scripts/` del progetto da
`sdlc-init`). Funziona con Claude Code e Codex. Guida completa: `README.md` e `docs/` del plugin.

| Fase | Skill | Script usati | Gate umano |
|---|---|---|---|
| Stato e prossimo passo | `sdlc-next` | `state.py` | — |
| Setup (§1) | `sdlc-init` | `verify.py` e tutti gli altri (copiati nel progetto) | Principi e stack |
| Mappa e baseline (§5, passi 1-3) | `sdlc-map-codebase` | `scan_repo.py`, `verify.py` | Mappa verificata a campione |
| Caratterizzazione (§5, passo 4) | `sdlc-characterize` | `verify.py` | Spot check |
| Spec (§3.3) | `sdlc-spec` | `spec_lint.py` | **Approvazione della spec** |
| Piano (§3.4) | `sdlc-plan` | `spec_lint.py --plan` | **Approvazione del piano** |
| Task (§3.5) | `sdlc-tasks` | `spec_lint.py --tasks` | Controllo rapido |
| Test dagli AC (§6) | `sdlc-tests-from-ac` | `trace_check.py` | Spot check |
| Implementazione (§4, fase 6) | `sdlc-implement` | `verify.py` | Review della PR |
| Loop (§7) | `sdlc-loop` | `loop.py` | **Permessi, tetto, avvio** |
| Bug fixing (§6.1) | `sdlc-bugfix` | `bug_lint.py`, `verify.py` | Atteso e "da NON cambiare" |
| Review del diff (§4, fase 7) | `sdlc-review-diff` | `diff_scope.py`, `trace_check.py` | **Decisione sulla review** |
| Documentazione (§6) | `sdlc-docs` | `docs_check.py` | Review |
| Riconciliazione (§4, fase 9) | `sdlc-sync` | `sync_check.py` | Review, poi PR |

**Script del plugin** (tutti Python, solo libreria standard, uguali su Windows e Linux; exit code `0` = ok, `1` = controllo fallito, `2` = uso errato o precondizione mancante):

| Script | Cosa controlla |
|---|---|
| `verify.py` | Format, lint, tipi, test del progetto: il criterio di "fatto" |
| `spec_lint.py` | Spec (sezioni, ID, REQ→AC, non-scope, approvazione, domande aperte); con `--plan` ogni AC è nella strategia di test; con `--tasks` ogni task ha verifica e copertura e nessun segnaposto, ogni AC è coperto, ci sono `T-DOC` e `T-SYNC` |
| `state.py` | Stato del progetto e prossima fase suggerita |
| `scan_repo.py` | Inventario deterministico di una codebase (stack, linguaggi, test, CI, entry point) |
| `trace_check.py` | Ogni AC citato in almeno un test della sua spec (`SPEC-nnn/AC-nnn` o file dichiarato); requisiti senza test; citazioni ambigue |
| `bug_lint.py` | Completezza del file di un bug in funzione del suo stato |
| `diff_scope.py` | File modificati: zone vietate (`Non modificare:` in `AGENTS.md`), test bloccati (`Test-Lock`) modificati dopo il blocco, file fuori piano, file pianificati non toccati |
| `docs_check.py` | Link relativi validi; esempi Python marcati eseguiti con successo |
| `sync_check.py` | Chiusura: spec `implemented`, task chiuse, review con decisione umana, pagina d'area, tracciabilità |
| `loop.py` | Loop esterno con tetto, rilevamento dello stallo, timeout per iterazione, baseline, branch protetto e dry run |

**Hook opzionali (solo Claude Code)**, inattivi se non abilitati con una variabile d'ambiente. Partono da `hooks/run.sh`, che esce subito se l'hook non è abilitato e altrimenti usa il primo tra `python3`, `python` e `py -3` che sia Python 3; senza Python l'errore è visibile ma non bloccante:

| Hook | Abilitazione | Effetto |
|---|---|---|
| `Stop` | `SDLC_ENFORCE_VERIFY=1` (e `SDLC_VERIFY_ARGS`, per es. `--fast`) | Se `verify` è rosso, l'agente non può dichiarare il lavoro finito, salvo fase rossa; evita i cicli con `stop_hook_active` |
| `PreToolUse` | `SDLC_GUARD=1` | Blocca force push, `reset --hard`, cancellazioni ricorsive, download-ed-esegui, lettura di `.env` |

**Subagent (solo Claude Code):** `sdlc-reviewer`, revisore indipendente in sola lettura usato da `sdlc-review-diff`. Con altri agenti la review si fa in una sessione nuova con le stesse istruzioni.

**Cosa non fa il plugin:** non approva al posto dell'umano, non lancia il loop da dentro una sessione, non copre rilascio, sicurezza dell'infrastruttura e operazione (§8), non configura i permessi dell'agente.

---

## 12. Fonti

- Articolo sugli strumenti SDD (Kiro, Spec Kit, Tessl) su martinfowler.com: https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- GitHub Spec Kit: https://github.com/github/spec-kit
- Confronto tra tool SDD: https://github.com/cameronsjo/spec-compare
- Standard `AGENTS.md`: https://agents.md
- Best practices Claude Code: https://code.claude.com/docs/en/best-practices
- Installazione e shell di Claude Code su Windows (nativo, Git Bash/PowerShell, WSL): https://code.claude.com/docs/en/install
- Task di VS Code: https://code.visualstudio.com/docs/editor/tasks
- Skill di Codex (formato Agent Skills): https://developers.openai.com/codex/skills
- Corso "Spec-Driven Development with Coding Agents" (DeepLearning.AI, con JetBrains): https://www.deeplearning.ai/courses/spec-driven-development-with-coding-agents
- Ralph loop (guida pratica): https://sidbharath.com/blog/ralph-wiggum-claude-code/
- Libro: Addy Osmani, *Beyond Vibe Coding* (O'Reilly)
