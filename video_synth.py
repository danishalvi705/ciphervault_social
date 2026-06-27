import subprocess
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def synthesize_short(frame_path, output_path, card_path="signal_card.png", duration=5, fps=30):
    # Filter for background zoom + overlay for the card
    # [0:v] is the background, [1:v] is the signal card
    filter_complex = (
        f"zoompan=z='min(zoom+0.001,1.1)':d={int(duration * fps)}:s=720x1280:fps={fps}[bg];"
        f"[bg][1:v]overlay=0:0"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", frame_path,       # Input 0: Background
        "-i", card_path,        # Input 1: Trading Card
        "-filter_complex", filter_complex,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg Error: {e.stderr}")
        raise Exception(f"Video synthesis failed: {e.stderr}")
