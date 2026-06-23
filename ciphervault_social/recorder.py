import asyncio
import os
import shutil
from playwright.async_api import async_playwright

async def capture_signal_video(dashboard_url: str, output_path: str):
    temp_video_dir = "/tmp/playwright_videos"
    os.makedirs(temp_video_dir, exist_ok=True)
    
    # Clean up old temporary files just in case
    for f in os.listdir(temp_video_dir):
        os.remove(os.path.join(temp_video_dir, f))

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        
        context = await browser.new_context(
            viewport={"width": 390, "height": 844}, 
            record_video_dir=temp_video_dir,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()

        try:
            print(f"Navigating to {dashboard_url}...")
            # Navigate and wait for basic load
            await page.goto(dashboard_url, timeout=60000, wait_until="domcontentloaded")
            
            # --- CRITICAL FIX ---
            # 'body' is too fast. Replace '.chart-container' with the actual class
            # of your signal card, chart, or dashboard wrapper.
            # You can check this by Inspecting the element in your browser.
            selector = ".signal-card" 
            print(f"Waiting for {selector} to render...")
            await page.wait_for_selector(selector, state="visible", timeout=30000)
            
            # Allow charts/animations to stabilize
            await asyncio.sleep(4)
            
            print("Recording started...")
            await asyncio.sleep(10)
            print("Recording finished.")
            
        except Exception as e:
            # Capture the state of the page at the moment of failure
            await page.screenshot(path="/tmp/error_capture.png")
            print(f"FAILED. Error: {e}")
            raise e
            
        finally:
            # Important: Get the path BEFORE closing the context
            video_file = page.video.path() if page.video else None
            await context.close()
            await browser.close()

            # Verify the file exists and is not empty before attempting to move
            if video_file and os.path.exists(video_file) and os.path.getsize(video_file) > 1024:
                shutil.move(video_file, output_path)
                print(f"Video saved successfully: {output_path}")
            else:
                print("Error: No valid video file generated.")
                raise FileNotFoundError("Video file was empty or missing.")
