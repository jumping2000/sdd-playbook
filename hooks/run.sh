#!/bin/sh
# Avvia un hook Python del plugin con il primo interprete Python 3 disponibile.
#
# Uso (da hooks/hooks.json):  sh run.sh <script.py> <variabile di abilitazione>
#
# - Se la variabile non vale 1 esce 0 subito: l'hook è inattivo e Python non serve.
# - Prova in ordine python3, python, "py -3" e usa il primo che è davvero Python 3.8+ (scarta gli
#   alias di Microsoft Store e Python 2). Su Ubuntu pulito esiste solo python3.
# - Se non trova Python 3 esce 1 con un messaggio: errore visibile ma non bloccante. Un exit 2 qui
#   bloccherebbe ogni stop o ogni comando senza poter leggere stop_hook_active.
# Nessun comando esterno: funziona anche con un PATH minimo.

script="$1"
abilitazione="$2"
eval "attivo=\${$abilitazione:-}"
[ "$attivo" = "1" ] || exit 0

# Cartella di questo file, anche con un percorso Windows (C:\...\hooks\run.sh).
case "$0" in
    */* | *\\*) dir=${0%[\\/]*} ;;
    *) dir=. ;;
esac

for cand in python3 python "py -3"; do
    # $cand non è tra virgolette di proposito: "py -3" sono due parole.
    if $cand -c "import sys; sys.exit(sys.version_info < (3, 8))" </dev/null >/dev/null 2>&1; then
        exec $cand "$dir/$script"
    fi
done

echo "sdlc-playbook: Python 3 non trovato (provati python3, python, py -3): hook $script non eseguito" >&2
exit 1
