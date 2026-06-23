from __future__ import annotations
from pathlib import Path
import matplotlib
from PIL import Image, ImageDraw, ImageFont

CANVAS_W, CANVAS_H = 1080, 1920
# Deep Institutional Dark Palette
BG = (10, 10, 10)           # Near Black
PANEL = (18, 18, 18)        # Slight separation
TEXT_MAIN = (230, 237, 243) # Off-White
TEXT_GREY = (140, 140, 140) # Muted text
ACCENT_BLUE = (41, 121, 255)
GREEN = (0, 200, 83)        # Institutional Green
RED = (255, 82, 82)         # Institutional Red

_MPL_FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
FONT_PATH = str(_MPL_FONT_DIR / "DejaVuSans-Bold.ttf") # Using standard fonts for stability

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()

def _fmt_price(v: float) -> str:
    return f"{v:,.2f}" if v >= 100 else f"{v:,.4f}"

def compose_frame(
    chart_path: str, symbol: str, side: str, entry: float, sl: float, tp: float, rr: float, score, output_path: str
) -> str:
    # Layout Config
    header_h, footer_h = 250, 450
    chart_h = 1000
    
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    draw = ImageDraw.Draw(canvas)
    side_color = GREEN if side == "long" else RED

    # 1. Header (Branding)
    draw.rectangle([0, 0, CANVAS_W, header_h], fill=PANEL)
    draw.rectangle([0, 0, 12, header_h], fill=side_color) # The "Signal" Accent Bar
    
    draw.text((50, 60), "CIPHERVAULT", font=_load_font(48), fill=ACCENT_BLUE)
    draw.text((50, 130), f"{symbol}  |  {side.upper()}", font=_load_font(52), fill=TEXT_MAIN)
    draw.text((50, 190), f"CONFIDENCE SCORE: {score}", font=_load_font(32), fill=TEXT_GREY)

    # 2. Chart (Paste with clean padding)
    chart = Image.open(chart_path).convert("RGB").resize((CANVAS_W, chart_h))
    canvas.paste(chart, (0, header_h))

    # 3. Footer (Stats Card)
    footer_y = header_h + chart_h
    draw.rectangle([0, footer_y, CANVAS_W, CANVAS_H], fill=PANEL)
    
    # Layout Stats
    stats = [("ENTRY", entry), ("SL", sl), ("TP", tp)]
    for i, (label, val) in enumerate(stats):
        x = 60 + (i * 340)
        draw.text((x, footer_y + 60), label, font=_load_font(30), fill=TEXT_GREY)
        draw.text((x, footer_y + 110), _fmt_price(val), font=_load_font(46), fill=TEXT_MAIN)

    # R:R and Disclaimer
    draw.text((60, footer_y + 240), f"RISK:REWARD RATIO", font=_load_font(30), fill=TEXT_GREY)
    draw.text((60, footer_y + 290), f"{rr:.2f}", font=_load_font(46), fill=ACCENT_BLUE)
    
    draw.text((60, CANVAS_H - 80), "NOT FINANCIAL ADVICE. FOR EDUCATIONAL PURPOSES ONLY.", font=_load_font(24), fill=TEXT_GREY)

    canvas.save(output_path)
    return output_path
