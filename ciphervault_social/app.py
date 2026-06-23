from __future__ import annotations
import os
import logging
import traceback
import gc
import asyncio  # Added for Semaphore
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx

# Import your custom modules
from chart_renderer import render_signal_chart
from frame_composer import compose_frame
from video_synth import synthesize_short

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ciphervault-social-render")

# Load Configuration
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Ensure temp directory exists
VIDEO_DIR = Path("/tmp/videos")
VIDEO_DIR.mkdir(exist_ok=True)

# --- CRITICAL: Concurrency Control ---
# This ensures only ONE rendering task runs at a time, 
# preventing the OOM crashes caused by concurrent resource usage.
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
    # Acquire the lock. If another render is running, this waits here.
    async with render_semaphore:
        chart_png = VIDEO_DIR / f"{signal.id}_chart.png"
        frame_png = VIDEO_DIR / f"{signal.id}_frame.png"
        video_path = VIDEO_DIR / f"{signal.id}.mp4"

        try:
            logger.info(f"TASK START: {signal.id}")
            
            # 1. Render Chart
            render_signal_chart(ohlcv, signal.symbol, signal.side, signal.entry, signal.sl, signal.tp, str(chart_png))
            gc.collect()
            logger.info("Rendered Chart")

            # 2. Compose Frame
            compose_frame(str(chart_png), signal.symbol, signal.side, signal.entry, signal.sl, signal.tp, signal.rr, signal.score, str(frame_png))
            gc.collect()
            logger.info("Composed Frame")

            # 3. Synthesize Video
            synthesize_short(str(frame_png), str(video_path))
            gc.collect()
            logger.info("Synthesized Video")

            # 4. Send to Telegram
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                async with httpx.AsyncClient() as client:
                    with open(video_path, "rb") as f:
                        await client.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo",
                            data={
                                "chat_id": TELEGRAM_CHAT_ID,
                                "caption": f"🚨 *{signal.symbol}* {signal.side.upper()}\nEntry: `{signal.entry}` | Score: `{signal.score}`",
                                "parse_mode": "Markdown"
                            },
                            files={"video": f},
                            timeout=60
                        )
                logger.info(f"Sent {signal.symbol} to Telegram")

        except Exception as e:
            logger.error(f"CRITICAL ERROR: {e}")
            logger.error(traceback.format_exc())
        finally:
            # Cleanup
            for p in [chart_png, frame_png, video_path]:
                if p.exists():
                    p.unlink()
            gc.collect()
            logger.info(f"Cleanup finished for {signal.id}")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/publish")
def publish(req: PublishRequest, background_tasks: BackgroundTasks, x_webhook_secret: str = Header(default="")):
    if not WEBHOOK_SECRET or x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    logger.info(f"Queuing request for {req.signal.symbol}")
    background_tasks.add_task(process_video_task, req.signal, req.ohlcv)
    return {"status": "queued"}
