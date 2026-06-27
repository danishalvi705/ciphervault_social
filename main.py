from fastapi import FastAPI, Header
from pydantic import BaseModel
import os
import requests
import subprocess
import random
import sys
from pathlib import Path
from playwright.async_api import async_playwright

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
        return {"status": "failed", "reason": str(e)}

async def generate_video_with_background(signal: Signal) -> str:
    bg_video = random.choice(list(Path(BACKGROUND_DIR).glob("*.mp4")))
    signal_image = await generate_signal_card_image(signal)
    video_path = f"/tmp/signal_{signal.id}.mp4"
    # Using overlay=0:0 to match the 1080x1920 canvas
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
    <head><style>
        body {{ margin: 0; width: 1080px; height: 1920px; background: transparent; display: flex; align-items: center; justify-content: center; }}
        .card {{ 
            width: 90%; max-width: 900px;
            background: rgba(10, 10, 15, 0.6); backdrop-filter: blur(40px); 
            border: 2px solid rgba(0, 255, 136, 0.5); border-radius: 50px; 
            padding: 60px; color: white; box-sizing: border-box;
            box-shadow: 0 0 50px rgba(0, 0, 0, 0.8);
            font-family: sans-serif;
        }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }}
        .symbol {{ font-size: 80px; font-weight: bold; margin-bottom: 40px; }}
        .row {{ display: flex; justify-content: space-between; padding: 25px 0; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 35px; }}
        .green {{ color: #00ff88; font-weight: bold; }}
        .red {{ color: #ff6b6b; font-weight: bold; }}
        .footer {{ display: flex; justify-content: space-between; margin-top: 50px; }}
        .box {{ background: rgba(255,255,255,0.05); padding: 30px; border-radius: 25px; text-align: center; width: 200px; }}
    </style></head>
    <body>
    <div class="card">
        <div class="header"><div style="font-size: 30px; letter-spacing: 3px;">CIPHERVAULT</div><div style="background:#d4a373; padding:10px 20px; border-radius:20px; color:black; font-weight:bold;">LIVE</div></div>
        <div class="symbol">{signal.symbol}</div>
        <div class="row"><span>ENTRY</span><span class="green">${signal.entry:,.2f}</span></div>
        <div class="row"><span>TP1</span><span>${tp_values[0]:,.2f}</span></div>
        <div class="row"><span>TP2</span><span>${tp_values[1]:,.2f}</span></div>
        <div class="row"><span>TP3</span><span>${tp_values[2]:,.2f}</span></div>
        <div class="row"><span>SL</span><span class="red">${signal.sl:,.2f}</span></div>
        <div class="footer">
            <div class="box"><div style="font-size:16px; color:#888;">GRADE</div><div style="font-size:35px; font-weight:bold;">{signal.grade}</div></div>
            <div class="box"><div style="font-size:16px; color:#888;">SCORE</div><div style="font-size:35px; font-weight:bold;">{signal.score}</div></div>
            <div class="box"><div style="font-size:16px; color:#888;">R:R</div><div style="font-size:35px; font-weight:bold;">{signal.rr}x</div></div>
        </div>
    </div>
    </body>
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
