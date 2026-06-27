from fastapi import FastAPI, Header
from pydantic import BaseModel
import os
import requests
import asyncio
import subprocess
import random
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

BACKGROUND_DIR = "/app/Background"

@app.post("/publish")
async def publish(request: PublishRequest, x_webhook_secret: str = Header(None)):
    """Receive signal and generate video with background"""
    secret = os.getenv("WEBHOOK_SECRET", "")

    if x_webhook_secret != secret:
        return {"error": "Unauthorized"}

    try:
        signal = request.signal
        print(f"[DEBUG] Signal received: {signal.symbol} {signal.side}", flush=True)
        
        video_path = await generate_video_with_background(signal)
        print(f"[DEBUG] Video path: {video_path}", flush=True)

        if not video_path:
            print("[DEBUG] Video path is None!", flush=True)
            return {"status": "success", "video": None}

        # Send to Telegram
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        print(f"[DEBUG] Token: {token[:10] if token else 'MISSING'}, Chat ID: {chat_id}", flush=True)

        if token and chat_id:
            print("[DEBUG] Sending to Telegram...", flush=True)
            await send_telegram(video_path, signal, token, chat_id)
            print("[DEBUG] Telegram send complete", flush=True)

        return {"status": "success", "video": video_path}
    except Exception as e:
        print(f"[ERROR] Exception: {str(e)}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        return {"error": str(e)}

async def generate_video_with_background(signal: Signal) -> str:
    """Generate MP4 video with signal card overlay on background video"""
    
    print(f"[DEBUG] Looking for backgrounds in: {BACKGROUND_DIR}", flush=True)
    
    bg_files = list(Path(BACKGROUND_DIR).glob("*.mp4")) + list(Path(BACKGROUND_DIR).glob("*.mkv"))
    
    print(f"[DEBUG] Found {len(bg_files)} background videos", flush=True)
    
    if not bg_files:
        print(f"[ERROR] No background videos found in {BACKGROUND_DIR}", flush=True)
        return None
    
    bg_video = random.choice(bg_files)
    print(f"[DEBUG] Using background: {bg_video}", flush=True)

    print("[DEBUG] Generating signal card image...", flush=True)
    signal_image = await generate_signal_card_image(signal)
    print(f"[DEBUG] Signal card image: {signal_image}", flush=True)
    
    if not signal_image or not os.path.exists(signal_image):
        print(f"[ERROR] Signal image generation failed", flush=True)
        return None
    
    video_path = f"/tmp/signal_{signal.id}.mp4"
    
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', str(bg_video),
        '-i', signal_image,
        '-filter_complex', '[0:v]scale=540:960[bg];[bg][1:v]overlay=(W-w)/2:(H-h)/2[out]',
        '-map', '[out]',
        '-map', '0:a?',
        '-c:v', 'libx264',
        '-crf', '18',
        '-pix_fmt', 'yuv420p',
        '-t', '10',
        video_path,
        '-y'
    ]
    
    print(f"[DEBUG] Running FFmpeg...", flush=True)
    
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"[ERROR] FFmpeg failed: {result.stderr}", flush=True)
            return None
        print(f"[DEBUG] Video created: {video_path}", flush=True)
    except Exception as e:
        print(f"[ERROR] FFmpeg execution error: {e}", flush=True)
        return None
    
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file does not exist: {video_path}", flush=True)
        return None
    
    file_size = os.path.getsize(video_path)
    print(f"[DEBUG] Video file size: {file_size} bytes", flush=True)
    
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
            background: rgba(15, 15, 30, 0.9);
            backdrop-filter: blur(10px); 
            border: 2px solid rgba(0,255,136,0.5);
            border-radius: 15px; 
            padding: 40px; 
            color: #00ff88;
            text-align: center; 
            width: 380px;
            box-shadow: 0 8px 32px rgba(0,255,136,0.2);
        }}
        .symbol {{ 
            font-size: 56px; 
            font-weight: bold; 
            margin: 20px 0; 
            color: #00ff88;
            text-shadow: 0 0 10px rgba(0,255,136,0.5);
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
            text-shadow: 0 0 8px rgba(0,255,136,0.4);
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
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'])
        page = await browser.new_page()
        await page.set_viewport_size({"width": 540, "height": 960})
        await page.set_content(html)
        await page.screenshot(path=temp_image)
        await browser.close()

    return temp_image

async def send_telegram(video_path: str, signal: Signal, token: str, chat_id: str):
    """Send MP4 video to Telegram"""
    try:
        if not os.path.exists(video_path):
            print(f"[ERROR] Video file not found: {video_path}", flush=True)
            return
        
        file_size = os.path.getsize(video_path)
        print(f"[DEBUG] Sending video ({file_size} bytes) to Telegram...", flush=True)
        
        with open(video_path, 'rb') as f:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendVideo",
                files={"video": f},
                data={
                    "chat_id": chat_id,
                    "caption": f"🎯 {signal.symbol} {signal.side.upper()}\n✓ Grade: {signal.grade} | Score: {signal.score}/10",
                    "parse_mode": "HTML"
                },
                timeout=60
            )
            print(f"[DEBUG] Telegram response code: {response.status_code}", flush=True)
            print(f"[DEBUG] Telegram response: {response.text}", flush=True)
    except Exception as e:
        print(f"[ERROR] Telegram error: {e}", flush=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
