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
        return {"status": "failed", "reason": str(e)}

async def generate_video_with_background(signal: Signal) -> str:
    bg_video = random.choice(list(Path(BACKGROUND_DIR).glob("*.mp4")))
    signal_image = await generate_signal_card_image(signal)
    video_path = f"/tmp/signal_{signal.id}.mp4"
    
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-i', str(bg_video), '-i', signal_image,
        '-filter_complex', 'overlay=0:0', '-t', '8',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', video_path
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    return video_path

async def generate_signal_card_image(signal: Signal) -> str:
    tp_values = signal.tp + [0.0, 0.0, 0.0]
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            width: 720px; height: 1280px; display: flex; align-items: center; justify-content: center; 
            padding-top: 100px; background: transparent !important; 
        }}
        .card {{ 
            width: 600px; background: rgba(10, 10, 15, 0.65); border: 2px solid rgba(0, 255, 136, 0.5); 
            border-radius: 40px; padding: 40px; color: white; box-shadow: 0 10px 30px rgba(0,0,0,0.8);
        }}
        .symbol {{ font-size: 60px; font-weight: bold; margin-bottom: 30px; }}
        .row {{ display: flex; justify-content: space-between; padding: 15px 0; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 28px; }}
        .green {{ color: #00ff88; font-weight: bold; }}
        .red {{ color: #ff6b6b; font-weight: bold; }}
        .footer {{ display: flex; justify-content: space-between; margin-top: 30px; gap: 10px; }}
        .stat-box {{ flex: 1; background: rgba(255,255,255,0.05); padding: 20px; border-radius: 20px; text-align: center; }}
        .disclaimer {{ margin-top: 30px; font-size: 14px; color: rgba(255,255,255,0.4); text-align: center; }}
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
        page = await browser.new_page(viewport={"width": 720, "height": 1280})
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

#crypto"""
    with open(video_path, 'rb') as f:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendVideo", 
            files={"video": f}, 
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
