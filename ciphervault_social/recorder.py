import asyncio
import os
import shutil
from playwright.async_api import async_playwright

async def capture_signal_video(dashboard_url: str, output_path: str):
    temp_video_dir = "/tmp/playwright_videos"
    os.makedirs(temp_video_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        
        # Add a realistic User Agent to avoid being blocked by the server
        context = await browser.new_context(
            viewport={"width": 390, "height": 844}, 
            record_video_dir=temp_video_dir,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()

        try:
            print(f"Navigating to {dashboard_url}...")
            # Do NOT rely on networkidle. Load the page simply.
            await page.goto(dashboard_url, timeout=60000)
            
            # --- CRITICAL FIX ---
            # Replace '#app' or '.signal-card' with a unique class/ID found on your dashboard.
            # Right-click the "CipherVault" title or a signal card in your browser -> Inspect
            # and find a reliable selector.
            print("Waiting for dashboard to render...")
            await page.wait_for_selector("body", state="attached", timeout=30000)
            
            # Additional small wait to let JavaScript charts/animations settle
            await asyncio.sleep(3)
            
            print("Recording started...")
            await asyncio.sleep(10)
            print("Recording finished.")
            
        except Exception as e:
            # DEBUG: If it fails, take a screenshot so you can see the 404 error
            error_file = "/tmp/error_capture.png"
            await page.screenshot(path=error_file)
            print(f"FAILED. Screenshot saved to {error_file}. Error: {e}")
            raise e
            
        finally:
            video_file = page.video.path() if page.video else None
            await context.close()
            await browser.close()

            if video_file and os.path.exists(video_file):
                shutil.move(video_file, output_path)
                print(f"Video saved to {output_path}")
            else:
                print("No video file found.")
