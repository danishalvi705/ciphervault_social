import asyncio
import os
import shutil
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger("ciphervault-social-render")

async def capture_signal_video(dashboard_url: str, selector: str, output_path: str):
    logger.info("RECORDER: Entering capture function.")
    temp_video_dir = "/tmp/playwright_videos"
    os.makedirs(temp_video_dir, exist_ok=True)

    async with async_playwright() as p:
        # Added --disable-gpu to save memory
        browser = await p.chromium.launch(
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        
        context = await browser.new_context(viewport={"width": 1080, "height": 1920})
        page = await context.new_page()
        
        try:
            logger.info(f"RECORDER: Navigating to {dashboard_url}...")
            await page.goto(dashboard_url, wait_until="domcontentloaded", timeout=40000)
            
            logger.info(f"RECORDER: Waiting for selector: {selector}...")
            # If this times out, it will go to the 'except' block
            await page.wait_for_selector(selector, timeout=20000)
            
            logger.info("RECORDER: Selector found. Recording...")
            await asyncio.sleep(10)
            logger.info("RECORDER: Recording finished.")
            
        except Exception as e:
            # DUMP PAGE CONTENT TO LOGS to see why it failed
            content = await page.content()
            logger.error(f"RECORDER: FAILED. Page content snippet: {content[:500]}")
            logger.error(f"RECORDER: CRITICAL FAILURE: {e}")
            raise e
        finally:
            await browser.close()
            logger.info("RECORDER: Browser closed.")
