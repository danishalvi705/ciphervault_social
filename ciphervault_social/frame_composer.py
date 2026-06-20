"""
CipherVault Social — Frame Composer
Composites the rendered chart onto a full 1080x1920 (9:16) canvas with
branded header/footer text. Pure Pillow — deliberately avoids ImageMagick,
since TextClip's ImageMagick dependency is a common source of headless-server
breakage (policy.xml blocking text rendering by default on Ubuntu).
"""

from __future__ import annotations
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageFont

CANVAS_W, CANVAS_H = 1080, 1920
BG = (13, 17, 23)
PANEL = (22, 27, 34)
GREEN = (63, 185, 80)
RED = (248, 81, 73)
BLUE = (88, 166, 255)
GREY = (139, 148, 158)
WHITE = (230, 237, 243)

# Prefer JetBrains Mono (matches the dashboard); fall back to the
# DejaVu Sans Mono that ships inside matplotlib so this never hard-fails
# on a fresh server with no extra fonts installed.
_MPL_FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
FONT_PATH_CANDIDATES = [
    "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
    str(_MPL_FONT_DIR / "DejaVuSansMono-Bold.ttf"),
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATH_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _fmt_price(v: float) -> str:
    if v >= 100:
        return f"{v:,.2f}"
    if v >= 1:
        return f"{v:,.4f}"
    return f"{v:.6f}"


def compose_frame(
    chart_path: str,
    symbol: str,
    side: str,
    entry: float,
    sl: float,
    tp: float,
    rr: float,
    score,
    output_path: str,
) -> str:
    header_h, chart_h, gap = 220, 1000, 40
    chart_y = header_h + gap
    footer_y = chart_y + chart_h

    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    draw = ImageDraw.Draw(canvas)

    # Header
    draw.rectangle([0, 0, CANVAS_W, header_h], fill=PANEL)
    side_color = GREEN if side == "long" else RED
    draw.text((40, 28), "CIPHERVAULT", font=_load_font(44), fill=BLUE)
    draw.text((40, 92), symbol, font=_load_font(62), fill=WHITE)
    draw.text((40, 162), f"{side.upper()}  ·  SCORE {score}", font=_load_font(32), fill=side_color)

    # Chart
    chart = Image.open(chart_path).convert("RGB").resize((CANVAS_W, chart_h))
    canvas.paste(chart, (0, chart_y))

    # Footer
    draw.rectangle([0, footer_y, CANVAS_W, CANVAS_H], fill=PANEL)
    font_label, font_value = _load_font(28), _load_font(38)
    for i, (label, value, color) in enumerate(
        [("ENTRY", entry, BLUE), ("SL", sl, RED), ("TP", tp, GREEN)]
    ):
        x = i * (CANVAS_W // 3) + 40
        draw.text((x, footer_y + 30), label, font=font_label, fill=GREY)
        draw.text((x, footer_y + 68), _fmt_price(value), font=font_value, fill=color)

    draw.text((40, footer_y + 140), f"R:R   {rr:.2f}", font=font_value, fill=WHITE)
    draw.text(
        (40, CANVAS_H - 50),
        "Not financial advice — for educational purposes only.",
        font=_load_font(22),
        fill=GREY,
    )

    canvas.save(output_path)
    return output_path
