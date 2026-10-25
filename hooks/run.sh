#!/bin/sh
# Starts one of the plugin's Python hooks with the first available Python 3 interpreter.
#
# Usage (from hooks/hooks.json):  sh run.sh <script.py> <enabling variable>
#
# - If the variable is not 1 it exits 0 immediately: the hook is inactive and Python is not needed.
# - Tries python3, python, "py -3" in this order and uses the first one that really is Python 3.8+ (discards the
#   Microsoft Store aliases and Python 2). On a clean Ubuntu only python3 exists.
# - If it finds no Python 3 it exits 1 with a message: a visible but non-blocking error. An exit 2 here would block
#   every stop or every command without being able to read stop_hook_active.
# No external commands: works even with a minimal PATH.

script="$1"
enabling="$2"
eval "active=\${$enabling:-}"
[ "$active" = "1" ] || exit 0

# Folder of this file, also with a Windows path (C:\...\hooks\run.sh).
case "$0" in
    */* | *\\*) dir=${0%[\\/]*} ;;
    *) dir=. ;;
esac

for cand in python3 python "py -3"; do
    # $cand is deliberately unquoted: "py -3" is two words.
    if $cand -c "import sys; sys.exit(sys.version_info < (3, 8))" </dev/null >/dev/null 2>&1; then
        exec $cand "$dir/$script"
    fi
done

echo "sdd-playbook: Python 3 not found (tried python3, python, py -3): hook $script not run" >&2
exit 1
