import os
import asyncio
from video_synth import synthesize_short
from telegram import Bot

# Update these with your actual values
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

async def test_flow():
    print("Generating test video...")
    
    test_signal = {
        "symbol": "BTC/USDT",
        "side": "BUY",
        "entry_price": 69150.25
    }
    
    try:
        # Calling the function we found in your file
        video_path = synthesize_short(test_signal)
        
        if os.path.exists(video_path):
            print(f"Video generated: {video_path}")
            
            bot = Bot(token=BOT_TOKEN)
            with open(video_path, 'rb') as video_file:
                await bot.send_video(
                    chat_id=CHAT_ID,
                    video=video_file,
                    caption="🚀 Test Signal Analysis"
                )
            print("Successfully sent!")
        else:
            print("Error: Video file was not created.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_flow())
