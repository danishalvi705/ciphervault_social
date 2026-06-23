import asyncio
import os
import shutil
from playwright.async_api import async_playwright

async def capture_signal_video(dashboard_url: str, selector: str, output_path: str):
    # Directory to store the raw recording before moving to final destination
    temp_video_dir = "/tmp/playwright_videos"
    os.makedirs(temp_video_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        
        # 1. Video MUST be configured here, when creating the context
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            record_video_dir=temp_video_dir
        )
        page = await context.new_page()
        
        try:
            # 2. Use 'networkidle' to wait for your dashboard charts/data to finish loading
            print(f"Navigating to {dashboard_url}...")
            await page.goto(dashboard_url, wait_until="networkidle", timeout=60000)
            
            # 3. Wait for the selector
            print(f"Waiting for selector: {selector}")
            await page.wait_for_selector(selector, timeout=45000)
            
            # Record for 10 seconds
            print("Recording started...")
            await asyncio.sleep(10)
            print("Recording complete.")
            
        except Exception as e:
            # DEBUGGING: If it fails, this captures exactly what the bot saw
            await page.screenshot(path="/tmp/debug_failure.png")
            print(f"FAILED. Screenshot saved to /tmp/debug_failure.png. Error: {e}")
            raise e
            
        finally:
            # 4. Save video path before closing
            video_file = await page.video.path()
            await context.close()
            await browser.close()

            # 5. Move the file to your desired output_path
            if video_file and os.path.exists(video_file):
                shutil.move(video_file, output_path)
                print(f"Video saved to {output_path}")
