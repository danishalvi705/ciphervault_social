from __future__ import annotations
import os
import logging
import traceback
import gc
import asyncio
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx

# Import for the new reliable Recorder
from recorder import capture_signal_video

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ciphervault-social-render")

# --- Settings ---
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

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

# --- The New Reliable Capture Task ---
async def process_video_task(signal: SignalPayload, is_manual: bool = False):
    logger.info(f"DEBUG: Starting task for {signal.id if signal else 'Manual Snap'}")
    async with render_semaphore:
        video_path = VIDEO_DIR / f"{signal.id if signal else 'manual'}.mp4"
        try:
            logger.info("DEBUG: Launching full-viewport browser capture...")
            # Using the new clean method: No selectors, just full screen capture
            await capture_signal_video(
                dashboard_url="http://168.144.131.132:8000/", 
                output_path=str(video_path)
            )
            logger.info("DEBUG: Capture call completed successfully.")
            
            # Send to Telegram only if it was an automatic signal (not a manual snap)
            if not is_manual and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
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
            logger.error(f"CRITICAL TASK ERROR: {e}")
            logger.error(traceback.format_exc())
        finally:
            if not is_manual and video_path.exists(): 
                video_path.unlink()
                gc.collect()

# --- Endpoints ---

@app.post("/publish")
def publish(req: PublishRequest, background_tasks: BackgroundTasks, x_webhook_secret: str = Header(default="")):
    if not WEBHOOK_SECRET or x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    try:
        if float(req.signal.score) < 4.0:
            return {"status": "ignored"}
    except:
        return {"status": "ignored"}

    background_tasks.add_task(process_video_task, req.signal)
    return {"status": "queued"}

@app.get("/snap")
async def manual_snap():
    """Trigger this from terminal: curl -o my_video.mp4 https://your-render-url.com/snap"""
    output_path = VIDEO_DIR / "manual_snap.mp4"
    # We await this to ensure the file is ready before returning
    await capture_signal_video("http://168.144.131.132:8000/", str(output_path))
    return FileResponse(path=str(output_path), media_type='video/mp4', filename='manual_snap.mp4')
