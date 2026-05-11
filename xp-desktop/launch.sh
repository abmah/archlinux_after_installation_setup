#!/usr/bin/env bash
# xp-desktop watchdog -- relaunches desktop.py if it crashes or exits.
# exec-once'd by Hyprland; safe to run as a singleton (uses a pid lock).

set -u

DIR="$(cd "$(dirname "$0")" && pwd)"
LOCK="${XDG_RUNTIME_DIR:-/tmp}/xp-desktop.lock"
LOG="${XDG_RUNTIME_DIR:-/tmp}/xp-desktop.log"

# Singleton check via flock so a second invocation (e.g. accidental
# double exec-once) exits cleanly without spawning a competing loop.
exec 9>"$LOCK"
flock -n 9 || { echo "[xp-desktop] already running"; exit 0; }

trap 'kill %% 2>/dev/null; exit 0' INT TERM

while :; do
    # Print start banner so the log is easy to grep
    {
        echo "==== $(date '+%F %T') start ===="
    } >> "$LOG"
    python3 -u "$DIR/desktop.py" >>"$LOG" 2>&1 &
    pid=$!
    wait "$pid"
    rc=$?
    {
        echo "==== $(date '+%F %T') exited rc=$rc ===="
    } >> "$LOG"
    # If exit was clean (rc=0) and very fast, back off to avoid a tight
    # respawn loop on a config error.
    sleep 1
done
