import os
import asyncio
import random
from dotenv import load_dotenv
from video_synth import synthesize_short
from generator import create_card
from telegram import Bot

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def test_flow():
    # Full signal data dictionary
    signal_data = {
        "symbol": "BTC/USDT",
        "entry": "60000",
        "tp1": "61000",
        "tp2": "62000",
        "tp3": "63000",
        "sl": "59000",
        "grade": "A",
        "score": "8.9/10",
        "rr": "3.1x"
    }
    
    temp_card = "temp_card.png"

    # 1. Generate the card
    print("Generating card...")
    create_card(signal_data, output_path=temp_card)

    if not os.path.exists(temp_card):
        print("Error: temp_card.png was not generated.")
        return

    # 2. Select random background
    bg_folder = "backgrounds"
    bg_files = [f for f in os.listdir(bg_folder) if f.endswith(".mp4")]
    if not bg_files:
        print("Error: No background videos found.")
        return
    selected_bg = os.path.join(bg_folder, random.choice(bg_files))
    output_filename = "test_output.mp4"

    # 3. Synthesize
    print(f"Synthesizing {output_filename}...")
    try:
        synthesize_short(selected_bg, output_filename, card_path=temp_card)

        if os.path.exists(output_filename):
            bot = Bot(token=BOT_TOKEN)
            with open(output_filename, 'rb') as video_file:
                await bot.send_video(chat_id=CHAT_ID, video=video_file, caption="🚀 Signal Analysis Ready")
            print("Successfully sent!")

            # Clean up
            if os.path.exists(output_filename): os.remove(output_filename)
            if os.path.exists(temp_card): os.remove(temp_card)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_flow())
