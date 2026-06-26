import os
import asyncio
from dotenv import load_dotenv
from video_synth import synthesize_short
from telegram import Bot

# Load variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def test_flow():
    print("Generating test video...")
    
    frame_directory = "backgrounds" 
    output_filename = "test_output.mp4"
    
    try:
        # Generate video
        synthesize_short(frame_directory, output_filename)
        
        if os.path.exists(output_filename):
            print(f"Video generated: {output_filename}")
            
            # Send to Telegram
            bot = Bot(token=BOT_TOKEN)
            with open(output_filename, 'rb') as video_file:
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
