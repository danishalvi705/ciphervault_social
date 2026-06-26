from __future__ import annotations
from typing import Sequence
import matplotlib
import gc
# Force headless rendering
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

# Deep Institutional Dark Palette
BG = "#0a0a0a"
GRID = "#1a1a1a"
TEXT = "#a0a0a0"
UP_COLOR = "#00c853"
DOWN_COLOR = "#ff5252"

def _market_colors(side: str):
    up = UP_COLOR if side == "long" else DOWN_COLOR
    down = DOWN_COLOR if side == "long" else UP_COLOR
    return mpf.make_marketcolors(
        up=up, down=down, 
        edge="inherit", wick="inherit",
        volume="#ffffff05" 
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
    # 1. Data Prep
    df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    df.set_index("ts", inplace=True)

    # 2. Style Config
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
            "font.size": 10,
            "axes.labelcolor": TEXT,
        },
    )

    # 3. Plotting
    fig, axlist = mpf.plot(
        df,
        type="candle",
        style=style,
        hlines=dict(
            hlines=[entry, sl, tp],
            colors=["#2979ff", "#ff5252", "#00c853"],
            linestyle="-",
            linewidths=1.8,
        ),
        volume=False,
        returnfig=True,
        figsize=(width_px / dpi, height_px / dpi),
        tight_layout=True,
    )

    # 4. Clean up "Chart Junk" (Professional Look)
    ax = axlist[0]
    ax.yaxis.set_visible(False) # Hide Y-axis for a clean, widget-like appearance
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # 5. Save and aggressively clear memory
    fig.savefig(output_path, dpi=dpi, facecolor=BG, bbox_inches='tight', pad_inches=0.05)
    
    plt.clf()
    plt.close(fig)
    del fig, axlist, df
    gc.collect()
    
    return output_path
