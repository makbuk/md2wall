# md2wall

![preview](desk-os-wallpaper.png)

KDE wallpaper generator from Markdown files. Reads columns from `content/`, renders a 1920×1080 PNG and sets it as wallpaper via the KDE API.

## Installation & usage

```bash
git clone https://github.com/makbuk/md2wall
cd md2wall
bash update-wallpaper.sh
```

Pillow is installed automatically on the first run.

Use a different content directory:

```bash
bash update-wallpaper.sh --dir=my-content
```

## Project structure

```
md2wall/
├── generate_wallpaper.py   — main script
├── settings.py.example     — default settings (copy to settings.py to customize)
├── settings.py             — personal settings, git-ignored
├── update-wallpaper.sh     — run manually or via cron
└── content/
    ├── header.md           — top bar text
    ├── footer.md           — bottom bar text
    ├── images/             — images used in columns
    ├── column1.md          — column 1
    ├── column2.md          — column 2
    └── ...                 — any number of columns up to MAX_COLUMNS
```

## Columns

Each `columnN.md` file is one wallpaper column. Files are read in alphabetical order.

File format:

```markdown
---
column: 1
title: Tasks
---

## Heading

---

- list item
- **bold** item

> blockquote

### Subheading

Plain text

*Italic text spanning
multiple lines*

```code block```

![32x32](images/icon.png) label

<!-- /column:1 -->
```

- `title:` — column header shown in the column's accent bar; taken from frontmatter
- The frontmatter block (`---...---`) and HTML comments (`<!-- -->`) are stripped before rendering
- `---` inside a column draws a horizontal rule at that position
- `*...*` spanning multiple lines renders as italic text

## Images

Place files in `content/images/` and reference them in any column:

```markdown
![](images/logo.png)               — original size
![32x32](images/icon.png)          — rectangle, scaled to 32×32 px
![48c](images/avatar.png)          — circle, diameter 48 px
![32x32](images/icon.png) KDE      — rectangle with a text label
![48c](images/avatar.png) KDE      — circle with a text label
```

| Alt text | Shape | Description |
|---|---|---|
| _(empty)_ | original | no resizing |
| `WxH` | rectangle | scaled to W×H pixels |
| `Nc` | circle | cropped to circle of diameter N px (`c` = circle) |

Text after `)` is rendered to the right of the image, vertically centered. PNG transparency is composited correctly.

## Header & footer

`content/header.md` and `content/footer.md` are plain text rendered as-is in the top and bottom bars.

Color individual words or characters with `[text](color)` syntax:

```
[DESK·OS](green) │ [~/wallpaper/content/](muted)
```

### Colors

| Name | Description |
|---|---|
| `green` `cyan` `red` `yellow` `purple` | accent colors (match column order) |
| `bright` | bright white |
| `main` | default text |
| `muted` | muted gray |
| `dim` | dark gray |
| `#rrggbb` | any hex color |

Text without markup uses the default color (header → `green`, footer → `muted`).

## Settings

Copy the example file to create your personal settings:

```bash
cp settings.py.example settings.py
```

The script loads `settings.py` if it exists, otherwise falls back to `settings.py.example`. `settings.py` is git-ignored so personal settings are never committed.

### All options

```python
# Resolution
WIDTH  = 1920
HEIGHT = 1080

# Paths
OUTPUT_PNG  = Path.home() / ".config" / "desk-os-wallpaper.png"
CONTENT_DIR = BASE_DIR / "content"

# Columns
MAX_COLUMNS = 5        # maximum number of columns rendered

# Layout
TOPBAR_H    = 36       # top bar height (px)
FOOTER_H    = 26       # bottom bar height (px)
COL_PADDING = 22       # inner column padding (px)

# Font sizes
FONT_SIZE_NORMAL = 12
FONT_SIZE_SMALL  = 11
FONT_SIZE_TINY   = 10

# Font paths — set to None for auto-detection
# Auto-detection order: JetBrains Mono → DejaVu → Liberation → Ubuntu Mono
FONT_REGULAR     = None  # e.g. "/usr/share/fonts/truetype/fira/FiraCode-Regular.ttf"
FONT_BOLD        = None
FONT_ITALIC      = None
FONT_BOLD_ITALIC = None

# Colors (RGB tuples)
BG          = (8, 8, 8)
BG_TOPBAR   = (12, 12, 12)   # top bar background
BG_FOOTER   = (12, 12, 12)   # bottom bar background
COL_COLORS  = [(0,255,136), (0,207,255), (255,107,107), (255,204,0), (200,130,255)]
TEXT_BRIGHT = (238, 238, 238)
TEXT_MAIN   = (187, 187, 187)
TEXT_MUTED  = (85, 85, 85)
TEXT_DIM    = (51, 51, 51)
BORDER      = (26, 26, 26)
```

`COL_COLORS` — accent colors assigned to columns in order: green, cyan, red, yellow, purple.

## Auto-update via cron

```bash
crontab -e
```

Add a line to refresh every 10 minutes:

```
*/10 * * * * bash /path/to/update-wallpaper.sh
```

`update-wallpaper.sh` exports `$DISPLAY` and `$DBUS_SESSION_BUS_ADDRESS` automatically so it works under cron without extra configuration.

If the wallpaper is not updating, verify your user UID matches the value in `update-wallpaper.sh`:

```bash
id -u   # default is 1000 on Ubuntu
```

If different, update the line in `update-wallpaper.sh`:

```bash
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/YOUR_UID/bus
```

## Requirements

- Python 3.8+
- KDE Plasma (Kubuntu 22.04+)
- Pillow (installed automatically)
- JetBrains Mono (optional — falls back to DejaVu / Liberation / Ubuntu Mono)
