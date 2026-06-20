"""
CipherVault Social — Video Synthesizer
Turns a composed 1080x1920 frame into a short MP4 with a slow zoom for
motion (platforms favor video over static images). Pin moviepy==1.0.3 —
the 2.x rewrite renames set_duration/resize/etc. and will break this file.
"""

from __future__ import annotations
from moviepy.editor import ImageClip, CompositeVideoClip

CANVAS_W, CANVAS_H = 1080, 1920


def synthesize_short(
    frame_path: str,
    output_path: str,
    duration: float = 12.0,
    fps: int = 30,
    zoom_to: float = 1.08,
) -> str:
    clip = (
        ImageClip(frame_path)
        .set_duration(duration)
        .resize(lambda t: 1 + (zoom_to - 1) * (t / duration))
        .set_position("center")
    )

    final = CompositeVideoClip([clip], size=(CANVAS_W, CANVAS_H)).set_duration(duration)

    final.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio=False,
        preset="medium",
        ffmpeg_params=["-pix_fmt", "yuv420p"],
        logger=None,
    )
    final.close()
    clip.close()
    return output_path
