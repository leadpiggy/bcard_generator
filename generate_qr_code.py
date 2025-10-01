import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image
from qrcode.image.styles.moduledrawers import CircleModuleDrawer
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import CircleModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import ImageDraw, ImageColor
from pathlib import Path
from config import QR_DIR

class PaddedDotDrawer(CircleModuleDrawer):
    """
    Draws each active module as an inset circle to create a 'dot' effect.
    """
    def __init__(self, padding=0.15):
        super().__init__()
        self.padding = padding  # fraction of cell to inset

    def drawrect_context(self, box, is_active, context):
        if not is_active:
            return
        (x1, y1), (x2, y2) = box
        w = x2 - x1
        inset = w * self.padding
        draw = ImageDraw.Draw(context.image)
        draw.ellipse(
            (x1 + inset, y1 + inset, x2 - inset, y2 - inset),
            fill=context.paint_color
        )

def generate_qr_code(first: str, last: str) -> str:
    # 1. Define the URL for the QR code
    url = f"https://thebenefitsboss.com/{first.lower()}-{last.lower()}-booking"

    # 2. Configure the QRCode object
    qr = qrcode.QRCode(
        version=None,                # Automatically determine size
        error_correction=ERROR_CORRECT_H,
        box_size=10,                 # Each module will be 10x10 pixels
        border=4                     # 4-module quiet zone
    )
    qr.add_data(url)
    qr.make(fit=True)

    # 3. Generate the image
    #    `make_image` returns a PIL Image, so no conversion is needed
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=PaddedDotDrawer(padding=0.15),
        color_mask=SolidFillColorMask(
            back_color=ImageColor.getrgb("#FFFABF"),
            front_color=ImageColor.getrgb("#000000")
        )
    )
    # 4. Save to disk in QR_DIR with a deterministic filename
    QR_DIR.mkdir(parents=True, exist_ok=True)
    output_path = QR_DIR / f"{first.lower()}-{last.lower()}-qr.png"
    # Save with file handle to maintain static analysis compatibility
    with open(output_path, 'wb') as f:
        img.save(f, 'PNG')

    print(f"✅ Saved functional QR to {output_path}")
    return str(output_path)