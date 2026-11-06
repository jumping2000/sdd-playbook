# Guida rapida

*English version: [quick-guide.md](quick-guide.md)*

Come usare SDD Playbook su un progetto nuovo o esistente. Il metodo è nel
[playbook](playbook-ai-software-lifecycle_IT.md); qui solo i passi.

## In una frase

Tu decidi **cosa** costruire e **se unirlo**, sempre selezionando un'opzione; l'agente scrive spec, piano, test e
codice; gli script controllano che ogni passo sia stato fatto davvero. In qualsiasi momento `sdd-next` (o
`python scripts/state.py`) ti dice il passo successivo.

## Prima di iniziare

| Cosa | Perché |
|---|---|
| Installa il plugin (README, "Installazione") | Rende disponibili le 7 skill |
| Python 3.8+ e git sulla macchina, qualunque sia il linguaggio del progetto | Gli script del playbook sono Python con sola libreria standard; `sdd-start` lo controlla per primo e indica come installarlo |
| Facoltativo: un remote GitHub | Una PR per task, e una CI che esegue `verify` su ogni PR |

Le skill si richiamano chiedendo all'agente, per esempio *"usa sdd-start per un export CSV dei report"*.

## Una feature, dall'idea a `main`

| # | Skill | Cosa ottieni | La tua decisione (opzioni) |
|---|---|---|---|
| 1 | `sdd-start` | La prima volta: script in `scripts/`, `AGENTS.md`, `verify.py` adattato ai tuoi comandi. Poi: domande a giri di opzioni e `docs/specs/<data-slug>/spec.md` con requisiti, criteri di accettazione, non-scope, anti-goal | `Confirm the spec` |
| 2 | `sdd-plan` | `plan.md`: approccio, interfacce, flowchart, da 3 a 8 task verticali (ognuno con AC, file, dipendenze e comando di verifica); la PR di design | `Confirm the plan`, poi `Merge into main` per la PR di design |
| 3 | `sdd-task` (uno per task) | Branch, test dagli AC del task bloccati da un commit `Test-Lock`, il codice, `verify` verde, la documentazione che cambia, una PR rivista da `sdd-reviewer` | `Merge into main`, `Change it` o `Leave it open` |
| — | `sdd-parallel` (quando proposto) | I task indipendenti con file diversi girano insieme, un worktree e una PR ciascuno | `Run them in parallel`, poi ogni merge |
| 4 | l'ultimo `sdd-task` | Anche la pagina d'area in `docs/system/` con i cinque diagrammi dal codice finale, e la spec `implemented` | `Merge into main` |

Prima di ogni domanda di merge vedi gli AC coperti, gli esiti dei controlli, il verdetto del revisore, lo stato della
CI e i **file sensibili** (`SENSITIVE` in `diff_scope.py`): leggi il loro diff prima di unire. Un task il cui
predecessore non è unito non parte. Per cambiare spec o piano dopo la PR di design: una nuova PR di spec/piano, mai una
modifica dentro un task.

## Codice esistente

1. **`sdd-start`** inizializza il progetto; con codice esistente propone prima la mappa.
2. **`sdd-map`** (in sola lettura sul codice): inventario, comandi reali provati, **baseline** (se è rossa si dichiara,
   non è colpa tua), `docs/system/map.md` con i diagrammi, e le righe `Do not modify` e `Sensitive areas` per
   `AGENTS.md`:
   ```
   - Do not modify: `migrations/applied/`, `src/generated/`
   - Sensitive areas: `src/auth/`, `src/payments/`
   ```
   Le zone "Do not modify" non si toccano mai (errore); le "Sensitive areas" sono segnalate in ogni PR che le tocca.
3. **`sdd-map`, parte 2**, sull'area da modificare: test di caratterizzazione che fissano il comportamento attuale e di
   cui si prova che possono fallire.
4. Il flusso della feature qui sopra, con una spec che descrive **solo la modifica**.

## Bug

`sdd-bugfix`: riproduzione (senza riproduzione niente correzione), comportamento atteso e **comportamento che NON deve
cambiare** (li confermi entrambi), test rosso bloccato, causa radice verificata, correzione minima, PR e domanda di
merge. Un bug banale (causa evidente, una riga) richiede solo un test rosso, la correzione e `verify`.

## Comandi che userai di più

| Comando | Quando |
|---|---|
| `python scripts/state.py` | Dove sono, qual è il passo successivo, quali task sono pronti |
| `python scripts/verify.py` | Formattazione, lint, tipi, test e segreti: la definizione di "fatto" |
| `python scripts/spec_lint.py <spec> --plan <plan>` | Spec e piano validi, task ben formati |
| `python scripts/trace_check.py <spec> --task T-01 --junit reports/junit.xml` | Gli AC del task hanno test eseguiti e passati |
| `python scripts/diff_scope.py docs/specs/<id> --task T-01` | Zone vietate, test bloccati, file fuori dal task, file sensibili |

## Hook di sicurezza (solo Claude Code, facoltativi)

Non disponibili in Codex e GitHub Copilot: lì la rete di sicurezza sono la CI e i permessi dell'agente.

| Variabile | Effetto |
|---|---|
| `SDD_ENFORCE_VERIFY=1` | L'agente non può dichiarare finito con `verify` rosso (salvo subito dopo un commit `Test-Lock`) |
| `SDD_GUARD=1` | Blocca push forzati, `reset --hard`, cancellazioni ricorsive, scarica-ed-esegui, lettura di `.env` |

Sono una rete di sicurezza, non un sandbox.

## Problemi comuni

| Sintomo | Cosa fare |
|---|---|
| `state.py` dice `choose` | Più spec attive: lavora sul branch il cui nome contiene la spec, oppure usa `--spec <id>` |
| `state.py`: "spec and plan not on main yet" | Apri e unisci la PR di design: è l'approvazione |
| `state.py`: "no task ready" | Unisci le PR aperte: i task successivi dipendono da esse |
| `spec_lint.py`: "blocking open questions" | Rispondi, oppure marca `blocking: no` quelle la cui risposta non cambierebbe un REQ o un AC |
| `spec_lint.py`: "N tasks (usually at most 8)" | Dividi la feature in due spec, oppure unisci i task in fette verticali |
| `diff_scope.py`: "locked test changed after locking" | I test sono cambiati dopo il commit `Test-Lock`: annulla la modifica, o correggi il test in un nuovo commit `Test-Lock` spiegato nella PR |
| `diff_scope.py`: "file outside the task" | È voluto? Dillo nella PR. Altrimenti sposta la modifica in un task suo |
| `verify` rosso subito dopo i test | È la **fase rossa**, attesa finché l'implementazione non è fatta |
| L'agente si è fermato su un task dopo 3 tentativi | Scegli `Revise the spec`, `Revise the plan`, `Try another approach` o `Stop here`; una revisione passa da una PR di revisione |

## Percorso di prova consigliato

1. **Greenfield giocattolo:** una feature piccola (lo stack Docker di Langfuse provato con la 0.17.0 è un buon banco
   di prova), tutto in modalità interattiva, una PR per task.
2. **Due task indipendenti** con `sdd-parallel`.
3. **Brownfield:** un repository reale ma non critico, un'area mappata e caratterizzata, una modifica.

Annota ogni punto in cui l'agente fraintende una skill: sono le correzioni più preziose per il plugin.
