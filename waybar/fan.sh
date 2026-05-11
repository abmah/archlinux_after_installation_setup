#!/usr/bin/env bash
# Waybar custom/fan source. Returns JSON with a 4-frame animated icon.
# Frame advances on every poll; with interval=1 in waybar, that's 1 fps.

rpm=$(cat /sys/class/hwmon/hwmon*/fan1_input 2>/dev/null | head -1)
rpm=${rpm:-0}
mode=$(awk '/^level:/ {print $2}' /proc/acpi/ibm/fan 2>/dev/null)
mode_user=$(cat /tmp/fan-mode-current 2>/dev/null || echo auto)
fan_control=$(cat /sys/module/thinkpad_acpi/parameters/fan_control 2>/dev/null)

# Animation: ASCII fan-blade spinner. Step (frames advanced per poll)
# scales with RPM so the spinner visually matches actual fan speed.
# With waybar interval=0.5: 0 RPM = static, ~1k = slow, ~2.5k = medium, 3.5k+ = fast.
if   [ "$rpm" -eq 0 ];     then step=0
elif [ "$rpm" -lt 1500 ];  then step=1
elif [ "$rpm" -lt 3000 ];  then step=2
else                            step=3
fi
frame_file=/tmp/fan-frame
n=$(cat "$frame_file" 2>/dev/null || echo 0)
n=$(( (n + step) % 4 ))
echo "$n" > "$frame_file"
frames=("|" "/" "-" "\\")
spin=${frames[$n]}

# Static fan icon
fan_icon=""

if [ "$rpm" -gt 0 ]; then
    text="$spin $fan_icon ${rpm}"
    cls="spinning"
else
    text="○ $fan_icon idle"
    cls="idle"
fi

[ "$mode_user" = "max" ] && cls="max"
[ "$fan_control" = "N" ] && warning="\nFan control disabled (reboot to enable)"

tooltip="Fan: ${rpm} RPM\nKernel mode: ${mode}\nUser mode: ${mode_user}${warning}\nClick: fan menu"

# Waybar JSON output
printf '{"text":"%s","class":"%s","tooltip":"%s"}\n' "$text" "$cls" "$tooltip"
