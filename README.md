Business Card Generator
=======================

This repository contains a small pipeline for generating personalized business cards from assets and simple inputs (first name, last name, phone). It composes a ringed headshot, generates a QR code, renders high-resolution text assets (name/phone/email) to PNGs, scales them to template guide boxes, and assembles a final business card image.

Files of interest

- `config.py` — central configuration (paths, bounding boxes, fonts and colors).
- `generate_agent_image.py` — creates a ringed headshot; detects/crops faces, masks to circle, overlays a ring, and writes into `static/assets/img/agents`.
- `generate_qr_code.py` — creates a styled QR code and writes into `static/assets/img/qrcodes`.
- `generate_texts.py` — renders the name, phone and email into high-resolution PNGs (transparent background) and saves into `static/assets/img/texts`.
- `generate_bcard.py` — orchestrator and assembler. It calls the other modules, scales and pastes assets into the template, and writes the final business card image into `static/assets/img/bcards`.

Requirements

-----------

Install the Python dependencies into a virtual environment. A minimal `requirements.txt` is provided.

On macOS / zsh (example):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Usage

-----------

Prepare assets (or use the demo assets already present in `static/assets/img`):

- Place agent headshots in `static/assets/img/headshots` with filenames like `first-last.png` lowercased.
- Ensure `static/assets/img/core/gold-ring.png` and `static/assets/img/core/bcard-bg.png` exist.
- Make sure fonts referenced in `config.py` exist (e.g. `static/assets/fonts/Montserrat-SemiBold.ttf`).

Run the quick demo to generate Sean Fallon's card:

```bash
python generate_bcard.py Sean Fallon "(801) 836-6758"
```

This will:

1. Compose a ringed headshot and write it to `static/assets/img/agents/`.
2. Generate a QR image to `static/assets/img/qrcodes/{first-last}-qr.png`.
3. Render text PNGs into `static/assets/img/texts/` (name, phone, email).
4. Scale and paste all assets onto the background template and write the final card to `static/assets/img/bcards/{first-last}-bcard.jpg`.

CUSTOMIZATION & advanced usage

-----------

- Provide a headshot URL or path with `--headshot` to have the pipeline fetch/save it before generating.
- Adjust bounding boxes and positions inside `config.py` to fit other templates.
- Switch output format by passing a `.png` output filename or changing the final save behavior in `generate_bcard.py`.

Notes

-----------

- The text rendering strategy: generate a high-resolution text PNG for crisp scaling. The pipeline then scales those PNGs to exactly match template box sizes — phone numbers are stretched to exactly fill their box, while name and email preserve aspect ratio and center within their boxes.
- The repository uses a small OpenCV face detector (bundled with opencv-python) when composing the headshot. If OpenCV fails to find a face the headshot is center-cropped.

Troubleshooting

-----------

- If you see `ModuleNotFoundError` for `qrcode` or `opencv`, ensure you installed the packages into the active Python env.
- If fonts or core images are missing, place the correct files under `static/assets/fonts` and `static/assets/img/core` respectively.
