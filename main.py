from fastapi import FastAPI, Header
from pydantic import BaseModel
import os
import requests
import asyncio
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

@app.post("/publish")
async def publish(request: PublishRequest, x_webhook_secret: str = Header(None)):
    """Receive signal and generate video"""
    secret = os.getenv("RENDER_SOCIAL_WEBHOOK_SECRET", "")
    
    if x_webhook_secret != secret:
        return {"error": "Unauthorized"}
    
    try:
        # Generate video with Playwright
        signal = request.signal
        video_path = await generate_video(signal)
        
        # Send to Telegram
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if token and chat_id:
            await send_telegram(video_path, signal, token, chat_id)
        
        return {"status": "success", "video": video_path}
    except Exception as e:
        return {"error": str(e)}

async def generate_video(signal: Signal) -> str:
    """Generate video with Playwright"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 20px; width: 540px; height: 960px; font-family: Arial; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); display: flex; align-items: center; justify-content: center; }}
        .card {{ background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); border-radius: 20px; padding: 30px; color: white; text-align: center; width: 100%; }}
        .symbol {{ font-size: 48px; font-weight: bold; margin: 20px 0; }}
        .row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        .label {{ font-size: 12px; color: #aaa; }}
        .value {{ font-size: 18px; font-weight: bold; }}
    </style>
    </head>
    <body>
    <div class="card">
        <div style="font-size: 24px; margin-bottom: 20px;">CIPHERVAULT</div>
        <div class="symbol">{signal.symbol}</div>
        <div class="row"><span class="label">ENTRY</span><span class="value">${signal.entry:.2f}</span></div>
        <div class="row"><span class="label">TP</span><span class="value">{signal.tp}</span></div>
        <div class="row"><span class="label">SL</span><span class="value">${signal.sl:.2f}</span></div>
        <div class="row"><span class="label">GRADE</span><span class="value">{signal.grade}</span></div>
        <div class="row"><span class="label">R:R</span><span class="value">{signal.rr}x</span></div>
    </div>
    </body>
    </html>
    """
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'])
        page = await browser.new_page()
        await page.set_viewport_size({"width": 540, "height": 960})
        await page.set_content(html)
        path = f"/tmp/signal_{signal.id}.png"
        await page.screenshot(path=path)
        await browser.close()
    
    return path

async def send_telegram(video_path: str, signal: Signal, token: str, chat_id: str):
    """Send to Telegram"""
    try:
        with open(video_path, 'rb') as f:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendDocument",
                files={"document": f},
                data={"chat_id": chat_id, "caption": f"{signal.symbol} {signal.side}"}
            )
    except Exception as e:
        print(f"Telegram error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
