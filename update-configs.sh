#!/bin/bash
# update-configs.sh
# Script to backup configs to ~/setup/

# Set the base backup directory
BACKUP_DIR=~/setup

# Copy Hyprland config
echo "Copying Hyprland config..."
mkdir -p "$BACKUP_DIR/hypr"
cp -r ~/.config/hypr/* "$BACKUP_DIR/hypr/"

# Copy Kitty config
echo "Copying Kitty config..."
mkdir -p "$BACKUP_DIR/kitty"
cp -r ~/.config/kitty/* "$BACKUP_DIR/kitty/"

# Copy Waybar config
echo "Copying Waybar config..."
mkdir -p "$BACKUP_DIR/waybar"
cp -r ~/.config/waybar/* "$BACKUP_DIR/waybar/"

echo "All configs copied to $BACKUP_DIR ✅"

