#!/usr/bin/env bash
# Waybar custom/bluetooth provider — outputs JSON for the bar pill.

powered=$(bluetoothctl show 2>/dev/null | awk -F': ' '/Powered:/ {print $2}')

if [ "$powered" != "yes" ]; then
    printf '{"text":"","tooltip":"Bluetooth off\\nClick to open Bluetooth Devices","class":"off","alt":"off"}\n'
    exit 0
fi

# Build list of connected devices
connected_names=$(
    bluetoothctl devices Connected 2>/dev/null \
        | sed -E 's/^Device [0-9A-F:]+ //'
)

if [ -n "$connected_names" ]; then
    n=$(printf '%s\n' "$connected_names" | wc -l)
    first=$(printf '%s' "$connected_names" | head -n1)
    if [ "$n" -gt 1 ]; then
        text="$first +$((n-1))"
    else
        text="$first"
    fi
    tooltip="Connected:\n${connected_names}\n\nClick: Bluetooth Devices"
    printf '{"text":" %s","tooltip":"%s","class":"connected","alt":"connected"}\n' \
        "$text" "${tooltip//$'\n'/\\n}"
else
    printf '{"text":"","tooltip":"Bluetooth on, no connections\\nClick: Bluetooth Devices","class":"on","alt":"on"}\n'
fi
