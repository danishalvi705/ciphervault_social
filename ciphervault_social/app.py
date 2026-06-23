from __future__ import annotations
import os
import logging
import traceback
import gc
import asyncio
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx

# Imports for Legacy Rendering
from chart_renderer import render_signal_chart
from frame_composer import compose_frame
from video_synth import synthesize_short

# Import for new Snap Method
from recorder import capture_signal_video

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ciphervault-social-render")

# --- Settings ---
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RENDER_METHOD = os.environ.get("RENDER_METHOD", "snap") # Switch between 'snap' and 'legacy'

VIDEO_DIR = Path("/tmp/videos")
VIDEO_DIR.mkdir(exist_ok=True)
render_semaphore = asyncio.Semaphore(1)

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

async def process_video_task(signal: SignalPayload, ohlcv: list[list[float]]):
    async with render_semaphore:
        video_path = VIDEO_DIR / f"{signal.id}.mp4"
        try:
            if RENDER_METHOD == "legacy":
                # --- LEGACY MODE ---
                chart_png = VIDEO_DIR / f"{signal.id}_chart.png"
                frame_png = VIDEO_DIR / f"{signal.id}_frame.png"
                render_signal_chart(ohlcv, signal.symbol, signal.side, signal.entry, signal.sl, signal.tp, str(chart_png))
                compose_frame(str(chart_png), signal.symbol, signal.side, signal.entry, signal.sl, signal.tp, signal.rr, signal.score, str(frame_png))
                synthesize_short(str(frame_png), str(video_path))
                # Cleanup
                for p in [chart_png, frame_png]:
                    if p.exists(): p.unlink()
            else:
                # --- SNAP MODE (Updated to external IP) ---
                await capture_signal_video(
                    dashboard_url="http://168.144.131.132:8000/", 
                    selector=".signal-card-active", 
                    output_path=str(video_path)
                )

            # Send to Telegram
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                async with httpx.AsyncClient() as client:
                    with open(video_path, "rb") as f:
                        await client.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo",
                            data={
                                "chat_id": TELEGRAM_CHAT_ID,
                                "caption": f"🚨 *{signal.symbol}* {signal.side.upper()}\nScore: `{signal.score}`",
                                "parse_mode": "Markdown"
                            },
                            files={"video": f},
                            timeout=60
                        )
        except Exception as e:
            logger.error(f"TASK ERROR: {e}")
        finally:
            if video_path.exists(): video_path.unlink()
            gc.collect()

@app.post("/publish")
def publish(req: PublishRequest, background_tasks: BackgroundTasks, x_webhook_secret: str = Header(default="")):
    if not WEBHOOK_SECRET or x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    # --- FILTERING LOGIC ---
    try:
        if float(req.signal.score) < 4.0:
            logger.info(f"Skipping {req.signal.symbol} - Score {req.signal.score} too low.")
            return {"status": "ignored"}
    except:
        return {"status": "ignored"} # Skip if score is unreadable

    logger.info(f"Queuing {req.signal.symbol} (Score: {req.signal.score})")
    background_tasks.add_task(process_video_task, req.signal, req.ohlcv)
    return {"status": "queued"}
