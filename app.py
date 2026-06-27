from fastapi import FastAPI, Header, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
import os
import requests
import asyncio
import logging
import traceback
import gc
from pathlib import Path
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ciphervault-social-render")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

app = FastAPI(title="CipherVault Social")

class Signal(BaseModel):
    id: str
    symbol: str
    side: str
    entry: float
    sl: float
    tp: float
    rr: float
    score: float | str

class PublishRequest(BaseModel):
    signal: Signal
    ohlcv: list

async def process_video_task(signal: Signal):
    """Generate signal image from HTML template"""
    if not signal:
        return
    
    try:
        html = f"""<!DOCTYPE html>
<html><head><style>
body {{ margin: 0; padding: 20px; width: 540px; height: 960px; font-family: Arial; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); display: flex; align-items: center; justify-content: center; }}
.card {{ background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); border-radius: 20px; padding: 30px; color: white; text-align: center; width: 100%; }}
.symbol {{ font-size: 48px; font-weight: bold; margin: 20px 0; }}
.row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }}
.label {{ font-size: 12px; color: #aaa; }}
.value {{ font-size: 18px; font-weight: bold; }}
</style></head><body>
<div class="card">
<div style="font-size: 24px; margin-bottom: 20px;">CIPHERVAULT</div>
<div class="symbol">{signal.symbol}</div>
<div class="row"><span class="label">ENTRY</span><span class="value">${signal.entry:.2f}</span></div>
<div class="row"><span class="label">TP</span><span class="value">${signal.tp[0]:.2f}</span></div>
<div class="row"><span class="label">SL</span><span class="value">${signal.sl:.2f}</span></div>
<div class="row"><span class="label">GRADE</span><span class="value">{signal.score}</span></div>
<div class="row"><span class="label">R:R</span><span class="value">{signal.rr}x</span></div>
</div></body></html>"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page()
            await page.set_viewport_size({"width": 540, "height": 960})
            await page.set_content(html)
            image_path = f"/tmp/signal_{signal.id}.png"
            await page.screenshot(path=image_path)
            await browser.close()
        
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            with open(image_path, 'rb') as f:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    files={"photo": f},
                    data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"{signal.symbol} {signal.side}"}
                )
        
        logger.info(f"Image sent for {signal.symbol}")
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
    finally:
        gc.collect()

@app.post("/publish")
async def publish(req: PublishRequest, background_tasks: BackgroundTasks, x_webhook_secret: str = Header(default="")):
    if not WEBHOOK_SECRET or x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    try:
        score = float(req.signal.score) if isinstance(req.signal.score, str) else req.signal.score
        if score < 4.0:
            return {"status": "ignored"}
    except:
        pass
    
    background_tasks.add_task(process_video_task, req.signal)
    return {"status": "queued"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
