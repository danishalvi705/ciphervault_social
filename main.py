from fastapi import FastAPI, Header
from pydantic import BaseModel
import os
import requests
import asyncio
import subprocess
import random
import logging
from pathlib import Path
from playwright.async_api import async_playwright

# Setup logging
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

@app.get("/debug/backgrounds")
async def debug_backgrounds():
    """Debug endpoint to check what backgrounds exist"""
    logger.info(f"DEBUG endpoint called - checking {BACKGROUND_DIR}")
    bg_dir = Path(BACKGROUND_DIR)
    if not bg_dir.exists():
        logger.error(f"Directory does not exist: {BACKGROUND_DIR}")
        return {"error": f"Directory does not exist: {BACKGROUND_DIR}", "exists": False}
    
    bg_files = list(bg_dir.glob("*.mp4")) + list(bg_dir.glob("*.mkv"))
    logger.info(f"Found {len(bg_files)} background videos")
    return {
        "directory": str(BACKGROUND_DIR),
        "exists": True,
        "files": [str(f) for f in bg_files],
        "count": len(bg_files)
    }

@app.get("/health")
async def health():
    """Health check"""
    logger.info("Health check called")
    return {"status": "ok"}

@app.post("/publish")
async def publish(request: PublishRequest, x_webhook_secret: str = Header(None)):
    """Receive signal and generate video with background"""
    logger.info(f"PUBLISH endpoint called")
    secret = os.getenv("WEBHOOK_SECRET", "")
    logger.info(f"Secret check: received={x_webhook_secret[:10] if x_webhook_secret else None}, expected={secret[:10] if secret else None}")

    if x_webhook_secret != secret:
        logger.error("Secret mismatch!")
        return {"error": "Unauthorized"}

    try:
        signal = request.signal
        logger.info(f"Signal received: {signal.symbol} {signal.side}")
        
        video_path = await generate_video_with_background(signal)
        logger.info(f"Video generation result: {video_path}")

        if not video_path:
            logger.warning("Video path is None")
            return {"status": "failed", "video": None}

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        logger.info(f"Telegram check: token={bool(token)}, chat_id={bool(chat_id)}")

        if token and chat_id:
            logger.info("Sending to Telegram...")
            await send_telegram(video_path, signal, token, chat_id)
            logger.info("Telegram send complete")

        return {"status": "success", "video": video_path}
    except Exception as e:
        logger.error(f"Exception: {str(e)}", exc_info=True)
        return {"error": str(e)}

async def generate_video_with_background(signal: Signal) -> str:
    """Generate MP4 video with signal card overlay on background video"""
    
    logger.info("Starting video generation")
    
    bg_dir = Path(BACKGROUND_DIR)
    logger.info(f"Background dir exists: {bg_dir.exists()}")
    
    if not bg_dir.exists():
        logger.error(f"Background directory does not exist: {BACKGROUND_DIR}")
        return None
    
    bg_files = list(bg_dir.glob("*.mp4")) + list(bg_dir.glob("*.mkv"))
    logger.info(f"Found {len(bg_files)} background videos")
    
    if not bg_files:
        logger.error(f"No background videos found")
        return None
    
    bg_video = random.choice(bg_files)
    logger.info(f"Selected: {bg_video.name}")

    logger.info("Generating signal card image...")
    signal_image = await generate_signal_card_image(signal)
    logger.info(f"Signal image: {signal_image}")
    
    if not signal_image or not os.path.exists(signal_image):
        logger.error("Signal image generation failed")
        return None
    
    video_path = f"/tmp/signal_{signal.id}.mp4"
    logger.info(f"Output path: {video_path}")
    
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', str(bg_video),
        '-i', signal_image,
        '-filter_complex', '[1:v]format=rgba,pad=iw:ih:0:0[overlay];[0:v]scale=1080:1920[base];[base][overlay]overlay=(W-w)/2:(H-h)/2:enable="gte(t,0)"[outv]',
        '-map', '[outv]',
        '-map', '0:a?',
        '-c:v', 'libx264',
        '-crf', '20',
        '-pix_fmt', 'yuv420p',
        '-t', '15',
        '-y',
        video_path
    ]
    
    logger.info("Running FFmpeg...")
    
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"FFmpeg failed: {result.stderr[:500]}")
            return None
        logger.info("Video created")
    except Exception as e:
        logger.error(f"FFmpeg error: {e}")
        return None
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not created: {video_path}")
        return None
    
    file_size = os.path.getsize(video_path)
    logger.info(f"Video size: {file_size} bytes")
    
    if file_size < 1000:
        logger.error(f"Video too small: {file_size}")
        return None
    
    try:
        os.remove(signal_image)
    except:
        pass
    
    return video_path

async def generate_signal_card_image(signal: Signal) -> str:
    """Generate signal card as PNG image using Playwright"""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ 
            margin: 0; 
            padding: 0;
            width: 540px; 
            height: 960px; 
            font-family: 'Courier New', monospace;
            background: transparent;
            display: flex; 
            align-items: center; 
            justify-content: center;
        }}
        .card {{ 
            background: rgba(15, 15, 30, 0.85);
            backdrop-filter: blur(15px); 
            border: 2px solid rgba(0,255,136,0.6);
            border-radius: 20px; 
            padding: 40px; 
            color: #00ff88;
            text-align: center; 
            width: 350px;
            box-shadow: 0 0 30px rgba(0,255,136,0.3);
        }}
        .symbol {{ 
            font-size: 56px; 
            font-weight: bold; 
            margin: 20px 0; 
            color: #00ff88;
            text-shadow: 0 0 15px rgba(0,255,136,0.6);
        }}
        .row {{ 
            display: flex; 
            justify-content: space-between; 
            padding: 12px 0; 
            border-bottom: 1px solid rgba(0,255,136,0.2);
            font-size: 14px;
        }}
        .label {{ 
            color: #888;
            text-transform: uppercase;
            font-size: 12px;
        }}
        .value {{ 
            font-weight: bold;
            color: #00ff88;
        }}
        .side {{
            margin-top: 20px;
            font-size: 20px;
            font-weight: bold;
            color: {"#00ff88" if signal.side.lower() == "long" else "#ff4444"};
            text-transform: uppercase;
            text-shadow: 0 0 12px rgba(0,255,136,0.5);
        }}
        .header {{
            font-size: 12px;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}
    </style>
    </head>
    <body>
    <div class="card">
        <div class="header">⚡ CIPHERVAULT</div>
        <div class="symbol">{signal.symbol}</div>
        <div class="row"><span class="label">ENTRY</span><span class="value">${signal.entry:.2f}</span></div>
        <div class="row"><span class="label">SL</span><span class="value">${signal.sl:.2f}</span></div>
        <div class="row"><span class="label">TP</span><span class="value">{', '.join([f'${tp:.2f}' for tp in signal.tp])}</span></div>
        <div class="row"><span class="label">GRADE</span><span class="value">{signal.grade}</span></div>
        <div class="row"><span class="label">SCORE</span><span class="value">{signal.score}/10</span></div>
        <div class="row"><span class="label">R:R</span><span class="value">{signal.rr}x</span></div>
        <div class="side">{signal.side.upper()}</div>
    </div>
    </body>
    </html>
    """

    temp_image = f"/tmp/signal_card_{signal.id}.png"
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page()
            await page.set_viewport_size({"width": 540, "height": 960})
            await page.set_content(html)
            await page.screenshot(path=temp_image)
            await browser.close()
        logger.info(f"Screenshot saved")
    except Exception as e:
        logger.error(f"Playwright error: {e}")
        return None

    return temp_image

async def send_telegram(video_path: str, signal: Signal, token: str, chat_id: str):
    """Send MP4 video to Telegram"""
    try:
        if not os.path.exists(video_path):
            logger.error(f"Video not found: {video_path}")
            return
        
        file_size = os.path.getsize(video_path)
        logger.info(f"Sending video ({file_size} bytes) to Telegram")
        
        with open(video_path, 'rb') as f:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendVideo",
                files={"video": f},
                data={
                    "chat_id": chat_id,
                    "caption": f"🎯 {signal.symbol} {signal.side.upper()}\n✓ Grade: {signal.grade} | Score: {signal.score}/10",
                    "parse_mode": "HTML"
                },
                timeout=120
            )
            logger.info(f"Telegram response: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Telegram error: {response.text[:200]}")
    except Exception as e:
        logger.error(f"Telegram exception: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
