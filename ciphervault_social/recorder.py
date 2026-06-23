from playwright.async_api import async_playwright

async def capture_signal_video(dashboard_url: str, selector: str, output_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1080, "height": 1920})
        page = await context.new_page()
        await page.goto(dashboard_url)
        await page.wait_for_selector(selector)
        
        # Start recording
        await page.video.start(path=output_path, record_video_size={"width": 1080, "height": 1920})
        await asyncio.sleep(10) # 10 second record
        await page.video.stop()
        await browser.close()
