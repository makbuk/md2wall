#!/bin/bash

# Update wallpaper - run manually or via cron

# Export display and D-Bus session variables so the script works under cron,
# which runs without access to the graphical environment
export DISPLAY=:0
export XAUTHORITY=/home/makbuk/.Xauthority
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install Pillow if not present
python3 -c "import PIL" 2>/dev/null || pip3 install pillow --break-system-packages

# Generate and install
python3 "$SCRIPT_DIR/generate_wallpaper.py"
