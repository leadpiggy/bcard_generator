from __future__ import annotations

import os
from typing import Tuple, Iterable
from PIL import Image, ImageDraw, ImageFont, ImageColor
from pathlib import Path
from config import (
    HEADSHOT_DIR,
    AGENT_DIR,
    RING_IMAGE,
    BCARD_BG,
    FONT_SEMIBOLD,
    FONT_REGULAR,
    FONT_COLOR,
    FONT_COLOR_TWO,
    AGENT_POS,
    AGENT_SIZE,
    QR_POS,
    NAME_BOX,
    PHONE_BOX,
    EMAIL_BOX,
    HEADSHOT_POS,
    HEADSHOT_SIZE,
    QR_BOX,
    COLOUR_WHITE,
    COLOUR_DOT,
    DEFAULT_TRACKING,
)
# Import generators
from generate_qr_code import generate_qr_code
from generate_texts import generate_text_assets, draw_text_image, measure_text, scale_to_fit
from generate_agent_image import compose_with_ring
from config import BCARD_DIR, QR_DIR, TEXT_DIR
# Use the local compose_headshot helper defined below. Avoid importing
# the CLI `main` from generate_agent_image which has a different API.

# Bounding boxes (x, y, width, height) for the various text elements and
# QR code.  These values were derived by scanning the supplied
# ``bcard-bg-with-guides.png`` file for the red guide rectangles.  They
# represent the exact pixel bounds in which each element must fit and
# align.  If you adjust the template artwork, you should re-extract
# these values.  See the repository README for details.

# (constants moved to config.py)


# ---------------------------------------------------------------------------
# Helper functions
#
def measure_text(text: str, font: ImageFont.FreeTypeFont, tracking: int) -> Tuple[int, int]:
    """
    Compute the approximate width and height in pixels of ``text`` when
    rendered with the given font and character spacing.  This helper
    uses the deprecated ``font.getsize`` API which still provides
    reliable extents for uppercase letters and digits when tracking
    characters manually.  The height is the maximum height among
    characters and the width includes added tracking between
    characters.

    :param text: The text to measure
    :param font: A PIL FreeTypeFont instance
    :param tracking: Pixels to add between characters
    :return: (width, height) in pixels
    """
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


def draw_text_image(
    text: str,
    font: ImageFont.FreeTypeFont,
    fill_main: str,
    fill_dot: str,
    tracking: int,
) -> Image.Image:
    """
    Render ``text`` into a new transparent image using the given
    ``font`` and character spacing.

    Unlike the previous implementation which relied on ``font.getsize``
    for extents, this version computes per-character bounding boxes
    (via ``font.getbbox``) and then aligns all glyphs against a
    common baseline.  It ensures that ascenders and descenders are
    respected and that no glyphs are clipped.  Each character is
    drawn at an offset that compensates for its own origin and the
    global baseline, so the resulting image tightly bounds the text.

    :param text: The text to render
    :param font: A PIL FreeTypeFont instance
    :param fill_main: Colour for non-dot characters
    :param fill_dot: Colour for dot characters
    :param tracking: Pixels between characters
    :return: A new RGBA image containing the rendered text
    """
    # Gather per-character bounding boxes relative to their origin.
    char_bboxes = []
    char_widths = []
    global_min_y = None
    global_max_y = None
    for ch in text:
        # getbbox returns (x0, y0, x1, y1) relative to the baseline.
        # See PIL.ImageFont.ImageFont.getbbox docs.
        bbox = font.getbbox(ch)
        char_bboxes.append(bbox)
        w = bbox[2] - bbox[0]
        char_widths.append(w)
        if global_min_y is None or bbox[1] < global_min_y:
            global_min_y = bbox[1]
        if global_max_y is None or bbox[3] > global_max_y:
            global_max_y = bbox[3]
    if global_min_y is None or global_max_y is None:
        # Empty string
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    # Height of the composite is the vertical span between the
    # highest ascender and the lowest descender.
    height = global_max_y - global_min_y
    # Total width includes tracking between characters.
    width_total = sum(char_widths) + tracking * (len(text) - 1)
    # Create a transparent canvas large enough to hold the text.
    img = Image.new("RGBA", (int(width_total), int(height)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    x_cursor = 0
    for idx, ch in enumerate(text):
        bbox = char_bboxes[idx]
        # Determine fill colour (dots use the special colour)
        colour = fill_dot if ch == "." else fill_main
        # ``bbox`` gives (x0, y0, x1, y1) relative to the baseline at (0,0).
        # ``y0`` may be positive for ascenders or negative for descenders.
        # ``y1`` indicates the baseline of the glyph.  We want to align
        # the bottom of each glyph's bounding box to ``global_max_y`` and
        # the top of the overall image to ``global_min_y``.  The y-offset
        # for drawing the glyph is computed as follows:
        # new_y = (global_max_y - bbox[3]) - global_min_y
        y_offset = (global_max_y - bbox[3]) - global_min_y
        # For the x-offset we align the left edge of the glyph's
        # bounding box at ``x_cursor``.
        x_offset = x_cursor - bbox[0]
        draw.text((x_offset, y_offset), ch, font=font, fill=colour)
        # Advance the cursor by the glyph width and tracking
        x_cursor += char_widths[idx]
        if idx < len(text) - 1:
            x_cursor += tracking
    return img


def scale_to_fit(
    image: Image.Image,
    box: Tuple[int, int],
    preserve_aspect: bool = True,
) -> Image.Image:
    """
    Resize ``image`` to fit within the bounding box of width ``box[0]`` and
    height ``box[1]``.  If ``preserve_aspect`` is true the scaling is
    uniform and the resulting image will fit within the box without
    distortion.  If false the image is stretched independently along
    width and height to exactly fill the box (used for phone numbers).

    :param image: An image to scale
    :param box: (width, height) of the bounding box
    :param preserve_aspect: Whether to keep the aspect ratio
    :return: A resized image
    """
    bw, bh = box
    iw, ih = image.size
    if preserve_aspect:
        scale = min(bw / iw, bh / ih)
        new_size = (int(iw * scale), int(ih * scale))
    else:
        new_size = (bw, bh)
    if new_size[0] <= 0 or new_size[1] <= 0:
        return image.copy()
    return image.resize(new_size, Image.Resampling.LANCZOS)


def compose_headshot(
    headshot_path: str, ring_path: str, size: int
) -> Image.Image:
    """
    Composite a square crop of the agent headshot with the gold ring.

    The input headshot is cropped to a centred square, resized to ``size``
    pixels and masked into a circle.  The ring is resized to the same
    dimensions and pasted on top.

    :param headshot_path: Path to the agent’s headshot image
    :param ring_path: Path to the gold ring overlay image
    :param size: Final width/height of the output composite in pixels
    :return: An RGBA image containing the ringed headshot
    """
    head = Image.open(headshot_path).convert("RGBA")
    ring = Image.open(ring_path).convert("RGBA")
    # Crop the headshot to a square (centre crop)
    w, h = head.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    head_cropped = head.crop((left, top, left + side, top + side))
    head_resized = head_cropped.resize((size, size), Image.Resampling.LANCZOS)
    # Apply a circular mask
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, size, size), fill=255)
    head_resized.putalpha(mask)
    ring_resized = ring.resize((size, size), Image.Resampling.LANCZOS)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(head_resized, (0, 0), head_resized)
    result.paste(ring_resized, (0, 0), ring_resized)
    return result


# ---------------------------------------------------------------------------
# Main card assembly
#
def generate_business_card(
    first_name: str,
    last_name: str,
    phone_number: str,
    headshot_path: str | Path,
    qr_image_path: str | Path,
    output_path: str = "output_card.png",
    background_path: Path = BCARD_BG,
    ring_path: Path = RING_IMAGE,
    font_name_path: Path = FONT_SEMIBOLD,
    font_phone_path: Path = FONT_SEMIBOLD,
    font_email_path: Path = FONT_SEMIBOLD,
    name_img_path: str | Path | None = None,
    phone_img_path: str | Path | None = None,
    email_img_path: str | Path | None = None,
) -> None:
    """
    Assemble a business card PNG for a single agent.

    :param first_name: Agent first name
    :param last_name: Agent last name
    :param phone_number: Raw phone number string (will be formatted)
    :param headshot_path: Path to agent headshot image
    :param qr_image_path: Path to a pre-generated QR code image
    :param output_path: Filename for the output card
    :param background_path: Path to the blank background PNG
    :param ring_path: Path to the gold ring overlay
    :param font_name_path: Font file for the name text
    :param font_phone_path: Font file for the phone number text
    :param font_email_path: Font file for the email user text
    """
    # Load assets
    bg = Image.open(background_path).convert("RGBA")
    card = bg.copy()
    qr = Image.open(qr_image_path).convert("RGBA").resize((QR_BOX[2], QR_BOX[3]), Image.Resampling.LANCZOS)
    # If caller passed a path to a precomposed agent image (with ring),
    # use it directly. Otherwise compose it from the raw headshot.
    headshot_candidate = Path(headshot_path)
    if headshot_candidate.exists():
        head = Image.open(str(headshot_candidate)).convert("RGBA").resize((HEADSHOT_SIZE, HEADSHOT_SIZE), Image.Resampling.LANCZOS)
    else:
        head = compose_headshot(str(headshot_path), str(ring_path), HEADSHOT_SIZE)
        head = head.convert("RGBA")
    # Paste headshot and QR code onto the card
    card.paste(head, HEADSHOT_POS, head)
    card.paste(qr, (QR_BOX[0], QR_BOX[1]), qr)
    # Prepare texts
    # Format the phone number: remove non-digit characters and format with dots
    digits: str = "".join(filter(str.isdigit, phone_number))
    phone_formatted = f"{digits[:3]}.{digits[3:6]}.{digits[6:10]}"
    # Format the email local part
    email_user = f"{first_name.lower()}.{last_name.lower()}"
    # Name: prefer pre-generated image if available, otherwise render.
    if name_img_path and Path(name_img_path).exists():
        name_img = Image.open(str(name_img_path)).convert("RGBA")
        scaled_name = scale_to_fit(name_img, (NAME_BOX[2], NAME_BOX[3]), preserve_aspect=True)
        nx = NAME_BOX[0] + (NAME_BOX[2] - scaled_name.width) // 2
        ny = NAME_BOX[1] + (NAME_BOX[3] - scaled_name.height) // 2
        card.paste(scaled_name, (int(nx), int(ny)), scaled_name)
    else:
        _draw_and_paste_text(
            card,
            text=f"{first_name.upper()} {last_name.upper()}",
            font_path=font_name_path,
            box=NAME_BOX,
            fill_main=COLOUR_WHITE,
            fill_dot=COLOUR_DOT,
            align_h="center",
            align_v="center",
            tracking=DEFAULT_TRACKING,
            preserve_aspect=True,
            max_font_size=400,
        )
    # Draw the phone (fills its box exactly, non-uniform scaling).  A
    # moderate base font size is sufficient because non-uniform
    # scaling will stretch the text to the bounding box.
    # Phone: prefer pre-generated phone image (which includes dot coloring)
    if phone_img_path and Path(phone_img_path).exists():
        phone_img = Image.open(str(phone_img_path)).convert("RGBA")
        # stretch to exactly fill the phone box. Paste at the box origin so
        # the asset fills the guide completely (matches the icon baseline).
        scaled_phone = scale_to_fit(phone_img, (PHONE_BOX[2], PHONE_BOX[3]), preserve_aspect=False)
        px = PHONE_BOX[0]
        py = PHONE_BOX[1]
        card.paste(scaled_phone, (int(px), int(py)), scaled_phone)
    else:
        _draw_and_paste_text(
            card,
            text=phone_formatted,
            font_path=font_phone_path,
            box=PHONE_BOX,
            fill_main=COLOUR_WHITE,
            fill_dot=COLOUR_DOT,
            align_h="left",
            # Centre the phone number vertically within its bounding box to
            # avoid clipping the tops or bottoms of tall digits.
            align_v="center",
            tracking=DEFAULT_TRACKING,
            preserve_aspect=False,
            max_font_size=200,
        )
    # Draw the email user (right aligned, bottom aligned).  Using a
    # generous base font size helps maximise the text within its
    # bounding box while preserving the aspect ratio.
    # Email: prefer pre-generated email image if available
    if email_img_path and Path(email_img_path).exists():
        email_img = Image.open(str(email_img_path)).convert("RGBA")
        scaled_email = scale_to_fit(email_img, (EMAIL_BOX[2], EMAIL_BOX[3]), preserve_aspect=True)
        ex = EMAIL_BOX[0] + (EMAIL_BOX[2] - scaled_email.width) // 2
        ey = EMAIL_BOX[1] + (EMAIL_BOX[3] - scaled_email.height) // 2
        card.paste(scaled_email, (int(ex), int(ey)), scaled_email)
    else:
        _draw_and_paste_text(
            card,
            text=email_user.upper(),
            font_path=font_email_path,
            box=EMAIL_BOX,
            fill_main=COLOUR_WHITE,
            fill_dot=COLOUR_DOT,
            align_h="center",
            align_v="center",
            tracking=DEFAULT_TRACKING,
            preserve_aspect=True,
            max_font_size=300,
        )
    # Save the final card. If saving as JPEG convert to RGB first.
    out_path = Path(output_path)
    if out_path.suffix.lower() in (".jpg", ".jpeg"):
        rgb = Image.new("RGB", card.size, (255, 255, 255))
        rgb.paste(card, mask=card.split()[3] if card.mode == "RGBA" else None)
        rgb.save(output_path, quality=95)
    else:
        card.save(output_path)


def _draw_and_paste_text(
    card: Image.Image,
    text: str,
    font_path: str | Path,
    box: Tuple[int, int, int, int],
    fill_main: str,
    fill_dot: str,
    align_h: str,
    align_v: str,
    tracking: int,
    preserve_aspect: bool,
    max_font_size: int = 200,
    min_font_size: int = 8,
) -> None:
    """
    Internal helper to render ``text`` into a temporary image, scale it to
    occupy its bounding box according to the specified constraints and then
    paste it onto ``card``.  This implementation differs from previous
    versions by always rendering the text at a single (large) font size
    rather than iterating sizes; the rendered image is then scaled to
    ensure that either its height or width fills the bounding box (when
    ``preserve_aspect`` is true) or that it completely covers the box
    (when false).  This simplifies logic and guarantees that one
    dimension will reach its limit without clipping.

    :param card: The card image onto which to paste
    :param text: The string to render (uppercase/lowercase as desired)
    :param font_path: Path to the TrueType font to use
    :param box: (x, y, width, height) bounding box in which to place the text
    :param fill_main: Colour for non-dot characters
    :param fill_dot: Colour for dot characters
    :param align_h: Horizontal alignment: "left", "center" or "right"
    :param align_v: Vertical alignment: "top", "center" or "bottom"
    :param tracking: Pixel spacing between characters (before scaling)
    :param preserve_aspect: Whether to maintain aspect ratio when scaling
    :param max_font_size: Base font size used to render text before scaling
    :param min_font_size: Unused in this version (kept for compatibility)
    """
    x, y, w, h = box
    # Render the text at a large base font size; this ensures crispness
    # after scaling.  We choose max_font_size here; adjustments can be
    # made by callers via the argument.
    base_font = ImageFont.truetype(str(font_path), max_font_size)
    text_img = draw_text_image(text, base_font, fill_main, fill_dot, tracking)
    # Scale the rendered text into the bounding box
    scaled = scale_to_fit(text_img, (w, h), preserve_aspect=preserve_aspect)
    sw, sh = scaled.size
    # Determine offsets based on alignment flags
    if align_h == "center":
        dx = x + (w - sw) // 2
    elif align_h == "right":
        dx = x + (w - sw)
    else:
        dx = x
    if align_v == "center":
        dy = y + (h - sh) // 2
    elif align_v == "bottom":
        dy = y + (h - sh)
    else:
        dy = y
    card.paste(scaled, (int(dx), int(dy)), scaled)


def build_card_for_agent(first: str, last: str, phone: str, headshot_source: str | None = None) -> str:
    """High-level flow: generate agent image, qr, text assets, assemble card.

    Returns path to saved business card JPEG.
    """
    # Ensure directories exist
    BCARD_DIR.mkdir(parents=True, exist_ok=True)
    QR_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    # Determine headshot path
    headshot_filename = f"{first.lower()}-{last.lower()}.png"
    headshot_path = HEADSHOT_DIR / headshot_filename
    if headshot_source:
        # Try to use save_headshot from generate_agent_image if available
        try:
            from generate_agent_image import save_headshot

            saved = save_headshot(headshot_source, first, last)
            headshot_path = Path(saved)
        except Exception:
            # Fallback: assume headshot_source is a local path
            headshot_path = Path(headshot_source)

    if not headshot_path.exists():
        raise FileNotFoundError(f"Headshot not found at {headshot_path}; provide a valid headshot or headshot_source.")

    # Create ringed agent image (writes into AGENT_DIR and returns path)
    print(f"Composing ringed headshot for {first} {last}...")
    agent_image_path = compose_with_ring(str(headshot_path))

    # Create QR code
    print("Creating QR code...")
    qr_path = generate_qr_code(first, last)

    # Generate text assets
    print("Generating text assets...")
    texts = generate_text_assets(first, last, phone)
    name_img = texts.get('name')
    phone_img = texts.get('phone')
    email_img = texts.get('email')

    # Assemble final business card
    out_file = BCARD_DIR / f"{first.lower()}-{last.lower()}-bcard.jpg"
    print(f"Assembling final card to {out_file}...")
    generate_business_card(
        first_name=first,
        last_name=last,
        phone_number=phone,
        headshot_path=str(agent_image_path),
        qr_image_path=str(qr_path),
        output_path=str(out_file),
        background_path=BCARD_BG,
        ring_path=RING_IMAGE,
        font_name_path=FONT_SEMIBOLD,
        font_phone_path=FONT_SEMIBOLD,
        font_email_path=FONT_REGULAR,
        name_img_path=name_img,
        phone_img_path=phone_img,
        email_img_path=email_img,
    )

    print(f"Business card written to {out_file}")
    return str(out_file)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build business card for an agent")
    parser.add_argument("first", help="First name")
    parser.add_argument("last", help="Last name")
    parser.add_argument("phone", help="Phone number")
    parser.add_argument("--headshot", help="Optional headshot source path or URL", default=None)
    args = parser.parse_args()

    build_card_for_agent(args.first, args.last, args.phone, headshot_source=args.headshot)


