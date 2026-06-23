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
from telegram import Update, InputFile
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
telegram_app = None 

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
    """Captures dashboard and sends it to Telegram with explicit parameter handling."""
    signal_id = signal.id if signal else "manual"
    video_path = VIDEO_DIR / f"{signal_id}.mp4"
    
    async with render_semaphore:
        try:
            logger.info(f"DEBUG: Starting capture for {signal_id}...")
            await capture_signal_video("http://168.144.131.132:8000/", str(video_path))
            
            if not video_path.exists() or video_path.stat().st_size == 0:
                raise FileNotFoundError("Recorder finished, but no video file was found or it is empty.")

            if telegram_app and telegram_app.bot:
                target_chat = int(chat_id or TELEGRAM_CHAT_ID)
                
                # Build the caption ONLY if signal exists
                caption = None
                if signal:
                    caption = f"SIGNAL: {str(signal.symbol).replace('_', '-')} {str(signal.side).upper()}\nScore: {signal.score}"
                
                logger.info(f"DEBUG: Sending file to {target_chat}")

                # Build arguments for send_video
                # We use a dictionary to only pass 'caption' if it is not None/Empty
                send_args = {
                    "chat_id": target_chat,
                    "video": open(video_path, "rb")
                }
                
                if caption and len(caption.strip()) > 0:
                    send_args["caption"] = caption
                    send_args["parse_mode"] = None # Avoid markdown parsing issues entirely

                # Send
                try:
                    await telegram_app.bot.send_video(**send_args)
                    logger.info("Video successfully sent to Telegram.")
                finally:
                    # Close the file manually since we opened it via open()
                    if "video" in send_args:
                        send_args["video"].close()

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
