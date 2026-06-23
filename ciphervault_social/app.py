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

# Import the recorder
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
    """Captures dashboard and sends it to Telegram with InputFile and strict arg handling."""
    signal_id = signal.id if signal else "manual"
    video_path = VIDEO_DIR / f"{signal_id}.mp4"
    
    async with render_semaphore:
        try:
            logger.info(f"DEBUG: Starting capture for {signal_id}...")
            await capture_signal_video("http://168.144.131.132:8000/", str(video_path))
            
            # File Validation
            if not video_path.exists():
                raise FileNotFoundError("Recorder finished, but no video file was found.")
            if video_path.stat().st_size < 1000:
                raise ValueError(f"Video file is corrupted/too small: {video_path.stat().st_size} bytes.")

            if telegram_app and telegram_app.bot:
                target_chat = int(chat_id or TELEGRAM_CHAT_ID)
                
                # Build Send Arguments
                # Using InputFile() is the standard for v20+ to ensure multipart/form-data encoding
                with open(video_path, "rb") as video_file:
                    send_args = {
                        "chat_id": target_chat,
                        "video": InputFile(video_file)
                    }
                    
                    # Only add caption if it is non-empty
                    if signal:
                        caption = f"SIGNAL: {str(signal.symbol).replace('_', '-')} {str(signal.side).upper()}\nScore: {signal.score}"
                        if caption.strip():
                            send_args["caption"] = caption

                    logger.info(f"DEBUG: Attempting send_video with keys: {list(send_args.keys())}")
                    
                    await telegram_app.bot.send_video(**send_args)
                    logger.info("Video successfully sent to Telegram.")
        
        except Exception as e:
            logger.error(f"CRITICAL TASK ERROR: {e}")
            logger.error(traceback.format_exc())
            # Optional: Notify chat if the error is triggered via command
            if chat_id:
                try:
                    await telegram_app.bot.send_message(chat_id=chat_id, text=f"Error: {str(e)[:50]}")
                except:
                    pass
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
        # Increased timeouts for slow video uploads
        telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).read_timeout(30).write_timeout(30).build()
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
