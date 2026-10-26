# Riferimento delle skill

*English version: [skills.md](skills.md)*

Ogni skill è una cartella `skills/<nome>/` con un `SKILL.md` (frontmatter `name` e `description`, poi le istruzioni)
e, se serve, `references/` con i template. Le istruzioni sono brevi di proposito (meno di 150 righe): i dettagli
del processo stanno nel [playbook](playbook-ai-software-lifecycle_IT.md), che ogni skill cita per sezione.
Skill e template sono in inglese, come ogni parte del plugin.

**Convenzioni comuni**
- Gli script si chiamano come `python scripts/<nome>.py` dalla radice del progetto: li copia `sdd-init`.
  Se un progetto è stato inizializzato con una versione precedente, copia lo script mancante da
  `skills/sdd-init/scripts/`.
- Ogni skill che produce un documento da approvare termina con **STOP**: chiede l'approvazione con nome e data,
  registra l'hash del contenuto approvato (`spec_lint.py --hash`) e non avvia la fase successiva. Spec, piano e task
  vanno poi nella PR di design: il merge su `main`, che fa solo l'umano, è l'approvazione (playbook §1.2).
- Le skill non committano senza autorizzazione dell'utente e mai su `main`/`master`.
- Quando un requisito è ambiguo, si fermano e chiedono: non assumono.

**Ordine tipico:** `sdd-init` → (`sdd-map-codebase` → `sdd-characterize`) → `sdd-spec` → `sdd-plan` →
`sdd-tasks` → `sdd-implement` (o `sdd-loop`) → `sdd-review-diff` → `sdd-docs` → `sdd-sync`. Il livello della
spec (playbook §2.1) lo accorcia o lo rafforza: S salta `sdd-plan` e `review.md`, L aggiunge ADR e revisione umana
del diff.

| Skill | Playbook | Produce | Controllo | Gate umano |
|---|---|---|---|---|
| `sdd-next` | tutto | niente (sola lettura) | `state.py` | — |
| `sdd-init` | §1 | scripts, `AGENTS.md`, `docs/`, task VS Code, CI | `verify.py` | principi e stack |
| `sdd-map-codebase` | §5 | `docs/system/map.md` | `scan_repo.py`, `verify.py` | mappa a campione |
| `sdd-characterize` | §5 | test di caratterizzazione, pagina d'area | `verify.py` + prova di fallimento | spot check |
| `sdd-spec` | §3.3 | `spec.md` | `spec_lint.py` | approvazione della spec |
| `sdd-plan` | §3.4 | `plan.md` | `spec_lint.py --plan` | approvazione del piano |
| `sdd-tasks` | §3.5 | `tasks.md` | `spec_lint.py --tasks` | controllo rapido |
| `sdd-tests-from-ac` | §6 | test rossi dagli AC | `trace_check.py` | approvazione dei test bloccati (M, L) |
| `sdd-implement` | §4 fase 6 | codice e commit | `verify.py` | review PR |
| `sdd-bugfix` | §6.1 | `docs/bugs/BUG-nnn.md`, test, fix | `bug_lint.py`, `verify.py` | atteso e "da NON cambiare" |
| `sdd-review-diff` | §4 fase 7 | `review.md` | `diff_scope.py`, `trace_check.py`, `secrets_check.py` | decisione sulla review |
| `sdd-docs` | §6 | documentazione aggiornata | `docs_check.py` | review |
| `sdd-sync` | §4 fase 9 | pagina d'area, spec `implemented` | `sync_check.py` | review, poi PR |
| `sdd-loop` | §7 | `PROMPT.md`, `progress.md`, comando | `loop.py --dry-run` | permessi, tetto, avvio |

---

### sdd-next

- **Quando:** non sai da dove ripartire, o vuoi sapere a che punto sei.
- **Cosa fa:** esegue `state.py`, riporta infrastruttura, spec (stato, approvazioni, task, review e passo di ognuna),
  bug non verificati e la riga `NEXT` con il motivo; chiede se procedere. Con più spec attive e nessuna legata al
  branch (`choose`), chiede all'utente su quale lavorare e rilancia con `--spec <id>`.
- **Non fa:** non modifica file, non avvia la fase successiva, non deduce lo stato dalla conversazione.

### sdd-init

- **Quando:** una volta per progetto, prima di spec o codice.
- **Cosa fa:** rileva sistema operativo, stack e se c'è già codice; chiede in un solo messaggio ciò che non
  rileva (comandi reali, Windows sì/no, provider CI); copia i 12 script in `scripts/` (ognuno con la versione del plugin in seconda riga, per gli aggiornamenti); adatta `STEPS` di
  `verify.py` provando ogni comando; crea `AGENTS.md`, `CLAUDE.md` (`@AGENTS.md`), `.gitattributes`,
  `.vscode/tasks.json`, `docs/constitution.md`, le cartelle `docs/*` e il workflow CI; esegue `verify` e `state`.
- **Regole:** non sovrascrive mai file esistenti (mostra la differenza, fa il merge di `tasks.json`); non inventa
  step o test; riporta `verify` rosso così com'è.
- **Inoltre:** la sezione **Decision rights** di `AGENTS.md` (decide da solo / chiede prima / mai), rivista con
  l'utente; `docs/glossary.md` solo se l'utente lo vuole.
- **Gate:** approvazione di `AGENTS.md`, constitution e step di `verify`.
- **Limiti dichiarati:** la CI generata non è mai stata eseguita; gli hook non vengono attivati.

### sdd-map-codebase

- **Quando:** inizio di un lavoro su codice esistente (brownfield).
- **Cosa fa:** `scan_repo.py` per l'inventario; baseline con `verify`; lettura del codice per compilare la mappa
  (moduli, entry point, dipendenze, zone da non toccare, rischi); ogni comando della tabella è eseguito;
  almeno 5 affermazioni verificate a campione nel codice; propone aggiornamenti di `AGENTS.md`.
- **Scrive solo:** `docs/system/map.md` e, con conferma, `AGENTS.md`.
- **Gate:** l'utente verifica la mappa a campione.

### sdd-characterize

- **Quando:** prima di modificare un'area esistente.
- **Cosa fa:** test che fissano il comportamento **attuale** (anche sbagliato, annotato come tale); devono passare
  sul codice non modificato; prova che sanno fallire con una rottura deliberata e ripristino (`git restore`,
  `git diff` vuoto); registra i test nella pagina d'area.
- **Non fa:** non modifica il codice di produzione né corregge i difetti trovati.
- **Precondizione:** `git status` pulito sui file dell'area.

### sdd-spec

- **Quando:** dall'idea a una specifica approvabile; anche per completare una bozza.
- **Cosa fa:** legge `AGENTS.md`, constitution, il codice coinvolto e (brownfield) mappa e pagina d'area prima di
  chiedere; riformula la richiesta con parole proprie; **pone** una domanda per messaggio, quella che cambierebbe di più
  ciò che si costruisce; propone 2-3 opzioni quando la richiesta ammette esiti davvero diversi per l'utente; scrive
  `spec.md` con livello proposto (S, M, L con i criteri del playbook §2.1), requisiti verificabili, AC
  Dato/quando/allora, non-scope obbligatorio, anti-obiettivi (`Anti-goals`), assunzioni marcate `[ASSUMPTION]`, domande
  aperte marcate `blocking: yes|no` (dopo l'approvazione restano aperte solo quelle non bloccanti), termini del glossario
  e nessuna parola vaga (avvisi di `spec_lint.py`); `spec_lint.py` deve passare; nel brownfield propone `sdd-characterize` se l'area non ha test.
- **Approvazione:** solo con conferma esplicita **e** nome dell'approvatore; poi `Status: approved`.

### sdd-plan

- **Precondizione:** spec `approved` e lint verde, livello M o L (nel livello S non c'è piano).
- **Cosa fa:** in sola lettura; `plan.md` con almeno un'alternativa scartata, file in formato `- path: what changes`,
  interfacce tra i componenti (cosa produce / cosa consuma), tutti gli AC nella strategia di test, il **review focus**
  (classi di input che nessun AC esercita, ognuna con il suo test), rischi, rilascio e rollback; autoverifica contro la
  spec (copertura, nomi, proporzione); `spec_lint.py --plan` deve passare. Segnala i candidati ADR senza crearli.

### sdd-tasks

- **Precondizione:** spec e piano approvati (livello S: solo la spec).
- **Cosa fa:** `tasks.md` con una riga per task nel formato descritto al §3.5 del playbook (azione, `verify:`, `covers:`), test prima del codice, ogni AC
  coperto, `T-SYNC` sempre presente e `T-DOC` salvo nel livello S; `spec_lint.py --tasks` deve passare.

### sdd-tests-from-ac

- **Quando:** per le task che scrivono test (le richiama `sdd-implement`) o a richiesta.
- **Cosa fa:** test dagli AC e non dal codice, con l'ID nel nome (`references/test-conventions.md`), più i casi di
  errore e i casi del review focus del piano; controlla la qualità dei test con gli anti-pattern delle convenzioni
  (asserzioni sui mock, asserzioni deboli, metodi di produzione solo per i test); scheletro minimo se serve; i test
  devono essere **rossi per il motivo giusto** (non per import o sintassi), con il messaggio di fallimento riportato;
  `trace_check.py --warn-only`.
- **Regola:** i test rossi si committano da soli, con il trailer `Test-Lock: T-nn` (lo scheletro, se c'è, in un commit
  precedente). `diff_scope.py` segnala ogni modifica successiva a quei test. La CI del branch resta rossa fino alla task
  di implementazione: è la "fase rossa", che l'hook `Stop` e `loop.py` riconoscono. Nei livelli M e L l'utente rilegge i
  test bloccati e solo allora l'agente scrive `tests approved: <name, date, sha>`; un nuovo commit `Test-Lock` per la stessa
  task fa decadere l'approvazione.

### sdd-implement

- **Precondizioni:** spec, piano e task validi e già uniti su `main` (`spec_lint.py ... --base main`); branch di
  feature; `verify` eseguito prima di iniziare (baseline).
- **Ciclo:** prima task `T-nn` aperta → implementa solo quella → comando di `verify:` e `verify` completo →
  verde: spunta, commit con trailer `Spec:` e `Agent:`; rosso: massimo 3 tentativi poi si ferma e chiede. Non modifica
  i test bloccati da un commit `Test-Lock`.
- **Diritti decisionali:** segue la sezione di `AGENTS.md`: decide da solo solo ciò che elenca "Decides alone" e lo
  registra in `progress.md`, sezione "Rulings" (`- T-nn: cosa — perché — costo se sbagliata`); si ferma su "Asks first",
  su una decisione che nessuna riga nomina e su una task che copre un AC nominato da una domanda aperta non bloccante;
  non fa mai ciò che elenca "Never".
- **Test scritti dopo il codice:** valori attesi dagli AC; un test in disaccordo con codice esterno alla task resta
  rosso e si segnala.
- **Review per task:** nel livello L (facoltativa nel livello M con `- Task review: on`) ogni task è rivista da
  `sdd-reviewer` sul suo pacchetto (`review_package.py <spec-dir> T-nn`) prima della successiva; i problemi alti e medi si
  correggono nella stessa task (al massimo 2 giri); l'esito va in `## Task reviews` di `progress.md`. I commit portano
  `Task: T-nn`.
- **Rilievi della review (`T-Rnn`):** verificati sul codice prima di toccarlo; un rilievo sbagliato non si corregge ma si
  annota con le prove in "Disputed review findings".
- **Fine:** quando restano solo `T-DOC` e `T-SYNC`, passa a `sdd-review-diff`; non dichiara la feature conclusa.

### sdd-bugfix

- **Quando:** un difetto da correggere (non per funzionalità nuove). Bug banali: test rosso, fix, `verify`, senza file.
- **Cosa fa:** `docs/bugs/BUG-nnn-slug.md` con stati `open → diagnosed → fixed → verified`, controllato da
  `bug_lint.py` a ogni transizione; riproduzione (se non si riproduce, si ferma), definizione di atteso e "da NON
  cambiare", test rosso, diagnosi in sola lettura con le tecniche di `references/debugging.md` (risalita alla sorgente,
  un'ipotesi alla volta, bisezione, test intermittenti), fix minimo, test di non-regressione, chiusura.
- **Gate:** l'utente conferma atteso e invariato (passo 2).
- **Regole:** un bug, un branch, un commit; niente refactoring nello stesso commit; altri difetti trovati = nuovi bug.

### sdd-review-diff

- **Precondizioni:** nessuna task `T-nn` aperta, `verify` verde, lavoro committato. Nel livello S bastano i
  controlli deterministici, riportati nella PR.
- **Cosa fa:** `diff_scope.py` (anche livello sottostimato e dipendenze senza decisione), `trace_check.py` e
  `secrets_check.py`; revisione indipendente (subagent `sdd-reviewer` in Claude Code, senza Bash: riceve nel messaggio il pacchetto del
  branch di `review_package.py` e gli output; dopo le review per task si concentra su integrazione, non-scope e decisioni;
  in GitHub Copilot lo stesso agente come custom agent `.github/agents/sdd-reviewer.agent.md`; altrimenti sessione nuova con spec, piano, output degli script e diff); scrive `review.md` con esito, problemi con file e riga,
  tentativi di confutazione.
- **Gate:** la **decisione è dell'utente** ("Decided by"; nel livello L anche "Human diff review", dopo che
  l'utente ha riletto il diff); con `non-compliant` ogni problema `high`/`medium` diventa una
  task `T-Rnn` in `tasks.md`, eseguita da `sdd-implement` o dal loop; chiuse le `T-R`, la review si ripete.
- **Non fa:** non modifica codice.

### sdd-docs

- **Precondizioni:** task `T-nn` chiuse, review valida e non `non-compliant`.
- **Cosa fa:** aggiorna README, documentazione API, note di migrazione da spec e codice reale; propone ADR (li crea dopo
  conferma); esegue gli esempi (Python marcati `# docs-check: run` con `docs_check.py --run-examples`, altri a mano);
  `docs_check.py` verifica i link; spunta `T-DOC`.

### sdd-sync

- **Precondizioni:** review con "Decided by" compilata (livello S: `diff_scope.py` e `trace_check.py` verdi),
  `T-DOC` chiusa.
- **Cosa fa:** confronta spec e comportamento reale: ogni scostamento è un bug (`sdd-bugfix`) o un cambio di
  requisito da approvare, mai nascosto; crea/aggiorna `docs/system/<area>.md` (facoltativa nel livello S); imposta `Status: implemented`; spunta
  `T-SYNC`; `sync_check.py` deve passare; propone lezioni per `AGENTS.md` e ADR.

### sdd-loop

- **Quando:** molte task piccole e indipendenti. Per poche task o molto accoppiate è meglio `sdd-implement`.
- **Cosa fa:** prepara `PROMPT.md` e `progress.md`, propone i permessi d'esempio (`settings.loop.json`), concorda `--max`, `--stall` e `--timeout`, esegue `loop.py --dry-run`, mostra la
  checklist di sicurezza e il comando.
- **Non fa:** **non lancia il loop**: lo lancia l'utente in un terminale isolato, dopo l'approvazione esplicita.
