import asyncio
import os
import shutil
from playwright.async_api import async_playwright

async def capture_signal_video(dashboard_url: str, output_path: str):
    temp_video_dir = "/tmp/playwright_videos"
    os.makedirs(temp_video_dir, exist_ok=True)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        
        # Set mobile-like dimensions (390x844 is standard iPhone size)
        # Using 1080x1920 is fine too, but this viewport defines the recording area
        context = await browser.new_context(
            viewport={"width": 390, "height": 844}, 
            record_video_dir=temp_video_dir
        )
        page = await context.new_page()

        try:
            print(f"Navigating to {dashboard_url}...")
            # 'networkidle' waits for the page to finish loading all data
            await page.goto(dashboard_url, wait_until="networkidle", timeout=60000)
            
            # Small buffer to ensure the UI renders nicely
            await asyncio.sleep(2)
            
            print("Recording started...")
            # This is your total recording time
            await asyncio.sleep(10)
            print("Recording finished.")
            
        except Exception as e:
            print(f"Error: {e}")
            raise e
            
        finally:
            video_file = page.video.path() if page.video else None
            await context.close()
            await browser.close()

            if video_file and os.path.exists(video_file):
                shutil.move(video_file, output_path)
                print(f"Video saved to {output_path}")
