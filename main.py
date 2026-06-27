from fastapi import FastAPI, Header
from pydantic import BaseModel
import os
import requests
import asyncio
import subprocess
import random
import sys
from pathlib import Path
from playwright.async_api import async_playwright

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

@app.get("/health")
async def health():
    log_info("Health check")
    return {"status": "ok"}

@app.post("/publish")
async def publish(request: PublishRequest, x_webhook_secret: str = Header(None)):
    log_info("=== PUBLISH ENDPOINT CALLED ===")
    secret = os.getenv("WEBHOOK_SECRET", "")
    
    if x_webhook_secret != secret:
        log_info("AUTH FAILED")
        return {"error": "Unauthorized"}

    try:
        signal = request.signal
        log_info(f"Signal: {signal.symbol} {signal.side}")
        
        video_path = await generate_video_with_background(signal)
        log_info(f"Result: {video_path}")

        if not video_path:
            log_info("VIDEO GENERATION RETURNED NONE")
            return {"status": "failed", "video": None}

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if token and chat_id:
            log_info("Sending to Telegram")
            await send_telegram(video_path, signal, token, chat_id)

        return {"status": "success", "video": video_path}
    except Exception as e:
        log_info(f"ERROR: {str(e)}")
        import traceback
        log_info(traceback.format_exc())
        return {"error": str(e)}

async def generate_video_with_background(signal: Signal) -> str:
    log_info("1. Starting video generation")
    
    bg_dir = Path(BACKGROUND_DIR)
    log_info(f"2. Background dir exists: {bg_dir.exists()}")
    
    if not bg_dir.exists():
        log_info(f"3. ERROR: Dir not found")
        return None
    
    bg_files = list(bg_dir.glob("*.mp4")) + list(bg_dir.glob("*.mkv"))
    log_info(f"4. Found {len(bg_files)} videos")
    
    if not bg_files:
        log_info(f"5. ERROR: No videos found")
        return None
    
    bg_video = random.choice(bg_files)
    log_info(f"6. Selected: {bg_video.name}")

    log_info("7. Generating image")
    signal_image = await generate_signal_card_image(signal)
    log_info(f"8. Image: {signal_image}")
    
    if not signal_image or not os.path.exists(signal_image):
        log_info("9. ERROR: Image failed")
        return None
    
    video_path = f"/tmp/signal_{signal.id}.mp4"
    log_info(f"10. Output: {video_path}")
    
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
    
    log_info("11. Running FFmpeg")
    
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
        log_info(f"12. FFmpeg return code: {result.returncode}")
        if result.returncode != 0:
            log_info(f"13. ERROR: {result.stderr[:300]}")
            return None
    except Exception as e:
        log_info(f"14. ERROR: {e}")
        return None
    
    if not os.path.exists(video_path):
        log_info(f"15. ERROR: File not created")
        return None
    
    file_size = os.path.getsize(video_path)
    log_info(f"16. Video size: {file_size}")
    
    if file_size < 1000:
        log_info(f"17. ERROR: Too small")
        return None
    
    try:
        os.remove(signal_image)
    except:
        pass
    
    log_info("18. SUCCESS - returning path")
    return video_path

async def generate_signal_card_image(signal: Signal) -> str:
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 0; width: 540px; height: 960px; font-family: 'Courier New', monospace; background: transparent; display: flex; align-items: center; justify-content: center; }}
        .card {{ background: rgba(15, 15, 30, 0.85); backdrop-filter: blur(15px); border: 2px solid rgba(0,255,136,0.6); border-radius: 20px; padding: 40px; color: #00ff88; text-align: center; width: 350px; box-shadow: 0 0 30px rgba(0,255,136,0.3); }}
        .symbol {{ font-size: 56px; font-weight: bold; margin: 20px 0; color: #00ff88; text-shadow: 0 0 15px rgba(0,255,136,0.6); }}
        .row {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(0,255,136,0.2); font-size: 14px; }}
        .label {{ color: #888; text-transform: uppercase; font-size: 12px; }}
        .value {{ font-weight: bold; color: #00ff88; }}
        .side {{ margin-top: 20px; font-size: 20px; font-weight: bold; color: {"#00ff88" if signal.side.lower() == "long" else "#ff4444"}; text-transform: uppercase; text-shadow: 0 0 12px rgba(0,255,136,0.5); }}
        .header {{ font-size: 12px; color: #666; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 2px; }}
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
    except Exception as e:
        log_info(f"Screenshot error: {e}")
        return None

    return temp_image

async def send_telegram(video_path: str, signal: Signal, token: str, chat_id: str):
    try:
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
            log_info(f"Telegram: {response.status_code}")
    except Exception as e:
        log_info(f"Telegram error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
