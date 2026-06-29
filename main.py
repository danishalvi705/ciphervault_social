from fastapi import FastAPI, Header
from pydantic import BaseModel
import os
import requests
import subprocess
import random
import logging
from pathlib import Path
from playwright.async_api import async_playwright
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from daily_videos import run_daily_videos

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scheduler lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    # Run all daily videos at 7PM UTC every day
    scheduler.add_job(
        run_daily_videos,
        CronTrigger(hour=19, minute=0, timezone="UTC"),
        id="daily_videos",
        name="Daily Video Generator",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("✅ Scheduler started — daily videos at 19:00 UTC")
    yield
    scheduler.shutdown()
    logger.info("Scheduler stopped.")


app = FastAPI(lifespan=lifespan)


# ---------------------------------------------------------------------------
# Signal model & webhook endpoint (unchanged)
# ---------------------------------------------------------------------------

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
        if token and chat_id:
            await send_telegram(video_path, request.signal, token, chat_id)
        return {"status": "success", "video": video_path}
    except Exception as e:
        logger.error(f"Publish error: {str(e)}")
        return {"status": "failed", "reason": str(e)}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/trigger-daily")
async def trigger_daily(x_webhook_secret: str = Header(None)):
    """Manual trigger for testing — hits the same logic as the scheduler."""
    if x_webhook_secret != os.getenv("WEBHOOK_SECRET"):
        return {"status": "failed", "reason": "Unauthorized"}
    import asyncio
    asyncio.create_task(run_daily_videos())
    return {"status": "triggered"}


# ---------------------------------------------------------------------------
# Video generation (unchanged from your original)
# ---------------------------------------------------------------------------

async def generate_video_with_background(signal: Signal) -> str:
    bg_path = Path(BACKGROUND_DIR)
    bg_videos = list(bg_path.glob("*.mp4"))
    if not bg_videos:
        raise Exception("No background videos found in ./backgrounds")
    bg_video = random.choice(bg_videos)

    signal_image = await generate_signal_card_image(signal)
    video_path = f"/tmp/signal_{signal.id}.mp4"

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
        .card {{ width: 700px; background: rgba(5, 5, 10, 0.55); border: 2px solid rgba(0, 255, 136, 0.7); border-radius: 40px; padding: 40px 50px; color: #ffffff; box-shadow: 0 10px 60px rgba(0,0,0,0.95); display: flex; flex-direction: column; justify-content: center; }}
        .symbol {{ font-size: 52px; font-weight: bold; margin-bottom: 25px; color: #ffffff; }}
        .row {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 0; border-bottom: 1px solid rgba(255,255,255,0.15); font-size: 30px; color: #ffffff; }}
        .row span:last-child {{ color: #ffffff; font-weight: 600; }}
        .green {{ color: #00ff88 !important; font-weight: bold; }}
        .red {{ color: #ff4444 !important; font-weight: bold; }}
        .footer {{ display: flex; justify-content: space-between; margin-top: 35px; gap: 15px; }}
        .stat-box {{ flex: 1; background: rgba(255,255,255,0.08); padding: 20px 10px; border-radius: 20px; text-align: center; color: #ffffff; font-size: 30px; }}
        .stat-box b {{ display: block; font-size: 36px; margin-top: 8px; color: #00ff88; }}
        .disclaimer {{ margin-top: 25px; font-size: 20px; color: rgba(255,255,255,0.5); text-align: center; }}
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
