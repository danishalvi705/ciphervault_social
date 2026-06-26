from __future__ import annotations
import subprocess
import logging

logger = logging.getLogger("ciphervault-social-render")

def synthesize_short(
    frame_path: str,
    output_path: str,
    duration: float = 12.0,
    fps: int = 24,  # Reduced to 24 for stability
    zoom_to: float = 1.08,
) -> str:
    """
    Synthesizes a video using FFmpeg directly via subprocess.
    Optimized for low-memory environments (Render 512MB limit).
    """
    
    # Calculate zoom increment per frame
    # (Target - Start) / Total Frames = (1.08 - 1.0) / (12 * 24)
    zoom_increment = (zoom_to - 1.0) / (duration * fps)
    
    # FFmpeg command optimized for memory constraints:
    # -vf zoompan: Sets output to 720x1280 (720p) to reduce RAM usage
    # -preset veryfast: Uses less RAM during encoding compared to 'medium'
    # -threads 1: Crucial to prevent CPU-core-based memory spikes
    # -maxrate/-bufsize: Forces encoder to stay within a memory buffer envelope
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", frame_path,
        "-vf", f"zoompan=z='min(zoom+{zoom_increment:.6f},{zoom_to})':d={int(duration * fps)}:s=720x1280:fps={fps}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-threads", "1",
        "-maxrate", "2M",
        "-bufsize", "4M",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        logger.info(f"Running optimized ffmpeg: {' '.join(cmd)}")
        # Run command and capture output to prevent filling up logs
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Video synthesized successfully via ffmpeg")
        return output_path
        
    except subprocess.CalledProcessError as e:
        # If ffmpeg fails, this will capture the exact error message
        error_msg = e.stderr
        logger.error(f"FFmpeg Error: {error_msg}")
        raise Exception(f"Video synthesis failed: {error_msg}")
