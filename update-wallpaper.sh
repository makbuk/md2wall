#!/bin/bash

# Update wallpaper - run manually or via cron
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install Pillow if not present
python3 -c "import PIL" 2>/dev/null || pip3 install pillow --break-system-packages

# Generate and install
python3 "$SCRIPT_DIR/generate_wallpaper.py"
