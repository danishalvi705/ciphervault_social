"""
CipherVault Social — Render Webhook Service
Receives signal + OHLCV data from the DO VPS, generates a video,
saves it, and sends it to Telegram for manual download and posting.
"""

from __future__ import annotations
import os
import logging
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from chart_renderer import render_signal_chart
from frame_composer import compose_frame
from video_synth import synthesize_short

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ciphervault-social-render")

WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

VIDEO_DIR = Path("/tmp/videos")
VIDEO_DIR.mkdir(exist_ok=True)

app = FastAPI(title="CipherVault Social Render Service")


class SignalPayload(BaseModel):
    id: str
    symbol: str
    side: str
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


@app.get("/video/{filename}")
def download_video(filename: str):
    path = VIDEO_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path, media_type="video/mp4", filename=filename)


@app.post("/publish")
def publish(req: PublishRequest, x_webhook_secret: str = Header(default="")):
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    signal = req.signal
    logger.info(f"Received publish request for {signal.symbol} ({signal.id})")

    try:
        chart_png = str(VIDEO_DIR / f"{signal.id}_chart.png")
        frame_png = str(VIDEO_DIR / f"{signal.id}_frame.png")
        video_path = str(VIDEO_DIR / f"{signal.id}.mp4")

        render_signal_chart(
            req.ohlcv, signal.symbol, signal.side,
            signal.entry, signal.sl, signal.tp,
            chart_png,
        )
        compose_frame(
            chart_png, signal.symbol, signal.side,
            signal.entry, signal.sl, signal.tp,
            signal.rr, signal.score,
            frame_png,
        )
        synthesize_short(frame_png, video_path)

        # Send to Telegram
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            caption = (
                f"🚨 *{signal.symbol}* {signal.side.upper()}\n"
                f"Entry: `{signal.entry}` | SL: `{signal.sl}` | TP: `{signal.tp}`\n"
                f"R:R: `{signal.rr:.2f}` | Score: `{signal.score}`\n"
                f"#CipherVault"
            )
            with open(video_path, "rb") as f:
                httpx.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo",
                    data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"},
                    files={"video": f},
                    timeout=60,
                )
            logger.info(f"Sent {signal.symbol} video to Telegram")

        logger.info(f"Published {signal.symbol} ({signal.id}) successfully")
        return {"status": "published", "signal_id": signal.id, "video": f"{signal.id}.mp4"}

    except Exception as e:
        logger.error(f"Failed to publish {signal.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
