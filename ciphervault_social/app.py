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
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 

VIDEO_DIR = Path("/tmp/videos")
VIDEO_DIR.mkdir(exist_ok=True)
render_semaphore = asyncio.Semaphore(1)

app = FastAPI(title="CipherVault Social Render Service")
telegram_app = None # Global variable to store the bot instance

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
async def process_video_task(signal: SignalPayload | None, chat_id: int | None = None):
    """Captures dashboard and sends it to Telegram."""
    signal_id = signal.id if signal else "manual"
    video_path = VIDEO_DIR / f"{signal_id}.mp4"
    
    async with render_semaphore:
        try:
            logger.info("DEBUG: Launching full-viewport browser capture...")
            await capture_signal_video("http://168.144.131.132:8000/", str(video_path))
            
            # Ensure the file exists before sending
            if not video_path.exists():
                raise FileNotFoundError("Video recording failed to generate file.")

            # Send to Telegram using the native library
            if telegram_app and telegram_app.bot:
                target_chat = chat_id or TELEGRAM_CHAT_ID
                caption = f"🚨 *{signal.symbol}* {signal.side.upper()}\nScore: `{signal.score}`" if signal else "Snapshot requested."
                
                # Using the native send_video method (Fixes 400 Bad Request error)
                with open(video_path, "rb") as video_file:
                    await telegram_app.bot.send_video(
                        chat_id=target_chat,
                        video=video_file,
                        caption=caption,
                        parse_mode="Markdown"
                    )
                logger.info("Video successfully sent to Telegram.")
        
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
    await process_video_task(None, chat_id=update.effective_chat.id)

@app.on_event("startup")
async def startup():
    global telegram_app
    if TELEGRAM_BOT_TOKEN:
        telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        telegram_app.add_handler(CommandHandler("snap", start_snap))
        await telegram_app.initialize()
        
        if WEBHOOK_URL:
            async with httpx.AsyncClient() as client:
                await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}/telegram-webhook")
        
        logger.info("Telegram Bot Initialized.")

# --- Endpoints ---

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    global telegram_app
    if not telegram_app:
        return {"status": "error", "message": "Bot not initialized"}
    
    # Process update using the initialized application
    update = Update.de_json(await request.json(), telegram_app.bot)
    await telegram_app.process_update(update)
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
