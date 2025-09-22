#!/bin/bash

# Wallpaper cycling script for hyprpaper
# Cycles through wallpapers in ~/wallpapers/ every minute

WALLPAPER_DIR="$HOME/wallpapers"
MONITOR="eDP-1"  # Change this to your monitor name if different
INTERVAL=60      # Time in seconds between wallpaper changes (60 = 1 minute)

# Check if wallpaper directory exists
if [ ! -d "$WALLPAPER_DIR" ]; then
    echo "Error: Wallpaper directory '$WALLPAPER_DIR' does not exist!"
    exit 1
fi

# Check if hyprpaper is running
if ! pgrep -x "hyprpaper" > /dev/null; then
    echo "Error: hyprpaper is not running!"
    echo "Please start hyprpaper first."
    exit 1
fi

# Get list of image files (jpg, jpeg, png, webp)
mapfile -t wallpapers < <(find "$WALLPAPER_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) | sort)

# Check if we found any wallpapers
if [ ${#wallpapers[@]} -eq 0 ]; then
    echo "Error: No wallpaper files found in '$WALLPAPER_DIR'!"
    echo "Supported formats: jpg, jpeg, png, webp"
    exit 1
fi

echo "Found ${#wallpapers[@]} wallpapers in '$WALLPAPER_DIR'"
echo "Cycling every $INTERVAL seconds on monitor '$MONITOR'"
echo "Press Ctrl+C to stop"
echo

# Function to set wallpaper
set_wallpaper() {
    local wallpaper="$1"
    echo "Setting wallpaper: $(basename "$wallpaper")"
    
    # Preload the wallpaper
    hyprctl hyprpaper preload "$wallpaper" 2>/dev/null
    
    # Set the wallpaper
    hyprctl hyprpaper wallpaper "$MONITOR,$wallpaper" 2>/dev/null
    
    # Optional: Unload previous wallpapers to save memory (uncomment if needed)
    # hyprctl hyprpaper unload all 2>/dev/null
}

# Trap Ctrl+C to exit gracefully
trap 'echo -e "\nExiting wallpaper cycler..."; exit 0' INT

# Main loop
index=0
while true; do
    # Set current wallpaper
    set_wallpaper "${wallpapers[$index]}"
    
    # Move to next wallpaper (loop back to start if at end)
    index=$(( (index + 1) % ${#wallpapers[@]} ))
    
    # Wait for specified interval
    sleep "$INTERVAL"
done
