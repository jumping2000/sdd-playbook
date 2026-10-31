# Riferimento degli script e degli hook

*English version: [scripts.md](scripts.md)*

Tutti gli script stanno in `skills/sdd-init/scripts/` e `sdd-init` li copia in `scripts/` del progetto. Sono Python con sola
libreria standard, senza comandi di shell, e girano uguali su Windows, Linux e macOS. Si lanciano dalla **radice del
progetto**. La seconda riga di ogni script riporta la versione del plugin (`# sdd-playbook: <versione>`), per
sapere quali copie aggiornare (`sdd-init`, sezione "Updating an already initialized project"). Exit code: `0` ok, `1` controllo fallito, `2` uso errato o precondizione mancante. L'output è sempre UTF-8,
anche con una console Windows in cp1252. I messaggi sono in inglese.

I formati dei file che gli script leggono sono descritti in [architecture_IT.md](architecture_IT.md#contratti-sui-file).

| Script | Usato da | Scopo |
|---|---|---|
| `verify.py` | tutte | criterio di "fatto" del progetto |
| `state.py` | `sdd-next` | stato e prossima fase |
| `spec_lint.py` | spec, plan, tasks, implement, loop | lint di spec, piano e task |
| `trace_check.py` | tests-from-ac, review-diff | tracciabilità AC → test |
| `bug_lint.py` | bugfix | completezza del file di un bug |
| `diff_scope.py` | review-diff, sync, loop | modifiche vs piano, zone vietate, test bloccati e livello |
| `scan_repo.py` | map-codebase | inventario di una codebase |
| `docs_check.py` | docs, sync, map-codebase | link, diagrammi Mermaid ed esempi |
| `sync_check.py` | sync | chiusura di una feature |
| `secrets_check.py` | review-diff, loop, `verify` | segreti nei file |
| `loop.py` | loop | loop autonomo esterno |
| `review_package.py` | implement, review-diff, loop | pacchetto di review di una task o dell'intero branch |
| `approve.py` | spec, plan, tasks, tests-from-ac, review-diff | registra un'approvazione selezionata dall'utente |

---

### verify.py

Esegue gli step di `STEPS` (format, lint, tipi, test, segreti) e stampa una riga per step più `VERIFY: GREEN|RED -> ...`.
Va adattato dal progetto: ogni comando è una lista di argomenti, provato a mano prima di registrarlo.

```
python scripts/verify.py                 # tutti gli step, si ferma al primo rosso
python scripts/verify.py --fast          # solo gli step marcati fast (format, lint, segreti)
python scripts/verify.py test lint       # solo gli step indicati
python scripts/verify.py --keep-going    # non si ferma al primo rosso
```

Exit: `0` verde, `1` almeno uno step rosso o comando non trovato, `2` nessuno step selezionato. Imposta `PYTHONUTF8=1`.

### state.py

Sola lettura. Riporta infrastruttura (`AGENTS.md`, `verify.py`, CI, `docs/`), presenza di codice esistente e della mappa,
stato e livello di ogni spec con il suo passo successivo (`-> skill`), bug non verificati, branch corrente e la riga
`NEXT`.
Ordine del suggerimento per una spec: `sdd-spec` (bozza, `in-revision`, approvazione decaduta) → `sdd-plan` (mancante,
da approvare o decaduto) → `sdd-tasks` (mancanti o basate su un altro piano) → `sdd-implement` (task `T-nn`/`T-Rnn`
aperte; invece `sdd-spec` se la task successiva copre un AC nominato da una domanda aperta non bloccante) → `sdd-review-diff` (review mancante; con `non-compliant`: creare le `T-R`, o ripetere la review quando sono
chiuse) → `sdd-docs` (`T-DOC` aperta) → `sdd-sync`. Prima di tutto `sdd-init` e, nel brownfield senza mappa né spec,
`sdd-map-codebase`. `scripts/`, `docs/`, `.github/` e `.vscode/` non contano come codice esistente.

**Livelli** (playbook §2.1). Livello S: dopo la spec approvata `sdd-tasks` (senza piano), poi `sdd-implement`,
`sdd-docs` se `T-DOC` è aperta e `sdd-sync`; `review.md` conta solo se c'è ed è `non-compliant`. Livelli M e L: una
task di test "expected: red" chiusa senza `tests approved:` porta a `sdd-tests-from-ac` prima dell'implementazione.
Livello L (o M con `- Task review: on` in `progress.md`): chiuse le task `T-nn`, ognuna deve avere `- T-nn: pass` nella
sezione `## Task reviews` di `progress.md`, altrimenti `sdd-implement`. Livello L: dopo una review accettata serve anche
`- Human diff review:` in `review.md`, altrimenti `sdd-review-diff`. Senza il campo `- Level:` la spec vale M.

**Profilo solo.** Con `- Profile: solo` in `AGENTS.md`, quando il design è approvato (spec, e piano e task nei livelli
M e L) ma `main` non contiene ancora gli stessi file, `NEXT` è `sdd-tasks` con l'istruzione di far avanzare `main`
(`git fetch . HEAD:main`). Nel profilo team quel passo è il merge della PR di design, che `spec_lint.py --base` controlla.

**Più spec attive.** `NEXT` riguarda la spec indicata con `--spec <id>` (nome della cartella o ID del titolo), quella
il cui nome di cartella compare nel branch corrente (`feat/2026-10-24-export-csv`), o l'unica attiva. Altrimenti riporta
`choose` con l'elenco delle spec e del loro passo: la scelta è dell'utente.

```
python scripts/state.py [--json] [--spec <id>] [radice]
```

### spec_lint.py

```
python scripts/spec_lint.py <spec.md> [--plan <plan.md>] [--tasks <tasks.md>] [--base <ref>]
python scripts/spec_lint.py <file.md> --hash
```

**Approvazione.** `--hash` stampa l'hash del corpo del file (dalla prima sezione `## ` in poi, fine riga e spazi
finali normalizzati, più il livello se la spec lo dichiara: abbassarlo dopo l'approvazione la fa decadere), da scrivere in `- Hash:` dopo l'approvazione. Una spec `approved`/`implemented` senza hash, o con
un hash che non corrisponde più al contenuto, è un errore. Un piano approvato deve avere `- Hash:` valido e
`- Based on spec:` uguale all'hash attuale della spec: se la spec cambia, il piano decade. Con `--base <ref>` spec e
piano devono esistere su `<ref>` ed essere identici alla copia di lavoro: il merge della PR di design su un branch
protetto è l'approvazione che l'agente non può darsi da solo (playbook §1.2).

| Modalità | Errori rilevati |
|---|---|
| spec | avviso sopra 6 AC nel livello S o 15 nel livello M (proporzione); stato non valido (`draft`, `approved`, `in-revision`, `implemented`, `superseded`); livello diverso da S, M, L (avviso se manca: vale M); titolo senza ID `# SPEC-<id>:`, data non valida o ID diverso dal nome della cartella; `in-revision` senza una voce in `## Revisions`; sezioni mancanti; ID REQ/AC duplicati; REQ senza AC; AC che cita REQ inesistenti; non-scope assente o con segnaposto (avviso se mancano gli anti-obiettivi, `Anti-goals`); se `approved`/`implemented`: approvatore mancante, hash mancante o non corrispondente, domande aperte bloccanti o senza `blocking: yes|no` (avviso per quelle non bloccanti e se restano `[ASSUMPTION]`); in ogni stato una domanda aperta `about:` un REQ o AC inesistente; avvisi per parole vaghe nei REQ e negli AC e, se esiste `docs/glossary.md`, per i sinonimi della sua colonna "Avoid" |
| `--plan` | sezione `## Test strategy` mancante; AC della spec assenti da quella sezione (ID esatto: `AC-001` non vale per `AC-0011`); sezione `## Review focus` mancante; review focus con segnaposto o vuoto (avviso prima dell'approvazione, errore dopo; `- none` è valido); sezione `## Diagrams` mancante, o mancante una delle sottosezioni `### Flowchart`, `### Sequence diagram`, `### State diagram`, `### Class diagram`, `### ER diagram` (errore); una sottosezione senza un blocco Mermaid del suo tipo (`flowchart`/`graph`, `sequenceDiagram`, `stateDiagram-v2`, `classDiagram`, `erDiagram`) né `- n/a: <motivo>`, un blocco vuoto, un flowchart `n/a` (avviso prima dell'approvazione, errore dopo); piano approvato con hash non valido o basato su un'altra versione della spec; avviso se il piano non è approvato |
| `--base` | spec o piano assenti su `<ref>` o diversi dalla versione su `<ref>` |
| `--tasks` | nessuna task; task `T-nn` senza `verify:` o `covers:` o con segnaposto `<...>`; task `T-Rnn` senza `verify:` o con segnaposto (`covers:` facoltativo); ID duplicati; `T-SYNC` mancante, o `T-DOC` mancante salvo nel livello S; AC non coperto da nessuna task; avviso per una task `T-nn` aperta che copre un AC nominato da una domanda aperta non bloccante |
| `--plan` e `--tasks` insieme | task con `- Based on plan:` diverso dall'hash del piano (avviso se il campo manca) |

### trace_check.py

```
python scripts/trace_check.py <spec.md> [--tests DIR ...] [--junit FILE|DIR ...] [--warn-only]
```

Cerca le citazioni degli AC nei file di test (cartelle di default: `tests`, `test`, `__tests__`, `spec`, `src/test`;
estensioni dei linguaggi più comuni) e le attribuisce a una spec, perché gli AC ripartono da AC-001 in ogni spec. L'ID
della spec viene dal titolo `# SPEC-<id>: ...` (data + slug, o numero nei progetti più vecchi) e si confronta in forma
normalizzata (`_` come `-`, numeri senza zeri iniziali): `SPEC-2026-10-24-export` non vale per `SPEC-2026-10-24-export-csv`.
- `SPEC-2026-10-24-export-csv/AC-001` (nei nomi di funzione `SPEC_2026_10_24_export_csv_AC_001`; per i numeri anche
  `SPEC-001-AC-001`, `SPEC001_AC001`) vale per quella spec;
- `AC-001`, `AC_001`, `AC001` in un file che nomina una sola spec (es. `# SPEC-2026-10-24-export-csv` in testa) vale per
  quella spec: è il modo consigliato con gli ID con data;
- `AC-001` in un file che non nomina spec vale solo se `docs/specs/` contiene una sola spec; altrimenti è **ambigua**,
  non conta ed è segnalata come avviso;
- le citazioni su righe con `TODO`, `FIXME` o `XXX` non contano e sono segnalate.

Stampa per ogni AC il numero di riferimenti o `NO TEST`, segnala i REQ senza alcun AC testato e, come avvisi, gli AC
attribuiti alla spec ma assenti dalla spec, le citazioni ambigue e quelle ignorate. Exit `1` se un AC non ha test (salvo
`--warn-only`), `2` se non trova cartelle di test.

**`--junit`: test eseguiti, non solo citati.** Con uno o più report JUnit XML (file, o cartelle di cui si leggono tutti
gli `*.xml`) ogni AC deve avere almeno un caso di test **eseguito e passato** e nessuno fallito; i casi saltati non
contano. Un caso vale per un AC se lo cita in forma qualificata nel nome o nel `classname`, oppure in forma breve quando
appartiene a un file di test attribuito alla spec (attributo `file`, o un componente del `classname` uguale al nome del
file, come `tests.test_export` per `tests/test_export.py` o `com.acme.ExportTest` per `ExportTest.java`) o il progetto
ha una sola spec. Il file di un caso è quello il cui percorso coincide più a lungo con `file` o `classname`: file
omonimi in cartelle diverse non si confondono, e a pari merito tra file di spec diverse il caso non conta. Report
illeggibile o `--junit` senza valore: exit `2`. Il report lo scrive `verify` (vedi `references/stacks.md` di `sdd-init`).

### bug_lint.py

```
python scripts/bug_lint.py docs/bugs/BUG-001-esempio.md
```

I requisiti crescono con lo stato: `open` → riproduzione compilata; `diagnosed` → atteso e attuale, "da NON
cambiare", causa radice, percorso del test rosso; `fixed` → fix minimo descritto e test di non-regressione indicato;
`verified` → tutte le voci di "Closure" spuntate. Segnaposto `<...>` ed etichette vuote non contano come contenuto.

### diff_scope.py

```
python scripts/diff_scope.py docs/specs/001-x [--base main] [--strict]
```

Calcola i file modificati dal merge-base con il ref di base (default: il primo esistente tra `main`, `master`,
`origin/main`, `origin/master`), inclusi file non committati e non tracciati. Le rinomine contano con il percorso di
partenza e quello di arrivo (`--no-renames`); i file generati (`__pycache__/`, `*.pyc`, `reports/`) non contano.
`AGENTS.md` e il livello della spec si leggono **dal merge-base** quando esistono lì: il ramo non può allentarli (se il
ramo modifica `AGENTS.md` c'è un avviso). Le voci di `AGENTS.md` valgono come percorsi (testo tra backtick o prima
parola); quelle che non sembrano percorsi sono segnalate e ignorate. Segnala:
- **errore** (exit 1): file nelle zone delle righe `- Do not modify:` di `AGENTS.md` (tutte, non solo la prima);
- **errore** (exit 1): file di test bloccati modificati dopo il blocco. Un commit con il trailer `Test-Lock: T-nn` blocca i
  suoi file di test (cartelle `tests`, `test`, `__tests__`, `spec` o nomi come `test_*.py`, `*_test.go`, `*.test.ts`,
  `*Test.java`); una modifica successiva in un commit senza lo stesso trailer, o non committata, è una violazione. I file
  non di test di un commit `Test-Lock` (per esempio uno scheletro) non vengono bloccati e sono segnalati come avviso;
- **avviso** (errore con `--strict`): file fuori dal piano (esclusi `docs/specs/<questa spec>/`, `docs/system/`,
  `docs/bugs/`, `docs/adr/`, `docs/glossary.md`). Il piano comprende le righe di "Components and files" (percorso = prima parola o testo tra
  backtick, quindi `- src/a.py (new): ...` vale `src/a.py`) e la colonna "Where" della strategia di test e del review focus;
- **errore** (exit 1): **livello sotto i criteri vincolanti** (playbook §2.1). Un file nelle righe `- Sensitive areas:`
  di `AGENTS.md` richiede L; una modifica a un manifest o lockfile delle dipendenze (`package.json`, `pyproject.toml`,
  `requirements*.txt`, `go.mod`, `*.csproj`, i lockfile, ...) richiede almeno M. Il livello dichiarato viene da
  `- Level:` della spec (M se manca); nel livello S senza piano il confronto con il piano è saltato;
- **avviso**: livello S con più di 3 file di produzione. Non contano test, `docs/`, `*.md`, file generati e strumenti del
  processo (gli script del playbook in `scripts/`, `AGENTS.md`, `CLAUDE.md`, `.github/`, `.vscode/`, `.gitattributes`,
  `.gitignore`, `.secrets-ignore`). Il livello l'ha scelto chi approva: la sola dimensione non lo scavalca; `[INFO]`
  quando il livello dichiarato è più alto di quanto richiedono i criteri vincolanti;
- **errore** (exit 1): **dipendenze senza decisione**: un manifest o lockfile modificato che il piano non elenca (un
  lockfile vale se il piano elenca il suo manifest nella stessa cartella), in un diff che non **aggiunge** un ADR in
  `docs/adr/` (README e indici non contano). Playbook §8: nuove dipendenze solo con ADR o nel piano approvato;
- **errore** (exit 1): **test approvati superati**: lo SHA di `tests approved: <name, date, sha>` non è un commit
  `Test-Lock` del ramo per quella task (rebase, amend), o dopo di esso c'è un altro commit `Test-Lock` per la stessa task;
- **info**: percorsi del piano non toccati.

Percorsi: esatti, cartelle (prefisso) o glob; il prefisso `./` si ignora, i punti iniziali (`.github/`) restano. Exit
`2` se non è un repository git o manca il ref di base.

### scan_repo.py

```
python scripts/scan_repo.py [radice] [--json]
```

Inventario in sola lettura: manifest e stack, linguaggi (file e righe), struttura di primo livello, cartelle di test,
CI, entry point probabili, documentazione. Usa `git ls-files` se disponibile. È un inventario, non una comprensione.

### docs_check.py

```
python scripts/docs_check.py [percorsi...] [--run-examples]
```

Default: `README.md` e `docs/`. Controlla i link e le immagini relativi (ignora codice, URL esterni, ancore pure). Con
`--run-examples` esegue i blocchi Python la cui prima riga non vuota è `# docs-check: run` (timeout 60 s, deve
terminare con exit 0). Gli altri blocchi non vengono eseguiti.

**Diagrammi.** Ogni blocco ```` ```mermaid ```` deve iniziare con un tipo di diagramma Mermaid noto (dopo i commenti
`%%` e il front matter `---`) e avere un corpo; il resto della sintassi non è controllato: guarda l'anteprima del
diagramma (GitHub, GitLab, VS Code con un'estensione Mermaid). Ogni pagina di `docs/system/` (pagine d'area e mappa)
richiede la sezione `## Diagrams` con i cinque diagrammi, ognuno disegnato o `- n/a: <motivo>`, con le stesse regole di
`spec_lint.py --plan` (qui sempre errori). Un blocco di codice si chiude solo con una recinzione dello stesso carattere
lunga almeno quanto quella d'apertura, così un template mostrato in un blocco ```` ```` ```` conserva i blocchi interni.

### sync_check.py

```
python scripts/sync_check.py docs/specs/001-x [--area docs/system/<area>.md] [--tests DIR ...] [--junit FILE|DIR ...]
```

Verifica che: la spec sia valida con `Status: implemented`; nessuna task sia aperta; `review.md` abbia un esito valido,
diverso da `non-compliant`, e la "Decided by" compilata; esista una pagina d'area (o quella indicata) con le sezioni
richieste, "Last aligned" compilato, la spec tra le "Linked specs" e la sezione `## Diagrams` completa (come in
`docs_check.py`); ogni AC sia citato in un test **di
questa spec**, con le regole di `trace_check.py` (se mancano test e ci sono citazioni ambigue, l'errore lo dice).
Livello S: `review.md` e pagina d'area facoltative (se `review.md` c'è, si controlla). Livello L: `review.md` deve avere
anche `- Human diff review:` compilato. Nei livelli M e L le task di test chiuse ("expected: red") riportano
`tests approved:`. Nel livello L, o M con `- Task review: on`, ogni task `T-nn` chiusa ha `- T-nn: pass` in
`## Task reviews` di `progress.md`. Con `--junit` gli AC devono essere verificati dal report dei test eseguiti, come in `trace_check.py`;
nel livello L il report è obbligatorio.

### secrets_check.py

```
python scripts/secrets_check.py [--base <ref>]     # file del ramo: modificati dal merge-base e non tracciati
python scripts/secrets_check.py --all              # tutti i file tracciati (lo step "secrets" di verify)
python scripts/secrets_check.py <file o cartella> ...
```

Errore (exit 1): chiavi private (`-----BEGIN ... PRIVATE KEY-----`), token con formato riconoscibile (AWS, GitHub,
GitLab, Slack, Stripe live, Google, Anthropic, OpenAI) e file `.env` nel repository (non `.env.example`, `.sample`,
`.template`). Avviso: password, secret, token o chiavi assegnati a una stringa letterale di almeno 8 caratteri, esclusi i
segnaposto evidenti. Il valore trovato non viene mai stampato. Una riga con `secrets-check: ignore` non viene controllata
(il falso positivo va motivato nella review); i file che non si possono annotare (fixture PEM, `.env.development`
versionato per convenzione) vanno in `.secrets-ignore`, un glob per riga. `.env.local.example` e simili non contano.
I percorsi non ASCII sono letti correttamente (`core.quotePath=false`). Salta file binari e oltre 1 MB. Exit `2` senza git o ref di base (usa
`--base`, `--all` o percorsi). È una rete veloce, non una scansione della storia: per quella serve uno strumento dedicato
in CI.

### loop.py

```
python scripts/loop.py docs/specs/001-x [--max 15] [--stall 3] [--timeout 1800] [--agent "claude -p"]
                                        [--junit reports/junit.xml] [--allow-main] [--allow-red-baseline] [--dry-run]
```

Legge `PROMPT.md` dalla cartella della spec e lo passa all'agente da stdin. Dopo ogni iterazione esegue `verify`.
Si ferma con exit `0` se `verify` è verde, non restano task `T-nn` né `T-Rnn` aperte (`T-DOC` e `T-SYNC` restano fuori) **e i
controlli finali passano**: `spec_lint.py` su spec, piano e task, `trace_check.py` sulla spec, `diff_scope.py` sulla
cartella e `secrets_check.py`, se presenti in `scripts/`, più le review per task nel livello L (o M con
`- Task review: on`). Le caselle le spunta l'agente; questi controlli no. Se `diff_scope` non può calcolare il diff (exit `2`, per esempio
senza ref di base) è un avviso; con
exit `1` al tetto `--max` o dopo `--stall` iterazioni senza cambiamenti (tasks.md, HEAD di git, **contenuto** delle
modifiche tracciate e non tracciate, esclusi i file generati come `__pycache__/` e `reports/`: un agente che lavora
sempre sullo stesso file non è in stallo, un report che cambia a ogni `verify` non è progresso). Con `--junit` avvisa se
il report non è ignorato da git. Ogni iterazione dura al
massimo `--timeout` secondi: oltre, l'agente viene terminato e il loop prosegue; un codice di uscita diverso da zero viene
riportato come avviso. Rifiuta di partire (exit `2`) su `main`/`master` (salvo `--allow-main` in ambienti isolati) e con
`verify` già rosso, salvo fase rossa (l'ultima task `T-nn` chiusa è "expected: red") o `--allow-red-baseline`.
**Test da approvare** (livelli M e L): se dopo un'iterazione una task di test "expected: red" è chiusa senza
`tests approved:`, il loop si ferma con exit `1` perché l'umano rilegga i test bloccati; con un'approvazione già in
attesa non parte (exit `2`). Con `--junit` il controllo finale `trace_check.py` usa il report dei test eseguiti.
`--dry-run` controlla le precondizioni senza lanciare l'agente e mostra se c'è una fase rossa. Non fa push. Permessi e
modalità non interattiva dell'agente vanno configurati a parte: `skills/sdd-loop/references/settings.loop.json` è un
esempio di allowlist e deny-list per Claude Code (nega anche la scrittura di `scripts/`, `AGENTS.md`, `.github/`, spec,
piano e review: i controlli e le regole del loop) (`--agent "claude -p --settings <file>"`, da verificare sulla versione).

### review_package.py

```
python scripts/review_package.py docs/specs/001-x T-03 [--base main] [--out FILE]
python scripts/review_package.py docs/specs/001-x [--base main] [--out FILE]     # intero branch
```

Non è un controllo: prepara l'input del revisore indipendente, che non ha Bash. Con una task raccoglie i commit del
branch il cui messaggio porta `Task: T-03` (commit di implementazione, vedi `sdd-implement`) o `Test-Lock: T-03` (test
bloccati); senza task, tutti i commit dal merge-base. Scrive un unico file Markdown con la riga della task, il testo
degli AC coperti (tutti per il branch), le sezioni `## Interfaces`, `## Diagrams` e `## Review focus` del piano, le decisioni di
`progress.md` (solo quelle della task), l'elenco dei commit, i file toccati e le patch con 10 righe di contesto; i file
generati (`__pycache__/`, `reports/`) sono esclusi e le modifiche non committate non sono incluse. Output di default:
`reports/review/<cartella della spec>/<task o branch>.md`. Exit `2` con un ID di task non valido, senza git o ref di
base, o se nessun commit corrisponde.

---

## Hook opzionali (solo Claude Code)

Non sono portati su Codex e GitHub Copilot (gli hook di Copilot hanno un formato diverso e nessun evento di stop
bloccante).

Si caricano con il plugin (`hooks/hooks.json`) ma restano **inattivi** finché non imposti la variabile d'ambiente.
Sono una rete di sicurezza minima, non un sandbox: non sostituiscono permessi, allowlist e isolamento.

Entrambi partono da `hooks/run.sh` (`sh run.sh <script.py> <variabile>`). Il launcher esce `0` subito se la variabile non
vale `1`, quindi un hook inattivo non richiede Python. Se è attivo usa il primo tra `python3`, `python` e `py -3` che sia
davvero Python 3.8+ (scarta gli alias di Microsoft Store e Python 2): su Ubuntu pulito esiste solo `python3`. Senza
Python 3 esce `1` con un messaggio, cioè un errore visibile ma non bloccante.

### approve.py

```
python scripts/approve.py spec   docs/specs/<id>/spec.md  --by "<nome>" [--commit]
python scripts/approve.py plan   docs/specs/<id>/plan.md  --by "<nome>" [--commit]
python scripts/approve.py tasks  docs/specs/<id>/tasks.md [--commit]
python scripts/approve.py tests  docs/specs/<id> T-01     --by "<nome>" [--base main] [--commit]
python scripts/approve.py review docs/specs/<id>          --by "<nome>" [--diff-read] [--commit]
```

Non è un controllo: registra l'approvazione che l'utente ha **selezionato** tra le opzioni di un gate (guida
`interaction.md` di `sdd-init`), così nessuno scrive a mano nomi, date e hash. `spec` imposta `Status: approved`,
`Approved by / date` e `Hash`; `plan` imposta `Approved by / date`, `Based on spec` (la spec approvata accanto) e `Hash`;
`tasks` imposta `Based on plan` (senza nome: le task si controllano, non si approvano); `tests` aggiunge
`— tests approved: <nome, data, sha>` alla task "expected: red" chiusa, con lo SHA del suo ultimo commit `Test-Lock` nel
branch; `review` imposta `Decided by` e, con `--diff-read`, `Human diff review`. Il nuovo testo deve passare
`spec_lint.py` (o, per la review, avere un esito valido): altrimenti non scrive nulla ed elenca gli errori (exit 1).
`--commit` committa solo quel file con il messaggio `<id spec>: approve <cosa> (<nome>)` e i trailer `Spec:` e
`Approved-by:`. L'agente lo lancia solo nel turno in cui l'utente ha selezionato l'approvazione, con il nome selezionato;
il loop mai.

### Hook `Stop` — `hooks/stop_verify.py`

Abilitazione: `SDD_ENFORCE_VERIFY=1`. Se `scripts/verify.py` esiste ed è rosso, esce con codice 2 e riporta le ultime
30 righe all'agente, che non può dichiarare il lavoro finito. Blocca fino a `SDD_STOP_MAX` volte di fila per sessione
(default 3; contatore per `session_id` in una cartella privata dell'utente, `%LOCALAPPDATA%\sdd-playbook` o
`~/.cache/sdd-playbook`, aperto senza seguire link simbolici e azzerato quando `verify` torna verde), poi lascia fermare
l'agente con un avviso per l'utente (`systemMessage`). Senza `session_id` blocca una volta sola (`stop_hook_active`).
Non agisce se il progetto non ha `verify.py`, o se una spec è in **fase rossa** (in `docs/specs/*/tasks.md` l'ultima task `T-nn` chiusa è
marcata "expected: red" e la successiva è aperta): lì i test rossi sono il risultato atteso. `SDD_VERIFY_ARGS` restringe la
verifica (es. `--fast`).

### Hook `PreToolUse` — `hooks/pretool_guard.py`

Abilitazione: `SDD_GUARD=1`. Analizza ogni comando di Bash e PowerShell per segmenti (`;`, `&&`, `||`, `|`) e parole,
non con una sola espressione regolare. Blocca:
- push forzati o distruttivi: `--force`, `-f` (anche dentro `-uf`), `--force-with-lease`, refspec con `+` (`+main`),
  `--delete`/`-d`, refspec `:branch`, `--mirror`;
- `git reset --hard`, `git clean -f`, anche con opzioni globali (`git -C . reset --hard`) o in altro ordine
  (`git reset HEAD~1 --hard`, `git clean -d -f`);
- cancellazioni ricorsive: `rm` con `-r`/`-R`/`--recursive` in qualsiasi forma (`rm -r -f`, `rm --recursive --force`),
  `git rm -r` senza `--cached`, `find -delete`, `Remove-Item -Recurse` (anche abbreviato), `rd /s`, `del /s|/f|/q`,
  `shutil.rmtree`;
- download-ed-esegui (`curl|wget ... | sh`, `iwr ... | iex`);
- qualsiasi riferimento a un file `.env`, anche attaccato ad altro (`cat .env>x`, `cat <.env`, `open('.env')`, `cp`,
  `Select-String`; maiuscole e stream NTFS come `.env::$DATA`), tranne `.env.example`, `.sample`, `.template` e i comandi
  su `.gitignore` (aggiunta, `grep` nel file, `git check-ignore`).
Per gli strumenti Read e Grep blocca i file `.env` (anche `glob: .env*`). Con un JSON illeggibile o un `tool_input` che non
è un oggetto **blocca** (fail-closed).
Esce con codice 2 e un messaggio. Resta una rete minima: un comando abbastanza contorto la aggira, per questo il
controllo vero sono i permessi nativi dell'agente e l'isolamento.

**Non verificato:** il comportamento in una sessione reale di Claude Code (codice di uscita 2 come blocco, formato del JSON in
ingresso, shell usata per il comando su Windows). Gli script e `run.sh` sono provati con l'input atteso su Linux e Windows
(con `sh` di Git for Windows); se su Windows Claude Code non trova `sh`, gli hook non partono.
