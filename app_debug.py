# Add this at the top of process_video_task to see errors

async def process_video_task(signal: Signal):
    """Generate signal image from HTML template"""
    if not signal:
        return
    
    print(f"DEBUG: Starting task for {signal.symbol}")
    print(f"DEBUG: TELEGRAM_BOT_TOKEN set: {bool(TELEGRAM_BOT_TOKEN)}")
    print(f"DEBUG: TELEGRAM_CHAT_ID set: {bool(TELEGRAM_CHAT_ID)}")
    
    try:
        html = f"""<!DOCTYPE html>..."""  # Your HTML
        
        print(f"DEBUG: HTML generated, launching Playwright...")
        async with async_playwright() as p:
            print(f"DEBUG: Launching browser...")
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page()
            await page.set_viewport_size({"width": 540, "height": 960})
            await page.set_content(html)
            image_path = f"/tmp/signal_{signal.id}.png"
            print(f"DEBUG: Taking screenshot to {image_path}...")
            await page.screenshot(path=image_path)
            await browser.close()
            print(f"DEBUG: Screenshot saved")
        
        print(f"DEBUG: Sending to Telegram...")
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            with open(image_path, 'rb') as f:
                resp = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    files={"photo": f},
                    data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"{signal.symbol} {signal.side}"}
                )
            print(f"DEBUG: Telegram response: {resp.status_code}")
        else:
            print(f"DEBUG: Telegram credentials missing!")
        
        logger.info(f"Image sent for {signal.symbol}")
    except Exception as e:
        print(f"DEBUG: Exception caught: {e}")
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
    finally:
        gc.collect()
