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
        video_path = await generate_video_with_background(request.signal)
        if not video_path: return {"status": "failed", "video": None}
        token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
        if token and chat_id: await send_telegram(video_path, request.signal, token, chat_id)
        return {"status": "success", "video": video_path}
    except Exception as e:
        log_info(f"FATAL ERROR: {str(e)}")
        return {"status": "failed", "reason": str(e)}

async def generate_video_with_background(signal: Signal) -> str:
    bg_video = random.choice(list(Path(BACKGROUND_DIR).glob("*.mp4")))
    signal_image = await generate_signal_card_image(signal)
    video_path = f"/tmp/signal_{signal.id}.mp4"
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-ss', '0', '-i', str(bg_video), '-i', signal_image,
        '-filter_complex', 'overlay=(W-w)/2:(H-h)/2', '-t', '8',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', video_path
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    return video_path

async def generate_signal_card_image(signal: Signal) -> str:
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><style>
        body {{ margin: 0; width: 1080px; height: 1920px; background: transparent; display: flex; align-items: center; justify-content: center; }}
        .card {{ background: rgba(20, 20, 20, 0.6); backdrop-filter: blur(20px); border: 3px solid #00ff88; border-radius: 30px; padding: 50px; color: #fff; width: 600px; text-align: center; }}
    </style></head>
    <body><div class="card"><h1>{signal.symbol}</h1><p>ENTRY: {signal.entry}</p><p>SIDE: {signal.side.upper()}</p></div></body>
    </html>
    """
    temp_image = f"/tmp/card_{signal.id}.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'])
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1080, "height": 1920})
        await page.set_content(html)
        await page.screenshot(path=temp_image, omit_background=True)
        await browser.close()
    return temp_image

async def send_telegram(video_path, signal, token, chat_id):
    with open(video_path, 'rb') as f:
        requests.post(f"https://api.telegram.org/bot{token}/sendVideo", files={"video": f}, data={"chat_id": chat_id})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
