#!/bin/sh

# Update wallpaper - run manually or via cron

# Export display and D-Bus session variables so the script works under cron,
# which runs without access to the graphical environment
export DISPLAY=:0
export XAUTHORITY=/home/makbuk/.Xauthority
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
CONTENT_DIR="content"

while [ "$#" -gt 0 ]; do
  case "$1" in
    -dir=*|--dir=*)
      CONTENT_DIR="${1#*=}"
      ;;
    -dir)
      shift
      if [ "$#" -gt 0 ]; then
        CONTENT_DIR="$1"
      fi
      ;;
  esac
  shift
done

# Generate and install
uv run --with pillow python "$SCRIPT_DIR/generate_wallpaper.py" --dir "$CONTENT_DIR"
