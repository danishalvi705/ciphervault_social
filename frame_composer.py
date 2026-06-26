from __future__ import annotations
from pathlib import Path
import matplotlib
from PIL import Image, ImageDraw, ImageFont
import gc

CANVAS_W, CANVAS_H = 1080, 1920
# Deep Institutional Dark Palette
BG = (10, 10, 10)
PANEL = (18, 18, 18)
TEXT_MAIN = (230, 237, 243)
TEXT_GREY = (140, 140, 140)
ACCENT_BLUE = (41, 121, 255)
GREEN = (0, 200, 83)
RED = (255, 82, 82)

_MPL_FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
FONT_PATH = str(_MPL_FONT_DIR / "DejaVuSans-Bold.ttf")

# Cache fonts to save RAM
_FONT_CACHE = {}

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = ImageFont.truetype(FONT_PATH, size)
        except:
            _FONT_CACHE[size] = ImageFont.load_default()
    return _FONT_CACHE[size]

def _fmt_price(v: float) -> str:
    return f"{v:,.2f}" if v >= 100 else f"{v:,.4f}"

def compose_frame(
    chart_path: str, symbol: str, side: str, entry: float, sl: float, tp: float, rr: float, score, output_path: str
) -> str:
    # 1. Canvas setup
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    draw = ImageDraw.Draw(canvas)
    side_color = GREEN if side == "long" else RED

    # 2. Header (Branding)
    draw.rectangle([0, 0, CANVAS_W, 250], fill=PANEL)
    draw.rectangle([0, 0, 12, 250], fill=side_color) # Accent bar
    draw.text((50, 60), "CIPHERVAULT", font=_load_font(48), fill=ACCENT_BLUE)
    draw.text((50, 130), f"{symbol}  |  {side.upper()}", font=_load_font(52), fill=TEXT_MAIN)
    draw.text((50, 190), f"CONFIDENCE SCORE: {score}", font=_load_font(32), fill=TEXT_GREY)

    # 3. Chart
    chart = Image.open(chart_path).convert("RGB").resize((CANVAS_W, 1000))
    canvas.paste(chart, (0, 250))

    # 4. Footer (Stats Card)
    draw.rectangle([0, 1250, CANVAS_W, CANVAS_H], fill=PANEL)
    stats = [("ENTRY", entry), ("SL", sl), ("TP", tp)]
    for i, (label, val) in enumerate(stats):
        x = 60 + (i * 340)
        draw.text((x, 1310), label, font=_load_font(30), fill=TEXT_GREY)
        draw.text((x, 1360), _fmt_price(val), font=_load_font(46), fill=TEXT_MAIN)

    draw.text((60, 1490), "RISK:REWARD RATIO", font=_load_font(30), fill=TEXT_GREY)
    draw.text((60, 1540), f"{rr:.2f}", font=_load_font(46), fill=ACCENT_BLUE)
    
    # Disclaimer
    draw.text((60, CANVAS_H - 100), "NOT FINANCIAL ADVICE. FOR EDUCATIONAL PURPOSES ONLY.", font=_load_font(24), fill=TEXT_GREY)

    # 5. Save and Cleanup
    canvas.save(output_path)
    
    # Explicitly clear objects to free memory
    del canvas, draw, chart
    gc.collect()
    
    return output_path
