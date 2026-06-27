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

# Import the reliable recorder
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
    # 1. Define the path clearly as a string/Path object
    signal_id = signal.id if signal else "manual"
    video_path = Path(VIDEO_DIR) / f"{signal_id}.mp4"
    
    logger.info(f"DEBUG: Task started. Path: {video_path}")
    
    async with render_semaphore:
        try:
            # 2. Perform the capture
            # Ensure capture_signal_video writes to the file at video_path
            await capture_signal_video("http://168.144.131.132:8000/", str(video_path))
            
            # 3. Verify file exists (This checks the path object, not a coroutine)
            if not video_path.exists():
                raise FileNotFoundError(f"Recorder failed to create file at {video_path}")
            
            # 4. Check file size (stat is now safe because video_path is definitely a Path)
            file_size = video_path.stat().st_size
            logger.info(f"DEBUG: File size: {file_size} bytes")
            
            if file_size < 1000:
                raise ValueError("Video file is corrupt (too small).")

            # 5. Sending
            if telegram_app and telegram_app.bot:
                target_chat = int(chat_id or TELEGRAM_CHAT_ID)
                
                with open(video_path, "rb") as video_file:
                    send_args = {
                        "chat_id": target_chat,
                        "video": InputFile(video_file)
                    }
                    
                    if signal:
                        caption = f"SIGNAL: {str(signal.symbol).replace('_', '-')} {str(signal.side).upper()}\nScore: {signal.score}"
                        send_args["caption"] = caption

                    await telegram_app.bot.send_video(**send_args)
                
                logger.info("SUCCESS: Video sent.")
        
        except Exception as e:
            error_msg = f"CRITICAL ERROR: {str(e)}"
            logger.error(error_msg)
            # Log traceback for deeper debugging in your server logs
            logger.error(traceback.format_exc())
            
            # Try to report to Telegram
            if chat_id and telegram_app and telegram_app.bot:
                try:
                    await telegram_app.bot.send_message(chat_id=chat_id, text=error_msg[:100])
                except:
                    pass
        
        finally:
            # Cleanup
            if video_path.exists():
                video_path.unlink()
            gc.collect()

# --- Telegram Bot Handler ---
async def start_snap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Recording dashboard... 10 seconds.")
    # Use create_task to avoid blocking the bot response
    asyncio.create_task(process_video_task(None, chat_id=update.effective_chat.id))

@app.on_event("startup")
async def startup():
    global telegram_app
    if TELEGRAM_BOT_TOKEN:
        telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        telegram_app.add_handler(CommandHandler("snap", start_snap))
        await telegram_app.initialize()
        
        if WEBHOOK_URL:
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}/telegram-webhook")
                except Exception as e:
                    logger.error(f"Failed to set webhook: {e}")
        
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
        pass

    background_tasks.add_task(process_video_task, req.signal)
    return {"status": "queued"}
