from fastapi import FastAPI, Header
from pydantic import BaseModel
import os
import requests
import subprocess
import random
import sys
from pathlib import Path
from playwright.async_api import async_playwright
import traceback

app = FastAPI()

def log_info(msg):
    print(msg, file=sys.stderr, flush=True)

class Signal(BaseModel):
    id: str
    symbol: str
    side: str
    entry: float
    tp: list
    sl: float
    grade: str
    score: float
    rr: float

class PublishRequest(BaseModel):
    signal: Signal
    ohlcv: list

BACKGROUND_DIR = "/app/backgrounds"

@app.post("/publish")
async def publish(request: PublishRequest, x_webhook_secret: str = Header(None)):
    secret = os.getenv("WEBHOOK_SECRET", "")
    if x_webhook_secret != secret:
        return {"status": "failed", "reason": "Unauthorized"}

    try:
        signal = request.signal
        video_path = await generate_video_with_background(signal)

        if not video_path:
            return {"status": "failed", "video": None}

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if token and chat_id:
            await send_telegram(video_path, signal, token, chat_id)

        return {"status": "success", "video": video_path}
    except Exception as e:
        log_info(f"FATAL ERROR: {str(e)}\n{traceback.format_exc()}")
        return {"status": "failed", "reason": str(e)}

async def generate_video_with_background(signal: Signal) -> str:
    bg_dir = Path(BACKGROUND_DIR)
    bg_files = list(bg_dir.glob("*.mp4")) + list(bg_dir.glob("*.mkv"))
    
    if not bg_files:
        log_info("ERROR: No background videos found")
        return None
    
    bg_video = random.choice(bg_files)
    signal_image = await generate_signal_card_image(signal)
    
    if not signal_image or not os.path.exists(signal_image):
        return None
    
    video_path = f"/tmp/signal_{signal.id}.mp4"
    
    # Simplified Command for 512MB RAM
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-ss', '0',
        '-i', str(bg_video),
        '-i', signal_image,
        '-filter_complex', 'overlay=(W-w)/2:(H-h)/2',
        '-t', '8',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-pix_fmt', 'yuv420p',
        video_path
    ]
    
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=90)
        if result.returncode != 0:
            log_info(f"FFmpeg Error: {result.stderr}")
            return None
    except Exception as e:
        log_info(f"FFmpeg Exception: {e}")
        return None
    
    return video_path

async def generate_signal_card_image(signal: Signal) -> str:
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 0; width: 540px; height: 960px; font-family: sans-serif; background: transparent; display: flex; align-items: center; justify-content: center; }}
        .card {{ background: rgba(0, 0, 0, 0.8); border: 2px solid #00ff88; border-radius: 20px; padding: 30px; color: #fff; width: 300px; }}
    </style>
    </head>
    <body>
    <div class="card">
        <h1>{signal.symbol}</h1>
        <p>ENTRY: {signal.entry}</p>
        <p>SIDE: {signal.side.upper()}</p>
    </div>
    </body>
    </html>
    """
    temp_image = f"/tmp/card_{signal.id}.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'])
        page = await browser.new_page()
        await page.set_viewport_size({"width": 540, "height": 960})
        await page.set_content(html)
        await page.screenshot(path=temp_image)
        await browser.close()
    return temp_image

async def send_telegram(video_path, signal, token, chat_id):
    with open(video_path, 'rb') as f:
        requests.post(f"https://api.telegram.org/bot{token}/sendVideo", 
                      files={"video": f}, data={"chat_id": chat_id})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
