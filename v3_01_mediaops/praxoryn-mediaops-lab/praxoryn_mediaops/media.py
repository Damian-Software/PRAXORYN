"""Offline preview media and FFmpeg encode; preview is NOT generative video."""
from __future__ import annotations
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw


def preview_image(path: Path, title: str) -> Path:
    image = Image.new('RGB', (1280,720), (230,239,243))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((80,100,1200,620), radius=45, fill=(21,68,84))
    draw.ellipse((135,165,425,455), fill=(18,164,155))
    draw.rectangle((485,230,1100,270), fill=(225,243,246))
    draw.rectangle((485,320,980,355), fill=(140,190,201))
    draw.rectangle((485,410,1030,445), fill=(140,190,201))
    # No text: diagrams can be reused across translated editions.
    image.save(path)
    return path


def still_to_video(image_path: Path, output_path: Path, seconds: int = 4) -> Path:
    if not (1 <= seconds <= 30):
        raise ValueError('seconds out of range')
    args = ['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1', '-framerate','25',
            '-i', str(image_path), '-t',str(seconds),'-c:v','libx264', '-pix_fmt','yuv420p',
            '-movflags','+faststart', str(output_path)]
    subprocess.run(args, check=True, timeout=90)
    if not output_path.is_file() or output_path.stat().st_size < 1000:
        raise RuntimeError('FFmpeg output missing or empty')
    return output_path
