# Riferimento di script e hook

*English version: [scripts.md](scripts.md)*

Tutti gli script stanno in `skills/sdd-start/scripts/` e `sdd-start` li copia nella cartella `scripts/` del progetto.
Sono Python con sola libreria standard, senza comandi di shell, e si comportano allo stesso modo su Windows, Linux e
macOS. Si eseguono dalla **radice del progetto**. La seconda riga di ogni script riporta la versione del plugin
(`# sdd-playbook: <versione>`), per sapere quali copie aggiornare (`sdd-start`, "Updating"). Codici di uscita: `0` ok,
`1` controllo fallito, `2` uso errato o precondizione mancante. L'output è sempre UTF-8, anche su una console Windows in
cp1252. I messaggi sono in inglese.

I formati dei file che gli script leggono sono descritti in [architecture_IT.md](architecture_IT.md#contratti-sui-file).

| Script | Usato da | Scopo |
|---|---|---|
| `verify.py` | tutte | la definizione di "fatto" del progetto |
| `spec_lint.py` | start, plan, task | lint della spec e del piano con i suoi task |
| `trace_check.py` | task, bugfix | tracciabilità AC → test, per task o per l'intera feature |
| `diff_scope.py` | task, parallel | il branch del task: zone vietate, test bloccati, perimetro, aree sensibili, dimensione |
| `state.py` | next, task, parallel | il passo successivo e i task pronti |
| `docs_check.py` | task, map | link, diagrammi Mermaid, i cinque diagrammi di `docs/system/`, esempi |
| `secrets_check.py` | `verify` | segreti nei file |
| `scan_repo.py` | map | inventario di una codebase |

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

### spec_lint.py

```
python scripts/spec_lint.py <spec.md> [--plan <plan.md>]
```

| Modalità | Errori | Avvisi |
|---|---|---|
| spec | `- Status:` diverso da `draft`, `approved`, `implemented`, `superseded`; titolo senza `# SPEC-<id>:`, data non valida o ID diverso dal nome della cartella; sezioni mancanti (Problem and goal, Scope, Requirements, Acceptance criteria, Open questions); ID REQ o AC duplicati; REQ senza AC; AC che cita un REQ inesistente; non-scope mancante o segnaposto; una spec `approved` o `implemented` con domande aperte bloccanti (o senza `blocking: yes|no`) | anti-goal o `## Current behaviour and impact` mancanti; parole vaghe in REQ e AC ("fast", "appropriate", "should", "etc", ...); domande aperte non bloccanti e `[ASSUMPTION]` rimasti in una spec approvata |
| `--plan` | `## Flowchart` mancante o senza un flowchart ```` ```mermaid ````; `## Tasks` mancante o vuota; una riga di task con un segnaposto, senza `covers:` (o che copre un AC non presente nella spec), senza `files:`, `verify: `<comando>`` o `depends:`, dipendente da un task inesistente o in un ciclo di dipendenze; ID di task duplicati; un AC della spec non coperto da alcun task; `## Review focus` mancante o non compilata (`- none` è valido) | `## Approach` mancante; più di 8 task (dividere la feature) |

Non c'è un campo da firmare: l'approvazione di spec e piano è il merge della PR di design, registrato da git. Lo stesso
modulo controlla la sezione `## Diagrams` delle pagine di documentazione per `docs_check.py` (cinque diagrammi, ognuno
un blocco Mermaid del suo tipo o `- n/a: <motivo>`; il flowchart si applica sempre).

### trace_check.py

```
python scripts/trace_check.py <spec.md> [--task T-nn] [--tests DIR ...] [--junit FILE|DIR ...] [--warn-only]
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
illeggibile o `--junit` senza valore: exit `2`. Il report lo scrive `verify` (vedi `references/stacks.md` di `sdd-start`).

**Altri linguaggi e file di test dichiarati.** I file di test si cercano nelle cartelle di test con le estensioni
comuni (Python, JavaScript/TypeScript, Java, Kotlin, Scala, C#, F#, Go, Ruby, PHP, Rust, C/C++, Swift, Dart, Elixir,
shell, bats, PowerShell, Gherkin, Robot, HCL, YAML), più i percorsi o glob di `- Test files:` in `AGENTS.md`. La
citazione breve accetta anche `ac_001` (Rust e altri nomi snake_case) e quella qualificata non distingue maiuscole.

**`--task T-nn`: il controllo della PR di un task.** Solo gli AC che il task copre (`covers:` nel `plan.md` accanto alla
spec) devono avere test (eseguiti e passati con `--junit`); gli AC dei task successivi non vengono segnalati. Senza
`--task` ogni AC della spec, e ogni REQ deve avere un AC testato: il controllo dell'intera feature, eseguito dal suo
ultimo task. Un task sconosciuto: exit `2`.

### diff_scope.py

```
python scripts/diff_scope.py docs/specs/<id> --task T-nn [--base main] [--strict]
python scripts/diff_scope.py docs/specs/<id> [--base main] [--strict]        # l'intero branch
```

Calcola i file modificati dal merge-base con il ref di base (default: il primo tra `main`, `master`, `origin/main`,
`origin/master`), compresi quelli non committati e non tracciati; i file generati (`__pycache__/`, `*.pyc`, `reports/`)
non contano. `AGENTS.md` si legge **dal merge-base** quando esiste lì: il branch non può allentarlo. Segnala:
- **errore** (exit 1): file nelle zone `- Do not modify:` di `AGENTS.md`;
- **errore** (exit 1): **test bloccati** modificati dopo il blocco. Un commit con il trailer `Test-Lock: T-nn` blocca i
  suoi file di test (cartelle `tests`, `test`, `__tests__`, `spec` o nomi come `test_*.py`, `*_test.go`, `*.test.ts`,
  `*Test.java`); una modifica successiva in un commit senza lo stesso trailer, o non committata, è una violazione. I
  file non di test di un commit `Test-Lock` non sono bloccati (avviso);
- **avviso** (errore con `--strict`): file fuori dai `files:` del task (di tutti i task senza `--task`), esclusi la
  cartella della spec, `docs/system/`, `docs/bugs/`, `docs/adr/` e gli strumenti del processo (gli script del playbook
  in `scripts/`, `AGENTS.md`, `CLAUDE.md`, `.github/`, `.vscode/`, i file di git);
- **avviso**: un manifest o lockfile delle dipendenze modificato (una nuova dipendenza si chiede prima e si dichiara
  nella PR);
- **avviso**: più di 400 righe modificate fuori da test e docs (la PR è difficile da leggere: valuta di dividerla);
- **riga `SENSITIVE:`**: file nelle `- Sensitive areas:` di `AGENTS.md`, da copiare nella descrizione della PR: l'umano
  ne legge il diff prima del merge. Non è un errore.

I file di test si riconoscono dalla cartella (`tests`, `test`, `__tests__`, `spec`) e dal nome (`test_*`, `*_test.*`,
`*.test.*`, `*.spec.*`, `*Test.*`, `*Tests.*`, `*.bats`, `*.tftest.hcl`); i manifest dal nome, per gli ecosistemi
comuni (npm, pip, uv, Poetry, Go, Cargo, Maven, Gradle, NuGet, Bundler, Composer, Mix, Pub, SwiftPM, Deno, Bun, conda,
Terraform, Helm, Conan, vcpkg). Un progetto aggiunge i propri con `- Test files: a, b` e `- Dependency manifests: a, b`
in `AGENTS.md`.

Percorsi: esatti, cartelle (prefisso) o glob (`**/` vale anche per nessuna cartella); il prefisso `./` si ignora, i
punti iniziali (`.github/`) restano. Exit `2` se non è un repository git, manca il ref di base o il task non esiste.

### state.py

```
python scripts/state.py [--json] [--spec <id>] [radice]
```

Sola lettura. Legge `AGENTS.md` e `scripts/verify.py` (inizializzazione), le spec in `docs/specs/` e, da git, la
versione di spec e piano su `main` (o `master`; senza git la copia di lavoro vale come `main`). Il passo successivo:

```
senza AGENTS.md o scripts/verify.py ................. sdd-start (inizializzazione)
codice esistente, senza mappa e senza spec .......... sdd-map
nessuna spec attiva ................................. sdd-start (prossima idea)
più spec attive, nessuna scelta ..................... choose (--spec <id>, o il branch della spec)
--- per la spec scelta ---
Status draft (o mancante) ........................... sdd-start (confermare la spec)
plan.md mancante .................................... sdd-plan
spec o piano non ancora su main ..................... sdd-plan (aprire e unire la PR di design)
due o più task pronti con file disgiunti ............ sdd-parallel (al massimo 3, indicati)
un task pronto ...................................... sdd-task (indicato)
task aperti, nessuno pronto ......................... sdd-task (prima unire le PR aperte)
tutti i task uniti, Status non implemented .......... sdd-task (chiudere la feature)
```

Un task è **fatto** quando la sua casella è spuntata nel piano **su `main`** (la sua PR è stata unita), **pronto**
quando non è fatto e tutte le sue dipendenze sono fatte. Una spec `implemented` o `superseded` non è più attiva. I bug
aperti (`docs/bugs/*.md` non `fixed` né `verified`) sono elencati per `sdd-bugfix`. `--json` stampa lo stato completo.

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
richiede la sezione `## Diagrams` con i cinque diagrammi, ognuno disegnato o `- n/a: <motivo>` (il flowchart si applica sempre). Un blocco di codice si chiude solo con una recinzione dello stesso carattere
lunga almeno quanto quella d'apertura, così un template mostrato in un blocco ```` ```` ```` conserva i blocchi interni.

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

### scan_repo.py

```
python scripts/scan_repo.py [radice] [--json]
```

Inventario in sola lettura: manifest e stack, linguaggi (file e righe), struttura di primo livello, cartelle di test,
CI, entry point probabili, documentazione. Usa `git ls-files` se disponibile. È un inventario, non una comprensione.

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

### Hook `Stop` — `hooks/stop_verify.py`

Abilitazione: `SDD_ENFORCE_VERIFY=1`. Se `scripts/verify.py` esiste ed è rosso, esce con codice 2 e riporta le ultime
30 righe all'agente, che non può dichiarare il lavoro finito. Blocca fino a `SDD_STOP_MAX` volte di fila per sessione
(default 3; contatore per `session_id` in una cartella privata dell'utente, `%LOCALAPPDATA%\sdd-playbook` o
`~/.cache/sdd-playbook`, aperto senza seguire link simbolici e azzerato quando `verify` torna verde), poi lascia fermare
l'agente con un avviso per l'utente (`systemMessage`). Senza `session_id` blocca una volta sola (`stop_hook_active`).
Non agisce se il progetto non ha `verify.py`, o nella **fase rossa** di un task: l'ultimo commit del branch porta il
trailer `Test-Lock: T-nn` (i test rossi sono appena stati bloccati e l'implementazione non è iniziata): lì i test rossi
sono il risultato atteso. `SDD_VERIFY_ARGS` restringe la
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
