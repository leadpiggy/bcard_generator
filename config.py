from pathlib import Path

# Base directories
PROJECT_ROOT = Path(__file__).parent
STATIC_IMG = PROJECT_ROOT / "static/assets/img"
HEADSHOT_DIR = STATIC_IMG / "headshots"
AGENT_DIR = STATIC_IMG / "agents"
QR_DIR = STATIC_IMG / "qrcodes"
BCARD_DIR = STATIC_IMG / "bcards"
CORE_DIR = STATIC_IMG / "core"
TEXT_DIR = STATIC_IMG / "texts"

# Core asset paths
RING_IMAGE = CORE_DIR / "gold-ring.png"
BCARD_BG = CORE_DIR / "bcard-bg.png"
QR_BLANK_SVG = CORE_DIR / "qr-code-blank.svg"

# Font paths
FONT_REGULAR = PROJECT_ROOT / "static/assets/fonts/Montserrat-Regular.ttf"
FONT_SEMIBOLD = PROJECT_ROOT / "static/assets/fonts/Montserrat-SemiBold.ttf"

# Font Colors
FONT_COLOR = (255, 255, 255)  # White
FONT_COLOR_TWO = (237, 220, 158)  # Light Gold

# Positioning tuned for 675x1125 canvas
# Agent ring (centered horizontally near top)
AGENT_POS = (165, 108)
# Desired agent diameter (px) when pasted onto the bcard. Tune to match preview.
AGENT_SIZE = 800
# QR positioned right-of-center lower on card
QR_POS = (336, 761)
# Name box centered under agent; width reduced to fit design
NAME_BOX = (100, 494, 473, 54)
# Phone box under name
# (swapped to match expected layout)
PHONE_BOX = (142, 612, 339, 44)
# Email box below phone, right-bottom alignment will be applied by renderer
EMAIL_BOX = (130, 667, 369, 49)

# Additional layout and rendering constants moved from generate_bcard.py
# Headshot (ring) circle. The centre of the ring sits at (166, 109) with
# a diameter of 335 pixels for the original template.
HEADSHOT_POS = (166, 109)
HEADSHOT_SIZE = 335

# QR code bounding box (x, y, width, height). The pre-generated QR
# image will be resized to fit within this area.
QR_BOX = (337, 762, 238, 238)

# Colours for the text. Dots in phone numbers and email addresses use
# a pale gold colour while all other characters are white.
COLOUR_WHITE = "#FFFFFF"
COLOUR_DOT = "#EDDC9E"

# Character spacing for the text. Expressed in pixels at the final scaled size.
DEFAULT_TRACKING = 2