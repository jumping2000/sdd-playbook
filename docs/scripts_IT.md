# Riferimento degli script e degli hook

*English version: [scripts.md](scripts.md)*

Tutti gli script stanno in `skills/sdlc-init/scripts/` e `sdlc-init` li copia in `scripts/` del progetto. Sono Python con sola
libreria standard, senza comandi di shell, e girano uguali su Windows, Linux e macOS. Si lanciano dalla **radice del
progetto**. La seconda riga di ogni script riporta la versione del plugin (`# sdlc-playbook: <versione>`), per
sapere quali copie aggiornare (`sdlc-init`, sezione "Aggiornare un progetto"). Exit code: `0` ok, `1` controllo fallito, `2` uso errato o precondizione mancante. L'output è sempre UTF-8,
anche con una console Windows in cp1252.

I formati dei file che gli script leggono sono descritti in [architecture_IT.md](architecture_IT.md#contratti-sui-file).

| Script | Usato da | Scopo |
|---|---|---|
| `verify.py` | tutte | criterio di "fatto" del progetto |
| `state.py` | `sdlc-next` | stato e prossima fase |
| `spec_lint.py` | spec, plan, tasks, implement, loop | lint di spec, piano e task |
| `trace_check.py` | tests-from-ac, review-diff | tracciabilità AC → test |
| `bug_lint.py` | bugfix | completezza del file di un bug |
| `diff_scope.py` | review-diff, sync, loop | modifiche vs piano, zone vietate, test bloccati e livello |
| `scan_repo.py` | map-codebase | inventario di una codebase |
| `docs_check.py` | docs | link ed esempi |
| `sync_check.py` | sync | chiusura di una feature |
| `secrets_check.py` | review-diff, loop, `verify` | segreti nei file |
| `loop.py` | loop | loop autonomo esterno |

---

### verify.py

Esegue gli step di `STEPS` (format, lint, tipi, test, segreti) e stampa una riga per step più `VERIFY: VERDE|ROSSO -> ...`.
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
`PROSSIMO`.
Ordine del suggerimento per una spec: `sdlc-spec` (bozza, `in-revisione`, approvazione decaduta) → `sdlc-plan` (mancante,
da approvare o decaduto) → `sdlc-tasks` (mancanti o basate su un altro piano) → `sdlc-implement` (task `T-nn`/`T-Rnn`
aperte) → `sdlc-review-diff` (review mancante; con `non conforme`: creare le `T-R`, o ripetere la review quando sono
chiuse) → `sdlc-docs` (`T-DOC` aperta) → `sdlc-sync`. Prima di tutto `sdlc-init` e, nel brownfield senza mappa né spec,
`sdlc-map-codebase`. `scripts/`, `docs/`, `.github/` e `.vscode/` non contano come codice esistente.

**Livelli** (playbook §2.1). Livello S: dopo la spec approvata `sdlc-tasks` (senza piano), poi `sdlc-implement`,
`sdlc-docs` se `T-DOC` è aperta e `sdlc-sync`; `review.md` conta solo se c'è ed è `non conforme`. Livelli M e L: una
task di test "atteso: rosso" chiusa senza `test approvati:` porta a `sdlc-tests-from-ac` prima dell'implementazione.
Livello L: dopo una review accettata serve anche `- Revisione umana del diff:` in `review.md`, altrimenti
`sdlc-review-diff`. Senza il campo `- Livello:` la spec vale M.

**Più spec attive.** `PROSSIMO` riguarda la spec indicata con `--spec <id>` (nome della cartella o ID del titolo), quella
il cui nome di cartella compare nel branch corrente (`feat/2026-10-24-export-csv`), o l'unica attiva. Altrimenti riporta
`scegli` con l'elenco delle spec e del loro passo: la scelta è dell'utente.

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
`- Basato su spec:` uguale all'hash attuale della spec: se la spec cambia, il piano decade. Con `--base <ref>` spec e
piano devono esistere su `<ref>` ed essere identici alla copia di lavoro: il merge della PR di design su un branch
protetto è l'approvazione che l'agente non può darsi da solo (playbook §1.2).

| Modalità | Errori rilevati |
|---|---|
| spec | stato non valido (`draft`, `approved`, `in-revisione`, `implemented`, `superseded`); livello diverso da S, M, L (avviso se manca: vale M); titolo senza ID `# SPEC-<id>:`, data non valida o ID diverso dal nome della cartella; `in-revisione` senza una voce in `## Revisioni`; sezioni mancanti; ID REQ/AC duplicati; REQ senza AC; AC che cita REQ inesistenti; non-scope assente o con segnaposto; se `approved`/`implemented`: approvatore mancante, hash mancante o non corrispondente, domande aperte (avviso se restano `[ASSUNZIONE]`) |
| `--plan` | sezione `## Strategia di test` mancante; AC della spec assenti da quella sezione (ID esatto: `AC-001` non vale per `AC-0011`); piano approvato con hash non valido o basato su un'altra versione della spec; avviso se il piano non è approvato |
| `--base` | spec o piano assenti su `<ref>` o diversi dalla versione su `<ref>` |
| `--tasks` | nessuna task; task `T-nn` senza `verifica:` o `copre:` o con segnaposto `<...>`; task `T-Rnn` senza `verifica:` o con segnaposto (`copre:` facoltativo); ID duplicati; `T-SYNC` mancante, o `T-DOC` mancante salvo nel livello S; AC non coperto da nessuna task |
| `--plan` e `--tasks` insieme | task con `- Basato su piano:` diverso dall'hash del piano (avviso se il campo manca) |

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

Stampa per ogni AC il numero di riferimenti o `NESSUN TEST`, segnala i REQ senza alcun AC testato e, come avvisi, gli AC
attribuiti alla spec ma assenti dalla spec, le citazioni ambigue e quelle ignorate. Exit `1` se un AC non ha test (salvo
`--warn-only`), `2` se non trova cartelle di test.

**`--junit`: test eseguiti, non solo citati.** Con uno o più report JUnit XML (file, o cartelle di cui si leggono tutti
gli `*.xml`) ogni AC deve avere almeno un caso di test **eseguito e passato** e nessuno fallito; i casi saltati non
contano. Un caso vale per un AC se lo cita in forma qualificata nel nome o nel `classname`, oppure in forma breve quando
appartiene a un file di test attribuito alla spec (attributo `file`, o un componente del `classname` uguale al nome del
file, come `tests.test_export` per `tests/test_export.py` o `com.acme.ExportTest` per `ExportTest.java`) o il progetto
ha una sola spec. Il file di un caso è quello il cui percorso coincide più a lungo con `file` o `classname`: file
omonimi in cartelle diverse non si confondono, e a pari merito tra file di spec diverse il caso non conta. Report
illeggibile o `--junit` senza valore: exit `2`. Il report lo scrive `verify` (vedi `references/stacks.md` di `sdlc-init`).

### bug_lint.py

```
python scripts/bug_lint.py docs/bugs/BUG-001-esempio.md
```

I requisiti crescono con lo stato: `aperto` → riproduzione compilata; `diagnosticato` → atteso e attuale, "da NON
cambiare", causa radice, percorso del test rosso; `corretto` → fix minimo descritto e test di non-regressione indicato;
`verificato` → tutte le voci di "Chiusura" spuntate. Segnaposto `<...>` ed etichette vuote non contano come contenuto.

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
- **errore** (exit 1): file nelle zone delle righe `- Non modificare:` di `AGENTS.md` (tutte, non solo la prima);
- **errore** (exit 1): file di test bloccati modificati dopo il blocco. Un commit con il trailer `Test-Lock: T-nn` blocca i
  suoi file di test (cartelle `tests`, `test`, `__tests__`, `spec` o nomi come `test_*.py`, `*_test.go`, `*.test.ts`,
  `*Test.java`); una modifica successiva in un commit senza lo stesso trailer, o non committata, è una violazione. I file
  non di test di un commit `Test-Lock` (per esempio uno scheletro) non vengono bloccati e sono segnalati come avviso;
- **avviso** (errore con `--strict`): file fuori dal piano (esclusi `docs/specs/<questa spec>/`, `docs/system/`,
  `docs/bugs/`, `docs/adr/`). Il piano comprende le righe di "Componenti e file" (percorso = prima parola o testo tra
  backtick, quindi `- src/a.py (nuovo): ...` vale `src/a.py`) e la colonna "Dove" della strategia di test;
- **errore** (exit 1): **livello sottostimato** (playbook §2.1). Un file nelle righe `- Aree sensibili:` di `AGENTS.md`
  richiede L; una modifica a un manifest o lockfile delle dipendenze (`package.json`, `pyproject.toml`,
  `requirements*.txt`, `go.mod`, `*.csproj`, i lockfile, ...) o più di 3 file di produzione (esclusi test, `docs/` e
  `*.md`) richiedono almeno M. Il livello dichiarato viene da `- Livello:` della spec (M se manca); nel livello S senza
  piano il confronto con il piano è saltato;
- **errore** (exit 1): **dipendenze senza decisione**: un manifest o lockfile modificato che il piano non elenca (un
  lockfile vale se il piano elenca il suo manifest nella stessa cartella), in un diff che non **aggiunge** un ADR in
  `docs/adr/` (README e indici non contano). Playbook §8: nuove dipendenze solo con ADR o nel piano approvato;
- **errore** (exit 1): **test approvati superati**: lo SHA di `test approvati: <nome, data, sha>` non è un commit
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

### sync_check.py

```
python scripts/sync_check.py docs/specs/001-x [--area docs/system/<area>.md] [--tests DIR ...] [--junit FILE|DIR ...]
```

Verifica che: la spec sia valida con `Stato: implemented`; nessuna task sia aperta; `review.md` abbia un esito valido,
diverso da `non conforme`, e la "Decisione di" compilata; esista una pagina d'area (o quella indicata) con le sezioni
richieste, "Ultimo allineamento" compilato e la spec tra le "Specifiche collegate"; ogni AC sia citato in un test **di
questa spec**, con le regole di `trace_check.py` (se mancano test e ci sono citazioni ambigue, l'errore lo dice).
Livello S: `review.md` e pagina d'area facoltative (se `review.md` c'è, si controlla). Livello L: `review.md` deve avere
anche `- Revisione umana del diff:` compilato. Nei livelli M e L le task di test chiuse ("atteso: rosso") riportano
`test approvati:`. Con `--junit` gli AC devono essere verificati dal report dei test eseguiti, come in `trace_check.py`;
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
cartella e `secrets_check.py`, se presenti in `scripts/`. Le caselle le spunta l'agente; questi controlli no. Se `diff_scope` non può calcolare il diff (exit `2`, per esempio
senza ref di base) è un avviso; con
exit `1` al tetto `--max` o dopo `--stall` iterazioni senza cambiamenti (tasks.md, HEAD di git, **contenuto** delle
modifiche tracciate e non tracciate, esclusi i file generati come `__pycache__/` e `reports/`: un agente che lavora
sempre sullo stesso file non è in stallo, un report che cambia a ogni `verify` non è progresso). Con `--junit` avvisa se
il report non è ignorato da git. Ogni iterazione dura al
massimo `--timeout` secondi: oltre, l'agente viene terminato e il loop prosegue; un codice di uscita diverso da zero viene
riportato come avviso. Rifiuta di partire (exit `2`) su `main`/`master` (salvo `--allow-main` in ambienti isolati) e con
`verify` già rosso, salvo fase rossa (l'ultima task `T-nn` chiusa è "atteso: rosso") o `--allow-red-baseline`.
**Test da approvare** (livelli M e L): se dopo un'iterazione una task di test "atteso: rosso" è chiusa senza
`test approvati:`, il loop si ferma con exit `1` perché l'umano rilegga i test bloccati; con un'approvazione già in
attesa non parte (exit `2`). Con `--junit` il controllo finale `trace_check.py` usa il report dei test eseguiti.
`--dry-run` controlla le precondizioni senza lanciare l'agente e mostra se c'è una fase rossa. Non fa push. Permessi e
modalità non interattiva dell'agente vanno configurati a parte: `skills/sdlc-loop/references/settings.loop.json` è un
esempio di allowlist e deny-list per Claude Code (nega anche la scrittura di `scripts/`, `AGENTS.md`, `.github/`, spec,
piano e review: i controlli e le regole del loop) (`--agent "claude -p --settings <file>"`, da verificare sulla versione).

---

## Hook opzionali (solo Claude Code)

Si caricano con il plugin (`hooks/hooks.json`) ma restano **inattivi** finché non imposti la variabile d'ambiente.
Sono una rete di sicurezza minima, non un sandbox: non sostituiscono permessi, allowlist e isolamento.

Entrambi partono da `hooks/run.sh` (`sh run.sh <script.py> <variabile>`). Il launcher esce `0` subito se la variabile non
vale `1`, quindi un hook inattivo non richiede Python. Se è attivo usa il primo tra `python3`, `python` e `py -3` che sia
davvero Python 3.8+ (scarta gli alias di Microsoft Store e Python 2): su Ubuntu pulito esiste solo `python3`. Senza
Python 3 esce `1` con un messaggio, cioè un errore visibile ma non bloccante.

### Hook `Stop` — `hooks/stop_verify.py`

Abilitazione: `SDLC_ENFORCE_VERIFY=1`. Se `scripts/verify.py` esiste ed è rosso, esce con codice 2 e riporta le ultime
30 righe all'agente, che non può dichiarare il lavoro finito. Blocca fino a `SDLC_STOP_MAX` volte di fila per sessione
(default 3; contatore per `session_id` in una cartella privata dell'utente, `%LOCALAPPDATA%\sdlc-playbook` o
`~/.cache/sdlc-playbook`, aperto senza seguire link simbolici e azzerato quando `verify` torna verde), poi lascia fermare
l'agente con un avviso per l'utente (`systemMessage`). Senza `session_id` blocca una volta sola (`stop_hook_active`).
Non agisce se il progetto non ha `verify.py`, o se una spec è in **fase rossa** (in `docs/specs/*/tasks.md` l'ultima task `T-nn` chiusa è
marcata "atteso: rosso" e la successiva è aperta): lì i test rossi sono il risultato atteso. `SDLC_VERIFY_ARGS` restringe la
verifica (es. `--fast`).

### Hook `PreToolUse` — `hooks/pretool_guard.py`

Abilitazione: `SDLC_GUARD=1`. Analizza ogni comando di Bash e PowerShell per segmenti (`;`, `&&`, `||`, `|`) e parole,
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
