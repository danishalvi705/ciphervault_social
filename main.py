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

BACKGROUND_DIR = "./backgrounds"

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
        logger.error(f"Publish error: {str(e)}")
        return {"status": "failed", "reason": str(e)}

async def generate_video_with_background(signal: Signal) -> str:
    # Ensure background directory exists and has files
    bg_path = Path(BACKGROUND_DIR)
    bg_videos = list(bg_path.glob("*.mp4"))
    if not bg_videos:
        raise Exception("No background videos found in ./backgrounds")
    bg_video = random.choice(bg_videos)
    
    signal_image = await generate_signal_card_image(signal)
    video_path = f"/tmp/signal_{signal.id}.mp4"
    
    # Stable overlay filter - centered
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-i', str(bg_video), '-i', signal_image,
        '-filter_complex', '[0:v][1:v]overlay=(W-w)/2:(H-h)/2', 
        '-t', '8', '-c:v', 'libx264', '-preset', 'ultrafast', 
        '-pix_fmt', 'yuv420p', video_path
    ]
    
    process = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if process.returncode != 0:
        raise Exception(f"FFmpeg failed: {process.stderr}")
        
    return video_path

async def generate_signal_card_image(signal: Signal) -> str:
    tp_values = signal.tp + [0.0, 0.0, 0.0]
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ width: 1080px; height: 1920px; display: flex; align-items: center; justify-content: center; background: transparent !important; }}
        .card {{ width: 820px; background: rgba(5, 5, 10, 0.85); border: 2px solid rgba(0, 255, 136, 0.7); border-radius: 40px; padding: 60px; color: #ffffff; box-shadow: 0 10px 60px rgba(0,0,0,0.95); display: flex; flex-direction: column; justify-content: center; }}
        .symbol {{ font-size: 68px; font-weight: bold; margin-bottom: 40px; color: #ffffff; }}
        .row {{ display: flex; justify-content: space-between; align-items: center; padding: 22px 0; border-bottom: 1px solid rgba(255,255,255,0.15); font-size: 38px; color: #ffffff; }}
        .row span:last-child {{ color: #ffffff; font-weight: 600; }}
        .green {{ color: #00ff88 !important; font-weight: bold; }}
        .red {{ color: #ff4444 !important; font-weight: bold; }}
        .footer {{ display: flex; justify-content: space-between; margin-top: 40px; gap: 15px; }}
        .stat-box {{ flex: 1; background: rgba(255,255,255,0.08); padding: 25px 10px; border-radius: 20px; text-align: center; color: #ffffff; font-size: 32px; }}
        .stat-box b {{ display: block; font-size: 38px; margin-top: 8px; color: #00ff88; }}
        .disclaimer {{ margin-top: 30px; font-size: 22px; color: rgba(255,255,255,0.5); text-align: center; }}
    </style>
    </head>
    <body>
        <div class="card">
            <div class="symbol">{signal.symbol}</div>
            <div class="row"><span>ENTRY</span><span class="green">${signal.entry:,.2f}</span></div>
            <div class="row"><span>TP1</span><span>${tp_values[0]:,.2f}</span></div>
            <div class="row"><span>TP2</span><span>${tp_values[1]:,.2f}</span></div>
            <div class="row"><span>TP3</span><span>${tp_values[2]:,.2f}</span></div>
            <div class="row"><span>SL</span><span class="red">${signal.sl:,.2f}</span></div>
            <div class="footer">
                <div class="stat-box">GRADE<br><b>{signal.grade}</b></div>
                <div class="stat-box">SCORE<br><b>{signal.score}</b></div>
                <div class="stat-box">R:R<br><b>{signal.rr}x</b></div>
            </div>
            <div class="disclaimer">Disclaimer: Trading is risky. Not financial advice.</div>
        </div>
    </body>
    </html>
    """
    temp_image = f"/tmp/card_{signal.id}.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'])
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        await page.set_content(html, wait_until='networkidle')
        await page.screenshot(path=temp_image, omit_background=True)
        await browser.close()
    return temp_image

async def send_telegram(video_path, signal, token, chat_id):
    caption = f"""#Trade_alert

<b>{signal.symbol}</b>
<b>Side:</b> {signal.side.upper()}
<b>Entry:</b> ${signal.entry:,.2f}
<b>TP1:</b> ${signal.tp[0]:,.2f}
<b>TP2:</b> ${signal.tp[1]:,.2f}
<b>TP3:</b> ${signal.tp[2]:,.2f}
<b>SL:</b> ${signal.sl:,.2f}

<b>Grade:</b> {signal.grade}
<b>Score:</b> {signal.score}
<b>R:R:</b> {signal.rr}x

#crypto #ciphervault"""
    with open(video_path, 'rb') as f:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendVideo", 
            files={"video": f}, 
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
