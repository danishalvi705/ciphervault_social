"""
CipherVault Social — Render Webhook Service
Receives signal + OHLCV data from the DO VPS, does the heavy lifting
(chart render -> frame compose -> video synth -> post to X) entirely on
this machine, isolated from CipherVault's trading engine.

Stateless by design: no rate limiting, no persistent storage. DO already
checked the daily cap before sending the webhook; this service just
processes whatever it's handed.
"""

from __future__ import annotations
import os
import tempfile
import logging
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from chart_renderer import render_signal_chart
from frame_composer import compose_frame
from video_synth import synthesize_short
import twitter_poster

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ciphervault-social-render")

WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

app = FastAPI(title="CipherVault Social Render Service")


class SignalPayload(BaseModel):
    id: str
    symbol: str
    side: str          # "long" | "short"
    entry: float
    sl: float
    tp: float
    rr: float
    score: float | str


class PublishRequest(BaseModel):
    signal: SignalPayload
    ohlcv: list[list[float]]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/publish")
def publish(req: PublishRequest, x_webhook_secret: str = Header(default="")):
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    signal = req.signal
    logger.info(f"Received publish request for {signal.symbol} ({signal.id})")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            chart_png = render_signal_chart(
                req.ohlcv, signal.symbol, signal.side,
                signal.entry, signal.sl, signal.tp,
                str(Path(tmp) / "chart.png"),
            )
            frame_png = compose_frame(
                chart_png, signal.symbol, signal.side,
                signal.entry, signal.sl, signal.tp,
                signal.rr, signal.score,
                str(Path(tmp) / "frame.png"),
            )
            video_path = synthesize_short(frame_png, str(Path(tmp) / "short.mp4"))

            caption = (
                f"{signal.symbol} {signal.side.upper()} \u00b7 Entry {signal.entry} "
                f"\u00b7 R:R {signal.rr:.2f} \u00b7 #CipherVault \u2014 not financial advice."
            )
            twitter_poster.post_video(video_path, caption, signal.id)

        logger.info(f"Published {signal.symbol} ({signal.id}) successfully")
        return {"status": "published", "signal_id": signal.id}

    except Exception as e:
        logger.error(f"Failed to publish {signal.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
