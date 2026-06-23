import asyncio
import os
import shutil
import logging
from playwright.async_api import async_playwright

# Setup logging
logger = logging.getLogger("ciphervault-social-render")

async def capture_signal_video(dashboard_url: str, selector: str, output_path: str):
    logger.info("RECORDER: Entering capture_signal_video function.")
    temp_video_dir = "/tmp/playwright_videos"
    os.makedirs(temp_video_dir, exist_ok=True)

    async with async_playwright() as p:
        logger.info("RECORDER: Launching chromium...")
        
        try:
            # Added a very aggressive timeout to the launch itself
            browser = await p.chromium.launch(
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            logger.info("RECORDER: Chromium launched successfully.")
            
            context = await browser.new_context(
                viewport={"width": 1080, "height": 1920},
                record_video_dir=temp_video_dir
            )
            page = await context.new_page()
            
            logger.info(f"RECORDER: Navigating to {dashboard_url}...")
            await page.goto(dashboard_url, wait_until="networkidle", timeout=40000)
            
            logger.info(f"RECORDER: Waiting for selector: {selector}...")
            await page.wait_for_selector(selector, timeout=30000)
            
            logger.info("RECORDER: Selector found. Sleeping for 10s...")
            await asyncio.sleep(10)
            logger.info("RECORDER: Recording finished.")
            
        except Exception as e:
            logger.error(f"RECORDER: CRITICAL FAILURE: {e}")
            raise e
        finally:
            logger.info("RECORDER: Cleaning up browser...")
            try:
                await browser.close()
            except:
                pass
            logger.info("RECORDER: Browser closed.")
