# Guida rapida

*English version: [quick-guide.md](quick-guide.md)*

Come usare `sdd-playbook` su un progetto nuovo (greenfield) o esistente (brownfield). Questa guida dice **cosa fare e in
che ordine**; il perché e i dettagli stanno nel [playbook](playbook-ai-software-lifecycle_IT.md), le singole skill nel
[riferimento delle skill](skills_IT.md), gli script nel [riferimento degli script](scripts_IT.md).

> Il plugin è **in progettazione** e non è ancora stato usato su un progetto reale. Prima di affidargli un progetto
> importante, segui il percorso di prova in fondo a questa pagina.
>
> Skill, template e messaggi degli script sono in inglese. I nomi dei campi come `- Status:`, `- Level:`,
> `tests approved:` o `expected: red` fanno parte dei contratti sui file letti dagli script: lasciali così.

## In una frase

Tu decidi **cosa** costruire e approvi i punti chiave, sempre **selezionando un'opzione** (`Approve as <name>`,
`Request changes`, `Stop here`); l'agente scrive spec, piano, test e codice, registra le tue approvazioni con
`approve.py` e, nel profilo solo, fa i passi git; gli script controllano che ogni passo sia stato fatto davvero. In qualsiasi momento `sdd-next` (o `python scripts/state.py`) ti dice dove sei e
qual è la prossima skill.

## Prima di iniziare (una volta)

| Cosa | Perché |
|---|---|
| Installa il plugin: `claude --plugin-dir <percorso>/sdd-playbook` per provarlo (Codex e GitHub Copilot: vedi il README) | Rende disponibili le 14 skill |
| Python 3 e git sulla macchina | Gli script sono Python con sola libreria standard |
| Scegli il **profilo**: `solo` (una persona, anche senza remote) o `team` | `sdd-init` lo chiede come opzione. Solo: l'agente fa branch, commit e fast-forward di `main` dopo l'approvazione che selezioni; niente da configurare |
| Solo team: un'**identità separata** per l'agente e, sulla piattaforma, `main` protetto con PR, CI e review dei code owner obbligatorie | Il merge su `main` protetto è l'unico controllo che l'agente non può aggirare. Il plugin crea i template, le regole le imposti tu |

Le skill si richiamano chiedendo all'agente di usarle, per esempio *"usa sdd-spec per una funzione di export CSV"*.

## Greenfield (repository vuoto)

1. **`sdd-init`**. L'agente rileva l'ambiente e ti chiede, in un giro di opzioni, profilo, nomi degli approvatori,
   stack, comandi reali di format/lint/tipi/test e se qualcuno usa Windows. Copia gli script in `scripts/`, crea
   `AGENTS.md`, `CLAUDE.md`, `docs/`, `.gitignore`, `.gitattributes` e il task VS Code; nel profilo team anche la CI,
   `CODEOWNERS` e il template della PR. **Gate:** approvi principi, stack e step di `verify`.
2. Solo nel profilo team: configura sulla piattaforma la protezione di `main` (vedi sopra).
3. Per ogni funzionalità, il **ciclo per feature** descritto sotto.

## Brownfield (codice esistente)

1. **`sdd-init`**, come sopra. Se trova codice, il passo successivo è la mappa.
2. **`sdd-map-codebase`** (sola lettura). Parte dall'inventario di `scan_repo.py`, legge il codice, scrive
   `docs/system/map.md` con comandi reali provati e la **baseline**: quali test passano già e quali no. Un rosso che
   c'era prima non è colpa dell'agente. **Gate:** verifichi la mappa a campione.
3. **Completa `AGENTS.md`** con due righe che gli script fanno rispettare, con i percorsi tra backtick, e rivedi i suoi
   **Decision rights** (cosa l'agente decide da solo, chiede prima, non fa mai):
   ```
   - Do not modify: `migrations/applied/`, `src/generated/`
   - Sensitive areas: `src/auth/`, `src/payments/`
   ```
   Le zone "Do not modify" non si toccano mai; le "Sensitive areas" obbligano al livello L.
4. **`sdd-characterize`** sull'area che vuoi modificare: test che fissano il comportamento attuale (anche se sbagliato)
   e la prova che sanno fallire. **Gate:** spot check.
5. Il **ciclo per feature**, con una spec che descrive **solo la modifica**, non il sistema intero.

Ripeti i passi 2-4 un'area alla volta, solo dove stai per intervenire: non serve documentare tutto in anticipo.

## Ciclo per feature (greenfield e brownfield)

| # | Skill | Cosa ottieni | Il tuo ruolo |
|---|---|---|---|
| 1 | `sdd-spec` | `docs/specs/<data-slug>/spec.md`: requisiti, acceptance criteria, non-scope, **livello** | Rispondi ai giri di opzioni (livello compreso), poi **selezioni** `Approve as <name>` |
| 2 | `sdd-plan` (non nel livello S) | `plan.md`: file da toccare, diagrammi Mermaid (flowchart, sequenza, stato, classi, ER), strategia di test, dipendenze, rischi | **Approvi** |
| 3 | `sdd-tasks` | `tasks.md`: task piccole, ognuna con un comando di verifica | Controllo rapido |
| — | **Design su `main`** | spec, piano e task approvati | Solo: l'agente fa avanzare `main` in fast-forward. Team: **il tuo merge della PR di design è l'approvazione** (l'agente può aprirla o farne il merge se lo selezioni) |
| 4 | `sdd-tests-from-ac` (la richiama `sdd-implement`) | Test rossi scritti dagli AC, bloccati con un commit `Test-Lock` | **Rileggi i test** e selezioni l'approvazione: `approve.py` scrive `tests approved: <name, date, sha>` (livelli M e L) |
| 5 | `sdd-implement`, oppure `sdd-loop` per molte task indipendenti | Il codice che fa passare i test senza modificarli | — |
| 6 | `sdd-review-diff` (non nel livello S) | `review.md`, da un revisore a contesto fresco che prova a confutare | **Decidi**; nel livello L rileggi anche il diff |
| 7 | `sdd-docs` | README, documentazione API, esempi eseguiti | Review |
| 8 | `sdd-sync` | Spec `implemented`, pagina d'area in `docs/system/` con i diagrammi ridisegnati dal codice | Review; poi solo: fast-forward di `main`; team: **PR di implementazione** |

Se la review è `non-compliant`, i problemi diventano task `T-R01`, `T-R02`… che si implementano come le altre; poi la
review si ripete. `sdd-next` te lo indica.

### Scegliere il livello

| Livello | Quando | Cosa cambia |
|---|---|---|
| **S** | Una modifica piccola: circa 3 file di produzione (strumenti del processo esclusi), nessuna area sensibile, nessuna dipendenza, nessuna interfaccia pubblica; di solito 3-6 AC | Niente piano né `review.md`; la review è quella della PR |
| **M** | Il caso normale | Il ciclo completo; a scelta una review di ogni task (`- Task review: on` in `progress.md`) |
| **L** | Aree sensibili, interfacce pubbliche, migrazioni di dati | Più un ADR per le decisioni, una review di ogni task e la tua **rilettura del diff** |

Scegli il livello tra le opzioni che l'agente propone (consigliato il più basso consentito dai criteri vincolanti); si
approva con la spec e fa parte del suo hash. `diff_scope.py` segnala un errore solo per un'area sensibile (serve L) o una
modifica alle dipendenze (serve M); più file del solito nel livello S sono un avviso. Non alzare il livello "per
sicurezza".

## Bug

`sdd-bugfix`, in parallelo al ciclo: riproduzione (se non si riproduce, l'agente si ferma), comportamento atteso e
**comportamento da NON cambiare** (lo confermi tu), test rosso, diagnosi, fix minimo, non-regressione. Per un bug banale
(causa evidente, una riga) bastano test rosso, fix e `verify`.

## Il loop autonomo (facoltativo)

`sdd-loop` prepara tutto ma **non lancia nulla**: lo lanci tu, in un terminale separato e in un ambiente isolato
(container senza rete, nessun segreto). Concordi tetto di iterazioni, stallo e timeout; l'agente fa il dry run e ti mostra
il comando:

```
python scripts/loop.py docs/specs/<id> --max 15 --stall 3 --timeout 1800 --junit reports/junit.xml
```

Il loop si ferma da solo dopo ogni task di test (livelli M e L) perché tu possa approvare i test, e chiude con successo
solo se passano `verify` e i controlli finali (`spec_lint`, `trace_check`, `diff_scope`, `secrets_check`). Usa il file di
permessi d'esempio `skills/sdd-loop/references/settings.loop.json`.

## I comandi che userai di più

| Comando | Quando |
|---|---|
| `python scripts/state.py` | Dove sono, qual è il prossimo passo |
| `python scripts/verify.py` | Format, lint, tipi, test e segreti: il criterio di "fatto" |
| `python scripts/spec_lint.py <spec> --plan <plan> --tasks <tasks> --base main` | Spec, piano e task validi e già su `main` (team: PR di design unita; solo: fast-forward) |
| `python scripts/approve.py spec <spec> --by "<nome>" --commit` | Registra l'approvazione che hai selezionato (anche `plan`, `tasks`, `tests`, `review`): nome, data e hash, controllati dal lint |
| `python scripts/trace_check.py <spec> --junit reports/junit.xml` | Ogni AC ha un test eseguito e passato |
| `python scripts/diff_scope.py docs/specs/<id>` | Zone vietate, test bloccati, livello, dipendenze, file fuori piano |
| `python scripts/sync_check.py docs/specs/<id> --junit reports/junit.xml` | Feature chiusa e riconciliata |

## Hook di sicurezza (solo Claude Code, facoltativi)

Non disponibili in Codex e GitHub Copilot: lì la rete di sicurezza è la CI, la protezione dei branch e i permessi
dell'agente.

| Variabile | Effetto |
|---|---|
| `SDD_ENFORCE_VERIFY=1` | L'agente non può dichiarare finito il lavoro con `verify` rosso (salvo fase rossa) |
| `SDD_GUARD=1` | Blocca push forzati, cancellazioni ricorsive, `reset --hard`, accesso a `.env` |

Sono una rete di sicurezza, non un sandbox: la difesa vera sono permessi, isolamento e CI.

## Problemi frequenti

| Sintomo | Cosa fare |
|---|---|
| `state.py` dice `choose` | Più spec attive: lavora sul branch che contiene il nome della spec, o usa `--spec <id>` |
| Un'approvazione "decade" | Il contenuto è cambiato dopo l'ok (l'hash non corrisponde): seleziona di nuovo l'approvazione; `approve.py` riscrive l'hash |
| `state.py`: "design approved but not on main yet" (solo) | Lascia che l'agente faccia avanzare `main`: `git fetch . HEAD:main` |
| `approve.py`: "APPROVAL: NOT RECORDED" | Il documento non passerebbe il lint (per esempio una domanda aperta bloccante): correggi ciò che elenca e seleziona di nuovo l'approvazione |
| `spec_lint.py`: "blocking open questions" | Rispondi, oppure marca `blocking: no` quelle la cui risposta non cambierebbe un REQ o un AC su cui si basa il piano |
| `diff_scope.py`: "level underestimated" | Un'area sensibile (serve L) o una modifica alle dipendenze (serve M) sotto il livello dichiarato: alzalo nella spec e seleziona di nuovo l'approvazione |
| `diff_scope.py`: "[WARN] level S with N production files" | Solo un avviso: tieni S se la modifica resta piccola, altrimenti alza il livello |
| `diff_scope.py`: "dependencies changed without plan or ADR" | Elenca il manifest nel piano approvato o aggiungi un ADR in `docs/adr/` |
| `diff_scope.py`: "tests approved" | I test sono cambiati dopo la tua approvazione: rileggili e approva il nuovo commit `Test-Lock` |
| `verify` rosso dopo i test | È la **fase rossa**, attesa finché la task di implementazione non è fatta |
| Il loop si ferma subito | Leggi il motivo: tetto, stallo o test da approvare. Non rilanciarlo alla cieca: rivedi spec e piano |

## Percorso di prova consigliato

1. **Greenfield giocattolo, profilo solo:** una feature di livello S, poi una di livello M, tutto in modalità
   interattiva (lo stack Langfuse provato con la 0.17.0 è un buon banco di prova per il livello S).
2. **Brownfield:** un repository reale ma non critico, un'area mappata e caratterizzata, una modifica di livello M.
3. **Il loop per ultimo**, in un container senza rete e con `settings.loop.json`.

Annota ogni punto in cui l'agente interpreta male una skill: sono le correzioni più preziose per il plugin.
