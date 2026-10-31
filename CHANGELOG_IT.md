# Changelog

*English version: [CHANGELOG.md](CHANGELOG.md)*

Le voci precedenti alla 0.13.0 usano i nomi del loro tempo (`sdlc-*`, `SDLC_*`, campi in italiano).

## 0.17.0
Diagrammi Mermaid, nella documentazione del plugin e in quella delle applicazioni costruite con esso.
- **Diagrammi nelle applicazioni:** `plan.md`, le pagine d'area (`docs/system/<area>.md`) e la mappa della codebase
  hanno una sezione `## Diagrams` con cinque sottosezioni: flowchart, diagramma di sequenza, di stato, delle classi ed
  ER. Ognuna contiene un blocco ```` ```mermaid ```` del suo tipo oppure `- n/a: <motivo>`; il flowchart si applica
  sempre. Il piano disegna la modifica come progettata, la pagina d'area l'area come costruita (ridisegnata dal codice in
  `sdd-sync`), la mappa il sistema esistente. Nuova guida `sdd-plan/references/diagrams.md` (quando serve ogni
  diagramma, esempi, trappole di sintassi).
- **Controlli:** `spec_lint.py --plan` (sezione o sottosezione mancante: errore; non compilata, tipo sbagliato, blocco
  vuoto o flowchart `n/a`: warning prima dell'approvazione, errore dopo), `sync_check.py` sulla pagina d'area della
  feature, `docs_check.py` su ogni pagina di `docs/system/` e su ogni blocco Mermaid della documentazione (tipo di
  diagramma noto, non vuoto). La sintassi completa è lasciata all'anteprima del renderer.
- **Skill e revisore:** `sdd-plan`, `sdd-sync`, `sdd-map-codebase` e `sdd-docs` disegnano e controllano i diagrammi;
  `review_package.py` aggiunge al pacchetto i diagrammi del piano; il revisore (Claude Code e Copilot) segnala i
  diagrammi in disaccordo con il codice.
- **Correzione:** `docs_check.py` chiudeva un blocco di codice su qualunque recinzione di tre backtick, anche dentro un
  blocco ```` ```` ````; ora una recinzione chiude solo con lo stesso carattere e lunga almeno quanto l'apertura.
- **Documentazione del plugin:** flowchart del ciclo nel README; nel playbook il diagramma di stato della spec (§3.3) e
  la sequenza dei gate umani (§4); nell'architettura il diagramma delle classi degli script e l'ER del modello di
  tracciabilità; tutti verificati con il renderer Mermaid. Playbook, script, skill e architettura descrivono le nuove
  regole, nelle due lingue.

## 0.16.0
Idee dal marketplace AI Unified Process (S2, S3, S4, S5, S8 dell'analisi comparativa), adattate a SDD Playbook.
- **Skill portabili (S2):** nessuna skill legge i file di un'altra skill con `../`; li trova con una ricerca
  (`**/sdd-sync/references/area-template.md`), così le skill funzionano anche installate una per una o con un prefisso
  dell'host. Test di coerenza: nessun `../` nei file delle skill, ogni percorso citato esiste, `name` e `description`
  nei limiti del formato Agent Skills.
- **Diritti decisionali (S3):** nuova sezione `## Decision rights` nel template di `AGENTS.md` (`Decides alone`, `Asks
  first`, `Never`); `sdd-implement` e il prompt del loop la seguono, le decisioni registrate sono solo quelle di
  "Decides alone", una decisione che nessuna riga nomina si chiede prima, "Never" può solo crescere; il revisore
  controlla le decisioni rispetto alla sezione.
- **Domande aperte con `blocking` (S4):** `- <domanda> — blocking: yes|no — about: REQ-nnn, AC-nnn`. Una spec approvata
  può tenere domande non bloccanti (avviso); quelle senza marcatore contano come bloccanti; gli ID di `about:` devono
  esistere; `spec_lint.py --tasks` avvisa quando una task aperta copre un AC nominato da una domanda non bloccante, e
  l'implementazione si ferma su quella task.
- **Linguaggio (S5):** `spec_lint.py` avvisa sulle parole vaghe nei REQ e negli AC e, se esiste `docs/glossary.md`
  (nuovo template facoltativo in `sdd-init`), sui sinonimi della sua colonna "Avoid".
- **Test scritti dopo il codice (S8):** nuova sezione delle convenzioni dei test: l'oracolo è la spec, valori attesi
  dagli AC, un test in disaccordo con codice esterno alla task resta rosso e si segnala; fanno eccezione i test di
  caratterizzazione.
- **Distribuzione:** `version`, `author`, `license` e `repository` nella voce del plugin di
  `.claude-plugin/marketplace.json` (un test di coerenza tiene la versione uguale ai manifest); tag git `vX.Y.Z` dalla
  0.13.0 in poi, per fissare una versione; README con i comandi di installazione provati con Claude Code.
- `state.py` indica `sdd-spec` quando la task successiva copre un AC nominato da una domanda aperta non bloccante;
  `sdd-tasks` mette quegli AC in task proprie, in fondo; `sdd-sync` segnala le domande non bloccanti rimaste alla
  chiusura; `docs/glossary.md` non conta come fuori piano in `diff_scope.py`; `sdd-init` spiega come portare un progetto
  esistente a questi formati.
- Playbook §3.1, §3.3, §6, riferimenti di skill e script, architettura e guida rapida aggiornati; nuovi test.

## 0.15.0
Review per task, dal "subagent-driven development" di superpowers, senza un nuovo agente.
- **Quando:** obbligatoria nel livello L; nel livello M se `progress.md` riporta `- Task review: on` (chiesto all'inizio
  della feature); mai nel livello S.
- **Come:** i commit di implementazione portano il trailer `Task: T-nn`. Dopo ogni task (anche dopo il commit `Test-Lock`
  di una task di test, prima dell'approvazione umana) l'agente esegue il nuovo `review_package.py <spec-dir> T-nn`, che
  scrive in un solo file la riga della task, gli AC coperti, interfacce e review focus del piano, le decisioni della task e
  le patch dei suoi commit, e passa solo quel percorso a `sdd-reviewer` nella nuova **modalità task review**
  (`Task verdict: pass | fix needed`). I problemi alti e medi si correggono nella stessa task, al massimo 2 giri; l'esito
  va in `## Task reviews` di `progress.md`.
- **Controlli:** `spec_lint.task_reviews_missing()`; `state.py` rimanda a `sdd-implement` finché una task `T-nn` chiusa
  non ha `- T-nn: pass`; `sync_check.py` e i controlli finali di `loop.py` falliscono. Il prompt del loop esegue la
  review per task e annota "not reviewed" se non c'è un revisore disponibile.
- **Review finale:** `sdd-review-diff` passa al revisore il pacchetto dell'intero branch (`review_package.py <spec-dir>`)
  e, dopo le review per task, si concentra su integrazione, non-scope, copertura complessiva e decisioni.
- `sdd-init` copia 12 script; playbook §2.1, §4, §11, riferimenti di skill e script, architettura aggiornati; nuovo
  `tests/test_task_review.py`.

## 0.14.0
Pratiche prese dal plugin superpowers e adattate alla governance di SDD Playbook: spec e piani migliori, test migliori,
decisioni rese visibili. Testo e template, più un nuovo controllo in `spec_lint.py`.
- **Spec (`sdd-spec`):** l'agente legge codice e materiale prima di chiedere, riformula la richiesta, fa una domanda per
  messaggio (quella che cambierebbe di più ciò che si costruisce), propone 2-3 opzioni quando gli esiti per l'utente sono
  davvero diversi; nuova riga `- **Anti-goals:**` nel template della spec (`spec_lint.py` avvisa se manca).
- **Piano (`sdd-plan`):** interfacce tra i componenti (cosa produce / cosa consuma, nomi esatti); nuova sezione
  `## Review focus` con al massimo 5 classi di input che nessun AC esercita, ognuna con il suo test
  (`spec_lint.py --plan`: sezione obbligatoria, segnaposto come avviso prima dell'approvazione ed errore dopo; `- none` è
  valido); autoverifica contro la spec (copertura, nomi coerenti, proporzione). `diff_scope.py` legge anche la colonna
  "Where" del review focus come percorsi pianificati.
- **Qualità dei test (`sdd-tests-from-ac`):** tabella degli anti-pattern e checklist di approvazione nelle convenzioni dei
  test; l'agente revisore giudica i test con questi criteri.
- **Decisioni (rulings):** le decisioni prese nei margini di spec e piano vanno in `progress.md` (`## Rulings`: cosa,
  perché, costo se sbagliata); `sdd-implement` crea `progress.md` se manca; il revisore controlla che nessuna decisione
  cambi un requisito.
- **Ricevere una review:** i rilievi delle task `T-Rnn` si verificano prima sul codice; quelli sbagliati si annotano in
  `## Disputed review findings` invece di essere "corretti"; l'utente decide quali rilievi diventano task.
- **Debugging (`sdd-bugfix`):** nuovo `references/debugging.md` (risalita alla sorgente, un'ipotesi alla volta,
  bisezione di storia, input e suite di test, test intermittenti, stop dopo tre correzioni fallite).
- Playbook §3.3, §3.4, §6, §6.1, §7.2 aggiornati; nuovi test per anti-obiettivi, review focus e sezioni del prompt del
  loop.

## 0.13.0
Il plugin si chiama **SDD Playbook**, è interamente in inglese e supporta anche GitHub Copilot. Nessuna compatibilità con
i nomi precedenti: il plugin è in progettazione e non è mai stato usato su un progetto.
- **Nome:** identificativo `sdd-playbook` in tutti i manifest e nel marketplace (`sdd-playbook-marketplace`, owner
  `jumping2000`); skill `sdlc-*` → `sdd-*`, subagent `sdd-reviewer`, variabili d'ambiente `SDLC_*` → `SDD_*`
  (`SDD_ENFORCE_VERIFY`, `SDD_VERIFY_ARGS`, `SDD_STOP_MAX`, `SDD_GUARD`), intestazione degli script copiati
  `# sdd-playbook: <versione>`, cartella del contatore dell'hook `Stop` `sdd-playbook`.
- **Plugin in inglese:** skill, template, script (commenti, docstring, messaggi), hook, agente e test. I contratti sui
  file cambiano di conseguenza: `- Status:`, `- Level:`, `- Owner:`, `- Approved by / date:`, `- Based on spec:`,
  `- Based on plan:`, `verify:`, `covers:`, `expected: red`, `tests approved:`, `- Outcome:` (`compliant`,
  `compliant with reservations`, `non-compliant`), `- Decided by:`, `- Human diff review:`, `Last aligned`,
  `Linked specs`, stati dei bug `open`/`diagnosed`/`fixed`/`verified`, `- Do not modify:` e `- Sensitive areas:` in
  `AGENTS.md`, `in-revision`, output `VERIFY: GREEN`/`RED` e `NEXT:`. `docs/system/mappa.md` → `docs/system/map.md`.
- **GitHub Copilot:** `plugin.json` nella radice (formato Agent Plugins) per la Copilot CLI, con le skill e l'agente
  revisore; `sdd-init` chiede quali agenti usa il team e, per Copilot, copia le skill in `.github/skills/` e il custom
  agent `sdd-reviewer.agent.md` (strumenti `read` e `search`) in `.github/agents/`. Gli hook non sono portati: limite
  dichiarato. Nessun percorso Copilot è ancora stato provato.
- **Licenza MIT** (`LICENSE`), autore e repository nei manifest; README con i badge tipici di GitHub (versione, licenza,
  CI, Python, dipendenze, piattaforme, agenti, stato, lingue, ultimo commit, stelle).
- **Documentazione bilingue completa:** anche changelog e review hanno la versione inglese (senza suffisso) e italiana
  (`_IT`); il playbook si intitola "SDD Playbook" e descrive Copilot.
- CI del repository e template generato da `sdd-init`: runner Linux fissato a `ubuntu-24.04` invece di
  `ubuntu-latest`, che passa a Ubuntu 26 dal 2026-10-19.
- Test riscritti in inglese e rinominati (`test_consistency`, `test_levels`, `test_test_verification`,
  `test_security`, `test_review_fixes`); nuovi controlli: tre manifest con la stessa versione, badge della versione,
  licenza, agente Copilot in sola lettura, nessun testo italiano nei file del plugin, nessun nome `sdlc-`/`SDLC_` fuori
  dalla storia.

## 0.12.0
Documentazione completa in inglese e in italiano. Nessuna modifica al comportamento di skill e script.
- `README.md` in inglese e `README_IT.md` in italiano, con obiettivo del plugin e razionale dell'insieme di skill (errore
  tipico di un coding agent → risposta del plugin → dove).
- Nuova guida rapida, `docs/quick-guide.md` e `docs/quick-guide_IT.md`: preparazione, greenfield, brownfield, ciclo per
  feature, livelli, bug, loop, comandi più usati, problemi frequenti e percorso di prova.
- Ogni documento di `docs/` in due lingue, con la convenzione del README (inglese senza suffisso, italiano `_IT`):
  `architettura.md` → `architecture_IT.md` (nuovo `architecture.md`), `skills.md` → `skills_IT.md`, `scripts.md` →
  `scripts_IT.md`, playbook generato da due sorgenti (`playbook.src.md`, `playbook_IT.src.md`) con la stessa numerazione
  dei §.
- `tools/build_playbook.py` genera i due playbook; i test di coerenza controllano entrambe le lingue (stessi §, ogni
  skill e script documentati, ogni documento presente in due lingue, link validi).
- Allineati i documenti italiani ai contenuti della 0.11.1 (controlli di processo in CI, approvazione dei test con SHA,
  stato "in progettazione").

## 0.11.1
Correzioni dalla review critica sulle versioni 0.9.0-0.11.0. Il plugin è ancora in progettazione e mai usato su un
progetto: nessuna regola di compatibilità aggiunta per progetti esistenti.
- **Test approvati legati allo SHA:** il formato è `test approvati: <nome, aaaa-mm-gg, sha>`; `diff_scope.py` segnala uno
  SHA che non è il commit `Test-Lock` della task, o un nuovo commit `Test-Lock` dopo l'approvazione. Prima un secondo
  commit `Test-Lock` poteva indebolire i test approvati senza che nessuno se ne accorgesse.
- **Livello non aggirabile dal ramo:** `diff_scope.py` conta le rinomine con il percorso di partenza (`--no-renames`),
  legge `AGENTS.md` e il livello della spec dal merge-base, interpreta le voci di `AGENTS.md` come percorsi (backtick o
  prima parola) e segnala quelle che non lo sono. `loop.py` esegue anche `spec_lint.py` tra i controlli finali.
- **Dipendenze:** serve un ADR **nuovo** in `docs/adr/` (README e indici non contano); un lockfile vale se il piano
  elenca il suo manifest.
- **JUnit:** il caso si attribuisce al file con il percorso più coincidente (`tests.a.test_api` ↔ `tests/a/test_api.py`),
  non al solo nome; riconosciuta la convenzione Go `TestAC001_`; convenzione Java con l'ID nel nome del metodo;
  `--junit` senza valore è un errore.
- **File generati:** `__pycache__/`, `*.pyc` e `reports/` non contano né come progresso del loop né come file di
  produzione; gli script non scrivono più bytecode nel progetto; `loop.py` avvisa se il report non è ignorato.
- **`loop.py` usa `spec_lint`** per livello e approvazioni invece di regex duplicate (il livello nelle Revisioni non
  conta più); "atteso: rosso" senza distinzione di maiuscole, anche nell'hook `Stop`.
- **Permessi del loop:** `settings.loop.json` nega la scrittura di `scripts/`, `AGENTS.md`, `.github/`, spec, piano e
  review, e `git commit --amend`; consente anche `python3`.
- **CI generata:** step "Controlli di processo" sulle PR (`spec_lint --base`, `diff_scope`, `trace_check --junit`,
  `secrets_check`), il controllo che l'agente non può aggirare.
- Minori: percorsi non ASCII in `secrets_check.py`, `diff_scope.py` e `loop.py` (`core.quotePath=false`);
  `.secrets-ignore` e `.env.*.example`; guard su `git reset ... --hard`, `git -C . reset --hard`, `git clean -d -f`,
  `.env` dentro una parola, `find -delete`, senza falsi positivi su `git rm -r --cached` e `git check-ignore`, e
  fail-closed su `tool_input` malformato; `sync_check.py` accetta la cartella della spec dopo le opzioni.

## 0.11.0
Quinto e ultimo rilascio del piano sulle criticità di processo: sicurezza e manutenzione (A5, A7, B10, C).
- Nuovo script `secrets_check.py`: chiavi private, token con formato noto (AWS, GitHub, GitLab, Slack, Stripe, Google,
  Anthropic, OpenAI) e file `.env` nei file del ramo, o in tutto il repository con `--all`; non stampa mai il valore.
  È uno step `secrets` del template di `verify.py` e un controllo finale di `loop.py`.
- `diff_scope.py`: un manifest o lockfile modificato deve essere nel piano approvato o accompagnato da un ADR in
  `docs/adr/` (A7: "nuove dipendenze solo con ADR" ora è controllato).
- Guard `PreToolUse` (B10): analisi per segmenti e parole; blocca `rm -r -f`, `rm --recursive --force`, `+refspec`,
  `--force-with-lease`, `--delete`, `git clean -f`, `Remove-Item -Recurse`, `shutil.rmtree`, ogni riferimento a `.env`
  (anche `cp`, `Select-String`, maiuscole, stream NTFS), lo strumento Grep sui `.env`; con JSON illeggibile blocca.
- Subagent `sdlc-reviewer` con soli strumenti di lettura (A5): diff e output dei controlli li riceve nel messaggio;
  il contenuto del repository è un dato, non un'istruzione.
- Loop: permessi d'esempio `settings.loop.json` (allowlist e deny-list per Claude Code); `PROMPT.md` contro la prompt
  injection e le dipendenze non pianificate.
- Manutenzione: ogni script copiato porta la versione del plugin in seconda riga; `sdlc-init` spiega come aggiornare un
  progetto. Action della CI e del template aggiornate a `checkout@v6` e `setup-python@v6` (Node 24).
- Documentazione: contatore dell'hook `Stop` descritto nella sua cartella reale; playbook §1.2, §7.2, §8, §11.

## 0.10.0
Quarto rilascio del piano sulle criticità di processo: verifica dei test (A3 residuo, test scritti e implementati dallo
stesso agente).
- `trace_check.py --junit FILE|DIR`: con il report JUnit XML dei test eseguiti ogni AC deve avere almeno un caso
  eseguito e passato, e nessuno fallito; i saltati non contano. Attribuzione dei casi alla spec con le stesse regole
  delle citazioni (qualificate, o file dichiarato riconosciuto da `file` e `classname`). Report illeggibile: exit 2.
- `sync_check.py --junit`, obbligatorio nel livello L; `loop.py --junit` lo passa al controllo finale.
- Test approvati: nei livelli M e L la task di test "atteso: rosso" chiusa riporta `— test approvati: <nome, data>`,
  scritto dopo che l'umano ha riletto i test bloccati. `state.py` indica `sdlc-tests-from-ac` finché manca,
  `loop.py` si ferma (exit 1) e non riparte con un'approvazione in attesa (exit 2), `sync_check.py` lo richiede.
- Template di `verify.py` con `--junitxml=reports/junit.xml`; tabella dei reporter JUnit per stack; template di task,
  `PROMPT.md` e PR aggiornati; skill `sdlc-tests-from-ac`, `sdlc-implement`, `sdlc-loop`, `sdlc-review-diff`,
  `sdlc-sync`, `sdlc-init` aggiornate. Playbook: principio 5, §3.5, §4, §6, §7, §9.

## 0.9.0
Terzo rilascio del piano sulle criticità di processo: processo proporzionato al rischio (A6, e la parte di A5 sulle
aree sensibili).
- Livelli S, M, L (playbook §2.1): campo `- Livello:` nella spec, controllato da `spec_lint.py` (avviso se manca: vale
  M) e incluso nell'hash, così abbassarlo dopo l'approvazione la fa decadere. Gli hash delle spec senza il campo non
  cambiano.
- `diff_scope.py` segnala come errore il **livello sottostimato**: un file nelle nuove righe `- Aree sensibili:` di
  `AGENTS.md` richiede L; un manifest o lockfile delle dipendenze, o più di 3 file di produzione, richiedono almeno M.
  Nel livello S senza piano il confronto con il piano è saltato.
- Livello S: niente piano né `review.md`, `T-DOC` facoltativa, pagina d'area facoltativa (`state.py`, `spec_lint.py`,
  `sync_check.py`).
- Livello L: `review.md` richiede `- Revisione umana del diff:` (`state.py`, `sync_check.py`); ADR per le decisioni prese.
- Template di spec, review e `AGENTS.md` aggiornati; skill `sdlc-spec`, `sdlc-plan`, `sdlc-tasks`, `sdlc-implement`,
  `sdlc-review-diff`, `sdlc-sync`, `sdlc-next`, `sdlc-init`, `sdlc-loop` aggiornate. Playbook: principio 5 e nuovo §2.1.

## 0.8.0
Secondo rilascio del piano sulle criticità di processo: ID e ciclo di vita delle spec, lavoro in team (A8).
- ID della spec = data + slug (`docs/specs/2026-10-24-export-csv/`, titolo `# SPEC-2026-10-24-export-csv: ...`):
  `spec_lint.py` controlla che titolo e cartella coincidano e che la data sia valida. I vecchi `SPEC-NNN` restano
  validi. `trace_check.py` e `sync_check.py` riconoscono i nuovi ID (anche nella forma con `_` dei nomi di funzione) e
  li confrontano per ID esatto: `SPEC-2026-10-24-export` non vale per `SPEC-2026-10-24-export-csv`.
- Stato `in-revisione` per modificare una spec approvata, con voce obbligatoria in `## Revisioni`. Le task registrano
  `- Basato su piano:`; con `--plan` e `--tasks` insieme `spec_lint.py` le segnala se il piano è cambiato.
- Task `T-Rnn` dai problemi della review: controllate da `spec_lint.py` (`copre:` facoltativo), eseguite da
  `sdlc-implement` e dal loop; `state.py` chiede di crearle dopo un `non conforme` e di ripetere la review quando sono
  chiuse.
- `state.py`: passo successivo per ogni spec attiva; `PROSSIMO` per la spec di `--spec`, del branch corrente o l'unica
  attiva, altrimenti `scegli`.
- Hook `Stop`: il contatore dei blocchi sta in una cartella privata dell'utente (0700) e si apre senza seguire link
  simbolici (segnalazione della review automatica di sicurezza sulla 0.7.0).

## 0.7.0
Primo rilascio del piano sulle criticità di processo (`REVIEW.md`): fiducia nelle attestazioni (A1, A4, B9).
- Hash anti-deriva: spec approvata e piano approvato riportano `- Hash:` del proprio corpo; il piano riporta anche
  `- Basato su spec:`. `spec_lint.py` segnala hash mancanti o non corrispondenti, `--hash` lo calcola; `state.py`
  considera decadute le approvazioni non valide e lo dice nel motivo.
- Approvazione tramite merge: `spec_lint.py --base <ref>` richiede che spec e piano siano su `<ref>` e identici.
  Playbook §1.2: identità separata per l'agente (senza push, oppure bot o token senza diritti di merge), PR di design,
  protezione di `main` con review dei code owner. Nuovi template `CODEOWNERS.tmpl` e `pull_request_template.md`,
  creati da `sdlc-init`.
- `loop.py`: chiude con successo solo se passano anche `trace_check.py` e `diff_scope.py` (controlli finali).
- Hook `Stop`: blocca fino a `SDLC_STOP_MAX` volte di fila per sessione (default 3), poi lascia fermare l'agente con un
  avviso; il contatore si azzera quando `verify` torna verde.
- Skill `sdlc-spec`, `sdlc-plan`, `sdlc-tasks`, `sdlc-implement`, `sdlc-sync`, `sdlc-loop`, `sdlc-init` aggiornate.

## 0.6.0
Correzione del punto B4 della review (`REVIEW.md`): tracciabilità degli AC per spec.
- `trace_check.py` attribuisce ogni citazione a una spec: `SPEC-nnn/AC-nnn` (o `SPEC001_AC001`) vale per quella spec;
  `AC-nnn` vale per la spec dichiarata nel file (`# SPEC-nnn`), oppure, in un file non dichiarato, solo se il progetto
  ha una sola spec. Le citazioni ambigue non contano e sono segnalate. Prima i test di SPEC-001 coprivano anche SPEC-002.
- Le citazioni su righe `TODO`/`FIXME`/`XXX` non contano più come test.
- `sync_check.py` usa le stesse regole e, se mancano test, indica le citazioni ambigue.
- Convenzioni dei test e skill `sdlc-tests-from-ac` aggiornate agli ID qualificati.
- Compatibilità: un progetto con una sola spec continua a funzionare con le citazioni brevi.

## 0.5.0
Correzioni dalla review del 2026-10-23 (`REVIEW.md`, punti B1-B3, B5-B8, B11 e conflitto TDD/hook/loop di A2).
- Output UTF-8 in tutti gli script e negli hook: la suite ora passa anche su Windows con console cp1252 (B1).
- Hook avviati da `hooks/run.sh`: esce subito se l'hook non è abilitato, cerca `python3`, `python`, `py -3`; senza
  Python 3 l'errore è visibile e non bloccante. Prima, su Ubuntu pulito, gli hook non partivano senza avvisare (B2).
- `diff_scope.py`: le zone vietate con il punto iniziale (`.github/`) ora scattano (B3); lette tutte le righe
  `Non modificare:`; percorso del piano = prima parola o testo tra backtick; colonna "Dove" della strategia di test
  inclusa nel piano (B5).
- `spec_lint.py`: segnaposto `<...>` nelle task `T-nn` sono errori (B6); AC cercati per ID esatto nella sola sezione
  "Strategia di test" (B7).
- `loop.py`: stallo calcolato anche sul contenuto delle modifiche; `--timeout` per iterazione; codice di uscita
  dell'agente riportato; rifiuto di una baseline rossa salvo fase rossa o `--allow-red-baseline` (B8).
- TDD: i test rossi si committano con il trailer `Test-Lock: T-nn` e `diff_scope.py` segnala ogni modifica successiva;
  "fase rossa" riconosciuta da hook `Stop` e `loop.py`; `PROMPT.md` del loop e skill aggiornati (A2).
- `.gitattributes` del repository con LF (B11).

## 0.4.0
- Skill `sdlc-docs` (T-DOC) e `sdlc-sync` (T-SYNC); script `docs_check.py` e `sync_check.py`.
- `sync_check.py` richiede anche la decisione umana nella review.
- Documentazione completa del plugin (`docs/skills.md`, `docs/scripts.md`, `docs/architettura.md`) e playbook generato
  dai file del plugin (`tools/build_playbook.py`).
- Test di coerenza tra skill, script, playbook e documentazione; CI su Ubuntu e Windows.

## 0.3.0
- Skill `sdlc-review-diff` e `sdlc-loop`; subagent `sdlc-reviewer` (Claude Code).
- Script `diff_scope.py` e `loop.py` (tetto, rilevamento dello stallo, rifiuto di main/master, dry run, stop sulle sole task `T-nn`).
- Hook opzionali `Stop` (`SDLC_ENFORCE_VERIFY`) e `PreToolUse` (`SDLC_GUARD`).
- `state.py`: fasi review-diff, docs e sync.

## 0.2.0
- Skill `sdlc-map-codebase`, `sdlc-characterize`, `sdlc-tests-from-ac`, `sdlc-bugfix`.
- Script `scan_repo.py`, `trace_check.py`, `bug_lint.py`.
- `state.py`: rilevamento del brownfield (codice esistente senza mappa) e dei bug non verificati.

## 0.1.0
- Skill `sdlc-next`, `sdlc-init`, `sdlc-spec`, `sdlc-plan`, `sdlc-tasks`, `sdlc-implement`.
- Script `verify.py`, `spec_lint.py` (spec, piano, task), `state.py`.
- Manifest per Claude Code e Codex.
