from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import aiohttp
from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
from datetime import datetime
import json
import subprocess
from pathlib import Path
import random

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = FastAPI()
video_generation_lock = asyncio.Lock()

import functools

def with_video_lock(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with video_generation_lock:
            return await func(*args, **kwargs)
    return wrapper

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CIPHERVAULT_API = os.getenv("CIPHERVAULT_API", "http://168.144.131.132:8000")
BACKGROUNDS_DIR = Path("./backgrounds")

BACKGROUNDS_DIR.mkdir(exist_ok=True)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def query_ciphervault_api(endpoint: str):
    """Query DigitalOcean CipherVault API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CIPHERVAULT_API}{endpoint}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return await resp.json()
    except Exception as e:
        print(f"API Error: {e}")
        return None


async def post_to_telegram(video_path: str, caption: str):
    """Post video to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
        
        with open(video_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('chat_id', TELEGRAM_CHAT_ID)
            data.add_field('video', f, filename=Path(video_path).name)
            data.add_field('caption', caption)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as resp:
                    result = await resp.json()
                    print(f"✅ Telegram posted: {result.get('ok')}")
                    return result
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return None


async def render_html_to_screenshot(html: str, output_path: str):
    """Render HTML to PNG using Playwright"""
    from playwright.async_api import async_playwright
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=[
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-sandbox",
                "--single-process",
                "--disable-extensions",
            ])
            page = await browser.new_page(viewport={"width": 1080, "height": 1920})
            await page.set_content(html)
            await page.screenshot(path=output_path, omit_background=True)
            await browser.close()
        print(f"✅ Screenshot: {output_path}")
    except Exception as e:
        print(f"❌ Screenshot error: {e}")
        raise


def overlay_on_background(screenshot_path: str, output_video: str):
    """Overlay screenshot on random background video using FFmpeg"""
    try:
        bg_files = list(BACKGROUNDS_DIR.glob("bg*.mp4"))
        if not bg_files:
            raise Exception("No background videos found in ./backgrounds/")
        
        bg_video = random.choice(bg_files)
        print(f"Using background: {bg_video.name}")
        
        filter_complex = (
            "[1]format=rgba,"
            "fade=t=in:st=0:d=0.8:alpha=1,"
            "zoompan=z='1+0.025*sin(2*3.14159*in/45)':d=1:s=1080x1920:fps=25[fg];"
            "[0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];"
            "[bg][fg]overlay=x=(W-w)/2:y=(H-h)/2[v]"
        )
        cmd = [
            "ffmpeg",
            "-i", str(bg_video),
            "-loop", "1",
            "-i", screenshot_path,
            "-filter_complex",
            filter_complex,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-crf", "23",
            "-c:a", "aac",
            "-t", "8",
            "-y",
            output_video
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise Exception(f"FFmpeg error: {result.stderr}")
        
        print(f"✅ Video: {output_video}")
        return output_video
    except Exception as e:
        print(f"❌ FFmpeg error: {e}")
        raise


# ============================================================================
# VIDEO GENERATION ENDPOINTS
# ============================================================================

@app.post("/generate-top-gainer")
@with_video_lock
async def generate_top_gainer():
    """Generate Top Gainer video"""
    try:
        data = await query_ciphervault_api("/api/v1/top-gainer")
        if not data or "error" in data:
            return {"error": data.get("error", "API error")}
        
        symbol = data['symbol']
        percent_gain = data['percent_gain']
        signal_type = data['signal_type'].replace('_', ' ').title()
        
        html = f"""
        <html>
        <head>
            <style>
                .disclaimer {{ margin-top: 50px; text-align: center; font-size: 24px; color: rgba(255,255,255,0.85); font-family: 'Arial', sans-serif; text-shadow: 0 2px 6px rgba(0,0,0,0.8); }}
                body {{ margin: 0; padding: 60px; font-family: 'Arial', sans-serif; width: 100%; height: 100%; }}
                .container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }}
                .title {{ font-size: 48px; color: #ff6b35; margin-bottom: 40px; font-weight: bold; }}
                .symbol {{ font-size: 64px; color: #ffffff; font-weight: bold; margin: 20px 0; }}
                .percent {{ font-size: 80px; color: #00ff41; font-weight: bold; margin: 30px 0; }}
                .type {{ font-size: 32px; color: #888; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title">🔥 TODAY'S TOP MOVER 🔥</div>
                <div class="symbol">{symbol}</div>
                <div class="percent">📈 +{percent_gain}%</div>
                <div class="type">{signal_type}</div>
            </div>
            <div class="disclaimer">Not Financial Advice. DYOR.</div>
        </body>
        </html>
        """
        
        screenshot = "/tmp/top_gainer.png"
        await render_html_to_screenshot(html, screenshot)
        
        output_video = f"/tmp/top_gainer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        overlay_on_background(screenshot, output_video)
        
        caption = f"🔥 Today's Top Mover!\n\n{symbol}\n+{percent_gain}% 📈\n\n{signal_type}\n\n#CipherVault #Trading\n\n⚠️ Not Financial Advice. DYOR."
        await post_to_telegram(output_video, caption)
        
        return {"status": "success", "video": output_video}
    except Exception as e:
        return {"error": str(e)}


@app.post("/generate-fear-greed")
@with_video_lock
async def generate_fear_greed():
    """Generate Fear & Greed video"""
    try:
        data = await query_ciphervault_api("/api/v1/fear-greed")
        if not data or "error" in data:
            return {"error": data.get("error", "API error")}
        
        value = data['value']
        sentiment = data['sentiment'].replace('_', ' ').title()
        
        if value < 25:
            color = "#ff0000"
            emoji = "😱"
        elif value < 45:
            color = "#ff6b35"
            emoji = "😟"
        elif value < 55:
            color = "#ffaa00"
            emoji = "😐"
        elif value < 75:
            color = "#00ff41"
            emoji = "😊"
        else:
            color = "#00aa00"
            emoji = "🚀"
        
        html = f"""
        <html>
        <head>
            <style>
                .disclaimer {{ margin-top: 50px; text-align: center; font-size: 24px; color: rgba(255,255,255,0.85); font-family: 'Arial', sans-serif; text-shadow: 0 2px 6px rgba(0,0,0,0.8); }}
                body {{ margin: 0; padding: 60px; font-family: 'Arial', sans-serif; width: 100%; height: 100%; }}
                .container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }}
                .title {{ font-size: 48px; color: #ffffff; margin-bottom: 40px; }}
                .gauge {{ font-size: 120px; color: {color}; font-weight: bold; margin: 30px 0; }}
                .sentiment {{ font-size: 44px; color: {color}; margin: 20px 0; font-weight: bold; }}
                .emoji {{ font-size: 80px; margin: 20px 0; }}
                .message {{ font-size: 32px; color: #999; margin-top: 40px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title">📊 MARKET SENTIMENT TODAY 📊</div>
                <div class="emoji">{emoji}</div>
                <div class="gauge">{value}</div>
                <div class="sentiment">{sentiment}</div>
                <div class="message">Best time to take profits?</div>
            </div>
            <div class="disclaimer">Not Financial Advice. DYOR.</div>
        </body>
        </html>
        """
        
        screenshot = "/tmp/fear_greed.png"
        await render_html_to_screenshot(html, screenshot)
        
        output_video = f"/tmp/fear_greed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        overlay_on_background(screenshot, output_video)
        
        caption = f"📊 Market Sentiment: {sentiment}\n\nFear & Greed Index: {value}\n\n{emoji}\n\n#CipherVault #Crypto\n\n⚠️ Not Financial Advice. DYOR."
        await post_to_telegram(output_video, caption)
        
        return {"status": "success", "video": output_video}
    except Exception as e:
        return {"error": str(e)}


@app.post("/generate-btc-dominance")
@with_video_lock
async def generate_btc_dominance():
    """Generate BTC Dominance video"""
    try:
        data = await query_ciphervault_api("/api/v1/btc-dominance")
        if not data or "error" in data:
            return {"error": data.get("error", "API error")}
        
        dominance = data['dominance']
        verdict = data['verdict']
        regime = data['regime']
        message = data['message']
        
        html = f"""
        <html>
        <head>
            <style>
                .disclaimer {{ margin-top: 50px; text-align: center; font-size: 24px; color: rgba(255,255,255,0.85); font-family: 'Arial', sans-serif; text-shadow: 0 2px 6px rgba(0,0,0,0.8); }}
                body {{ margin: 0; padding: 60px; font-family: 'Arial', sans-serif; width: 100%; height: 100%; }}
                .container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }}
                .title {{ font-size: 48px; color: #ffffff; margin-bottom: 40px; font-weight: bold; }}
                .dominance {{ font-size: 72px; color: #ffaa00; font-weight: bold; margin: 20px 0; }}
                .verdict {{ font-size: 52px; color: #ffffff; margin: 30px 0; font-weight: bold; }}
                .message {{ font-size: 36px; color: #999; margin: 20px 0; }}
                .regime {{ font-size: 40px; color: #00ff41; margin-top: 40px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title">BTC DOMINANCE VERDICT</div>
                <div class="dominance">BTC: {dominance}%</div>
                <div class="verdict">{verdict}</div>
                <div class="message">"{message}"</div>
                <div class="regime">BTC Trend: {regime}</div>
            </div>
            <div class="disclaimer">Not Financial Advice. DYOR.</div>
        </body>
        </html>
        """
        
        screenshot = "/tmp/btc_dominance.png"
        await render_html_to_screenshot(html, screenshot)
        
        output_video = f"/tmp/btc_dominance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        overlay_on_background(screenshot, output_video)
        
        caption = f"📊 BTC Dominance: {dominance}%\n\n{verdict}\n\n{message}\n\nTrend: {regime}\n\n#CipherVault #Bitcoin\n\n⚠️ Not Financial Advice. DYOR."
        await post_to_telegram(output_video, caption)
        
        return {"status": "success", "video": output_video}
    except Exception as e:
        return {"error": str(e)}


@app.post("/generate-signal-reveal")
@with_video_lock
async def generate_signal_reveal():
    """Generate Signal Reveal video"""
    try:
        data = await query_ciphervault_api("/api/v1/signal-reveal")
        if not data or "error" in data:
            return {"error": data.get("error", "API error")}
        
        symbol = data['symbol']
        entry = data['entry_price']
        tp = data['tp_price']
        gain = data['percent_gain']
        days = data['days_held']
        signal_type = data['signal_type'].replace('_', ' ').title()
        
        html = f"""
        <html>
        <head>
            <style>
                .disclaimer {{ margin-top: 50px; text-align: center; font-size: 24px; color: rgba(255,255,255,0.85); font-family: 'Arial', sans-serif; text-shadow: 0 2px 6px rgba(0,0,0,0.8); }}
                body {{ margin: 0; padding: 60px; font-family: 'Arial', sans-serif; width: 100%; height: 100%; }}
                .container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }}
                .checkmark {{ font-size: 80px; color: #00ff41; margin-bottom: 20px; }}
                .title {{ font-size: 44px; color: #00ff41; margin-bottom: 30px; font-weight: bold; }}
                .symbol {{ font-size: 56px; color: #ffffff; font-weight: bold; margin: 20px 0; }}
                .prices {{ font-size: 36px; color: #999; margin: 20px 0; }}
                .price-hit {{ font-size: 40px; color: #00ff41; margin: 10px 0; }}
                .gain {{ font-size: 64px; color: #00ff41; font-weight: bold; margin: 20px 0; }}
                .days {{ font-size: 32px; color: #888; margin: 10px 0; }}
                .type {{ font-size: 28px; color: #666; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="checkmark">✅</div>
                <div class="title">WE CALLED THIS 3+ DAYS AGO</div>
                <div class="symbol">{symbol}</div>
                <div class="prices">Entry: ${entry:.4f}</div>
                <div class="price-hit">Target Hit: ${tp:.4f} ✅</div>
                <div class="gain">+{gain}%</div>
                <div class="days">{days} Days Held</div>
                <div class="type">{signal_type}</div>
            </div>
            <div class="disclaimer">Not Financial Advice. DYOR.</div>
        </body>
        </html>
        """
        
        screenshot = "/tmp/signal_reveal.png"
        await render_html_to_screenshot(html, screenshot)
        
        output_video = f"/tmp/signal_reveal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        overlay_on_background(screenshot, output_video)
        
        caption = f"✅ Signal Reveal!\n\n{symbol}\nEntry: ${entry:.4f}\nTarget Hit: ${tp:.4f}\n\n+{gain}% Gain 🎯\n\n{days} Days Held\n\n#{signal_type.replace(' ', '')}\n#CipherVault\n\n⚠️ Not Financial Advice. DYOR."
        await post_to_telegram(output_video, caption)
        
        return {"status": "success", "video": output_video}
    except Exception as e:
        return {"error": str(e)}


@app.post("/generate-weekly-leaderboard")
@with_video_lock
async def generate_weekly_leaderboard():
    """Generate Weekly Leaderboard video"""
    try:
        data = await query_ciphervault_api("/api/v1/weekly-leaderboard")
        if not data or "error" in data:
            return {"error": data.get("error", "API error")}
        
        signals = data.get('signals', [])
        total_gain = data.get('total_gain', 0)
        
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]
        for i, sig in enumerate(signals):
            medal = medals[i] if i < 3 else f"{i+1}."
            leaderboard_text += f"\n{medal} {sig['symbol']}  +{sig['percent_gain']}%"
        
        if not leaderboard_text:
            leaderboard_text = "\nNo winners this week yet"
        
        html = f"""
        <html>
        <head>
            <style>
                .disclaimer {{ margin-top: 50px; text-align: center; font-size: 24px; color: rgba(255,255,255,0.85); font-family: 'Arial', sans-serif; text-shadow: 0 2px 6px rgba(0,0,0,0.8); }}
                body {{ margin: 0; padding: 60px; font-family: 'Arial', sans-serif; width: 100%; height: 100%; }}
                .container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }}
                .title {{ font-size: 48px; color: #ffaa00; margin-bottom: 40px; font-weight: bold; }}
                .leaderboard {{ font-size: 40px; color: #ffffff; margin: 30px 0; line-height: 1.8; font-family: monospace; }}
                .medal {{ font-size: 60px; }}
                .total {{ font-size: 44px; color: #00ff41; margin-top: 40px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title">THIS WEEK'S TOP 3 SIGNALS 🏆</div>
                <div class="leaderboard">{leaderboard_text}</div>
                <div class="total">Total: +{total_gain}% 🎯</div>
            </div>
            <div class="disclaimer">Not Financial Advice. DYOR.</div>
        </body>
        </html>
        """
        
        screenshot = "/tmp/weekly_leaderboard.png"
        await render_html_to_screenshot(html, screenshot)
        
        output_video = f"/tmp/weekly_leaderboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        overlay_on_background(screenshot, output_video)
        
        caption = f"🏆 This Week's Top 3 Signals\n{leaderboard_text}\n\nTotal Gains: +{total_gain}%\n\n#CipherVault #Trading\n\n⚠️ Not Financial Advice. DYOR."
        await post_to_telegram(output_video, caption)
        
        return {"status": "success", "video": output_video}
    except Exception as e:
        return {"error": str(e)}



# ============================================================================
# TEMPORARY TEST ENDPOINTS — remove after verifying
# ============================================================================
from daily_videos import generate_educational_video, generate_news_impact_video

@app.post("/test-educational")
async def test_educational():
    try:
        result = await generate_educational_video()
        return {"status": "success", "video": result}
    except Exception as e:
        return {"error": str(e)}

@app.post("/test-news")
async def test_news():
    try:
        result = await generate_news_impact_video()
        return {"status": "success", "video": result}
    except Exception as e:
        return {"error": str(e)}


@app.get("/test-news-debug")
async def test_news_debug():
    from news_fetch import fetch_coindesk_headlines, fetch_cointelegraph_headlines, fetch_decrypt_headlines
    return {
        "coindesk_count": len(fetch_coindesk_headlines()),
        "cointelegraph_count": len(fetch_cointelegraph_headlines()),
        "decrypt_count": len(fetch_decrypt_headlines()),
    }


@app.get("/test-news-headlines")
async def test_news_headlines():
    from news_fetch import fetch_coindesk_headlines, fetch_cointelegraph_headlines, fetch_decrypt_headlines, extract_coin_from_headline
    all_headlines = fetch_coindesk_headlines() + fetch_cointelegraph_headlines() + fetch_decrypt_headlines()
    results = []
    for h in all_headlines:
        coin_id, symbol_hit = extract_coin_from_headline(h["title"])
        results.append({"title": h["title"], "source": h["source"], "matched_coin": symbol_hit})
    return {"headlines": results}


@app.get("/test-price-debug")
async def test_price_debug():
    from news_fetch import get_price_change
    result = get_price_change("bitcoin")
    return {"price_data": result}

@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.post("/generate-educational")
@with_video_lock
async def generate_educational():
    """Generate Educational video"""
    try:
        result = await generate_educational_video()
        return {"status": "success", "video": result}
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# EVENT-TRIGGERED VIDEOS (liquidation / whale / volatility / listings)
# ============================================================================
from triggers.liquidation_listener import run_liquidation_listener
from triggers.whale_tracker import run_whale_tracker
from triggers.volatility_monitor import run_volatility_monitor
from triggers.listing_scanner import run_listing_scanner

@with_video_lock
async def generate_liquidation_alert(payload: dict):
    try:
        symbol = payload["symbol"]; side = payload["side"]
        usd_value = payload["usd_value"]; price = payload["price"]
        direction = "LONGS REKT" if side == "SELL" else "SHORTS REKT"
        html = f"""
        <html><head><style>
            .disclaimer {{ margin-top: 50px; text-align: center; font-size: 24px; color: rgba(255,255,255,0.85); font-family: 'Arial', sans-serif; text-shadow: 0 2px 6px rgba(0,0,0,0.8); }}
            body {{ margin: 0; padding: 60px; font-family: 'Arial', sans-serif; width: 100%; height: 100%; }}
            .container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }}
            .title {{ font-size: 48px; color: #ff2b2b; margin-bottom: 40px; font-weight: bold; }}
            .symbol {{ font-size: 64px; color: #ffffff; font-weight: bold; margin: 20px 0; }}
            .usd {{ font-size: 76px; color: #ff2b2b; font-weight: bold; margin: 30px 0; }}
            .direction {{ font-size: 40px; color: #ffaa00; margin: 20px 0; font-weight: bold; }}
            .price {{ font-size: 30px; color: #888; margin-top: 20px; }}
        </style></head><body>
            <div class="container">
                <div class="title">💥 LIQUIDATION ALERT 💥</div>
                <div class="symbol">{symbol}</div>
                <div class="usd">${usd_value:,.0f}</div>
                <div class="direction">{direction}</div>
                <div class="price">@ ${price:,.4f}</div>
            </div>
            <div class="disclaimer">Not Financial Advice. DYOR.</div>
        </body></html>
        """
        screenshot = "/tmp/liquidation_alert.png"
        await render_html_to_screenshot(html, screenshot)
        output_video = f"/tmp/liquidation_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        overlay_on_background(screenshot, output_video)
        caption = f"💥 LIQUIDATION ALERT\n\n{symbol}\n${usd_value:,.0f} {direction}\n\n@ ${price:,.4f}\n\n#CipherVault #Liquidation\n\n⚠️ Not Financial Advice. DYOR."
        await post_to_telegram(output_video, caption)
        return {"status": "success", "video": output_video}
    except Exception as e:
        print(f"❌  liquidation video error: {e}")
        return {"error": str(e)}

@with_video_lock
async def generate_whale_movement(payload: dict):
    try:
        symbol = payload["symbol"]; side = payload["side"]
        usd_value = payload["usd_value"]; price = payload["price"]
        html = f"""
        <html><head><style>
            .disclaimer {{ margin-top: 50px; text-align: center; font-size: 24px; color: rgba(255,255,255,0.85); font-family: 'Arial', sans-serif; text-shadow: 0 2px 6px rgba(0,0,0,0.8); }}
            body {{ margin: 0; padding: 60px; font-family: 'Arial', sans-serif; width: 100%; height: 100%; }}
            .container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }}
            .title {{ font-size: 48px; color: #29a3ff; margin-bottom: 40px; font-weight: bold; }}
            .symbol {{ font-size: 64px; color: #ffffff; font-weight: bold; margin: 20px 0; }}
            .usd {{ font-size: 76px; color: #29a3ff; font-weight: bold; margin: 30px 0; }}
            .side {{ font-size: 40px; color: #00ff41; margin: 20px 0; font-weight: bold; text-transform: uppercase; }}
            .price {{ font-size: 30px; color: #888; margin-top: 20px; }}
        </style></head><body>
            <div class="container">
                <div class="title">🐋 WHALE MOVEMENT 🐋</div>
                <div class="symbol">{symbol}</div>
                <div class="usd">${usd_value:,.0f}</div>
                <div class="side">{side}</div>
                <div class="price">@ ${price:,.4f}</div>
            </div>
            <div class="disclaimer">Not Financial Advice. DYOR.</div>
        </body></html>
        """
        screenshot = "/tmp/whale_movement.png"
        await render_html_to_screenshot(html, screenshot)
        output_video = f"/tmp/whale_movement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        overlay_on_background(screenshot, output_video)
        caption = f"🐋 WHALE MOVEMENT\n\n{symbol}\n${usd_value:,.0f} {side.upper()}\n\n@ ${price:,.4f}\n\n#CipherVault #Whale\n\n⚠️ Not Financial Advice. DYOR."
        await post_to_telegram(output_video, caption)
        return {"status": "success", "video": output_video}
    except Exception as e:
        print(f"❌  whale video error: {e}")
        return {"error": str(e)}

@with_video_lock
async def generate_volatility_alert(payload: dict):
    try:
        symbol = payload["symbol"]; pct_change = payload["pct_change"]; price = payload["price"]
        arrow = "🚀" if pct_change > 0 else "🔻"
        color = "#00ff41" if pct_change > 0 else "#ff2b2b"
        sign = "+" if pct_change > 0 else ""
        html = f"""
        <html><head><style>
            .disclaimer {{ margin-top: 50px; text-align: center; font-size: 24px; color: rgba(255,255,255,0.85); font-family: 'Arial', sans-serif; text-shadow: 0 2px 6px rgba(0,0,0,0.8); }}
            body {{ margin: 0; padding: 60px; font-family: 'Arial', sans-serif; width: 100%; height: 100%; }}
            .container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }}
            .title {{ font-size: 46px; color: #ffaa00; margin-bottom: 40px; font-weight: bold; }}
            .symbol {{ font-size: 64px; color: #ffffff; font-weight: bold; margin: 20px 0; }}
            .pct {{ font-size: 84px; color: {color}; font-weight: bold; margin: 30px 0; }}
            .price {{ font-size: 34px; color: #999; margin-top: 20px; }}
        </style></head><body>
            <div class="container">
                <div class="title">⚡ BREAKING VOLATILITY ⚡</div>
                <div class="symbol">{symbol}</div>
                <div class="pct">{arrow} {sign}{pct_change}%</div>
                <div class="price">Now: ${price:,.4f}</div>
            </div>
            <div class="disclaimer">Not Financial Advice. DYOR.</div>
        </body></html>
        """
        screenshot = "/tmp/volatility_alert.png"
        await render_html_to_screenshot(html, screenshot)
        output_video = f"/tmp/volatility_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        overlay_on_background(screenshot, output_video)
        caption = f"⚡ BREAKING VOLATILITY\n\n{symbol}\n{arrow} {sign}{pct_change}%\n\nNow: ${price:,.4f}\n\n#CipherVault #Volatility\n\n⚠️ Not Financial Advice. DYOR."
        await post_to_telegram(output_video, caption)
        return {"status": "success", "video": output_video}
    except Exception as e:
        print(f"❌  volatility video error: {e}")
        return {"error": str(e)}

@with_video_lock
async def generate_new_listing(payload: dict):
    try:
        symbol = payload["symbol"]; exchange = payload["exchange"]
        html = f"""
        <html><head><style>
            .disclaimer {{ margin-top: 50px; text-align: center; font-size: 24px; color: rgba(255,255,255,0.85); font-family: 'Arial', sans-serif; text-shadow: 0 2px 6px rgba(0,0,0,0.8); }}
            body {{ margin: 0; padding: 60px; font-family: 'Arial', sans-serif; width: 100%; height: 100%; }}
            .container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }}
            .title {{ font-size: 48px; color: #00ff41; margin-bottom: 40px; font-weight: bold; }}
            .symbol {{ font-size: 68px; color: #ffffff; font-weight: bold; margin: 20px 0; }}
            .exchange {{ font-size: 40px; color: #888; margin: 20px 0; text-transform: uppercase; }}
        </style></head><body>
            <div class="container">
                <div class="title">🆕 NEW LISTING 🆕</div>
                <div class="symbol">{symbol}</div>
                <div class="exchange">Now live on {exchange}</div>
            </div>
            <div class="disclaimer">Not Financial Advice. DYOR.</div>
        </body></html>
        """
        screenshot = "/tmp/new_listing.png"
        await render_html_to_screenshot(html, screenshot)
        output_video = f"/tmp/new_listing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        overlay_on_background(screenshot, output_video)
        caption = f"🆕 NEW LISTING\n\n{symbol} is now live on {exchange.upper()}\n\n#CipherVault #NewListing\n\n⚠️ Not Financial Advice. DYOR."
        await post_to_telegram(output_video, caption)
        return {"status": "success", "video": output_video}
    except Exception as e:
        print(f"❌  new listing video error: {e}")
        return {"error": str(e)}

@with_video_lock
async def generate_volume_spike(payload: dict):
    try:
        symbol = payload["symbol"]; exchange = payload["exchange"]
        multiplier = payload["multiplier"]; volume = payload["volume"]
        html = f"""
        <html><head><style>
            .disclaimer {{ margin-top: 50px; text-align: center; font-size: 24px; color: rgba(255,255,255,0.85); font-family: 'Arial', sans-serif; text-shadow: 0 2px 6px rgba(0,0,0,0.8); }}
            body {{ margin: 0; padding: 60px; font-family: 'Arial', sans-serif; width: 100%; height: 100%; }}
            .container {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }}
            .title {{ font-size: 46px; color: #b829ff; margin-bottom: 40px; font-weight: bold; }}
            .symbol {{ font-size: 64px; color: #ffffff; font-weight: bold; margin: 20px 0; }}
            .mult {{ font-size: 80px; color: #b829ff; font-weight: bold; margin: 30px 0; }}
            .vol {{ font-size: 32px; color: #999; margin-top: 20px; }}
            .exchange {{ font-size: 28px; color: #666; margin-top: 10px; text-transform: uppercase; }}
        </style></head><body>
            <div class="container">
                <div class="title">📊 VOLUME SPIKE 📊</div>
                <div class="symbol">{symbol}</div>
                <div class="mult">{multiplier}x</div>
                <div class="vol">24h Volume: ${volume:,.0f}</div>
                <div class="exchange">{exchange}</div>
            </div>
            <div class="disclaimer">Not Financial Advice. DYOR.</div>
        </body></html>
        """
        screenshot = "/tmp/volume_spike.png"
        await render_html_to_screenshot(html, screenshot)
        output_video = f"/tmp/volume_spike_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        overlay_on_background(screenshot, output_video)
        caption = f"📊 VOLUME SPIKE\n\n{symbol} ({exchange.upper()})\n{multiplier}x average volume\n\n#CipherVault #VolumeSpike\n\n⚠️ Not Financial Advice. DYOR."
        await post_to_telegram(output_video, caption)
        return {"status": "success", "video": output_video}
    except Exception as e:
        print(f"❌  volume spike video error: {e}")
        return {"error": str(e)}

@app.on_event("startup")
async def start_event_triggers():
    asyncio.create_task(run_liquidation_listener(generate_liquidation_alert))
    asyncio.create_task(run_whale_tracker(generate_whale_movement))
    asyncio.create_task(run_volatility_monitor(generate_volatility_alert))
    asyncio.create_task(run_listing_scanner(generate_new_listing, generate_volume_spike))
    print("✅  Event triggers started: liquidation, whale, volatility, listings")
