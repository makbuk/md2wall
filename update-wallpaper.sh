#!/bin/bash
# Обновить обои — запускай вручную или через cron

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Установить Pillow если нет
python3 -c "import PIL" 2>/dev/null || pip3 install pillow --break-system-packages

# Сгенерировать и установить
python3 "$SCRIPT_DIR/generate_wallpaper.py"
