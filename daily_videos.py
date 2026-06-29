"""
daily_videos.py — CipherVault Daily & Weekly Video Generator
Add this file to your ~/ciphervault_social/ directory on Render.

Videos generated at 7PM UTC daily:
  1. Top Signals of the Day
  2. Market Summary (top gainers/losers from your signals)
  3. Fear & Greed Index
  4. Weekly Leaderboard (Saturdays only)

All data pulled from your Digital Ocean API + CoinGecko Fear & Greed API.
"""

import os
import asyncio
import random
import logging
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

DO_API_BASE   = os.getenv("DO_API_BASE", "http://168.144.131.132:8000")
BACKGROUND_DIR = "./backgrounds"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pick_bg() -> str:
    bg_videos = list(Path(BACKGROUND_DIR).glob("*.mp4"))
    if not bg_videos:
        raise Exception("No background videos in ./backgrounds")
    return str(random.choice(bg_videos))


async def html_to_image(html: str, out_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(path=out_path, omit_background=True)
        await browser.close()


def image_to_video(image_path: str, video_path: str, duration: int = 10):
    import subprocess
    bg = pick_bg()
    cmd = [
        "ffmpeg", "-y", "-i", bg, "-i", image_path,
        "-filter_complex", "[0:v][1:v]overlay=(W-w)/2:(H-h)/2",
        "-t", str(duration), "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg error: {result.stderr}")


async def send_telegram_video(video_path: str, caption: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not set, skipping send.")
        return
    with open(video_path, "rb") as f:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo",
            files={"video": f},
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"},
            timeout=60,
        )
    if not resp.ok:
        logger.error(f"Telegram send failed: {resp.text}")


def fetch_signals():
    resp = requests.get(f"{DO_API_BASE}/api/signals", timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_stats():
    resp = requests.get(f"{DO_API_BASE}/api/stats", timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_fear_and_greed():
    resp = requests.get(
        "https://api.alternative.me/fng/?limit=1", timeout=10
    )
    resp.raise_for_status()
    data = resp.json()["data"][0]
    return {
        "value": int(data["value"]),
        "label": data["value_classification"],
    }


# ---------------------------------------------------------------------------
# Card CSS base (shared across all cards)
# ---------------------------------------------------------------------------

BASE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    width: 1080px; height: 1920px;
    display: flex; align-items: center; justify-content: center;
    background: transparent !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.card {
    width: 700px;
    background: rgba(5, 5, 10, 0.55);
    border: 2px solid rgba(0, 255, 136, 0.7);
    border-radius: 40px;
    padding: 40px 50px;
    color: #ffffff;
    box-shadow: 0 10px 60px rgba(0,0,0,0.95);
    display: flex; flex-direction: column;
}
.header {
    font-size: 22px; color: rgba(0,255,136,0.8);
    text-transform: uppercase; letter-spacing: 3px;
    margin-bottom: 8px;
}
.title {
    font-size: 48px; font-weight: bold; color: #ffffff;
    margin-bottom: 30px; line-height: 1.1;
}
.divider {
    height: 1px; background: rgba(255,255,255,0.15);
    margin: 10px 0;
}
.row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 0; border-bottom: 1px solid rgba(255,255,255,0.08);
    font-size: 28px; color: #ffffff;
}
.row:last-child { border-bottom: none; }
.green  { color: #00ff88; font-weight: bold; }
.red    { color: #ff4444; font-weight: bold; }
.yellow { color: #ffd700; font-weight: bold; }
.gray   { color: rgba(255,255,255,0.5); }
.badge {
    display: inline-block; padding: 4px 14px;
    border-radius: 20px; font-size: 22px; font-weight: bold;
}
.badge-long  { background: rgba(0,255,136,0.2); color: #00ff88; }
.badge-short { background: rgba(255,68,68,0.2);  color: #ff4444; }
.footer-note {
    margin-top: 20px; font-size: 16px;
    color: rgba(255,255,255,0.35); text-align: center;
}
.stat-grid {
    display: flex; gap: 12px; margin: 20px 0;
}
.stat-box {
    flex: 1; background: rgba(255,255,255,0.06);
    padding: 18px 10px; border-radius: 16px;
    text-align: center; font-size: 22px; color: rgba(255,255,255,0.7);
}
.stat-box b { display: block; font-size: 32px; margin-top: 6px; color: #00ff88; }
"""


# ---------------------------------------------------------------------------
# 1. Top Signals of the Day
# ---------------------------------------------------------------------------

async def generate_top_signals_video():
    logger.info("[Daily] Generating Top Signals video...")
    signals = fetch_signals()

    # Filter today's signals
    today = datetime.now(timezone.utc).date()
    today_signals = [
        s for s in signals
        if s.get("created_at", "")[:10] == str(today)
    ]

    # If no signals today, use last 5 overall sorted by score
    if not today_signals:
        today_signals = sorted(signals, key=lambda x: x.get("score", 0), reverse=True)[:5]
        period = "Recent Top"
    else:
        today_signals = sorted(today_signals, key=lambda x: x.get("score", 0), reverse=True)[:5]
        period = "Today's Top"

    rows_html = ""
    for s in today_signals:
        direction = s.get("direction", "LONG")
        badge_cls = "badge-long" if direction == "LONG" else "badge-short"
        grade = s.get("grade", "").split(" ")[0]
        score = s.get("score", 0)
        status = s.get('status', 'pending')
        if 'tp3' in status:   status_str, status_cls = 'TP3 ✅', 'green'
        elif 'tp2' in status: status_str, status_cls = 'TP2 ✅', 'green'
        elif 'tp1' in status: status_str, status_cls = 'TP1 ✅',    'green'
        elif 'sl'  in status: status_str, status_cls = 'SL ❌',     'red'
        elif status == 'active':  status_str, status_cls = 'ACTIVE 🟢', 'green'
        else:                     status_str, status_cls = 'PENDING ⏳', 'gray'
        rows_html += f"""
        <div class="row">
            <span style="font-size:22px">{s.get('symbol','')}</span>
            <span class="badge {badge_cls}" style="font-size:16px">{direction}</span>
            <span class="yellow" style="font-size:22px">{grade}</span>
            <span class="{status_cls}" style="font-size:20px">{status_str}</span>
        </div>"""

    html = f"""<!DOCTYPE html><html><head><style>{BASE_CSS}</style></head><body>
    <div class="card">
        <div class="header">CipherVault Signals</div>
        <div class="title">🔥 {period}<br>Signals</div>
        <div class="divider"></div>
        <div class="row" style="font-size:20px;color:rgba(255,255,255,0.5)">
            <span>PAIR</span><span>SIDE</span><span>GRADE</span><span>SCORE</span>
        </div>
        {rows_html}
        <div class="footer-note">Disclaimer: Not financial advice. Trade at your own risk.</div>
    </div>
    </body></html>"""

    img = f"/tmp/daily_signals_{today}.png"
    vid = f"/tmp/daily_signals_{today}.mp4"
    await html_to_image(html, img)
    image_to_video(img, vid, duration=10)

    caption = f"""🔥 <b>{period} Signals</b>
{chr(10).join([f"• <b>{s['symbol']}</b> {s['direction']} | Grade: {s['grade'].split()[0]} | Score: {s['score']}/10" for s in today_signals])}

#CipherVault #crypto #signals"""
    await send_telegram_video(vid, caption)
    logger.info("[Daily] Top Signals video sent!")
    return vid


# ---------------------------------------------------------------------------
# 2. Market Summary
# ---------------------------------------------------------------------------

async def generate_market_summary_video():
    logger.info("[Daily] Generating Market Summary video...")
    signals = fetch_signals()
    stats   = fetch_stats()

    today = datetime.now(timezone.utc).date()
    today_signals = [
        s for s in signals
        if s.get("created_at", "")[:10] == str(today)
    ]
    total_today   = len(today_signals)
    longs_today   = sum(1 for s in today_signals if s.get("direction") == "LONG")
    shorts_today  = total_today - longs_today
    bias          = "BULLISH 📈" if longs_today >= shorts_today else "BEARISH 📉"
    bias_color    = "green" if longs_today >= shorts_today else "red"

    win_rate  = stats.get("win_rate", 0)
    avg_rr    = stats.get("avg_rr", 0)
    total_sig = stats.get("total_signals", 0)
    wins      = stats.get("wins", 0)
    losses    = stats.get("losses", 0)

    html = f"""<!DOCTYPE html><html><head><style>{BASE_CSS}</style></head><body>
    <div class="card">
        <div class="header">CipherVault</div>
        <div class="title">📊 Daily Market<br>Summary</div>
        <div class="divider"></div>

        <div class="row">
            <span>Date</span>
            <span class="gray">{today.strftime('%b %d, %Y')}</span>
        </div>
        <div class="row">
            <span>Market Bias</span>
            <span class="{bias_color}">{bias}</span>
        </div>
        <div class="row">
            <span>Signals Today</span>
            <span class="yellow">{total_today}</span>
        </div>
        <div class="row">
            <span>Longs / Shorts</span>
            <span><span class="green">{longs_today}L</span> / <span class="red">{shorts_today}S</span></span>
        </div>

        <div class="divider" style="margin-top:20px"></div>
        <div style="font-size:20px;color:rgba(255,255,255,0.5);margin:12px 0">ALL TIME STATS</div>

        <div class="stat-grid">
            <div class="stat-box">WIN RATE<br><b>{win_rate}%</b></div>
            <div class="stat-box">AVG R:R<br><b>{avg_rr}x</b></div>
            <div class="stat-box">TOTAL<br><b>{total_sig}</b></div>
        </div>
        <div class="stat-grid">
            <div class="stat-box" style="color:#00ff88">WINS<br><b style="color:#00ff88">{wins}</b></div>
            <div class="stat-box" style="color:#ff4444">LOSSES<br><b style="color:#ff4444">{losses}</b></div>
        </div>

        <div class="footer-note">Disclaimer: Not financial advice. Trade at your own risk.</div>
    </div>
    </body></html>"""

    img = f"/tmp/daily_summary_{today}.png"
    vid = f"/tmp/daily_summary_{today}.mp4"
    await html_to_image(html, img)
    image_to_video(img, vid, duration=10)

    caption = f"""📊 <b>Daily Market Summary — {today.strftime('%b %d, %Y')}</b>

Market Bias: <b>{bias}</b>
Signals Today: <b>{total_today}</b> (Longs: {longs_today} | Shorts: {shorts_today})

📈 All-Time Stats:
• Win Rate: <b>{win_rate}%</b>
• Avg R:R: <b>{avg_rr}x</b>
• Total Signals: <b>{total_sig}</b>

#CipherVault #crypto #marketupdate"""
    await send_telegram_video(vid, caption)
    logger.info("[Daily] Market Summary video sent!")
    return vid


# ---------------------------------------------------------------------------
# 3. Fear & Greed Index
# ---------------------------------------------------------------------------

async def generate_fear_greed_video():
    logger.info("[Daily] Generating Fear & Greed video...")
    fg = fetch_fear_and_greed()
    value = fg["value"]
    label = fg["label"]
    today = datetime.now(timezone.utc).date()

    # Color based on value
    if value <= 25:
        color = "#ff4444"
        emoji = "😱"
    elif value <= 45:
        color = "#ff8c00"
        emoji = "😟"
    elif value <= 55:
        color = "#ffd700"
        emoji = "😐"
    elif value <= 75:
        color = "#90ee90"
        emoji = "😊"
    else:
        color = "#00ff88"
        emoji = "🤑"

    # Gauge arc percentage
    pct = value / 100.0
    arc_color = color

    html = f"""<!DOCTYPE html><html><head><style>
    {BASE_CSS}
    .gauge-container {{
        display: flex; flex-direction: column; align-items: center;
        margin: 20px 0;
    }}
    .gauge-value {{
        font-size: 120px; font-weight: bold; color: {arc_color};
        line-height: 1; margin: 10px 0;
    }}
    .gauge-label {{
        font-size: 38px; font-weight: bold; color: {arc_color};
        text-transform: uppercase; letter-spacing: 2px;
    }}
    .gauge-bar-bg {{
        width: 100%; height: 20px; background: rgba(255,255,255,0.1);
        border-radius: 10px; margin: 20px 0; overflow: hidden;
    }}
    .gauge-bar-fill {{
        height: 100%; width: {value}%;
        background: linear-gradient(90deg, #ff4444, #ffd700, #00ff88);
        border-radius: 10px;
    }}
    .scale-labels {{
        display: flex; justify-content: space-between;
        font-size: 18px; color: rgba(255,255,255,0.4);
        width: 100%;
    }}
    </style></head><body>
    <div class="card">
        <div class="header">CipherVault</div>
        <div class="title">{emoji} Fear &amp; Greed<br>Index</div>
        <div class="divider"></div>

        <div class="gauge-container">
            <div class="gauge-value">{value}</div>
            <div class="gauge-label">{label}</div>
            <div class="gauge-bar-bg">
                <div class="gauge-bar-fill"></div>
            </div>
            <div class="scale-labels">
                <span>😱 Fear</span>
                <span>😐 Neutral</span>
                <span>🤑 Greed</span>
            </div>
        </div>

        <div class="divider"></div>
        <div class="row">
            <span>Date</span>
            <span class="gray">{today.strftime('%b %d, %Y')}</span>
        </div>
        <div class="row">
            <span>Signal</span>
            <span style="color:{arc_color};font-weight:bold">
                {"BUY THE FEAR" if value <= 30 else "TAKE PROFIT" if value >= 75 else "HOLD STEADY"}
            </span>
        </div>

        <div class="footer-note">Source: alternative.me | Not financial advice.</div>
    </div>
    </body></html>"""

    img = f"/tmp/fear_greed_{today}.png"
    vid = f"/tmp/fear_greed_{today}.mp4"
    await html_to_image(html, img)
    image_to_video(img, vid, duration=10)

    caption = f"""{emoji} <b>Crypto Fear &amp; Greed Index</b>

Today's Score: <b>{value}/100</b>
Sentiment: <b>{label}</b>

{'🟢 Markets in extreme fear — historically a good buying opportunity!' if value <= 25 else '🔴 Extreme greed — consider taking profits!' if value >= 75 else '🟡 Market sentiment is neutral — watch for breakouts.'}

#CipherVault #crypto #fearandgreed"""
    await send_telegram_video(vid, caption)
    logger.info("[Daily] Fear & Greed video sent!")
    return vid


# ---------------------------------------------------------------------------
# 4. Weekly Leaderboard (Saturdays only)
# ---------------------------------------------------------------------------

async def generate_weekly_leaderboard_video():
    logger.info("[Weekly] Generating Leaderboard video...")
    signals = fetch_signals()
    stats   = fetch_stats()

    # Last 7 days
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    week_signals = [
        s for s in signals
        if s.get("created_at", "") >= week_ago.isoformat()
    ]

    # Top 5 by score this week
    top5 = sorted(week_signals, key=lambda x: x.get("score", 0), reverse=True)[:5]

    # Weekly win/loss
    closed = [s for s in week_signals if s.get("status") not in ("pending", "active")]
    wins   = sum(1 for s in closed if "tp" in s.get("status", ""))
    losses = sum(1 for s in closed if s.get("status") == "sl_hit")
    win_rate = round(wins / len(closed) * 100, 1) if closed else 0

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    rows_html = ""
    for i, s in enumerate(top5):
        direction = s.get("direction", "LONG")
        badge_cls = "badge-long" if direction == "LONG" else "badge-short"
        grade = s.get("grade", "").split(" ")[0]
        rows_html += f"""
        <div class="row">
            <span style="font-size:26px">{medals[i]}</span>
            <span style="font-size:22px">{s.get('symbol','')}</span>
            <span class="badge {badge_cls}" style="font-size:18px">{direction}</span>
            <span class="yellow" style="font-size:22px">{grade}</span>
            <span class="gray" style="font-size:22px">{s.get('score',0)}/10</span>
        </div>"""

    today = datetime.now(timezone.utc).date()
    week_start = (today - timedelta(days=6)).strftime('%b %d')
    week_end   = today.strftime('%b %d')

    html = f"""<!DOCTYPE html><html><head><style>{BASE_CSS}</style></head><body>
    <div class="card">
        <div class="header">CipherVault Weekly</div>
        <div class="title">🏆 Leaderboard<br><span style="font-size:28px;color:rgba(255,255,255,0.5)">{week_start} – {week_end}</span></div>
        <div class="divider"></div>

        <div class="stat-grid">
            <div class="stat-box">WIN RATE<br><b>{win_rate}%</b></div>
            <div class="stat-box" style="color:#00ff88">WINS<br><b style="color:#00ff88">{wins}</b></div>
            <div class="stat-box" style="color:#ff4444">LOSSES<br><b style="color:#ff4444">{losses}</b></div>
        </div>

        <div class="divider"></div>
        <div style="font-size:20px;color:rgba(255,255,255,0.5);margin:10px 0">TOP SIGNALS THIS WEEK</div>

        {rows_html}

        <div class="row" style="margin-top:10px">
            <span>All-Time Win Rate</span>
            <span class="green">{stats.get('win_rate',0)}%</span>
        </div>
        <div class="row">
            <span>All-Time Avg R:R</span>
            <span class="yellow">{stats.get('avg_rr',0)}x</span>
        </div>

        <div class="footer-note">Disclaimer: Not financial advice. Trade at your own risk.</div>
    </div>
    </body></html>"""

    img = f"/tmp/leaderboard_{today}.png"
    vid = f"/tmp/leaderboard_{today}.mp4"
    await html_to_image(html, img)
    image_to_video(img, vid, duration=12)

    caption = f"""🏆 <b>Weekly Leaderboard — {week_start} to {week_end}</b>

This Week:
• Win Rate: <b>{win_rate}%</b>
• Wins: <b>{wins}</b> | Losses: <b>{losses}</b>

Top Signals:
{chr(10).join([f"{medals[i]} {s['symbol']} {s['direction']} | {s['grade'].split()[0]} | {s['score']}/10" for i, s in enumerate(top5)])}

#CipherVault #crypto #leaderboard #weeklyreview"""
    await send_telegram_video(vid, caption)
    logger.info("[Weekly] Leaderboard video sent!")
    return vid


# ---------------------------------------------------------------------------
# Main scheduler — called by APScheduler in main.py
# ---------------------------------------------------------------------------

async def run_daily_videos():
    """Run all daily videos. Call this at 7PM UTC every day."""
    today_weekday = datetime.now(timezone.utc).weekday()  # 5 = Saturday

    tasks = [
        generate_top_signals_video(),
        generate_market_summary_video(),
        generate_fear_greed_video(),
    ]

    # Add weekly leaderboard on Saturdays
    if today_weekday == 5:
        tasks.append(generate_weekly_leaderboard_video())

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error(f"[Daily Video {i}] Failed: {r}")
