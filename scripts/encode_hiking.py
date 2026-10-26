"""Encode the original Blender scene after rendering all 288 PNG frames.
python scripts/encode_hiking.py [--frames /path/to/frames]
"""
import argparse
from pathlib import Path
import subprocess
import imageio_ffmpeg

parser = argparse.ArgumentParser()
parser.add_argument("--frames", type=Path, default=Path("/private/tmp/weijia-snow-frames"))
args = parser.parse_args()
assert all((args.frames / f"{i:04d}.png").is_file() for i in range(288)), "Render all 288 frames first."
root = Path(__file__).resolve().parents[1]
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([
    ffmpeg, "-y", "-v", "error", "-framerate", "24", "-i", str(args.frames / "%04d.png"),
    "-frames:v", "288", "-an", "-c:v", "libx264", "-crf", "20", "-preset", "slow",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(root / "media/hiking-stylized.mp4")
], check=True)
subprocess.run([
    ffmpeg, "-y", "-v", "error", "-i", str(args.frames / "0020.png"),
    "-frames:v", "1", "-q:v", "2", str(root / "media/hiking-stylized-poster.jpg")
], check=True)
