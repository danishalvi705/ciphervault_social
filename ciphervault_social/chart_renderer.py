from __future__ import annotations
from typing import Sequence
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

# Professional "TradingView-esque" Palette
BG = "#0a0a0a"         # Deep black background
GRID = "#1e1e1e"       # Subtle grid
TEXT = "#b2b5be"       # Muted text
UP_COLOR = "#26a69a"   # Professional Teal
DOWN_COLOR = "#ef5350" # Professional Red

def _market_colors(side: str):
    # If it's a Long, green represents profit-taking, red represents danger
    up = UP_COLOR if side == "long" else DOWN_COLOR
    down = DOWN_COLOR if side == "long" else UP_COLOR
    return mpf.make_marketcolors(
        up=up, down=down, 
        edge="inherit", wick="inherit",
        volume="#26a69a33" # Faded volume if used
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
    dpi: int = 200, # Higher DPI for sharper lines
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
        gridstyle="-", # Solid thin lines look cleaner than dashed
        rc={
            "font.family": "sans-serif", # Sans-serif looks more modern than monospace
            "font.size": 10,
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
            colors=["#58a6ff", "#f85149", "#3fb950"],
            linestyle="-", # Clean solid lines
            linewidths=1.5,
        ),
        volume=False,
        returnfig=True,
        figsize=(width_px / dpi, height_px / dpi),
        tight_layout=True,
    )

    # Aesthetics cleanup: Remove unnecessary borders (spines)
    ax = axlist[0]
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    fig.savefig(output_path, dpi=dpi, facecolor=BG, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return output_path
