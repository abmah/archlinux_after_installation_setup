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
    echo "==== $(date '+%F %T') start desktop ====" >>"$LOG"
    python3 -u "$DIR/desktop.py" >>"$LOG" 2>&1 &
    pid=$!
    wait "$pid"
    rc=$?
    echo "==== $(date '+%F %T') desktop exited rc=$rc ====" >>"$LOG"
    sleep 1
done
