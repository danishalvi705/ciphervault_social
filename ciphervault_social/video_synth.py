from __future__ import annotations
import subprocess
import logging

logger = logging.getLogger("ciphervault-social-render")

def synthesize_short(
    frame_path: str,
    output_path: str,
    duration: float = 12.0,
    fps: int = 30,
    zoom_to: float = 1.08,
) -> str:
    """
    Synthesizes a video using FFmpeg directly via subprocess.
    This bypasses memory-heavy Python libraries like moviepy.
    """
    
    # Calculate zoom increment per frame
    # 1.08 total zoom over 12 seconds at 30 fps (360 frames)
    # The math: (Target - Start) / Total Frames = (1.08 - 1.0) / 360 = 0.000222
    zoom_increment = (zoom_to - 1.0) / (duration * fps)
    
    # FFmpeg command:
    # -loop 1: Loop the input image
    # -vf zoompan: The high-performance zoom filter
    # -c:v libx264: Efficient codec
    # -t: Duration
    # -pix_fmt yuv420p: Ensure compatibility
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", frame_path,
        "-vf", f"zoompan=z='min(zoom+{zoom_increment:.6f},{zoom_to})':d={int(duration * fps)}:s=1080x1920:fps={fps}",
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
        # Run command and capture output to prevent filling up logs
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info("Video synthesized successfully via ffmpeg")
        return output_path
    except subprocess.CalledProcessError as e:
        # If ffmpeg fails, this will give you the error details
        error_msg = e.stderr.decode()
        logger.error(f"FFmpeg Error: {error_msg}")
        raise Exception(f"Video synthesis failed: {error_msg}")
