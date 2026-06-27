async def generate_signal_card_image(signal: Signal) -> str:
    # Formatting TP values safely
    tp_values = signal.tp + [0.0, 0.0, 0.0]  # Ensure at least 3 values exist
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 0; width: 1080px; height: 1920px; background: transparent; font-family: 'Arial', sans-serif; display: flex; align-items: center; justify-content: center; }}
        .card {{ 
            background: rgba(15, 15, 15, 0.9); border: 2px solid #333; border-radius: 40px; 
            padding: 60px; color: white; width: 850px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }}
        .badge {{ background: #d4a373; padding: 10px 20px; border-radius: 20px; font-weight: bold; color: black; }}
        .symbol {{ font-size: 80px; font-weight: bold; margin-bottom: 40px; }}
        .row {{ display: flex; justify-content: space-between; padding: 30px 0; border-bottom: 1px solid #333; font-size: 36px; }}
        .green {{ color: #00ff88; }}
        .red {{ color: #ff6b6b; }}
        .footer {{ display: flex; justify-content: space-between; margin-top: 50px; }}
        .box {{ background: #222; padding: 30px; border-radius: 20px; text-align: center; width: 250px; }}
    </style>
    </head>
    <body>
    <div class="card">
        <div class="header">
            <div style="font-size: 40px; letter-spacing: 5px;">CIPHERVAULT</div>
            <div class="badge">LIVE</div>
        </div>
        <div class="symbol">{signal.symbol}</div>
        <div class="row"><span>ENTRY</span><span class="green">${signal.entry:,.2f}</span></div>
        <div class="row"><span>TP1</span><span>${tp_values[0]:,.2f}</span></div>
        <div class="row"><span>TP2</span><span>${tp_values[1]:,.2f}</span></div>
        <div class="row"><span>TP3</span><span>${tp_values[2]:,.2f}</span></div>
        <div class="row"><span>SL</span><span class="red">${signal.sl:,.2f}</span></div>
        <div class="footer">
            <div class="box"><div style="font-size: 20px; color: #888;">GRADE</div><div style="font-size: 40px; font-weight:bold;">{signal.grade}</div></div>
            <div class="box"><div style="font-size: 20px; color: #888;">SCORE</div><div style="font-size: 40px; font-weight:bold;">{signal.score}/10</div></div>
            <div class="box"><div style="font-size: 20px; color: #888;">R:R</div><div style="font-size: 40px; font-weight:bold;">{signal.rr}x</div></div>
        </div>
        <div style="margin-top: 50px; font-size: 20px; color: #555; text-align: center;">
            ⚠️ DISCLAIMER: Not financial advice | Trade at your own risk | Past performance ≠ Future results
        </div>
    </div>
    </body>
    </html>
    """
    temp_image = f"/tmp/card_{signal.id}.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox'])
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1080, "height": 1920})
        await page.set_content(html)
        await page.screenshot(path=temp_image, omit_background=True)
        await browser.close()
    return temp_image
