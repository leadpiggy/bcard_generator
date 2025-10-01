"""
generate_agent_image.py
=======================

This module contains a helper function and CLI for creating a ringed
headshot from an agent’s profile image.  It crops the provided
headshot to a square, resizes it, applies a circular mask and then
overlays a gold ring graphic.  The result is written to a file in
``AGENT_DIR``.

Usage as a script::

    python3 generate_agent_image.py FIRST LAST

where ``FIRST`` and ``LAST`` are the agent’s first and last names.
The script will search for the headshot in ``HEADSHOT_DIR/{first}-{last}.png``
or ``.jpg`` (case insensitive) and write the ringed image to
``AGENT_DIR/{first}-{last}.png``.  Directories can be overridden via
environment variables:

``HEADSHOT_DIR``: directory containing the raw headshots (default:
``headshots``)
``AGENT_DIR``: directory in which to save the ringed images (default:
``agents``)
``RING_IMAGE``: path to the ring overlay PNG (default:
``gold-ring.png`` in the current directory)

If invoked programmatically, call :func:`generate_agent_image` with
explicit paths.
"""

from __future__ import annotations

import os
import sys
from typing import Optional
from PIL import Image, ImageDraw
from pathlib import Path
import cv2
import requests
import shutil

from config import RING_IMAGE, AGENT_DIR, HEADSHOT_DIR

# Ensure AGENT_DIR and HEADSHOT_DIR are pathlib.Path instances
AGENT_DIR = Path(AGENT_DIR)
HEADSHOT_DIR = Path(HEADSHOT_DIR)



def detect_face_crop_square(img_path: str) -> Image.Image:
    cv_img = cv2.imread(img_path)
    if cv_img is None:
        raise ValueError(f"Image at path '{img_path}' could not be read.")
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    h_img, w_img = gray.shape
    cascade_path = os.path.join(os.path.dirname(cv2.__file__), 'data', 'haarcascade_frontalface_default.xml')
    face_cascade = cv2.CascadeClassifier(cascade_path)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))
    if len(faces) > 0:
        x, y, w, h = max(faces, key=lambda r: r[2]*r[3])
        cx, cy = x + w//2, y + h//2
    else:
        cx, cy = w_img//2, h_img//2
    side = min(w_img, h_img)
    half = side // 2
    left = max(0, min(w_img-side, cx-half))
    top = max(0, min(h_img-side, cy-half))
    pil_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
    return pil_img.crop((left, top, left+side, top+side))

def circular_mask(size: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    return mask

def compose_with_ring(headshot_path: str) -> str:
    """Create a ringed headshot image and write it to AGENT_DIR.

    Returns the path to the saved image as a string.
    """
    head_square = detect_face_crop_square(headshot_path)
    ring = Image.open(str(RING_IMAGE)).convert("RGBA")
    target_size = ring.width
    head_resized = head_square.resize((target_size, target_size), Image.Resampling.LANCZOS)
    mask = circular_mask(target_size)
    head_resized.putalpha(mask)
    canvas = Image.new("RGBA", (target_size, target_size), (0,0,0,0))
    canvas.paste(head_resized, (0,0), head_resized)
    canvas.paste(ring, (0,0), ring)
    output_filename = Path(headshot_path).stem + "_with-ring.png"
    AGENT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = AGENT_DIR / output_filename
    canvas.save(output_file)
    return str(output_file)


def find_headshot(headshot_dir: str, first: str, last: str) -> Optional[str]:
    """Search ``headshot_dir`` for ``firstname-lastname`` with png/jpg extension."""
    base = f"{first.lower()}-{last.lower()}"
    for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
        candidate = os.path.join(headshot_dir, base + ext)
        if os.path.exists(candidate):
            return candidate
    return None

def save_headshot(source, first, last):
    """
    Save headshot from uploaded file path or URL to HEADSHOT_DIR.
    Returns saved path.
    """
    first_l = first.lower()
    last_l = last.lower()
    target_png = HEADSHOT_DIR / f"{first_l}-{last_l}.png"
    # Determine if source is URL or file path
    if isinstance(source, str) and source.startswith("http"):
        r = requests.get(source)
        r.raise_for_status()
        target_png.write_bytes(r.content)
    else:
        # It's a file-like object or path
        if hasattr(source, 'read'):  # Check if source is a file-like object
            with open(target_png, 'wb') as f:
                with open(source, 'rb') as src_file:
                    shutil.copyfileobj(src_file, f)
        else:
            shutil.copy(Path(source), target_png)
    return target_png


def main(first: str, last: str) -> Optional[str]:
    headshot_dir = os.environ.get("HEADSHOT_DIR", "headshots")
    headshot_path = find_headshot(headshot_dir, first, last)
    if not headshot_path:
        print(f"Error: headshot for {first} {last} not found in {headshot_dir}", file=sys.stderr)
        sys.exit(2)
    output_path = compose_with_ring(headshot_path)
    print(f"Ringed image saved to {output_path}")
    return output_path


if __name__ == "__main__":
    main("sean","fallon")