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

# Copy Wofi config
echo "Copying Wofi config..."
mkdir -p "$BACKUP_DIR/wofi"
cp -r ~/.config/wofi/* "$BACKUP_DIR/wofi/"

# Copy btop theme
echo "Copying btop theme..."
mkdir -p "$BACKUP_DIR/btop"
cp ~/.config/btop/themes/minimal_white.theme "$BACKUP_DIR/btop/"

echo "All configs copied to $BACKUP_DIR ✅"
