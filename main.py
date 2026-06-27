from fastapi import FastAPI, Header
from pydantic import BaseModel
import os
import requests
import subprocess
import random
import logging
from pathlib import Path
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

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
    if x_webhook_secret != os.getenv("WEBHOOK_SECRET"):
        return {"status": "failed", "reason": "Unauthorized"}
    try:
        video_path = await generate_video_with_background(request.signal)
        token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
        if token and chat_id: await send_telegram(video_path, request.signal, token, chat_id)
        return {"status": "success", "video": video_path}
    except Exception as e:
        logger.error(f"Publish error: {str(e)}", exc_info=True)
        return {"status": "failed", "reason": str(e)}

async def generate_video_with_background(signal: Signal) -> str:
    bg_dir_path = Path(BACKGROUND_DIR)
    logger.debug(f"Checking backgrounds directory: {BACKGROUND_DIR}")
    logger.debug(f"Directory exists: {bg_dir_path.exists()}")
    
    if bg_dir_path.exists():
        mp4_files = list(bg_dir_path.glob("*.mp4"))
        logger.debug(f"Found {len(mp4_files)} MP4 files: {mp4_files}")
    else:
        logger.error(f"Backgrounds directory does not exist: {BACKGROUND_DIR}")
        raise Exception(f"No backgrounds directory at {BACKGROUND_DIR}")
    
    if not mp4_files:
        raise Exception(f"No .mp4 files found in {BACKGROUND_DIR}")
    
    bg_video = random.choice(mp4_files)
    logger.info(f"Selected background: {bg_video}")
    
    signal_image = await generate_signal_card_image(signal)
    video_path = f"/tmp/signal_{signal.id}.mp4"
    
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-i', str(bg_video), '-i', signal_image,
        '-filter_complex', 'overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2',
        '-t', '8',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', video_path
    ]
    
    logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"FFmpeg error: {result.stderr}")
        raise Exception(f"FFmpeg failed: {result.stderr}")
    
    logger.info(f"Video generated: {video_path}")
    return video_path

async def generate_signal_card_image(signal: Signal) -> str:
    tp_values = signal.tp + [0.0, 0.0, 0.0]
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><style>
    /* 1. Ensure body is strictly transparent */
    body { 
        margin: 0; 
        width: 1080px; 
        height: 1920px; 
        background-color: transparent !important; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
    }
    /* 2. Style the card with the glassmorphism effect */
    .card { 
        width: 900px; 
        /* Use a very dark, slightly transparent black background */
        background: rgba(10, 10, 15, 0.4); 
        /* The blur filter is what creates the "frosted" glass look */
        backdrop-filter: blur(20px); 
        -webkit-backdrop-filter: blur(20px);
        border: 2px solid rgba(0, 255, 136, 0.3); 
        border-radius: 50px; 
        padding: 60px; 
        color: white; 
        box-sizing: border-box;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    /* ... keep the rest of your classes here ... */
</style></head>
    <body>
    <div class="card">
        <div class="header">
            <div class="brand">CIPHERVAULT</div>
            <div class="live-badge">LIVE</div>
        </div>
        <div class="symbol">{signal.symbol}</div>
        <div class="row"><span class="label">ENTRY</span><span class="value green">${signal.entry:,.2f}</span></div>
        <div class="row"><span class="label">TP1</span><span class="value">${tp_values[0]:,.2f}</span></div>
        <div class="row"><span class="label">TP2</span><span class="value">${tp_values[1]:,.2f}</span></div>
        <div class="row"><span class="label">TP3</span><span class="value">${tp_values[2]:,.2f}</span></div>
        <div class="row"><span class="label">SL</span><span class="value red">${signal.sl:,.2f}</span></div>
        <div class="footer">
            <div class="stat-box"><div class="stat-label">GRADE</div><div class="stat-value">{signal.grade}</div></div>
            <div class="stat-box"><div class="stat-label">SCORE</div><div class="stat-value">{signal.score}</div></div>
            <div class="stat-box"><div class="stat-label">R:R</div><div class="stat-value">{signal.rr}x</div></div>
        </div>
    </div>
    </body>
    </html>
    """
    temp_image = f"/tmp/card_{signal.id}.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'])
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        await page.set_content(html, wait_until='networkidle')
        await page.wait_for_timeout(500)
        await page.screenshot(path=temp_image)
        await browser.close()
    logger.info(f"Card image generated: {temp_image}")
    return temp_image

async def send_telegram(video_path, signal, token, chat_id):
    with open(video_path, 'rb') as f:
        requests.post(f"https://api.telegram.org/bot{token}/sendVideo", files={"video": f}, data={"chat_id": chat_id})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
