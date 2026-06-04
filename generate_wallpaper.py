#!/usr/bin/env python3
"""
DESK·OS — MD → Wallpaper for Kubuntu
Reads column files from content/, renders PNG, sets as KDE wallpaper
"""

import subprocess
import sys
import os
import re
import textwrap
import time
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing Pillow...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], check=True)
    from PIL import Image, ImageDraw, ImageFont

from settings import (
    WIDTH, HEIGHT, OUTPUT_PNG, CONTENT_DIR,
    MAX_COLUMNS,
    TOPBAR_H, FOOTER_H, COL_PADDING,
    FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TINY,
    BG, COL_COLORS, TEXT_BRIGHT, TEXT_MAIN, TEXT_MUTED, TEXT_DIM, BORDER,
)

# ══════════════════════════════════════════════
#  FONTS — look for JetBrains Mono or fallback
# ══════════════════════════════════════════════
def find_font(size, bold=False, italic=False):
    if bold and italic:
        candidates = [
            f"/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-BoldItalic.ttf",
            f"{Path.home()}/.local/share/fonts/JetBrainsMono-BoldItalic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-BoldOblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-BoldItalic.ttf",
            "/usr/share/fonts/truetype/ubuntu/UbuntuMono-BI.ttf",
        ]
    elif italic:
        candidates = [
            f"/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Italic.ttf",
            f"{Path.home()}/.local/share/fonts/JetBrainsMono-Italic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Oblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Italic.ttf",
            "/usr/share/fonts/truetype/ubuntu/UbuntuMono-RI.ttf",
        ]
    elif bold:
        candidates = [
            f"/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
            f"/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
            f"{Path.home()}/.local/share/fonts/JetBrainsMono-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf",
        ]
    else:
        candidates = [
            f"/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf",
            f"/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono.ttf",
            f"{Path.home()}/.local/share/fonts/JetBrainsMono-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

# ══════════════════════════════════════════════
#  MARKDOWN PARSER
# ══════════════════════════════════════════════
def parse_md_line(line):
    """Returns (type, text, extra) — for img: text=path, extra=size string or empty"""
    if line.startswith('### '): return ('h3', line[4:].strip(), '')
    if line.startswith('## '):  return ('h2', line[3:].strip(), '')
    if line.startswith('# '):   return ('h1', line[2:].strip(), '')
    if line.startswith('- '):   return ('li', line[2:].strip(), '')
    if line.startswith('> '):   return ('bq', line[2:].strip(), '')
    if line.startswith('```'):  return ('code_toggle', '', '')
    if line.strip() == '---':   return ('hr', '', '')
    if line.strip() == '':      return ('empty', '', '')
    m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)(.*)', line.strip())
    if m:                       return ('img', m.group(2).strip(), (m.group(1).strip(), m.group(3).strip()))
    return ('p', line.strip(), '')

def strip_inline(text):
    """Remove ** * ` markers from text before rendering"""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*',     r'\1', text)
    text = re.sub(r'`(.*?)`',       r'\1', text)
    return text

def is_bold_segment(text):
    """Check whether text contains bold markup"""
    return bool(re.search(r'\*\*.*?\*\*', text))

# ══════════════════════════════════════════════
#  IMAGE HELPERS
# ══════════════════════════════════════════════
def crop_circle(image):
    """Return image cropped to a circle using an alpha mask"""
    image = image.convert('RGBA')
    size  = min(image.width, image.height)
    image = image.crop((0, 0, size, size))
    mask  = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    result.paste(image, mask=mask)
    return result

# ══════════════════════════════════════════════
#  COLORED TEXT RENDERER
#  Syntax: [text](color)  where color is a name
#  (green/cyan/red/yellow/purple/bright/main/muted/dim)
#  or a hex value (#rrggbb)
# ══════════════════════════════════════════════
_NAMED_COLORS = {
    'green':  COL_COLORS[0],
    'cyan':   COL_COLORS[1],
    'red':    COL_COLORS[2],
    'yellow': COL_COLORS[3],
    'purple': COL_COLORS[4],
    'bright': TEXT_BRIGHT,
    'main':   TEXT_MAIN,
    'muted':  TEXT_MUTED,
    'dim':    TEXT_DIM,
}

def _parse_color(color_str):
    """Convert a color name or #rrggbb string to an (r, g, b) tuple"""
    c = color_str.strip().lower()
    if c in _NAMED_COLORS:
        return _NAMED_COLORS[c]
    if re.match(r'^#[0-9a-f]{6}$', c):
        return tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
    return None

def draw_colored_text(draw, x, y, text, font, default_color, max_right=None):
    """Draw text with inline [word](color) spans; unstyled text uses default_color.
    If max_right is set, stops drawing at that x coordinate."""
    segments = re.split(r'(\[.*?\]\([^)]*\))', text)
    cx = x
    for seg in segments:
        m = re.fullmatch(r'\[([^\]]*)\]\(([^)]*)\)', seg)
        if m:
            label, color_str = m.group(1), m.group(2)
            color = _parse_color(color_str) or default_color
        else:
            label, color = seg, default_color
        if label:
            if max_right is not None and cx >= max_right:
                break
            draw.text((cx, y), label, font=font, fill=color)
            cx += font.getbbox(label)[2]

# ══════════════════════════════════════════════
#  COLUMN FILE READER
# ══════════════════════════════════════════════
def parse_frontmatter(text):
    """Extract YAML frontmatter fields and return (fields_dict, remaining_text)"""
    if not text.startswith('---\n'):
        return {}, text
    end = text.find('\n---\n', 4)
    if end == -1:
        return {}, text
    fields = {}
    for line in text[4:end].splitlines():
        if ':' in line:
            key, _, val = line.partition(':')
            fields[key.strip()] = val.strip()
    return fields, text[end + 5:]

def strip_html_comments(text):
    """Remove HTML comment lines (<!-- ... -->) used as file footers"""
    lines = [l for l in text.split('\n') if not l.strip().startswith('<!--')]
    return '\n'.join(lines)

def read_column_file(path):
    """Read a column file and return (title, content) — title comes from frontmatter"""
    text = path.read_text(encoding='utf-8')
    fields, text = parse_frontmatter(text)
    text = strip_html_comments(text)
    title = fields.get('title', path.stem)
    return title, text.strip()

def read_content():
    """Read all column*.md files from content/ in sorted order and join them as sections"""
    col_files = sorted(CONTENT_DIR.glob('column*.md'))
    if not col_files:
        return None, [], []
    titles, sections = zip(*[read_column_file(f) for f in col_files])
    return '\n[[COL]]\n'.join(sections), list(col_files), list(titles)

# ══════════════════════════════════════════════
#  SINGLE COLUMN RENDERER
# ══════════════════════════════════════════════
def render_column(img, draw, md_text, x, y, w, h, col_index, col_title,
                  font_n, font_b, font_s, font_ss, font_i):
    color  = COL_COLORS[col_index % len(COL_COLORS)]
    cx     = x + COL_PADDING
    max_w  = w - COL_PADDING * 2
    cy     = y

    # Colored top bar
    draw.rectangle([x, y, x+w, y+2], fill=color)
    cy += 10

    # Column header with index number
    num_text = f"0{col_index+1}"
    draw.text((cx, cy), num_text, font=font_ss, fill=color)
    nw = font_ss.getbbox(num_text)[2]
    draw.text((cx + nw + 10, cy+1), col_title.upper(), font=font_ss, fill=TEXT_BRIGHT)
    cy += 22

    # Separator line
    draw.line([x, cy, x+w, cy], fill=BORDER, width=1)
    cy += 12

    # Parse and draw each line
    lines     = md_text.strip().split('\n')
    in_code   = False
    in_italic = False
    code_buf  = []

    for raw_line in lines:
        if cy > y + h - 20:
            break

        kind, text, extra = parse_md_line(raw_line)

        if kind == 'img':
            size_str, label = extra
            img_path = CONTENT_DIR / text
            if img_path.exists():
                try:
                    icon = Image.open(img_path).convert('RGBA')
                    circle = re.match(r'^(\d+)c$', size_str.lower())
                    rect   = re.match(r'^(\d+)x(\d+)$', size_str.lower())
                    if circle:
                        d    = int(circle.group(1))
                        icon = crop_circle(icon.resize((d, d), Image.LANCZOS))
                    elif rect:
                        icon = icon.resize((int(rect.group(1)), int(rect.group(2))), Image.LANCZOS)
                    img.paste(icon, (cx, cy), icon)
                    if label:
                        label_y = cy + (icon.height - font_n.getbbox('A')[3]) // 2
                        draw.text((cx + icon.width + 8, label_y), label.strip(), font=font_n, fill=TEXT_MAIN)
                    cy += icon.height + 6
                except Exception:
                    pass
            continue

        if kind == 'code_toggle':
            if not in_code:
                in_code  = True
                code_buf = []
            else:
                in_code = False
                # Draw collected code block
                block_h = len(code_buf) * 16 + 10
                draw.rectangle([cx-4, cy-2, cx+max_w+4, cy+block_h], fill=(14,14,14), outline=BORDER)
                for cline in code_buf:
                    draw.text((cx+4, cy+4), cline, font=font_ss, fill=color)
                    cy += 16
                cy += 14
            continue

        if in_code:
            code_buf.append(raw_line)
            continue

        if kind == 'empty':
            cy += 6
            continue

        if kind == 'hr':
            cy += 6
            draw.line([cx, cy, cx+max_w, cy], fill=BORDER, width=1)
            cy += 8

        elif kind == 'h1':
            cy += 4
            draw.text((cx, cy), text.upper(), font=font_b, fill=TEXT_BRIGHT)
            cy += font_b.getbbox(text)[3] + 4

        elif kind == 'h2':
            cy += 6
            draw.text((cx, cy), text, font=font_b, fill=TEXT_BRIGHT)
            cy += font_b.getbbox(text)[3] + 4

        elif kind == 'h3':
            cy += 4
            draw.text((cx, cy), text, font=font_s, fill=TEXT_MUTED)
            cy += font_s.getbbox(text)[3] + 4

        elif kind == 'li':
            prefix = '›  '
            draw.text((cx, cy), prefix, font=font_n, fill=TEXT_DIM)
            fw = font_n.getbbox(prefix)[2]
            max_right = x + w - COL_PADDING
            indent = cx + fw
            if re.search(r'\[.*?\]\([^)]*\)', text):
                # Split into command span and description (after " — ")
                m_sep = re.search(r'^(\[.*?\]\([^)]*\))(.*)', text)
                if m_sep and ' — ' in m_sep.group(2):
                    cmd_span = m_sep.group(1)
                    rest     = m_sep.group(2)  # starts with " — description"
                    draw_colored_text(draw, indent, cy, cmd_span, font_n, TEXT_MAIN, max_right=max_right)
                    cmd_w = font_n.getbbox(re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', cmd_span))[2]
                    # Draw description on same line if fits, else wrap to next line
                    desc_x = indent + cmd_w
                    desc_text = rest
                    desc_w = font_n.getbbox(desc_text)[2]
                    if desc_x + desc_w <= max_right:
                        draw.text((desc_x, cy), desc_text, font=font_n, fill=TEXT_MAIN)
                        cy += 19
                    else:
                        cy += 19
                        desc_clean = rest.lstrip(' —').lstrip()
                        wrapped = textwrap.wrap(f"— {desc_clean}", width=(max_right - indent) // 7)
                        for wline in wrapped:
                            draw.text((indent + 4, cy), wline, font=font_n, fill=TEXT_MAIN)
                            cy += 17
                else:
                    draw_colored_text(draw, indent, cy, text, font_n, TEXT_MAIN, max_right=max_right)
                    cy += 19
            else:
                clean = strip_inline(text)
                clr   = TEXT_BRIGHT if is_bold_segment(text) else TEXT_MAIN
                wrapped = textwrap.wrap(clean, width=(max_right - indent) // 7)
                for i, wline in enumerate(wrapped):
                    draw.text((indent if i == 0 else indent + 4, cy), wline, font=font_n, fill=clr)
                    cy += 17
                cy += 2

        elif kind == 'bq':
            draw.rectangle([cx, cy, cx+3, cy+16], fill=COL_COLORS[2])
            clean = strip_inline(text)
            draw.text((cx+10, cy), clean, font=font_n, fill=TEXT_MUTED)
            cy += 20

        elif kind == 'p':
            # Detect start/end of a multi-line italic block (* ... *)
            stripped = text.strip()
            render_italic = in_italic
            if not in_italic and stripped.startswith('*') and not stripped.endswith('*'):
                in_italic = True
                render_italic = True
                text = stripped[1:]
            elif in_italic and stripped.endswith('*'):
                in_italic = False
                render_italic = True
                text = stripped[:-1]
            elif not in_italic and stripped.startswith('*') and stripped.endswith('*') and len(stripped) > 1:
                render_italic = True
                text = stripped[1:-1]
            clean   = strip_inline(text)
            wrapped = textwrap.wrap(clean, width=max_w//7)
            for wline in wrapped:
                if render_italic:
                    draw.text((cx, cy), wline, font=font_i, fill=TEXT_MUTED)
                elif is_bold_segment(text):
                    draw.text((cx, cy), wline, font=font_n, fill=TEXT_BRIGHT)
                else:
                    draw.text((cx, cy), wline, font=font_n, fill=TEXT_MAIN)
                cy += 18
            cy += 2

# ══════════════════════════════════════════════
#  MAIN RENDER
# ══════════════════════════════════════════════
def render(content_md, col_titles, header_text, footer_text):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    fn  = find_font(FONT_SIZE_NORMAL)
    fb  = find_font(FONT_SIZE_NORMAL, bold=True)
    fi  = find_font(FONT_SIZE_NORMAL, italic=True)
    fs  = find_font(FONT_SIZE_SMALL)
    fss = find_font(FONT_SIZE_TINY)

    # ── TOPBAR — raw text from header.md ──
    draw.rectangle([0, 0, WIDTH, TOPBAR_H], fill=(12,12,12))
    draw.line([0, TOPBAR_H, WIDTH, TOPBAR_H], fill=BORDER, width=1)
    draw_colored_text(draw, 14, 11, header_text, fb, COL_COLORS[0])

    # ── COLUMNS ──
    sections = content_md.split('\n[[COL]]\n')
    count    = min(len(sections), MAX_COLUMNS)
    col_w    = WIDTH // count
    col_y    = TOPBAR_H + 2
    col_h    = HEIGHT - TOPBAR_H - FOOTER_H - 2

    for i, (sec, title) in enumerate(zip(sections[:MAX_COLUMNS], col_titles[:count])):
        cx = i * col_w
        # Vertical divider between columns
        if i > 0:
            draw.line([cx, col_y, cx, col_y+col_h], fill=BORDER, width=1)
        render_column(img, draw, sec, cx, col_y, col_w, col_h, i, title,
                      fn, fb, fs, fss, fi)

    # ── FOOTER — raw text from footer.md ──
    fy = HEIGHT - FOOTER_H
    draw.rectangle([0, fy, WIDTH, HEIGHT], fill=(12,12,12))
    draw.line([0, fy, WIDTH, fy], fill=BORDER, width=1)
    draw_colored_text(draw, 14, fy+7, footer_text, fss, TEXT_MUTED)

    return img

# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
def main():
    if not CONTENT_DIR.exists():
        print(f"Content directory not found: {CONTENT_DIR}")
        sys.exit(1)

    content, col_files, col_titles = read_content()
    if not content:
        print(f"No column*.md files found in: {CONTENT_DIR}")
        sys.exit(1)

    print(f"Reading {len(col_files)} column(s) from: {CONTENT_DIR}")

    # Read header and footer as plain text — no parsing, no logic
    header_text = (CONTENT_DIR / "header.md").read_text(encoding='utf-8').strip()
    footer_text = (CONTENT_DIR / "footer.md").read_text(encoding='utf-8').strip()

    img = render(content, col_titles, header_text, footer_text)

    # Save to a timestamped filename so KDE always sees a new path and refreshes
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_PNG.parent / f"desk-os-wallpaper-{int(time.time())}.png"
    img.save(str(output_path))
    print(f"Saved: {output_path}")

    # Remove previous wallpaper files, keep only the new one
    for old in OUTPUT_PNG.parent.glob("desk-os-wallpaper-*.png"):
        if old != output_path:
            old.unlink(missing_ok=True)

    # Set as KDE wallpaper via qdbus
    uri = f"file://{output_path}"
    result = subprocess.run([
        "qdbus", "org.kde.plasmashell", "/PlasmaShell",
        "org.kde.PlasmaShell.evaluateScript",
        f"""
var allDesktops = desktops();
for (var i=0; i<allDesktops.length; i++) {{
    var d = allDesktops[i];
    d.wallpaperPlugin = 'org.kde.image';
    d.currentConfigGroup = ['Wallpaper','org.kde.image','General'];
    d.writeConfig('Image', '{uri}');
    d.reloadConfig();
}}
"""
    ], capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Wallpaper updated via qdbus")
    else:
        # Fallback: plasma-apply-wallpaperimage (Kubuntu 22.04+)
        result2 = subprocess.run(
            ["plasma-apply-wallpaperimage", str(output_path)],
            capture_output=True, text=True
        )
        if result2.returncode == 0:
            print("✓ Wallpaper set via plasma-apply-wallpaperimage")
        else:
            print(f"Failed to set wallpaper: {result.stderr}")
            print(f"Set manually: {output_path}")

if __name__ == "__main__":
    main()
