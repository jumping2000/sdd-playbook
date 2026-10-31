# Review critica di sdlc-playbook 0.4.0

*English version: [REVIEW.md](REVIEW.md)*

> Documento storico: usa i nomi della 0.4.0 (`sdlc-*`, `SDLC_*`, campi in italiano). Dalla 0.13.0 il plugin si chiama
> SDD Playbook (`sdd-*`, `SDD_*`, campi in inglese).

- Data: 2026-10-23
- Oggetto: playbook (`docs/playbook-ai-software-lifecycle.md`), 14 skill, 2 hook, subagent `sdlc-reviewer`, 10 script
- Revisore: Claude (Opus 5.5) su richiesta del proprietario del repository
- Codice del plugin: **non modificato**. Il commit di import contiene lo zip 0.4.0 così com'è; questa review elenca i
  problemi, non li corregge.

## Sintesi

L'impianto è buono: non-scope obbligatorio, test di caratterizzazione nel brownfield, "comportamento da NON
cambiare" nei bug, criteri di stop oggettivi per il loop, limiti dichiarati con onestà nel README. I problemi seri
sono tre:

1. **Garanzie solo apparenti.** Approvazioni, tracciabilità e stop del loop sono controllati da script che
   verificano la *presenza* di testo che l'agente stesso può scrivere.
2. **Meccanismi in conflitto.** Il TDD richiede test rossi; l'hook `Stop` e il prompt del loop spingono l'agente a
   renderli verdi.
3. **Mai provato end-to-end.** Il README lo ammette (skill mai eseguite da un agente reale, hook mai in una sessione
   vera, loop mai con `claude -p`). In più, su Windows nativo la suite del plugin fallisce e su Linux pulito gli hook
   non partono.

## Ambienti e risultati

| Ambiente | Come | Suite del plugin (61 test) | Note |
|---|---|---|---|
| Windows 11, Python 3.13, console cp1252 | `python -m unittest discover -s tests` | **3 errori** | Encoding: vedi B1 |
| Linux: Ubuntu 24.04 su WSL2, Python 3.12.3, filesystem ext4 | clone del repository, stesso comando | **OK** | Anche con `LC_ALL=C` |
| GitHub Actions (`.github/workflows/ci.yml`) | push su `main` | vedi sezione "CI su GitHub" | |

Le prove sugli script (sezione B) sono state ripetute su entrambe le piattaforme con lo stesso esito, salvo dove
indicato: i difetti di logica non dipendono dal sistema operativo.

## A. Criticità di processo (playbook)

**A1. I gate umani non sono applicati.** "Approvata da / data" è un campo di testo che compila l'agente; gli script
verificano solo che non sia vuoto o un segnaposto. L'approvazione non è legata a una versione: una spec modificata
dopo l'ok resta `approved`.
*Proposta:* approvazione come atto che l'agente non può compiere (review di PR con CODEOWNERS su `docs/specs/**`,
commit firmato dell'umano); in alternativa minima, hash della spec approvata registrato nel piano e `spec_lint` che
fallisce se il file cambia.

**A2. Il TDD è in conflitto con l'automazione.** Le task di test devono finire rosse ("atteso: rosso"), ma:
- l'hook `Stop` impedisce di fermarsi con `verify` rosso, quindi spinge l'agente a implementare subito o a
  indebolire i test;
- `PROMPT.md` del loop dice "se fallisce correggi, a verde commit" e non conosce le task "atteso: rosso".

La regola "i test rossi non si committano da soli" elimina anche il punto di controllo più utile: con i test
committati prima dell'implementazione si potrebbe verificare che il commit di implementazione non li tocchi.
*Proposta:* commit dei test rossi (marcati `xfail`/skip con ID, o CI tollerante sul branch) e un controllo che i file
di test non cambino nel commit di implementazione senza approvazione.

**A3. La tracciabilità non regge più spec.** Gli AC ripartono da AC-001 in ogni spec, `trace_check` cerca in tutti i
test. Una citazione in un commento (`# TODO AC-003`) vale come test. Lo script misura citazioni, non test che esistono
e passano (prova B4).
*Proposta:* ID qualificati (`SPEC-002/AC-001`) e, dove possibile, report dei test eseguiti (JUnit XML).

**A4. Lo stop del loop dipende da ciò che dichiara l'agente.** Esce con `verify` verde e caselle spuntate, ma le
caselle le spunta l'agente. *Proposta:* aggiungere `trace_check` e `diff_scope` al criterio di uscita.

**A5. Review poco indipendente.** Stesso modello in contesto fresco: errori correlati. Il subagent "in sola lettura"
ha `Bash`, quindi la sola lettura è un'istruzione, non un vincolo. Il principio 5 ("non rileggi ogni riga") lascia un
vuoto di responsabilità. *Proposta:* review umana obbligatoria sulle aree sensibili, o un modello diverso per la
review; strumenti del subagent senza scrittura.

**A6. Cerimonia e gate fatigue.** Circa 7 documenti e 4-5 gate per feature; la soglia "feature piccola" ("descrivi il
diff in una frase") è vaga. Documentazione duplicata (spec, pagina d'area, README, ADR, mappa): T-SYNC rischia di
diventare un rituale. *Proposta:* livelli espliciti S/M/L con criteri oggettivi (file toccati, API pubbliche, aree
sensibili); dopo `implemented` la spec diventa archivio e la fonte viva sono pagina d'area e test.

**A7. Sicurezza fuori perimetro, ma è il rischio tipico del codice generato.** Il template di `verify` non ha audit
delle dipendenze né scansione dei segreti; "nuove dipendenze solo con ADR" non è controllato da nessuno script; il
loop gira senza supervisione e non si parla di prompt injection. *Proposta:* `diff_scope` segnala modifiche a
manifest e lockfile; gitleaks e audit delle dipendenze come step di `verify`.

**A8. Lavoro in team non previsto.** Numeri `SPEC-NNN` che collidono tra branch; `state.py` considera solo la prima
spec attiva; nessun flusso per modificare una spec approvata; i problemi della review non diventano task (dopo un
"non conforme" `state.py` rimanda a `sdlc-implement`, che non trova task aperte).

## B. Difetti confermati negli script e negli hook

| # | Dove | Problema | Windows | Linux |
|---|---|---|---|---|
| B1 | tutti gli script | Stampano testo non ASCII ("è") con l'encoding della console. Su Windows è cp1252: chi legge in UTF-8 (test, agente) riceve caratteri illeggibili o `None`. Manca `sys.stdout.reconfigure(encoding="utf-8")` | 3 test falliscono | OK |
| B2 | `hooks/hooks.json` | Lancia `python ...`. Su Ubuntu pulito `python` non esiste (c'è solo `python3`): l'hook esce 127, che per Claude Code è un errore **non bloccante**, quindi `SDLC_ENFORCE_VERIFY` e `SDLC_GUARD` non hanno effetto e nessuno se ne accorge. Su Windows `python` può mancare dal PATH (per questo `tasks.json` usa `py -3`) | rischio | **confermato** (exit 127) |
| B3 | `diff_scope.py` | `lstrip("./")` toglie tutti i punti iniziali: `.github/` diventa `github/` e non corrisponde mai. In un repo git reale con `- Non modificare: .github/`, una modifica a `.github/workflows/ci.yml` dà solo un avviso "fuori piano" ed exit 0 | confermato | confermato |
| B4 | `trace_check.py` | Ricerca globale degli ID: una SPEC-002 senza test propri risulta coperta al 100% dai test di SPEC-001; un commento TODO conta come test | confermato | confermato |
| B5 | `diff_scope.py` | Legge solo la prima riga `Non modificare:`; `- src/a.py (nuovo): ...` diventa il percorso `src/a.py (nuovo)`; i test non elencati nel piano producono rumore "fuori piano" | confermato | confermato |
| B6 | `spec_lint.py --tasks` | Accetta il template con i segnaposto (`verifica: \`<comando test mirato>\``). È voluto: `test_coerenza` verifica che il template passi il lint. Ma allora il lint non distingue un `tasks.md` compilato da uno copiato | confermato | confermato |
| B7 | `spec_lint.py --plan` | Controllo per sottostringa: basta citare gli AC in una frase qualsiasi; `AC-1` risulta presente dentro `AC-10` | confermato | confermato |
| B8 | `loop.py` | Il progresso è calcolato da `git status --porcelain`, che riporta solo i nomi dei file. Prova: un agente che aggiunge una riga per iterazione allo stesso file (già modificato, non ancora committato) viene fermato per "nessun progresso" dopo 2 iterazioni con `--stall 2`, mentre il lavoro avanzava. Inoltre: nessun timeout per iterazione, exit code dell'agente ignorato, baseline verde non controllata | — | **confermato** |
| B9 | `stop_verify.py` | Blocca una volta sola (`stop_hook_active`); esegue il `verify` completo a ogni fine turno, anche quando l'utente fa solo una domanda | per costruzione | per costruzione |
| B10 | `pretool_guard.py` | Aggirabile: `rm -r -f`, `rm --recursive --force`, `git push origin +main`, `Remove-Item -Recurse`, `shutil.rmtree`, `Select-String .env`, `cp .env`, tool Grep sul file passano tutti. `ENV_FILE` non ignora le maiuscole (`.ENV` su Windows), non gestisce gli stream NTFS (`.env::$DATA`), e con JSON illeggibile lascia passare (fail-open) | confermato | confermato |
| B11 | repository del plugin | Non ha un proprio `.gitattributes`, che il playbook raccomanda: su Windows con `core.autocrlf=true` gli script vanno in CRLF nella copia di lavoro | osservato | — |

## C. Skill

- **`sdlc-loop`:** nessuna configurazione dei permessi. `claude -p` senza allowlist o si blocca (stallo) o spinge a
  `--dangerously-skip-permissions`. Serve un `settings.json` di esempio con allowlist e deny-list.
- **`sdlc-init`:** copia gli script nel progetto senza intestazione di versione né percorso di aggiornamento: copie
  e plugin divergono nel tempo.
- **`sdlc-spec`, `sdlc-plan`, `sdlc-review-diff`:** l'agente scrive il nome dell'approvatore senza sapere chi sia
  (rischio "Approvata da: utente").
- **`sdlc-tests-from-ac` + `sdlc-implement`:** stesso agente e spesso stessa sessione scrivono test e codice; lo spot
  check umano prima dell'implementazione è l'unico argine (vedi A2).
- **`sdlc-review-diff`:** review unica a fine feature su un diff grande; i problemi trovati non diventano task.
- **Punti di forza:** `sdlc-characterize` (rottura deliberata e ripristino), `sdlc-bugfix` (riproduzione obbligatoria,
  "da NON cambiare", 3 tentativi), STOP espliciti, `sdlc-next` che si basa sullo script e non sulla conversazione.

## D. Priorità

1. Approvazioni legate a PR o hash, non a un campo di testo (A1).
2. Risolvere il conflitto TDD/hook/loop; commit dei test rossi e controllo "test intoccati" (A2).
3. ID degli AC qualificati per spec (A3, B4).
4. Rendere gli hook affidabili: interprete risolto in modo portabile (`python3`/`py -3`) e fallimento visibile (B2).
5. Correggere B1, B3, B5-B8.
6. Permessi nativi dell'agente e sandbox al posto del guard a regex; file di permessi pronto per il loop (B10, C).
7. Audit delle dipendenze e scansione dei segreti in `verify` (A7).
8. Prova end-to-end su un greenfield e un brownfield reali prima di distribuire.

## CI su GitHub

Esito del workflow `.github/workflows/ci.yml` sul commit di import `0e748d2`
([run #1](https://github.com/jumping2000/sdd-playbook/actions/runs/39994902377)):

| Job | Esito | Note |
|---|---|---|
| `test (ubuntu-latest)` | **successo** | Coerente con la prova su WSL |
| `test (windows-latest)` | **fallito** nello step `python -m unittest discover -s tests -v` (exit 1, 25 s) | Il log richiede il login a GitHub e non è stato letto; l'esito è coerente con B1, riprodotto in locale |

Avviso del runner su entrambi i job: `actions/checkout@v4` e `actions/setup-python@v5` usano Node.js 20, deprecato.
Lo stesso vale per il template `skills/sdlc-init/references/ci-github-actions.yml`, quindi anche per la CI che
`sdlc-init` genera nei progetti: va aggiornato alle versioni correnti delle action (fissate per SHA nei contesti
regolati).

Conclusione per piattaforma: **Linux** è la piattaforma su cui il plugin funziona come dichiarato, a parte gli hook
che su un'installazione pulita non partono (B2). **Windows nativo**, indicato come supportato, non passa la propria
suite.

## Stato delle correzioni (0.5.0-0.13.0)

| Punto | Stato | Come |
|---|---|---|
| B1 | corretto | `reconfigure(encoding="utf-8")` in ogni script e hook; test con `PYTHONIOENCODING=cp1252` |
| B2 | corretto | `hooks/run.sh`: abilitazione controllata prima di cercare Python, poi `python3`/`python`/`py -3`; senza Python exit 1 visibile |
| B3 | corretto | `normalizza()` toglie solo il prefisso `./` |
| B4 | corretto (0.6.0) | citazioni attribuite alla spec: `SPEC-nnn/AC-nnn`, file dichiarato `# SPEC-nnn`, o citazione breve solo con una spec nel progetto; ambigue segnalate; righe `TODO`/`FIXME`/`XXX` ignorate. Resta vero che lo script legge testo e non controlla che i test passino |
| B5 | corretto | tutte le righe `Non modificare:`; percorso = prima parola o testo tra backtick; colonna "Dove" nel piano |
| B6 | corretto | segnaposto nelle task `T-nn` = errore; il template ora risulta "da compilare" |
| B7 | corretto | AC cercati per ID esatto nella sezione "Strategia di test" |
| B8 | corretto | impronta con `git diff HEAD` e contenuto dei non tracciati; `--timeout`; exit code riportato; baseline controllata |
| B11 | corretto | `.gitattributes` con LF |
| A2 | corretto | commit `Test-Lock` dei test rossi + controllo in `diff_scope.py`; fase rossa nell'hook `Stop` e in `loop.py`; `PROMPT.md` e skill aggiornati |
| A1 | corretto (0.7.0) | hash anti-deriva su spec e piano; approvazione = merge della PR di design su `main` protetto (`spec_lint.py --base`), con identità separata dell'agente; template CODEOWNERS e PR. La protezione del branch va configurata sulla piattaforma |
| A4 | corretto (0.7.0) | il loop chiude con successo solo se passano anche `trace_check.py` e `diff_scope.py` |
| B9 | corretto in parte (0.7.0) | contatore per sessione (`SDLC_STOP_MAX`); resta il `verify` completo a ogni fine turno, riducibile con `SDLC_VERIFY_ARGS` |
| A8 | corretto in gran parte (0.8.0) | ID data + slug (niente collisioni tra branch), stato `in-revisione` con catena di hash spec → piano → task, problemi della review come task `T-R`, `state.py` con più spec e associazione al branch. Resta da gestire il conflitto di merge di due modifiche alla stessa spec |
| A6 | corretto (0.9.0) | livelli S/M/L nella spec (inclusi nell'hash); `diff_scope.py` segnala il livello sottostimato (aree sensibili → L; dipendenze o più di 3 file di produzione → almeno M); S senza piano né `review.md`, L con ADR e revisione umana del diff. Interfacce pubbliche e formati dati restano a giudizio di chi approva |
| A5 | corretto in parte (0.9.0) | revisione umana del diff obbligatoria nel livello L (aree sensibili). Restano gli strumenti del subagent |
| A3 | corretto (0.10.0) | con `--junit` `trace_check.py` e `sync_check.py` contano solo i test eseguiti e passati nel report JUnit (obbligatorio nel livello L) |
| C (`sdlc-tests-from-ac` + `sdlc-implement`) | corretto (0.10.0) | nei livelli M e L i test bloccati si approvano prima dell'implementazione (`test approvati:`), controllato da `state.py`, `loop.py` e `sync_check.py` |
| A5 | corretto (0.9.0, 0.11.0) | revisione umana del diff nel livello L; subagent con soli strumenti di lettura; modello diverso possibile con `model:`. Resta un modello della stessa famiglia, salvo scelta dell'utente |
| A7 | corretto (0.11.0) | `secrets_check.py` in `verify` e nel loop; dipendenze solo nel piano o con ADR (`diff_scope.py`); prompt injection in playbook e `PROMPT.md`. L'audit delle dipendenze è documentato per stack, non incluso |
| B10 | corretto in gran parte (0.11.0) | guard per segmenti e parole, tutti i casi della tabella B bloccati, fail-closed. Resta aggirabile da comandi costruiti apposta: il controllo vero sono i permessi nativi |
| C (`sdlc-loop`, `sdlc-init`) | corretto (0.11.0) | `settings.loop.json` d'esempio; versione negli script copiati e procedura di aggiornamento |
| CI su GitHub (Node 20) | corretto (0.11.0) | `checkout@v6` e `setup-python@v6` nella CI e nel template |
| Review critica 0.9-0.11 (I1-I8) | corretto (0.11.1) | approvazioni dei test legate allo SHA `Test-Lock`; `AGENTS.md` e livello letti dal merge-base, rinomine contate; ADR nuovo per le dipendenze; attribuzione JUnit per percorso; file generati esclusi; `loop.py` usa `spec_lint`; permessi del loop senza scrittura sui controlli; controlli di processo nella CI delle PR. I7 (compatibilità con progetti 0.8.0) non applicabile: il plugin non è ancora in uso |
| Nome, lingua e agenti (0.13.0) | fatto (0.13.0) | plugin rinominato SDD Playbook (`sdd-*`, `SDD_*`), interamente in inglese, licenza MIT, supporto GitHub Copilot (plugin CLI, skill in `.github/skills/`, custom agent). Copilot non ancora provato; hook non portati su Copilot |
| A6 rivisto (0.20.0) | cambiato (0.20.0) | la prima prova reale ha mostrato il rischio opposto: troppa cerimonia per un compito piccolo. Il livello ora lo sceglie l'utente tra opzioni; `diff_scope.py` tiene come errori solo aree sensibili (→ L) e dipendenze (→ M), la dimensione nel livello S è un avviso e gli strumenti del processo non contano; `spec_lint.py` avvisa se gli AC sono troppi |
| A1 rivisto (0.20.0) | cambiato (0.20.0) | approvazioni selezionate tra opzioni e scritte da `approve.py`; profili: **team** tiene il merge della PR di design come approvazione, **solo** lascia che l'agente faccia avanzare `main` in fast-forward dopo un gate selezionato (nel profilo solo la prova è la selezione dell'utente, vedi architettura, limiti) |
| Prova end-to-end (D.8) | in parte fatta (0.17.0) | una prova di Claude Code su un piccolo greenfield (stack Docker): ha prodotto le modifiche della 0.20.0. Hook e loop non ancora eseguiti da un agente reale; la 0.20.0 non ancora provata su un progetto |
