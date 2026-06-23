import asyncio
import os
import shutil
from playwright.async_api import async_playwright

async def capture_signal_video(dashboard_url: str, selector: str, output_path: str):
    temp_video_dir = "/tmp/playwright_videos"
    os.makedirs(temp_video_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            record_video_dir=temp_video_dir
        )
        page = await context.new_page()
        
        try:
            print(f"Navigating to {dashboard_url}...")
            # Ensure the page fully loads the dynamic API data
            await page.goto(dashboard_url, wait_until="networkidle", timeout=60000)
            
            # --- DYNAMIC SELECTOR ---
            # Now we use the 'selector' variable passed to this function.
            # This makes the script work for ANY ticker/class.
            print(f"Waiting for signal element: {selector}")
            await page.wait_for_selector(selector, timeout=45000)
            
            print("Recording started...")
            await asyncio.sleep(10)
            print("Recording complete.")
            
        except Exception as e:
            await page.screenshot(path="/tmp/debug_failure.png")
            print(f"FAILED. Could not find selector '{selector}'. Screenshot saved. Error: {e}")
            raise e
            
        finally:
            video_file = await page.video.path()
            await context.close()
            await browser.close()

            if video_file and os.path.exists(video_file):
                shutil.move(video_file, output_path)
                print(f"Video saved to {output_path}")
