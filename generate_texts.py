#!/usr/bin/env python3
from __future__ import annotations
"""Module to generate standalone text PNG assets (name, phone, email).

Provides:
- generate_text_assets(first, last, phone, out_dir=TEXT_DIR)
- utility functions: measure_text, scale_to_fit

The module still uses draw_text_image from `draw_dynamic_text` for rendering.
"""
from pathlib import Path
from typing import Tuple
from PIL import Image, ImageFont, ImageDraw

from config import TEXT_DIR, FONT_SEMIBOLD, FONT_REGULAR, FONT_COLOR, FONT_COLOR_TWO

# --- Utilities ---
def draw_text_image(
    text: str,
    font: ImageFont.FreeTypeFont,
    fill_main,
    fill_dot,
    tracking: int,
    char_color_map: dict | None = None,
) -> Image.Image:
    # Baseline-aware per-character rendering to avoid unnecessary
    # top/bottom padding. This computes per-glyph bounding boxes via
    # font.getbbox and aligns glyphs against a common baseline.
    char_bboxes = []
    char_widths = []
    global_min_y = None
    global_max_y = None
    for ch in text:
        bbox = font.getbbox(ch)
        char_bboxes.append(bbox)
        w = bbox[2] - bbox[0]
        char_widths.append(w)
        if global_min_y is None or bbox[1] < global_min_y:
            global_min_y = bbox[1]
        if global_max_y is None or bbox[3] > global_max_y:
            global_max_y = bbox[3]
    if global_min_y is None or global_max_y is None:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    height = global_max_y - global_min_y
    width_total = sum(char_widths) + tracking * (len(text) - 1)
    img = Image.new("RGBA", (max(1, int(width_total)), max(1, int(height))), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    x_cursor = 0
    for idx, ch in enumerate(text):
        bbox = char_bboxes[idx]
        if char_color_map and idx in char_color_map:
            colour = char_color_map[idx]
        else:
            colour = fill_dot if ch == "." else fill_main
        y_offset = (global_max_y - bbox[3]) - global_min_y
        x_offset = x_cursor - bbox[0]
        draw.text((x_offset, y_offset), ch, font=font, fill=colour)
        x_cursor += char_widths[idx]
        if idx < len(text) - 1:
            x_cursor += tracking
    return img

# --- Core text measurement and scaling functions ---
def measure_text(text: str, font: ImageFont.FreeTypeFont, tracking: int) -> Tuple[int, int]:
    total_width = 0
    max_height = 0
    for index, ch in enumerate(text):
        bbox = font.getbbox(ch)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        total_width += w
        max_height = max(max_height, h)
        if index < len(text) - 1:
            total_width += tracking
    return int(total_width), int(max_height)


def scale_to_fit(image: Image.Image, box: Tuple[int, int], preserve_aspect: bool = True) -> Image.Image:
    bw, bh = box
    iw, ih = image.size
    if preserve_aspect:
        scale = min(bw / iw, bh / ih)
        new_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))
    else:
        new_size = (max(1, int(bw)), max(1, int(bh)))
    return image.resize(new_size, Image.Resampling.LANCZOS)

# --- Color utility ---
def _rgb_to_hex(rgb_tuple):
    if isinstance(rgb_tuple, tuple) and len(rgb_tuple) >= 3:
        return '#%02x%02x%02x' % (rgb_tuple[0], rgb_tuple[1], rgb_tuple[2])
    return str(rgb_tuple)


# --- Main API ---
def generate_text_assets(first: str, last: str, phone: str, out_dir: Path | str = TEXT_DIR) -> dict:
    """Generate name, phone, and email PNG assets and return a dict of paths.

    Returns a dict: {"name": Path(...), "phone": Path(...), "email": Path(...)}
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # Name
    name = f"{first} {last}".upper()
    name_font = ImageFont.truetype(str(FONT_SEMIBOLD), 300)
    name_img = draw_text_image(name, name_font, _rgb_to_hex(FONT_COLOR), _rgb_to_hex(FONT_COLOR_TWO), tracking=2)
    name_path = out_dir / f"{first}-{last}-name.png"
    name_img.save(name_path)
    results['name'] = name_path

    # Phone
    phone_fmt = phone.replace("(", "").replace(")", "").replace("-", ".").replace(" ", ".")
    phone_font = ImageFont.truetype(str(FONT_SEMIBOLD), 120)
    main_col = _rgb_to_hex(FONT_COLOR)
    dot_col = _rgb_to_hex(FONT_COLOR_TWO)
    phone_char_map = {i: (dot_col if ch == '.' else main_col) for i, ch in enumerate(phone_fmt)}
    phone_img = draw_text_image(phone_fmt, phone_font, main_col, dot_col, tracking=2, char_color_map=phone_char_map)
    phone_path = out_dir / f"{first}-{last}-phone.png"
    phone_img.save(phone_path)
    results['phone'] = phone_path

    # Email
    email = f"{first}.{last}".upper()
    email_font = ImageFont.truetype(str(FONT_REGULAR), 180)
    try:
        dot_index = email.index('.')
    except ValueError:
        dot_index = -1
    char_map = {}
    if dot_index >= 0:
        for i in range(len(email)):
            # Include the dot itself and all characters after it (the last name)
            # in the alternate color (FONT_COLOR_TWO).
            char_map[i] = (_rgb_to_hex(FONT_COLOR_TWO) if i >= dot_index else _rgb_to_hex(FONT_COLOR))
    else:
        for i in range(len(email)):
            char_map[i] = _rgb_to_hex(FONT_COLOR)

    email_img = draw_text_image(email, email_font, _rgb_to_hex(FONT_COLOR), _rgb_to_hex(FONT_COLOR_TWO), tracking=2, char_color_map=char_map)
    email_path = out_dir / f"{first}-{last}-email.png"
    email_img.save(email_path)
    results['email'] = email_path

    return results


if __name__ == '__main__':
    # quick CLI demo
    import argparse
    parser = argparse.ArgumentParser(description='Generate text assets for a contact')
    parser.add_argument('--first', default='sean')
    parser.add_argument('--last', default='fallon')
    parser.add_argument('--phone', default='801.836.6758')
    parser.add_argument('--out', default=str(TEXT_DIR))
    args = parser.parse_args()
    print('Generating text assets to', args.out)
    res = generate_text_assets(args.first, args.last, args.phone, out_dir=args.out)
    for k, p in res.items():
        print(k, p)
