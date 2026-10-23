# Riferimento degli script e degli hook

Tutti gli script stanno in `skills/sdlc-init/scripts/` e `sdlc-init` li copia in `scripts/` del progetto. Sono Python con sola
libreria standard, senza comandi di shell, e girano uguali su Windows, Linux e macOS. Si lanciano dalla **radice del
progetto**. Exit code: `0` ok, `1` controllo fallito, `2` uso errato o precondizione mancante. L'output è sempre UTF-8,
anche con una console Windows in cp1252.

I formati dei file che gli script leggono sono descritti in [architettura.md](architettura.md#contratti-sui-file).

| Script | Usato da | Scopo |
|---|---|---|
| `verify.py` | tutte | criterio di "fatto" del progetto |
| `state.py` | `sdlc-next` | stato e prossima fase |
| `spec_lint.py` | spec, plan, tasks, implement, loop | lint di spec, piano e task |
| `trace_check.py` | tests-from-ac, review-diff | tracciabilità AC → test |
| `bug_lint.py` | bugfix | completezza del file di un bug |
| `diff_scope.py` | review-diff | modifiche vs piano e zone vietate |
| `scan_repo.py` | map-codebase | inventario di una codebase |
| `docs_check.py` | docs | link ed esempi |
| `sync_check.py` | sync | chiusura di una feature |
| `loop.py` | loop | loop autonomo esterno |

---

### verify.py

Esegue gli step di `STEPS` (format, lint, tipi, test) e stampa una riga per step più `VERIFY: VERDE|ROSSO -> ...`.
Va adattato dal progetto: ogni comando è una lista di argomenti, provato a mano prima di registrarlo.

```
python scripts/verify.py                 # tutti gli step, si ferma al primo rosso
python scripts/verify.py --fast          # solo gli step marcati fast (format, lint)
python scripts/verify.py test lint       # solo gli step indicati
python scripts/verify.py --keep-going    # non si ferma al primo rosso
```

Exit: `0` verde, `1` almeno uno step rosso o comando non trovato, `2` nessuno step selezionato. Imposta `PYTHONUTF8=1`.

### state.py

Sola lettura. Riporta infrastruttura (`AGENTS.md`, `verify.py`, CI, `docs/`), presenza di codice esistente e della mappa,
stato di ogni spec, bug non verificati e la riga `PROSSIMO`. Ordine del suggerimento: `sdlc-init` → `sdlc-map-codebase`
(codice esistente senza mappa e senza spec) → `sdlc-spec` → `sdlc-plan` → `sdlc-tasks` → `sdlc-implement` (task `T-nn`
aperte) → `sdlc-review-diff` (review mancante) → `sdlc-implement` (review `non conforme`) → `sdlc-docs` (`T-DOC` aperta) →
`sdlc-sync`. `scripts/`, `docs/`, `.github/` e `.vscode/` non contano come codice esistente.

```
python scripts/state.py [--json] [radice]
```

### spec_lint.py

```
python scripts/spec_lint.py <spec.md> [--plan <plan.md>] [--tasks <tasks.md>]
```

| Modalità | Errori rilevati |
|---|---|
| spec | stato non valido; sezioni mancanti; ID REQ/AC duplicati; REQ senza AC; AC che cita REQ inesistenti; non-scope assente o con segnaposto; se `approved`/`implemented`: approvatore mancante o domande aperte (avviso se restano `[ASSUNZIONE]`) |
| `--plan` | sezione `## Strategia di test` mancante; AC della spec assenti da quella sezione (ID esatto: `AC-001` non vale per `AC-0011`); avviso se il piano non è approvato |
| `--tasks` | nessuna task; task `T-nn` senza `verifica:` o `copre:` o con segnaposto `<...>`; ID duplicati; `T-DOC` o `T-SYNC` mancanti; AC non coperto da nessuna task |

### trace_check.py

```
python scripts/trace_check.py <spec.md> [--tests DIR ...] [--warn-only]
```

Cerca le citazioni degli AC nei file di test (cartelle di default: `tests`, `test`, `__tests__`, `spec`, `src/test`;
estensioni dei linguaggi più comuni) e le attribuisce a una spec, perché gli AC ripartono da AC-001 in ogni spec. L'ID
della spec viene dal titolo `# SPEC-nnn: ...`.
- `SPEC-001/AC-001` (anche `SPEC-001-AC-001`, `SPEC_001_AC_001`, `SPEC001_AC001`) vale per SPEC-001;
- `AC-001`, `AC_001`, `AC001` in un file che nomina una sola spec (es. `# SPEC-001` in testa) vale per quella spec;
- `AC-001` in un file che non nomina spec vale solo se `docs/specs/` contiene una sola spec; altrimenti è **ambigua**,
  non conta ed è segnalata come avviso;
- le citazioni su righe con `TODO`, `FIXME` o `XXX` non contano e sono segnalate.

Stampa per ogni AC il numero di riferimenti o `NESSUN TEST`, segnala i REQ senza alcun AC testato e, come avvisi, gli AC
attribuiti alla spec ma assenti dalla spec, le citazioni ambigue e quelle ignorate. Exit `1` se un AC non ha test (salvo
`--warn-only`), `2` se non trova cartelle di test.

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
`origin/main`, `origin/master`), inclusi file non committati e non tracciati. Segnala:
- **errore** (exit 1): file nelle zone delle righe `- Non modificare:` di `AGENTS.md` (tutte, non solo la prima);
- **errore** (exit 1): file di test bloccati modificati dopo il blocco. Un commit con il trailer `Test-Lock: T-nn` blocca i
  suoi file di test (cartelle `tests`, `test`, `__tests__`, `spec` o nomi come `test_*.py`, `*_test.go`, `*.test.ts`,
  `*Test.java`); una modifica successiva in un commit senza lo stesso trailer, o non committata, è una violazione. I file
  non di test di un commit `Test-Lock` (per esempio uno scheletro) non vengono bloccati e sono segnalati come avviso;
- **avviso** (errore con `--strict`): file fuori dal piano (esclusi `docs/specs/<questa spec>/`, `docs/system/`,
  `docs/bugs/`, `docs/adr/`). Il piano comprende le righe di "Componenti e file" (percorso = prima parola o testo tra
  backtick, quindi `- src/a.py (nuovo): ...` vale `src/a.py`) e la colonna "Dove" della strategia di test;
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
python scripts/sync_check.py docs/specs/001-x [--area docs/system/<area>.md] [--tests DIR ...]
```

Verifica che: la spec sia valida con `Stato: implemented`; nessuna task sia aperta; `review.md` abbia un esito valido,
diverso da `non conforme`, e la "Decisione di" compilata; esista una pagina d'area (o quella indicata) con le sezioni
richieste, "Ultimo allineamento" compilato e la spec tra le "Specifiche collegate"; ogni AC sia citato in un test **di
questa spec**, con le regole di `trace_check.py` (se mancano test e ci sono citazioni ambigue, l'errore lo dice).

### loop.py

```
python scripts/loop.py docs/specs/001-x [--max 15] [--stall 3] [--timeout 1800] [--agent "claude -p"]
                                        [--allow-main] [--allow-red-baseline] [--dry-run]
```

Legge `PROMPT.md` dalla cartella della spec e lo passa all'agente da stdin. Dopo ogni iterazione esegue `verify`.
Si ferma con exit `0` se `verify` è verde e non restano task `T-nn` aperte (`T-DOC` e `T-SYNC` restano fuori); con
exit `1` al tetto `--max` o dopo `--stall` iterazioni senza cambiamenti (tasks.md, HEAD di git, **contenuto** delle
modifiche tracciate e non tracciate: un agente che lavora sempre sullo stesso file non è in stallo). Ogni iterazione dura al
massimo `--timeout` secondi: oltre, l'agente viene terminato e il loop prosegue; un codice di uscita diverso da zero viene
riportato come avviso. Rifiuta di partire (exit `2`) su `main`/`master` (salvo `--allow-main` in ambienti isolati) e con
`verify` già rosso, salvo fase rossa (l'ultima task `T-nn` chiusa è "atteso: rosso") o `--allow-red-baseline`.
`--dry-run` controlla le precondizioni senza lanciare l'agente e mostra se c'è una fase rossa. Non fa push. Permessi e
modalità non interattiva dell'agente vanno configurati a parte.

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
30 righe all'agente, che non può dichiarare il lavoro finito. Non agisce se `stop_hook_active` è vero (evita cicli), se il
progetto non ha `verify.py`, o se una spec è in **fase rossa** (in `docs/specs/*/tasks.md` l'ultima task `T-nn` chiusa è
marcata "atteso: rosso" e la successiva è aperta): lì i test rossi sono il risultato atteso. `SDLC_VERIFY_ARGS` restringe la
verifica (es. `--fast`).

### Hook `PreToolUse` — `hooks/pretool_guard.py`

Abilitazione: `SDLC_GUARD=1`. Per Bash e PowerShell blocca: `git push --force`/`-f`, `git reset --hard`, `rm -rf`,
`Remove-Item -Recurse -Force`, `rd /s`, `del /s|/f|/q`, download-ed-esegui (`curl|wget ... | sh`, `iwr ... | iex`), lettura di
`.env`; per lo strumento Read blocca i file `.env` (non `.env.example`). Esce con codice 2 e un messaggio.

**Non verificato:** il comportamento in una sessione reale di Claude Code (codice di uscita 2 come blocco, formato del JSON in
ingresso, shell usata per il comando su Windows). Gli script e `run.sh` sono provati con l'input atteso su Linux e Windows
(con `sh` di Git for Windows); se su Windows Claude Code non trova `sh`, gli hook non partono.
