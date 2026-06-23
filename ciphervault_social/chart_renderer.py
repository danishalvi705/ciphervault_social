from __future__ import annotations
from typing import Sequence
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

# Professional "Modern Dark" Palette
BG = "#0a0a0a"         # Pitch black (looks better on mobile screens)
GRID = "#1a1a1a"       # Very subtle grid lines
TEXT = "#a0a0a0"       # Neutral gray text
UP_COLOR = "#00c853"   # Vivid, clean green
DOWN_COLOR = "#ff5252" # Vivid, clean red

def _market_colors(side: str):
    up = UP_COLOR if side == "long" else DOWN_COLOR
    down = DOWN_COLOR if side == "long" else UP_COLOR
    return mpf.make_marketcolors(
        up=up, down=down, 
        edge="inherit", wick="inherit",
        volume="#ffffff05" # Keep volume noise extremely low
    )

def render_signal_chart(
    ohlcv: Sequence[Sequence[float]],
    symbol: str,
    side: str,
    entry: float,
    sl: float,
    tp: float,
    output_path: str,
    width_px: int = 1080,
    height_px: int = 1000,
    dpi: int = 200, 
) -> str:
    df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    df.set_index("ts", inplace=True)

    # Professional Style Config
    mc = _market_colors(side)
    style = mpf.make_mpf_style(
        base_mpl_style="dark_background",
        marketcolors=mc,
        facecolor=BG,
        figcolor=BG,
        gridcolor=GRID,
        gridstyle="-", 
        rc={
            "font.family": "sans-serif", 
            "font.size": 11,
            "axes.labelcolor": TEXT,
            "xtick.color": TEXT,
            "ytick.color": TEXT,
        },
    )

    # Create the plot
    fig, axlist = mpf.plot(
        df,
        type="candle",
        style=style,
        hlines=dict(
            hlines=[entry, sl, tp],
            colors=["#2979ff", "#ff5252", "#00c853"], # Blue (Entry), Red (SL), Green (TP)
            linestyle="-", 
            linewidths=1.5,
        ),
        volume=False,
        returnfig=True,
        figsize=(width_px / dpi, height_px / dpi),
        tight_layout=True,
    )

    # Strip away chart junk
    ax = axlist[0]
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    fig.savefig(output_path, dpi=dpi, facecolor=BG, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return output_path
