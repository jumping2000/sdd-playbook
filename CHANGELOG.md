# Changelog

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
