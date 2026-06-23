import asyncio
import os
import shutil
from playwright.async_api import async_playwright

async def capture_signal_video(dashboard_url: str, selector: str, output_path: str):
    temp_video_dir = "/tmp/playwright_videos"
    os.makedirs(temp_video_dir, exist_ok=True)

    async with async_playwright() as p:
        # --- ESSENTIAL RENDER/DOCKER FLAGS ---
        # --no-sandbox: Required for Linux container environments
        # --disable-dev-shm-usage: Fixes "hanging" caused by low memory in /dev/shm
        browser = await p.chromium.launch(
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-dev-shm-usage"
            ]
        )
        
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            record_video_dir=temp_video_dir,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"DEBUG: Navigating to {dashboard_url}...")
            # Increased timeout to 60s for slow network
            await page.goto(dashboard_url, wait_until="networkidle", timeout=60000)
            
            # Diagnostic: Take a quick look if it loads
            print("DEBUG: Page navigation command sent.")
            
            print(f"DEBUG: Waiting for selector: {selector}")
            # wait_for_selector will raise a TimeoutError if the selector is not found
            await page.wait_for_selector(selector, timeout=30000)
            
            print("DEBUG: Selector found. Recording...")
            # We record for 10 seconds
            await asyncio.sleep(10)
            print("DEBUG: Recording finished.")
            
        except Exception as e:
            # Capture a screenshot to see if the page is just white or erroring out
            await page.screenshot(path="/tmp/debug_failure.png")
            print(f"CRITICAL ERROR in recorder.py: {e}")
            raise e
            
        finally:
            # Find the video file
            video_file = await page.video.path()
            
            await context.close()
            await browser.close()

            if video_file and os.path.exists(video_file):
                shutil.move(video_file, output_path)
                print(f"SUCCESS: Video moved to {output_path}")
            else:
                print("ERROR: Video file was not created by Playwright.")
