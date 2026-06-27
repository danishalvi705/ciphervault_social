import sys

with open('app.py', 'r') as f:
    lines = f.readlines()

# Find start of process_video_task (line 50)
start = 49  # 0-indexed

# Find end (look for next function definition)
end = start
for i in range(start + 1, len(lines)):
    if lines[i].startswith('async def ') or lines[i].startswith('def ') or lines[i].startswith('# ---'):
        end = i
        break

print(f"Replacing lines {start+1} to {end}")

# New function
new_func = '''async def process_video_task(signal: SignalPayload | None, chat_id: int | None = None):
    """Generate signal image from HTML template"""
    if not signal:
        return
    
    try:
        # HTML template with signal data
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
            <div class="row"><span class="label">TP</span><span class="value">${signal.tp:.2f}</span></div>
            <div class="row"><span class="label">SL</span><span class="value">${signal.sl:.2f}</span></div>
            <div class="row"><span class="label">GRADE</span><span class="value">{signal.grade}</span></div>
            <div class="row"><span class="label">R:R</span><span class="value">{signal.rr}x</span></div>
        </div>
        </body>
        </html>
        """
        
        # Playwright screenshot
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page()
            await page.set_viewport_size({"width": 540, "height": 960})
            await page.set_content(html)
            image_path = f"/tmp/signal_{signal.id}.png"
            await page.screenshot(path=image_path)
            await browser.close()
        
        # Send to Telegram
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

'''

# Replace
new_lines = lines[:start] + [new_func + '\n'] + lines[end:]

with open('app.py', 'w') as f:
    f.writelines(new_lines)

print("✓ Replaced process_video_task")
