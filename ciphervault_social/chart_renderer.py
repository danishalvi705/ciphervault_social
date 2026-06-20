"""
CipherVault Social — Chart Renderer
Generates a branded candlestick PNG for a signal, styled to match the
dashboard's terminal-dark theme (dark background, monospace font).
"""

from __future__ import annotations
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

BG = "#0d1117"
PANEL = "#161b22"
GREEN = "#3fb950"
RED = "#f85149"
BLUE = "#58a6ff"


def _market_colors(side: str):
    up = GREEN if side == "long" else RED
    down = RED if side == "long" else GREEN
    return mpf.make_marketcolors(up=up, down=down, edge="inherit", wick="inherit")


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
    dpi: int = 150,
) -> str:
    """
    ohlcv: ccxt-style rows [ts_ms, open, high, low, close, volume].
    Reuse whatever candle window you already pull for entry-touch checks —
    no need for a second exchange call here.
    """
    df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    df.set_index("ts", inplace=True)

    style = mpf.make_mpf_style(
        base_mpl_style="dark_background",
        marketcolors=_market_colors(side),
        facecolor=BG,
        figcolor=BG,
        gridcolor=PANEL,
        gridstyle="--",
        rc={"font.family": "monospace", "font.size": 11},
    )

    fig, _ = mpf.plot(
        df,
        type="candle",
        style=style,
        hlines=dict(
            hlines=[entry, sl, tp],
            colors=[BLUE, RED, GREEN],
            linestyle="--",
            linewidths=1.2,
        ),
        volume=False,
        returnfig=True,
        figsize=(width_px / dpi, height_px / dpi),
        tight_layout=True,
    )
    fig.savefig(output_path, dpi=dpi, facecolor=BG)
    plt.close(fig)
    return output_path
