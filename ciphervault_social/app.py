from __future__ import annotations
import os
import logging
import traceback
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

if not WEBHOOK_SECRET:
    logger.error("WARNING: WEBHOOK_SECRET is not set in Environment Variables!")

# Ensure temp directory exists
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

# --- Background Task (The heavy lifting) ---
async def process_video_task(signal: SignalPayload, ohlcv: list[list[float]]):
    chart_png = VIDEO_DIR / f"{signal.id}_chart.png"
    frame_png = VIDEO_DIR / f"{signal.id}_frame.png"
    video_path = VIDEO_DIR / f"{signal.id}.mp4"
    
    try:
        logger.info(f"Starting background synthesis for {signal.id}")
        
        # 1. Generate Assets
        render_signal_chart(ohlcv, signal.symbol, signal.side, signal.entry, signal.sl, signal.tp, str(chart_png))
        compose_frame(str(chart_png), signal.symbol, signal.side, signal.entry, signal.sl, signal.tp, signal.rr, signal.score, str(frame_png))
        synthesize_short(str(frame_png), str(video_path))

        # 2. Send to Telegram
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            caption = (
                f"🚨 *{signal.symbol}* {signal.side.upper()}\n"
                f"Entry: `{signal.entry}` | SL: `{signal.sl}` | TP: `{signal.tp}`\n"
                f"R:R: `{signal.rr:.2f}` | Score: `{signal.score}`"
            )
            
            async with httpx.AsyncClient() as client:
                with open(video_path, "rb") as f:
                    await client.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo",
                        data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"},
                        files={"video": f},
                        timeout=60
                    )
            logger.info(f"Sent {signal.symbol} to Telegram successfully")
        else:
            logger.warning("Telegram credentials missing, skipping upload.")

    except Exception as e:
        logger.error(f"Critical error in background task: {e}")
        logger.error(traceback.format_exc())

    finally:
        # 3. CRITICAL: Cleanup temp files to prevent OOM / Disk Full
        for p in [chart_png, frame_png, video_path]:
            if p.exists():
                p.unlink()
                logger.info(f"Cleaned up {p.name}")

# --- API Routes ---

@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/publish")
def publish(req: PublishRequest, background_tasks: BackgroundTasks, x_webhook_secret: str = Header(default="")):
    # Verify Secret
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    logger.info(f"Queuing publish request for {req.signal.symbol} ({req.signal.id})")
    
    # Offload work to background
    background_tasks.add_task(process_video_task, req.signal, req.ohlcv)
    
    return {"status": "queued", "signal_id": req.signal.id}
