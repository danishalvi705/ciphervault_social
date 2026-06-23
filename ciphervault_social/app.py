from __future__ import annotations
import os
import logging
import traceback
import gc
import asyncio
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
import httpx
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Import for the new reliable Recorder
from recorder import capture_signal_video

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ciphervault-social-render")

# --- Settings ---
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # e.g., https://your-app.onrender.com

VIDEO_DIR = Path("/tmp/videos")
VIDEO_DIR.mkdir(exist_ok=True)
render_semaphore = asyncio.Semaphore(1)

app = FastAPI(title="CipherVault Social Render Service")
bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None

# --- Models ---
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

# --- Core Capture Logic ---
async def process_video_task(signal: SignalPayload, chat_id: int | None = None):
    """Captures dashboard and optionally sends to Telegram."""
    video_path = VIDEO_DIR / f"{signal.id if signal else 'manual'}.mp4"
    
    async with render_semaphore:
        try:
            logger.info("DEBUG: Launching full-viewport browser capture...")
            await capture_signal_video("http://168.144.131.132:8000/", str(video_path))
            
            # Send to Telegram
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                target_chat = chat_id or TELEGRAM_CHAT_ID
                async with httpx.AsyncClient() as client:
                    with open(video_path, "rb") as f:
                        await client.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo",
                            data={
                                "chat_id": target_chat,
                                "caption": f"🚨 *{signal.symbol}* {signal.side.upper()}\nScore: `{signal.score}`" if signal else "Snapshot requested.",
                                "parse_mode": "Markdown"
                            },
                            files={"video": f},
                            timeout=60
                        )
        except Exception as e:
            logger.error(f"CRITICAL TASK ERROR: {e}")
            logger.error(traceback.format_exc())
        finally:
            if video_path.exists(): 
                video_path.unlink()
            gc.collect()

# --- Telegram Bot Handler ---
async def start_snap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Recording dashboard... 10 seconds.")
    # We pass None for signal payload since this is a manual snap
    await process_video_task(None, chat_id=update.effective_chat.id)

@app.on_event("startup")
async def startup():
    if TELEGRAM_BOT_TOKEN and WEBHOOK_URL:
        # Set the webhook automatically on startup
        async with httpx.AsyncClient() as client:
            await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}/telegram-webhook")

# --- Endpoints ---

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    bot_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("snap", start_snap))
    
    update = Update.de_json(await request.json(), bot)
    await bot_app.process_update(update)
    return {"status": "ok"}

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
