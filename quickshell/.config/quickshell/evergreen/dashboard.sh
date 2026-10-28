#!/bin/sh
# Serialize startup/toggle requests; a named Quickshell instance owns the panel.
set -eu
mode=${1:-start}
case "$mode" in start|toggle) ;; *) echo 'Usage: dashboard.sh [start|toggle]' >&2; exit 2 ;; esac
command -v qs >/dev/null || { echo 'Install quickshell to enable the dashboard.' >&2; exit 1; }
: "${XDG_RUNTIME_DIR:?No desktop runtime directory}"
exec 9>"$XDG_RUNTIME_DIR/evergreen-dashboard.lock"
flock -x 9
if qs -c evergreen ipc call dashboard visible >/dev/null 2>&1; then
    if [ "$mode" = toggle ]; then qs -c evergreen ipc call dashboard toggle; fi
    exit 0
fi
# --no-duplicate covers the small gap before the IPC handler is registered.
qs -c evergreen --no-duplicate >"$XDG_RUNTIME_DIR/evergreen-dashboard.log" 2>&1 9>&- &
